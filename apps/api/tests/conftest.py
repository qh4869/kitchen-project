"""Pytest fixtures.

Tests assume PostgreSQL is reachable via DATABASE_URL (docker compose up postgres).
Each test gets a fresh async engine + session factory tied to its own event loop,
so asyncpg doesn't outlive the loop pytest-asyncio closes after each test.

`get_db` is overridden in the FastAPI app to use the per-test session factory,
keeping tests isolated from the production session factory in app/db/session.py.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.deps import get_db
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    TestSession = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Wipe before each test, in dependency-safe order
        async with TestSession() as session:
            await session.execute(text("DELETE FROM purchase_items"))
            await session.execute(text("DELETE FROM purchases"))
            await session.execute(text("DELETE FROM suppliers"))
            await session.commit()
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
