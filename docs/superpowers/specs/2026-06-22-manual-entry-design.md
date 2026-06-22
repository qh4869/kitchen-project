# Phase 3.5 设计：手工记账

**状态**：已通过头脑风暴评审，待写实现 plan
**日期**：2026-06-22
**关联**：[Phase 2 OCR 设计](./2026-06-17-phase2-ocr-design.md)；[Phase 3 价格搜索](./2026-06-18-phase3-price-search-design.md)

## 1. 背景与目标

当前 `/upload` 页只支持拍照记账（上传小票 / 菜摊照片 → OCR → 人工微调 → 保存）。部分场景下用户没有照片，只想快速手工录入一笔采购（"今天在楼下菜场买了 2 斤番茄 ¥13"）。当前要么强制走 OCR（不自然），要么无法记录。

本期新增**手工记账模式**，与拍照模式并列在同一页面里；左侧菜单栏标签从"拍照记账"改为"记账"，反映页面职责的扩展。

**本期范围**：
- 前端：`/upload` → `/entry` 路由重命名，页面加 mode toggle，加手工模式表单分支
- 后端：**零改动** —— 现有 `POST /api/v1/purchases` 早就支持无图创建

**显式不做（延后）**：
- 混合模式（边填商品边上传照片）—— UX 纠缠，YAGNI
- 切换 mode 时"确认丢失改动"提示 —— v1 直接清空
- 前端单测框架（vitest 等）—— 单独工作量
- 手工记账也带 image_key 字段 —— 后端 schema 已经允许，但本期不暴露

## 2. 关键决策（已与用户确认）

| 决策 | 结论 | 理由 |
|---|---|---|
| 路由 | `/upload` → `/entry` 重命名 | URL 语义准确；家庭单用户场景无书签失效问题 |
| 导航标签 | "拍照记账" → "记账" | 页面职责扩展为"两种记账方式"，标签需相应泛化 |
| mode 切换 | 同一页面 segmented control | 两种模式共享 ItemEditor + 表单字段，分开页面会重复代码 |
| 默认模式 | 拍照 | 保留现有行为，对当前用户无意外 |
| mode 切换时表单处理 | 直接清空 | YAGNI；"确认丢失改动"提示 v1 不做 |
| 手工模式默认时间 | `now()` | 最常见场景是"刚买的"，默认现在省一次输入 |
| 保存端点 | `POST /api/v1/purchases`（**非** `/purchases/from-ocr`） | from-ocr 要求 image_key；普通 POST 不要求 |
| 成功后行为 | 显示 "✓ 已保存" + "新建一条" 按钮（清空回初始） | 与 OCR 流程一致 |

## 3. 架构

### 3.1 文件改动

| 路径 | 操作 | 责任 |
|---|---|---|
| `apps/web/src/pages/UploadPage.tsx` | 重命名为 `EntryPage.tsx` | 加 `mode` state + 手工模式分支 |
| `apps/web/src/App.tsx` | 修改 | nav label / route / import 改名 |
| `apps/web/src/pages/PurchasesPage.tsx` | 修改（1 行） | 空状态文案 "拍照记账" → "记账"（行 81） |
| `apps/api/**` | **零改动** | — |

### 3.2 组件结构

`EntryPage.tsx` 内部结构：

```
EntryPage
├── 标题 "记账"
├── SegmentedControl (mode = 'photo' | 'manual')
│   ├── [📷 拍照]
│   └── [✍️ 手工]
├── if mode === 'photo':
│   └── (现有 UploadPage 完整流程)
│       ├── ImageUploader
│       ├── OCR 状态显示
│       └── OcrEditForm (供应商/时间/总额 + ItemEditor + 保存按钮)
└── if mode === 'manual':
    └── ManualEntryForm
        ├── 供应商下拉
        ├── datetime-local (默认 now)
        ├── 总额 input
        ├── ItemEditor (默认一行空白)
        └── 保存按钮 → POST /api/v1/purchases
```

### 3.3 数据流

**拍照模式**：完全不变
```
upload → /api/v1/uploads → /api/v1/ocr/extract → 编辑 → /api/v1/purchases/from-ocr
```

**手工模式**：
```
EntryPage 表单
  ↓ useMutation
api.post('/api/v1/purchases', {
  supplier_id: supplierId || null,
  purchase_time: purchaseTime ? new Date(purchaseTime).toISOString() : null,
  total_amount: totalAmount || null,
  items: items
    .filter(i => i.name.trim() && i.unit_price)
    .map(i => ({
      name: i.name.trim(),
      quantity: i.quantity || "1",
      unit: i.unit || null,
      unit_price: i.unit_price,
      category: i.category || null,
      brand: i.brand || null,
    })),
})
  ↓ onSuccess
qc.invalidateQueries({ queryKey: ['purchases'] })
setPhase('saved')
```

## 4. UI 契约

### 4.1 Segmented Control

两个按钮并排，激活的 emerald 高亮：

```tsx
<div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
  <button
    onClick={() => switchMode('photo')}
    className={`rounded-md px-4 py-1.5 text-sm ${
      mode === 'photo' ? 'bg-white text-emerald-700 font-medium shadow-sm' : 'text-slate-600'
    }`}
  >📷 拍照</button>
  <button
    onClick={() => switchMode('manual')}
    className={`rounded-md px-4 py-1.5 text-sm ${
      mode === 'manual' ? 'bg-white text-emerald-700 font-medium shadow-sm' : 'text-slate-600'
    }`}
  >✍️ 手工</button>
</div>
```

`switchMode(next)` 做两件事：
1. `setMode(next)`
2. 调用 `reset()` 清空所有表单状态（imageKey / previewUrl / supplierId / purchaseTime / totalAmount / items / rawLlm / dirty / phase）

### 4.2 手工模式默认值

| 字段 | 默认值 |
|---|---|
| `purchaseTime` | 当前本地时间，格式 `YYYY-MM-DDTHH:mm`（`<input type="datetime-local">` 接受的格式）。注意 `new Date().toISOString().slice(0, 16)` 是 UTC 值，对 UTC+8 用户会显示成 "8 小时前"。实现时用 helper：见 §7 |
| `supplierId` | `""`（下拉选"— 不选 —"） |
| `totalAmount` | `""` |
| `items` | `[{name:"",quantity:"1",unit:"",unit_price:"",category:"",brand:""}]`（一行空白） |
| `dirty` | `false` |

### 4.3 手工模式状态机

| Phase | 触发 | 展示 |
|---|---|---|
| `idle` | 切到手工模式 / 点"新建一条" | 表单 + 保存按钮（disabled 直到至少一条 name+unit_price） |
| `saving` | `saveMut.isPending` | 保存按钮变 "保存中…"，表单不 disabled（允许继续编辑） |
| `saved` | `saveMut.onSuccess` | 绿色 banner "✓ 已保存" + "新建一条" 按钮（调 `reset()`） |
| `error` | `saveMut.onError` | 红色 banner `保存失败：${error.detail}`，表单保留，允许改后重试 |

## 5. 错误处理

| 场景 | 行为 |
|---|---|
| `items.filter(i => i.name.trim() && i.unit_price).length === 0` | 保存按钮 `disabled`（同 OCR 流程） |
| 网络失败 / 5xx | 红色 banner：`保存失败：${error.detail}` |
| 成功 | 绿色 banner + "新建一条" 按钮（reset 表单回 idle） |
| 切换 mode 时表单有改动 | 直接清空，无确认提示（YAGNI） |

## 6. 测试策略

**后端**：零改动 → 零新测试。现有 91 个测试不变。

**前端**：项目无前端单测框架，v1 不引入。验证方式：
- `pnpm build:web` —— TS 编译必须通过
- 手工 E2E：
  1. 进 `/entry` 默认是拍照模式
  2. 点 "✍️ 手工" → 表单清空 + 展示空白表单
  3. 不填任何字段 → 保存按钮 disabled
  4. 填一条 name + unit_price → 保存按钮 enabled
  5. 点保存 → 绿色 banner + /purchases 列表多一条
  6. 点 "📷 拍照" → 切回拍照模式（状态清空）

## 7. 未决问题（实现时可决策）

- **mode state 持久化**：v1 用 `useState`（页面卸载即丢失）。如果要"记住上次模式"，加 localStorage —— 后置。
- **datetime-local 时区**：`new Date().toISOString().slice(0, 16)` 是 UTC 值，对 UTC+8 用户会显示成"8 小时前"。实现时用本地时间 helper，例如：
  ```ts
  function nowLocalDateTime(): string {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  ```
  写到 plan 里。
- **保存成功后是否自动切到 idle**：是。`reset()` 把 phase 回 `idle` + items 重置为一行空白。
