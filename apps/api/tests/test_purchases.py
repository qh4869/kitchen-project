"""Tests for /api/v1/purchases CRUD with nested items."""

import uuid
from decimal import Decimal


PURCHASES = "/api/v1/purchases"
SUPPLIERS = "/api/v1/suppliers"


def _items(**overrides):
    base = {
        "name": "番茄",
        "quantity": Decimal("1.5"),
        "unit": "kg",
        "unit_price": Decimal("6.50"),
        "category": "蔬菜",
    }
    base.update(overrides)
    return base


class _Encoder:
    """Decimal isn't JSON-serializable by default; let httpx convert via str."""

    @staticmethod
    def to_jsonable(d):
        out = {}
        for k, v in d.items():
            if isinstance(v, Decimal):
                out[k] = str(v)
            elif isinstance(v, list):
                out[k] = [
                    {kk: (str(vv) if isinstance(vv, Decimal) else vv) for kk, vv in x.items()}
                    if isinstance(x, dict)
                    else (str(x) if isinstance(x, Decimal) else x)
                    for x in v
                ]
            else:
                out[k] = v
        return out


async def test_create_and_get_with_items(client):
    supplier = (await client.post(SUPPLIERS, json={"name": "城南菜场"})).json()

    payload = _Encoder.to_jsonable(
        {
            "supplier_id": supplier["id"],
            "total_amount": Decimal("19.50"),
            "items": [_items(name="番茄"), _items(name="黄瓜", unit_price=Decimal("4.00"))],
        }
    )
    r = await client.post(PURCHASES, json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["supplier_id"] == supplier["id"]
    assert len(created["items"]) == 2
    assert {i["name"] for i in created["items"]} == {"番茄", "黄瓜"}

    # GET detail
    r2 = await client.get(f"{PURCHASES}/{created['id']}")
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 2


async def test_list_shows_item_count(client):
    p1 = _Encoder.to_jsonable({"items": [_items(), _items(name="鸡蛋")]})
    p2 = _Encoder.to_jsonable({"items": [_items()]})
    await client.post(PURCHASES, json=p1)
    await client.post(PURCHASES, json=p2)

    r = await client.get(PURCHASES)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    counts = {row["item_count"] for row in rows}
    assert counts == {1, 2}


async def test_filter_by_supplier(client):
    s1 = (await client.post(SUPPLIERS, json={"name": "A"})).json()
    s2 = (await client.post(SUPPLIERS, json={"name": "B"})).json()

    await client.post(
        PURCHASES,
        json=_Encoder.to_jsonable({"supplier_id": s1["id"], "items": [_items()]}),
    )
    await client.post(
        PURCHASES,
        json=_Encoder.to_jsonable({"supplier_id": s2["id"], "items": [_items()]}),
    )

    r = await client.get(PURCHASES, params={"supplier_id": s1["id"]})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["supplier_id"] == s1["id"]


async def test_update_marks_manual_adjustment(client):
    created = (await client.post(PURCHASES, json=_Encoder.to_jsonable({"items": [_items()]}))).json()
    r = await client.put(
        f"{PURCHASES}/{created['id']}",
        json={"total_amount": "99.99", "manual_adjustment": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_amount"] == "99.99"
    assert body["manual_adjustment"] is True


async def test_delete_cascades_items(client):
    created = (
        await client.post(
            PURCHASES, json=_Encoder.to_jsonable({"items": [_items(), _items()]})
        )
    ).json()
    r = await client.delete(f"{PURCHASES}/{created['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"{PURCHASES}/{created['id']}")
    assert r2.status_code == 404


async def test_get_not_found(client):
    r = await client.get(f"{PURCHASES}/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_create_validation_error_negative_price(client):
    bad = _Encoder.to_jsonable({"items": [_items(unit_price=Decimal("-1"))]})
    r = await client.post(PURCHASES, json=bad)
    assert r.status_code == 422
