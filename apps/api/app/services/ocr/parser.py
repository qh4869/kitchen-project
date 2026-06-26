"""Parse LLM output into OcrResult, with multiple fallbacks.

Tries in order:
1. Direct json.loads
2. Strip markdown fence (```json ... ```)
3. Regex extract first {...} block
4. Raise OcrParseError
"""

import json
import re
from typing import Any

from app.schemas.ocr import OcrResult
from app.services.ocr.exceptions import OcrParseError

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_object(content: str) -> dict[str, Any]:
    # 1. Direct parse
    try:
        v = json.loads(content)
        if isinstance(v, dict):
            return v
    except json.JSONDecodeError:
        pass

    # 2. Markdown fence
    m = _FENCE_RE.search(content)
    if m:
        try:
            v = json.loads(m.group(1))
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            pass

    # 3. First {...} block
    m = _OBJECT_RE.search(content)
    if m:
        try:
            v = json.loads(m.group(0))
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            pass

    raise OcrParseError(f"could not parse JSON from LLM output: {content[:120]!r}")


def parse_llm_json(content: str, *, provider: str, image_key: str) -> OcrResult:
    obj = _extract_json_object(content)
    return OcrResult(
        image_key=image_key,
        supplier_name=obj.get("supplier_name"),
        purchase_time=obj.get("purchase_time"),
        items=obj.get("items") or [],
        raw_llm_output=obj,
        provider=provider,
    )
