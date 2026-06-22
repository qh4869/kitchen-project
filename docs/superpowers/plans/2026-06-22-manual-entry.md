# Manual Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual bookkeeping mode (no photo) alongside the existing OCR flow on a renamed `/entry` route; update nav label from "拍照记账" to "记账".

**Architecture:** Pure frontend change — backend `POST /api/v1/purchases` already supports no-image creation. One page (`EntryPage`) hosts a segmented control toggling between photo mode (current OCR flow, unchanged) and manual mode (form → `POST /api/v1/purchases`). The ItemEditor component and supplier/datetime/total form fields are reused from the OCR edit phase.

**Tech Stack:** React 18 + TypeScript + TanStack Query v5 + Tailwind v3. No backend changes, no new tests.

**Reference spec:** `docs/superpowers/specs/2026-06-22-manual-entry-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/web/src/pages/UploadPage.tsx` | Rename to `EntryPage.tsx` | Page host + segmented control + photo mode (existing) + manual mode (new) |
| `apps/web/src/App.tsx` | Modify | Import `EntryPage`, change route `/upload` → `/entry`, change nav label "拍照记账" → "记账" |
| `apps/web/src/pages/PurchasesPage.tsx` | Modify (1 line) | Empty-state copy "拍照记账" → "记账" |
| `apps/api/**` | **No changes** | — |

---

## Tasks

### Task 1: Rename route + files + labels (mechanical plumbing)

**Files:**
- Rename: `apps/web/src/pages/UploadPage.tsx` → `apps/web/src/pages/EntryPage.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/pages/PurchasesPage.tsx`

This task does NOT add new functionality — it only renames and relabels. The OCR flow should work exactly as before, just at `/entry` instead of `/upload`.

- [ ] **Step 1: Rename the file**

Run from repo root:

```bash
cd D:/workspace/kitchen-project
git mv apps/web/src/pages/UploadPage.tsx apps/web/src/pages/EntryPage.tsx
```

- [ ] **Step 2: Rename the default export function inside EntryPage.tsx**

Open `apps/web/src/pages/EntryPage.tsx`. Find:

```tsx
export default function UploadPage() {
```

Replace:

```tsx
export default function EntryPage() {
```

- [ ] **Step 3: Update App.tsx — import, route, nav label**

Open `apps/web/src/App.tsx`. Three changes:

Find:
```tsx
import UploadPage from "./pages/UploadPage";
```
Replace:
```tsx
import EntryPage from "./pages/EntryPage";
```

Find:
```tsx
  { to: "/upload", label: "拍照记账", end: false, page: "upload" },
```
Replace:
```tsx
  { to: "/entry", label: "记账", end: false, page: "entry" },
```

Find:
```tsx
          <Route path="/upload" element={<UploadPage />} />
```
Replace:
```tsx
          <Route path="/entry" element={<EntryPage />} />
```

- [ ] **Step 4: Update PurchasesPage.tsx empty-state copy**

Open `apps/web/src/pages/PurchasesPage.tsx`. Find (around line 81):

```tsx
                  暂无采购记录。点击左侧"拍照记账"添加第一条。
```

Replace:

```tsx
                  暂无采购记录。点击左侧"记账"添加第一条。
```

- [ ] **Step 5: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully (no TS errors). 88 modules transformed.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/pages/EntryPage.tsx apps/web/src/App.tsx apps/web/src/pages/PurchasesPage.tsx
git commit -m "refactor(web): rename /upload → /entry, nav label 拍照记账 → 记账"
```

---

### Task 2: Add manual mode (the actual feature)

**Files:**
- Modify: `apps/web/src/pages/EntryPage.tsx`

This task adds the `Mode` state, segmented control UI, and manual mode form. Photo mode behavior is preserved unchanged.

- [ ] **Step 1: Read current EntryPage.tsx for reference**

Run: `cat apps/web/src/pages/EntryPage.tsx` (or open in editor)

Familiarize yourself with the current structure. Key pieces to preserve:
- State: `phase`, `imageKey`, `previewUrl`, `errorMsg`, `supplierId`, `purchaseTime`, `totalAmount`, `items`, `rawLlm`, `dirty`
- Mutations: `ocrMut`, `saveMut`
- Query: `suppliers` via `useQuery`
- Helper: `ocrErrorText`, `itemFromOcr`, `num`

- [ ] **Step 2: Replace the entire EntryPage.tsx**

Overwrite `apps/web/src/pages/EntryPage.tsx` with the following complete file. This file:
- Keeps photo mode 100% unchanged (just wrapped in `mode === 'photo'` conditional)
- Adds `mode` state + segmented control at top
- Adds manual mode form (reuses supplier/time/total/ItemEditor pattern)
- Adds `nowLocalDateTime()` helper for default time (avoids UTC→local display bug)
- Adds `switchMode()` that resets all state when switching

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import ImageUploader from "../components/ImageUploader";
import ItemEditor, { type Item } from "../components/ItemEditor";

type Mode = "photo" | "manual";

type Supplier = { id: string; name: string };
type OcrItem = {
  name: string;
  quantity?: string | number | null;
  unit?: string | null;
  unit_price?: string | number | null;
  category?: string | null;
  brand?: string | null;
};
type OcrResult = {
  image_key: string;
  supplier_name: string | null;
  purchase_time: string | null;
  total_amount: string | null;
  items: OcrItem[];
  raw_llm_output: Record<string, unknown>;
  provider: string;
};

type PhotoPhase = "idle" | "uploaded" | "recognizing" | "recognized" | "failed" | "saving" | "saved";
type ManualPhase = "idle" | "saving" | "saved" | "error";

const num = (v: unknown): string =>
  v === null || v === undefined || v === "" ? "" : String(v);

const itemFromOcr = (it: OcrItem): Item => ({
  name: it.name ?? "",
  quantity: num(it.quantity),
  unit: it.unit ?? "",
  unit_price: num(it.unit_price),
  category: it.category ?? "",
  brand: it.brand ?? "",
});

function nowLocalDateTime(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const EMPTY_ITEM: Item = {
  name: "",
  quantity: "1",
  unit: "",
  unit_price: "",
  category: "",
  brand: "",
};

export default function EntryPage() {
  const qc = useQueryClient();

  // --- Mode (segmented control) ---
  const [mode, setMode] = useState<Mode>("photo");

  // --- Photo mode state (unchanged from original UploadPage) ---
  const [photoPhase, setPhotoPhase] = useState<PhotoPhase>("idle");
  const [imageKey, setImageKey] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [photoErrorMsg, setPhotoErrorMsg] = useState<string | null>(null);

  const [photoSupplierId, setPhotoSupplierId] = useState<string>("");
  const [photoPurchaseTime, setPhotoPurchaseTime] = useState<string>("");
  const [photoTotalAmount, setPhotoTotalAmount] = useState<string>("");
  const [photoItems, setPhotoItems] = useState<Item[]>([]);
  const [photoRawLlm, setPhotoRawLlm] = useState<Record<string, unknown>>({});
  const [photoDirty, setPhotoDirty] = useState(false);

  // --- Manual mode state (new) ---
  const [manualSupplierId, setManualSupplierId] = useState<string>("");
  const [manualPurchaseTime, setManualPurchaseTime] = useState<string>(nowLocalDateTime());
  const [manualTotalAmount, setManualTotalAmount] = useState<string>("");
  const [manualItems, setManualItems] = useState<Item[]>([{ ...EMPTY_ITEM }]);
  const [manualDirty, setManualDirty] = useState(false);

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/api/v1/suppliers"),
  });

  // --- Photo mode mutations (unchanged) ---
  const ocrMut = useMutation({
    mutationFn: async (key: string) =>
      api.post<OcrResult>("/api/v1/ocr/extract", { image_key: key }),
    onMutate: () => {
      setPhotoPhase("recognizing");
      setPhotoErrorMsg(null);
    },
    onSuccess: (r) => {
      setImageKey(r.image_key);
      setPhotoRawLlm(r.raw_llm_output);
      setPhotoItems(r.items.map(itemFromOcr));
      setPhotoTotalAmount(num(r.total_amount));
      setPhotoPhase("recognized");
      if (r.items.length === 0) {
        setPhotoErrorMsg("未识别到任何商品信息，请重拍或改手工录入");
        setPhotoPhase("failed");
      }
    },
    onError: (e: ApiError) => {
      setPhotoErrorMsg(ocrErrorText(e));
      setPhotoPhase("failed");
    },
  });

  const photoSaveMut = useMutation({
    mutationFn: async () => {
      const body = {
        image_key: imageKey,
        supplier_id: photoSupplierId || null,
        purchase_time: photoPurchaseTime ? new Date(photoPurchaseTime).toISOString() : null,
        total_amount: photoTotalAmount || null,
        ocr_raw: photoRawLlm,
        manual_adjustment: photoDirty,
        items: photoItems
          .filter((i) => i.name.trim() && i.unit_price)
          .map((i) => ({
            name: i.name.trim(),
            quantity: i.quantity || "1",
            unit: i.unit || null,
            unit_price: i.unit_price,
            category: i.category || null,
            brand: i.brand || null,
          })),
      };
      return api.post("/api/v1/purchases/from-ocr", body);
    },
    onMutate: () => {
      setPhotoPhase("saving");
      setPhotoErrorMsg(null);
    },
    onSuccess: () => {
      setPhotoPhase("saved");
      qc.invalidateQueries({ queryKey: ["purchases"] });
    },
    onError: (e: ApiError) => {
      setPhotoErrorMsg(`保存失败：${e.detail}`);
      setPhotoPhase("recognized");
    },
  });

  // --- Manual mode mutation (new) ---
  const manualSaveMut = useMutation({
    mutationFn: async () => {
      const body = {
        supplier_id: manualSupplierId || null,
        purchase_time: manualPurchaseTime
          ? new Date(manualPurchaseTime).toISOString()
          : null,
        total_amount: manualTotalAmount || null,
        items: manualItems
          .filter((i) => i.name.trim() && i.unit_price)
          .map((i) => ({
            name: i.name.trim(),
            quantity: i.quantity || "1",
            unit: i.unit || null,
            unit_price: i.unit_price,
            category: i.category || null,
            brand: i.brand || null,
          })),
      };
      return api.post("/api/v1/purchases", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["purchases"] });
    },
  });

  // --- Mode switching ---
  const resetPhotoState = () => {
    setPhotoPhase("idle");
    setImageKey(null);
    setPreviewUrl(null);
    setPhotoErrorMsg(null);
    setPhotoSupplierId("");
    setPhotoPurchaseTime("");
    setPhotoTotalAmount("");
    setPhotoItems([]);
    setPhotoRawLlm({});
    setPhotoDirty(false);
  };

  const resetManualState = () => {
    setManualSupplierId("");
    setManualPurchaseTime(nowLocalDateTime());
    setManualTotalAmount("");
    setManualItems([{ ...EMPTY_ITEM }]);
    setManualDirty(false);
  };

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    resetPhotoState();
    resetManualState();
    setMode(next);
  };

  // Manual mode phase is derived from mutation state
  const manualPhase: ManualPhase = manualSaveMut.isPending
    ? "saving"
    : manualSaveMut.isSuccess
      ? "saved"
      : manualSaveMut.isError
        ? "error"
        : "idle";

  const manualErrorMsg = manualSaveMut.isError
    ? `保存失败：${(manualSaveMut.error as ApiError).detail}`
    : null;

  const manualCanSave =
    !manualSaveMut.isPending &&
    manualItems.filter((i) => i.name.trim() && i.unit_price).length > 0;

  return (
    <div className="max-w-3xl">
      <h2 className="mb-4 text-xl font-bold">记账</h2>

      {/* Segmented control */}
      <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
        <button
          type="button"
          onClick={() => switchMode("photo")}
          className={`rounded-md px-4 py-1.5 text-sm transition-colors ${
            mode === "photo"
              ? "bg-white text-emerald-700 font-medium shadow-sm"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          📷 拍照
        </button>
        <button
          type="button"
          onClick={() => switchMode("manual")}
          className={`rounded-md px-4 py-1.5 text-sm transition-colors ${
            mode === "manual"
              ? "bg-white text-emerald-700 font-medium shadow-sm"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          ✍️ 手工
        </button>
      </div>

      {mode === "photo" ? (
        <>
          {/* ============ PHOTO MODE (unchanged from original UploadPage) ============ */}
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
            {photoPhase === "idle" ? (
              <ImageUploader
                onUploaded={(key, url) => {
                  setImageKey(key);
                  setPreviewUrl(url);
                  setPhotoPhase("uploaded");
                  ocrMut.mutate(key);
                }}
              />
            ) : (
              <div className="flex items-start gap-4">
                {previewUrl && (
                  <img
                    src={previewUrl}
                    alt="预览"
                    className="h-32 rounded border border-slate-200 object-contain"
                  />
                )}
                <div className="flex-1 text-sm">
                  {photoPhase === "uploaded" && <p className="text-slate-500">准备识别…</p>}
                  {photoPhase === "recognizing" && <p className="text-slate-500">🔍 识别中…</p>}
                  {photoPhase === "recognized" && (
                    <p className="text-emerald-600">✓ 识别完成，可编辑后保存</p>
                  )}
                  {photoPhase === "failed" && photoErrorMsg && (
                    <p className="text-red-600">{photoErrorMsg}</p>
                  )}
                  {photoPhase === "saving" && <p className="text-slate-500">保存中…</p>}
                  {photoPhase === "saved" && (
                    <p className="text-emerald-600">✓ 已保存，可继续上传下一张</p>
                  )}
                  <div className="mt-2 flex gap-2">
                    <button
                      className="rounded border border-slate-300 px-3 py-1 text-xs"
                      onClick={resetPhotoState}
                    >
                      重新上传
                    </button>
                    {photoPhase === "failed" && (
                      <>
                        <button
                          className="rounded bg-emerald-600 px-3 py-1 text-xs text-white"
                          onClick={() => imageKey && ocrMut.mutate(imageKey)}
                          disabled={!imageKey}
                        >
                          重试识别
                        </button>
                        <button
                          className="rounded border border-emerald-600 px-3 py-1 text-xs text-emerald-700"
                          onClick={() => {
                            setPhotoPhase("recognized");
                            setPhotoErrorMsg(null);
                          }}
                        >
                          改手工录入
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>

          {(photoPhase === "recognized" ||
            photoPhase === "saving" ||
            photoPhase === "saved") && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">供应商</span>
                  <select
                    className="rounded border border-slate-300 px-2 py-1"
                    value={photoSupplierId}
                    onChange={(e) => {
                      setPhotoSupplierId(e.target.value);
                      setPhotoDirty(true);
                    }}
                  >
                    <option value="">— 不选 —</option>
                    {suppliers?.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">采购时间</span>
                  <input
                    type="datetime-local"
                    className="rounded border border-slate-300 px-2 py-1"
                    value={photoPurchaseTime}
                    onChange={(e) => {
                      setPhotoPurchaseTime(e.target.value);
                      setPhotoDirty(true);
                    }}
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">总额 (¥)</span>
                  <input
                    type="number"
                    step="0.01"
                    className="rounded border border-slate-300 px-2 py-1"
                    value={photoTotalAmount}
                    onChange={(e) => {
                      setPhotoTotalAmount(e.target.value);
                      setPhotoDirty(true);
                    }}
                  />
                </label>
              </div>

              <ItemEditor
                items={photoItems}
                onChange={(next) => {
                  setPhotoItems(next);
                  setPhotoDirty(true);
                }}
              />

              <div className="mt-4 flex justify-end gap-2">
                <button
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  onClick={() => photoSaveMut.mutate()}
                  disabled={
                    photoSaveMut.isPending ||
                    photoItems.filter((i) => i.name && i.unit_price).length === 0
                  }
                >
                  {photoSaveMut.isPending ? "保存中…" : "保存"}
                </button>
              </div>
            </section>
          )}
        </>
      ) : (
        <>
          {/* ============ MANUAL MODE (new) ============ */}
          {manualPhase === "saved" ? (
            <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center">
              <p className="text-emerald-700">✓ 已保存</p>
              <button
                type="button"
                onClick={() => {
                  manualSaveMut.reset();
                  resetManualState();
                }}
                className="mt-3 rounded border border-emerald-600 px-4 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
              >
                新建一条
              </button>
            </section>
          ) : (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">供应商</span>
                  <select
                    className="rounded border border-slate-300 px-2 py-1"
                    value={manualSupplierId}
                    onChange={(e) => {
                      setManualSupplierId(e.target.value);
                      setManualDirty(true);
                    }}
                  >
                    <option value="">— 不选 —</option>
                    {suppliers?.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">采购时间</span>
                  <input
                    type="datetime-local"
                    className="rounded border border-slate-300 px-2 py-1"
                    value={manualPurchaseTime}
                    onChange={(e) => {
                      setManualPurchaseTime(e.target.value);
                      setManualDirty(true);
                    }}
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-slate-600">总额 (¥)</span>
                  <input
                    type="number"
                    step="0.01"
                    className="rounded border border-slate-300 px-2 py-1"
                    value={manualTotalAmount}
                    onChange={(e) => {
                      setManualTotalAmount(e.target.value);
                      setManualDirty(true);
                    }}
                  />
                </label>
              </div>

              <ItemEditor
                items={manualItems}
                onChange={(next) => {
                  setManualItems(next);
                  setManualDirty(true);
                }}
              />

              {manualErrorMsg && (
                <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  {manualErrorMsg}
                </div>
              )}

              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:bg-slate-400"
                  onClick={() => manualSaveMut.mutate()}
                  disabled={!manualCanSave}
                >
                  {manualPhase === "saving" ? "保存中…" : "保存"}
                </button>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ocrErrorText(e: ApiError): string {
  if (e.status === 504 && e.detail.includes("OCR_TIMEOUT")) {
    return "OCR 超时（30s），请重试或换一张清晰的图";
  }
  if (e.detail.includes("OCR_PARSE_ERROR")) {
    return "OCR 服务异常（结果解析失败），请稍后再试";
  }
  if (e.detail.includes("OCR_UPSTREAM_ERROR")) {
    return "OCR 服务异常，请稍后再试";
  }
  return `OCR 失败：${e.detail}`;
}
```

- [ ] **Step 3: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully. The bundle will be slightly larger (~240 kB vs 225 kB) due to the manual mode code.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/EntryPage.tsx
git commit -m "feat(web): add manual entry mode to /entry page"
```

---

### Task 3: End-to-end smoke

**Files:** None (verification only)

- [ ] **Step 1: Ensure DB + API are running**

If `kitchen-postgres` is not up: `pnpm db:up`.

If dev API isn't running, or if you see stale behavior from prior uvicorn runs (Windows quirk — see CLAUDE.md), fully kill Python first:

```bash
taskkill //F //IM python.exe 2>&1 | tail -3
```

Then start:

```bash
cd D:/workspace/kitchen-project && pnpm dev
```

Wait ~6 seconds. Probe `http://localhost:3000/health` — should return `{"status":"ok"}`.

- [ ] **Step 2: Photo mode regression check (via browser)**

Open `http://localhost:5173/entry`. Verify:
1. Page title is "记账" (no camera emoji)
2. Segmented control visible with two buttons: "📷 拍照" (active, white background) and "✍️ 手工" (inactive, grey)
3. Click "📷 拍照" → existing OCR flow (upload zone visible)
4. Upload a receipt photo → OCR runs → edit form appears → save → success message + record in `/` (采购记录)

Expected: photo mode behavior identical to before the rename.

- [ ] **Step 3: Manual mode happy path**

Click "✍️ 手工". Verify:
1. Form appears directly (no upload zone)
2. 采购时间 field auto-fills with current local time (not 8 hours off)
3. 供应商 dropdown shows "— 不选 —" + any suppliers you have
4. 总额 field is empty
5. ItemEditor shows one empty row
6. Save button is disabled (no name+price yet)

Fill in:
- 供应商: pick any
- Item row 1: name="番茄", quantity="1.5", unit="kg", unit_price="6.5"
- Click "+ 添加一行"
- Item row 2: name="鸡蛋", quantity="10", unit="个", unit_price="1.2"
- 总额: "19.50"

Click 保存. Verify:
- Button label changes to "保存中…" briefly
- Green "✓ 已保存" banner appears with "新建一条" button
- Navigate to `/` (采购记录) — new purchase appears with item_count=2, total_amount=19.50

- [ ] **Step 4: Manual mode empty-input disabling**

Click "新建一条" (resets form). Verify save button is disabled again (no name+price).

- [ ] **Step 5: Manual mode error path**

Stop the dev API server (Ctrl+C in its terminal). Try to save a manual entry. Verify:
- Red banner appears: "保存失败：..." (network error message)

Restart API: `pnpm dev:api` (or `pnpm dev`).

- [ ] **Step 6: Mode switching clears state**

In manual mode, fill in some items (don't save). Click "📷 拍照". Verify:
- Upload zone appears (photo mode)
- Click "✍️ 手工" again — form is reset to empty (one blank row, time = now)

- [ ] **Step 7: Nav label + empty-state copy**

Open `/` (采购记录) in a fresh state (or visually inspect the sidebar). Verify:
- Sidebar shows "记账" (not "拍照记账")
- Click it → URL is `/entry` (not `/upload`)

If 采购记录 has 0 rows, verify empty-state text reads "点击左侧"记账"添加第一条" (with curly quotes around 记账).

- [ ] **Step 8: Run full backend test suite (regression check)**

Run: `cd D:/workspace/kitchen-project/apps/api && python -m uv run pytest`
Expected: 91 passed (or 91 + integration passed = 92, depending on whether `LLM_API_KEY` is set). No regressions — backend was unchanged.

- [ ] **Step 9: Commit nothing (verification only)**

If any defect was found and fixed during smoke, commit those fixes. Otherwise nothing to commit.

---

## Self-Review

### Spec coverage

- §1 background / scope → covered by plan goal/architecture
- §2 decisions table → each decision mapped:
  - Rename route `/upload` → `/entry` → Task 1 Step 3
  - Nav label "拍照记账" → "记账" → Task 1 Step 3
  - mode segmented control → Task 2 (mode state + UI in code)
  - Default mode = photo → Task 2 (`useState<Mode>("photo")`)
  - Mode switch clears form → Task 2 (`switchMode` calls `resetPhotoState` + `resetManualState`)
  - Default time = local now → Task 2 (`nowLocalDateTime()` helper)
  - Save endpoint = `/api/v1/purchases` → Task 2 (`manualSaveMut` posts there)
  - Success state = "✓ 已保存" + "新建一条" → Task 2 (manual `saved` branch)
- §3 architecture → Task 1 (rename) + Task 2 (single file with conditional rendering)
- §3.2 component structure → Task 2 (inline `mode === 'photo' ? ... : ...`)
- §3.3 data flow → Task 2 (`manualSaveMut` payload matches spec)
- §4 UI contract → Task 2 (segmented control code matches §4.1; default values match §4.2; phase derivation matches §4.3)
- §5 error handling → Task 2 (`manualCanSave` disables button; `manualErrorMsg` renders red banner; `saved` state shows green)
- §6 testing strategy → Task 3 (E2E smoke covers all 6 scenarios in §6)
- §7 未决问题:
  - mode state persistence → v1 uses `useState` (not localStorage) ✅
  - datetime-local timezone → Task 2 uses `nowLocalDateTime()` helper ✅
  - saved → idle reset → Task 2 "新建一条" button calls `manualSaveMut.reset()` + `resetManualState()` ✅

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO" / "implement later"
- Task 2 has full file content (not additions-only)
- Task 3 has specific verification steps with expected outcomes
- No "similar to Task N" — all code shown inline

### Type consistency

- `Mode = "photo" | "manual"` defined once in Task 2, used consistently
- `PhotoPhase` and `ManualPhase` are separate types (avoids invalid state combinations)
- `EMPTY_ITEM` constant defined once, reused via `{ ...EMPTY_ITEM }` spread
- `nowLocalDateTime()` helper defined once, called in `useState` initializer and `resetManualState`
- `manualSaveMut` variable name consistent across definition, `onClick`, `manualPhase` derivation, `manualCanSave`
- All `setManualX` setters match their corresponding `manualX` state variables
- `switchMode(next: Mode)` parameter type matches `Mode` type
- Item type imported from `../components/ItemEditor` (unchanged from original)

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-22-manual-entry.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks. 3 well-bounded tasks (mechanical rename → feature addition → smoke).

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
