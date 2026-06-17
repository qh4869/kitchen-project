"""Mock OCR adapter. Returns a fixed OcrResult for local dev / unit tests."""

from app.schemas.ocr import OcrItem, OcrResult


_DEFAULT_RESULT = OcrResult(
    image_key="mock",
    supplier_name="mock 菜场",
    total_amount=None,
    items=[
        OcrItem(name="番茄（mock）", quantity=1.5, unit="kg", unit_price=6.5, category="蔬菜"),
        OcrItem(name="鸡蛋（mock）", quantity=10, unit="个", unit_price=1.2),
    ],
    raw_llm_output={"mock": True, "note": "default fixture"},
    provider="mock",
)


class MockOcrAdapter:
    """Returns a fixed OcrResult.

    If `fixture_path` is provided, loads JSON from there (must satisfy OcrResult
    schema). Otherwise returns `_DEFAULT_RESULT`.
    """

    provider = "mock"

    def __init__(self, fixture_path: str | None = None) -> None:
        self.fixture_path = fixture_path

    async def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        if not self.fixture_path:
            return _DEFAULT_RESULT.model_copy()
        # Late import to keep the happy path cheap
        import json
        with open(self.fixture_path, encoding="utf-8") as f:
            data = json.load(f)
        return OcrResult.model_validate(data)
