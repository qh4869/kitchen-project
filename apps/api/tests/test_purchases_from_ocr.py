import io

from PIL import Image

from app.config import settings
from app.deps import get_storage
from app.services.storage.local import LocalFileStorage


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "red").save(buf, "PNG")
    return buf.getvalue()


async def test_from_ocr_creates_purchase(client, tmp_path):
    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    payload = {
        "image_key": image_key,
        "items": [
            {"name": "番茄", "quantity": "1.5", "unit": "kg", "unit_price": "6.50"},
            {"name": "鸡蛋", "quantity": "10", "unit": "个", "unit_price": "1.20"},
        ],
        "ocr_raw": {"mock": True},
    }
    r = await client.post("/api/v1/purchases/from-ocr", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["items"]) == 2
    assert body["receipt_image_path"] == image_key
    assert body["ocr_provider"] == settings.ocr_provider  # stamped from current setting


async def test_from_ocr_404_on_missing_image(client, tmp_path):
    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    payload = {
        "image_key": "2026/01/01/nonexistent.jpg",
        "items": [{"name": "x", "unit_price": "1.00"}],
    }
    r = await client.post("/api/v1/purchases/from-ocr", json=payload)
    # Missing image should NOT block save — image is optional metadata.
    # Decision: still 404 because spec says "若 image_key 不存在 → 404 IMAGE_NOT_FOUND".
    assert r.status_code == 404


async def test_from_ocr_records_manual_adjustment(client, tmp_path):
    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    payload = {
        "image_key": image_key,
        "items": [{"name": "x", "unit_price": "1.00"}],
        "manual_adjustment": True,
    }
    r = await client.post("/api/v1/purchases/from-ocr", json=payload)
    assert r.status_code == 201
    assert r.json()["manual_adjustment"] is True
