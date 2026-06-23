# Empty Price Query → Show All Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `GET /api/v1/prices/search` treat empty / whitespace-only `q` as match-all (return latest N regardless of name); frontend auto-loads on page mount and lets the user re-fire with empty input.

**Architecture:** Single conditional in the SQL builder — when `q.strip()` is empty, skip the `.where(...)` clause entirely. Frontend drops the `'initial'` phase + hint banner and removes the `!input.trim()` button-disable + `enabled: !!submittedQ` query gate.

**Tech Stack:** Python 3.13 + FastAPI + SQLAlchemy 2.0 async + pytest; React 18 + TanStack Query v5 + Tailwind v3.

**Reference spec:** `docs/superpowers/specs/2026-06-23-empty-query-shows-all-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/api/app/routers/prices.py` | Modify | `q: str = Query("")` (default empty); skip WHERE when stripped empty; update too-long message wording |
| `apps/api/tests/test_prices_search.py` | Modify | 2 tests rewrite (422→200), 1 test new (empty-q respects limit), 1 test message-tweak (too-long wording) |
| `apps/web/src/pages/DashboardPage.tsx` | Modify | Drop `'initial'` phase + hint banner; button always enabled; empty-query copy branches |

---

## Tasks

### Task 1: Backend router + tests (TDD)

**Files:**
- Modify: `apps/api/app/routers/prices.py`
- Modify: `apps/api/tests/test_prices_search.py`

- [ ] **Step 1: Read current router for reference**

Run: `cat apps/api/app/routers/prices.py`

Current shape: `q: str = Query(...)` (required), raises 422 on empty-after-strip and on too-long, then builds a SELECT with mandatory `.where(PurchaseItem.name.ilike(...))`.

- [ ] **Step 2: Rewrite the test file's two empty-query tests + add a new limit-on-empty test + tweak too-long assertion**

Open `apps/api/tests/test_prices_search.py`.

**Find** `test_search_query_required` (currently expects 422 when `q` is missing):

```python
async def test_search_query_required(client):
    r = await client.get("/api/v1/prices/search")
    assert r.status_code == 422
```

**Replace** with:

```python
async def test_search_empty_q_returns_all_items(client):
    """No q param → match-all, returns latest N items regardless of name."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
            {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
            {"name": "黄瓜", "quantity": "2", "unit_price": "3.8"},
        ],
    )

    r = await client.get("/api/v1/prices/search")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == ""
    assert body["count"] == 3
    names = {it["name"] for it in body["items"]}
    assert names == {"番茄", "鸡蛋", "黄瓜"}


async def test_search_whitespace_q_returns_all_items(client):
    """q='   ' strips to empty → match-all."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "   "})
    assert r.status_code == 200
    assert r.json()["count"] == 1


async def test_search_empty_q_respects_limit(client):
    """Empty q with limit=10 truncates to 10 even when more rows exist."""
    sid = await _make_supplier(client)
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

    r = await client.get("/api/v1/prices/search", params={"limit": 10})
    assert r.status_code == 200
    assert r.json()["count"] == 10
```

**Find** `test_search_query_too_long_returns_422`:

```python
async def test_search_query_too_long_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x" * 101})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.startswith("INVALID_QUERY: query must be 1-100 chars")
    assert "101" in detail  # actual length is included
```

**Replace** with:

```python
async def test_search_query_too_long_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x" * 101})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.startswith("INVALID_QUERY: query must be at most 100 chars")
    assert "101" in detail  # actual length is included
```

(Only the assertion string changed: `"1-100 chars"` → `"at most 100 chars"` to match the new wording in the implementation.)

- [ ] **Step 3: Run tests to verify they fail in the expected way**

Run: `cd apps/api && python -m uv run pytest tests/test_prices_search.py -v`

Expected failures (because router still requires `q`):
- `test_search_empty_q_returns_all_items` — FAIL with 422 instead of 200
- `test_search_whitespace_q_returns_all_items` — FAIL with 422 instead of 200
- `test_search_empty_q_respects_limit` — FAIL with 422 instead of 200
- `test_search_query_too_long_returns_422` — FAIL with `"query must be 1-100 chars"` not found

All other tests in the file should still PASS.

- [ ] **Step 4: Rewrite the router**

Overwrite `apps/api/app/routers/prices.py` with:

```python
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
            Purchase.id.label("purchase_id"),
            Purchase.purchase_time,
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
            purchase_time=row.purchase_time,
        )
        for row in rows
    ]
    return SearchResult(query=q_stripped, count=len(items), items=items)
```

Three changes from the original:
1. `q: str = Query(...)` → `q: str = Query("")` (default empty string)
2. Removed the `if not q_stripped: raise 422` branch
3. Wrapped `.where(...)` in `if q_stripped:` conditional (moved after the base `stmt`)
4. Updated too-long message: `"query must be 1-100 chars"` → `"query must be at most 100 chars"` (since 0 is now valid)

- [ ] **Step 5: Run router tests to verify they pass**

Run: `cd apps/api && python -m uv run pytest tests/test_prices_search.py -v`
Expected: 14 passed (was 13 — one new test added).

- [ ] **Step 6: Run full backend suite to confirm no regression**

Run: `cd apps/api && python -m uv run pytest`
Expected: 92 passed (was 91; +1 from the new test_search_empty_q_respects_limit).

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/routers/prices.py apps/api/tests/test_prices_search.py
git commit -m "feat(api): empty q in /prices/search returns all recent items"
```

---

### Task 2: Frontend DashboardPage

**Files:**
- Modify: `apps/web/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Read current DashboardPage for reference**

Run: `cat apps/web/src/pages/DashboardPage.tsx`

Current shape: `submittedQ: string` (default `""`), `useQuery` with `enabled: !!submittedQ` (gated), button `disabled={isFetching || !input.trim()}`, phase includes `'initial'` showing a hint banner.

- [ ] **Step 2: Overwrite DashboardPage.tsx**

Overwrite `apps/web/src/pages/DashboardPage.tsx` with:

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

type Phase = "loading" | "empty" | "success" | "error";

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
  });

  const phase: Phase = isFetching
    ? "loading"
    : error
      ? "error"
      : data && data.count === 0
        ? "empty"
        : "success";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittedQ(input.trim());
  };

  return (
    <div className="max-w-4xl">
      <h2 className="mb-4 text-xl font-bold">价格查询</h2>

      <form onSubmit={handleSubmit} className="mb-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入食材名（留空 = 看最近 50 条），如 番茄 / 鸡蛋 / 五花肉"
          className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button
          type="submit"
          disabled={isFetching}
          className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
        >
          {isFetching ? "搜索中…" : "搜索"}
        </button>
      </form>

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
          {submittedQ === ""
            ? "暂无采购记录。去「记账」添加第一条。"
            : `未找到 "${submittedQ}" 的采购记录。可以换个关键词，或先去「记账」/「采购记录」录入。`}
        </div>
      )}

      {phase === "success" && data && (
        <>
          <p className="mb-2 text-xs text-slate-500">
            {submittedQ === ""
              ? `最近 ${data.count} 条采购记录（按时间倒序）`
              : `找到 ${data.count} 条匹配记录（按采购时间倒序）`}
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

Changes from current:
1. `Phase` type: dropped `'initial'` (4 values instead of 5)
2. `useQuery`: removed `enabled: !!submittedQ` line (always enabled → auto-fires on mount)
3. `phase` derivation: removed `!submittedQ ? "initial" :` branch
4. `handleSubmit`: removed `if (q) setSubmittedQ(q)` guard — now always calls `setSubmittedQ(input.trim())`
5. `placeholder`: added "（留空 = 看最近 50 条）" hint
6. Button `disabled`: removed `|| !input.trim()` (only `isFetching` now)
7. Removed the `phase === "initial"` hint banner block entirely
8. Empty-state copy: branch on `submittedQ === ""` ("暂无采购记录" vs "未找到 X")
9. Success-state count copy: branch on `submittedQ === ""` ("最近 N 条" vs "找到 N 条匹配记录")

- [ ] **Step 3: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully (88 modules, ~230 kB).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/DashboardPage.tsx
git commit -m "feat(web): auto-load latest 50 on /dashboard mount"
```

---

### Task 3: End-to-end smoke

**Files:** None (verification only)

- [ ] **Step 1: Ensure DB + API running**

If `kitchen-postgres` is not up: `pnpm db:up`.

Kill stale Python first (Windows uvicorn quirk):
```bash
taskkill //F //IM python.exe 2>&1 | tail -3
```

Start fresh dev API in background:
```bash
cd D:/workspace/kitchen-project && pnpm dev:api
```
Wait ~5s, probe `http://localhost:3000/health`.

- [ ] **Step 2: Verify empty-q returns all via curl**

First, ensure at least one purchase exists (skip if you know there's data):
```bash
curl -s "http://localhost:3000/api/v1/purchases" | python -c "import sys,json; print('count:', len(json.load(sys.stdin)))"
```

If 0 purchases, seed some via `/api/v1/suppliers` + `/api/v1/purchases`.

Now verify empty-q:
```bash
# Case A: no q param at all
curl -s "http://localhost:3000/api/v1/prices/search" | python -c "import sys,json; d=json.load(sys.stdin); print(f'query={d[\"query\"]!r} count={d[\"count\"]}')"

# Case B: empty string
curl -s "http://localhost:3000/api/v1/prices/search?q=" | python -c "import sys,json; d=json.load(sys.stdin); print(f'query={d[\"query\"]!r} count={d[\"count\"]}')"

# Case C: whitespace
curl -s "http://localhost:3000/api/v1/prices/search?q=%20%20%20" | python -c "import sys,json; d=json.load(sys.stdin); print(f'query={d[\"query\"]!r} count={d[\"count\"]}')"
```

Expected for all three: `query='' count=N` where N is your total purchase_items count (up to 50).

- [ ] **Step 3: Verify keyword still works**

```bash
# Pick a name you know exists in the DB
curl -s "http://localhost:3000/api/v1/prices/search?q=%E7%95%AA%E8%8C%84" | python -c "import sys,json; d=json.load(sys.stdin); print(f'query={d[\"query\"]!r} count={d[\"count\"]}')"
# %E7%95%AA%E8%8C%84 = URL-encoded "番茄"
```

Expected: `query='番茄' count=M` where M ≤ N (filtered subset).

- [ ] **Step 4: Verify too-long still rejected**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:3000/api/v1/prices/search?q=$(python -c 'print("x"*101)')"
```

Expected: `422`.

```bash
curl -s "http://localhost:3000/api/v1/prices/search?q=$(python -c 'print("x"*101)')"
```

Expected detail: `INVALID_QUERY: query must be at most 100 chars (got 101)`.

- [ ] **Step 5: Browser walkthrough**

Open `http://localhost:5173/dashboard`. Verify:
1. Page loads → brief "查询中…" → table of recent 50 items appears (no amber hint banner)
2. Above the table: "最近 N 条采购记录（按时间倒序）"
3. Leave input empty + click 搜索 → table refreshes (or stays same if no state change)
4. Type a name you know + Enter → "找到 N 条匹配记录" + filtered table
5. Type a name that doesn't exist + Enter → "未找到 X 的采购记录..."
6. Clear the input + click 搜索 → back to "最近 N 条"

Expected: all behaviors match.

- [ ] **Step 6: Run full backend test suite one final time**

```bash
cd D:/workspace/kitchen-project/apps/api && python -m uv run pytest
```

Expected: 92 passed (or +1 integration if LLM_API_KEY set).

- [ ] **Step 7: Commit nothing (verification only)**

If any defect found and fixed, commit those. Otherwise nothing to commit.

---

## Self-Review

### Spec coverage

- §1 background → plan goal
- §2 decisions table:
  - 空 query 全匹配 → Task 1 Step 4 (`if q_stripped:` gating the WHERE)
  - 进页面自动加载 → Task 2 Step 2 (useQuery no `enabled`)
  - onSubmit 触发 → Task 2 Step 2 (handleSubmit unchanged in pattern)
  - `q=""` 默认 + max_length → Task 1 Step 4 (`Query("")` + manual length check)
  - 纯空白当空 → Task 1 Step 4 (strip applied before branch)
  - 0 条记录文案分支 → Task 2 Step 2 (empty-state ternary)
- §3 architecture → Task 1 (router) + Task 2 (frontend)
- §4 API contract → Task 1 (200/422 boundary matches)
- §5 frontend → Task 2 (Phase shrinks, button enabled, copy branches, placeholder updated)
- §6 error handling matrix → Task 1 (422 for too-long) + Task 2 (empty/error banners)
- §7 testing strategy → Task 1 Step 2 (2 rewrite + 1 new + 1 message tweak)
- §8 未决问题: staleTime default → unchanged (out of scope); query field returns `q_stripped` → Task 1 returns it; max_length manual → Task 1 uses manual check ✅

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO"
- All code blocks have actual content
- All commands have expected outputs

### Type consistency

- `q: str = Query("")` in router (Task 1) ↔ `q=` (default empty) in URL (Task 3 smoke)
- `query` field returns `q_stripped` (Task 1) ↔ `body["query"] == ""` (Task 1 test) ↔ `submittedQ === ""` check in frontend (Task 2)
- `MAX_QUERY_LENGTH = 100` constant preserved
- Test helper names (`_make_supplier`, `_make_purchase`, `_iso`) unchanged from prior plan
- `Phase` type changes from 5 values to 4 — only used in `DashboardPage.tsx` (Task 2), no cross-file coupling

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-empty-query-shows-all.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 3 well-bounded tasks (router+tests, frontend, smoke).

**2. Inline Execution** — Current session, batch with checkpoints.

Which approach?
