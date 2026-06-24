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

## 部署到阿里云 ECS

### 架构

```
[Internet] → ECS :80
              ↓
       ┌──────────────────────────────────────────┐
       │ web container (nginx:alpine)             │
       │  ├ /              → baked 静态文件       │
       │  ├ /api/v1/*      → 反代到 api:3000      │
       │  └ /static/*      → 反代到 api:3000      │
       └──────┬───────────────────────────────────┘
              ↓ (docker internal network)
       ┌──────────────────────────────────────────┐
       │ api container (python:3.13-slim)         │
       │  uvicorn --workers 2                     │
       │  volume: /app/uploads                    │
       └──────┬───────────────────────────────────┘
              ↓
       ┌──────────────────────────────────────────┐
       │ postgres container (16-alpine)           │
       │  volume: pgdata                          │
       └──────────────────────────────────────────┘
```

3 个 docker 容器跑在同一台 ECS 上。HTTP-only v1，HTTPS / 域名后续扩展位。

### 部署文件清单（已在 repo 里）

| 文件 | 用途 |
|---|---|
| `Dockerfile.api` | Python 3.13 + uv sync + uvicorn (2 workers, 无 --reload) |
| `Dockerfile.web` | 多阶段：node:22 build → nginx:alpine serve + 反代 |
| `nginx/kitchen.conf` | `/` + `/api/` + `/static/` 三个 location，12M body，60s 超时 |
| `docker-compose.prod.yml` | 3 服务编排 + pgdata/uploads 两个 named volumes |
| `.env.example.prod` | 生产环境变量模板（DB 密码、LLM key、ECS IP） |
| `.dockerignore` | 排除 venv / node_modules / dist / .git 等 |
| `scripts/deploy.sh` | ECS 上直接跑的更新脚本（git pull + rebuild + migrate + prune） |
| `scripts/backup-db.sh` | DB 每日备份（cron 调用） |

### ECS 准备（一次性）

1. **买 ECS**：2 vCPU / 4 GB / 40 GB 系统盘 / Ubuntu 22.04 LTS / 北京或杭州区域（离 Volcengine Ark OCR 近）
2. **安全组**：开 22（限你源 IP）+ 80（HTTP）。**不要**开 5432 / 3000（docker 内部网络用，外部访问不到也不需要）
3. **SSH 登录后装 Docker + 配镜像加速**（China 网络必需）：
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-vpn git
   sudo usermod -aG docker $USER
   # 退出重登让 group 生效

   # Docker Hub 镜像加速（China 网络必需，否则拉不到 postgres / python / nginx / node 镜像）
   echo '{"registry-mirrors": ["https://docker.m.daocloud.io"]}' | sudo tee /etc/docker/daemon.json
   sudo systemctl restart docker
   ```

   **PyPI 镜像在 Dockerfile 里已经配好了**（`tsinghua` mirror via `UV_INDEX_URL` env var），不用 ECS 上手动配。注意 `Dockerfile.api` 用的是 `uv pip install` 而非 `uv sync` —— `uv.lock` 里有写死的 `files.pythonhosted.org` URL，`uv sync` 会直连绕过 env var。详见 `CLAUDE.md` 的 "Dev-server quirks" 段。

### 首次部署

```bash
# 在 ECS 上：
git clone git@github.com:qh4869/kitchen-project.git ~/kitchen-project
cd ~/kitchen-project

cp .env.example.prod .env
nano .env       # 见下方"生产 .env 字段说明"
chmod 600 .env  # 限制权限

docker compose -f docker-compose.prod.yml up -d --build
# 首次 build 约 5 分钟（拉镜像 + pnpm install + uv sync + vite build）

docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head

# 加 DB 每日备份 cron
crontab -e
# 加入：0 3 * * * /home/$USER/kitchen-project/scripts/backup-db.sh
```

### 验证

- `curl http://<ECS_IP>/health` → `{"status":"ok"}`
- `curl http://<ECS_IP>/api/v1/prices/search` → `{"query":"","count":N,"items":[...]}`
- 浏览器开 `http://<ECS_IP>/`，4 个 nav 都能点开，OCR 上传 / 手工记账 / 价格搜索全跑通

### 后续更新（在 ECS 上跑）

SSH 进 ECS 后，任意目录下执行：

```bash
bash ~/kitchen-project/scripts/deploy.sh
# 或
bash /path/to/kitchen-project/scripts/deploy.sh
```

脚本用 `BASH_SOURCE[0]` 定位项目根，cwd 不影响。

`deploy.sh` 做：`git pull` → `docker compose up -d --build` → `alembic upgrade head` → `docker image prune -f`（清理 dangling 镜像）。完成后打印 `Deploy complete.`。

### 生产 `.env` 字段说明

复制 `.env.example.prod` 为 `.env` 后，需要填/改这几个字段：

| 字段 | 怎么填 | 用途 |
|---|---|---|
| `POSTGRES_USER` | `kitchen`（保持默认） | compose 初始化 PG 时创建的超级用户名 |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` 生成的随机串 | PG 超级用户密码；compose 组装进 `DATABASE_URL` |
| `POSTGRES_DB` | `kitchen`（保持默认） | compose 初始化时创建的默认库 |
| `LLM_API_KEY` | `ark-...` 开头的 Volcengine Ark key | OCR 调用认证；同本地的那个 |
| `LLM_MODEL` | `doubao-seed-2-0-mini-260428`（已填好，勿改） | Ark 模型 ID；老的 `Doubao-Seed-2.0-mini` 会 404 |
| `OCR_PROVIDER` | `volcengine`（保持默认） | 生产必须真实调用，不用 `mock` |
| `LLM_BASE_URL` | `https://ark.cn-beijing.volces.com/api/v3`（保持默认） | Ark OpenAI 兼容端点 |
| `LLM_FORCE_JSON` | `true`（保持默认） | 强制 LLM 返回 JSON 对象 |
| `STORAGE_DRIVER` | `local`（保持默认） | 上传图片存本地磁盘；未来切 OSS 时改 `s3` |
| `UPLOAD_DIR` | `/app/uploads`（保持默认） | 容器内绝对路径；compose 把 volume 挂到这里 |
| `WEB_ORIGIN` | `http://<ECS_IP>` | CORS 允许列表；同源时实际不生效，但配着防御 |

注：`.env` 里**不要**写 `DATABASE_URL`，compose 会用 `${POSTGRES_USER}` 等组装好注入容器，覆盖优先级最高。

### 运维

**查日志**：
```bash
docker compose -f docker-compose.prod.yml logs -f api     # API 日志
docker compose -f docker-compose.prod.yml logs -f web     # nginx 日志
```

**DB 备份恢复**：
```bash
gunzip -c /mnt/data/backups/kitchen-2026-06-23.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U kitchen kitchen
```

**升级 HTTPS（未来）**：
1. 域名 ICP 备案（1-2 周）
2. A 记录指向 ECS 公网 IP
3. 改 `nginx/kitchen.conf` 加 `listen 443 ssl;` + 证书路径 + 80→443 跳转
4. 安全组开 443

## 本地 vs 生产 环境对比

| | 本地 dev | 生产 prod |
|---|---|---|
| **API 进程** | 本机 uvicorn `--reload`（`pnpm dev:api`） | docker 容器 `kitchen-api`，`uvicorn --workers 2`（无 reload） |
| **前端** | Vite dev server :5173（HMR） | nginx 容器 :80，服务构建产物静态文件 |
| **Postgres** | docker 容器，暴露 5432 到 `localhost` | docker 容器，仅 docker 内部网络可达 |
| **API → DB 连接** | `localhost:5432` | `postgres:5432`（按 compose 服务名解析） |
| **前端 → API** | Vite dev proxy `/api → :3000` | nginx `location /api/ → api:3000` 反代 |
| **图片存储** | `./uploads`（项目目录下） | docker volume `uploads`，挂到容器 `/app/uploads` |
| **CORS** | 跨 :5173 ↔ :3000，必需 | 同源（都走 :80），实际不触发；配 `WEB_ORIGIN` 仅防御 |
| **环境变量来源** | `.env`（来自 `.env.example`） | `.env`（来自 `.env.example.prod`）+ compose `environment:` 注入 |
| **DB 凭据** | `kitchen/kitchen`（默认弱密码，仅本机） | 强随机密码（`openssl rand -base64 24`） |
| **`DATABASE_URL`** | `.env` 里完整 URL | compose 用 `${POSTGRES_*}` 组装，**不要**在 `.env` 里写 |
| **OCR provider** | 可选 `mock`（免 key 测流程） | 必须 `volcengine`（真实付费调用） |
| **测试数据** | `pytest` 前会 wipe 表 | 真实数据；靠 `scripts/backup-db.sh` 每日备份 |

### `.env` 选哪个模板

| 文件 | 何时用 |
|---|---|
| `.env.example` | 本地 dev，复制成 `.env`，配合 `pnpm dev` |
| `.env.example.prod` | ECS 生产，复制成 `.env`，配合 `docker compose -f docker-compose.prod.yml` |

两个文件**互不干扰**：
- 本地的 `pnpm dev` 和 `docker-compose.yml`（仅起 PG）**完全不读** `.env.example.prod`
- 生产 compose **完全不读** `.env.example`

如果你在本地不小心把 `.env` 改成了 prod 模板的内容（含 `POSTGRES_PASSWORD` 等字段），`pnpm dev` 会找不到 `DATABASE_URL` 启动失败 —— 这时把 `.env` 删掉重新 `cp .env.example .env` 即可。

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
