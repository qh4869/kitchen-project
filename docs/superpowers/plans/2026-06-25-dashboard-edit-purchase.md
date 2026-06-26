# Dashboard Edit Purchase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ✎ edit button on dashboard rows; click → confirm → open the entire purchase in EntryPage's manual mode pre-filled, allowing modify/add/remove items, save via PUT, navigate back.

**Architecture:** Backend extends existing `PUT /api/v1/purchases/{id}` to accept optional `items` list (replace if provided, preserve if omitted). Frontend DashboardPage adds ✎ button per row that navigates to `/entry?edit={purchase_id}` after a confirm dialog. EntryPage detects `?edit=` query param, fetches purchase via existing GET endpoint, locks to manual mode with form pre-filled, saves via PUT, navigates back to `/`.

**Tech Stack:** Python 3.13 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + pytest; React 18 + TanStack Query v5 + react-router-dom v6 + Tailwind.

**Reference spec:** `docs/superpowers/specs/2026-06-25-dashboard-edit-purchase-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/api/app/schemas/purchase.py` | Modify | `PurchaseUpdate` add optional `items: list[PurchaseItemCreate] \| None = None` |
| `apps/api/app/routers/purchases.py` | Modify | `update_purchase` handler — replace items if provided |
| `apps/api/tests/test_purchases.py` | Modify | Add 3 PUT-with-items tests |
| `apps/web/src/pages/DashboardPage.tsx` | Modify | Add ✎ button + `handleEdit` + `useNavigate` |
| `apps/web/src/pages/EntryPage.tsx` | Modify | Edit-mode detection, prefill, save via PUT, cancel button |
| `apps/web/src/api/client.ts` | Modify (if missing) | Add `api.put` helper |

---

## Tasks

### Task 1: Backend — extend PUT /purchases to handle items (TDD)

**Files:**
- Modify: `apps/api/app/schemas/purchase.py`
- Modify: `apps/api/app/routers/purchases.py`
- Modify: `apps/api/tests/test_purchases.py`

- [ ] **Step 1: Write failing tests**

Open `apps/api/tests/test_purchases.py`. At the bottom of the file, add:

```python
from uuid import uuid4


async def test_update_purchase_replaces_items_when_provided(client):
    # Create purchase with 2 items
    r = await client.post(
        "/api/v1/purchases",
        json={
            "items": [
                {"name": "番茄", "quantity": "1", "unit_price": "5"},
                {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
            ],
        },
    )
    purchase_id = r.json()["id"]

    # PUT with 3 new items (different from original)
    r = await client.put(
        f"/api/v1/purchases/{purchase_id}",
        json={
            "items": [
                {"name": "番茄", "quantity": "2", "unit_price": "6"},
                {"name": "黄瓜", "quantity": "1", "unit_price": "3"},
                {"name": "葱", "quantity": "0.5", "unit_price": "2"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 3
    names = {it["name"] for it in items}
    assert names == {"番茄", "黄瓜", "葱"}
    # 鸡蛋 (original) should be gone
    assert "鸡蛋" not in names


async def test_update_purchase_preserves_items_when_omitted(client):
    r = await client.post(
        "/api/v1/purchases",
        json={"items": [{"name": "番茄", "quantity": "1", "unit_price": "5"}]},
    )
    purchase_id = r.json()["id"]
    original_item_id = r.json()["items"][0]["id"]

    # PUT without items key, only updating manual_adjustment
    r = await client.put(
        f"/api/v1/purchases/{purchase_id}",
        json={"manual_adjustment": True},
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    # Same item preserved (not deleted + recreated)
    assert items[0]["id"] == original_item_id
    assert items[0]["name"] == "番茄"


async def test_update_purchase_404_on_missing_purchase(client):
    fake_id = uuid4()
    r = await client.put(
        f"/api/v1/purchases/{fake_id}",
        json={"manual_adjustment": True},
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && python -m uv run pytest tests/test_purchases.py::test_update_purchase_replaces_items_when_provided tests/test_purchases.py::test_update_purchase_preserves_items_when_omitted tests/test_purchases.py::test_update_purchase_404_on_missing_purchase -v
```

Expected:
- `test_update_purchase_replaces_items_when_provided` — FAIL: PUT accepts items but doesn't replace them. Will likely show 2 items instead of 3 (or might pass partially if items list is currently being added to relationship, leaving 5). Investigate the actual failure to understand current behavior.
- `test_update_purchase_preserves_items_when_omitted` — likely already PASSES (current code only updates explicit fields).
- `test_update_purchase_404_on_missing_purchase` — likely already PASSES (existing handler raises 404).

So expected: 1 fail (first test), 2 passes.

- [ ] **Step 3: Add optional `items` field to PurchaseUpdate**

Open `apps/api/app/schemas/purchase.py`. Find `PurchaseUpdate`:

```python
class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    notes: str | None = None
    manual_adjustment: bool | None = None
```

Add `items` field at the end:

```python
class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    purchase_time: datetime | None = None
    notes: str | None = None
    manual_adjustment: bool | None = None
    items: list[PurchaseItemCreate] | None = None
```

- [ ] **Step 4: Update `update_purchase` handler to replace items when provided**

Open `apps/api/app/routers/purchases.py`. Find the existing `update_purchase` handler:

```python
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
```

Replace with:

```python
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

    payload_dict = payload.model_dump(exclude_unset=True)

    # Update purchase-level fields (everything except items)
    for field, value in payload_dict.items():
        if field == "items":
            continue
        setattr(purchase, field, value)

    # If items explicitly provided, replace the entire items list.
    # SQLAlchemy's cascade="all, delete-orphan" on Purchase.items relationship
    # automatically deletes the old items when we assign a new list.
    if "items" in payload_dict:
        purchase.items = [
            PurchaseItem(**item.model_dump()) for item in (payload.items or [])
        ]

    await db.commit()
    # Re-fetch to ensure items collection is freshly loaded after replace
    refreshed = await db.get(
        Purchase, purchase_id, options=[selectinload(Purchase.items)]
    )
    assert refreshed is not None
    return refreshed
```

Key changes:
- Compute `payload_dict` once to detect which fields were explicitly set
- Skip `items` in the field-update loop (handle separately)
- If `items` key present: assign new list to `purchase.items` (SQLAlchemy cascade deletes old, inserts new)
- After commit, re-fetch to ensure response has correct items list (avoid stale state)

- [ ] **Step 5: Run new tests to verify they pass**

```bash
cd apps/api && python -m uv run pytest tests/test_purchases.py::test_update_purchase_replaces_items_when_provided tests/test_purchases.py::test_update_purchase_preserves_items_when_omitted tests/test_purchases.py::test_update_purchase_404_on_missing_purchase -v
```

Expected: 3 passed.

- [ ] **Step 6: Run full suite to confirm no regression**

```bash
cd apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: 98 passed (was 95, +3 new tests).

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/schemas/purchase.py apps/api/app/routers/purchases.py apps/api/tests/test_purchases.py
git commit -m "feat(api): PUT /purchases/{id} accepts optional items for full replace"
```

---

### Task 2: Frontend — DashboardPage ✎ edit button

**Files:**
- Modify: `apps/web/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Add `useNavigate` import**

Open `apps/web/src/pages/DashboardPage.tsx`. Update the react-router-dom import.

Find:
```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
```

Add `useNavigate` from react-router-dom. After the existing imports, add:

```typescript
import { useNavigate } from "react-router-dom";
```

(Full import block becomes:)
```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
```

- [ ] **Step 2: Add navigate + handleEdit inside the component**

Inside the `DashboardPage` component, after the `useQueryClient` line (`const qc = useQueryClient();`), add:

```typescript
const navigate = useNavigate();

const handleEdit = (purchaseId: string) => {
  if (window.confirm("编辑将打开该记录所属采购单的全部内容，是否继续？")) {
    navigate(`/entry?edit=${purchaseId}`);
  }
};
```

- [ ] **Step 3: Add ✎ button to the operation column**

Find the existing `<td>` for the operation column in the table row body (currently just contains the ✕ delete button):

```tsx
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
```

Replace with (add ✎ before ✕, plus `whitespace-nowrap` to prevent wrap, and `mr-2` spacing):

```tsx
<td className="px-3 py-1.5 text-right whitespace-nowrap">
  <button
    type="button"
    title="编辑"
    className="text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50 mr-2"
    onClick={() => handleEdit(it.purchase_id)}
    disabled={deleteMut.isPending}
  >
    ✎
  </button>
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
```

- [ ] **Step 4: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -5
```

Expected: builds clean.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/DashboardPage.tsx
git commit -m "feat(web): add edit button on dashboard rows"
```

---

### Task 3: Frontend — EntryPage edit mode

**Files:**
- Modify: `apps/web/src/pages/EntryPage.tsx`
- Modify (if `api.put` missing): `apps/web/src/api/client.ts`

- [ ] **Step 1: Verify `api.put` helper exists**

Open `apps/web/src/api/client.ts`. Check if the exported `api` object has a `put` method.

If NOT present, add it. Likely the existing pattern (next to `get`, `post`, `delete`):

```typescript
async function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

export const api = { get, post, put, upload, delete: del };
```

(Adjust to match the existing helper pattern — read the file first to see how `post` is implemented, then mirror for `put`.)

- [ ] **Step 2: Add edit-mode imports + state**

Open `apps/web/src/pages/EntryPage.tsx`. Update imports.

Find:
```typescript
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
```

Add `useEffect` to React import and react-router-dom imports:

```typescript
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
```

- [ ] **Step 3: Define PurchaseOut type + edit-mode detection**

Near the top of the file (after the existing `OcrResult` type), add:

```typescript
type PurchaseOutItem = {
  id: string;
  name: string;
  quantity: string;
  unit: string | null;
  unit_price: string;
  category: string | null;
  brand: string | null;
};

type PurchaseOut = {
  id: string;
  supplier_id: string | null;
  purchase_time: string;
  notes: string | null;
  manual_adjustment: boolean;
  items: PurchaseOutItem[];
};
```

- [ ] **Step 4: Add `toLocalInputValue` helper**

Near the existing `nowLocalDateTime` helper, add:

```typescript
function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
```

- [ ] **Step 5: Inside EntryPage component, detect edit mode + fetch purchase**

After the existing `const qc = useQueryClient();` line, add:

```typescript
const navigate = useNavigate();
const [searchParams] = useSearchParams();
const editPurchaseId = searchParams.get("edit");
const isEditMode = !!editPurchaseId;

const { data: editPurchase } = useQuery<PurchaseOut>({
  queryKey: ["purchase", editPurchaseId],
  queryFn: () => api.get<PurchaseOut>(`/api/v1/purchases/${editPurchaseId}`),
  enabled: isEditMode,
});

useEffect(() => {
  if (editPurchase) {
    setManualSupplierId(editPurchase.supplier_id ?? "");
    setManualPurchaseTime(toLocalInputValue(editPurchase.purchase_time));
    setManualItems(
      editPurchase.items.map((it) => ({
        name: it.name,
        quantity: it.quantity,
        unit: it.unit ?? "",
        unit_price: it.unit_price,
        category: it.category ?? "",
        brand: it.brand ?? "",
      }))
    );
  }
}, [editPurchase]);
```

- [ ] **Step 6: Branch saveMut on edit mode**

Find the existing `manualSaveMut` definition (the manual-mode save mutation). It currently always POSTs:

```typescript
const manualSaveMut = useMutation({
  mutationFn: async () => {
    const body = {
      supplier_id: manualSupplierId || null,
      purchase_time: manualPurchaseTime ? new Date(manualPurchaseTime).toISOString() : null,
      items: manualItems.filter(...).map(...),
    };
    return api.post("/api/v1/purchases", body);
  },
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["purchases"] });
  },
});
```

Replace the `mutationFn` + `onSuccess` to branch on edit mode:

```typescript
const manualSaveMut = useMutation({
  mutationFn: async () => {
    const body = {
      supplier_id: manualSupplierId || null,
      purchase_time: manualPurchaseTime ? new Date(manualPurchaseTime).toISOString() : null,
      manual_adjustment: isEditMode ? true : undefined,
      items: manualItems
        .filter((i) => i.name.trim() && i.unit_price)
        .map((i) => ({
          name: i.name.trim(),
          quantity: (i.quantity || "1").trim() || "1",
          unit: i.unit?.trim() || null,
          unit_price: i.unit_price,
          category: i.category?.trim() || null,
          brand: i.brand?.trim() || null,
        })),
    };
    if (isEditMode && editPurchaseId) {
      return api.put(`/api/v1/purchases/${editPurchaseId}`, body);
    }
    return api.post("/api/v1/purchases", body);
  },
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["prices"] });
    if (isEditMode && editPurchaseId) {
      qc.invalidateQueries({ queryKey: ["purchase", editPurchaseId] });
      navigate("/");
    }
  },
});
```

Note: `manual_adjustment: isEditMode ? true : undefined` — when undefined, JSON.stringify omits the key, so POST creates new purchase with default `false`. When `true`, PUT marks the purchase as manually adjusted.

- [ ] **Step 7: Add loading state for edit-mode purchase fetch**

Right after the existing hooks (after the `useEffect` from Step 5), add:

```typescript
const isLoadingPurchase = isEditMode && !editPurchase;
```

Then add a loading return at the top of the component's return statement (before the main `<div className="max-w-3xl">`):

Find the `return (` of the component. Right after it, before `<div className="max-w-3xl">`, insert:

```tsx
if (isLoadingPurchase) {
  return (
    <div className="max-w-3xl">
      <p className="text-sm text-slate-500">加载采购单...</p>
    </div>
  );
}
```

- [ ] **Step 8: Conditional rendering — title, mode toggle, action buttons**

Find the existing `<h2 className="mb-4 text-xl font-bold">记账</h2>` line.

Replace with:
```tsx
<h2 className="mb-4 text-xl font-bold">{isEditMode ? "编辑记录" : "记账"}</h2>
```

Find the segmented control `<div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">...</div>`. Wrap it in a conditional so it only renders when NOT in edit mode:

```tsx
{!isEditMode && (
  <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
    {/* existing two buttons */}
  </div>
)}
```

For the manual-mode save button (find the existing `<button type="button" ... onClick={() => { if (!manualSaveMut.isPending) manualSaveMut.mutate(); }}>` for manual save), update its rendering to show "取消" + "保存修改" in edit mode:

Find (around the manual save button):
```tsx
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
                  onClick={() => {
                    if (!manualSaveMut.isPending) manualSaveMut.mutate();
                  }}
                  disabled={!manualCanSave}
                >
                  {manualPhase === "saving" ? "保存中…" : "保存"}
                </button>
              </div>
```

Replace with:
```tsx
              <div className="mt-4 flex justify-end gap-2">
                {isEditMode && (
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                    onClick={() => navigate("/")}
                  >
                    取消
                  </button>
                )}
                <button
                  type="button"
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
                  onClick={() => {
                    if (!manualSaveMut.isPending) manualSaveMut.mutate();
                  }}
                  disabled={!manualCanSave}
                >
                  {manualPhase === "saving"
                    ? "保存中…"
                    : isEditMode
                      ? "保存修改"
                      : "保存"}
                </button>
              </div>
```

- [ ] **Step 9: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -5
```

Expected: builds clean.

- [ ] **Step 10: Commit**

```bash
git add apps/web/src/pages/EntryPage.tsx apps/web/src/api/client.ts
git commit -m "feat(web): EntryPage edit mode — prefill from purchase, PUT on save"
```

(Drop `apps/web/src/api/client.ts` from the add line if it wasn't modified.)

---

### Task 4: End-to-end smoke

**Files:** None (verification only)

- [ ] **Step 1: Restart dev servers**

```bash
taskkill //F //IM python.exe 2>&1 | tail -3
cd D:/workspace/kitchen-project && pnpm dev
```

- [ ] **Step 2: Verify backend via curl**

```bash
# Create a purchase with 1 item
CREATE_RESP=$(curl -s -X POST http://localhost:3000/api/v1/purchases -H "Content-Type: application/json" -d '{"items":[{"name":"test-tomato","quantity":"1","unit_price":"5"}]}')
PID=$(echo "$CREATE_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "purchase id: $PID"

# PUT replace items with 2 new ones
curl -s -X PUT "http://localhost:3000/api/v1/purchases/$PID" -H "Content-Type: application/json" -d '{"items":[{"name":"test-a","quantity":"1","unit_price":"1"},{"name":"test-b","quantity":"2","unit_price":"2"}]}' | python -c "import sys,json; d=json.load(sys.stdin); print(f'after PUT: {len(d[\"items\"])} items, names={[i[\"name\"] for i in d[\"items\"]]}')"

# Verify GET returns the updated items
curl -s "http://localhost:3000/api/v1/purchases/$PID" | python -c "import sys,json; d=json.load(sys.stdin); print(f'after GET: {len(d[\"items\"])} items')"
```

Expected:
- After PUT: 2 items, names = ['test-a', 'test-b']
- After GET: 2 items (original 'test-tomato' is gone)

- [ ] **Step 3: Browser walkthrough**

Open `http://localhost:5173/`. Verify:

1. Dashboard shows recent purchases (auto-loads)
2. Each row's 操作 column has TWO buttons: ✎ (edit) and ✕ (delete)
3. Click ✎ on any row → confirm dialog "编辑将打开该记录所属采购单的全部内容，是否继续？"
4. Click 取消 in confirm → nothing happens (stay on dashboard)
5. Click ✎ again → 确认 → navigate to `/entry?edit=xxx`
6. Brief "加载采购单..." → form appears pre-filled with the purchase's items
7. Page title is "编辑记录" (not "记账")
8. No mode toggle (segmented control hidden)
9. "取消" button visible next to "保存修改"
10. Modify a field (e.g., change quantity of an item)
11. Click "+ 添加一行" → new empty row appears
12. Fill the new row's name + unit_price
13. Click 保存修改 → button shows "保存中…" → navigate back to `/`
14. Dashboard table refreshes, showing updated row data + new item

- [ ] **Step 4: Cancel path**

Repeat edit flow but click 取消 instead of 保存修改. Should navigate back to `/` without saving.

- [ ] **Step 5: Edge case — clear all items**

Edit a purchase, delete all item rows via ItemEditor's ✕ buttons (until list is empty).
Verify: 保存修改 button is disabled (manualCanSave = false). Cannot save 0 items.

- [ ] **Step 6: Run full backend test suite**

```bash
cd D:/workspace/kitchen-project/apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: 98 passed (was 95, +3 new from Task 1).

- [ ] **Step 7: Verify Docker images still build**

```bash
cd D:/workspace/kitchen-project && docker build -f Dockerfile.api -t kitchen-api:smoke . 2>&1 | tail -3
docker build -f Dockerfile.web -t kitchen-web:smoke . 2>&1 | tail -3
docker image rm kitchen-api:smoke kitchen-web:smoke
```

- [ ] **Step 8: Commit nothing (verification only)**

If defects found and fixed, commit those. Otherwise nothing.

---

## Self-Review

### Spec coverage

Mapping each spec section to a task:

- §1 background → plan goal
- §2 decisions table:
  - Edit scope = whole purchase → Task 1 (PUT replaces items) + Task 3 (EntryPage edit mode loads purchase)
  - Confirm dialog → Task 2 Step 3 (handleEdit with window.confirm)
  - Extend existing PUT → Task 1 (no new endpoint)
  - items=[] protected by frontend → Task 3 (`manualCanSave` disables button when no valid items)
  - Mode toggle hidden in edit → Task 3 Step 8 (conditional `{!isEditMode && ...}`)
  - Navigate to / on success → Task 3 Step 6 (onSuccess: navigate("/"))
  - 取消 button → Task 3 Step 8
  - Title "编辑记录" → Task 3 Step 8
  - Save button "保存修改" → Task 3 Step 8
  - Direct URL access works → Task 3 Step 5 (useQuery with enabled flag)
- §3 architecture → Task 1 (backend) + Task 2 (DashboardPage) + Task 3 (EntryPage)
- §3.2 data flow → all three tasks contribute
- §4 API contract → Task 1 Step 4 (handler change matches spec behavior)
- §5 frontend UI → Task 2 (✎ button) + Task 3 (edit mode rendering)
- §6 error handling → Task 3 Step 6 (onError via mutation, plus loading state)
- §7 testing → Task 1 (3 new tests) + Task 4 (E2E smoke)
- §8 未决问题:
  - api.put helper existence → Task 3 Step 1 explicitly checks ✅
  - toLocalInputValue helper → Task 3 Step 4 ✅
  - useEffect deps → Task 3 Step 5 uses `[editPurchase]` ✅
  - 取消 navigate behavior → Task 3 Step 8 implements ✅
  - manual_adjustment hardcoded true → Task 3 Step 6 ✅

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO"
- All code blocks have actual content
- Backend test code in Task 1 Step 1 is complete + runnable
- Frontend code in Task 3 Steps 1-8 are full snippets, not pseudocode
- Migration to verify: implementer reads client.ts first (Task 3 Step 1) before deciding to modify

### Type consistency

- `PurchaseOut` TS type in Task 3 Step 3 matches the backend Pydantic `PurchaseOut` fields (Task 1 implicitly, schema is unchanged in structure — only `PurchaseUpdate` got new `items` field)
- `PurchaseOutItem` TS type matches `PurchaseItemOut` Pydantic shape (id, name, quantity, unit, unit_price, category, brand)
- `editPurchaseId: string | null` (from `searchParams.get(...)`) — Task 3 uses this consistently
- `isEditMode: boolean` — derived once, used in 4+ places (title, toggle visibility, save branch, button label)
- `manual_adjustment: isEditMode ? true : undefined` — `undefined` causes JSON.stringify to omit the key, ensuring POST behavior unchanged
- `handleEdit(purchaseId: string)` in Task 2 matches `navigate(`/entry?edit=${purchase_id}`)` URL pattern, which Task 3's `searchParams.get("edit")` reads back

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-25-dashboard-edit-purchase.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 4 well-bounded tasks. Task 1 is pure backend TDD, Tasks 2-3 are pure frontend, Task 4 is smoke.

**2. Inline Execution** — Current session, batch with checkpoints.

Which approach?
