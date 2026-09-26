from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON
from app.database.connection import Base


class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(512), nullable=False)
    status = Column(String(64), nullable=False, default="UPLOADED", index=True)
    error_message = Column(Text, nullable=True)
    page_count = Column(Integer, default=0)
    full_text = Column(Text, nullable=True)
    ocr_result = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    validation_result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "document_id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "status": self.status,
            "error_message": self.error_message,
            "page_count": self.page_count,
            "full_text": self.full_text,
            "ocr_result": self.ocr_result,
            "extracted_data": self.extracted_data,
            "validation_result": self.validation_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
