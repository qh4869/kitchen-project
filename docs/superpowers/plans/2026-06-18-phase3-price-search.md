# Phase 3 Price Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /api/v1/prices/search` (ILIKE substring + LEFT JOIN suppliers) and replace `DashboardPage` placeholder with a search form + result table.

**Architecture:** Single SQLAlchemy 2.0 async JOIN query → Pydantic `SearchResult` → FastAPI JSON response. Frontend uses TanStack Query keyed by `['prices', q]` with form-submit trigger (no debounce).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, pytest + pytest-asyncio; React 18 + TanStack Query + Tailwind.

**Reference spec:** `docs/superpowers/specs/2026-06-18-phase3-price-search-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/api/app/schemas/price.py` | Create | `SearchResultItem`, `SearchResult` Pydantic models |
| `apps/api/app/routers/prices.py` | Create | `GET /search` handler, query validation, SQL JOIN |
| `apps/api/app/main.py` | Modify | Register `prices` router |
| `apps/api/tests/test_price_schemas.py` | Create | Schema-level unit tests |
| `apps/api/tests/test_prices_search.py` | Create | Router integration tests (12 cases) |
| `apps/web/src/pages/DashboardPage.tsx` | Modify | Replace placeholder with search UI |

---

## Tasks

### Task 1: Pydantic schemas

**Files:**
- Create: `apps/api/app/schemas/price.py`
- Create: `apps/api/tests/test_price_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_price_schemas.py`:

```python
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from app.schemas.price import SearchResult, SearchResultItem


def test_search_result_item_accepts_all_fields():
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1.5"),
        unit="kg",
        unit_price=Decimal("6.50"),
        category="蔬菜",
        brand=None,
        supplier_id=uuid4(),
        supplier_name="城南菜场",
        purchase_id=uuid4(),
        purchase_time=datetime(2026, 6, 17, 9, 32, 29),
    )
    assert item.name == "番茄"
    assert item.quantity == Decimal("1.5")
    assert item.supplier_name == "城南菜场"


def test_search_result_item_allows_null_supplier():
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1"),
        unit=None,
        unit_price=Decimal("5"),
        category=None,
        brand=None,
        supplier_id=None,
        supplier_name=None,
        purchase_id=uuid4(),
        purchase_time=datetime(2026, 6, 17),
    )
    assert item.supplier_id is None
    assert item.supplier_name is None
    assert item.unit is None


def test_search_result_empty_items():
    r = SearchResult(query="nothing", count=0, items=[])
    assert r.count == 0
    assert r.items == []
    assert r.query == "nothing"


def test_search_result_decimal_serializes_as_str():
    """FastAPI's jsonable_encoder turns Decimal into string for JSON output."""
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1.5"),
        unit="kg",
        unit_price=Decimal("6.50"),
        category=None,
        brand=None,
        supplier_id=None,
        supplier_name=None,
        purchase_id=uuid4(),
        purchase_time=datetime(2026, 6, 17),
    )
    encoded = jsonable_encoder(item)
    assert encoded["quantity"] == "1.5"
    assert encoded["unit_price"] == "6.50"
    assert isinstance(encoded["quantity"], str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m uv run pytest tests/test_price_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas.price'`.

- [ ] **Step 3: Implement schemas**

Create `apps/api/app/schemas/price.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && python -m uv run pytest tests/test_price_schemas.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/schemas/price.py apps/api/tests/test_price_schemas.py
git commit -m "feat(api): add price-search response schemas"
```

---

### Task 2: /prices/search router

**Files:**
- Create: `apps/api/app/routers/prices.py`
- Create: `apps/api/tests/test_prices_search.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_prices_search.py`:

```python
from datetime import datetime, timezone


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def _make_supplier(client, name="城南菜场"):
    r = await client.post("/api/v1/suppliers", json={"name": name})
    return r.json()["id"]


async def _make_purchase(client, *, items, supplier_id=None, purchase_time):
    """Create one purchase with the given items. items: [{name, quantity, unit_price, ...}]"""
    payload = {
        "supplier_id": supplier_id,
        "purchase_time": _iso(purchase_time),
        "items": items,
    }
    r = await client.post("/api/v1/purchases", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_search_returns_matching_items_ordered_by_time_desc(client):
    sid = await _make_supplier(client)
    older = await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )
    newer = await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1.5", "unit_price": "6.5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "番茄"
    assert body["count"] == 2
    assert body["items"][0]["purchase_id"] == newer
    assert body["items"][1]["purchase_id"] == older


async def test_search_case_insensitive(client):
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "Tomato", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "tomato"})
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = await client.get("/api/v1/prices/search", params={"q": "TOMATO"})
    assert r.status_code == 200
    assert r.json()["count"] == 1


async def test_search_substring_matches(client):
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
            {"name": "番薯", "quantity": "2", "unit_price": "3.8"},
            {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
        ],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    names = {it["name"] for it in body["items"]}
    assert names == {"番茄", "番薯"}


async def test_search_includes_supplier_name(client):
    sid = await _make_supplier(client, name="永辉超市")
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    body = r.json()
    assert body["items"][0]["supplier_name"] == "永辉超市"


async def test_search_handles_null_supplier(client):
    # Purchase with no supplier_id
    await _make_purchase(
        client,
        supplier_id=None,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["supplier_id"] is None
    assert body["items"][0]["supplier_name"] is None


async def test_search_default_limit_50(client):
    sid = await _make_supplier(client)
    # Insert 60 distinct items all matching "x"
    items = [
        {"name": f"x{i}", "quantity": "1", "unit_price": "1"}
        for i in range(60)
    ]
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=items,
    )

    r = await client.get("/api/v1/prices/search", params={"q": "x"})
    body = r.json()
    assert body["count"] == 50


async def test_search_custom_limit(client):
    sid = await _make_supplier(client)
    items = [
        {"name": f"x{i}", "quantity": "1", "unit_price": "1"}
        for i in range(20)
    ]
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=items,
    )

    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 10})
    body = r.json()
    assert body["count"] == 10


async def test_search_limit_zero_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 0})
    assert r.status_code == 422


async def test_search_limit_over_max_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 201})
    assert r.status_code == 422


async def test_search_query_required(client):
    r = await client.get("/api/v1/prices/search")
    assert r.status_code == 422


async def test_search_query_empty_after_strip_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "   "})
    assert r.status_code == 422
    assert "INVALID_QUERY" in r.json()["detail"]


async def test_search_query_too_long_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x" * 101})
    assert r.status_code == 422
    assert "INVALID_QUERY" in r.json()["detail"]


async def test_search_escapes_like_wildcards(client):
    """User searching for literal % or _ must not get wildcard behavior."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "100%纯果汁", "quantity": "1", "unit_price": "10"},
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
        ],
    )

    # Searching for literal "%" should match only the juice, not everything
    r = await client.get("/api/v1/prices/search", params={"q": "%"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["name"] == "100%纯果汁"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m uv run pytest tests/test_prices_search.py -v`
Expected: All tests FAIL with 404 (route doesn't exist yet) or import errors.

- [ ] **Step 3: Implement router**

Create `apps/api/app/routers/prices.py`:

```python
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
            detail="INVALID_QUERY: query is empty after strip",
        )
    if len(q_stripped) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"INVALID_QUERY: query exceeds {MAX_QUERY_LENGTH} chars",
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
```

- [ ] **Step 4: Register router in main.py**

Open `apps/api/app/main.py`. Modify the router import line and the `include_router` calls.

Find:
```python
from app.routers import ocr, purchases, suppliers, uploads
```
Replace:
```python
from app.routers import ocr, prices, purchases, suppliers, uploads
```

Find:
```python
app.include_router(ocr.router, prefix=api_prefix)
```
Add after it:
```python
app.include_router(prices.router, prefix=api_prefix)
```

Final relevant section of `main.py`:

```python
from app.routers import ocr, prices, purchases, suppliers, uploads
# ...
api_prefix = "/api/v1"
app.include_router(suppliers.router, prefix=api_prefix)
app.include_router(purchases.router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)
app.include_router(ocr.router, prefix=api_prefix)
app.include_router(prices.router, prefix=api_prefix)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/api && python -m uv run pytest tests/test_prices_search.py -v`
Expected: 12 passed.

If `test_search_default_limit_50` is slow (60 items in one purchase), that's normal — single-row insert.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routers/prices.py apps/api/app/main.py apps/api/tests/test_prices_search.py
git commit -m "feat(api): add GET /api/v1/prices/search with ILIKE + supplier JOIN"
```

---

### Task 3: Frontend DashboardPage

**Files:**
- Modify: `apps/web/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Replace DashboardPage placeholder**

Overwrite `apps/web/src/pages/DashboardPage.tsx`:

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";

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

type SearchResult = {
  query: string;
  count: number;
  items: SearchResultItem[];
};

type Phase = "initial" | "loading" | "empty" | "success" | "error";

function formatPrice(unitPrice: string, unit: string | null): string {
  return `¥${unitPrice}${unit ? ` / ${unit}` : ""}`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function DashboardPage() {
  const [input, setInput] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");

  const { data, isFetching, error } = useQuery<SearchResult>({
    queryKey: ["prices", submittedQ],
    queryFn: () =>
      api.get<SearchResult>(
        `/api/v1/prices/search?q=${encodeURIComponent(submittedQ)}`
      ),
    enabled: !!submittedQ,
  });

  const phase: Phase = !submittedQ
    ? "initial"
    : isFetching
      ? "loading"
      : error
        ? "error"
        : data && data.count === 0
          ? "empty"
          : "success";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (q) setSubmittedQ(q);
  };

  return (
    <div className="max-w-4xl">
      <h2 className="mb-4 text-xl font-bold">价格查询</h2>

      <form onSubmit={handleSubmit} className="mb-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入食材名，如 番茄 / 鸡蛋 / 五花肉"
          className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={isFetching || !input.trim()}
          className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
        >
          {isFetching ? "搜索中…" : "搜索"}
        </button>
      </form>

      {phase === "initial" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          提示：商品名为 OCR 或手工录入时的原文，子串模糊匹配（"番" 能搜到番茄、番薯）。最多返回 50 条最近记录。
        </div>
      )}

      {phase === "loading" && (
        <p className="text-sm text-slate-500">查询中…</p>
      )}

      {phase === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          查询失败：{(error as ApiError).detail || "网络异常，请稍后重试"}
        </div>
      )}

      {phase === "empty" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          未找到 &ldquo;{submittedQ}&rdquo; 的采购记录。可以换个关键词，或先去「拍照记账」/「采购记录」录入。
        </div>
      )}

      {phase === "success" && data && (
        <>
          <p className="mb-2 text-xs text-slate-500">
            找到 {data.count} 条匹配记录（按采购时间倒序）
          </p>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">商品名</th>
                  <th className="px-3 py-2 text-right font-medium">单价</th>
                  <th className="px-3 py-2 text-left font-medium">店铺</th>
                  <th className="px-3 py-2 text-left font-medium">采购时间</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it, idx) => (
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully (no TS errors).

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/pages/DashboardPage.tsx
git commit -m "feat(web): replace DashboardPage placeholder with price search UI"
```

---

### Task 4: End-to-end smoke

**Files:** None (verification only)

- [ ] **Step 1: Ensure DB is up**

Run: `docker ps --filter name=kitchen-postgres --format "{{.Status}}"`
Expected: `Up ... (healthy)`. If not running: `pnpm db:up`.

- [ ] **Step 2: Ensure at least one purchase with items exists**

The /purchases endpoints should already have data from earlier sessions. If 0 purchases exist, create one via the browser at http://localhost:5173/upload (mock provider is fine) or directly POST to /api/v1/purchases.

- [ ] **Step 3: Start dev servers**

Run: `cd D:/workspace/kitchen-project && pnpm dev`
Expected: `[api]` shows `Uvicorn running on http://0.0.0.0:3000`; `[web]` shows vite ready on 5173.

If on Windows and you see stale behavior from previous uvicorn runs, fully kill Python processes first: `taskkill //F //IM python.exe` (use `//` not `/` to escape the path-like arg in Git Bash), then restart `pnpm dev`.

- [ ] **Step 4: Walk the search flow in browser**

Open http://localhost:5173/dashboard. Steps:
1. Search box shows the amber hint banner — initial state correct.
2. Type "番茄" (or any name that exists in your purchases) and press Enter.
3. Button shows "搜索中…" briefly, then results table appears with count message.
4. Verify columns: 商品名 / 单价 (¥X / unit) / 店铺 / 采购时间 (YYYY-MM-DD HH:mm).
5. If a row has no supplier, "—（未绑店铺）" should appear in grey.
6. Search for a non-existent name like "xyz" — empty banner appears.
7. Search for "" (empty) — button is disabled, no request fires.

Expected: all states render correctly.

- [ ] **Step 5: Run full test suite**

Run: `cd apps/api && python -m uv run pytest`
Expected: all previous tests (73) + 4 schema tests + 12 router tests = 89 passed, 1 integration test SKIPPED.

- [ ] **Step 6: Commit nothing (verification only)**

If any defect was found and fixed during smoke, commit those fixes. Otherwise nothing to commit.

---

## Self-Review

### Spec coverage

Mapping each spec section to a task:

- §1 background / scope → covered by plan goal/architecture
- §2 decisions table → each decision mapped:
  - Scope (search only) → all tasks (no chart/comparison code)
  - ILIKE substring → Task 2 router + test_substring_matches
  - Top 50 default → Task 2 router + test_default_limit_50
  - 4 columns (name / price+unit / supplier / time) → Task 3 frontend
  - LEFT JOIN null supplier → Task 2 router + test_handles_null_supplier
  - `/prices/search` URL → Task 2 router
  - onSubmit trigger → Task 3 frontend (no debounce)
  - Replace DashboardPage → Task 3
- §3 architecture → Task 1 (schemas) + Task 2 (router)
- §3.2 SQL escape → Task 2 router + test_escapes_like_wildcards
- §4 API contract → Task 1 (response shape) + Task 2 (request validation)
- §5 frontend → Task 3 (all 5 states rendered)
- §6 error handling → Task 2 (422 codes) + Task 3 (banner states)
- §7 testing strategy → 12 tests written into Task 2; 4 schema tests in Task 1
- §8 未决问题 defaults: Decimal as Decimal-let-FastAPI-handle-str (Task 1 schema), ISO 8601 with Z (Task 1 + tests), `ESCAPE '\\'` (Task 2 router)

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO" / "implement later"
- Every code step has actual code
- Every test step has actual test code
- No "similar to Task N" — repeated where needed

### Type consistency

- `SearchResultItem` schema (Task 1) used identically in Task 2 router and Task 3 frontend (`SearchResultItem` TS type matches the Pydantic fields)
- `SearchResult` (Task 1) matches router return type (Task 2) and frontend `SearchResult` type (Task 3)
- `quantity: Decimal` in Python ↔ `quantity: string` in TS (FastAPI serializes Decimal → str; tested in Task 1 Step 1 `test_search_result_decimal_serializes_as_str`)
- `purchase_id: UUID` in Python ↔ `purchase_id: string` in TS (JSON has no UUID type)
- Router signature `search_prices(q, limit, db)` consistent across impl (Task 2 Step 3) and tests (Task 2 Step 1 — both use `params={"q": ..., "limit": ...}`)
- Helper signatures `_make_supplier`, `_make_purchase` defined once at top of test file (Task 2 Step 1) and used by all subsequent tests

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-18-phase3-price-search.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Best when tasks are well-bounded (they are — 4 tasks, clear inputs/outputs).

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Best when you want to follow along / course-correct in real time.

Which approach?
