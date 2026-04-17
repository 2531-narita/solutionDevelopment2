from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st
try:
    from streamlit_image_coordinates import streamlit_image_coordinates
except Exception:
    streamlit_image_coordinates = None

from app.services.excel_exporter import export_records_to_excel
from app.services.format_matcher import match_format_with_score
from app.services.format_registry import DuplicateFormatError, FormatRegistry
from app.services.line_detector import detect_boxes
from app.services.ocr_extractor import OcrExtractionError, extract_text_by_ocr
from app.services.pdf_loader import PdfLoadError, detect_pdf_type, load_first_page_image
from app.services.text_extractor import TextExtractionError, extract_text_by_normalized_fields
from app.ui.mode_select import render_mode_select
from app.ui.recognize_text import section_title as recognize_title
from app.ui.register_format import section_title as register_title
from app.utils.image_utils import clamp_box, draw_boxes, from_normalized_box, to_normalized_box

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
FORMATS_JSON = DATA_DIR / "formats.json"


def init_state() -> None:
    st.session_state.setdefault("detected_boxes", [])
    st.session_state.setdefault("register_uploaded_name", "")
    st.session_state.setdefault("selected_indexes", [])
    st.session_state.setdefault("records", [])
    st.session_state.setdefault("editable_values", {})
    st.session_state.setdefault("edit_mode", False)
    st.session_state.setdefault("matcher_threshold", 0.18)
    st.session_state.setdefault("last_register_click", None)


def main() -> None:
    st.set_page_config(page_title="伝票転記アプリ", layout="wide")
    init_state()

    st.title("伝票自動転記アプリ (MVP)")
    st.caption("フォーマット登録と文字認識を切り替えて実行します。")

    mode = render_mode_select()

    if mode == "フォーマット登録機能":
        render_register_mode()
    else:
        render_recognition_mode()


def render_register_mode() -> None:
    register_title()
    registry = FormatRegistry(FORMATS_JSON)

    with st.expander("登録済みフォーマット管理", expanded=False):
        render_format_management_panel(registry)

    uploaded = st.file_uploader("空フォーマットPDFをアップロード", type=["pdf"], key="register_pdf")
    if not uploaded:
        return

    pdf_bytes = uploaded.getvalue()
    st.session_state["register_uploaded_name"] = uploaded.name

    try:
        image_bgr, page_size = load_first_page_image(pdf_bytes)
    except PdfLoadError as exc:
        st.error(f"PDF読み込み失敗: {exc}")
        return

    boxes = detect_boxes(image_bgr)
    if not boxes:
        st.error("枠線が検出できませんでした。")
        return

    st.session_state["detected_boxes"] = boxes

    highlighted = draw_boxes(image_bgr, boxes)
    left, right = st.columns([1.2, 1.0])

    with left:
        selected_indexes = st.session_state.get("selected_indexes", [])
        selected_boxes = [boxes[idx] for idx in selected_indexes if idx < len(boxes)]
        highlighted_with_selected = draw_boxes(highlighted, selected_boxes, color=(0, 0, 255))

        if streamlit_image_coordinates is not None:
            st.caption("枠を直接クリックすると選択/解除できます（赤枠が選択中）。")
            clicked = streamlit_image_coordinates(
                highlighted_with_selected[:, :, ::-1],
                key="register_clickable_image",
            )
            _handle_register_click(clicked, boxes)
        else:
            st.info("クリック選択を使うには `streamlit-image-coordinates` をインストールしてください。")
            st.image(highlighted_with_selected[:, :, ::-1], caption="検出枠")

    with right:
        st.write(f"検出枠数: {len(boxes)}")
        selected_indexes = st.multiselect(
            "抽出対象の枠インデックスを選択（クリック選択の補助）",
            options=list(range(len(boxes))),
            default=st.session_state.get("selected_indexes", []),
        )
        st.session_state["selected_indexes"] = selected_indexes

        selected_fields: list[dict] = []
        for idx in selected_indexes:
            tag = st.text_input(f"枠 #{idx} のタグ名", key=f"register_tag_{idx}").strip()
            if tag:
                selected_fields.append(
                    {
                        "tag": tag,
                        "box": boxes[idx],
                        "source_image_width": int(image_bgr.shape[1]),
                        "source_image_height": int(image_bgr.shape[0]),
                    }
                )

        format_name = st.text_input("フォーマット名", value=Path(uploaded.name).stem).strip()

        if st.button("フォーマット登録を保存", type="primary"):
            save_format(registry, format_name, page_size, selected_fields)


def save_format(registry: FormatRegistry, format_name: str, page_size: tuple[int, int], selected_fields: list[dict]) -> None:
    if not format_name:
        st.error("フォーマット名を入力してください。")
        return
    if not selected_fields:
        st.error("少なくとも1つのタグ付き枠を選択してください。")
        return

    tags = [f["tag"] for f in selected_fields]
    if len(tags) != len(set(tags)):
        st.error("タグ名が重複しています。")
        return

    try:
        created = registry.add_format(format_name, page_size, selected_fields)
        st.success(f"登録完了: {created['format_id']}")
    except DuplicateFormatError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"JSON保存失敗: {exc}")


def render_recognition_mode() -> None:
    recognize_title()
    registry = FormatRegistry(FORMATS_JSON)
    registered_formats = registry.list_formats()

    threshold = st.slider(
        "判別しきい値 (小さいほど厳密)",
        min_value=0.05,
        max_value=0.40,
        value=float(st.session_state.get("matcher_threshold", 0.18)),
        step=0.01,
    )
    st.session_state["matcher_threshold"] = threshold
    show_debug_boxes = st.checkbox("デバッグ: 抽出枠を画像に表示", value=True)
    show_detected_boxes = st.checkbox("デバッグ: 検出枠も表示", value=False)

    if not registered_formats:
        st.warning("登録済みフォーマットがありません。先にフォーマット登録機能で登録してください。")
        return

    uploaded = st.file_uploader("記入済みPDFをアップロード", type=["pdf"], key="recognition_pdf")
    if not uploaded:
        render_records_panel()
        return

    pdf_bytes = uploaded.getvalue()

    try:
        image_bgr, _ = load_first_page_image(pdf_bytes)
    except PdfLoadError as exc:
        st.error(f"PDF読み込み失敗: {exc}")
        return

    detected_boxes = detect_boxes(image_bgr)
    matched, best_score, candidates = match_format_with_score(
        registered_formats,
        detected_boxes,
        image_bgr.shape[1],
        image_bgr.shape[0],
        threshold=threshold,
    )

    chosen_format = matched
    if not chosen_format:
        st.error("登録済みフォーマットに一致しませんでした。")
        if candidates:
            st.write("候補スコア (小さいほど近い)")
            for cand, score, score_detail in candidates[:3]:
                st.write(f"- {cand['name']} ({cand['format_id']}): {score:.4f}")
                st.write(f"  　アンカー距離: {score_detail['anchor_distance']:.4f} (重み 45%)")
                st.write(f"  　レイアウト距離: {score_detail['layout_distance']:.4f} (重み 45%)")
                st.write(f"  　縦横比距離: {score_detail.get('aspect_distance', 0.0):.4f} (重み 10%)")

        use_manual = st.checkbox("手動でフォーマット指定して続行する")
        if use_manual:
            options = {
                f"{fmt['name']} ({fmt['format_id']})": fmt for fmt in registered_formats
            }
            selected_label = st.selectbox("使用フォーマット", list(options.keys()))
            chosen_format = options[selected_label]
            st.info("手動指定フォーマットで抽出を実行します。")
        else:
            render_records_panel()
            return
    else:
        st.caption(f"自動判定スコア: {best_score:.4f}")

    shift_x, shift_y = _compute_anchor_shift(chosen_format, detected_boxes, image_bgr.shape[1], image_bgr.shape[0])
    shifted_fields = _build_shifted_fields(chosen_format.get("fields", []), shift_x, shift_y, image_bgr.shape[1], image_bgr.shape[0])
    st.caption(f"アンカー補正: dx={shift_x}px, dy={shift_y}px")

    pdf_type = detect_pdf_type(pdf_bytes)

    try:
        if pdf_type == "text":
            values = extract_text_by_normalized_fields(pdf_bytes, shifted_fields)
        else:
            values = extract_text_by_ocr(image_bgr, shifted_fields)
    except TextExtractionError as exc:
        st.error(f"テキスト抽出失敗: {exc}")
        return
    except OcrExtractionError as exc:
        st.error(f"OCR失敗: {exc}")
        return

    left, right = st.columns([1.3, 1.0])
    with left:
        preview_image = image_bgr.copy()
        if show_detected_boxes:
            preview_image = draw_boxes(preview_image, detected_boxes, color=(255, 0, 0))

        if show_debug_boxes:
            target_boxes = _fields_to_image_boxes(shifted_fields, preview_image.shape[1], preview_image.shape[0])
            preview_image = draw_boxes(preview_image, target_boxes, color=(0, 0, 255))

        caption = f"PDFプレビュー ({pdf_type}-based)"
        if show_debug_boxes or show_detected_boxes:
            caption += " / 赤=抽出枠, 青=検出枠"
        st.image(preview_image[:, :, ::-1], caption=caption)
    with right:
        st.write(f"判定フォーマット: {chosen_format['name']} ({chosen_format['format_id']})")
        st.write("抽出結果")
        for key, val in values.items():
            st.write(f"- {key}: {val}")

    record = {
        "format_id": chosen_format["format_id"],
        "source_filename": uploaded.name,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "values": values,
    }

    if st.button("この抽出結果を追加", type="primary"):
        st.session_state["records"].append(record)
        st.success("結果を一時リストへ追加しました。")

    render_records_panel()


def render_records_panel() -> None:
    st.divider()
    st.subheader("抽出結果リスト")

    records = st.session_state["records"]
    if not records:
        st.info("まだ追加された抽出結果はありません。")
        return

    latest = records[-1]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("編集", key="edit_on"):
            st.session_state["edit_mode"] = True
            st.session_state["editable_values"] = latest["values"].copy()
    with col2:
        if st.button("編集保存", key="edit_save"):
            if st.session_state["edit_mode"]:
                latest["values"] = st.session_state["editable_values"].copy()
                st.session_state["edit_mode"] = False
                st.success("修正内容を保存しました。")

    st.write(f"現在の蓄積件数: {len(records)}")

    if st.session_state["edit_mode"]:
        st.write("最新レコードを編集中")
        editable = st.session_state["editable_values"]
        for key in list(editable.keys()):
            editable[key] = st.text_input(f"{key}", value=editable[key], key=f"edit_field_{key}")
    else:
        st.write("最新レコード")
        for key, val in latest["values"].items():
            st.write(f"- {key}: {val}")

    if st.button("新規Excelを作成して保存", key="export_excel"):
        try:
            path = export_records_to_excel(records, OUTPUT_DIR)
            st.success(f"Excelを出力しました: {path.name}")
            with path.open("rb") as f:
                st.download_button(
                    "Excelダウンロード",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as exc:
            st.error(f"Excel出力失敗: {exc}")


def render_format_management_panel(registry: FormatRegistry) -> None:
    formats = registry.list_formats()
    if not formats:
        st.info("登録済みフォーマットはありません。")
        return

    st.write(f"登録数: {len(formats)}")
    options = {f"{fmt['name']} ({fmt['format_id']})": fmt for fmt in formats}
    selected_label = st.selectbox("管理対象フォーマット", list(options.keys()), key="manage_format")
    selected = options[selected_label]

    st.write(
        f"フィールド数: {len(selected.get('fields', []))} / 作成日時: {selected.get('created_at', '-') }"
    )

    rename_col, delete_col = st.columns(2)
    with rename_col:
        new_name = st.text_input("新しいフォーマット名", value=selected.get("name", ""), key="rename_input").strip()
        if st.button("名称変更", key="rename_btn"):
            if not new_name:
                st.error("新しい名称を入力してください。")
            elif registry.rename_format(selected["format_id"], new_name):
                st.success("フォーマット名を更新しました。")
                st.rerun()
            else:
                st.error("フォーマット名の更新に失敗しました。")

    with delete_col:
        confirm = st.checkbox("削除を確認", key="confirm_delete")
        if st.button("削除", key="delete_btn"):
            if not confirm:
                st.error("削除を確認してください。")
            elif registry.delete_format(selected["format_id"]):
                st.success("フォーマットを削除しました。")
                st.rerun()
            else:
                st.error("フォーマット削除に失敗しました。")


def _handle_register_click(clicked: dict | None, boxes: list[dict]) -> None:
    if not clicked:
        return

    point = (clicked.get("x"), clicked.get("y"))
    if point == st.session_state.get("last_register_click"):
        return

    st.session_state["last_register_click"] = point
    x, y = point
    if x is None or y is None:
        return

    idx = _find_box_index_by_point(int(x), int(y), boxes)
    if idx is None:
        return

    selected_indexes = list(st.session_state.get("selected_indexes", []))
    if idx in selected_indexes:
        selected_indexes.remove(idx)
    else:
        selected_indexes.append(idx)

    selected_indexes.sort()
    st.session_state["selected_indexes"] = selected_indexes
    st.rerun()


def _find_box_index_by_point(x: int, y: int, boxes: list[dict]) -> int | None:
    hit_indexes = []
    for i, box in enumerate(boxes):
        if box["x"] <= x <= box["x"] + box["w"] and box["y"] <= y <= box["y"] + box["h"]:
            hit_indexes.append((i, box["w"] * box["h"]))

    if not hit_indexes:
        return None

    # Pick the smallest containing box to favor inner cells when boxes overlap.
    hit_indexes.sort(key=lambda item: item[1])
    return hit_indexes[0][0]


def _fields_to_image_boxes(fields: list[dict], image_width: int, image_height: int) -> list[dict]:
    boxes: list[dict] = []
    for field in fields:
        norm = field.get("box_norm")
        if norm:
            boxes.append(from_normalized_box(norm, image_width, image_height))
            continue

        raw = field.get("box")
        if raw:
            boxes.append(raw)
    return boxes


def _compute_anchor_shift(chosen_format: dict, detected_boxes: list[dict], image_width: int, image_height: int) -> tuple[int, int]:
    if not detected_boxes:
        return 0, 0
    anchor_norm = chosen_format.get("reference", {}).get("anchor_box_norm")

    if not anchor_norm:
        fields = chosen_format.get("fields", [])
        norm_fields = [f.get("box_norm") for f in fields if f.get("box_norm")]
        if not norm_fields:
            return 0, 0
        anchor_norm = min(norm_fields, key=lambda b: (b["y"], b["x"]))

    expected_anchor = from_normalized_box(anchor_norm, image_width, image_height)
    detected_anchor = _find_best_detected_anchor(expected_anchor, detected_boxes)
    dx = int(detected_anchor["x"] - expected_anchor["x"])
    dy = int(detected_anchor["y"] - expected_anchor["y"])

    # Prevent extreme correction when anchor detection is unstable.
    max_dx = int(image_width * 0.25)
    max_dy = int(image_height * 0.25)
    if abs(dx) > max_dx or abs(dy) > max_dy:
        return 0, 0

    return dx, dy


def _build_shifted_fields(fields: list[dict], dx: int, dy: int, image_width: int, image_height: int) -> list[dict]:
    shifted_fields: list[dict] = []
    for field in fields:
        box = None
        norm = field.get("box_norm")
        if norm:
            box = from_normalized_box(norm, image_width, image_height)
        elif field.get("box"):
            box = clamp_box(field["box"], image_width, image_height)

        if box is None:
            shifted_fields.append(field)
            continue

        shifted_box = clamp_box(
            {
                "x": box["x"] + dx,
                "y": box["y"] + dy,
                "w": box["w"],
                "h": box["h"],
            },
            image_width,
            image_height,
        )

        shifted_field = dict(field)
        shifted_field["box"] = shifted_box
        shifted_field["box_norm"] = to_normalized_box(shifted_box, image_width, image_height)
        shifted_fields.append(shifted_field)

    return shifted_fields


def _find_best_detected_anchor(expected_anchor: dict, detected_boxes: list[dict]) -> dict:
    ex_cx = expected_anchor["x"] + expected_anchor["w"] / 2
    ex_cy = expected_anchor["y"] + expected_anchor["h"] / 2

    def _score(box: dict) -> float:
        bx_cx = box["x"] + box["w"] / 2
        bx_cy = box["y"] + box["h"] / 2
        center_dist = ((bx_cx - ex_cx) ** 2 + (bx_cy - ex_cy) ** 2) ** 0.5
        size_penalty = 0.5 * (abs(box["w"] - expected_anchor["w"]) + abs(box["h"] - expected_anchor["h"]))
        return center_dist + size_penalty

    return min(detected_boxes, key=_score)


if __name__ == "__main__":
    main()
