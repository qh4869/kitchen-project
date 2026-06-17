import io
from pathlib import Path

from PIL import Image

from app.deps import get_ocr_adapter, get_storage
from app.schemas.ocr import OcrItem, OcrResult
from app.services.ocr.mock import MockOcrAdapter
from app.services.storage.local import LocalFileStorage


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "red").save(buf, "PNG")
    return buf.getvalue()


async def test_extract_returns_mock_items(client, tmp_path):
    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)
    overrides[get_ocr_adapter] = lambda: MockOcrAdapter()

    # Upload first
    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    # Then OCR
    r = await client.post("/api/v1/ocr/extract", json={"image_key": image_key})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "mock"
    assert len(body["items"]) >= 1
    # Router should fill in image_key from request, not the adapter's ""
    assert body["image_key"] == image_key


async def test_extract_404_on_missing_image(client, tmp_path):
    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)
    overrides[get_ocr_adapter] = lambda: MockOcrAdapter()

    r = await client.post(
        "/api/v1/ocr/extract", json={"image_key": "2026/01/01/nonexistent.jpg"}
    )
    assert r.status_code == 404
    assert "IMAGE_NOT_FOUND" in r.json()["detail"]


async def test_extract_timeout_returns_504(client, tmp_path):
    from app.services.ocr.exceptions import OcrTimeoutError

    class _TimingOut:
        provider = "timeout-mock"
        async def extract(self, b, c):
            raise OcrTimeoutError("simulated")

    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)
    overrides[get_ocr_adapter] = lambda: _TimingOut()

    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    r = await client.post("/api/v1/ocr/extract", json={"image_key": image_key})
    assert r.status_code == 504
    assert r.json()["detail"] == "OCR_TIMEOUT"


async def test_extract_upstream_error_returns_502(client, tmp_path):
    from app.services.ocr.exceptions import OcrUpstreamError

    class _Broken:
        provider = "broken-mock"
        async def extract(self, b, c):
            raise OcrUpstreamError("500 from upstream")

    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)
    overrides[get_ocr_adapter] = lambda: _Broken()

    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    r = await client.post("/api/v1/ocr/extract", json={"image_key": image_key})
    assert r.status_code == 502
    assert r.json()["detail"].startswith("OCR_UPSTREAM_ERROR")


async def test_extract_parse_error_returns_502(client, tmp_path):
    from app.services.ocr.exceptions import OcrParseError

    class _BadParse:
        provider = "badparse-mock"
        async def extract(self, b, c):
            raise OcrParseError("bad json")

    overrides = client._transport.app.dependency_overrides
    overrides[get_storage] = lambda: LocalFileStorage(root=tmp_path)
    overrides[get_ocr_adapter] = lambda: _BadParse()

    upload = await client.post(
        "/api/v1/uploads",
        files={"file": ("r.png", _png_bytes(), "image/png")},
    )
    image_key = upload.json()["image_key"]

    r = await client.post("/api/v1/ocr/extract", json={"image_key": image_key})
    assert r.status_code == 502
    assert r.json()["detail"] == "OCR_PARSE_ERROR"
