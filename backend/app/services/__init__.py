"""
Unified Services Shim Layer
This module provides backward-compatible re-exports from the central `services` package.
All core business logic, AI extraction, validation, and OCR engines reside in `services/`.
"""

from services.extraction_service import extract_document
from services.ocr_service import process_document, normalize_response
from services.validation_service import validate_document
from services.verification_service import verify_document
from services.report_document_service import generate_report_document

__all__ = [
    "extract_document",
    "process_document",
    "normalize_response",
    "validate_document",
    "verify_document",
    "generate_report_document",
]
