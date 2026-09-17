import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("court_checker")

_COURT_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _load_court_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Dynamically loads court litigation keywords and patterns from configuration."""
    global _COURT_CONFIG_CACHE
    if _COURT_CONFIG_CACHE is not None and config_path is None:
        return _COURT_CONFIG_CACHE

    if config_path and os.path.exists(config_path):
        resolved_path = config_path
    else:
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "court_litigation_keywords.json"),
            os.path.join(os.getcwd(), "backend", "data", "court_litigation_keywords.json"),
            os.path.join(os.getcwd(), "data", "court_litigation_keywords.json"),
        ]
        resolved_path = None
        for cand in candidates:
            if os.path.exists(cand):
                resolved_path = cand
                break

    if not resolved_path or not os.path.exists(resolved_path):
        logger.warning(f"[COURT_CHECKER] Keywords config not found at: {resolved_path}, using dynamic fallback")
        return {
            "keywords": [],
            "case_number_patterns": [],
            "routing_config": {
                "recommended_routing": "SPECIALIZED_ADMINISTRATIVE_DRO_REVIEW",
                "target_authority": "DRO_SPECIAL_LEGAL_CELL",
                "priority": "HIGH",
                "default_routing": "STANDARD_PROCESSING",
                "default_priority": "NORMAL"
            }
        }

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            _COURT_CONFIG_CACHE = json.load(f)
            return _COURT_CONFIG_CACHE
    except Exception as e:
        logger.error(f"[COURT_CHECKER] Failed to load court keywords from {resolved_path}: {e}")
        return {"keywords": [], "case_number_patterns": [], "routing_config": {}}


def check_court_jurisdiction(
    petition_payload: Union[Dict[str, Any], str],
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes petition text bodies dynamically against configured litigation markers.
    Zero hardcoded keyword lists in Python code; all patterns flow from configuration.
    """
    if isinstance(petition_payload, str):
        petition_payload = {"description": petition_payload}
    elif not isinstance(petition_payload, dict):
        petition_payload = {}

    cfg = _load_court_config(config_path)
    keywords = cfg.get("keywords", [])
    patterns = cfg.get("case_number_patterns", [])
    routing_cfg = cfg.get("routing_config", {})

    description = str(petition_payload.get("description") or "")
    subject = str(petition_payload.get("subject") or petition_payload.get("grievance_type") or "")
    raw_ocr = str(petition_payload.get("ocr_text") or petition_payload.get("full_text") or "")
    address = str(petition_payload.get("address") or "")
    claims = petition_payload.get("claims") or []
    claims_text = " ".join([str(c) if not isinstance(c, dict) else str(c.get("text", "")) for c in claims])

    combined_corpus = f"{description}\n{subject}\n{raw_ocr}\n{address}\n{claims_text}".lower()

    detected_keywords: List[str] = []

    for kw in keywords:
        kw_clean = str(kw).lower().strip()
        if kw_clean and kw_clean in combined_corpus:
            detected_keywords.append(str(kw).strip())

    for pat in patterns:
        try:
            match = re.search(pat, combined_corpus, re.IGNORECASE)
            if match:
                matched_str = match.group(0)
                if matched_str not in detected_keywords:
                    detected_keywords.append(matched_str)
        except re.error as e:
            logger.warning(f"[COURT_CHECKER] Invalid regex pattern '{pat}': {e}")

    is_pending = len(detected_keywords) > 0

    if is_pending:
        rec_routing = routing_cfg.get("recommended_routing", "SPECIALIZED_ADMINISTRATIVE_DRO_REVIEW")
        target_auth = routing_cfg.get("target_authority", "DRO_SPECIAL_LEGAL_CELL")
        priority = routing_cfg.get("priority", "HIGH")
        alert_notice = (
            "HIGH-PRIORITY STRUCTURAL ALERT: Active civil court / inheritance / joint-property dispute detected "
            f"({', '.join(detected_keywords)}). Routing intercepted for Specialized Administrative / DRO Review."
        )
        logger.warning(f"[COURT_CHECKER] Dispute flagged: {alert_notice}")
    else:
        rec_routing = routing_cfg.get("default_routing", "STANDARD_PROCESSING")
        target_auth = "DISTRICT_REVENUE_ADMINISTRATION"
        priority = routing_cfg.get("default_priority", "NORMAL")
        alert_notice = None

    return {
        "is_civil_court_pending": is_pending,
        "court_blockage_detected": is_pending,
        "alert_notice": alert_notice,
        "routing_recommendation": rec_routing,
        "recommended_routing": rec_routing,
        "target_authority": target_auth,
        "priority": priority,
        "detected_court_keywords": detected_keywords,
        "matched_court_keywords": detected_keywords,
        "case_identifiers": [kw for kw in detected_keywords if re.search(r'\d+', kw)]
    }


# Alias for backwards compatibility & naming clarity
check_court_jurisdictional_blockage = check_court_jurisdiction
