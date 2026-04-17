from __future__ import annotations


def match_format(
    registered_formats: list[dict],
    detected_boxes: list[dict],
    image_width: int,
    image_height: int,
    threshold: float = 0.18,
) -> dict | None:
    matched, _, _ = match_format_with_score(
        registered_formats=registered_formats,
        detected_boxes=detected_boxes,
        image_width=image_width,
        image_height=image_height,
        threshold=threshold,
    )
    return matched


def match_format_with_score(
    registered_formats: list[dict],
    detected_boxes: list[dict],
    image_width: int,
    image_height: int,
    threshold: float = 0.18,
) -> tuple[dict | None, float, list[tuple[dict, float, dict]]]:
    if not registered_formats:
        return None, float("inf"), []
    if not detected_boxes:
        return None, float("inf"), []

    detected_norm = [_to_norm(b, image_width, image_height) for b in detected_boxes]

    best_format = None
    best_score = float("inf")
    scored_candidates: list[tuple[dict, float, dict]] = []

    for fmt in registered_formats:
        fields = fmt.get("fields", [])
        if not fields:
            continue

        expected = [f.get("box_norm", {}) for f in fields]
        if not all(expected):
            continue

        expected_anchor = (
            fmt.get("reference", {}).get("anchor_box_norm")
            or _get_anchor_norm(expected)
        )
        anchor_distance = _anchor_distance_to_nearest(expected_anchor, detected_norm)
        layout_distance = _format_distance(expected, detected_norm)
        aspect_distance = _aspect_ratio_distance(fmt, image_width, image_height)

        # Use anchor + layout + page aspect to reduce false positives across formats.
        score = (anchor_distance * 0.45) + (layout_distance * 0.45) + (aspect_distance * 0.10)
        score_detail = {
            "anchor_distance": anchor_distance,
            "layout_distance": layout_distance,
            "aspect_distance": aspect_distance,
            "anchor_weight": 0.45,
            "layout_weight": 0.45,
            "aspect_weight": 0.10,
        }
        scored_candidates.append((fmt, score, score_detail))
        if score < best_score:
            best_score = score
            best_format = fmt

    scored_candidates.sort(key=lambda item: item[1])
    if best_score > threshold:
        return None, best_score, scored_candidates[:5]
    return best_format, best_score, scored_candidates[:5]


def _to_norm(box: dict, width: int, height: int) -> dict:
    return {
        "x": box["x"] / width,
        "y": box["y"] / height,
        "w": box["w"] / width,
        "h": box["h"] / height,
    }


def _format_distance(expected_fields: list[dict], detected_fields: list[dict]) -> float:
    if not detected_fields:
        return 1.0

    # Nearest-neighbor mean distance in normalized coordinate space.
    distances = []
    for expected in expected_fields:
        ex_cx = expected["x"] + expected["w"] / 2
        ex_cy = expected["y"] + expected["h"] / 2

        nearest = min(
            (
                ((d["x"] + d["w"] / 2 - ex_cx) ** 2 + (d["y"] + d["h"] / 2 - ex_cy) ** 2) ** 0.5
                + 0.5 * (abs(d["w"] - expected["w"]) + abs(d["h"] - expected["h"]))
                for d in detected_fields
            ),
            default=1.0,
        )
        distances.append(nearest)

    # Penalize large differences in field count both ways.
    count_gap_ratio = abs(len(expected_fields) - len(detected_fields)) / max(
        1,
        len(expected_fields),
        len(detected_fields),
    )
    coverage_penalty = count_gap_ratio * 0.08
    return (sum(distances) / max(1, len(distances))) + coverage_penalty


def _get_anchor_norm(fields: list[dict]) -> dict:
    anchor = min(fields, key=lambda b: (b.get("y", 1.0), b.get("x", 1.0)))
    return {
        "x": anchor["x"],
        "y": anchor["y"],
        "w": anchor.get("w", 0.0),
        "h": anchor.get("h", 0.0),
    }


def _anchor_distance(expected_anchor: dict, detected_anchor: dict) -> float:
    ex_cx = expected_anchor["x"] + expected_anchor.get("w", 0.0) / 2
    ex_cy = expected_anchor["y"] + expected_anchor.get("h", 0.0) / 2
    de_cx = detected_anchor["x"] + detected_anchor.get("w", 0.0) / 2
    de_cy = detected_anchor["y"] + detected_anchor.get("h", 0.0) / 2
    return ((de_cx - ex_cx) ** 2 + (de_cy - ex_cy) ** 2) ** 0.5


def _anchor_distance_to_nearest(expected_anchor: dict, detected_fields: list[dict]) -> float:
    if not detected_fields:
        return 1.0
    return min(_anchor_distance(expected_anchor, detected) for detected in detected_fields)


def _aspect_ratio_distance(fmt: dict, image_width: int, image_height: int) -> float:
    page_size = fmt.get("page_size", {})
    fmt_w = page_size.get("width")
    fmt_h = page_size.get("height")
    if not fmt_w or not fmt_h or not image_width or not image_height:
        return 0.0

    image_aspect = image_width / image_height
    format_aspect = fmt_w / fmt_h
    return min(1.0, abs(image_aspect - format_aspect))
