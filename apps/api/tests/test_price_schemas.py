from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from app.schemas.price import SearchResult, SearchResultItem


def test_search_result_item_accepts_all_fields():
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1.5"),
        unit="kg",
        unit_price=Decimal("6.50"),
        category="蔬菜",
        brand=None,
        supplier_id=uuid4(),
        supplier_name="城南菜场",
        purchase_id=uuid4(),
        purchase_item_id=uuid4(),
        purchase_time=datetime(2026, 6, 17, 9, 32, 29),
        receipt_image_path=None,
    )
    assert item.name == "番茄"
    assert item.quantity == Decimal("1.5")
    assert item.supplier_name == "城南菜场"


def test_search_result_item_allows_null_supplier():
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1"),
        unit=None,
        unit_price=Decimal("5"),
        category=None,
        brand=None,
        supplier_id=None,
        supplier_name=None,
        purchase_id=uuid4(),
        purchase_item_id=uuid4(),
        purchase_time=datetime(2026, 6, 17),
        receipt_image_path=None,
    )
    assert item.supplier_id is None
    assert item.supplier_name is None
    assert item.unit is None


def test_search_result_empty_items():
    r = SearchResult(query="nothing", count=0, items=[])
    assert r.count == 0
    assert r.items == []
    assert r.query == "nothing"


def test_search_result_decimal_serializes_as_str():
    """FastAPI's jsonable_encoder turns Decimal into string for JSON output."""
    item = SearchResultItem(
        name="番茄",
        quantity=Decimal("1.5"),
        unit="kg",
        unit_price=Decimal("6.50"),
        category=None,
        brand=None,
        supplier_id=None,
        supplier_name=None,
        purchase_id=uuid4(),
        purchase_item_id=uuid4(),
        purchase_time=datetime(2026, 6, 17),
        receipt_image_path=None,
    )
    encoded = jsonable_encoder(item)
    assert encoded["quantity"] == "1.5"
    assert encoded["unit_price"] == "6.50"
    assert isinstance(encoded["quantity"], str)
