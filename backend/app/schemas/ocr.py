from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class OCRLine(BaseModel):
    line_id: str
    text: str
    confidence: float = 0.0
    bounding_box: Optional[BoundingBox] = None


class OCRBlock(BaseModel):
    block_id: str
    block_type: str = "text"
    text: str
    confidence: float = 0.0
    lines: List[OCRLine] = []
    bounding_box: Optional[BoundingBox] = None


class OCRPage(BaseModel):
    page_number: int
    width: int = 0
    height: int = 0
    text: str = ""
    blocks: List[OCRBlock] = []
    confidence: float = 0.0


class InternalOCRDocument(BaseModel):
    document_id: str
    provider: str
    processed_at: str
    page_count: int
    full_text: str
    pages: List[OCRPage]
    metadata: Dict[str, Any] = {}
