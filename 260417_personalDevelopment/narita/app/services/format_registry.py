from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.utils.image_utils import to_normalized_box
from app.utils.json_store import ensure_json_file, read_json, write_json


class DuplicateFormatError(Exception):
    pass


class FormatRegistry:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        ensure_json_file(self.json_path, {"formats": []})

    def list_formats(self) -> list[dict]:
        return read_json(self.json_path).get("formats", [])

    def get_format(self, format_id: str) -> dict | None:
        for fmt in self.list_formats():
            if fmt.get("format_id") == format_id:
                return fmt
        return None

    def add_format(self, name: str, page_size: tuple[int, int], selected_fields: list[dict]) -> dict:
        data = read_json(self.json_path)
        formats = data.get("formats", [])

        if self._is_duplicate(formats, page_size, selected_fields):
            raise DuplicateFormatError("類似フォーマットが既に登録されています。")

        img_w = max(f["source_image_width"] for f in selected_fields)
        img_h = max(f["source_image_height"] for f in selected_fields)

        anchor = min((f["box"] for f in selected_fields), key=lambda b: (b["y"], b["x"]))

        new_format = {
            "format_id": f"fmt_{uuid4().hex[:10]}",
            "name": name,
            "page_size": {"width": page_size[0], "height": page_size[1]},
            "reference": {
                "anchor_box": anchor,
                "anchor_box_norm": to_normalized_box(anchor, img_w, img_h),
            },
            "fields": [
                {
                    "tag": f["tag"],
                    "box": f["box"],
                    "box_norm": to_normalized_box(f["box"], img_w, img_h),
                }
                for f in selected_fields
            ],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        formats.append(new_format)
        data["formats"] = formats
        write_json(self.json_path, data)
        return new_format

    def rename_format(self, format_id: str, new_name: str) -> bool:
        data = read_json(self.json_path)
        formats = data.get("formats", [])
        updated = False

        for fmt in formats:
            if fmt.get("format_id") == format_id:
                fmt["name"] = new_name
                updated = True
                break

        if updated:
            write_json(self.json_path, data)
        return updated

    def delete_format(self, format_id: str) -> bool:
        data = read_json(self.json_path)
        formats = data.get("formats", [])
        filtered = [fmt for fmt in formats if fmt.get("format_id") != format_id]

        if len(filtered) == len(formats):
            return False

        data["formats"] = filtered
        write_json(self.json_path, data)
        return True

    def _is_duplicate(self, formats: list[dict], page_size: tuple[int, int], selected_fields: list[dict]) -> bool:
        if not selected_fields:
            return False

        candidate_count = len(selected_fields)
        candidate_anchor = min((f["box"] for f in selected_fields), key=lambda b: (b["y"], b["x"]))
        img_w = max(f["source_image_width"] for f in selected_fields)
        img_h = max(f["source_image_height"] for f in selected_fields)
        candidate_norm = [to_normalized_box(f["box"], img_w, img_h) for f in selected_fields]

        page_ratio = page_size[0] / max(1, page_size[1])

        for fmt in formats:
            size = fmt.get("page_size", {})
            fmt_ratio = size.get("width", 1) / max(1, size.get("height", 1))
            if abs(fmt_ratio - page_ratio) > 0.08:
                continue

            fmt_fields = fmt.get("fields", [])
            if abs(len(fmt_fields) - candidate_count) > 2:
                continue

            anchor = fmt.get("reference", {}).get("anchor_box", {"x": 0, "y": 0})
            dx = abs(anchor.get("x", 0) - candidate_anchor["x"])
            dy = abs(anchor.get("y", 0) - candidate_anchor["y"])
            layout_close = self._layout_distance(
                [f.get("box_norm", {}) for f in fmt_fields if f.get("box_norm")],
                candidate_norm,
            ) <= 0.055

            if (dx <= 40 and dy <= 40) or layout_close:
                return True

        return False

    def _layout_distance(self, expected_fields: list[dict], candidate_fields: list[dict]) -> float:
        if not expected_fields or not candidate_fields:
            return 1.0

        distances = []
        for expected in expected_fields:
            ex_cx = expected["x"] + expected["w"] / 2
            ex_cy = expected["y"] + expected["h"] / 2

            nearest = min(
                (
                    ((c["x"] + c["w"] / 2 - ex_cx) ** 2 + (c["y"] + c["h"] / 2 - ex_cy) ** 2) ** 0.5
                    + 0.5 * (abs(c["w"] - expected["w"]) + abs(c["h"] - expected["h"]))
                    for c in candidate_fields
                ),
                default=1.0,
            )
            distances.append(nearest)

        coverage_penalty = max(0, len(expected_fields) - len(candidate_fields)) * 0.02
        return (sum(distances) / max(1, len(distances))) + coverage_penalty
