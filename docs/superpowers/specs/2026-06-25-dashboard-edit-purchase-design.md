# 设计：首页编辑功能（点击行进入记账手工编辑整张 purchase）

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-25
**关联**：[Phase 3.6 删除 + 移除采购记录页 + 干掉 total_amount](./2026-06-24-dashboard-delete-remove-purchases-page-design.md)

## 1. 背景

Phase 3.6 之后首页（dashboard）只能删除错记的商品，但**改不了**：
- 单价记错了想改 → 没办法
- 多记了一条想加进去 → 必须删整单重录
- 漏记一条想补 → 同上

本期给"操作"列加第二个按钮 ✎ 编辑：点击 → 弹确认 → 跳到 `/entry?edit={purchase_id}` → 复用记账页的手工模式 UI，预填该 purchase 的全部内容 → 用户改完保存 → 跳回首页刷新。

**为什么是整张 purchase 不是单条 item**：用户原话"可以修改和重新添加"暗示要能加新商品，单条 item 编辑做不到。整张 purchase 编辑虽然"点一行看到多条"会有意外感，**用确认弹窗消除这个意外**。

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 编辑粒度 | 整张 purchase（含其所有 items） | 用户要能"重新添加"，单条做不到；用户已确认 |
| 点击范围保护 | `window.confirm` 弹窗告知"将打开整张采购单" | 避免点一行看到多条时的意外 |
| 后端实现 | 扩展现有 `PUT /purchases/{id}` 接受可选 `items` 字段 | 复用现有端点，避免新增；items 缺省时不动 |
| items=[] 保护 | **前端拦截**（disabled 保存按钮 + 提示） | 后端 cascade-delete purchase 逻辑复杂（响应类型不一致），简化为前端校验 |
| Mode toggle | 编辑模式锁手工 mode（隐藏 toggle） | 编辑不涉及 OCR，照片 mode 无意义 |
| 跳转目的地 | 保存成功后 navigate('/') 回首页 | 用户从首页来，自然回首页看更新结果 |
| 取消编辑 | "取消"按钮紧挨"保存修改" | 用户可能误进，需 exit 路径 |
| 标题文案 | "记账" → "编辑记录" | 明确当前 mode |
| 保存按钮文案 | "保存" → "保存修改" | 同上 |
| 直接访问 `/entry?edit=xxx` | 一样工作（useQuery 拉 purchase） | 不需特判来源 |

## 3. 架构

### 3.1 文件改动

| 路径 | 操作 | 责任 |
|---|---|---|
| `apps/api/app/schemas/purchase.py` | 修改 | `PurchaseUpdate` 加 `items: list[PurchaseItemCreate] \| None = None` |
| `apps/api/app/routers/purchases.py` | 修改 | `update_purchase` 处理 items 替换逻辑 |
| `apps/api/tests/test_purchases.py` | 修改 | 加 3 个 PUT-with-items 测试 |
| `apps/web/src/pages/DashboardPage.tsx` | 修改 | 加 ✎ 按钮 + `handleEdit` + `useNavigate` |
| `apps/web/src/pages/EntryPage.tsx` | 修改 | 检测 edit mode、加载 purchase、预填、PUT 保存、取消按钮 |
| `apps/web/src/api/client.ts` | 修改（如缺） | 加 `api.put` helper（如果还没有） |

### 3.2 数据流

**点击编辑**：
```
[Dashboard 行 ✎]
  → window.confirm("编辑将打开该记录所属采购单的全部内容，是否继续？")
  → 取消 → 静默返回
  → 确认 → navigate(`/entry?edit=${purchase_id}`)
```

**编辑页加载**：
```
[EntryPage mount with ?edit={purchase_id}]
  → useSearchParams 拿 editPurchaseId
  → useQuery(['purchase', editPurchaseId]) GET /api/v1/purchases/{id}
  → useEffect 看 editPurchase data，预填 manualSupplierId / manualPurchaseTime / manualItems
  → 强制 mode = 'manual'，隐藏 segmented control
  → 标题、按钮文案切换
```

**保存修改**：
```
[点保存修改]
  → 校验 manualItems.filter(name && unit_price).length > 0
    （=== 0 → 按钮 disabled，前端拦截 items=[]）
  → api.put(`/api/v1/purchases/${editPurchaseId}`, {
      supplier_id, purchase_time, items, manual_adjustment: true
    })
  → onSuccess: qc.invalidateQueries(['prices', 'purchase'])
              navigate('/')
  → 首页表格刷新，显示编辑后内容
```

## 4. API 契约

### 4.1 `PUT /api/v1/purchases/{purchase_id}`（扩展）

**请求 body**（`PurchaseUpdate`）：

```jsonc
{
  "supplier_id": "uuid-or-null",
  "purchase_time": "2026-06-25T10:00:00Z",
  "notes": "可选",
  "manual_adjustment": true,
  "items": [
    {"name": "番茄", "quantity": "1.5", "unit": "kg", "unit_price": "6.5", "category": "蔬菜", "brand": null},
    ...
  ]
}
```

**行为**：
- 字段未传（`exclude_unset`）→ 不动
- `items` 字段传了（哪怕空数组）→ 删除原有 items，按 payload 重建
- `items` 字段未传 → 原 items 不动
- `items: []` → 删完后 purchase 是 0 items。**前端保证不发生**（保存按钮 disabled）；后端不专门处理（让 cascade 行为靠 DELETE /purchase-items 流程，不在 PUT 路径里搞）

**响应**：200 + `PurchaseOut`（含更新后的 items 列表）

**错误**：
- 404 `"Purchase not found"` — purchase_id 不存在
- 422 — Pydantic 校验失败

### 4.2 现有 `GET /api/v1/purchases/{purchase_id}`

不变，已经在 `PurchaseOut` 里返回完整 items 数组。

## 5. 前端 UI

### 5.1 DashboardPage 操作列

合并 ✎ + ✕ 到一个 `<td>`，`whitespace-nowrap` 防换行：

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

```tsx
const navigate = useNavigate();

const handleEdit = (purchaseId: string) => {
  if (window.confirm("编辑将打开该记录所属采购单的全部内容，是否继续？")) {
    navigate(`/entry?edit=${purchaseId}`);
  }
};
```

注：`navigate` 是同步的，无需 `editMut.isPending`；只保留 `deleteMut.isPending` 防止删除中点编辑。

### 5.2 EntryPage edit mode

```tsx
import { useSearchParams, useNavigate } from "react-router-dom";

const [searchParams] = useSearchParams();
const navigate = useNavigate();
const editPurchaseId = searchParams.get("edit");
const isEditMode = !!editPurchaseId;

const { data: editPurchase } = useQuery({
  queryKey: ["purchase", editPurchaseId],
  queryFn: () => api.get<PurchaseOut>(`/api/v1/purchases/${editPurchaseId}`),
  enabled: isEditMode,
});

useEffect(() => {
  if (editPurchase) {
    setManualSupplierId(editPurchase.supplier_id ?? "");
    setManualPurchaseTime(toLocalInputValue(editPurchase.purchase_time));
    setManualItems(editPurchase.items.map((it) => ({
      name: it.name,
      quantity: it.quantity,
      unit: it.unit ?? "",
      unit_price: it.unit_price,
      category: it.category ?? "",
      brand: it.brand ?? "",
    })));
  }
}, [editPurchase]);

const saveMut = useMutation({
  mutationFn: async () => {
    const body = {
      supplier_id: manualSupplierId || null,
      purchase_time: manualPurchaseTime ? new Date(manualPurchaseTime).toISOString() : null,
      manual_adjustment: true,
      items: manualItems.filter(i => i.name.trim() && i.unit_price).map(i => ({...})),
    };
    if (isEditMode) {
      return api.put(`/api/v1/purchases/${editPurchaseId}`, body);
    }
    return api.post("/api/v1/purchases", body);
  },
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ["prices"] });
    qc.invalidateQueries({ queryKey: ["purchase", editPurchaseId] });
    if (isEditMode) navigate("/");
  },
});
```

UI 渲染：
- `{isEditMode ? <h2>编辑记录</h2> : <h2>记账</h2>}`
- `{!isEditMode && <SegmentedControl />}` — 编辑模式不渲染 toggle
- 表单（手工 mode 的那块）两种 mode 都用
- 操作按钮区：
  ```tsx
  {isEditMode ? (
    <>
      <button onClick={() => navigate("/")}>取消</button>
      <button onClick={() => saveMut.mutate()} disabled={!canSave}>保存修改</button>
    </>
  ) : (
    <button onClick={() => saveMut.mutate()} disabled={!canSave}>保存</button>
  )}
  ```

### 5.3 加载状态

edit mode 进入时，`useQuery` 还没拉到 purchase 数据，预填 effect 没执行 → 表单显示空（默认 1 条空白 item）。这会闪一下。

加个 loading 状态：
```tsx
const isLoadingPurchase = isEditMode && !editPurchase;
if (isLoadingPurchase) {
  return <p className="text-sm text-slate-500">加载采购单...</p>;
}
```

## 6. 错误处理

| 场景 | 后端 | 前端 |
|---|---|---|
| 编辑期间 purchase 被其他端删除 | PUT 返 404 | alert + navigate('/') |
| items 全部清空（用户删光了） | 不会发请求 | 保存按钮 disabled，提示"至少保留一条" |
| 网络断 | fetch reject | alert("网络异常，请稍后重试") |
| 编辑某字段类型错（如 unit_price 非数字） | 422 | alert(detail) |

## 7. 测试

### 7.1 后端新增（`tests/test_purchases.py`）

- `test_update_purchase_replaces_items_when_provided` — 建 purchase 含 2 条 item，PUT 带 items=[3 条新]，响应 items 长度 = 3，原 items 不在
- `test_update_purchase_preserves_items_when_omitted` — 建 purchase 含 2 条 item，PUT 不带 items key，响应 items 长度仍 = 2，内容不变
- `test_update_purchase_404_on_missing_purchase` — 不存在的 UUID → 404

### 7.2 后端现有测试可能受影响

- 现有 `test_update_marks_manual_adjustment` 走 PUT 不带 items，应该仍 PASS（向后兼容）

### 7.3 前端

无单测（项目惯例）。E2E smoke 走：
1. 首页某行点 ✎ → 弹窗 → 确认 → 跳到 /entry?edit=xxx
2. 表单预填该 purchase 的所有 items
3. 改一个字段 + 加一条 item → 点保存修改
4. 跳回首页，原行内容更新，新增的 item 也显示

## 8. 未决问题（实现时可决策）

- **`api.put` helper 是否存在**：先 `cat apps/web/src/api/client.ts` 看。Task 5 加过 `api.delete`，应该有同款 `api.put`；若没有，加上。
- **`toLocalInputValue` helper**：把 ISO 时间转成 `<input type="datetime-local">` 接受的格式（YYYY-MM-DDTHH:mm in local tz）。EntryPage 已有 `nowLocalDateTime`，可以提取一个反向函数。
- **预填 useEffect 依赖**：`[editPurchase]` 单元素依赖数组。如果 React 在 StrictMode 下双调 effect，会预填两次但 idempotent，没问题。
- **取消按钮的 navigate('/')**：会触发 React Router 重新 mount DashboardPage，自动触发 useQuery 拉 /prices/search，等价于 invalidateQueries(['prices'])。无需额外刷。
- **`manual_adjustment: true` 写死**：编辑场景确实属于"人工调整"，硬编码 true 合理。新建场景仍然 false（保留原行为）。
