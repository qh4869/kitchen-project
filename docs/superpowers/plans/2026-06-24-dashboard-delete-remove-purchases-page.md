# Dashboard Delete + Remove Purchases Page + Drop total_amount Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-item delete on the price-search dashboard, remove the redundant Purchases page (promoting dashboard to `/`), and drop the vestigial `total_amount` column from the data model.

**Architecture:** New `DELETE /api/v1/purchase-items/{id}` endpoint (with cascade-delete of empty purchases). Frontend dashboard gains a 5th column with ✕ buttons. `total_amount` removed from `Purchase` model + all schemas + OCR prompt + frontend inputs, plus an Alembic migration to drop the DB column.

**Tech Stack:** Python 3.13 + FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic v2 + pytest; React 18 + TanStack Query + Tailwind.

**Reference spec:** `docs/superpowers/specs/2026-06-24-dashboard-delete-remove-purchases-page-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/api/app/db/models.py` | Modify | Remove `total_amount` column from `Purchase` |
| `apps/api/app/schemas/purchase.py` | Modify | Remove `total_amount` from `PurchaseBase`, `PurchaseUpdate`, `PurchaseListItem` |
| `apps/api/app/schemas/ocr.py` | Modify | Remove `total_amount` from `OcrResult`, `PurchaseFromOcrRequest` |
| `apps/api/app/schemas/price.py` | Modify | Add `purchase_item_id` to `SearchResultItem` |
| `apps/api/app/services/ocr/prompt.py` | Modify | Remove `total_amount` from SYSTEM_PROMPT |
| `apps/api/app/services/ocr/parser.py` | Modify | Stop copying `total_amount` |
| `apps/api/app/services/ocr/mock.py` | Modify | Drop `total_amount=None` from `_DEFAULT_RESULT` |
| `apps/api/app/routers/purchases.py` | Modify | Stop setting `total_amount` in create + from-ocr |
| `apps/api/app/routers/prices.py` | Modify | Add `PurchaseItem.id.label("purchase_item_id")` to SELECT |
| `apps/api/app/routers/purchase_items.py` | **Create** | New `DELETE /{item_id}` endpoint with cascade logic |
| `apps/api/app/main.py` | Modify | Register `purchase_items` router |
| `apps/api/alembic/versions/<new>_drop_total_amount.py` | **Create** | Auto-generated drop column migration |
| `apps/api/tests/test_purchase_items.py` | **Create** | 3 tests: delete item, cascade empty purchase, 404 |
| `apps/api/tests/test_purchases.py` | Modify | Remove `total_amount` from payloads + assertions |
| `apps/api/tests/test_purchases_from_ocr.py` | Modify | Remove `total_amount` from payloads |
| `apps/api/tests/test_ocr_parser.py` | Modify | Drop `total_amount` assertion |
| `apps/api/tests/test_ocr_mock.py` | Modify (likely no-op) | Verify pydantic ignores extra fields |
| `apps/api/tests/test_prices_search.py` | Modify | Helpers unaffected; add `purchase_item_id` to assertions in 2-3 tests |
| `apps/web/src/App.tsx` | Modify | Remove `PurchasesPage` import + route; move `/dashboard` → `/`; update navItems |
| `apps/web/src/pages/PurchasesPage.tsx` | **Delete** | No longer needed |
| `apps/web/src/pages/DashboardPage.tsx` | Modify | Add `purchase_item_id` to type, delete mutation + 5th column with ✕ button |
| `apps/web/src/pages/EntryPage.tsx` | Modify | Remove `manualTotalAmount` + `photoTotalAmount` state / inputs / body fields |
| `apps/web/src/api/client.ts` | Modify (if needed) | Add `api.delete` helper if not present |

---

## Tasks

### Task 1: Drop total_amount from backend (model + schemas + OCR + tests + migration)

**Files:**
- Modify: `apps/api/app/db/models.py`
- Modify: `apps/api/app/schemas/purchase.py`
- Modify: `apps/api/app/schemas/ocr.py`
- Modify: `apps/api/app/services/ocr/prompt.py`
- Modify: `apps/api/app/services/ocr/parser.py`
- Modify: `apps/api/app/services/ocr/mock.py`
- Modify: `apps/api/app/routers/purchases.py`
- Modify: `apps/api/tests/test_purchases.py`
- Modify: `apps/api/tests/test_purchases_from_ocr.py`
- Modify: `apps/api/tests/test_ocr_parser.py`
- Create: `apps/api/alembic/versions/<new>_drop_total_amount.py` (via autogenerate)

- [ ] **Step 1: Remove `total_amount` from Purchase model**

Open `apps/api/app/db/models.py`. Find the `Purchase` class. Remove the line:

```python
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
```

- [ ] **Step 2: Remove `total_amount` from purchase schemas**

Open `apps/api/app/schemas/purchase.py`. Make these changes:

In `PurchaseBase`:
```python
class PurchaseBase(BaseModel):
    supplier_id: UUID | None = None
    total_amount: Decimal | None = Field(None, ge=0)  # ← remove this line
    purchase_time: datetime | None = None
    notes: str | None = None
```

In `PurchaseUpdate`:
```python
class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    total_amount: Decimal | None = Field(None, ge=0)  # ← remove this line
    purchase_time: datetime | None = None
    notes: str | None = None
    manual_adjustment: bool | None = None
```

In `PurchaseListItem`:
```python
class PurchaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID | None
    total_amount: Decimal | None  # ← remove this line
    purchase_time: datetime
    manual_adjustment: bool
    item_count: int
    created_at: datetime
```

Also remove the now-unused `Decimal` import if it's no longer used anywhere in this file. Check: `PurchaseItemBase.quantity: Decimal` and `unit_price: Decimal` still use it. Keep the import.

- [ ] **Step 3: Remove `total_amount` from OCR schemas**

Open `apps/api/app/schemas/ocr.py`. Make these changes:

In `OcrResult`:
```python
class OcrResult(BaseModel):
    image_key: str
    supplier_name: str | None = None
    purchase_time: datetime | None = None
    total_amount: Decimal | None = None  # ← remove this line
    items: list[OcrItem] = Field(default_factory=list)
    raw_llm_output: dict[str, Any] = Field(default_factory=dict)
    provider: str
```

In `PurchaseFromOcrRequest`:
```python
class PurchaseFromOcrRequest(BaseModel):
    image_key: str
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    total_amount: Decimal | None = Field(None, ge=0)  # ← remove this line
    notes: str | None = None
    ocr_raw: dict[str, Any] | None = None
    manual_adjustment: bool = False
    items: list[PurchaseFromOcrItem] = Field(..., min_length=1)
```

- [ ] **Step 4: Remove `total_amount` from OCR prompt**

Open `apps/api/app/services/ocr/prompt.py`. Edit `SYSTEM_PROMPT`:

Find this section in the prompt:
```
输出 schema（必须严格匹配，不能添加任何额外字段）：
{
  "supplier_name": string | null,        // 店铺名（看不清就 null）
  "purchase_time": string | null,        // ISO 8601，看不清就 null
  "total_amount": number | null,         // 总金额（人民币）
  "items": [
```

Replace with:
```
输出 schema（必须严格匹配，不能添加任何额外字段）：
{
  "supplier_name": string | null,        // 店铺名（看不清就 null）
  "purchase_time": string | null,        // ISO 8601，看不清就 null
  "items": [
```

Find this line in the硬性规则 section:
```
5. 若图片不是小票 / 价签（比如风景照），返 {"items": [], "supplier_name": null, "purchase_time": null, "total_amount": null}
```

Replace with:
```
5. 若图片不是小票 / 价签（比如风景照），返 {"items": [], "supplier_name": null, "purchase_time": null}
```

Also update test_ocr_prompt.py assertion if it checks for `total_amount` in SYSTEM_PROMPT (it currently checks `supplier_name` / `purchase_time` / `items` only — should be fine, but verify).

- [ ] **Step 5: Remove `total_amount` from parser**

Open `apps/api/app/services/ocr/parser.py`. In `parse_llm_json`:

Find:
```python
    return OcrResult(
        image_key=image_key,
        supplier_name=obj.get("supplier_name"),
        purchase_time=obj.get("purchase_time"),
        total_amount=obj.get("total_amount"),
        items=obj.get("items") or [],
        raw_llm_output=obj,
        provider=provider,
    )
```

Replace with:
```python
    return OcrResult(
        image_key=image_key,
        supplier_name=obj.get("supplier_name"),
        purchase_time=obj.get("purchase_time"),
        items=obj.get("items") or [],
        raw_llm_output=obj,
        provider=provider,
    )
```

- [ ] **Step 6: Remove `total_amount` from mock adapter**

Open `apps/api/app/services/ocr/mock.py`. In `_DEFAULT_RESULT`:

Find:
```python
_DEFAULT_RESULT = OcrResult(
    image_key="mock",
    supplier_name="mock 菜场",
    total_amount=None,
    items=[
        ...
    ],
    raw_llm_output={"mock": True, "note": "default fixture"},
    provider="mock",
)
```

Remove the `total_amount=None,` line. (`OcrResult` no longer has that field, so leaving it would crash.)

- [ ] **Step 7: Remove `total_amount` from purchases router**

Open `apps/api/app/routers/purchases.py`.

In `create_purchase` (around line 67-75):
Find:
```python
    purchase = Purchase(
        supplier_id=payload.supplier_id,
        total_amount=payload.total_amount,
        purchase_time=payload.purchase_time,
        ...
    )
```

Remove the `total_amount=payload.total_amount,` line.

In `create_purchase_from_ocr` (near the bottom of the file):
Find:
```python
    purchase = Purchase(
        supplier_id=payload.supplier_id,
        total_amount=payload.total_amount,
        purchase_time=payload.purchase_time,
        ...
    )
```

Remove the `total_amount=payload.total_amount,` line.

Also in `list_purchases` (the GET handler), find the dict construction:
```python
    return [
        {
            "id": p.id,
            "supplier_id": p.supplier_id,
            "total_amount": p.total_amount,
            "purchase_time": p.purchase_time,
            ...
        }
        for p, count in rows
    ]
```

Remove the `"total_amount": p.total_amount,` line.

- [ ] **Step 8: Update existing tests to drop total_amount**

Open `apps/api/tests/test_purchases.py`. Find every `total_amount` reference and remove:

In any test POST body (e.g. `test_create_and_get_with_items`), remove lines like:
```python
"total_amount": "19.50",
```

In any response assertion, remove:
```python
assert body["total_amount"] == "19.50"
```

Open `apps/api/tests/test_purchases_from_ocr.py`. In the 3 test payloads, remove `"total_amount": "..."` lines.

Open `apps/api/tests/test_ocr_parser.py`. In `test_parse_copies_top_level_fields`:

Find:
```python
def test_parse_copies_top_level_fields():
    content = '{"supplier_name": "城南菜场", "total_amount": 19.5, "items": [{"name": "番茄", "unit_price": 6.5}]}'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.supplier_name == "城南菜场"
    assert result.total_amount == 19.5
```

Replace with:
```python
def test_parse_copies_top_level_fields():
    content = '{"supplier_name": "城南菜场", "items": [{"name": "番茄", "unit_price": 6.5}]}'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.supplier_name == "城南菜场"
```

(The LLM might still return `total_amount` in real responses, but the parser now ignores it. Pydantic's default `extra='ignore'` on `OcrResult` means a stray `total_amount` key in the JSON won't cause an error.)

- [ ] **Step 9: Generate the Alembic migration**

Make sure postgres is running (`docker ps | grep postgres`). From repo root:

```bash
pnpm db:revision -m "drop total_amount"
```

This auto-generates `apps/api/alembic/versions/<rev>_drop_total_amount.py`. Open it to verify the content is just:

```python
def upgrade():
    op.drop_column('purchases', 'total_amount')


def downgrade():
    op.add_column('purchases', sa.Column('total_amount', sa.Numeric(10, 2), nullable=True))
```

If alembic generated extra unrelated changes (e.g. due to model drift), delete those — only the `total_amount` drop should remain.

- [ ] **Step 10: Apply migration**

```bash
pnpm db:migrate
```

- [ ] **Step 11: Run pytest to verify all tests pass**

```bash
cd apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: all tests pass (count may be slightly lower if any total_amount-only tests were removed, but should be ~89-92).

If any test still references `total_amount` and fails, fix it by removing the reference.

- [ ] **Step 12: Commit**

```bash
git add apps/api/app/db/models.py apps/api/app/schemas/purchase.py apps/api/app/schemas/ocr.py apps/api/app/services/ocr/ apps/api/app/routers/purchases.py apps/api/tests/ apps/api/alembic/versions/
git commit -m "feat(api): drop total_amount from data model + OCR prompt + tests"
```

---

### Task 2: Add `purchase_item_id` to /prices/search response

**Files:**
- Modify: `apps/api/app/schemas/price.py`
- Modify: `apps/api/app/routers/prices.py`
- Modify: `apps/api/tests/test_prices_search.py`

- [ ] **Step 1: Add field to SearchResultItem schema**

Open `apps/api/app/schemas/price.py`. In `SearchResultItem`:

```python
class SearchResultItem(BaseModel):
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
```

Add new field at the end (before `purchase_time` is fine, or after — be consistent):

```python
    purchase_id: UUID
    purchase_item_id: UUID
    purchase_time: datetime
```

Also add `purchase_item_id` to the test in `apps/api/tests/test_price_schemas.py` if any test constructs `SearchResultItem` directly (it does — `test_search_result_item_all_fields`). Add `purchase_item_id=uuid4(),` to that construction.

- [ ] **Step 2: Update SQL SELECT in router**

Open `apps/api/app/routers/prices.py`. In the `select(...)` call inside `search_prices`:

Find:
```python
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
```

Add `PurchaseItem.id.label("purchase_item_id"),` after the `brand` line:

```python
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
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
        )
```

Then in the list comprehension building `items`, add `purchase_item_id=row.purchase_item_id,` to the `SearchResultItem(...)` construction:

```python
    items = [
        SearchResultItem(
            name=row.name,
            quantity=row.quantity,
            unit=row.unit,
            unit_price=row.unit_price,
            category=row.category,
            brand=row.brand,
            purchase_item_id=row.purchase_item_id,
            supplier_id=row.supplier_id,
            supplier_name=row.supplier_name,
            purchase_id=row.purchase_id,
            purchase_time=row.purchase_time,
        )
        for row in rows
    ]
```

- [ ] **Step 3: Update price search tests**

Open `apps/api/tests/test_prices_search.py`. Tests that check item fields should now also see `purchase_item_id`. Add to `test_search_returns_matching_items_ordered_by_time_desc`:

Find:
```python
    assert body["items"][0]["purchase_id"] == newer
```

After it, add:
```python
    assert "purchase_item_id" in body["items"][0]
    assert body["items"][0]["purchase_item_id"]  # non-empty uuid string
```

Optional: add similar assertion to `test_search_includes_supplier_name`.

- [ ] **Step 4: Run tests + commit**

```bash
cd apps/api && python -m uv run pytest tests/test_prices_search.py tests/test_price_schemas.py -v
```

Expected: all pass.

```bash
git add apps/api/app/schemas/price.py apps/api/app/routers/prices.py apps/api/tests/test_prices_search.py apps/api/tests/test_price_schemas.py
git commit -m "feat(api): expose purchase_item_id in /prices/search response"
```

---

### Task 3: Add `DELETE /api/v1/purchase-items/{item_id}` endpoint (TDD)

**Files:**
- Create: `apps/api/app/routers/purchase_items.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_purchase_items.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_purchase_items.py`:

```python
from uuid import uuid4

from app.db.models import Purchase


async def test_delete_item_succeeds_when_purchase_has_other_items(client):
    # Create a purchase with 2 items via the API
    r = await client.post(
        "/api/v1/purchases",
        json={
            "items": [
                {"name": "番茄", "quantity": "1", "unit_price": "5"},
                {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    purchase_id = r.json()["id"]
    item_id_to_delete = r.json()["items"][0]["id"]

    # Delete one item
    r = await client.delete(f"/api/v1/purchase-items/{item_id_to_delete}")
    assert r.status_code == 204, r.text

    # Purchase should still exist with 1 item left
    r = await client.get(f"/api/v1/purchases/{purchase_id}")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


async def test_delete_last_item_cascades_purchase_deletion(client):
    r = await client.post(
        "/api/v1/purchases",
        json={
            "items": [
                {"name": "番茄", "quantity": "1", "unit_price": "5"},
            ],
        },
    )
    assert r.status_code == 201
    purchase_id = r.json()["id"]
    item_id = r.json()["items"][0]["id"]

    r = await client.delete(f"/api/v1/purchase-items/{item_id}")
    assert r.status_code == 204

    # Purchase should be gone (cascade)
    r = await client.get(f"/api/v1/purchases/{purchase_id}")
    assert r.status_code == 404


async def test_delete_nonexistent_item_returns_404(client):
    fake_id = uuid4()
    r = await client.delete(f"/api/v1/purchase-items/{fake_id}")
    assert r.status_code == 404
    assert "PURCHASE_ITEM_NOT_FOUND" in r.json()["detail"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && python -m uv run pytest tests/test_purchase_items.py -v
```

Expected: all 3 fail with 404 (route doesn't exist yet).

- [ ] **Step 3: Implement the router**

Create `apps/api/app/routers/purchase_items.py`:

```python
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
```

- [ ] **Step 4: Register router in main.py**

Open `apps/api/app/main.py`. Find the router import:

```python
from app.routers import ocr, prices, purchases, suppliers, uploads
```

Add `purchase_items`:

```python
from app.routers import ocr, prices, purchase_items, purchases, suppliers, uploads
```

Find the `include_router` block and add the new router:

```python
app.include_router(prices.router, prefix=api_prefix)
app.include_router(purchase_items.router, prefix=api_prefix)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd apps/api && python -m uv run pytest tests/test_purchase_items.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Run full suite to verify no regression**

```bash
cd apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/routers/purchase_items.py apps/api/app/main.py apps/api/tests/test_purchase_items.py
git commit -m "feat(api): add DELETE /api/v1/purchase-items/{id} with cascade empty purchase"
```

---

### Task 4: Frontend routing — remove PurchasesPage, move Dashboard to `/`

**Files:**
- Modify: `apps/web/src/App.tsx`
- Delete: `apps/web/src/pages/PurchasesPage.tsx`

- [ ] **Step 1: Update App.tsx**

Open `apps/web/src/App.tsx`. Replace the entire file:

```tsx
import { NavLink, Route, Routes } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";

const navItems = [
  { to: "/", label: "首页", end: true, page: "dashboard" },
  { to: "/entry", label: "记账", end: false, page: "entry" },
  { to: "/suppliers", label: "供应商", end: false, page: "suppliers" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
        <div className="mb-6 px-2">
          <h1 className="text-lg font-bold">烹饪助手</h1>
          <p className="text-xs text-slate-500">智慧采购 · v0.1</p>
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700 font-medium"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-x-hidden p-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/entry" element={<EntryPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

Changes from current:
- Removed `PurchasesPage` import
- Removed `/upload` (already gone) and `/` (was PurchasesPage) routes
- Removed `/dashboard` route — `/` now points to DashboardPage
- navItems reduced from 4 to 3; "价格仪表盘" → "首页", `to: "/dashboard"` → `to: "/"`, `end: true`

- [ ] **Step 2: Delete PurchasesPage.tsx**

```bash
git rm apps/web/src/pages/PurchasesPage.tsx
```

- [ ] **Step 3: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -5
```

Expected: builds clean (87 modules instead of 88 — one fewer page).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/App.tsx apps/web/src/pages/PurchasesPage.tsx
git commit -m "refactor(web): remove PurchasesPage, promote Dashboard to /"
```

---

### Task 5: Dashboard add delete button (frontend)

**Files:**
- Modify: `apps/web/src/pages/DashboardPage.tsx`
- Modify: `apps/web/src/api/client.ts` (if `api.delete` doesn't exist)

- [ ] **Step 1: Verify api.delete helper exists**

Open `apps/web/src/api/client.ts`. Check if there's an `api.delete` method.

If not, add it next to `api.get` / `api.post`:

```typescript
async function del<T>(path: string): Promise<T> {
  const r = await fetch(path, { method: "DELETE" });
  if (r.status === 204) return undefined as T;
  if (!r.ok) throw new ApiError(r.status, await r.json());
  return r.json();
}

export const api = { get, post, upload, delete: del };
```

(Adjust to match the existing api object's export style. Check the file first.)

- [ ] **Step 2: Update DashboardPage.tsx**

Open `apps/web/src/pages/DashboardPage.tsx`. Three changes:

(a) Add `purchase_item_id` to the TS type. Find:

```typescript
type SearchResultItem = {
  name: string;
  quantity: string;
  unit: string | null;
  unit_price: string;
  category: string | null;
  brand: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  purchase_id: string;
  purchase_time: string;
};
```

Add `purchase_item_id: string;` before `purchase_time`:

```typescript
type SearchResultItem = {
  name: string;
  quantity: string;
  unit: string | null;
  unit_price: string;
  category: string | null;
  brand: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  purchase_id: string;
  purchase_item_id: string;
  purchase_time: string;
};
```

(b) Add a `useMutation` for delete + handler. Add `useMutation` to the import:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
```

Inside the component (after the `useQuery` block), add:

```typescript
const deleteMut = useMutation({
  mutationFn: (id: string) => api.delete(`/api/v1/purchase-items/${id}`),
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["prices"] });
  },
  onError: (err: ApiError) => {
    alert(err.detail || "删除失败，请稍后再试");
  },
});

const handleDelete = (id: string, name: string) => {
  if (window.confirm(`确定删除「${name}」这条记录？`)) {
    deleteMut.mutate(id);
  }
};
```

(Note: `qc` is the existing `useQueryClient()` return value. If DashboardPage doesn't have `qc` yet, add `const qc = useQueryClient();` at the top of the component.)

(c) Add the operation column. In the table header, find:

```tsx
                <tr>
                  <th className="px-3 py-2 text-left font-medium">商品名</th>
                  <th className="px-3 py-2 text-right font-medium">单价</th>
                  <th className="px-3 py-2 text-left font-medium">店铺</th>
                  <th className="px-3 py-2 text-left font-medium">采购时间</th>
                </tr>
```

Add a 5th column:

```tsx
                <tr>
                  <th className="px-3 py-2 text-left font-medium">商品名</th>
                  <th className="px-3 py-2 text-right font-medium">单价</th>
                  <th className="px-3 py-2 text-left font-medium">店铺</th>
                  <th className="px-3 py-2 text-left font-medium">采购时间</th>
                  <th className="px-3 py-2 text-right font-medium">操作</th>
                </tr>
```

In each row `<tr>`, find the last `<td>` (purchase_time) and add a new `<td>` after it:

```tsx
                  <tr key={`${it.purchase_id}-${idx}`} className="border-t border-slate-100">
                    <td className="px-3 py-1.5">{it.name}</td>
                    <td className="px-3 py-1.5 text-right font-mono tabular-nums">
                      {formatPrice(it.unit_price, it.unit)}
                    </td>
                    <td className="px-3 py-1.5">
                      {it.supplier_name ?? (
                        <span className="text-slate-400">—（未绑店铺）</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-slate-600">
                      {formatTime(it.purchase_time)}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      <button
                        type="button"
                        title="删除"
                        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                        onClick={() => handleDelete(it.purchase_item_id, it.name)}
                        disabled={deleteMut.isPending}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
```

- [ ] **Step 3: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -5
```

Expected: builds clean.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/DashboardPage.tsx apps/web/src/api/client.ts
git commit -m "feat(web): add per-item delete button on dashboard"
```

---

### Task 6: EntryPage remove total_amount inputs

**Files:**
- Modify: `apps/web/src/pages/EntryPage.tsx`

- [ ] **Step 1: Read current EntryPage to identify all total_amount references**

Run: `grep -n "TotalAmount\|total_amount" apps/web/src/pages/EntryPage.tsx`

Should find references in:
- State declarations: `manualTotalAmount`, `photoTotalAmount`
- Setters: `setManualTotalAmount`, `setPhotoTotalAmount`
- Reset functions: `resetManualState`, `resetPhotoState`
- JSX: `<label>` + `<input type="number">` for both modes
- Save body: `total_amount: manualTotalAmount || null`, `total_amount: photoTotalAmount || null`

- [ ] **Step 2: Remove all total_amount references**

Open `apps/web/src/pages/EntryPage.tsx`. Remove:

(a) State declarations:
```typescript
const [manualTotalAmount, setManualTotalAmount] = useState<string>("");
const [photoTotalAmount, setPhotoTotalAmount] = useState<string>("");
```

(b) Reset setters (inside `resetManualState` and `resetPhotoState`):
```typescript
setManualTotalAmount("");
setPhotoTotalAmount("");
```

(c) Save body fields (inside `manualSaveMut.mutationFn` and `photoSaveMut.mutationFn`):
```typescript
total_amount: manualTotalAmount || null,
total_amount: photoTotalAmount || null,
```

(d) The JSX `<label>` blocks for "总额 (¥)" in both manual and photo modes. Each looks like:
```tsx
<label className="flex flex-col gap-1 text-sm">
  <span className="text-slate-600">总额 (¥)</span>
  <input
    type="number"
    step="0.01"
    className="rounded border border-slate-300 px-2 py-1"
    value={manualTotalAmount /* or photoTotalAmount */}
    onChange={(e) => {
      setManualTotalAmount(e.target.value);  /* or photo */
      ...
    }}
  />
</label>
```

Remove the entire `<label>` block in both places.

(e) The grid that held these inputs was `grid-cols-1 md:grid-cols-3`. Now with only 2 fields (供应商 / 采购时间), change to `md:grid-cols-2`:

Find (in both modes):
```tsx
<div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
```

Replace with:
```tsx
<div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
```

- [ ] **Step 3: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -5
```

Expected: builds clean. Bundle slightly smaller (~227 kB vs 229 kB).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/EntryPage.tsx
git commit -m "feat(web): remove total_amount input from EntryPage (both modes)"
```

---

### Task 7: End-to-end smoke

**Files:** None (verification only)

- [ ] **Step 1: Restart API + web dev servers**

Kill stale processes (Windows uvicorn quirk):
```bash
taskkill //F //IM python.exe 2>&1 | tail -3
```

Start dev:
```bash
cd D:/workspace/kitchen-project && pnpm dev
```

- [ ] **Step 2: Browser walkthrough**

Open `http://localhost:5173/`. Verify:

1. Lands on dashboard (not purchases list). URL is `/`.
2. nav has 3 items: 首页 / 记账 / 供应商. No "采购记录".
3. Dashboard table has 5 columns: 商品名 / 单价 / 店铺 / 采购时间 / 操作.
4. Each row's 操作 column has a red ✕ button.
5. Click ✕ → confirm dialog "确定删除「番茄」这条记录？" → OK → row disappears within 1-2 seconds.
6. Type a search term (e.g., "番茄") + Enter → filtered results, each still has ✕ button.
7. Click `/entry` nav → 记账 page. No "总额" input. 2-column form (供应商 / 采购时间).
8. Switch to 手工 mode → also no 总额 field.
9. Save a manual purchase → success. Goes back to dashboard via 首页 nav → new item at top.

- [ ] **Step 3: Cascade-delete verification**

In dashboard, find a row belonging to a purchase that has only 1 item (use the search filter or just test any single-item purchase).

Click ✕ → confirm → row disappears.

Now search for any other item that was in the same purchase — there shouldn't be any. Verify via:
```bash
curl -s "http://localhost:3000/api/v1/purchases" | python -c "import sys,json; print(len(json.load(sys.stdin)))"
```

Or check: the purchase was deleted from the purchases list.

- [ ] **Step 4: 404 path**

Use browser dev tools or curl:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE http://localhost:3000/api/v1/purchase-items/00000000-0000-0000-0000-000000000000
```

Expected: `404`.

- [ ] **Step 5: Run full backend test suite**

```bash
cd D:/workspace/kitchen-project/apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: all pass (count = previous count + 3 new purchase_items tests).

- [ ] **Step 6: Verify Docker images still build**

```bash
cd D:/workspace/kitchen-project && docker build -f Dockerfile.api -t kitchen-api:smoke . 2>&1 | tail -3
docker build -f Dockerfile.web -t kitchen-web:smoke . 2>&1 | tail -3
docker image rm kitchen-api:smoke kitchen-web:smoke
```

Expected: both build successfully.

- [ ] **Step 7: Commit nothing (verification only)**

If any defect found and fixed, commit those. Otherwise nothing to commit.

---

## Self-Review

### Spec coverage

Mapping each spec section to a task:

- §1 background / 3 pain points → covered by plan goal
- §2 decisions table:
  - Delete粒度 single item → Task 3 (delete endpoint impl)
  - Cascade empty purchase → Task 3 (cascade logic)
  - total_amount 完全干掉 → Task 1 (backend code) + Task 6 (frontend inputs)
  - Dashboard → / → Task 4 (App.tsx routing)
  - Remove 采购记录 page → Task 4 (delete PurchasesPage.tsx)
  - Nav label "首页" → Task 4 (navItems update)
  - Delete UX with ✕ + confirm → Task 5 (handleDelete + window.confirm)
  - Refresh via invalidateQueries → Task 5 (deleteMut.onSuccess)
  - Hard delete, no soft delete → Task 3 (db.delete)
  - Keep old purchases CRUD endpoints → Task 1 doesn't remove them
- §3 architecture → Task 3 (purchase_items router) + Task 4 (App.tsx) + Task 5 (DashboardPage)
- §3.2 data flow → Task 3 implementation
- §4 API contract → Task 2 (purchase_item_id) + Task 3 (DELETE endpoint) + Task 1 (total_amount removal)
- §5 migration → Task 1 Step 9 (alembic autogenerate)
- §6 frontend UI → Task 5 (delete button) + Task 6 (remove total input)
- §7 error handling → Task 5 (onError alert)
- §8 testing → Tasks 1, 2, 3 all include test updates; Task 7 runs full suite
- §9 未决问题:
  - Cascade timing: Task 3 uses "delete item first, then count" approach ✅
  - api.delete helper: Task 5 Step 1 explicitly checks + adds ✅
  - purchase_item_id position: Task 2 puts it after `purchase_id` ✅
  - Delete button label: ✕ + title="删除" per Task 5 Step 2 ✅

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO" / "implement later"
- All code blocks have actual content
- All commands have expected outputs
- Migration step uses autogenerate (standard Alembic workflow) — content will be filled at runtime, but expected output is shown

### Type consistency

- `purchase_item_id: UUID` in Python schema (Task 2) ↔ `purchase_item_id: string` in TS (Task 5) ✅
- `delete_purchase_item(item_id: UUID, db)` signature in Task 3 matches test calls in Task 3 ✅
- `api.delete<T>(path: string)` helper signature in Task 5 matches `deleteMut.mutationFn` call `api.delete(...)` ✅
- `SearchResultItem` schema field name `purchase_item_id` matches SELECT label `PurchaseItem.id.label("purchase_item_id")` in Task 2 ✅
- `handleDelete(id: string, name: string)` in Task 5 matches onClick `(it.purchase_item_id, it.name)` ✅
- `total_amount` removal is consistent: model + schemas + OCR + prompt + parser + mock + routers + tests + frontend — all listed in Task 1 and Task 6

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-24-dashboard-delete-remove-purchases-page.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 7 well-bounded tasks. Backend tasks (1-3) touch different files mostly independently; frontend tasks (4-6) are isolated.

**2. Inline Execution** — Current session, batch with checkpoints.

Which approach?
