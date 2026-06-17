"""Tests for /api/v1/suppliers CRUD."""

import uuid


SUPPLIERS = "/api/v1/suppliers"


async def test_list_empty(client):
    r = await client.get(SUPPLIERS)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_and_get(client):
    payload = {
        "name": "城南菜场",
        "address": "城南街道",
        "preferences": ["蔬菜便宜", "海鲜新鲜"],
        "business_hours": ["周一至周日 06:00-20:00"],
    }
    r = await client.post(SUPPLIERS, json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "城南菜场"
    assert created["preferences"] == ["蔬菜便宜", "海鲜新鲜"]
    assert uuid.UUID(created["id"])

    # GET detail
    r2 = await client.get(f"{SUPPLIERS}/{created['id']}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "城南菜场"


async def test_list_with_search(client):
    await client.post(SUPPLIERS, json={"name": "城南菜场"})
    await client.post(SUPPLIERS, json={"name": "城北超市"})

    r = await client.get(SUPPLIERS, params={"q": "城北"})
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert names == ["城北超市"]


async def test_update(client):
    create = (await client.post(SUPPLIERS, json={"name": "旧名"})).json()
    r = await client.put(f"{SUPPLIERS}/{create['id']}", json={"name": "新名"})
    assert r.status_code == 200
    assert r.json()["name"] == "新名"


async def test_delete(client):
    create = (await client.post(SUPPLIERS, json={"name": "待删"})).json()
    r = await client.delete(f"{SUPPLIERS}/{create['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"{SUPPLIERS}/{create['id']}")
    assert r2.status_code == 404


async def test_get_not_found(client):
    r = await client.get(f"{SUPPLIERS}/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_create_validation_error(client):
    r = await client.post(SUPPLIERS, json={"name": ""})
    assert r.status_code == 422
