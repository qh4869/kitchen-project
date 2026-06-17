"""Pillow preprocessing for uploaded receipt images.

Responsibilities:
- Register HEIC/HEIF opener (iPhone default format)
- Correct EXIF orientation (phones store landscape + rotation flag)
- Downscale so longest edge <= MAX_LONG_EDGE (controls LLM token cost)
- Convert to RGB JPEG quality 85 (uniform output; HEIC → JPEG avoids browser issues)
"""

import io

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# Idempotent — safe to call at module import
register_heif_opener()

MAX_LONG_EDGE = 2000
JPEG_QUALITY = 85


def preprocess_image(raw: bytes) -> tuple[bytes, str]:
    """Returns (processed_bytes, content_type). Always JPEG output."""
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)  # apply EXIF rotation, strip the tag

    if max(img.size) > MAX_LONG_EDGE:
        ratio = MAX_LONG_EDGE / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    if img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue(), "image/jpeg"
