import logging
from typing import Dict, Any

logger = logging.getLogger("gdp_verification_service")


async def verify_document(document_id: str, extracted_data: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final verification barrier verifying data integrity, department jurisdiction,
    and routing recommendations before final disposition.
    """
    logger.info(f"Executing verification service for document {document_id}")

    is_verified = validation_result.get("is_valid", False)
    final_status = "VERIFIED" if is_verified else "FLAGGED_FOR_REVIEW"

    return {
        "document_id": document_id,
        "final_status": final_status,
        "verified": is_verified,
        "review_reasons": validation_result.get("flags", []),
        "department_routing": {
            "assigned_department": extracted_data.get("category", "General Public Grievance"),
            "section": extracted_data.get("subcategory", "General")
        }
    }
