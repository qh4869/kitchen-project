# 设计：手机端响应式 UI 改造

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-23
**关联**：现有 UI 在桌面端工作正常，手机端侧边栏占 224px 把主内容挤没

## 1. 背景与目标

当前 `App.tsx` 用固定 `w-56`（224px）左侧 sidebar，在手机屏幕（iPhone SE 375px）上占去 60% 宽度，主内容只剩 ~150px 不可用。具体后果：
- 上传区域（ImageUploader）被挤到一窄条，手机用户感觉"传不上去"
- 表格（DashboardPage 结果、EntryPage 商品明细）超出宽度被 `overflow-x-hidden` 裁掉
- nav 文字 + 图标横向挤，每个 NavLink 高度也偏小不易点中

目标：让同一份代码在桌面和手机上都可用，**不引入断点逻辑**（一套 JSX + CSS 适配所有宽度）。

**本期范围**：
- 侧边栏从 `w-56 p-4` 改 `w-16 p-2`，nav 项变为图标 + native `title` tooltip
- 主内容 `overflow-x-hidden p-6` → `overflow-x-auto p-3 md:p-6`
- 两处表格 wrapper `overflow-hidden` → `overflow-x-auto`

**显式不做（延后）**：
- 自定义 hover tooltip 组件（用 native `title` 属性，零 JS）
- 卡片式列表替代表格（`overflow-x-auto` 横向滚动够用）
- 引入图标库（emoji 与 codebase 风格一致）
- 改路由 / 改 nav 数量
- ItemEditor 列数调整（7 列在手机上横向滚动可接受）

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 统一策略 | 左侧 icon 导航栏（Slack/Discord 风格） | 桌面 + 手机同一份代码无断点；64px 比 224px 节省 70% 横向空间；改动最小 |
| 图标选型 | emoji | 现有 codebase 各处都用 emoji（OCR 提示、空状态、按钮），保持一致；不引依赖 |
| Label 显示方式 | native HTML `title` 属性 | 零 JS 零 CSS；hover 0.5s 显示中文标签；触屏长按也能触发 |
| 表格在手机上的处理 | 横向滚动（`overflow-x-auto`） | 改 1 行 CSS；卡片式要写两套组件，YAGNI |
| 主内容 padding | `p-3 md:p-6` 响应式 | 手机 12px 够用，桌面保持 24px 视觉留白 |
| 上传组件改动 | **不改** | 已有 `accept="image/*" capture="environment"`，技术上工作；之前问题来自侧边栏挤压，导航改了自然解决 |

## 3. 架构

### 3.1 改动文件

| 路径 | 改动 |
|---|---|
| `apps/web/src/App.tsx` | sidebar 改 icon rail；main 改 padding + overflow |
| `apps/web/src/pages/DashboardPage.tsx` | 表格 wrapper `overflow-hidden` → `overflow-x-auto` |
| `apps/web/src/components/ItemEditor.tsx` | 表格 wrapper `overflow-hidden` → `overflow-x-auto` |

零新文件、零新依赖。

### 3.2 nav 项 icon 映射

需要在 `App.tsx` 的 `navItems` 数组里加 `icon` 字段：

```tsx
const navItems = [
  { to: "/", label: "采购记录", icon: "📋", end: true, page: "purchases" },
  { to: "/entry", label: "记账", icon: "📷", end: false, page: "entry" },
  { to: "/suppliers", label: "供应商", icon: "🏪", end: false, page: "suppliers" },
  { to: "/dashboard", label: "价格仪表盘", icon: "💰", end: false, page: "dashboard" },
];
```

渲染时 `<NavLink>` 加 `title={item.label}` + 子元素改成 `<div className="text-xl">{item.icon}</div>`。

### 3.3 sidebar 改造细节

```tsx
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
```

变化点：
- `w-56` → `w-16`（224px → 64px）
- `p-4` → `p-2`
- logo 文本 → 单个 🍳 emoji（带 `title` 显示完整应用名）
- NavLink 子元素：`{label}` → `{icon}`（文字到 emoji）
- NavLink className：去掉 `text-sm`，加 `text-xl px-2 py-3 flex justify-center`（让图标居中、触摸目标 ≥44px）
- 加 `title={item.label}` 属性

### 3.4 主内容区改造

```tsx
<main className="flex-1 overflow-x-auto p-3 md:p-6">
```

- `overflow-x-hidden` → `overflow-x-auto`：宽表格可以横向滚动
- `p-6` → `p-3 md:p-6`：手机端 12px padding（更多内容空间），桌面保持 24px

### 3.5 表格 wrapper 改造

**`DashboardPage.tsx`**：
```diff
- <div className="overflow-hidden rounded-lg border border-slate-200">
+ <div className="overflow-x-auto rounded-lg border border-slate-200">
```

**`components/ItemEditor.tsx`**：
```diff
- <div className="overflow-hidden rounded-lg border border-slate-200">
+ <div className="overflow-x-auto rounded-lg border border-slate-200">
```

注：`overflow-x-auto` 会保留外层的 `rounded-lg` + `border` 视觉，只是允许内部 `<table>` 横向滚动。

## 4. 不需要改的部分（验证清单）

- **`ImageUploader.tsx`**：`accept="image/*" capture="environment"` 已就绪。手机浏览器（iOS Safari、Chrome Android、微信内置）会调起相机或相册选择器。
- **`EntryPage.tsx` 的 3 列 form 网格**：已经用 `grid-cols-1 md:grid-cols-3`，手机单列、桌面三列。
- **`PurchasesPage.tsx`**：列表已经是卡片式，响应式天然支持。
- **`SuppliersPage.tsx`**：列表布局，宽度自适应。
- **所有按钮 / 输入框的 `text-sm` (14px) 字号**：移动端可读、可点。

## 5. 视觉与交互验证

### 5.1 桌面端（≥ 1024px）

- nav 在左侧 64px 宽，4 个 emoji 图标垂直排列
- 当前活动页对应图标 emerald 高亮 + emerald-50 背景
- hover 图标 0.5s 后浏览器显示中文 label tooltip（native title）
- 主内容区从 64px 后开始，留白正常
- 表格在桌面宽屏下不会触发横向滚动（内容能放下）

### 5.2 手机端（iPhone SE 375px）

- nav 占 64px，主内容区剩 ~295px
- nav 图标触摸目标 `px-2 py-3 text-xl` ≈ 48px 高 × 48px 宽，超过 iOS 44px / Android 48dp 推荐最小值
- `/` 采购记录：卡片列表正常显示
- `/entry` 记账：
  - 拍照模式：上传区域 (flex-1) ~231px 宽，正常可点
  - 手工模式：3 列 form 自动堆成单列（已 responsive）
  - ItemEditor 表格超宽时横向滚动
- `/suppliers`：列表正常
- `/dashboard` 价格查询：搜索 form 正常，结果表横向滚动
- 主内容 padding 12px，比之前 24px 多出 24px 横向空间

### 5.3 平板（768px - 1024px）

- nav 64px + 主内容 ~700-960px，体验介于手机和桌面之间
- 表格在中等宽度下可能仍有横向滚动，可接受

## 6. 已知限制

- **`title` 属性的 tooltip 不能定制样式**：浏览器原生的（黄色背景、小字号）。桌面端 hover 0.5s 触发，手机端长按 emoji 触发。够用，不漂亮。如果以后想做得更精致（如 React 组件 tooltip），是另一个工作量。
- **表格横向滚动在小屏上不优雅**：用户要左右滑才能看完所有列。但比当前 `overflow-hidden` 把内容裁掉好太多。卡片式列表（每行变卡片）是 Phase 5+ 的工作。
- **侧边栏在超宽屏（≥1920px）下显得"瘦"**：64px 在 1920px 屏上占比 3%。可以接受；如果想优化，加 `md:w-16 lg:w-20` 让稍宽，但本期不做。
- **`hover:bg-slate-100`** 在触屏上点一下也会触发"hover"状态残留（CSS hover 在 mobile 上的已知行为），但下一个 nav 点击其他地方会自动清除。无影响。

## 7. 测试策略

**无新单元测试**：纯 CSS className 改动，没业务逻辑变化。

**手动验证**：
1. `pnpm build:web` 通过
2. 桌面 Chrome：sidebar 64px 宽，4 个图标，hover 显示 label
3. Chrome DevTools 切 iPhone SE (375 × 667)：
   - nav 占 64px，主内容可正常滚动
   - 4 个页面都能正常显示，无横向溢出（除非主动滚动表格）
   - `/entry` 上传区域足够宽，点上传调起文件选择器（devtools 模拟下是普通文件选择）
4. 真机验证（可选）：手机浏览器打开 dev server IP，实际拍照上传测一遍 OCR 流程

## 8. 未决问题（实现时可决策）

- **应用 logo emoji**：当前 mockup 用 🍳（煎蛋）。也可以选 🥘（砂锅）、👨‍🍳（厨师）、🥬（蔬菜）。选哪个不影响功能，建议 🍳 跟"烹饪助手" 主题对得上。
- **是否在 logo 下加 tiny 文字**：当前完全去掉文字。如果觉得"光一个 emoji 不知道是什么应用"，可以在 emoji 下加 8px 字号的 "v0.1" 标记。倾向不加 —— `title` 属性已经提供完整应用名 tooltip。
