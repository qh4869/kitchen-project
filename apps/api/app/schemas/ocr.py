from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OcrItem(BaseModel):
    """Single item extracted by OCR. All fields except name can be null."""

    name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=20)
    unit_price: Decimal | None = Field(None, ge=0)
    category: str | None = Field(None, max_length=50)
    brand: str | None = Field(None, max_length=100)


class OcrResult(BaseModel):
    """What /ocr/extract returns. items may be empty (that's 'OCR failure')."""

    image_key: str
    supplier_name: str | None = None
    purchase_time: datetime | None = None
    total_amount: Decimal | None = None
    items: list[OcrItem] = Field(default_factory=list)
    raw_llm_output: dict[str, Any] = Field(default_factory=dict)
    provider: str


class OcrExtractRequest(BaseModel):
    image_key: str = Field(..., min_length=1)


class PurchaseFromOcrItem(OcrItem):
    """In from-ocr, both name and unit_price are required (Pydantic enforces)."""

    name: str = Field(..., min_length=1, max_length=200)
    unit_price: Decimal = Field(..., ge=0)


class PurchaseFromOcrRequest(BaseModel):
    image_key: str
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    total_amount: Decimal | None = Field(None, ge=0)
    notes: str | None = None
    ocr_raw: dict[str, Any] | None = None
    manual_adjustment: bool = False
    items: list[PurchaseFromOcrItem] = Field(..., min_length=1)


class UploadResponse(BaseModel):
    image_key: str
    size: int
    content_type: str
