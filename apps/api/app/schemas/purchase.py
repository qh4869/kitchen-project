from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal = Field(..., ge=0)
    unit: str | None = Field(None, max_length=20)
    unit_price: Decimal = Field(..., ge=0)
    category: str | None = Field(None, max_length=50)
    brand: str | None = Field(None, max_length=100)


class PurchaseItemCreate(PurchaseItemBase):
    pass


class PurchaseItemOut(PurchaseItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_id: UUID


class PurchaseBase(BaseModel):
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    notes: str | None = None


class PurchaseCreate(PurchaseBase):
    items: list[PurchaseItemCreate] = Field(default_factory=list, min_length=0)


class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    notes: str | None = None
    manual_adjustment: bool | None = None
    items: list[PurchaseItemCreate] | None = None


class PurchaseOut(PurchaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_time: datetime
    receipt_image_path: str | None
    ocr_provider: str | None
    manual_adjustment: bool
    created_at: datetime
    items: list[PurchaseItemOut] = Field(default_factory=list)


class PurchaseListItem(BaseModel):
    """Lighter view for list pages — omits items to keep responses small."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID | None
    purchase_time: datetime
    manual_adjustment: bool
    item_count: int
    created_at: datetime
