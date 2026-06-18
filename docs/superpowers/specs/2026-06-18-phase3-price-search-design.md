# Phase 3 设计：价格查询（v1 搜索）

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-18
**关联**：[Phase 2 OCR 设计](./2026-06-17-phase2-ocr-design.md)；PRD §2.A 价格仪表盘

## 1. 背景与目标

PRD §2.A 给"价格仪表盘"画了三件事：① 单品历史价格曲线 ② 跨店铺比价 ③ 搜索食材名返回最近价格 + 推荐店铺。本期 v1 只做**③ 的简化版**：搜索 → 表格展示最近 N 条匹配记录（价格 / 店铺 / 时间）。

理由：① 和 ② 都依赖"商品名归一化"（OCR 会把同一个番茄写成番茄 / 西红柿 / 番茄(有机)）和"单位归一化"（¥/kg vs ¥/500g vs ¥/个 不可比）。在归一化方案明确前先做曲线和比价，数据会乱。搜索场景下原始记录直出即可，归一化可后置。

**本期范围**：
- 新增 `GET /api/v1/prices/search` 端点
- 替换 `DashboardPage.tsx` 占位为搜索表单 + 结果表格
- 单元测试覆盖 SQL 构造、参数校验、空结果、错误响应

**显式不做（延后）**：
- 价格曲线 / 图表（Recharts 已装但不用）
- 跨店铺比价聚合
- "推荐店铺"算法
- 商品名归一化（番茄 ↔ 西红柿 ↔ 番茄(有机)）
- 单位归一化（¥/kg ↔ ¥/个 换算）
- 分页 / 虚拟滚动（数据量小，单页 50 条够用）
- URL query state（v1 不做可分享链接）
- 搜索防抖（输入触发，回车 / 按钮提交）

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| v1 范围 | 只做搜索 | ① ② 依赖归一化，归一化方案未定；搜索场景下原始数据可用 |
| 匹配方式 | `ILIKE '%q%'` 子串模糊 | 中文场景零配置；OCR 名字带括号 / 品种后缀也能匹配上 |
| 返回量 | 最近 50 条，按 `purchase_time DESC` | 家庭场景数据量小，无需分页；时间倒序最符合"近期"直觉 |
| 列结构 | 商品名 / 单价+单位 / 店铺 / 采购时间（4 列） | 商品名消歧（搜"番"区分番茄 / 番薯）；单价带单位才有上下文 |
| 未绑店铺 | 显示"—（未绑店铺）" | `purchases.supplier_id` 可空，不强行 INNER JOIN |
| API URL | `GET /api/v1/prices/search` | 独立命名空间，后期加 `/prices/history`、`/prices/compare` 互不干扰 |
| 触发方式 | 表单 onSubmit（回车 / 按钮） | v1 简单；防抖增加复杂度且对低频查询无收益 |
| UI 位置 | 替换 `DashboardPage.tsx` 占位，保留侧边栏标签 "价格仪表盘" | 后期曲线 / 比价同页扩展 |

## 3. 架构

### 3.1 模块新增

```text
apps/api/
├── app/
│   ├── routers/
│   │   └── prices.py               ← 新增：GET /search
│   ├── schemas/
│   │   └── price.py                ← 新增：SearchResultItem, SearchResult, SearchQuery
│   └── main.py                     ← 修改：注册 prices router
└── tests/
    └── test_prices_search.py       ← 新增：路由 + 校验 + 边界

apps/web/src/
├── pages/
│   └── DashboardPage.tsx           ← 修改：替换占位为搜索 UI
└── api/
    └── client.ts                   ← 不动（已有 api.get）
```

### 3.2 数据流

```
[DashboardPage]
  useQuery(['prices', q, limit], () => api.get('/api/v1/prices/search?q=...&limit=...'))
       ↓
[GET /api/v1/prices/search]
       ↓
[prices.search_handler]
  - 校验 q / limit → 422 if invalid
  - SQLAlchemy 2.0 async:
      SELECT pi.*, p.id, p.purchase_time, s.id, s.name
      FROM purchase_items pi
      JOIN purchases p ON pi.purchase_id = p.id
      LEFT JOIN suppliers s ON p.supplier_id = s.id
      WHERE pi.name ILIKE :pattern
      ORDER BY p.purchase_time DESC
      LIMIT :limit
  - 序列化为 SearchResult
       ↓
[Response 200]
```

`pattern = f"%{q.strip()}%"`，转义 `%` / `_` 字符避免用户输入污染模式（`q.replace('%', '\\%').replace('_', '\\_')`，配合 `ILIKE ... ESCAPE '\\'`）。

## 4. API 契约

### 4.1 请求

`GET /api/v1/prices/search?q=<str>&limit=<int>`

| 参数 | 类型 | 必填 | 默认 | 校验 |
|---|---|---|---|---|
| `q` | str | 是 | — | strip 后 1 ≤ len ≤ 100；否则 422 `INVALID_QUERY` |
| `limit` | int | 否 | 50 | 1 ≤ limit ≤ 200；否则 422 `INVALID_LIMIT` |

### 4.2 响应

**200 OK** — `SearchResult`：

```jsonc
{
  "query": "番茄",
  "count": 3,
  "items": [
    {
      "name": "番茄",
      "quantity": "1.5",
      "unit": "kg",
      "unit_price": "6.50",
      "category": "蔬菜",
      "brand": null,
      "supplier_id": "uuid-...",
      "supplier_name": "城南菜场",
      "purchase_id": "uuid-...",
      "purchase_time": "2026-06-17T09:32:29Z"
    }
  ]
}
```

字段说明：
- `quantity` / `unit_price` 序列化为字符串，避免 JS Number 精度问题（Decimal → str）
- `supplier_id` / `supplier_name` 在 `purchases.supplier_id` 为空时均为 `null`
- `purchase_time` 为 ISO 8601 with timezone（DB 列是 `DateTime(timezone=True)`）

**422 Unprocessable Entity**：

```jsonc
{ "detail": "INVALID_QUERY: query must be 1-100 chars after strip" }
// 或
{ "detail": "INVALID_LIMIT: limit must be 1-200" }
```

## 5. 前端

### 5.1 组件结构

`DashboardPage.tsx` 单文件实现，无子组件拆分（页面元素少）：

```
<form onSubmit={...}>
  <input value={q} onChange={...} placeholder="输入食材名，如 番茄 / 鸡蛋 / 五花肉" />
  <button disabled={isFetching || !q.trim()}>搜索</button>
</form>

{state === 'initial' && <HintBanner>提示：…</HintBanner>}
{state === 'loading' && <p>查询中…</p>}
{state === 'error'   && <ErrorBanner>{errorMsg}</ErrorBanner>}
{state === 'empty'   && <HintBanner>未找到 "…" 的采购记录…</HintBanner>}
{state === 'success' && <ResultTable items={data.items} />}
```

### 5.2 查询触发

- 表单 `onSubmit` 阻止默认行为，调用 `setQuery(submittedQ)`
- `useQuery` 的 `queryKey: ['prices', query]`，`enabled: !!query.trim()`
- 初始未搜索时不发请求（`query` 状态为空字符串）
- 重复搜索同一关键词 → TanStack Query 自动用缓存

### 5.3 结果表格

| 列 | 数据源 | 渲染 |
|---|---|---|
| 商品名 | `item.name` | 原样 |
| 单价 | `item.unit_price` + `item.unit` | `¥${unit_price} / ${unit \|\| '—'}` |
| 店铺 | `item.supplier_name` | 原样；null → `—（未绑店铺）` 灰色 |
| 采购时间 | `item.purchase_time` | `YYYY-MM-DD HH:mm`（去秒） |

## 6. 错误处理

| 场景 | 后端响应 | 前端展示 |
|---|---|---|
| 空 query | 422 `INVALID_QUERY` | 不应发生（前端 disabled 按钮），兜底 banner |
| limit 越界 | 422 `INVALID_LIMIT` | 同上（前端不暴露 limit 参数） |
| DB 连接失败 | 500（FastAPI 默认） | 红色 banner：`查询失败：网络异常，请稍后重试` |
| 0 条匹配 | 200 `{count: 0, items: []}` | 黄色 banner：`未找到 "{q}" 的采购记录…` |
| 网络断开 | fetch reject | 同 500 |

## 7. 测试策略

`tests/test_prices_search.py`：

- `test_search_returns_matching_items_ordered_by_time_desc` — 插入 3 条 purchase_items（不同 name / time），搜素 "番茄" 应返回按时间倒序的 2 条
- `test_search_case_insensitive` — "tomato" 能匹配 "Tomato" / "TOMATO"
- `test_search_substring_matches` — "番" 能匹配 "番茄" 和 "番薯"
- `test_search_includes_supplier_name` — JOIN 正确
- `test_search_handles_null_supplier` — `purchases.supplier_id = NULL` 时 `supplier_id/name` 均为 null
- `test_search_default_limit_50` — 插入 60 条，只返回 50
- `test_search_custom_limit` — `?limit=10` 只返回 10
- `test_search_limit_validation` — `?limit=0` / `?limit=201` → 422
- `test_search_query_required` — 缺 `q` → 422
- `test_search_query_empty_after_strip` — `q="   "` → 422
- `test_search_query_too_long` — `q="x"*101` → 422
- `test_search_escapes_like_wildcards` — 搜 `%` / `_` 字面字符不破坏模式

## 8. 未决问题（实现时可决策）

以下细节不阻塞 plan，实现时按列出的默认行为做，如有 push back 再讨论：

- **_decimal 精度**：DB 是 `Numeric(10, 2)`，序列化为 `str(unit_price)`，前端直接展示。不做 `toFixed(2)`（DB 已经存了 2 位）。
- **purchase_time 时区**：DB 存 UTC，响应里 ISO 8601 with `Z`。前端 dayjs / Date 直接 format。不引入额外日期库。
- **SQLAlchemy ESCAPE**：默认用 `\` 作转义字符，`ILIKE :pattern ESCAPE '\\'`。
