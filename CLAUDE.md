# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project scope

Family cooking-assistant web app. **Feature 1 only (智慧采购 / procurement):** suppliers CRUD, purchases CRUD, OCR-driven receipt logging, (Phase 3, pending) price dashboard. **Feature 2 (烹饪编排 / cooking orchestration) is explicitly out of scope** — only the `/api/v1` prefix and Alembic DB are reserved for it. Do not create Feature 2 routes, schemas, or tables.

## Common commands

All commands run from repo root unless noted.

```bash
pnpm db:up                         # start PostgreSQL (docker compose)
pnpm dev                           # api (3000) + web (5173) concurrently
pnpm dev:api                       # uvicorn --reload (cd apps/api first)
pnpm dev:web                       # vite dev server
pnpm build:web                     # tsc -b && vite build
pnpm gen:types                     # fetch /openapi.json → packages/api-types/src/index.ts
pnpm db:migrate                    # alembic upgrade head
pnpm db:revision -m "msg"          # autogenerate migration from ORM diff
pnpm test:api                      # cd apps/api && uv run pytest

# Single test / file
cd apps/api && python -m uv run pytest tests/test_ocr_parser.py::test_parse_pure_json -v

# Real-API integration test (requires LLM_API_KEY in .env or shell)
cd apps/api && python -m uv run pytest -m integration tests/integration/test_ocr_real.py -v
```

Tests that touch the DB (`conftest.py` `client` fixture) need `kitchen-postgres` running and will wipe `purchase_items` / `purchases` / `suppliers` before each test. Integration tests are skipped unless `-m integration` is passed.

## Architecture

**Monorepo, two languages, single source of truth for the API contract:**
- `apps/api` (Python 3.13 + FastAPI, managed by `uv`)
- `apps/web` (React 18 + Vite, pnpm workspace package `@kitchen/web`)
- `packages/api-types` — TS types generated from FastAPI's `/openapi.json` via `openapi-typescript`. Never hand-edit; run `pnpm gen:types` (needs the API server running).

**Async end-to-end:** SQLAlchemy 2.0 async + asyncpg + FastAPI async handlers. `app/db/session.py` exposes the engine + `get_session()`; `app/deps.py:get_db()` re-exports it so tests can override via `app.dependency_overrides`.

**OCR pipeline (Phase 2):** upload → preprocess → LLM extract → user edit → persist.

```
POST /api/v1/uploads            → Pillow preprocess (services/storage/image.py)
                                   → LocalFileStorage.save
POST /api/v1/ocr/extract        → storage.read + adapter.extract
POST /api/v1/purchases/from-ocr → verifies image exists, stamps ocr_provider
                                   from settings, persists items
```

**Adapter pattern (key design):**
- `app/services/ocr/adapter.py` defines `OcrAdapter` Protocol + `create_ocr_adapter()` factory routed by `settings.ocr_provider`.
- `OpenAICompatAdapter` covers Volcengine Ark / OpenAI / Qwen / Deepseek — only `base_url`/`api_key`/`model` differ; the provider name is just a label.
- `MockOcrAdapter` returns a canned `OcrResult` for local dev without an API key (`OCR_PROVIDER=mock`).
- `OcrTimeoutError` → 504, `OcrUpstreamError` → 502, `OcrParseError` → 502 — mapped in `routers/ocr.py`.

**Storage abstraction:** `FileStorage` Protocol in `services/storage/adapter.py`; only `LocalFileStorage` today. `STORAGE_DRIVER=s3` is a future option, do not implement unless asked.

**Dependency injection:** `get_db`, `get_storage`, `get_ocr_adapter` in `app/deps.py`. The OCR adapter is a module-level singleton (`_OCR_ADAPTER`) — once created it's pinned for the process lifetime. To swap providers in tests, override via `app.dependency_overrides[get_ocr_adapter]`; to swap in dev, restart the API process.

## Configuration gotchas

- **Settings loads `.env` from two locations**: `env_file=(".env", "../../.env")` in `app/config.py`. This is intentional — uvicorn runs from `apps/api/` (per `pnpm dev:api`), so a single root `.env` works whether you launch from project root or `apps/api`. Edit the root `.env`, not `apps/api/.env`.
- **API key aliases:** `llm_api_key` accepts either `LLM_API_KEY` (typically in `.env`) or `ARK_API_KEY_KITCHEN` (shell env, preferred for secrets not committed anywhere).
- **Default `OCR_PROVIDER=volcengine`** with `LLM_MODEL=doubao-seed-2-0-mini-260428`. The model ID is lowercase with date suffix — do not "fix" it to `Doubao-Seed-2.0-mini`; that 404s against Ark.
- **`.env` is gitignored** (line 30 of `.gitignore`). The file exists locally but is not tracked.
- **Integration test gates on `settings.llm_api_key`, not `os.environ`** — pydantic-settings does not inject `.env` values into `os.environ`, so a `os.environ.get(...)` check would always skip when the key lives only in `.env`.

## Dev-server quirks (Windows)

- **`uvicorn --reload` watches `.py` files only.** Editing `.env` does not trigger reload — fully stop and restart `pnpm dev:api` to pick up env changes.
- **On Windows the uvicorn worker can survive its parent process.** If you see stale behavior after restarting `pnpm dev:api`, run `taskkill //F //IM python.exe` to clear all Python processes, then start fresh. Stale `__pycache__` can also pin old code — safe to delete under `apps/api/app/`.
- **`uv` is not on PATH on this machine.** Always invoke as `python -m uv ...` (the `pnpm` scripts already do this).
- **Docker Hub is blocked on this network.** If `pnpm db:up` fails to pull `postgres:16-alpine`, configure `docker.m.daocloud.io` as a registry mirror in Docker Desktop settings (not `daemon.json` — that file is ignored by Docker Desktop).
- **PyPI is slow / unreliable from China.** Inside `Dockerfile.api`, `pip install` and `uv sync` both default to `pypi.org/files.pythonhosted.org` which times out or crawls. The Dockerfile sets `PIP_INDEX_URL` and `UV_INDEX_URL` env vars to `https://mirrors.aliyun.com/pypi/simple/` to fix this. If you remove those env vars, the build hangs at `RUN pip install uv` (~25 MB wheel taking 10+ minutes).

## Test discipline

- New OCR/storage/service code: write the failing test first (tests under `apps/api/tests/`), implement, run pytest. The Phase 2 plan in `docs/superpowers/plans/` follows TDD step-by-step and is the reference for where each piece lives.
- For router tests, override storage to a `tmp_path` `LocalFileStorage` so the test doesn't write to `./uploads`. See `tests/test_uploads.py` for the pattern: `client._transport.app.dependency_overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)`.
- `httpx`'s `Request.read()` returns `bytes`, not a JSON-parsed object. Use `json.loads(req.read())` in `respx` side-effect callbacks.

## Memory

The user maintains a project-state memory at `~/.claude/projects/D--workspace-kitchen-project/memory/kitchen-project-state.md`. Consult it for stack rationale and phase status. The plan file `docs/superpowers/plans/2026-06-17-phase2-ocr.md` documents Phase 2 task-by-task.
