# 设计：ItemEditor 手机横向滚动

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-26
**关联**：[Phase 3.7 编辑购买](./2026-06-25-dashboard-edit-purchase-design.md)

## 1. 背景

手机（尤其竖屏）打开 `/entry` 手工记账页时，`ItemEditor` 是 7 列表格（名称 / 数量 / 单位 / 单价 / 类目 / 品牌 / ✕），每列被挤到 ~50px，名称输入框完全不可读，无法正常录入商品名。

用户已确认走 **"表格加横向滚动"** 方案（不做卡片重排、不开启 pinch-zoom）。

## 2. 决策

| 决策 | 结论 | 理由 |
|---|---|---|
| 方案 | 表格 `overflow-x-auto` + `min-w-[680px]` | 用户已选；改动最小 |
| 最小宽度 | 680px | 7 列 + padding 后的舒适阅读宽度（名称 120 + 数量 64 + 单位 56 + 单价 80 + 类目 80 + 品牌 80 + ✕ 40 + padding ≈ 600px，680px 留 buffer） |
| 是否同步改 DashboardPage | 否 | 用户只提了手工记账页；DashboardPage 是只读表格，问题不严重；scope 外 |
| viewport meta | 不改 | 浏览器默认已允许 pinch-zoom；不需要 |

## 3. 实现

`apps/web/src/components/ItemEditor.tsx` 两处 className 改动：

```diff
- <div className="overflow-hidden rounded-lg border border-slate-200">
-   <table className="w-full text-sm">
+ <div className="overflow-x-auto rounded-lg border border-slate-200">
+   <table className="w-full text-sm min-w-[680px]">
```

仅此而已。

## 4. 行为变化

| 场景 | 改前 | 改后 |
|---|---|---|
| 桌面（≥768px） | 表格铺满父容器 | 无可见变化（680px < 父容器宽度，无滚动条） |
| 手机横屏（~667px） | 列宽被挤到 ~50px | 表格保 680px，容器横向滚动，列宽正常 |
| 手机竖屏（~360px） | 同上更糟 | 同上，需要更多滑动 |

## 5. 验证

- `pnpm build:web` 通过
- 浏览器 DevTools 切 iPhone SE (375×667) 视图：表格容器底部出现横向滚动条，每列宽度恢复正常，名称输入框可见可输入
- 桌面视图无可见差别

## 6. 不做

- 响应式卡片重排（之前推荐的 Option B）
- 同步修复 DashboardPage（scope 外）
- 滚动指示器 / 返回顶部按钮
- 任何后端 / 测试改动
