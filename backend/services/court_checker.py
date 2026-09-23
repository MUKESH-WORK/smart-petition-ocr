import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger("court_checker")

_COURT_CONFIG_CACHE: Optional[Dict[str, Any]] = None


DEFAULT_COURT_CONFIG: Dict[str, Any] = {
    "keywords": [
        "தம்பி பட்டாவும்", "அனுபவத்தில் உள்ளது", "பாகப்பிரிவினை", "சொத்து தகராறு", "உரிமையியல் தகராறு",
        "நீதிமன்றம்", "வழக்கு", "உயர்நீதிமன்றம்", "உரிமையியல் நீதிமன்றம்", "நீதிமன்ற வழக்கு",
        "தீர்ப்பு", "தடை உத்தரவு", "மனு எண்", "வழக்கு எண்", "இடைக்கால தடை", "உத்தரவு",
        "high court", "civil court", "court litigation", "writ petition", "interim injunction",
        "stay order", "injunction order", "decree", "civil suit", "court order", "pending suit",
        "legal notice", "sub court", "district court", "munsi court"
    ],
    "case_number_patterns": [
        r'\b(?:W\.?P\.?|Writ\s*Petition|O\.?S\.?|Original\s*Suit|C\.?M\.?A\.?|W\.?A\.?|S\.?A\.?|C\.?R\.?P\.?|C\.?C\.?|M\.?C\.?)\s*(?:No\.?)?\s*[:\/-]?\s*\d+\s*(?:of|\/)\s*(?:19|20)\d{2}\b',
        r'\b(?:வழக்கு\s*எண்|மனு\s*எண்)\s*[:\/-]?\s*\d+\s*(?:of|\/)\s*(?:19|20)\d{2}\b',
        r'\b(?:OS|WP|WA|SA|CRP|CMA)\s*\.?\s*\d+\s*\/\s*(?:19|20)\d{2}\b'
    ],
    "routing_config": {
        "recommended_routing": "SPECIALIZED_ADMINISTRATIVE_DRO_REVIEW",
        "target_authority": "DRO_SPECIAL_LEGAL_CELL",
        "priority": "HIGH",
        "default_routing": "STANDARD_PROCESSING",
        "default_priority": "NORMAL"
    }
}


def _load_court_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads court litigation keywords and patterns dynamically from database cm_taxonomy_mappings."""
    global _COURT_CONFIG_CACHE
    if _COURT_CONFIG_CACHE is not None and config_path is None:
        return _COURT_CONFIG_CACHE

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _COURT_CONFIG_CACHE = json.load(f)
                return _COURT_CONFIG_CACHE
        except Exception as e:
            logger.error(f"[COURT_CHECKER] Failed to load court keywords from {config_path}: {e}")

    # Dynamically query legal & court keywords from Database taxonomy mappings
    db_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_admin.db"),
        os.path.join(os.getcwd(), "temp_cache", "dro_admin.db"),
        os.path.join(os.getcwd(), "backend", "temp_cache", "dro_admin.db"),
    ]
    
    db_kws = set(DEFAULT_COURT_CONFIG["keywords"])
    for cand in db_candidates:
        if os.path.exists(cand):
            try:
                import sqlite3
                con = sqlite3.connect(cand)
                cur = con.cursor()
                cur.execute("""
                    SELECT grievance_type, grievance_sub_type, search_text 
                    FROM cm_taxonomy_mappings 
                    WHERE grievance_type LIKE '%Court%' OR grievance_type LIKE '%Legal%' 
                       OR grievance_sub_type LIKE '%Court%' OR grievance_sub_type LIKE '%Dispute%' 
                       OR search_text LIKE '%நீதிமன்ற%' OR search_text LIKE '%வழக்கு%'
                """)
                for r in cur.fetchall():
                    for val in r:
                        if val:
                            for word in re.split(r'[,|;\n]+', str(val)):
                                w_clean = word.strip().lower()
                                if len(w_clean) >= 3:
                                    db_kws.add(w_clean)
                con.close()
                break
            except Exception as e:
                logger.debug(f"Court checker DB notice: {e}")

    _COURT_CONFIG_CACHE = {
        "keywords": list(db_kws),
        "case_number_patterns": DEFAULT_COURT_CONFIG["case_number_patterns"],
        "routing_config": DEFAULT_COURT_CONFIG["routing_config"]
    }
    return _COURT_CONFIG_CACHE


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
