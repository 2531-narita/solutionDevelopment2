from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class Box(BaseModel):
    x: float
    y: float
    w: float
    h: float


class FieldDefinition(BaseModel):
    tag: str = Field(min_length=1)
    box: Box
    box_norm: Box


class FormatReference(BaseModel):
    anchor_box: Box
    anchor_box_norm: Box


class FormatDefinition(BaseModel):
    format_id: str
    name: str
    page_size: dict
    reference: FormatReference
    fields: List[FieldDefinition]
    created_at: str


class FormatCollection(BaseModel):
    formats: List[FormatDefinition] = []


class ExtractedRecord(BaseModel):
    format_id: str
    source_filename: str
    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    values: dict
