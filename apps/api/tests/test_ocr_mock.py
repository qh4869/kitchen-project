import json
from pathlib import Path

import pytest

from app.services.ocr.mock import MockOcrAdapter


async def test_mock_default_returns_two_items():
    adapter = MockOcrAdapter()
    result = await adapter.extract(b"fake-image", "image/jpeg")
    assert result.provider == "mock"
    assert len(result.items) == 2
    assert result.items[0].name


async def test_mock_ignores_image_bytes():
    adapter = MockOcrAdapter()
    r1 = await adapter.extract(b"a", "image/jpeg")
    r2 = await adapter.extract(b"b", "image/png")
    assert r1.items == r2.items


async def test_mock_loads_from_fixture(tmp_path: Path):
    fixture = tmp_path / "fx.json"
    fixture.write_text(
        json.dumps(
            {
                "image_key": "fx.jpg",
                "items": [{"name": "fixture-item", "unit_price": 1.0}],
                "provider": "mock",
                "raw_llm_output": {"from": "fixture"},
            }
        ),
        encoding="utf-8",
    )
    adapter = MockOcrAdapter(fixture_path=str(fixture))
    result = await adapter.extract(b"img", "image/jpeg")
    assert result.items[0].name == "fixture-item"
    assert result.raw_llm_output == {"from": "fixture"}


async def test_mock_fixture_missing_file_raises():
    adapter = MockOcrAdapter(fixture_path="/nonexistent/path.json")
    with pytest.raises(FileNotFoundError):
        await adapter.extract(b"img", "image/jpeg")
