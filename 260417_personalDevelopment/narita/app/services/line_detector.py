from __future__ import annotations

import cv2
import numpy as np


def detect_boxes(image_bgr: np.ndarray, min_area: int = 500, max_boxes: int = 250) -> list[dict]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5,
    )

    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    lines_h = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h)
    lines_v = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)
    merged = cv2.add(lines_h, lines_v)

    contours, _ = cv2.findContours(merged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[dict] = []
    h, w = gray.shape
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < min_area:
            continue
        if bw >= w - 5 or bh >= h - 5:
            continue
        ratio = bw / max(1, bh)
        if ratio < 0.2 or ratio > 25:
            continue
        boxes.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh)})

    boxes = _deduplicate_boxes(boxes)
    boxes.sort(key=lambda b: (b["y"], b["x"]))
    return boxes[:max_boxes]


def _deduplicate_boxes(boxes: list[dict], iou_threshold: float = 0.9) -> list[dict]:
    filtered: list[dict] = []
    for box in boxes:
        if not any(_iou(box, keep) > iou_threshold for keep in filtered):
            filtered.append(box)
    return filtered


def _iou(a: dict, b: dict) -> float:
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0

    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / max(1, union)
