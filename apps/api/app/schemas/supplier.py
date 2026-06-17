from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    business_hours: list[str] | None = None
    contact_info: str | None = None
    preferences: list[str] | None = None
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    business_hours: list[str] | None = None
    contact_info: str | None = None
    preferences: list[str] | None = None
    notes: str | None = None


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
