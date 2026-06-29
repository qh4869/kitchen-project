# 设计：手机版导航改顶部栏 + 抽屉

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-29
**关联**：无（独立改动；用户在手机上用了一段时间后反馈侧栏占位过大）

## 1. 背景

`apps/web/src/App.tsx` 当前用固定 `w-56`（224px）的左侧 sidebar 作为全局导航（首页 / 记账 / 供应商），所有视口宽度下都展开。

在 375px 宽的手机上，sidebar 占 224px 后内容区只剩 151px，所有页面（Dashboard 表格、Entry 表单、Suppliers 表格）被严重挤压。已经用 [ItemEditor 横向滚动](./2026-06-26-item-editor-horizontal-scroll-design.md) 这种局部 band-aid 缓解过 `/entry` 的表格，但根本原因是导航布局没区分桌面 / 移动。

用户已确认走 **"只改手机版，PC 不动"** 的方向，并且选择 **"顶部栏 + ☰ 抽屉"** 的导航模式（在 A 底部 Tab / B 抽屉 / C 顶部 Tab 三选一时选 B）。

## 2. 决策

| 决策 | 结论 | 理由 |
|---|---|---|
| 改动范围 | 只加 `< 768px` 的响应式层；`≥ 768px` 维持现状 | 用户明确选 "PC 不动"；最小风险 |
| 桌面/移动断点 | `md`（768px） | Tailwind 默认；与 ItemEditor `min-w-[680px]` 接近，过渡自然 |
| 移动导航模式 | 顶部 42px app bar + 左滑抽屉 | 用户已选 B 方案 |
| 抽屉宽度 | 75% 视口宽（约 280px @ 375 视口） | 标准做法；保留右侧 25% 露出主内容作"半模态"提示 |
| 抽屉动画时长 | 200ms ease-out | 业界标准；快到不阻塞、慢到看得见 |
| 遮罩不透明度 | `bg-black/45` | iOS / Material 通用值 |
| 关闭方式 | 点遮罩 / 点 nav 项 / 再点 ☰ / ESC | 四种全支持，符合直觉 |
| 页面标题来源 | 按当前路由写死一张映射表 | 3 条路由足够简单，不需要服务端 / 复杂逻辑 |
| 当前页高亮 | 抽屉内 emerald 高亮（与 PC sidebar 完全一致） | 复用 NavLink 的 isActive 逻辑 |
| 抽屉打开时是否锁 body 滚动 | 是 | 避免抽屉背后内容也跟着滚 |

## 3. 实现

### 3.1 文件改动

| 路径 | 操作 | 内容 |
|---|---|---|
| `apps/web/src/App.tsx` | 修改 | 加路由→标题映射；Layout 加 mobile 分支：`<md:` 渲染 MobileShell（顶部栏 + Drawer），`≥md:` 维持现状 |
| `apps/web/src/components/MobileNav.tsx` | 新建 | 顶部栏 + 抽屉组件；props: `currentPath`，自管 `drawerOpen` state |

### 3.2 MobileNav 组件结构

```tsx
type Props = { currentPath: string };

const TITLE_MAP: Record<string, string> = {
  "/": "价格查询",
  "/entry": "记账",
  "/suppliers": "供应商管理",
};

export default function MobileNav({ currentPath }: Props) {
  const [open, setOpen] = useState(false);
  const title = TITLE_MAP[currentPath] ?? "";

  // ESC 关闭 + body 滚动锁
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* 顶部栏 */}
      <header className="md:hidden sticky top-0 z-30 flex h-[42px] items-center gap-2 border-b border-slate-200 bg-white px-3.5">
        <button onClick={() => setOpen(true)} aria-label="打开菜单" className="text-xl leading-none px-1">☰</button>
        <span className="flex-1 text-[13px] font-semibold text-slate-900">{title}</span>
      </header>

      {/* 抽屉 + 遮罩 */}
      {open && (
        <div className="md:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/45" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-3/4 max-w-[320px] bg-white p-3.5 shadow-xl flex flex-col animate-[slideIn_.2s_ease-out]">
            {/* 品牌区 */}
            <div className="mb-4 border-b border-slate-100 px-1 pb-3">
              <h1 className="text-base font-bold">烹饪助手</h1>
              <p className="text-xs text-slate-500">智慧采购 · v0.1</p>
            </div>
            {/* 导航 */}
            <nav className="flex flex-col gap-0.5">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2 text-sm ${
                      isActive ? "bg-emerald-50 text-emerald-700 font-medium" : "text-slate-600 hover:bg-slate-100"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="mt-auto px-1 py-2 text-[10px] text-slate-400">v0.1 · 2026</div>
          </aside>
        </div>
      )}
    </>
  );
}
```

### 3.3 App.tsx 改动

```diff
  export default function App() {
+   const location = useLocation();
    return (
-     <div className="flex min-h-screen">
+     <div className="flex min-h-screen">
+       {/* Mobile: 顶部栏（仅 <md 显示） */}
+       <MobileNav currentPath={location.pathname} />
+
        {/* Desktop: 左侧 sidebar（仅 ≥md 显示） */}
-       <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
+       <aside className="hidden md:block w-56 shrink-0 border-r border-slate-200 bg-white p-4">
          {/* ... 原内容不变 ... */}
        </aside>
+       {/* Mobile: 内容区从顶部 42px 下方开始；Desktop: 维持现状 */}
-       <main className="flex-1 overflow-x-hidden p-6">
+       <main className="flex-1 overflow-x-hidden p-4 md:p-6">
          {/* ... 路由不变 ... */}
        </main>
      </div>
    );
  }
```

要点：
- Desktop sidebar 加 `hidden md:block`（`<md` 时彻底不渲染、不占位）
- `<main>` 内边距 `p-4 md:p-6`（手机更紧凑）
- `MobileNav` 内的所有元素都用 `md:hidden` 前缀，`≥md` 时不渲染
- 因为 flex 容器是 `flex`（默认 `flex-row`），而 MobileNav 的根 `<header>` 是 `sticky`，需要把 MobileNav 放在 flex 容器外层或用 absolute 定位 —— 实现时用「fixed/sticky 顶部栏 + main 加 top padding」更简单，避开 flex 子项的复杂度。具体取舍在 plan 里定。

### 3.4 动画 keyframes

`apps/web/src/index.css` 加：

```css
@keyframes slideIn {
  from { transform: translateX(-100%); }
  to   { transform: translateX(0); }
}
```

## 4. 行为变化

| 场景 | 改前 | 改后 |
|---|---|---|
| 桌面 ≥768px | 224px sidebar + 内容 | 无可见变化 |
| 手机 <768px | 224px sidebar + 151px 内容 | 42px 顶部栏 + 全宽内容；点 ☰ 弹 75% 宽抽屉 |
| 手机切换页面 | 点 sidebar 项 → 即时切换 | 点 ☰ → 抽屉 → 点 nav 项 → 抽屉关 + 切换 |
| 手机抽屉打开时背景 | — | 45% 黑遮罩；点遮罩 / 点 nav 项 / ESC / 再点 ☰ 关闭 |
| 手机抽屉打开时 body 滚动 | — | 锁定（`overflow: hidden`） |
| ItemEditor `min-w-[680px]` | 手机要横滑才能看完 7 列 | 不变（已确认不动 ItemEditor） |

## 5. 验证

- `pnpm build:web` 通过（无 TS 错误）
- 浏览器 DevTools 切设备：
  - **iPhone SE (375×667)**：顶部栏 42px，☰ 可点开抽屉，抽屉 75% 宽约 280px，遮罩半透，点遮罩关闭，点 nav 项跳转并关闭，ESC 关闭，打开时背景不滚动
  - **iPad Mini (768×1024)**：≥md 断点，显示左侧 sidebar，与改前一致
  - **桌面 (1440×900)**：与改前完全一致
- /、/entry、/suppliers 三个路由下，顶部栏标题分别是 "价格查询" / "记账" / "供应商管理"
- 抽屉中当前页用 emerald 高亮（与 PC sidebar 一致）
- 进入 `/entry?edit={id}` 时标题仍为 "记账"（query string 不影响 pathname 匹配）

## 6. 边界 case

- **路由不存在时**：`TITLE_MAP` 取不到值 → 标题为空字符串。当前所有路由都在表内，无 fallback 需求。
- **抽屉打开时切换路由（非通过点 nav 项）**：用浏览器后退键切换时抽屉不自动关。`useEffect` 监听 `location.pathname` 变化时也关一下，作为兜底。
- **超窄视口（< 320px）**：抽屉 `w-3/4 max-w-[320px]` 在 280px 视口下仍是 210px（75%），可读；不需要额外处理。

## 7. 不做

- ❌ 改桌面 sidebar（保持现状）
- ❌ 改 ItemEditor 表格（已单独解决横向滚动）
- ❌ 改 DashboardPage / EntryPage / SuppliersPage 内部布局（这些页面的"在手机上是否能用好"是独立议题，本期不动；先把全局导航改对）
- ❌ 底部 Tab 栏（用户选了 B 不是 A）
- ❌ 抽屉内的二级菜单 / 分组（只有 3 个 nav 项，YAGNI）
- ❌ 抽屉打开时焦点陷阱（focus trap）—— 移动端无障碍场景很少；YAGNI
- ❌ 抽屉手势滑动关闭（左滑关抽屉）—— 增加实现复杂度，用户没要求
- ❌ 任何后端 / API 改动
