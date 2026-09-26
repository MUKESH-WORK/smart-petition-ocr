import logging
from typing import Dict, Any, List

logger = logging.getLogger("gdp_validation_service")


async def validate_document(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted petition data against administrative business rules.
    Returns validation verdict determining if document is VERIFIED or FLAGGED_FOR_REVIEW.
    """
    flags: List[str] = []
    is_valid = True
    confidence = 0.95

    summary = extracted_data.get("grievance_summary") or ""
    petitioner = extracted_data.get("petitioner_name")

    # 1. Content completeness check
    if not summary or len(summary.strip()) < 15:
        flags.append("Insufficient petition narrative or low OCR clarity")
        confidence -= 0.35

    # 2. Check for court/sub-judice matters (disallowed in administrative grievance day)
    lower_summary = summary.lower()
    court_keywords = ["court", "sub judice", "interim order", "stay order", "high court", "நீதிமன்றம்", "வழக்கு"]
    if any(k in lower_summary for k in court_keywords):
        flags.append("Potential sub-judice or pending court litigation matter")
        confidence -= 0.30

    # 3. Petitioner identity validation
    if not petitioner:
        flags.append("Petitioner identity not explicitly resolved from header")
        confidence -= 0.10

    if confidence < 0.70 or any("sub-judice" in f for f in flags):
        is_valid = False

    result = {
        "is_valid": is_valid,
        "confidence": max(0.0, min(1.0, round(confidence, 2))),
        "flags": flags,
        "details": {
            "category": extracted_data.get("category"),
            "subcategory": extracted_data.get("subcategory"),
            "petitioner_resolved": bool(petitioner),
            "summary_length": len(summary)
        }
    }

    logger.info(f"Validation result for {extracted_data.get('document_id')}: is_valid={is_valid}, flags={flags}")
    return result
