from __future__ import annotations

import cv2
import pytesseract

from app.utils.image_utils import from_normalized_box


class OcrExtractionError(Exception):
    pass


def extract_text_by_ocr(image_bgr, fields: list[dict], lang: str = "jpn+eng") -> dict[str, str]:
    h, w = image_bgr.shape[:2]
    results: dict[str, str] = {}

    try:
        for field in fields:
            tag = field["tag"]
            norm_box = field.get("box_norm") or {}
            if not norm_box:
                results[tag] = ""
                continue

            box = from_normalized_box(norm_box, w, h)
            roi = image_bgr[box["y"] : box["y"] + box["h"], box["x"] : box["x"] + box["w"]]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            txt = pytesseract.image_to_string(th, lang=lang, config="--oem 3 --psm 6")
            results[tag] = txt.strip()
        return results
    except Exception as exc:
        raise OcrExtractionError(f"Failed to run OCR extraction: {exc}") from exc
