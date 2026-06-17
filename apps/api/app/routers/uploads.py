"""POST /uploads — accept a receipt image, preprocess, persist."""

import io
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.deps import get_storage
from app.schemas.ocr import UploadResponse
from app.services.storage.adapter import FileStorage
from app.services.storage.image import preprocess_image

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ACCEPTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    storage: FileStorage = Depends(get_storage),
) -> UploadResponse:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="UPLOAD_TOO_LARGE"
        )
    if file.content_type and file.content_type.lower() not in ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"UNSUPPORTED_IMAGE_TYPE: {file.content_type}"
        )

    try:
        processed, content_type = preprocess_image(raw)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"INVALID_IMAGE: {e!s}"
        ) from e

    today = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"{today}/{uuid4().hex}.jpg"
    await storage.save(processed, key)
    return UploadResponse(image_key=key, size=len(processed), content_type=content_type)
