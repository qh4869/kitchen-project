# 连续烹饪助手 · 智慧采购模块

家庭烹饪助手的 Web 应用，本期实现 PRD §4.1 智慧采购模块（视觉化记账、供应商管理、价格仪表盘）。烹饪编排（Feature 2）留作兼容性预留。

## 技术栈

- **后端**：Python 3.13 + FastAPI + SQLAlchemy 2.0 (async) + asyncpg + Alembic
- **前端**：React 18 + Vite + TypeScript + TailwindCSS + TanStack Query
- **数据库**：PostgreSQL 16（Docker）
- **OCR**：可插拔适配器，默认 GLM-4V
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

## 快速开始

### 首次初始化

```bash
# 1. 复制环境变量并填入 GLM_API_KEY
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
- `OCR_*` 不变（OCR 是第三方 API，与部署位置无关）

前端 `pnpm build:web` 后产物为静态资源，可放任意 CDN / nginx。后端用 `uvicorn app.main:app --workers 4`（生产推荐 gunicorn + uvicorn worker）。

## Feature 2 兼容

本期不实现烹饪编排，但已为后续留好扩展位：
- API 路由统一 `/api/v1` 前缀，Feature 2 加 `/api/v1/recipes`、`/api/v1/cooking-plans` 不冲突
- 数据库通过 Alembic 管理，未来加表零阻力
- 不预先声明 Feature 2 的 Pydantic schema，避免污染 OpenAPI 契约
