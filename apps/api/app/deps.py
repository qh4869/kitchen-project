from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """Re-export of get_session for FastAPI dependency injection.

    Kept as a separate name so test code can override `app.deps.get_db`
    without touching the underlying session factory.
    """
    async for session in get_session():
        yield session
