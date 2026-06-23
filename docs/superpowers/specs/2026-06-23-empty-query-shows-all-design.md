# 设计：价格查询 — 空 query 当作全匹配

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-23
**关联**：[Phase 3 价格搜索](./2026-06-18-phase3-price-search-design.md)

## 1. 背景与目标

当前 `/dashboard` 价格查询页有两个交互问题：

1. 进页面看到的是"提示 banner"，**必须先输入关键词再点搜索**才能看到数据。
2. 输入框为空时**按钮 disabled**，即使想浏览最近采购也办不到。

本期改成"空 query 当作全匹配"：进页面自动加载最近 50 条；清空输入再点搜索 = 刷新最近 50 条；输入关键词 = ILIKE 过滤。

**本期范围**：
- 后端 `GET /api/v1/prices/search`：`q` 从必填变可选，空 / 纯空白 → 跳过 WHERE 子句
- 前端 `DashboardPage.tsx`：进页面自动加载、按钮始终启用、空 query 文案分支
- 测试：2 条改名 + 1 条新增

**显式不做（延后）**：
- URL query state（可分享链接）
- 输入防抖（仍然 onSubmit 触发）
- 自动补全
- 分页（v1 仍然最近 50）

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 空 query 语义 | 全匹配（返最近 50 条） | 满足"浏览最近采购"的隐式需求；用户已确认 |
| 进页面行为 | 自动加载 | 体验最顺；用户已确认 |
| 触发方式 | 仍然 onSubmit | 与现有 UX 一致；防抖是另一项工作 |
| `q` 参数语义 | 可选、默认空字符串 | FastAPI `Query("", max_length=100)` 自动拒绝超长 |
| 纯空白（`q="   "`） | strip 后按空 query 处理 | 与用户在输入框敲空格等价 |
| 0 条记录的 empty 文案 | 分支：空 query 显"暂无采购记录"，非空 query 显"未找到 X" | 两种语义不同，混用尴尬 |

## 3. 架构

### 3.1 改动文件

| 路径 | 操作 | 责任 |
|---|---|---|
| `apps/api/app/routers/prices.py` | 修改 | `q` 改可选，空时跳过 WHERE |
| `apps/api/tests/test_prices_search.py` | 修改 | 2 条改名/重写 + 1 条新增 |
| `apps/web/src/pages/DashboardPage.tsx` | 修改 | 自动加载、按钮启用、empty 文案分支 |
| `apps/api/app/schemas/price.py` | 不变 | `SearchResult.query: str` 已支持空字符串 |
| `apps/api/app/main.py` | 不变 | 路由已注册 |

### 3.2 数据流

**空 query 路径（新）**：
```
GET /api/v1/prices/search                (无 q 参数)
GET /api/v1/prices/search?q=             (空字符串)
GET /api/v1/prices/search?q=%20%20%20    (纯空白)
       ↓
search_prices(q=""):
  q_stripped = ""
  → stmt 不带 .where(...) 子句
  → JOIN + ORDER BY purchase_time DESC + LIMIT 50
  → 返回最近 50 条（不区分商品名）
       ↓
Response 200 {"query": "", "count": N, "items": [...]}
```

**非空 query 路径（不变）**：
```
GET /api/v1/prices/search?q=番茄
       ↓
search_prices(q="番茄"):
  q_stripped = "番茄"
  len(q_stripped) <= 100 → OK
  escaped + pattern
  → stmt 带 .where(name ILIKE pattern)
       ↓
Response 200 {"query": "番茄", "count": N, "items": [...]}
```

## 4. API 契约

### 4.1 请求

`GET /api/v1/prices/search?q=<str>&limit=<int>`

| 参数 | 类型 | 必填 | 默认 | 校验 |
|---|---|---|---|---|
| `q` | str | 否 | `""` | strip 后 ≤ 100 字符；超过 → 422 `INVALID_QUERY`（仍由 max_length 守，但消息需手写） |
| `limit` | int | 否 | 50 | 1 ≤ limit ≤ 200（FastAPI `ge`/`le` 默认 422） |

### 4.2 响应

**200 OK** — 与 Phase 3 v1 完全一致：

```jsonc
{
  "query": "",                 // 或 "番茄" 等
  "count": 23,
  "items": [
    {
      "name": "番茄",
      "quantity": "1.5",
      "unit": "kg",
      "unit_price": "6.50",
      "category": "蔬菜",
      "brand": null,
      "supplier_id": "...",
      "supplier_name": "城南菜场",
      "purchase_id": "...",
      "purchase_time": "2026-06-23T09:32:29Z"
    }
    // ...最多 50 行
  ]
}
```

**422 Unprocessable Entity** — 仅一种：
- `q` 超过 100 字符（`q` 缺失 / 空字符串 / 纯空白都返回 200）

```jsonc
{ "detail": "INVALID_QUERY: query must be 1-100 chars (got N)" }
```

注：`limit` 边界违例仍走 FastAPI 默认 422。

## 5. 前端

### 5.1 状态机（简化）

去掉 `'initial'` 相位：

```tsx
type Phase = "loading" | "empty" | "success" | "error";
// 进页面立即 loading → (success | empty | error)
```

### 5.2 查询配置

```tsx
const { data, isFetching, error } = useQuery<SearchResult>({
  queryKey: ["prices", submittedQ],
  queryFn: () =>
    api.get<SearchResult>(
      `/api/v1/prices/search?q=${encodeURIComponent(submittedQ)}`
    ),
  // enabled: 默认 true，进页面就触发
});
```

### 5.3 按钮 / 输入

```tsx
<button
  type="submit"
  disabled={isFetching}            // 去掉 !input.trim()
  className="..."
>
  {isFetching ? "搜索中…" : "搜索"}
</button>
```

`handleSubmit` 仍然 `setSubmittedQ(input.trim())`，不再需要 `if (q)` 守卫（空字符串也允许）。

### 5.4 相位分支

```tsx
const phase: Phase = isFetching
  ? "loading"
  : error
    ? "error"
    : data && data.count === 0
      ? "empty"
      : "success";
```

### 5.5 文案分支

```tsx
{phase === "empty" && (
  <div className="...">
    {submittedQ === ""
      ? `暂无采购记录。去「记账」添加第一条。`
      : `未找到 "${submittedQ}" 的采购记录。可以换个关键词，或先去「记账」/「采购记录」录入。`
    }
  </div>
)}
```

### 5.6 删 hint banner

原本的 `phase === "initial"` 提示 banner（"商品名为 OCR 或手工录入时的原文…"）整个删掉。进页面就是 loading，然后表格。

## 6. 错误处理

| 场景 | 后端响应 | 前端展示 |
|---|---|---|
| 进页面 / 空 query | 200 + 最近 N 条 | loading → 表格 |
| 关键词匹配到 N 条 | 200 + N 条 | loading → 表格 |
| 关键词 0 匹配 | 200 `{count:0, items:[]}` | loading → empty banner（"未找到 X"） |
| DB 里 0 条采购记录 | 200 `{count:0, items:[]}` | loading → empty banner（"暂无采购记录"） |
| `q` 超过 100 字符 | 422 `INVALID_QUERY` | 不应发生（前端不限制长度）；兜底红色 banner |
| `limit` 越界 | 422 | 不应发生（前端不暴露 limit） |
| DB 连接失败 | 500 | 红色 banner：`查询失败：网络异常，请稍后重试` |
| 网络断开 | fetch reject | 同 500 |

## 7. 测试策略

`tests/test_prices_search.py` 改动：

**改写（原 422 行为变 200）**：

- `test_search_query_required` → `test_search_empty_q_returns_all_items`
  - 不传 `q` 参数 → 200，count = 测试数据总条数
- `test_search_query_empty_after_strip_returns_422` → `test_search_whitespace_q_returns_all_items`
  - `q="   "` → 200，count = 测试数据总条数

**新增**：

- `test_search_empty_q_respects_limit`
  - 插 60 条，不传 q，传 `limit=10` → count=10

**不变**（10 条）：
- ordering by time desc
- case insensitive
- substring matches
- includes supplier name
- handles null supplier
- default limit 50（带 q 仍然测）
- custom limit（带 q 仍然测）
- limit zero returns 422
- limit over max returns 422
- query too long returns 422
- escapes like wildcards

## 8. 未决问题（实现时可决策）

- **TanStack Query staleTime**：进页面触发自动加载后，如果用户切换 tab 再切回来，TanStack Query 默认会 refetch（refetchOnWindowFocus）。这对一个查询页是合理的，v1 不动。
- **空 query 时 `query` 字段返回什么**：响应里 `query` 字段 = `q_stripped`（即空字符串 `""`）。前端已用 `submittedQ === ""` 判断，无需改。
- **保留 max_length=100 在 Query 里还是手写检查**：FastAPI 的 `Query("", max_length=100)` 会返标准 Pydantic 校验错误（422 但 detail 是 Pydantic 格式，不是 `INVALID_QUERY:` 前缀）。如果想保持自定义消息，用手写 `if len(q_stripped) > MAX_QUERY_LENGTH` —— 当前实现用的就是手写，本次保持。
