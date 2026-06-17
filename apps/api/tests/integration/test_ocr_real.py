"""Real-API smoke test. Skipped unless LLM_API_KEY is set and -m integration is passed.

To run:
  1. Put a real receipt photo at tests/fixtures/receipt_sample.jpg
  2. Set LLM_API_KEY in .env (or env)
  3. pytest -m integration tests/integration/test_ocr_real.py -v
"""

import os
from pathlib import Path

import pytest

from app.services.ocr.adapter import create_ocr_adapter
from app.services.storage.image import preprocess_image

FIXTURE = Path(__file__).parent.parent / "fixtures" / "receipt_sample.jpg"


@pytest.mark.integration
async def test_real_ocr_returns_at_least_one_item():
    if not (os.environ.get("LLM_API_KEY") or os.environ.get("ARK_API_KEY_KITCHEN")):
        pytest.skip("LLM_API_KEY or ARK_API_KEY_KITCHEN not set")
    if not FIXTURE.exists():
        pytest.skip(f"put a real receipt photo at {FIXTURE}")

    raw = FIXTURE.read_bytes()
    processed, content_type = preprocess_image(raw)

    adapter = create_ocr_adapter()
    result = await adapter.extract(processed, content_type)

    assert len(result.items) >= 1, "expected at least one item from real receipt"
    first = result.items[0]
    assert first.name, "item name should not be empty"
