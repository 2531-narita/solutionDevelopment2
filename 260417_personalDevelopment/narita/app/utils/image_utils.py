from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np


def clamp_box(box: dict, width: int, height: int) -> dict:
    x = max(0, min(int(box["x"]), width - 1))
    y = max(0, min(int(box["y"]), height - 1))
    w = max(1, min(int(box["w"]), width - x))
    h = max(1, min(int(box["h"]), height - y))
    return {"x": x, "y": y, "w": w, "h": h}


def to_normalized_box(box: dict, width: int, height: int) -> dict:
    return {
        "x": box["x"] / width,
        "y": box["y"] / height,
        "w": box["w"] / width,
        "h": box["h"] / height,
    }


def from_normalized_box(box: dict, width: int, height: int) -> dict:
    raw = {
        "x": round(box["x"] * width),
        "y": round(box["y"] * height),
        "w": round(box["w"] * width),
        "h": round(box["h"] * height),
    }
    return clamp_box(raw, width, height)


def draw_boxes(image: np.ndarray, boxes: Iterable[dict], color: tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
    out = image.copy()
    for box in boxes:
        cv2.rectangle(
            out,
            (int(box["x"]), int(box["y"])),
            (int(box["x"] + box["w"]), int(box["y"] + box["h"])),
            color,
            2,
        )
    return out
