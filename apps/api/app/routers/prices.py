"""GET /prices/search — search purchase_items by name substring (ILIKE).

Returns recent matches joined with their purchase + supplier, ordered by
purchase_time DESC. Up to 50 rows by default.
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
    q: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> SearchResult:
    q_stripped = q.strip()
    if not q_stripped:
        raise HTTPException(
            status_code=422,
            detail="INVALID_QUERY: query must be 1-100 chars after strip",
        )
    if len(q_stripped) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"INVALID_QUERY: query must be 1-100 chars (got {len(q_stripped)})",
        )

    # Escape ILIKE wildcards so user input is treated literally
    escaped = (
        q_stripped.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    pattern = f"%{escaped}%"

    stmt = (
        select(
            PurchaseItem.name,
            PurchaseItem.quantity,
            PurchaseItem.unit,
            PurchaseItem.unit_price,
            PurchaseItem.category,
            PurchaseItem.brand,
            Purchase.id.label("purchase_id"),
            Purchase.purchase_time,
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
        )
        .join(Purchase, PurchaseItem.purchase_id == Purchase.id)
        .outerjoin(Supplier, Purchase.supplier_id == Supplier.id)
        .where(PurchaseItem.name.ilike(pattern, escape="\\"))
        .order_by(Purchase.purchase_time.desc())
        .limit(limit)
    )
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
            purchase_time=row.purchase_time,
        )
        for row in rows
    ]
    return SearchResult(query=q_stripped, count=len(items), items=items)
