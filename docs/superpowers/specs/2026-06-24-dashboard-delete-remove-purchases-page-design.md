# 设计：仪表盘加删除 + 移除采购记录页 + 干掉 total_amount

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-24
**关联**：[Phase 3 价格搜索](./2026-06-18-phase3-price-search-design.md)、[空 query 显示全部](./2026-06-23-empty-query-shows-all-design.md)

## 1. 背景

当前用户体验有 3 个痛点：

1. **错记的商品改不了**。仪表盘只能查不能改，要删一笔得切到「采购记录」页面找对应的 purchase 再整单删。
2. **「采购记录」页面其实没必要**。仪表盘已经能看全部商品记录（按时间倒序、可搜索），「采购记录」只是另一种聚合视图，导航冗余。
3. **`total_amount` 字段鸡肋**。前端从 OCR 自动填的总额用户不一定信；手工输入的总额经常懒得填；DB 里大量 NULL。仪表盘也不展示它。维护成本 > 价值。

本期一次性解决这三件事：
- 仪表盘加 **逐条商品删除** 能力（删单条 `purchase_item`，不动同 purchase 其他商品）
- 移除「采购记录」页面，仪表盘提升为首页（`/`）
- `total_amount` 从数据模型 / API / 前端 / OCR prompt 彻底移除

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 删除粒度 | 删单个 `purchase_item`，不影响同 purchase 其他 item | 用户原话"只删除单独的商品，不涉及 purchase 其他商品" |
| 删到最后一个 item 时 | 级联删除整个 purchase | 避免 purchase 表出现 0 item 的孤儿行；DB 层没设反过来 cascade，应用层兜底 |
| `total_amount` | 完全干掉（DB 列 + 所有 schema + 前端输入 + OCR prompt） | 用户原话"数据部不用保留总价内容"；维护成本 > 价值 |
| 旧 `/dashboard` 路由 | 改成 `/`（仪表盘升为首页） | 用户选了"Dashboard 当首页（推荐）" |
| 旧 `/` 路由（采购记录） | 整个移除 | 用户原话"去掉采购记录页面" |
| nav 标签 | 移除"采购记录"，"价格仪表盘" → "首页" | 配合路由变化 |
| 删除 UX | 表格加第 5 列"操作"，每行红色 ✕ 按钮，点击 `window.confirm` 后 DELETE | 简单、移动端友好（不用 hover） |
| 删除后刷新 | `qc.invalidateQueries({ queryKey: ['prices'] })` | TanStack Query 自动重发当前查询，表格立即更新 |
| 软删除 / 回收站 | 不做 | YAGNI，硬删除即可 |
| 保留旧 purchases CRUD 端点 | 是（GET list / GET {id} / PUT {id} / DELETE {id}） | 前端暂时不用，但删端点没收益、未来可能恢复 |

## 3. 架构

### 3.1 文件改动总览

| 路径 | 操作 | 责任 |
|---|---|---|
| `apps/api/app/routers/purchase_items.py` | **新建** | `DELETE /{item_id}` 端点 + 级联空 purchase 删除 |
| `apps/api/app/main.py` | 修改 | 注册 `purchase_items` router |
| `apps/api/app/db/models.py` | 修改 | `Purchase` 删 `total_amount` 列 |
| `apps/api/app/schemas/purchase.py` | 修改 | `PurchaseBase` / `PurchaseUpdate` / `PurchaseListItem` 删 `total_amount` |
| `apps/api/app/schemas/ocr.py` | 修改 | `OcrResult` / `PurchaseFromOcrRequest` 删 `total_amount` |
| `apps/api/app/schemas/price.py` | 修改 | `SearchResultItem` 加 `purchase_item_id` 字段 |
| `apps/api/app/services/ocr/prompt.py` | 修改 | SYSTEM_PROMPT 删 `total_amount` 字段说明 |
| `apps/api/app/services/ocr/parser.py` | 修改 | `parse_llm_json` 不再 copy total_amount |
| `apps/api/app/services/ocr/mock.py` | 修改 | `_DEFAULT_RESULT` 删 total_amount |
| `apps/api/app/routers/purchases.py` | 修改 | create_purchase + from-ocr 不再传 total_amount |
| `apps/api/app/routers/prices.py` | 修改 | SELECT 加 `PurchaseItem.id.label("purchase_item_id")` |
| `apps/api/alembic/versions/XXXX_drop_total_amount.py` | **新建** | `op.drop_column('purchases', 'total_amount')` |
| `apps/api/tests/test_purchase_items.py` | **新建** | 3 个测试覆盖删除 + 级联 + 404 |
| `apps/api/tests/test_purchases.py` | 修改 | 删 total_amount 相关字段 |
| `apps/api/tests/test_purchases_from_ocr.py` | 修改 | 同上 |
| `apps/api/tests/test_ocr_*.py` | 修改（如有断言） | 删 total_amount 断言 |
| `apps/api/tests/test_prices_search.py` | 修改（如 helper 用到） | helper 不动；测试断言新字段 `purchase_item_id` |
| `apps/web/src/App.tsx` | 修改 | 删 PurchasesPage 引用 + 路由，Dashboard 移到 `/`，nav 重命名 |
| `apps/web/src/pages/PurchasesPage.tsx` | **删除** | 整个文件不要 |
| `apps/web/src/pages/DashboardPage.tsx` | 修改 | 加 `purchase_item_id` 类型 + 第 5 列删除按钮 + delete mutation |
| `apps/web/src/pages/EntryPage.tsx` | 修改 | 删 `manualTotalAmount` + `photoTotalAmount` state / input / body 字段 |
| `apps/web/src/api/client.ts` | 修改（如有 `api.delete` 不存在则加） | 加 `api.delete(path)` helper |

### 3.2 数据流

**删除单条商品**：
```
[DashboardPage row ✕]
  → window.confirm("删除这条记录？")
  → api.delete(`/api/v1/purchase-items/${purchase_item_id}`)
       ↓
[DELETE /api/v1/purchase-items/{item_id}]
  - db.get(PurchaseItem, item_id) → 404 if None
  - purchase_id = item.purchase_id
  - db.delete(item); await db.commit()
  - remaining = SELECT count(*) WHERE purchase_id = X
  - if remaining == 0:
      db.get(Purchase, purchase_id); db.delete(purchase); await db.commit()
  - return 204
       ↓
[DashboardPage]
  onSuccess: qc.invalidateQueries({ queryKey: ['prices'] })
  → 当前查询自动重新拉取，行从表格里消失
```

## 4. API 契约

### 4.1 新端点 `DELETE /api/v1/purchase-items/{item_id}`

- **路径参数**：`item_id` (UUID)
- **响应**：204 No Content
- **错误**：
  - 404 `PURCHASE_ITEM_NOT_FOUND` — item_id 不存在

### 4.2 `GET /api/v1/prices/search` 响应字段变化

`SearchResultItem` 新增：
```jsonc
{
  "name": "...",
  ...
  "purchase_id": "...",
  "purchase_item_id": "uuid-...",  // ← 新字段，给前端做删除用
  "purchase_time": "..."
}
```

### 4.3 `total_amount` 字段移除（破坏性变更）

以下端点的请求/响应不再含 `total_amount`：

- `POST /api/v1/purchases`（请求 body）
- `POST /api/v1/purchases/from-ocr`（请求 body）
- `GET /api/v1/purchases`（响应里 `total_amount` 字段没了）
- `GET /api/v1/purchases/{id}`（响应里没了）
- `PUT /api/v1/purchases/{id}`（请求 body 不再接受）
- `POST /api/v1/ocr/extract`（响应 `OcrResult.total_amount` 没了）

前端调任何上述端点时如果还传 `total_amount`，后端会 422（pydantic 默认拒绝 extra fields？不会，`extra='ignore'` 模式下会忽略）。本仓库的 schema 没显式设置 extra，pydantic v2 默认是 `ignore`，所以即使前端没改也不会报错，但建议同步清理。

## 5. 数据库迁移

新建 `apps/api/alembic/versions/2026_06_24_xxxx_drop_total_amount.py`：

```python
"""drop total_amount from purchases

Revision ID: <auto>
Revises: <previous revision>
Create Date: 2026-06-24 ...
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('purchases', 'total_amount')


def downgrade():
    op.add_column('purchases', sa.Column('total_amount', sa.Numeric(10, 2), nullable=True))
```

**数据丢失**：DROP COLUMN 在 PG 是破坏性的，该列所有现存数据丢失。家庭场景数据量小，可接受。ECS 部署后跑 `alembic upgrade head` 即生效。

## 6. 前端 UI 细节

### 6.1 Dashboard 删除按钮

表头：
```tsx
<th className="px-3 py-2 text-right font-medium">操作</th>
```

每行：
```tsx
<td className="px-3 py-1.5 text-right">
  <button
    type="button"
    className="text-xs text-red-500 hover:text-red-700"
    onClick={() => handleDelete(it.purchase_item_id, it.name)}
  >
    ✕
  </button>
</td>
```

`handleDelete`：
```tsx
const deleteMut = useMutation({
  mutationFn: (id: string) => api.delete(`/api/v1/purchase-items/${id}`),
  onSuccess: () => qc.invalidateQueries({ queryKey: ['prices'] }),
});

const handleDelete = (id: string, name: string) => {
  if (window.confirm(`确定删除「${name}」这条记录？`)) {
    deleteMut.mutate(id);
  }
};
```

### 6.2 EntryPage 移除总额字段

原 3 列 grid（供应商 / 采购时间 / 总额）变 2 列（供应商 / 采购时间）。两个 mode（photo / manual）同步删。

## 7. 错误处理

| 场景 | 后端响应 | 前端展示 |
|---|---|---|
| 删除成功 | 204 | 表格刷新（TanStack Query 自动） |
| item_id 不存在 | 404 `PURCHASE_ITEM_NOT_FOUND` | alert / banner（v1 用 `alert()` 简单处理） |
| DB 连接失败 | 500 | 同上 |
| 网络断开 | fetch reject | 同上 |

简化处理：失败时 `alert((err as ApiError).detail || '删除失败，请稍后再试')`。不做 toast 系统（YAGNI）。

## 8. 测试策略

### 8.1 新增 `tests/test_purchase_items.py`

```python
async def test_delete_item_succeeds_when_purchase_has_other_items(client):
    # 建 purchase 含 2 个 item，删其中一个 → 204，剩余 1 个 item，purchase 还在
    ...

async def test_delete_last_item_cascades_purchase_deletion(client):
    # 建 purchase 含 1 个 item，删之 → 204，purchase 也没了（GET /purchases/{id} → 404）
    ...

async def test_delete_nonexistent_item_returns_404(client):
    # 随机 UUID → 404 PURCHASE_ITEM_NOT_FOUND
    ...
```

### 8.2 现有测试更新

- `tests/test_purchases.py`：`test_create_and_get_with_items` 等 — POST body 不再含 `total_amount`；GET 响应不再断言 `total_amount`
- `tests/test_purchases_from_ocr.py`：3 个测试的 payload 删 `total_amount` 字段
- `tests/test_ocr_endpoint.py` / `tests/test_ocr_mock.py` / `tests/test_ocr_parser.py`：如断言 `result.total_amount`，删；fixture 里 raw_llm_output 含 total_amount 可保留（pydantic `extra='ignore'` 会忽略）
- `tests/test_prices_search.py`：现有测试断言 items 字段无需改；可选加一个测试断言 `purchase_item_id` 字段存在

### 8.3 验证命令

```bash
cd apps/api && python -m uv run pytest -v        # 全部通过
cd D:/workspace/kitchen-project && pnpm build:web # TS 编译过
```

## 9. 未决问题（实现时可决策）

- **purchase cascade 删除时机**：先删 item 再 count，还是先 count 再删？目前是"先删 item → count → 若 0 则删 purchase"，多一次 DB 往返但逻辑清晰。
- **`api.delete` helper**：检查 `apps/web/src/api/client.ts` 是否已有。若无，加一个跟 `api.get` 同款签名的 helper。
- **`purchase_item_id` 字段在 SearchResultItem 的位置**：放最后（`purchase_time` 之后），跟现有命名顺序一致。
- **删除按钮 label**：用 ✕ 字符还是 "删除" 文本？✕ 紧凑、跨语言；"删除" 中文更明确。建议 ✕ + `title="删除"` 属性。
