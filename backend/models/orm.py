import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey,
    Index, BigInteger, LargeBinary, UniqueConstraint
)
from sqlalchemy.types import TypeDecorator, CHAR, JSON, String as SAString
from models.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(str(value))
            except (ValueError, AttributeError):
                return value
        return value


class SafeJSON(TypeDecorator):
    """Uses JSONB on PostgreSQL and JSON on SQLite/others."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class SafeArray(TypeDecorator):
    """Uses ARRAY on PostgreSQL, JSON list on SQLite/others."""
    impl = JSON
    cache_ok = True

    def __init__(self, item_type=SAString, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(self.item_type))
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name != "postgresql" and isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return [value]
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return [value]
        return list(value)


class SafeINET(TypeDecorator):
    """Uses INET on PostgreSQL, String(45) on SQLite/others."""
    impl = SAString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import INET
            return dialect.type_descriptor(INET())
        else:
            return dialect.type_descriptor(SAString(45))


class SafeVector(TypeDecorator):
    """Uses pgvector Vector on PostgreSQL (if available), JSON float array on SQLite/others."""
    impl = JSON
    cache_ok = True

    def __init__(self, dim=384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except Exception:
                return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name != "postgresql":
            if isinstance(value, (list, tuple)):
                return list(value)
            elif isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
        return value


class MasterLocation(Base):
    __tablename__ = "master_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_code = Column(String(50))
    district_name_tamil = Column(String(200))
    district_name_en = Column(String(200))
    division_code = Column(String(50))
    division_name_tamil = Column(String(200))
    division_name_en = Column(String(200))
    taluk_code = Column(String(50))
    taluk_name_tamil = Column(String(200))
    taluk_name_en = Column(String(200))
    firka_code = Column(String(50))
    firka_name_tamil = Column(String(200))
    firka_name_en = Column(String(200))
    block_code = Column(String(50))
    block_name_tamil = Column(String(200))
    block_name_en = Column(String(200))
    village_code = Column(String(50))
    village_name_tamil = Column(String(200))
    village_name_en = Column(String(200))
    local_body_type = Column(String(200))
    ward_no = Column(Integer)
    ward_name_tamil = Column(String(200))
    ward_name_en = Column(String(200))
    pincode = Column(String(20))
    search_text = Column(Text)
    embedding = Column(SafeVector(384))
    sub_departments = Column(String(500))


class Officer(Base):
    __tablename__ = "officers"

    officer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=True)
    name_tamil = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    mobile = Column(String(20), nullable=True)
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    status = Column(String(20), default="Active")
    taluk_access = Column(SafeArray(String(10)))
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    officer_id = Column(String(50), ForeignKey("officers.officer_id"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer)
    file_hash = Column(String(64), unique=True)
    phash = Column(String(64), nullable=True)
    page_count = Column(Integer, default=0)
    status = Column(String(30), default="uploaded")
    content_fingerprint = Column(SafeJSON, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))



class OCRResult(Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        UniqueConstraint("source_id", "page_number", name="uq_ocr_source_page"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(GUID(), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    full_text = Column(Text)
    blocks = Column(SafeJSON)
    tables = Column(SafeJSON)
    avg_confidence = Column(Float)
    ocr_engine = Column(String(50))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source_id = Column(GUID(), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(SafeVector(384))
    metadata_ = Column("metadata", SafeJSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(GUID(), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_value = Column(Text, nullable=False)
    confidence = Column(Float)
    validation_status = Column(String(20), default="pending")
    source_page = Column(Integer)
    source_chunk_id = Column(GUID(), ForeignKey("document_chunks.id"), nullable=True)
    extracted_by = Column(String(20), default="regex")
    officer_corrected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(GUID(), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    grievance_type_suggested = Column(String(100))
    grievance_subtype_suggested = Column(String(100))
    department_suggested = Column(String(100))
    priority_suggested = Column(String(20))
    description_summary_tamil = Column(Text)
    description_summary_english = Column(Text)
    action_items = Column(SafeJSON)
    claims = Column(SafeJSON)
    hallucination_score = Column(Float)
    grounding_score = Column(Float)
    raw_ai_response = Column(SafeJSON)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GrievanceDraft(Base):
    __tablename__ = "grievance_drafts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    source_id = Column(GUID(), ForeignKey("sources.source_id"), nullable=True)
    officer_id = Column(String(50), ForeignKey("officers.officer_id"), nullable=True)
    
    # 1. Petitioner Details
    petitioner_name = Column(String(200))
    father_husband_name = Column(String(200))
    complainant_signatory = Column(String(200), nullable=True)
    email = Column(String(100))
    phone = Column(String(20))
    is_own_phone = Column(Boolean, default=False)
    alternate_phone = Column(String(20))
    address = Column(Text)
    gender = Column(String(20), default=None)
    is_differently_abled = Column(String(10), default=None)
    community_or_individual = Column(String(50), default=None)

    # 2. Grievance Details
    description = Column(Text)
    grievance_source = Column(String(100), default=None)
    ref_number = Column(String(100), default=None)
    department = Column(String(255), default=None)
    sub_department = Column(String(255), default=None)
    local_body_type = Column(String(255), default=None)
    grievance_type = Column(String(255))
    grievance_subtype = Column(String(255))

    # 3. Location & Hierarchy
    district = Column(String(255), default=None)
    revenue_division = Column(String(255))
    taluk = Column(String(255))
    firka = Column(String(255))
    block = Column(String(255))
    village = Column(String(255))
    ward = Column(String(255))
    municipality_ward = Column(String(255))
    street_name = Column(String(255))
    door_no = Column(String(100))
    responsible_officer = Column(String(255))
    reason_for_redirection = Column(Text)
    communication_address_different = Column(Boolean, default=False)
    communication_address = Column(Text)

    # 4. Status & Tracking
    due_date = Column(DateTime, nullable=True)
    status = Column(String(50), default=None)
    source_code = Column(String(50))
    dro_grievance_id = Column(String(100), default=None)
    priority = Column(String(20), default=None)
    call_disposition = Column(String(50))
    is_whatsapp_appeal = Column(Boolean, default=False)
    is_whatsapp_tracking = Column(Boolean, default=False)
    is_whatsapp_receipt = Column(Boolean, default=False)
    ex_servicemen_relationship = Column(String(50), default=None)

    # 5. Workflow Sign-off
    dro_status = Column(String(50), default="draft")
    officer_approved = Column(Boolean, default=False)
    officer_notes = Column(Text)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False)
    source_id = Column(GUID(), ForeignKey("sources.source_id"), nullable=True)
    payload = Column(SafeJSON)
    status = Column(String(20), default="pending")
    worker_id = Column(String(50))
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_id = Column(GUID(), nullable=True)
    officer_id = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(SafeJSON)
    ip_address = Column(SafeINET, nullable=True)


class SemanticCacheRecord(Base):
    __tablename__ = "semantic_cache"

    id = Column(String(50), primary_key=True)
    prompt_hash = Column(String(64), index=True, nullable=False)
    prompt_text = Column(Text, nullable=True)
    embedding = Column(SafeVector(384), nullable=True)
    response_json = Column(SafeJSON, nullable=False)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)

