import pytest

from app.services.ocr.exceptions import (
    OcrError,
    OcrParseError,
    OcrTimeoutError,
    OcrUpstreamError,
)


def test_exception_hierarchy():
    assert issubclass(OcrTimeoutError, OcrError)
    assert issubclass(OcrUpstreamError, OcrError)
    assert issubclass(OcrParseError, OcrError)
    assert issubclass(OcrError, Exception)


def test_can_be_raised_and_caught_as_base():
    with pytest.raises(OcrError):
        raise OcrTimeoutError("timed out")
