import uuid
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, Index, BigInteger, LargeBinary)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET
from pgvector.sqlalchemy import Vector
from models.database import Base


class MasterLocation(Base):
    __tablename__ = "master_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_code = Column(String(10), nullable=False)
    district_name_tamil = Column(String(100))
    taluk_code = Column(String(10), nullable=False)
    taluk_name_tamil = Column(String(100))
    block_code = Column(String(10))
    block_name_tamil = Column(String(100))
    firka_code = Column(String(10))
    firka_name_tamil = Column(String(100))
    village_code = Column(String(10))
    village_name_tamil = Column(String(100))


class Officer(Base):
    __tablename__ = "officers"

    officer_id = Column(String(50), primary_key=True)
    name_tamil = Column(String(100))
    designation = Column(String(100))
    department = Column(String(50))
    taluk_access = Column(ARRAY(String(10)))
    created_at = Column(DateTime, default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    officer_id = Column(String(50), ForeignKey("officers.officer_id"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer)
    file_hash = Column(String(64), unique=True)
    page_count = Column(Integer, default=0)
    status = Column(String(30), default="uploaded")
    content_fingerprint = Column(JSONB, nullable=True)
    file_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    full_text = Column(Text)
    blocks = Column(JSONB)
    tables = Column(JSONB)
    avg_confidence = Column(Float)
    ocr_engine = Column(String(50))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer)
    chunk_index = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_value = Column(Text, nullable=False)
    confidence = Column(Float)
    validation_status = Column(String(20), default="pending")
    source_page = Column(Integer)
    source_chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=True)
    extracted_by = Column(String(20), default="regex")
    officer_corrected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    grievance_type_suggested = Column(String(100))
    grievance_subtype_suggested = Column(String(100))
    department_suggested = Column(String(100))
    priority_suggested = Column(String(20))
    description_summary_tamil = Column(Text)
    description_summary_english = Column(Text)
    action_items = Column(JSONB)
    claims = Column(JSONB)
    hallucination_score = Column(Float)
    grounding_score = Column(Float)
    raw_ai_response = Column(JSONB)
    generated_at = Column(DateTime, default=datetime.utcnow)


class GrievanceDraft(Base):
    __tablename__ = "grievance_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=True)
    officer_id = Column(String(50), ForeignKey("officers.officer_id"), nullable=True)
    
    # 1. Petitioner Details
    petitioner_name = Column(String(200))
    father_husband_name = Column(String(200))
    email = Column(String(100))
    phone = Column(String(20))
    is_own_phone = Column(Boolean, default=True)
    alternate_phone = Column(String(20))
    address = Column(Text)
    gender = Column(String(20), default="-None-")
    is_differently_abled = Column(String(10), default="No")
    community_or_individual = Column(String(50), default="Public")

    # 2. Grievance Details
    description = Column(Text)
    grievance_source = Column(String(100), default="DRO Camp / மாவட்ட வருவாய் அலுவலர் முகாம்")
    ref_number = Column(String(100))
    department = Column(String(100), default="Revenue and Disaster Management / வருவாய் மற்றும் பேரிடர் மேலாண்மை")
    sub_department = Column(String(100), default="Revenue / வருவாய்த்துறை")
    local_body_type = Column(String(100), default="Village Panchayat")
    grievance_type = Column(String(100))
    grievance_subtype = Column(String(100))

    # 3. Location & Hierarchy
    district = Column(String(100), default="Erode (ERD)")
    revenue_division = Column(String(100))
    taluk = Column(String(100))
    firka = Column(String(100))
    block = Column(String(100))
    village = Column(String(100))
    ward = Column(String(50))
    municipality_ward = Column(String(50))
    street_name = Column(String(150))
    door_no = Column(String(50))
    responsible_officer = Column(String(100))
    reason_for_redirection = Column(Text)
    communication_address_different = Column(Boolean, default=False)
    communication_address = Column(Text)

    # 4. Status & Tracking
    due_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="Open")
    source_code = Column(String(50))
    dro_grievance_id = Column(String(100))
    priority = Column(String(20), default="MEDIUM")
    call_disposition = Column(String(50))
    is_whatsapp_appeal = Column(Boolean, default=False)
    is_whatsapp_tracking = Column(Boolean, default=True)
    is_whatsapp_receipt = Column(Boolean, default=True)
    ex_servicemen_relationship = Column(String(50), default="-None-")

    # 5. Workflow Sign-off
    dro_status = Column(String(50), default="draft")
    officer_approved = Column(Boolean, default=False)
    officer_notes = Column(Text)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id"), nullable=True)
    payload = Column(JSONB)
    status = Column(String(20), default="pending")
    worker_id = Column(String(50))
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow)
    source_id = Column(UUID(as_uuid=True), nullable=True)
    officer_id = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(JSONB)
    ip_address = Column(INET, nullable=True)
