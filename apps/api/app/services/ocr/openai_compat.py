"""OCR adapter that calls any OpenAI-compatible chat completions endpoint.

Works for Volcengine Ark (Doubao), OpenAI (GPT-4o), Qwen-VL, Deepseek, etc.
— only base_url, api_key, and model differ.
"""

import base64

import httpx

from app.schemas.ocr import OcrResult
from app.services.ocr.exceptions import (
    OcrParseError,
    OcrTimeoutError,
    OcrUpstreamError,
)
from app.services.ocr.parser import parse_llm_json
from app.services.ocr.prompt import SYSTEM_PROMPT, USER_PROMPT


class OpenAICompatAdapter:
    """Calls {base_url}/chat/completions with an image_url user message.

    Maps httpx errors to Ocr* exceptions (see services/ocr/exceptions.py).
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: str,
        timeout: float = 10,
        force_json: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider_name
        self.timeout = timeout
        self.force_json = force_json

    async def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        data_url = (
            f"data:{content_type};base64,{base64.b64encode(image_bytes).decode()}"
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if self.force_json:
            payload["response_format"] = {"type": "json_object"}

        content = await self._call_llm(payload)

        try:
            return parse_llm_json(content, provider=self.provider, image_key="")
        except OcrParseError:
            raise
        except Exception as e:
            raise OcrParseError(f"parse failed: {e}") from e

    async def _call_llm(self, payload: dict) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
        except httpx.TimeoutException as e:
            raise OcrTimeoutError(f"upstream timeout after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            raise OcrUpstreamError(
                f"upstream returned {e.response.status_code}"
            ) from e
        except httpx.HTTPError as e:
            raise OcrUpstreamError(f"network: {e!s}") from e

        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise OcrUpstreamError(f"unexpected upstream body: {e!s}") from e
