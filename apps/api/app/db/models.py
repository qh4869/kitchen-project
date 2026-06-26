from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Supplier(Base):
    """线下菜场/超市等供应方。PRD §5.2。"""

    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    business_hours: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    contact_info: Mapped[str | None] = mapped_column(Text)
    preferences: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    purchases: Mapped[list["Purchase"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class Purchase(Base):
    """一次采购记录（一张小票 = 一条）。PRD §5.3。"""

    __tablename__ = "purchases"
    __table_args__ = (
        Index("idx_purchases_time", "purchase_time"),
        Index("idx_purchases_supplier", "supplier_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    purchase_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    receipt_image_path: Mapped[str | None] = mapped_column(Text)
    ocr_raw: Mapped[dict | None] = mapped_column(JSONB)
    ocr_provider: Mapped[str | None] = mapped_column(String(50))
    manual_adjustment: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    supplier: Mapped["Supplier | None"] = relationship(back_populates="purchases")
    items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan"
    )


class PurchaseItem(Base):
    """采购明细行。PRD §5.3 PurchaseItem。"""

    __tablename__ = "purchase_items"
    __table_args__ = (
        Index("idx_items_name", "name"),
        Index("idx_items_purchase", "purchase_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    purchase_id: Mapped[UUID] = mapped_column(
        ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    brand: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    purchase: Mapped["Purchase"] = relationship(back_populates="items")
