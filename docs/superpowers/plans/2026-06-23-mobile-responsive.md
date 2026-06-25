# Mobile Responsive UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 224px text sidebar with 64px emoji-only icon rail (Slack/Discord style) + let wide tables scroll horizontally instead of clipping; verify mobile upload now has enough space.

**Architecture:** Pure CSS className changes — no new components, no new deps, no breakpoint logic. Three files touched (~10 line diff). Sidebar shrinks from `w-56 p-4` to `w-16 p-2`, nav items render emoji + native `title` tooltip instead of text, main drops `overflow-x-hidden` for `overflow-x-auto` + responsive padding, two table wrappers follow the same overflow pattern.

**Tech Stack:** React 18 + Tailwind v3. No tests (pure UI).

**Reference spec:** `docs/superpowers/specs/2026-06-23-mobile-responsive-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/web/src/App.tsx` | Modify | Sidebar → icon rail; main → responsive padding + scroll |
| `apps/web/src/pages/DashboardPage.tsx` | Modify | Table wrapper overflow-hidden → overflow-x-auto |
| `apps/web/src/components/ItemEditor.tsx` | Modify | Table wrapper overflow-hidden → overflow-x-auto |

Zero new files, zero new deps.

---

## Tasks

### Task 1: App.tsx — icon rail + responsive main

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Read current App.tsx for reference**

Run: `cat apps/web/src/App.tsx`

Current shape: `navItems` array has 4 entries each with `{ to, label, end, page }` (no icon). Sidebar uses `w-56 p-4`, renders text labels. Main is `flex-1 overflow-x-hidden p-6`.

- [ ] **Step 2: Overwrite App.tsx**

Overwrite `apps/web/src/App.tsx` with:

```tsx
import { NavLink, Route, Routes } from "react-router-dom";
import SuppliersPage from "./pages/SuppliersPage";
import PurchasesPage from "./pages/PurchasesPage";
import EntryPage from "./pages/EntryPage";
import DashboardPage from "./pages/DashboardPage";

const navItems = [
  { to: "/", label: "采购记录", icon: "📋", end: true, page: "purchases" },
  { to: "/entry", label: "记账", icon: "📷", end: false, page: "entry" },
  { to: "/suppliers", label: "供应商", icon: "🏪", end: false, page: "suppliers" },
  { to: "/dashboard", label: "价格仪表盘", icon: "💰", end: false, page: "dashboard" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-16 shrink-0 border-r border-slate-200 bg-white p-2">
        <div
          className="mb-4 px-2 py-2 text-center text-2xl"
          title="烹饪助手 · 智慧采购"
        >
          🍳
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              className={({ isActive }) =>
                `flex justify-center rounded-md px-2 py-3 text-xl ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {item.icon}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-x-auto p-3 md:p-6">
        <Routes>
          <Route path="/" element={<PurchasesPage />} />
          <Route path="/entry" element={<EntryPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

Changes from current:
1. `navItems` array: added `icon` field to each entry (📋 / 📷 / 🏪 / 💰)
2. `<aside>`: `w-56 p-4` → `w-16 p-2`
3. Logo block: text `<h1>烹饪助手</h1><p>智慧采购 · v0.1</p>` → single `🍳` emoji with `title` attribute carrying the full app name
4. `<NavLink>`: added `title={item.label}` attribute; class changed from `px-3 py-2 text-sm` to `flex justify-center px-2 py-3 text-xl`; child changed from `{item.label}` to `{item.icon}`
5. `<main>`: `overflow-x-hidden p-6` → `overflow-x-auto p-3 md:p-6`

- [ ] **Step 3: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully (88 modules, ~230 kB).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/App.tsx
git commit -m "feat(web): icon rail sidebar + responsive main padding"
```

---

### Task 2: Table wrappers — overflow-hidden → overflow-x-auto

**Files:**
- Modify: `apps/web/src/pages/DashboardPage.tsx`
- Modify: `apps/web/src/components/ItemEditor.tsx`

- [ ] **Step 1: Patch DashboardPage.tsx**

Open `apps/web/src/pages/DashboardPage.tsx`. Find the success-state table wrapper (around line 113):

```tsx
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
```

Replace the wrapper className:

```tsx
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
```

(Only `overflow-hidden` → `overflow-x-auto`. Everything else in the file unchanged.)

- [ ] **Step 2: Patch ItemEditor.tsx**

Open `apps/web/src/components/ItemEditor.tsx`. Find the outer wrapper div (around line 3):

```tsx
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-sm">
```

Replace the wrapper className:

```tsx
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-sm">
```

(Only `overflow-hidden` → `overflow-x-auto`.)

- [ ] **Step 3: Build to verify TS compiles**

Run: `cd D:/workspace/kitchen-project && pnpm build:web`
Expected: builds successfully (88 modules, ~230 kB).

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/DashboardPage.tsx apps/web/src/components/ItemEditor.tsx
git commit -m "feat(web): wide tables scroll horizontally instead of clipping"
```

---

### Task 3: End-to-end smoke (no code changes)

**Files:** None

- [ ] **Step 1: Ensure dev servers running**

If not running, or if you see stale behavior on Windows (per CLAUDE.md):

```bash
taskkill //F //IM python.exe 2>&1 | tail -3
cd D:/workspace/kitchen-project && pnpm dev
```

Wait ~6 seconds. Probe `http://localhost:3000/health` and `http://localhost:5173/`.

- [ ] **Step 2: Desktop browser walkthrough (≥ 1024px)**

Open `http://localhost:5173/`. Verify:
1. Sidebar on left is 64px wide (4 fingers visually narrow)
2. Logo block shows a single 🍳 emoji (no text)
3. 4 emoji icons vertically stacked: 📋 / 📷 / 🏪 / 💰
4. Current page's icon is highlighted with emerald-50 background + emerald-700 text color
5. Hover any icon for ~0.5s — browser shows a small tooltip with the Chinese label ("采购记录" etc.)
6. Click each icon — navigates to the right route, active state moves correctly
7. Main content area has comfortable padding (24px)

- [ ] **Step 3: Mobile viewport walkthrough (iPhone SE 375 × 667)**

Open Chrome DevTools → Toggle Device Toolbar → iPhone SE.

Verify on each page:
- **`/` 采购记录**: cards display full-width, sidebar takes only 64px, no horizontal page scroll
- **`/entry` 记账**:
  - Photo mode: upload dropzone has plenty of horizontal room (~295px wide minus padding). Click triggers file picker (in DevTools mobile emulation, behaves like desktop file picker — that's expected; on a real phone it'd offer camera/album)
  - Switch to "✍️ 手工" mode: 3-column form (supplier/time/total) stacks to single column
  - Add 3+ items to ItemEditor: table is wider than viewport → horizontal scrollbar appears below table, swipe scrolls it left/right
- **`/suppliers`**: list displays normally
- **`/dashboard` 价格查询**:
  - On first load: table of recent 50 items appears (auto-load from earlier change)
  - If table is wider than viewport, horizontal scroll works
  - Search box + button are reachable, button not clipped

- [ ] **Step 4: Edge cases**

- Tap an emoji (mobile) — should navigate (same as click). Touch target ≥ 48×48px (py-3 = 12px top + 12px bottom + text-xl ≈ 24px line height ≈ 48px total).
- Resize browser window from 1500px down to 375px — sidebar stays at 64px throughout (no breakpoint jump). Main padding transitions at `md` (768px).
- Long-press an emoji on mobile (real device, not DevTools) — native `title` tooltip shows.

- [ ] **Step 5: Run backend test suite (regression check)**

```bash
cd D:/workspace/kitchen-project/apps/api && python -m uv run pytest 2>&1 | tail -5
```

Expected: 92 passed (unchanged — no backend touched). The pre-existing `datetime.utcnow()` deprecation warnings may appear, that's known.

- [ ] **Step 6: Commit nothing (verification only)**

If any defect found and fixed, commit those. Otherwise nothing to commit.

---

## Self-Review

### Spec coverage

- §1 background / scope → plan goal
- §2 decisions table → each decision mapped:
  - icon rail (64px) → Task 1 Step 2 (`w-16 p-2`)
  - emoji icons → Task 1 Step 2 (navItems.icon + render `{item.icon}`)
  - native title attribute → Task 1 Step 2 (`title={item.label}` on NavLink)
  - horizontal scroll for tables → Task 2 (overflow-x-auto)
  - responsive padding → Task 1 Step 2 (`p-3 md:p-6` on main)
  - ImageUploader unchanged → Task 3 Step 3 verifies upload still works (no code touch)
  - no new deps / no icon library → confirmed in plan structure (zero Create: directives)
- §3 architecture → Task 1 (App.tsx full code) + Task 2 (table wrappers)
- §3.2 navItems icon mapping → Task 1 Step 2 (📋 / 📷 / 🏪 / 💰)
- §3.3 sidebar改造细节 → Task 1 Step 2 verbatim
- §3.4 main改造 → Task 1 Step 2 (`overflow-x-auto p-3 md:p-6`)
- §3.5 表格 wrapper → Task 2 (both files)
- §4 不需要改的部分 → Task 3 Step 3 verifies ImageUploader works through the new layout (no code touch)
- §5 视觉验证 → Task 3 Step 2 (desktop) + Step 3 (iPhone SE) + Step 4 (edge cases)
- §6 已知限制 → acknowledged in plan, none require code action
- §7 测试策略 → no new tests, manual verification in Task 3
- §8 未决问题:
  - logo emoji 🍳 → baked into Task 1 Step 2 (no decision deferred)
  - no tiny version text → baked into Task 1 Step 2 (no `<p>v0.1</p>`)

No spec gaps.

### Placeholder scan

- No "TBD" / "TODO" / "implement later"
- Task 1 Step 2 shows the complete new App.tsx verbatim
- Task 2 shows the exact find/replace for both files
- Task 3 has specific verification steps with expected outcomes
- No "similar to Task N" — each task self-contained

### Type consistency

- `navItems` array shape: `{ to, label, icon, end, page }` — same in Task 1 Step 2 as referenced everywhere
- NavLink props unchanged from current (`to`, `end`, `className`, `children`) — only added `title`
- Emoji glyphs (📋 / 📷 / 🏪 / 💰 / 🍳) consistent across plan and spec
- Tailwind class names (`w-16`, `p-2`, `text-xl`, `overflow-x-auto`) consistent in Task 1 and Task 2
- All commits use `feat(web):` scope prefix consistently

No mismatches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-mobile-responsive.md`. Two execution options:

**1. Subagent-Driven (recommended)** — 3 well-bounded tasks. Each produces self-contained commits.

**2. Inline Execution** — Current session, batch with checkpoints.

Which approach?
