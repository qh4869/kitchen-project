"""DELETE /purchase-items/{item_id} — delete a single purchase_item.

If the parent purchase ends up with zero items, cascade-delete the
purchase too (avoids orphan purchase rows).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Purchase, PurchaseItem
from app.deps import get_db

router = APIRouter(prefix="/purchase-items", tags=["purchase-items"])


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    item = await db.get(PurchaseItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="PURCHASE_ITEM_NOT_FOUND")

    purchase_id = item.purchase_id

    await db.delete(item)
    await db.commit()

    # Cascade: if the parent purchase now has zero items, delete it too
    remaining = await db.scalar(
        select(func.count(PurchaseItem.id)).where(
            PurchaseItem.purchase_id == purchase_id
        )
    )
    if remaining == 0:
        purchase = await db.get(Purchase, purchase_id)
        if purchase is not None:
            await db.delete(purchase)
            await db.commit()
