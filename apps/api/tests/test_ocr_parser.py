import pytest

from app.schemas.ocr import OcrResult
from app.services.ocr.parser import parse_llm_json


def test_parse_pure_json():
    content = '{"items": [{"name": "番茄", "quantity": 1.5, "unit_price": 6.5}]}'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert isinstance(result, OcrResult)
    assert len(result.items) == 1
    assert result.items[0].name == "番茄"


def test_parse_strips_markdown_fence():
    content = '```json\n{"items": []}\n```'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.items == []


def test_parse_extracts_json_from_surrounding_text():
    content = 'Here is the result:\n{"items": [{"name": "鸡蛋"}]}\nHope it helps.'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.items[0].name == "鸡蛋"


def test_parse_copies_top_level_fields():
    content = '{"supplier_name": "城南菜场", "total_amount": 19.5, "items": [{"name": "番茄", "unit_price": 6.5}]}'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.supplier_name == "城南菜场"
    assert result.total_amount == 19.5


def test_parse_preserves_raw_output():
    content = '{"items": []}'
    result = parse_llm_json(content, provider="mock", image_key="x.jpg")
    assert result.raw_llm_output == {"items": []}


def test_parse_raises_on_non_json():
    with pytest.raises(Exception):
        parse_llm_json("this is plain text with no json", provider="mock", image_key="x.jpg")


def test_parse_raises_on_non_object_json():
    with pytest.raises(Exception):
        parse_llm_json("[1, 2, 3]", provider="mock", image_key="x.jpg")
