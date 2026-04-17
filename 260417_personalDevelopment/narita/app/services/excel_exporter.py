from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


def export_records_to_excel(records: list[dict], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_tags: list[str] = []
    for rec in records:
        for key in rec.get("values", {}).keys():
            if key not in all_tags:
                all_tags.append(key)

    wb = Workbook()
    ws = wb.active
    ws.title = "ExtractedData"

    header = ["source_filename", "format_id", "extracted_at", *all_tags]
    ws.append(header)

    for rec in records:
        row = [
            rec.get("source_filename", ""),
            rec.get("format_id", ""),
            rec.get("extracted_at", ""),
        ]
        values = rec.get("values", {})
        row.extend(values.get(tag, "") for tag in all_tags)
        ws.append(row)

    filename = f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = output_dir / filename
    wb.save(path)
    return path
