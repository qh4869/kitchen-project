import io
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image
import pytest

from app.deps import get_storage
from app.services.storage.local import LocalFileStorage


def _png(size=(100, 100)):
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, "PNG")
    return buf.getvalue()


async def test_uploads_png_returns_image_key(client, tmp_path):
    # Override storage to use tmp_path so we don't pollute ./uploads
    app_overrides_storage = client._transport.app.dependency_overrides
    app_overrides_storage[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    r = await client.post(
        "/api/v1/uploads",
        files={"file": ("receipt.png", _png(), "image/png")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["content_type"] == "image/jpeg"
    assert body["size"] > 0
    assert body["image_key"].endswith(".jpg")
    # Date-prefixed path
    today = datetime.utcnow().strftime("%Y/%m/%d")
    assert body["image_key"].startswith(today + "/")


async def test_uploads_too_large_rejected(client, tmp_path):
    app_overrides_storage = client._transport.app.dependency_overrides
    app_overrides_storage[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    big = b"\x00" * (10 * 1024 * 1024 + 1)
    r = await client.post(
        "/api/v1/uploads",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413 or r.status_code == 400


async def test_uploads_invalid_image_rejected(client, tmp_path):
    app_overrides_storage = client._transport.app.dependency_overrides
    app_overrides_storage[get_storage] = lambda: LocalFileStorage(root=tmp_path)

    r = await client.post(
        "/api/v1/uploads",
        files={"file": ("notimage.png", b"definitely not an image", "image/png")},
    )
    assert r.status_code == 400
    assert "INVALID_IMAGE" in r.json()["detail"]
