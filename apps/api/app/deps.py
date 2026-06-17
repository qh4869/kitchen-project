from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


def get_storage():
    """FileStorage singleton. LocalFileStorage reads settings.upload_path."""
    from app.services.storage.local import LocalFileStorage
    return LocalFileStorage(root=settings.upload_path)


_OCR_ADAPTER = None


def get_ocr_adapter():
    """OcrAdapter singleton (created once per process).

    Override in tests by reassigning this function on the FastAPI app via
    `app.dependency_overrides[get_ocr_adapter] = lambda: mock_adapter`.
    """
    global _OCR_ADAPTER
    if _OCR_ADAPTER is None:
        from app.services.ocr.adapter import create_ocr_adapter
        _OCR_ADAPTER = create_ocr_adapter()
    return _OCR_ADAPTER
