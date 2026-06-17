import pytest

from app.deps import get_ocr_adapter, get_storage
from app.services.storage.local import LocalFileStorage


def test_get_storage_returns_local_storage():
    storage = get_storage()
    assert isinstance(storage, LocalFileStorage)


def test_get_ocr_adapter_returns_something_with_extract():
    adapter = get_ocr_adapter()
    assert hasattr(adapter, "extract")
    assert hasattr(adapter, "provider")
