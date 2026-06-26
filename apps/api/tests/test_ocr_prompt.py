from app.services.ocr.prompt import SYSTEM_PROMPT, USER_PROMPT


def test_system_prompt_mentions_json():
    assert "JSON" in SYSTEM_PROMPT or "json" in SYSTEM_PROMPT.lower()


def test_system_prompt_lists_required_fields():
    assert "supplier_name" in SYSTEM_PROMPT
    assert "purchase_time" in SYSTEM_PROMPT
    assert "items" in SYSTEM_PROMPT


def test_system_prompt_forbids_fabrication():
    assert "null" in SYSTEM_PROMPT
    assert "禁止编造" in SYSTEM_PROMPT or "不要编" in SYSTEM_PROMPT


def test_user_prompt_is_brief():
    assert len(USER_PROMPT) < 200
