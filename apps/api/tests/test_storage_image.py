import io
from pathlib import Path

import pytest
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

from app.services.storage.image import MAX_LONG_EDGE, preprocess_image


def _png_bytes(size: tuple[int, int], color="red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _heic_bytes(size: tuple[int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, "HEIF")
    return buf.getvalue()


def test_png_passes_through_as_jpeg():
    out, ct = preprocess_image(_png_bytes((100, 100)))
    assert ct == "image/jpeg"
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"


def test_heic_converted_to_jpeg():
    out, ct = preprocess_image(_heic_bytes((100, 100)))
    assert ct == "image/jpeg"
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"


def test_large_image_downscaled_to_max_long_edge():
    out, _ = preprocess_image(_png_bytes((4000, 3000)))
    img = Image.open(io.BytesIO(out))
    assert max(img.size) <= MAX_LONG_EDGE


def test_small_image_not_upscaled():
    out, _ = preprocess_image(_png_bytes((500, 400)))
    img = Image.open(io.BytesIO(out))
    # Allow 1px slack from rounding
    assert abs(img.size[0] - 500) <= 1
    assert abs(img.size[1] - 400) <= 1


def test_invalid_bytes_raises():
    with pytest.raises(Exception):
        preprocess_image(b"not an image")
