from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Supplier
from app.deps import get_db
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(
    q: str | None = Query(None, description="模糊搜索名称/地址/备注"),
    db: AsyncSession = Depends(get_db),
) -> list[Supplier]:
    stmt = select(Supplier).order_by(Supplier.created_at.desc())
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Supplier.name.ilike(pattern)
            | Supplier.address.ilike(pattern)
            | Supplier.notes.ilike(pattern)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate, db: AsyncSession = Depends(get_db)
) -> Supplier:
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: UUID, db: AsyncSession = Depends(get_db)
) -> Supplier:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
) -> Supplier:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await db.delete(supplier)
    await db.commit()
