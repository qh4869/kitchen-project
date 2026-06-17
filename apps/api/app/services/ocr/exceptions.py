"""OCR adapter exception hierarchy.

Router layer (routers/ocr.py) catches these and maps to HTTP status codes:
- OcrTimeoutError → 504 OCR_TIMEOUT
- OcrUpstreamError → 502 OCR_UPSTREAM_ERROR
- OcrParseError → 502 OCR_PARSE_ERROR
"""


class OcrError(Exception):
    """Base class for all OCR adapter errors."""


class OcrTimeoutError(OcrError):
    """LLM did not respond within the timeout window."""


class OcrUpstreamError(OcrError):
    """LLM returned non-2xx, or a network error occurred."""


class OcrParseError(OcrError):
    """LLM output could not be parsed as JSON."""
