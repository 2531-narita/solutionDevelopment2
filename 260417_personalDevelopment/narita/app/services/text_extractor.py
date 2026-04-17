from __future__ import annotations

from io import BytesIO

import pdfplumber


class TextExtractionError(Exception):
    pass


def extract_text_by_normalized_fields(pdf_bytes: bytes, fields: list[dict]) -> dict[str, str]:
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            page = pdf.pages[0]
            pw, ph = page.width, page.height
            results: dict[str, str] = {}

            for field in fields:
                tag = field["tag"]
                b = field.get("box_norm") or {}
                if not b:
                    results[tag] = ""
                    continue

                x0 = b["x"] * pw
                top = b["y"] * ph
                x1 = (b["x"] + b["w"]) * pw
                bottom = (b["y"] + b["h"]) * ph

                cropped = page.crop((x0, top, x1, bottom))
                text = (cropped.extract_text() or "").strip()
                results[tag] = text

            return results
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract text from text-based PDF: {exc}") from exc
