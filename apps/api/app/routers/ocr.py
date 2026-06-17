"""POST /ocr/extract — read image from storage, call OCR adapter."""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_ocr_adapter, get_storage
from app.schemas.ocr import OcrExtractRequest, OcrResult
from app.services.ocr.exceptions import (
    OcrParseError,
    OcrTimeoutError,
    OcrUpstreamError,
)
from app.services.storage.adapter import FileStorage

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/extract", response_model=OcrResult)
async def extract(
    req: OcrExtractRequest,
    storage: FileStorage = Depends(get_storage),
    adapter=Depends(get_ocr_adapter),
) -> OcrResult:
    # Read image
    try:
        image_bytes = await storage.read(req.image_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="IMAGE_NOT_FOUND")

    content_type = "image/jpeg"  # /uploads always converts to JPEG
    try:
        result = await adapter.extract(image_bytes, content_type)
    except OcrTimeoutError:
        raise HTTPException(status_code=504, detail="OCR_TIMEOUT")
    except OcrUpstreamError as e:
        raise HTTPException(status_code=502, detail=f"OCR_UPSTREAM_ERROR: {e}")
    except OcrParseError:
        raise HTTPException(status_code=502, detail="OCR_PARSE_ERROR")

    # Adapter doesn't know the key; stamp it on the way out
    result.image_key = req.image_key
    return result
