# 连续烹饪助手 · 智慧采购模块

家庭烹饪助手的 Web 应用，本期实现 PRD §4.1 智慧采购模块（视觉化记账、供应商管理、价格仪表盘）。烹饪编排（Feature 2）留作兼容性预留。

## 技术栈

- **后端**：Python 3.13 + FastAPI + SQLAlchemy 2.0 (async) + asyncpg + Alembic
- **前端**：React 18 + Vite + TypeScript + TailwindCSS + TanStack Query
- **数据库**：PostgreSQL 16（Docker）
- **OCR**：可插拔适配器，默认 Volcengine Ark Doubao-Seed-2.0-mini（OpenAI 兼容协议，可切 OpenAI / Qwen / Deepseek；本地开发可用 `mock` provider 免 key）
- **图像处理**：Pillow + pillow-heif（HEIC 解码、EXIF 旋转、长边 ≤2000px 压缩、JPEG q85）
- **包管理**：uv（Python）/ pnpm（前端 monorepo）
- **类型同步**：FastAPI 自动产出 OpenAPI → `openapi-typescript` 生成 TS 类型

## 目录结构

```
kitchen-project/
├── apps/
│   ├── api/                 # FastAPI 后端
│   └── web/                 # Vite + React 前端
├── packages/
│   └── api-types/           # 由 OpenAPI 自动生成的 TS 类型
├── scripts/
│   └── gen-api-types.sh
├── docker-compose.yml       # PostgreSQL
└── .env.example
```

## 功能概览

| 模块 | 状态 | 说明 |
|---|---|---|
| 供应商管理（CRUD） | ✅ | 线下菜场 / 超市维护 |
| 采购记录（CRUD） | ✅ | 手工录入或 OCR 落库 |
| 记账（拍照 + 手工） | ✅ | 拍照：上传小票 / 价签 → LLM 识别 → 人工微调；手工：直接填写明细 → 保存（`POST /api/v1/purchases`） |
| 价格查询（搜索） | ✅ | 按食材名 ILIKE 子串匹配，返回最近 50 条价格 + 店铺 + 时间 |
| 价格曲线 / 跨店比价 | 🚧 | 需先做商品名 / 单位归一化 |

**OCR 流程**：浏览器上传图片 → `/uploads` Pillow 预处理（HEIC 解码 / EXIF 旋转 / 压缩）→ `/ocr/extract` 调用 LLM 提取商品明细（30s 超时）→ 前端可编辑 → `/purchases/from-ocr` 落库。识别对象支持采购小票、单品价签、菜摊 / 货架陈列照、冷柜分类牌。

**手工记账**：`/entry` 页面切到 "✍️ 手工" mode → 直接填供应商 / 时间 / 总额 + 商品明细（复用 `ItemEditor`）→ `POST /api/v1/purchases` 落库。不经过 OCR，适合没拍照、记得买了什么的快速记录。

**价格查询**：`/dashboard` 输入食材名（如"番茄"）→ ILIKE 子串模糊匹配 `purchase_items.name` → 表格返回最近 50 条记录，按采购时间倒序，含商品名 / 单价+单位 / 店铺 / 采购时间。未绑店铺的记录显示"—（未绑店铺）"。

## 快速开始

### 首次初始化

```bash
# 1. 复制环境变量；按需填 LLM_API_KEY（或用 OCR_PROVIDER=mock 免 key 跑）
cp .env.example .env

# 2. 启动 PostgreSQL
pnpm db:up

# 3. 初始化后端（创建虚拟环境 + 安装依赖 + 数据库迁移）
cd apps/api
uv venv --python 3.13
uv sync
uv run alembic upgrade head
cd ../..

# 4. 安装前端依赖
pnpm install

# 5. 生成前端类型（需后端先跑起来；见下）
pnpm dev:api &       # 等 5 秒
pnpm gen:types
```

### 日常开发

```bash
pnpm db:up           # 启动 PostgreSQL（如未启动）
pnpm dev             # 同时启动前后端：api:3000 / web:5173
```

| URL | 用途 |
|---|---|
| http://localhost:5173 | 前端 |
| http://localhost:3000/docs | FastAPI Swagger UI |
| http://localhost:3000/openapi.json | OpenAPI 规范 |

### 常用命令

| 命令 | 用途 |
|---|---|
| `pnpm db:up` | 启动 PostgreSQL 容器 |
| `pnpm db:down` | 停止 PostgreSQL |
| `pnpm db:migrate` | 应用数据库迁移 |
| `pnpm db:revision -m "msg"` | 生成新迁移（基于 ORM 模型差异） |
| `pnpm gen:types` | 从后端 OpenAPI 重新生成前端 TS 类型 |
| `pnpm test:api` | 运行后端 pytest |
| `pnpm build:web` | 构建前端生产产物 |

## 迁移到服务器

只需修改 `.env`：
- `DATABASE_URL` → 远程 PG
- `STORAGE_DRIVER=s3` + 对象存储凭证（S3/OSS 兼容）
- `LLM_*` 不变（OCR 是第三方 API，与部署位置无关）

前端 `pnpm build:web` 后产物为静态资源，可放任意 CDN / nginx。后端用 `uvicorn app.main:app --workers 4`（生产推荐 gunicorn + uvicorn worker）。

## 待开发与遗留事项

### Phase 3 v2+（价格仪表盘扩展）

当前 v1 只做了 PRD §2.A 的第三件事（搜索）。剩余两件依赖**商品名归一化**（OCR 会把同一个番茄写成番茄 / 西红柿 / 番茄(有机)）和**单位归一化**（¥/kg vs ¥/500g vs ¥/个 不可比），归一化方案未定前先延后：

- **单品价格曲线**：Recharts 已装但未用；需要名称归一化后按周 / 月聚合
- **跨店铺比价**：同品类在不同店铺的当前预估价；需要单位归一化做换算
- **推荐购买店铺**：基于"近期最低价 + 距离 / 偏好"的排序算法
- **搜索增强**：分页、URL query state（可分享链接）、输入防抖、自动补全
- **类型同步**：`DashboardPage.tsx` 当前手写 TS 类型，应迁到 `@kitchen/api-types` 生成产物

### 已知技术债

代码层面遗留，不阻塞使用但值得在下一次相关改动时顺手清理：

- **`datetime.utcnow()` 弃用警告**：`apps/api/app/routers/uploads.py:49` 及其测试用 `datetime.utcnow()`，Python 3.13 标记为弃用。改为 `datetime.now(datetime.UTC)`
- **`/suppliers` 的 ILIKE 未转义**：`apps/api/app/routers/suppliers.py` 直接拼 `%{q}%`，用户输入 `%` / `_` 会被当通配符。与 `/prices/search` 的转义逻辑（`routers/prices.py:39-43`）不一致，应对齐
- **前端手写类型 vs 生成类型**：`DashboardPage.tsx`、`EntryPage.tsx` 等手写响应类型，没用 `@kitchen/api-types`。存在漂移风险，应统一改为 `import type { paths } from "@kitchen/api-types"`
- **`test_search_default_limit_50` 二级排序未验证**：60 条记录同 `purchase_time` 时，`ORDER BY` 无 tie-breaker，顺序未定义。测试只验 count，未验顺序确定性
- **`purchase_items.name` 无 trigram 索引**：`LIKE '%foo%'` 走全表扫。家庭数据量无感，若数据量大需加 `pg_trgm` 扩展 + GIN 索引

### Feature 2（烹饪编排）预留

本期不实现烹饪编排，但已为后续留好扩展位：
- API 路由统一 `/api/v1` 前缀，Feature 2 加 `/api/v1/recipes`、`/api/v1/cooking-plans` 不冲突
- 数据库通过 Alembic 管理，未来加表零阻力
- 不预先声明 Feature 2 的 Pydantic schema，避免污染 OpenAPI 契约
