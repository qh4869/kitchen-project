"""OCR adapter factory. Routes by settings.ocr_provider.

Add new OpenAI-compatible providers by extending the branch in create_ocr_adapter
— they all share OpenAICompatAdapter.
"""

from typing import Protocol, runtime_checkable

from app.config import settings
from app.schemas.ocr import OcrResult


@runtime_checkable
class OcrAdapter(Protocol):
    provider: str

    async def extract(self, image_bytes: bytes, content_type: str) -> OcrResult: ...


def create_ocr_adapter() -> OcrAdapter:
    name = settings.ocr_provider
    if name == "mock":
        from app.services.ocr.mock import MockOcrAdapter
        return MockOcrAdapter(fixture_path=settings.ocr_mock_fixture or None)
    if name in {"volcengine", "openai", "qwen", "deepseek"}:
        from app.services.ocr.openai_compat import OpenAICompatAdapter
        return OpenAICompatAdapter(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            provider_name=name,
            timeout=10,
            force_json=settings.llm_force_json,
        )
    raise ValueError(f"Unknown OCR_PROVIDER: {name!r}")
