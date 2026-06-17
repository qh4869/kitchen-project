from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import purchases, suppliers, uploads


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure upload directory exists at startup
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="烹饪助手 · 智慧采购 API",
    version="0.1.0",
    description="PRD §4.1 智慧采购模块后端",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounted at /api/v1 so Feature 2 can add /api/v1/recipes etc. without conflict.
api_prefix = "/api/v1"
app.include_router(suppliers.router, prefix=api_prefix)
app.include_router(purchases.router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)

# Serve uploaded receipt images. In production, swap to S3/OSS via STORAGE_DRIVER.
app.mount("/static", StaticFiles(directory=str(settings.upload_path)), name="static")


@app.get("/")
async def root() -> dict:
    return {"name": "kitchen-api", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
