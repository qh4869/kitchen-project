from uuid import uuid4

from app.db.models import Purchase


async def test_delete_item_succeeds_when_purchase_has_other_items(client):
    # Create a purchase with 2 items via the API
    r = await client.post(
        "/api/v1/purchases",
        json={
            "items": [
                {"name": "番茄", "quantity": "1", "unit_price": "5"},
                {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    purchase_id = r.json()["id"]
    item_id_to_delete = r.json()["items"][0]["id"]

    # Delete one item
    r = await client.delete(f"/api/v1/purchase-items/{item_id_to_delete}")
    assert r.status_code == 204, r.text

    # Purchase should still exist with 1 item left
    r = await client.get(f"/api/v1/purchases/{purchase_id}")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


async def test_delete_last_item_cascades_purchase_deletion(client):
    r = await client.post(
        "/api/v1/purchases",
        json={
            "items": [
                {"name": "番茄", "quantity": "1", "unit_price": "5"},
            ],
        },
    )
    assert r.status_code == 201
    purchase_id = r.json()["id"]
    item_id = r.json()["items"][0]["id"]

    r = await client.delete(f"/api/v1/purchase-items/{item_id}")
    assert r.status_code == 204

    # Purchase should be gone (cascade)
    r = await client.get(f"/api/v1/purchases/{purchase_id}")
    assert r.status_code == 404


async def test_delete_nonexistent_item_returns_404(client):
    fake_id = uuid4()
    r = await client.delete(f"/api/v1/purchase-items/{fake_id}")
    assert r.status_code == 404
    assert "PURCHASE_ITEM_NOT_FOUND" in r.json()["detail"]
