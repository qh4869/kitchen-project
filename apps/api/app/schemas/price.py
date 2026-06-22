"""Response schemas for /api/v1/prices/* endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchResultItem(BaseModel):
    """One row in a price-search result table."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    category: str | None
    brand: str | None
    supplier_id: UUID | None
    supplier_name: str | None
    purchase_id: UUID
    purchase_time: datetime


class SearchResult(BaseModel):
    """Wrapper for /prices/search response."""

    query: str
    count: int
    items: list[SearchResultItem]
