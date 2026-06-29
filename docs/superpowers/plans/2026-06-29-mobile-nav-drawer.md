# Mobile Nav Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mobile-only (< 768px) navigation layer to the web app — top app bar (42px) with ☰ button that opens a left slide-in drawer containing the same 3 nav links as the PC sidebar. Desktop (≥ 768px) sidebar layout stays untouched.

**Architecture:** React fragment at the top of `App.tsx` renders `<MobileNav>` (which returns nothing on desktop, since every element inside is `md:hidden`) as a sibling of the existing `flex` container. `MobileNav` owns `drawerOpen` state and exposes the top bar + drawer overlay. Shared `nav-items.ts` holds the link array so the PC sidebar and the mobile drawer stay in sync. CSS keyframe in `index.css` drives the 200ms slide-in.

**Tech Stack:** React 18 + TypeScript + Vite + TailwindCSS v3 + react-router-dom v6.

**Reference spec:** `docs/superpowers/specs/2026-06-29-mobile-nav-drawer-design.md`

**Testing note:** This project has no frontend test framework (no Jest/Vitest). Each task verifies via `pnpm build:web` (which runs `tsc -b && vite build` — catches type errors) and a final manual browser walkthrough in Task 5. TDD doesn't apply.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/web/src/nav-items.ts` | Create | Shared `navItems` array (link config), imported by `App.tsx` and `MobileNav.tsx` |
| `apps/web/src/index.css` | Modify | Add `slideIn` keyframe for drawer animation |
| `apps/web/src/components/MobileNav.tsx` | Create | Mobile-only top bar + drawer; owns `drawerOpen` state; ESC + body-scroll-lock + pathname-close effects |
| `apps/web/src/App.tsx` | Modify | Import `navItems` from shared module; add `<MobileNav>` + `useLocation`; sidebar `hidden md:block`; main padding `p-4 md:p-6` |

**Ordering rationale:**
- Task 1 (extract `navItems`) before Task 3 (MobileNav imports it) — clean module boundary first.
- Task 2 (CSS keyframe) can land anytime before Task 5; doing it early keeps the runtime animation working as soon as MobileNav exists.
- Task 3 (MobileNav) before Task 4 (wire into App) — App needs the component to import.
- Task 5 is pure manual verification, no commit.

---

## Tasks

### Task 1: Extract `navItems` to shared module

**Why first:** A pure refactor that should change zero behavior. Isolating it makes the subsequent diffs smaller and gives MobileNav a clean import target.

**Files:**
- Create: `apps/web/src/nav-items.ts`
- Modify: `apps/web/src/App.tsx`

**Note on the `page` field:** The current `navItems` array has a `page: "dashboard" | "entry" | "suppliers"` field that is **never read anywhere** (verified via grep). Drop it during extraction — it's dead config.

- [ ] **Step 1: Create `apps/web/src/nav-items.ts`**

Create the file with this exact content:

```typescript
export type NavItem = {
  to: string;
  label: string;
  end: boolean;
};

export const navItems: NavItem[] = [
  { to: "/", label: "首页", end: true },
  { to: "/entry", label: "记账", end: false },
  { to: "/suppliers", label: "供应商", end: false },
];
```

- [ ] **Step 2: Update `apps/web/src/App.tsx` to import from the shared module**

Open `apps/web/src/App.tsx`. Find this block at the top of the file (lines 1–10):

```typescript
import { NavLink, Route, Routes } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";

const navItems = [
  { to: "/", label: "首页", end: true, page: "dashboard" },
  { to: "/entry", label: "记账", end: false, page: "entry" },
  { to: "/suppliers", label: "供应商", end: false, page: "suppliers" },
];
```

Replace with:

```typescript
import { NavLink, Route, Routes } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";
import { navItems } from "./nav-items";
```

(The inline `navItems` const is deleted; the import replaces it. No other change in this file.)

- [ ] **Step 3: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -10
```

Expected: build succeeds with no errors. The `NavLink` usage in `App.tsx` still works because `navItems` items still have `to`, `end`, `label` — the dropped `page` field was never read.

- [ ] **Step 4: Commit**

```bash
cd D:/workspace/kitchen-project && git add apps/web/src/nav-items.ts apps/web/src/App.tsx && git commit -m "refactor(web): extract navItems to shared module"
```

---

### Task 2: Add `slideIn` keyframe

**Files:**
- Modify: `apps/web/src/index.css`

- [ ] **Step 1: Add the keyframe to `apps/web/src/index.css`**

Open `apps/web/src/index.css`. Current content:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply antialiased;
  }
}
```

Append the keyframe at the end of the file (do not touch the existing `@layer base` block):

```css

@keyframes slideIn {
  from { transform: translateX(-100%); }
  to   { transform: translateX(0); }
}
```

- [ ] **Step 2: Build to verify CSS still compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -10
```

Expected: build succeeds. CSS keyframes are passively defined — they don't trigger until referenced by `animate-[slideIn_...]` in Task 3.

- [ ] **Step 3: Commit**

```bash
cd D:/workspace/kitchen-project && git add apps/web/src/index.css && git commit -m "feat(web): add slideIn keyframe for mobile drawer"
```

---

### Task 3: Create `MobileNav` component

**Files:**
- Create: `apps/web/src/components/MobileNav.tsx`

**Note:** The `navItems` import path is `../nav-items` (file is at `apps/web/src/components/MobileNav.tsx`, nav-items is at `apps/web/src/nav-items.ts`).

- [ ] **Step 1: Create `apps/web/src/components/MobileNav.tsx`**

Create the file with this exact content:

```typescript
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { navItems } from "../nav-items";

type Props = { currentPath: string };

const TITLE_MAP: Record<string, string> = {
  "/": "价格查询",
  "/entry": "记账",
  "/suppliers": "供应商管理",
};

export default function MobileNav({ currentPath }: Props) {
  const [open, setOpen] = useState(false);
  const title = TITLE_MAP[currentPath] ?? "";

  // Close drawer whenever the route changes (covers browser back/forward
  // and any programmatic navigation that doesn't go through NavLink onClick).
  useEffect(() => {
    setOpen(false);
  }, [currentPath]);

  // ESC to close + lock body scroll while drawer is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Top app bar — only on mobile */}
      <header className="md:hidden sticky top-0 z-30 flex h-[42px] items-center gap-2 border-b border-slate-200 bg-white px-3.5">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="打开菜单"
          className="px-1 text-xl leading-none"
        >
          ☰
        </button>
        <span className="flex-1 text-[13px] font-semibold text-slate-900">
          {title}
        </span>
      </header>

      {/* Drawer + overlay — only rendered when open */}
      {open && (
        <div className="md:hidden fixed inset-0 z-50">
          {/* Dimmed backdrop; click closes */}
          <div
            className="absolute inset-0 bg-black/45"
            onClick={() => setOpen(false)}
          />

          {/* Drawer panel */}
          <aside className="absolute left-0 top-0 flex h-full w-3/4 max-w-[320px] animate-[slideIn_.2s_ease-out] flex-col bg-white p-3.5 shadow-xl">
            {/* Brand block — visually mirrors the PC sidebar */}
            <div className="mb-4 border-b border-slate-100 px-1 pb-3">
              <h1 className="text-base font-bold">烹饪助手</h1>
              <p className="text-xs text-slate-500">智慧采购 · v0.1</p>
            </div>

            {/* Nav links — emerald active state matches PC sidebar */}
            <nav className="flex flex-col gap-0.5">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2 text-sm ${
                      isActive
                        ? "bg-emerald-50 font-medium text-emerald-700"
                        : "text-slate-600 hover:bg-slate-100"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="mt-auto px-1 py-2 text-[10px] text-slate-400">
              v0.1 · 2026
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 2: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -10
```

Expected: build succeeds. `MobileNav` is defined but not yet imported by `App.tsx` — that's fine; Vite/tree-shaking handles unused modules, and `tsc` doesn't error on exported-but-unused modules.

(If `tsc` complains about `MobileNav` being unused, ignore — it's a default export, not a local variable. Default exports don't trigger `noUnusedLocals`.)

- [ ] **Step 3: Commit**

```bash
cd D:/workspace/kitchen-project && git add apps/web/src/components/MobileNav.tsx && git commit -m "feat(web): add MobileNav component (top bar + drawer)"
```

---

### Task 4: Wire `MobileNav` into `App.tsx` + responsive classes

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Add `useLocation` import and `MobileNav` import**

Open `apps/web/src/App.tsx`. The current imports (after Task 1) look like:

```typescript
import { NavLink, Route, Routes } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";
import { navItems } from "./nav-items";
```

Add `useLocation` to the react-router-dom import and add the `MobileNav` import. Result:

```typescript
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import EntryPage from "./pages/EntryPage";
import SuppliersPage from "./pages/SuppliersPage";
import DashboardPage from "./pages/DashboardPage";
import MobileNav from "./components/MobileNav";
import { navItems } from "./nav-items";
```

- [ ] **Step 2: Wrap return in a fragment and render `<MobileNav>` as the first child**

The current `App()` return (after Task 1) is:

```tsx
export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
        {/* ... brand + nav ... */}
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

Replace the entire `App()` function body with:

```tsx
export default function App() {
  const location = useLocation();
  return (
    <>
      <MobileNav currentPath={location.pathname} />

      <div className="flex min-h-screen">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
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
                      ? "bg-emerald-50 font-medium text-emerald-700"
                      : "text-slate-600 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 overflow-x-hidden p-4 md:p-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/entry" element={<EntryPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
```

Three concrete changes from the original:
1. **Wrap return in `<>...</>**` (React fragment) so `MobileNav` and the `flex` container are siblings — not parent/child. This prevents the mobile `<header>` from becoming a horizontal flex child of the row.
2. **`<aside>` className gains `hidden md:block`** — sidebar hidden on mobile, shown on desktop. This is the only change to that element.
3. **`<main>` padding `p-6` → `p-4 md:p-6`** — tighter mobile padding, original desktop padding preserved.

- [ ] **Step 3: Build to verify TS compiles**

```bash
cd D:/workspace/kitchen-project && pnpm build:web 2>&1 | tail -10
```

Expected: build succeeds with no TS errors.

- [ ] **Step 4: Commit**

```bash
cd D:/workspace/kitchen-project && git add apps/web/src/App.tsx && git commit -m "feat(web): wire MobileNav into App, hide sidebar on mobile"
```

---

### Task 5: Browser walkthrough (no commit)

**Files:** none modified — verification only.

This is the only reliable way to catch visual / interaction regressions. `pnpm build:web` cannot verify drawer animation, sticky header behavior, or touch-target sizes.

- [ ] **Step 1: Start the dev server**

```bash
cd D:/workspace/kitchen-project && pnpm dev 2>&1 | head -20
```

Wait ~5 seconds for both api (3000) and web (5173) to come up. Open `http://localhost:5173/` in the browser.

- [ ] **Step 2: Desktop layout unchanged**

At default browser size (≥ 768px wide), confirm visually:
- Left sidebar (224px) is visible with brand + 3 nav items
- No top app bar (no ☰ button visible at top)
- No mobile drawer
- All three pages (`/`, `/entry`, `/suppliers`) render as before

- [ ] **Step 3: Open DevTools device emulator, set to iPhone SE (375 × 667)**

In Chrome DevTools: `Ctrl+Shift+M` to toggle device toolbar, pick "iPhone SE" from the dropdown.

Confirm at 375px width:
- Top app bar (42px tall) is visible at top: ☰ on left, "价格查询" on right
- Left sidebar is gone (no 224px sidebar eating space)
- Content area (`<main>`) uses the full 375px width minus padding
- Page is usable: dashboard table, entry form, suppliers list all fit horizontally (tables with `min-w-[680px]` will still scroll horizontally — that's expected per the spec, not a regression)

- [ ] **Step 4: Drawer open / close behaviors**

Tap ☰ in the top bar. Confirm:
- Drawer slides in from left over ~200ms (animation is visible, not instant)
- Drawer is ~280px wide (75% of 375px), white background, with brand "烹饪助手 / 智慧采购 · v0.1" at top, 3 nav items below, "v0.1 · 2026" at the bottom
- Active page (e.g. "首页" when on `/`) is highlighted emerald
- Backdrop is dimmed (~45% black); underlying page content is still partially visible to the right of the drawer

Close the drawer four ways, one at a time, reopening between each:
1. **Tap backdrop** — drawer disappears
2. **Tap a nav item** (e.g. 记账) — drawer closes AND page navigates to `/entry`. Top bar title changes to "记账".
3. **Press ESC key** — drawer closes
4. **(Skip "tap ☰ again"** — the ☰ button only opens, doesn't toggle. This matches the spec — `☰` has no `onClick` to close, only `setOpen(true)`. Document if this feels wrong; it's intentional per spec section 2.)

- [ ] **Step 5: Body scroll lock**

With drawer open, try scrolling the background page (two-finger swipe on the dimmed area, or mouse wheel over it). Confirm:
- Background page does NOT scroll while drawer is open
- After closing the drawer, background scrolls normally again

- [ ] **Step 6: Route-change fallback close**

Open drawer. Without tapping a nav item, use browser back button (or DevTools → click a link programmatically). Confirm drawer closes when `currentPath` changes.

- [ ] **Step 7: Test ≥ md / < md boundary**

In DevTools, resize viewport to exactly 768px wide. Confirm:
- Layout shows desktop sidebar (≥ md = 768px is inclusive)
- No mobile top bar

Resize to 767px. Confirm:
- Layout flips to mobile: top bar appears, sidebar hidden

- [ ] **Step 8: Page-specific title check**

Visit each route on mobile, confirm the top bar title:
- `/` → "价格查询"
- `/entry` → "记账"
- `/entry?edit=abc123` → "记账" (query string ignored — only pathname matters)
- `/suppliers` → "供应商管理"

- [ ] **Step 9: Stop dev server**

`Ctrl+C` in the terminal running `pnpm dev`. No commit needed — Task 5 made no code changes.

---

## Self-Review Checklist (run by author after writing plan)

- **Spec coverage:** Every decision in spec section 2 ("决策") maps to a task:
  - 改动范围 (mobile only) → Task 4 (`hidden md:block`)
  - 桌面/移动断点 (md=768px) → Task 4 (`md:block`, `md:p-6`)
  - 移动导航模式 (top bar + drawer) → Tasks 3 + 4
  - 抽屉宽度 (75% / max 320px) → Task 3 (`w-3/4 max-w-[320px]`)
  - 抽屉动画时长 (200ms ease-out) → Task 2 (keyframe) + Task 3 (`animate-[slideIn_.2s_ease-out]`)
  - 遮罩不透明度 (bg-black/45) → Task 3
  - 关闭方式 (4 ways) → Task 3 (onClick backdrop, NavLink onClick, ESC) + pathname effect; ✓
  - 页面标题来源 (TITLE_MAP) → Task 3
  - 当前页高亮 (emerald) → Task 3 (NavLink isActive)
  - body 滚动锁 → Task 3 (useEffect)
  - 路由变化兜底关 → Task 3 (useEffect on currentPath)

- **Edge cases (spec section 6):**
  - 路由不存在 → empty title (Task 3 `?? ""` covers it)
  - 超窄视口 → `w-3/4 max-w-[320px]` adapts (no special handling needed)
  - 浏览器后退键 → useEffect on currentPath (Task 3)

- **Placeholder scan:** None. Every code step has full code, every command has expected output.

- **Type consistency:** `NavItem` shape is consistent across `nav-items.ts` (Task 1) and `MobileNav.tsx` (Task 3, uses `navItems` import). `Props = { currentPath: string }` matches the call site `<MobileNav currentPath={location.pathname} />` in Task 4. `TITLE_MAP` keys match the three route paths exactly.

- **Scope check:** Single feature, single component addition. No backend changes. Sufficient for one plan.
