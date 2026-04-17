from __future__ import annotations

from io import BytesIO

import fitz
import numpy as np
import pdfplumber


class PdfLoadError(Exception):
    pass


def load_first_page_image(pdf_bytes: bytes, zoom: float = 2.0) -> tuple[np.ndarray, tuple[int, int]]:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc.load_page(0)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        # RGB -> BGR for OpenCV
        img = img[:, :, ::-1].copy()
        width, height = page.rect.width, page.rect.height
        doc.close()
        return img, (int(width), int(height))
    except Exception as exc:
        raise PdfLoadError(f"Failed to render PDF page: {exc}") from exc


def detect_pdf_type(pdf_bytes: bytes, min_chars: int = 10) -> str:
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            page = pdf.pages[0]
            chars = page.chars or []
            if len(chars) >= min_chars:
                return "text"
            text = page.extract_text() or ""
            return "text" if len(text.strip()) >= min_chars else "image"
    except Exception:
        return "image"
