from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Purchase, PurchaseItem
from app.deps import get_db, get_storage
from app.config import settings
from app.schemas.ocr import PurchaseFromOcrRequest
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseListItem,
    PurchaseOut,
    PurchaseUpdate,
)
from app.services.storage.adapter import FileStorage

router = APIRouter(prefix="/purchases", tags=["purchases"])


def _item_count_subquery():
    return (
        select(func.count(PurchaseItem.id))
        .where(PurchaseItem.purchase_id == Purchase.id)
        .correlate(Purchase)
        .scalar_subquery()
    )


@router.get("", response_model=list[PurchaseListItem])
async def list_purchases(
    supplier_id: UUID | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(Purchase, _item_count_subquery().label("item_count"))
        .order_by(Purchase.purchase_time.desc())
    )
    if supplier_id is not None:
        stmt = stmt.where(Purchase.supplier_id == supplier_id)
    if from_ is not None:
        stmt = stmt.where(Purchase.purchase_time >= from_)
    if to is not None:
        stmt = stmt.where(Purchase.purchase_time <= to)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": p.id,
            "supplier_id": p.supplier_id,
            "total_amount": p.total_amount,
            "purchase_time": p.purchase_time,
            "manual_adjustment": p.manual_adjustment,
            "item_count": count,
            "created_at": p.created_at,
        }
        for p, count in rows
    ]


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate, db: AsyncSession = Depends(get_db)
) -> Purchase:
    purchase = Purchase(
        supplier_id=payload.supplier_id,
        total_amount=payload.total_amount,
        purchase_time=payload.purchase_time,
        notes=payload.notes,
        items=[
            PurchaseItem(**item.model_dump()) for item in payload.items
        ],
    )
    db.add(purchase)
    await db.commit()
    # Reload with items to populate response
    refreshed = await db.get(
        Purchase, purchase.id, options=[selectinload(Purchase.items)]
    )
    assert refreshed is not None
    return refreshed


@router.post("/from-ocr", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_from_ocr(
    payload: PurchaseFromOcrRequest,
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_storage),
) -> Purchase:
    # Verify image exists
    try:
        await storage.read(payload.image_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="IMAGE_NOT_FOUND") from None

    purchase = Purchase(
        supplier_id=payload.supplier_id,
        total_amount=payload.total_amount,
        purchase_time=payload.purchase_time,
        notes=payload.notes,
        receipt_image_path=payload.image_key,
        ocr_raw=payload.ocr_raw,
        ocr_provider=settings.ocr_provider,
        manual_adjustment=payload.manual_adjustment,
        items=[PurchaseItem(**item.model_dump()) for item in payload.items],
    )
    db.add(purchase)
    await db.commit()
    refreshed = await db.get(
        Purchase, purchase.id, options=[selectinload(Purchase.items)]
    )
    assert refreshed is not None
    return refreshed


@router.get("/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(
    purchase_id: UUID, db: AsyncSession = Depends(get_db)
) -> Purchase:
    purchase = await db.get(
        Purchase, purchase_id, options=[selectinload(Purchase.items)]
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseOut)
async def update_purchase(
    purchase_id: UUID,
    payload: PurchaseUpdate,
    db: AsyncSession = Depends(get_db),
) -> Purchase:
    purchase = await db.get(
        Purchase, purchase_id, options=[selectinload(Purchase.items)]
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(purchase, field, value)
    await db.commit()
    await db.refresh(purchase)
    return purchase


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    purchase_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    purchase = await db.get(Purchase, purchase_id)
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    await db.delete(purchase)
    await db.commit()
