from app.config import settings
from app.services.ocr.adapter import create_ocr_adapter
from app.services.ocr.mock import MockOcrAdapter
from app.services.ocr.openai_compat import OpenAICompatAdapter


def test_factory_returns_mock_when_provider_is_mock(monkeypatch):
    monkeypatch.setattr(settings, "ocr_provider", "mock")
    adapter = create_ocr_adapter()
    assert isinstance(adapter, MockOcrAdapter)


def test_factory_returns_openai_compat_for_volcengine(monkeypatch):
    monkeypatch.setattr(settings, "ocr_provider", "volcengine")
    monkeypatch.setattr(settings, "llm_base_url", "https://ark.cn-beijing.volces.com/api/v3")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_model", "doubao-1.5-vision-pro")
    monkeypatch.setattr(settings, "llm_force_json", True)
    adapter = create_ocr_adapter()
    assert isinstance(adapter, OpenAICompatAdapter)
    assert adapter.provider == "volcengine"
    assert adapter.model == "doubao-1.5-vision-pro"


def test_factory_unknown_provider_raises():
    import pytest
    settings.__dict__["ocr_provider"] = "bogus"
    try:
        with pytest.raises(ValueError):
            create_ocr_adapter()
    finally:
        settings.__dict__["ocr_provider"] = "volcengine"
