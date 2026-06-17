import base64
import json

import httpx
import pytest
import respx

from app.services.ocr.exceptions import OcrParseError, OcrTimeoutError, OcrUpstreamError
from app.services.ocr.openai_compat import OpenAICompatAdapter


def _adapter():
    return OpenAICompatAdapter(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="test-model",
        provider_name="test",
        timeout=2,
        force_json=True,
    )


def _ok_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


async def test_extracts_items_from_llm_json():
    body = json.dumps({"items": [{"name": "番茄", "quantity": 1.5, "unit_price": 6.5}]})
    with respx.mock:
        route = respx.post("https://api.example.com/v1/chat/completions").respond(
            200, json=_ok_response(body)
        )
        r = await _adapter().extract(b"img", "image/jpeg")
    assert route.called
    assert r.items[0].name == "番茄"
    assert r.provider == "test"


async def test_request_body_includes_image_as_data_url():
    body = json.dumps({"items": []})
    captured: dict = {}
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").respond(
            200, json=_ok_response(body)
        ).mock(side_effect=lambda req: captured.update(json.loads(req.read())) or httpx.Response(200, json=_ok_response(body)))
        await _adapter().extract(b"abc", "image/jpeg")
    assert captured["model"] == "test-model"
    assert captured["temperature"] == 0
    assert captured["response_format"] == {"type": "json_object"}
    # Last user message should contain a data URL
    user_msg = captured["messages"][-1]["content"][-1]
    assert user_msg["type"] == "image_url"
    expected_prefix = "data:image/jpeg;base64," + base64.b64encode(b"abc").decode()
    assert user_msg["image_url"]["url"] == expected_prefix


async def test_force_json_false_omits_response_format():
    adapter = OpenAICompatAdapter(
        base_url="https://api.example.com/v1",
        api_key="k",
        model="m",
        provider_name="t",
        timeout=2,
        force_json=False,
    )
    captured: dict = {}
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").respond(
            200, json=_ok_response('{"items": []}')
        ).mock(side_effect=lambda req: captured.update(json.loads(req.read())) or httpx.Response(200, json=_ok_response('{"items": []}')))
        await adapter.extract(b"x", "image/jpeg")
    assert "response_format" not in captured


async def test_timeout_raises_ocr_timeout():
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        with pytest.raises(OcrTimeoutError):
            await _adapter().extract(b"x", "image/jpeg")


async def test_500_raises_ocr_upstream():
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").respond(500, text="boom")
        with pytest.raises(OcrUpstreamError):
            await _adapter().extract(b"x", "image/jpeg")


async def test_unparseable_content_raises_ocr_parse():
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").respond(
            200, json=_ok_response("not json at all")
        )
        with pytest.raises(OcrParseError):
            await _adapter().extract(b"x", "image/jpeg")


async def test_network_error_raises_ocr_upstream():
    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("no route")
        )
        with pytest.raises(OcrUpstreamError):
            await _adapter().extract(b"x", "image/jpeg")
