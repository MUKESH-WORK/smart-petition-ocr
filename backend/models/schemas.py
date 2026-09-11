from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


# --- Common & Auth ---
class TokenPayload(BaseModel):
    officer_id: str
    name_tamil: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    taluk_access: Optional[List[str]] = None
    exp: Optional[int] = None


# --- Source Documents ---
class SourceUploadResponse(BaseModel):
    source_id: UUID
    file_name: str
    file_size_bytes: int
    page_count: int
    status: str
    created_at: datetime


class SourceStatusResponse(BaseModel):
    source_id: UUID
    file_name: str
    status: str
    ocr_confidence: Optional[float] = None
    page_count: int
    chunk_count: int
    entity_count: int
    ai_analysis_ready: bool
    draft_ready: bool
    officer_approved: bool
    dro_status: Optional[str] = None
    created_at: datetime


# --- OCR Schemas ---
class OCRBlock(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]
    engine: Optional[str] = None


class OCRPageResult(BaseModel):
    page_number: int
    full_text: Optional[str] = ""
    avg_confidence: Optional[float] = 0.0
    ocr_engine: Optional[str] = "paddleocr"
    processing_time_ms: Optional[int] = 0
    blocks: List[Dict[str, Any]] = []
    tables: Optional[List[Dict[str, Any]]] = []


class OCRDocumentResponse(BaseModel):
    source_id: UUID
    pages: List[OCRPageResult]
    total_blocks: int
    surya_fallback_count: int = 0


# --- Entity Schemas ---
class ExtractedEntityItem(BaseModel):
    id: Optional[int] = None
    entity_type: str
    entity_value: str
    confidence: Optional[float] = 1.0
    validation_status: str = "pending"  # pending, verified, suspect, missing
    source_page: Optional[int] = None
    source_chunk_id: Optional[UUID] = None
    extracted_by: str = "regex"  # regex, ai_ner, master_db_lookup, officer_edit
    officer_corrected: bool = False


class EntityExtractionResponse(BaseModel):
    source_id: UUID
    entities: List[ExtractedEntityItem]
    verified_count: int
    suspect_count: int


# --- AI Analysis Schemas ---
class ActionItem(BaseModel):
    action: str
    department: Optional[str] = None
    deadline_hint: Optional[str] = None


class ClaimItem(BaseModel):
    text: str
    source_page: Optional[int] = None
    confidence: Optional[float] = None
    verified: Optional[bool] = False


class AIAnalysisResponse(BaseModel):
    source_id: UUID
    grievance_type_suggested: Optional[str] = None
    grievance_subtype_suggested: Optional[str] = None
    department_suggested: Optional[str] = None
    priority_suggested: Optional[str] = "MEDIUM"
    description_summary_tamil: Optional[str] = None
    description_summary_english: Optional[str] = None
    action_items: List[ActionItem] = []
    claims: List[ClaimItem] = []
    hallucination_score: float = 0.0
    grounding_score: float = 1.0
    generated_at: Optional[datetime] = None


# --- Chat & RAG Schemas ---
class ChatRequest(BaseModel):
    question: str
    top_k: int = 5


class ChatCitation(BaseModel):
    page_number: int
    chunk_id: UUID
    snippet: str
    similarity: float


class ChatStreamResponse(BaseModel):
    delta: Optional[str] = None
    citations: Optional[List[ChatCitation]] = None
    done: bool = False


# --- Grievance Draft Schemas ---
class GrievanceDraftResponse(BaseModel):
    id: UUID
    source_id: Optional[UUID] = None
    officer_id: Optional[str] = None
    
    # Petitioner
    petitioner_name: Optional[str] = None
    father_husband_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_own_phone: Optional[bool] = True
    alternate_phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = "-None-"
    is_differently_abled: Optional[str] = "No"
    community_or_individual: Optional[str] = "Public"

    # Grievance
    description: Optional[str] = None
    grievance_source: Optional[str] = None
    ref_number: Optional[str] = None
    department: Optional[str] = None
    sub_department: Optional[str] = None
    local_body_type: Optional[str] = None
    grievance_type: Optional[str] = None
    grievance_subtype: Optional[str] = None

    # Location & Hierarchy
    district: Optional[str] = None
    revenue_division: Optional[str] = None
    taluk: Optional[str] = None
    firka: Optional[str] = None
    block: Optional[str] = None
    village: Optional[str] = None
    ward: Optional[str] = None
    municipality_ward: Optional[str] = None
    street_name: Optional[str] = None
    door_no: Optional[str] = None
    responsible_officer: Optional[str] = None
    reason_for_redirection: Optional[str] = None
    communication_address_different: Optional[bool] = False
    communication_address: Optional[str] = None

    # Status & Tracking
    due_date: Optional[datetime] = None
    status: Optional[str] = "Open"
    source_code: Optional[str] = None
    dro_grievance_id: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    call_disposition: Optional[str] = None
    is_whatsapp_appeal: Optional[bool] = False
    is_whatsapp_tracking: Optional[bool] = True
    is_whatsapp_receipt: Optional[bool] = True
    ex_servicemen_relationship: Optional[str] = "-None-"

    # Sign-off
    dro_status: Optional[str] = "draft"
    officer_approved: bool = False
    officer_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DraftUpdate(BaseModel):
    petitioner_name: Optional[str] = None
    father_husband_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_own_phone: Optional[bool] = None
    alternate_phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    is_differently_abled: Optional[str] = None
    community_or_individual: Optional[str] = None
    
    description: Optional[str] = None
    grievance_source: Optional[str] = None
    ref_number: Optional[str] = None
    department: Optional[str] = None
    sub_department: Optional[str] = None
    local_body_type: Optional[str] = None
    grievance_type: Optional[str] = None
    grievance_subtype: Optional[str] = None
    
    district: Optional[str] = None
    revenue_division: Optional[str] = None
    taluk: Optional[str] = None
    firka: Optional[str] = None
    block: Optional[str] = None
    village: Optional[str] = None
    ward: Optional[str] = None
    municipality_ward: Optional[str] = None
    street_name: Optional[str] = None
    door_no: Optional[str] = None
    responsible_officer: Optional[str] = None
    reason_for_redirection: Optional[str] = None
    communication_address_different: Optional[bool] = None
    communication_address: Optional[str] = None
    
    status: Optional[str] = None
    source_code: Optional[str] = None
    priority: Optional[str] = None
    call_disposition: Optional[str] = None
    is_whatsapp_appeal: Optional[bool] = None
    is_whatsapp_tracking: Optional[bool] = None
    is_whatsapp_receipt: Optional[bool] = None
    ex_servicemen_relationship: Optional[str] = None
    officer_notes: Optional[str] = None


class DraftApproveRequest(BaseModel):
    officer_id: str
    officer_notes: Optional[str] = None


# --- Search Schemas ---
class SearchRequest(BaseModel):
    query: str
    source_id: Optional[UUID] = None
    search_type: str = "hybrid"  # vector, fulltext, hybrid
    top_k: int = 5


class SearchResultItem(BaseModel):
    id: UUID
    chunk_text: str
    page_number: int
    score: float
    metadata: Optional[Dict[str, Any]] = None


# --- Admin & Queue Schemas ---
class QueueStatusResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int


class MasterLocationCreate(BaseModel):
    district_code: str
    district_name_tamil: str
    taluk_code: str
    taluk_name_tamil: str
    block_code: Optional[str] = None
    block_name_tamil: Optional[str] = None
    firka_code: Optional[str] = None
    firka_name_tamil: Optional[str] = None
    village_code: Optional[str] = None
    village_name_tamil: Optional[str] = None
