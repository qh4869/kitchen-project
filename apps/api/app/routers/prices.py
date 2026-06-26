"""GET /prices/search — search purchase_items by name substring (ILIKE).

Empty / whitespace-only query matches all items (returns latest N
regardless of name). Non-empty query does ILIKE substring matching
with wildcard escaping. Ordered by purchase_time DESC, limit default 50.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Purchase, PurchaseItem, Supplier
from app.deps import get_db
from app.schemas.price import SearchResult, SearchResultItem

router = APIRouter(prefix="/prices", tags=["prices"])

MAX_QUERY_LENGTH = 100


@router.get("/search", response_model=SearchResult)
async def search_prices(
    q: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> SearchResult:
    q_stripped = q.strip()
    if len(q_stripped) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"INVALID_QUERY: query must be at most 100 chars (got {len(q_stripped)})",
        )

    stmt = (
        select(
            PurchaseItem.name,
            PurchaseItem.quantity,
            PurchaseItem.unit,
            PurchaseItem.unit_price,
            PurchaseItem.category,
            PurchaseItem.brand,
            PurchaseItem.id.label("purchase_item_id"),
            Purchase.id.label("purchase_id"),
            Purchase.purchase_time,
            Purchase.receipt_image_path,
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
        )
        .join(Purchase, PurchaseItem.purchase_id == Purchase.id)
        .outerjoin(Supplier, Purchase.supplier_id == Supplier.id)
        .order_by(Purchase.purchase_time.desc())
        .limit(limit)
    )

    # Apply ILIKE filter only when query is non-empty
    if q_stripped:
        escaped = (
            q_stripped.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        stmt = stmt.where(PurchaseItem.name.ilike(pattern, escape="\\"))

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        SearchResultItem(
            name=row.name,
            quantity=row.quantity,
            unit=row.unit,
            unit_price=row.unit_price,
            category=row.category,
            brand=row.brand,
            supplier_id=row.supplier_id,
            supplier_name=row.supplier_name,
            purchase_id=row.purchase_id,
            purchase_item_id=row.purchase_item_id,
            purchase_time=row.purchase_time,
            receipt_image_path=row.receipt_image_path,
        )
        for row in rows
    ]
    return SearchResult(query=q_stripped, count=len(items), items=items)
