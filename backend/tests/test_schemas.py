import uuid
from datetime import datetime
from models.schemas import (
    SourceStatus,
    TokenPayload,
    SourceUploadResponse,
    DuplicateResolveRequest,
)


def test_source_status_enum():
    """Verify source status enum values."""
    assert SourceStatus.UPLOADED == "uploaded"
    assert SourceStatus.COMPLETED == "completed"
    assert SourceStatus.FAILED == "failed"


def test_token_payload_schema():
    """Verify token payload parsing."""
    payload = TokenPayload(
        officer_id="OFFICER_001",
        name_tamil="அதிகாரி",
        designation="Tahsildar",
        department="Revenue",
    )
    assert payload.officer_id == "OFFICER_001"
    assert payload.designation == "Tahsildar"


def test_duplicate_resolve_schema():
    """Verify duplicate resolve request schema."""
    req = DuplicateResolveRequest(action="reprocess")
    assert req.action == "reprocess"
    assert req.duplicate_source_id is None
