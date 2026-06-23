from datetime import datetime, timezone


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


async def _make_supplier(client, name="城南菜场"):
    r = await client.post("/api/v1/suppliers", json={"name": name})
    return r.json()["id"]


async def _make_purchase(client, *, items, supplier_id=None, purchase_time):
    """Create one purchase with the given items. items: [{name, quantity, unit_price, ...}]"""
    payload = {
        "supplier_id": supplier_id,
        "purchase_time": _iso(purchase_time),
        "items": items,
    }
    r = await client.post("/api/v1/purchases", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_search_returns_matching_items_ordered_by_time_desc(client):
    sid = await _make_supplier(client)
    older = await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )
    newer = await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1.5", "unit_price": "6.5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "番茄"
    assert body["count"] == 2
    assert body["items"][0]["purchase_id"] == newer
    assert body["items"][1]["purchase_id"] == older


async def test_search_case_insensitive(client):
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "Tomato", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "tomato"})
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = await client.get("/api/v1/prices/search", params={"q": "TOMATO"})
    assert r.status_code == 200
    assert r.json()["count"] == 1


async def test_search_substring_matches(client):
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
            {"name": "番薯", "quantity": "2", "unit_price": "3.8"},
            {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
        ],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    names = {it["name"] for it in body["items"]}
    assert names == {"番茄", "番薯"}


async def test_search_includes_supplier_name(client):
    sid = await _make_supplier(client, name="永辉超市")
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    body = r.json()
    assert body["items"][0]["supplier_name"] == "永辉超市"


async def test_search_handles_null_supplier(client):
    # Purchase with no supplier_id
    await _make_purchase(
        client,
        supplier_id=None,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "番茄"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["supplier_id"] is None
    assert body["items"][0]["supplier_name"] is None


async def test_search_default_limit_50(client):
    sid = await _make_supplier(client)
    # Insert 60 distinct items all matching "x"
    items = [
        {"name": f"x{i}", "quantity": "1", "unit_price": "1"}
        for i in range(60)
    ]
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=items,
    )

    r = await client.get("/api/v1/prices/search", params={"q": "x"})
    body = r.json()
    assert body["count"] == 50


async def test_search_custom_limit(client):
    sid = await _make_supplier(client)
    items = [
        {"name": f"x{i}", "quantity": "1", "unit_price": "1"}
        for i in range(20)
    ]
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=items,
    )

    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 10})
    body = r.json()
    assert body["count"] == 10


async def test_search_limit_zero_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 0})
    assert r.status_code == 422


async def test_search_limit_over_max_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x", "limit": 201})
    assert r.status_code == 422


async def test_search_empty_q_returns_all_items(client):
    """No q param → match-all, returns latest N items regardless of name."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
            {"name": "鸡蛋", "quantity": "10", "unit_price": "1.2"},
            {"name": "黄瓜", "quantity": "2", "unit_price": "3.8"},
        ],
    )

    r = await client.get("/api/v1/prices/search")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == ""
    assert body["count"] == 3
    names = {it["name"] for it in body["items"]}
    assert names == {"番茄", "鸡蛋", "黄瓜"}


async def test_search_whitespace_q_returns_all_items(client):
    """q='   ' strips to empty → match-all."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[{"name": "番茄", "quantity": "1", "unit_price": "5"}],
    )

    r = await client.get("/api/v1/prices/search", params={"q": "   "})
    assert r.status_code == 200
    assert r.json()["count"] == 1


async def test_search_empty_q_respects_limit(client):
    """Empty q with limit=10 truncates to 10 even when more rows exist."""
    sid = await _make_supplier(client)
    items = [
        {"name": f"x{i}", "quantity": "1", "unit_price": "1"}
        for i in range(60)
    ]
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=items,
    )

    r = await client.get("/api/v1/prices/search", params={"limit": 10})
    assert r.status_code == 200
    assert r.json()["count"] == 10


async def test_search_query_too_long_returns_422(client):
    r = await client.get("/api/v1/prices/search", params={"q": "x" * 101})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.startswith("INVALID_QUERY: query must be at most 100 chars")
    assert "101" in detail  # actual length is included


async def test_search_escapes_like_wildcards(client):
    """User searching for literal % or _ must not get wildcard behavior."""
    sid = await _make_supplier(client)
    await _make_purchase(
        client,
        supplier_id=sid,
        purchase_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        items=[
            {"name": "100%纯果汁", "quantity": "1", "unit_price": "10"},
            {"name": "番茄", "quantity": "1", "unit_price": "5"},
        ],
    )

    # Searching for literal "%" should match only the juice, not everything
    r = await client.get("/api/v1/prices/search", params={"q": "%"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["name"] == "100%纯果汁"
