from app.config import Settings


def test_settings_default_provider_is_volcengine(monkeypatch, tmp_path):
    # Run from an empty dir so neither ./apps/api/.env nor ./.env is picked up.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    s = Settings()
    assert s.ocr_provider == "volcengine"


def test_settings_has_llm_fields():
    s = Settings()
    assert hasattr(s, "llm_base_url")
    assert hasattr(s, "llm_api_key")
    assert hasattr(s, "llm_model")
    assert hasattr(s, "llm_force_json")
    assert hasattr(s, "ocr_mock_fixture")


def test_settings_no_legacy_glm_fields():
    s = Settings()
    assert not hasattr(s, "glm_api_key")
    assert not hasattr(s, "glm_model")
    assert not hasattr(s, "openai_api_key")
    assert not hasattr(s, "openai_model")
