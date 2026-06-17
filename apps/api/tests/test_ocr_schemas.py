from decimal import Decimal

from app.schemas.ocr import OcrItem, OcrExtractRequest, OcrResult, PurchaseFromOcrRequest


def test_ocr_item_allows_null_optionals():
    item = OcrItem(name="番茄")
    assert item.name == "番茄"
    assert item.quantity is None
    assert item.unit_price is None


def test_ocr_result_with_empty_items():
    r = OcrResult(image_key="x.jpg", items=[], raw_llm_output={}, provider="mock")
    assert r.items == []
    assert r.purchase_time is None


def test_ocr_extract_request_validation():
    req = OcrExtractRequest(image_key="2026/06/17/abc.jpg")
    assert req.image_key == "2026/06/17/abc.jpg"


def test_purchase_from_ocr_request_minimal():
    req = PurchaseFromOcrRequest(
        image_key="x.jpg",
        items=[{"name": "番茄", "quantity": "1.5", "unit_price": "6.50"}],
    )
    assert req.supplier_id is None
    assert req.ocr_raw is None
    assert req.items[0].name == "番茄"


def test_purchase_from_ocr_request_rejects_empty_items():
    import pytest
    with pytest.raises(ValueError):
        PurchaseFromOcrRequest(image_key="x.jpg", items=[])
