from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    success: bool = True
    documentId: str
    status: str = "UPLOADED"
    message: str = "Document accepted for processing."


class DocumentStatusUpdate(BaseModel):
    status: str
    error: Optional[str] = None


class DocumentResponse(BaseModel):
    document_id: str
    filename: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    page_count: int = 0
    full_text: Optional[str] = None
    ocr_result: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentResponse]
