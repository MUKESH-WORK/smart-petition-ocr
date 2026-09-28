import os
import re
import logging
from typing import Dict, Any
from app.schemas.ocr import InternalOCRDocument

logger = logging.getLogger("gdp_extraction_service")


async def extract_document(ocr_result: InternalOCRDocument) -> Dict[str, Any]:
    """
    Extract structured grievance and petitioner information from normalized OCR result.
    Uses AI / LLM if available, with robust pattern extraction fallback.
    """
    full_text = ocr_result.full_text or ""
    document_id = ocr_result.document_id

    logger.info(f"Extracting structured fields for document {document_id} ({len(full_text)} chars)")

    # 1. Try existing deep extraction engine if present in backend
    try:
        from services.entity_extractor import extract_all_entities
        extracted = extract_all_entities(full_text)
        if extracted and isinstance(extracted, dict):
            extracted["document_id"] = document_id
            return extracted
    except Exception as ex:
        logger.debug(f"Direct backend entity extractor not used: {ex}")

    # 2. Heuristic & Regex extraction engine
    extracted: Dict[str, Any] = {
        "document_id": document_id,
        "petitioner_name": None,
        "father_or_husband_name": None,
        "phone_number": None,
        "address": None,
        "district": None,
        "taluk": None,
        "village": None,
        "category": "General Public Grievance",
        "subcategory": "Other",
        "grievance_summary": None,
        "urgency": "Normal",
        "metadata": {
            "page_count": ocr_result.page_count,
            "provider": ocr_result.provider
        }
    }

    phone_match = re.search(r"\b[6-9]\d{9}\b", full_text)
    if phone_match:
        extracted["phone_number"] = phone_match.group(0)

    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", full_text)
    if email_match:
        extracted["email"] = email_match.group(0)

    name_patterns = [
        r"(?:பெயர்|Name|Applicant|Petitioner)[:\s\-]+([A-Za-z\.\s\u0B80-\u0BFF]{3,35})",
        r"(?:Thiru|Tmt|Selvi|Mr\.|Mrs\.|Shri)\s+([A-Za-z\.\s]{3,35})"
    ]
    for pattern in name_patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            extracted["petitioner_name"] = m.group(1).strip()
            break

    summary_lines = [l.strip() for l in full_text.splitlines() if len(l.strip()) > 20]
    if summary_lines:
        extracted["grievance_summary"] = " ".join(summary_lines[:3])[:500]
    else:
        extracted["grievance_summary"] = full_text[:300] if full_text else "Grievance petition content."

    lower_text = full_text.lower()
    if any(k in lower_text for k in ["patta", "chitta", "land", "survey", "பட்டா", "நிலம்"]):
        extracted["category"] = "Revenue - Land Administration"
        extracted["subcategory"] = "Patta Transfer"
    elif any(k in lower_text for k in ["ration", "smart card", "food", "ரேஷன்", "உணவு"]):
        extracted["category"] = "Civil Supplies & Consumer Protection"
        extracted["subcategory"] = "Ration Card Issue"
    elif any(k in lower_text for k in ["road", "drainage", "water", "சாக்கடை", "குடிநீர்"]):
        extracted["category"] = "Municipal Administration & Water Supply"
        extracted["subcategory"] = "Infrastructure & Public Works"
    elif any(k in lower_text for k in ["pension", "oap", "முதியோர் உதவித்தொகை", "விதவை"]):
        extracted["category"] = "Social Welfare & Women Empowerment"
        extracted["subcategory"] = "Old Age / Widow Pension"

    return extracted
