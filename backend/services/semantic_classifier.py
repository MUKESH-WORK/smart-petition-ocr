"""
Dynamic Database-Driven Semantic Petition Classifier
====================================================
Implements High-Recall Multi-Path Retrieval against all 1,847 official database
taxonomy rows in cm_taxonomy_mappings followed by Contextual Reranking.

Core Pipeline:
  1. Multiline Subject Extraction (Zone B பொருள் line)
  2. Prayer / Requested Action Extraction (What the petitioner is asking the government to DO)
  3. Domain Concept Extraction
  4. High-Recall Multi-Path Retrieval (All 1,847 DB rows):
       - Path A: Semantic Intent Embedding Retrieval (Top 20)
       - Path B: Subject Line Embedding & Lexical Retrieval (Top 20)
       - Path C: Prayer / Requested Action Retrieval (Top 20)
       - Path D: Domain Concept & Recipient Addressee Retrieval (Top 20)
       - Path E: Relevant Body Context Retrieval (Top 20)
  5. Candidate Union + Deduplication by taxonomy_id
  6. Contextual Reranking with Contradiction & Incidental Penalties
  7. Top 10 Candidates for LLM Verification
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
import numpy as np

logger = logging.getLogger(__name__)

# Configurable Weights for Contextual Reranking
SEMANTIC_WEIGHT = 0.25
SUBJECT_WEIGHT = 0.35
PRAYER_WEIGHT = 0.20
DOMAIN_WEIGHT = 0.20
RECIPIENT_BOOST = 0.25
RERANK_MARGIN_THRESHOLD = 0.08
DEFAULT_TOP_K = 10


def _extract_subject_line(text: str) -> str:
    """
    Extract the பொருள் (Subject) line from petition text or Zone B.
    Handles multiline subjects across linebreaks and trims boilerplate headers.
    """
    if not text:
        return ""

    subject_match = re.search(
        r'(?:பொருள்|Subject|Porul)\s*[:：]\s*\n*\s*(.+?)(?:\n\s*\n|\n\s*(?:ஐயா|அய்யா|வணக்கம்|Sir|Respected|இப்படிக்கு|பெறுநர்)|$)',
        text,
        re.DOTALL | re.IGNORECASE
    )
    if subject_match:
        raw_subj = subject_match.group(1).strip()
        lines = [l.strip() for l in raw_subj.split('\n') if l.strip()]
        if lines:
            # Join up to 3 lines of multiline subject cleanly
            combined = " ".join(lines[:3])
            # Strip excessive punctuation, symbols, and leading/trailing markers
            combined = re.sub(r'^(?:பொருள்\s*[:\.\-]?|மனு\s*[:\.\-]?)\s*', '', combined).strip()
            combined = re.sub(r'\s+', ' ', combined).strip(' .,;:-')
            return combined

    return ""


def _extract_prayer_section(text: str) -> str:
    """
    Extracts the petitioner's explicit prayer/request section (கோரிக்கை / பிரார்த்தனை).
    This is what the petitioner is asking the government to DO (requested action).
    """
    if not text:
        return ""

    prayer_patterns = [
        r'(?:^|\n)\s*(?:கோரிக்கைகள்?|பிரார்த்தனை|வேண்டுகோள்)\s*[:：]\s*(.+?)(?:\n\s*(?:இப்படிக்கு|இவண்|நன்றி|நாள்|தேதி)|$)',
        r'(?:^|\n)\s*(?:எனவே|ஆகவே|ஆதலால்)\s*[,]?\s*(.+?)(?:கேட்டுக்\s*கொள்கிறேன்|கேட்டுக்கொள்கிறோம்|வேண்டுகிறேன்|வேண்டுகிறோம்|கோருகிறேன்|கோருகிறோம்|அளித்துள்ளார்|$)',
    ]

    for pattern in prayer_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            prayer = match.group(1).strip()
            lines = [l.strip() for l in prayer.split('\n') if l.strip()]
            if lines:
                combined = " ".join(lines[:3])
                combined = re.sub(r'\s+', ' ', combined).strip(' .,;:-')
                if len(combined) > 5:
                    return combined

    # Scan lines near closing signature block
    sig_idx = text.find("இப்படிக்கு")
    if sig_idx == -1:
        sig_idx = text.find("இவண்")
    if sig_idx > 50:
        pre_sig = text[max(0, sig_idx - 300):sig_idx].strip()
        sentences = [s.strip() for s in re.split(r'[.।\n]', pre_sig) if len(s.strip()) > 15]
        if sentences:
            return sentences[-1]

    return ""


def _clean_text_for_road_detection(text: str) -> str:
    """
    Strips all occurrences and inflections of Erode district / taluk names
    ('ஈரோடு', 'ஈ.ரோடு', 'ஈ. ரோடு', 'ஈ - ரோடு', 'ஈரோட்டில்', 'ஈரோட்டு', 'erode') 
    before checking for road-related keywords, preventing substring collision on 'ரோடு'.
    """
    cleaned = re.sub(r'\berode\b', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'ஈ[\.\s\-]*ரோ[ட|ட்][\u0B80-\u0BFF]*', '', cleaned)
    cleaned = re.sub(r'ஈ[\.\s\-]*ரோடு[ா-ூ]*', '', cleaned)
    return cleaned


def _has_road_signals(text: str) -> bool:
    """
    Checks if text has genuine road signals, strictly avoiding Erode place name false positives
    and bare address street names.
    """
    cleaned = _clean_text_for_road_detection(text).lower()
    specific_road_terms = [
        "சாலை", "தார் சாலை", "மண் சாலை", "குண்டு குழி", "குண்டும் குழியுமாக", "சேதமடைந்த சாலை",
        "நெடுஞ்சாலை", "சாலை சீரமைப்பு", "சாலை பராமரிப்பு", "சாலை பழுது", "சாலை பணி", "சாலைப்பணி", "சாலை அமைக்க",
        "தார் ரோடு", "ரோடு வசதி", "ரோடு சீரமைப்பு", "ரோடு பராமரிப்பு", "ரோடு பழுது", "ரோடு பணி", "ரோடு அமைக்க",
        "pothole", "pavement", "highway", "road repair", "road maintenance", "road work", "laying of road"
    ]
    if any(t in cleaned for t in specific_road_terms):
        return True
    if re.search(r'(?:ரோடு|road)\s*(?:சீரமைக்க|பழுது|அமைக்க|பராமரிப்பு|குழி|சேதம்|விளக்கு|வசதி|பணி|repair|maintenance|laying|damaged|condition|pothole)', cleaned):
        return True
    return False


def _score_candidate_text_alignment(cand_text: str, target_text: str) -> float:
    """
    Computes fine-grained, principled alignment between a candidate taxonomy field
    and the petition target text (subject line or prayer section) across all 1,847 rows.
    - Exact phrase match: 1.0
    - Multi-token 100% coverage: 0.90
    - Strong token coverage (>= 66%): 0.65 * coverage
    - Moderate token coverage (>= 50%): 0.35 * coverage
    - Isolated single-word collision (< 50%): only 0.05 * coverage
    """
    if not cand_text or not target_text:
        return 0.0
    c_clean = cand_text.strip().lower()
    t_clean = target_text.strip().lower()

    if not c_clean or not t_clean:
        return 0.0

    # 1. Exact phrase match
    if c_clean in t_clean:
        return 1.0

    # 2. Tokenize excluding punctuation and short stop words
    stop_tokens = {"and", "for", "the", "with", "from", "department", "govt", "tamil", "nadu", "-", "/", "&"}
    tokens = [w for w in re.split(r'[\s\-:,/()]+', c_clean) if len(w) >= 3 and w not in stop_tokens]
    if not tokens:
        return 0.0

    matched = [w for w in tokens if w in t_clean]
    coverage = len(matched) / len(tokens)

    if coverage == 1.0:
        return 0.90
    elif coverage >= 0.66:
        return 0.65 * coverage
    elif coverage >= 0.50:
        return 0.35 * coverage
    else:
        # Isolated single-token collision (e.g. 'community' in 'st community genuiness verification')
        return 0.05 * coverage


# ─────────────────────────────────────────────────────────────────────────────
# Domain Keyword Lexicons for Context, Retrieval, and Contradiction Scoring
# ─────────────────────────────────────────────────────────────────────────────
DOMAIN_INDICATORS = {
    "animal_husbandry": [
        "கால்நடை", "கால்நடை மருத்துவமனை", "கால்நடை மருந்தகம்", "கால்நடை மருத்துவர்", 
        "கால்நடை பராமரிப்பு", "ஆடு மாடு மருத்துவம்", "மாடு", "ஆடு", "கோழி", "veterinary", 
        "animal husbandry", "dispensary", "slaughter house", "cattle", "livestock"
    ],
    "burial_ground": [
        "புதைகுழி", "மயானம்", "சுடுகாடு", "மயானப்பாதை", "மயானப் பாதை", "இறுதி ஊர்வலம்", 
        "மயான வழி", "burial ground", "cremation ground", "crematorium", "pathway to burial ground",
        "burial pathway", "grave"
    ],
    "water_channel_encroachment": [
        "நீர்வழிப்பாதை", "நீர்வழிப் பாதை", "நீர்வழி", "ஓடை ஆக்கிரமிப்பு", "நீர்நிலை ஆக்கிரமிப்பு", 
        "கால்வாய் ஆக்கிரமிப்பு", "ஏரி ஆக்கிரமிப்பு", "மழைநீர் தேக்கம்", "ஓடை", "கால்வாய்", 
        "water channel encroachment", "stream encroachment"
    ],
    "building_repair": [
        "கட்டிடம் பழுது", "கட்டிட சீரமைப்பு", "மருத்துவமனை கட்டிடம்", "அரசு கட்டிடம்", 
        "பழுதடைந்த கட்டிடம்", "கூரை வழியாக தண்ணீர்", "கட்டிடம் கட்ட", "building repair", 
        "rehabilitation of old building", "demolition of old building"
    ],
    "scholarship": [
        "scholarship", "கல்வி உதவித்தொகை", "கல்வி உதவித் தொகை", "கல்வி உதவி தொகை",
        "scholarship amount", "scholarship application", "post matric scholarship", 
        "pre matric scholarship", "கல்விக் கட்டண சலுகை"
    ],
    "education": [
        "மாணவர்", "மாணவி", "பள்ளி", "கல்லூரி", "கல்வி", "படிப்பு", 
        "b.e", "b.tech", "degree", "college", "student", "பல்கலைக்கழகம்",
        "படிப்பிற்கு", "உயர்கல்வி", "higher education"
    ],
    "community_hall": [
        "சமுதாய கூடம்", "சமூக கூடம்", "சமுதாயக்கூடம்", "சமுதாய பவன்", "community hall",
        "திருமண மண்டபம்", "பொது மண்டபம்", "சமுதாய நலக்கூடம்"
    ],
    "old_age_pension": [
        "முதியோர் உதவித்தொகை", "முதியோர் ஓய்வூதியம்", "முதியோர் பென்ஷன்", "மூத்த குடிமக்கள் ஓய்வூதியம்", 
        "வயது முதிர்ந்ததால் உதவி", "oap", "ignoaps", "social security pension"
    ],
    "widow_pension": [
        "விதவை உதவித்தொகை", "விதவை ஓய்வூதியம்", "ஆதரவற்ற விதவை", "widow pension", "dwps", "dwp"
    ],
    "disability_pension": [
        "மாற்றுத்திறனாளி உதவித்தொகை", "மாற்றுத்திறனாளி ஓய்வூதியம்", "ஊனமுற்றோர் உதவித்தொகை", 
        "differently abled pension", "dap", "disability assistance"
    ],
    "road_repair": [
        "சாலை", "தார் சாலை", "மண் சாலை", "குண்டு குழி", "சேதமடைந்த சாலை", 
        "நெடுஞ்சாலை", "pothole", "pavement", "highway", "சாலை சீரமைப்பு", "சாலை பராமரிப்பு", "சாலை பழுது",
        "தார் ரோடு", "மெயின் ரோடு", "ரோடு வசதி", "ரோடு சீரமைப்பு", "ரோடு பழுது", "road repair"
    ],
    "drinking_water": [
        "குடிநீர்", "தண்ணீர் குழாய்", "மேல்நிலைத் தொட்டி", "குடிநீர் இணைப்பு", 
        "குடிநீர் விநியோகம்", "drinking water", "water connection", "water supply", "பைப் லைன்"
    ],
    "street_lights": [
        "தெருவிளக்கு", "மின்விளக்கு", "பழுதடைந்த விளக்கு", "street light", "தெரு விளக்குகள்"
    ],
    "electricity": [
        "மின்சாரம்", "மின் இணைப்பு", "மின்மாற்றி", "டிரான்ஸ்பார்மர்", "மின் கம்பம்", 
        "low voltage", "tangedco", "electricity", "மின்வெட்டு", "மின்கட்டணம்"
    ],
    "drainage": [
        "வடிகால்", "கழிவுநீர்", "சாக்கடை", "தூர்வார", "drainage", "storm water", "sewage"
    ],
    "patta_land": [
        "பட்டா", "சிட்டா", "அடங்கல்", "உட்பிரிவு", "நில அளவை", "சர்வே", "patta", 
        "sub division", "survey", "நத்தம் பட்டா", "வீட்டு மனை பட்டா"
    ],
    "encroachment": [
        "ஆக்கிரமிப்பு", "பொதுப்பாதை ஆக்கிரமிப்பு", "வழி ஆக்கிரமிப்பு", "முள்வேலி", "encroachment", "eviction"
    ],
    "ration_pds": [
        "ரேஷன்", "ரேஷன் அட்டை", "குடும்ப அட்டை", "நியாய விலைக்கடை", "smart card", "ration card", "pds"
    ],
    "agriculture": [
        "பயிர் காப்பீடு", "பயிர் சேதம்", "வறட்சி நிவாரணம்", "மழை வெள்ள நிவாரணம்", 
        "விவசாய கடன்", "crop loss relief", "crop insurance", "நெற்பயிர் சேதம்", "விதை மானியம்"
    ]
}

BILINGUAL_CONCEPT_MAP = {
    "ஆக்கிரமிப்பு": ["encroachment", "eviction"],
    "நீர்வழிப்பாதை": ["encroachment", "water resources", "water channel"],
    "நீர்வழிப் பாதை": ["encroachment", "water resources", "water channel"],
    "ஓடை": ["encroachment", "water resources", "stream"],
    "கால்நடை": ["animal husbandry", "veterinary", "ahfish", "ahvs"],
    "மருத்துவமனை": ["hospital", "dispensary", "veterinary", "other petitions - ah"],
    "கட்டிடம்": ["building", "repair and rehabilitation of old building", "building - pwd"],
    "பழுது": ["repair", "rehabilitation", "other petitions - ah", "building - pwd"],
    "சீரமைக்க": ["repair", "rehabilitation", "maintenance"],
    "மயானம்": ["burial ground", "cremation", "pathway to burial ground"],
    "புதைகுழி": ["burial ground", "cremation", "pathway to burial ground"],
    "பாதை": ["pathway", "pathway to burial ground", "road"],
    "சாலை": ["road", "highway"],
    "குடிநீர்": ["drinking water", "water supply", "water connection"],
    "தெருவிளக்கு": ["street light", "lighting"],
    "வடிகால்": ["drainage", "storm water"],
    "சாக்கடை": ["drainage", "sewage"],
    "கல்வி உதவித்தொகை": ["scholarship"],
    "கல்லூரி": ["college", "higher education", "high edu"],
    "உயர்கல்வி": ["higher education", "high edu"],
    "சமுதாய கூடம்": ["community hall"],
    "சமூக கூடம்": ["community hall"],
    "ஓய்வூதியம்": ["pension", "oap"],
    "பட்டா": ["patta", "patta transfer"],
}


def _compute_contradiction_score(
    query_text: str,
    candidate: Dict[str, Any],
    subject_line: str = "",
    prayer_section: str = ""
) -> float:
    """
    Computes contradiction penalty where a candidate strongly clashes with petition intent.
    Returns float in [0.0, 1.0].
    """
    q_lower = query_text.lower()
    t_sub = (candidate.get("grievance_sub_type") or "").lower()
    t_type = (candidate.get("grievance_type") or "").lower()
    t_dept = (candidate.get("department") or "").lower()
    cand_str = f"{t_dept} {t_type} {t_sub}"

    # 1. Civic infrastructure / Burial Ground / Veterinary / Road / Encroachment vs Pension
    has_civic_infrastructure = any(
        w in q_lower for w in [
            "மயானம்", "புதைகுழி", "சுடுகாடு", "பாதை", "சாலை", "குடிநீர்", "கழிவுநீர்",
            "வடிகால்", "மின்சாரம்", "மின்மாற்றி", "தெருவிளக்கு", "கட்டிடம்", "மருத்துவமனை",
            "ஆக்கிரமிப்பு", "ஓடை", "நீர்வழி", "burial ground", "cremat", "hospital", "dispensary"
        ]
    )
    has_explicit_pension_request = any(
        w in q_lower for w in [
            "ஓய்வூதியம்", "முதியோர் உதவித்தொகை", "விதவை உதவித்தொகை", "மாற்றுத்திறனாளி உதவித்தொகை",
            "உதவித்தொகை வழங்க", "பென்ஷன்", "oap", "pension", "ignoaps", "ignwps", "igndps"
        ]
    )
    is_pension_cand = any(
        w in cand_str for w in [
            "old age pension", "oap", "ignoaps", "destitute widow", "dwps", 
            "differently abled pension", "social security schemes (sss)", "pension"
        ]
    )
    if has_civic_infrastructure and not has_explicit_pension_request and is_pension_cand:
        return 1.0

    # 2. Veterinary Hospital / Animal Healthcare vs Agriculture / Horticulture
    has_vet_intent = any(w in q_lower for w in DOMAIN_INDICATORS["animal_husbandry"])
    if has_vet_intent:
        if any(w in cand_str for w in ["horti", "horticulture", "crop loss relief", "sericulture", "seeds", "pesticides"]):
            return 1.0

    # 3. Road Repair with standing water / puddles vs Drinking Water
    has_road_signals = _has_road_signals(q_lower)
    has_explicit_water_request = any(
        w in q_lower for w in [
            "குடிநீர் வழங்க", "குடிநீர் இணைப்பு", "குடிநீர் வசதி", "தண்ணீர் வசதி", 
            "drinking water supply", "water connection", "drinking water", "tap water", "water tap"
        ]
    )
    is_drinking_water_cand = any(
        w in cand_str for w in ["drinking water", "water connection", "insufficient water supply", "twad"]
    )
    if has_road_signals and not has_explicit_water_request and is_drinking_water_cand:
        return 1.0

    # 4. Drinking Water vs Road Maintenance
    has_water_signals = any(w in q_lower for w in DOMAIN_INDICATORS["drinking_water"])
    is_road_cand = any(
        w in cand_str for w in [
            "road maintenance", "road repair", "highways", "laying new roads", 
            "upgradation of panchayat road", "road - cc", "road - concrete", "road - odr", "road - mdr",
            "roads and bridges", "paver block", "bt road"
        ]
    )
    if has_water_signals and not has_road_signals and is_road_cand:
        return 1.0

    # 4b. Burial Ground / Crematorium Pathway vs Generic Road
    has_burial_intent = any(w in q_lower for w in DOMAIN_INDICATORS.get("burial_ground", [])) or any(
        w in q_lower for w in ["மயானம்", "சுடுகாடு", "புதைகுழி", "burial ground", "cremat", "மயானப் பாதை", "மயானப்பாதை"]
    )
    is_road_infrastructure = any(
        w in cand_str for w in [
            "road", "highway", "paver block", "bridge", "pavement", "laying new roads", 
            "upgradation of panchayat road", "roads and bridges", "road - cc", "road - concrete", "bt road"
        ]
    )
    is_burial_cand = any(w in cand_str for w in ["burial", "cremat", "மயானம்", "சுடுகாடு", "புதைகுழி"])
    if has_burial_intent and is_road_infrastructure and not is_burial_cand:
        return 1.0

    # 5. Education / Student Scholarship vs Pension
    has_edu_signals = any(w in q_lower for w in DOMAIN_INDICATORS["education"])
    if has_edu_signals and is_pension_cand and not has_explicit_pension_request:
        return 1.0

    # 6. Community Hall vs Scholarship / Pension
    has_hall_intent = any(w in q_lower for w in DOMAIN_INDICATORS["community_hall"])
    if has_hall_intent and (is_pension_cand or "scholarship" in cand_str):
        return 1.0

    # 6b. Civic Infrastructure / Community Hall vs Certificate / Genuineness Verification
    is_cert_verification = any(
        w in cand_str for w in [
            "genuiness", "genuineness", "community certificate", "caste certificate",
            "verification of community", "issuance of certificate", "verification - dtw"
        ]
    )
    has_cert_request = any(
        w in q_lower for w in [
            "சான்றிதழ் சரிபார்ப்பு", "உண்மைத்தன்மை", "சான்றிதழ் வழங்க", "சாதி சான்றிதழ்",
            "community certificate", "caste certificate", "genuiness", "genuineness"
        ]
    )
    if is_cert_verification and not has_cert_request and (has_civic_infrastructure or has_hall_intent or any(w in q_lower for w in ["சமுதாய கூடம்", "கூடம்", "மண்டபம்", "கட்டிடம்", "அமைக்க"])):
        return 1.0

    # 7. Non-widow petition vs Destitute Widow Pension
    has_widow_signals = any(w in q_lower for w in DOMAIN_INDICATORS["widow_pension"])
    is_widow_cand = any(w in cand_str for w in ["destitute widow", "dwps", "dwp"])
    if not has_widow_signals and is_widow_cand:
        return 0.8

    # 8. Non-disability petition vs Differently Abled Pension
    has_disability_signals = any(w in q_lower for w in DOMAIN_INDICATORS["disability_pension"])
    is_disability_cand = any(w in cand_str for w in ["differently abled", "dap"])
    if not has_disability_signals and is_disability_cand:
        return 0.8

    # 9. Public / Citizen petition vs Employee Grievances (Pension, Pending Dues, Compassionate Appointment)
    has_employee_markers = any(w in q_lower for w in [
        "பணியாளர்", "ஊழியர்", "பணிபுரிந்து", "ஓய்வுபெற்ற", "பணிக்கொடை", "பணி நியமனம்", 
        "employee", "service period", "compassionate appointment", "terminal benefits"
    ])
    is_employee_cand = any(w in cand_str for w in [
        "employee grievances", "pending dues", "service period fixation", 
        "compassionate appointment", "terminal benefits", "superannuation pension"
    ])
    if is_employee_cand and not has_employee_markers:
        return 1.0

    # 10. Civic infrastructure / Encroachment / General petition vs Accident, Death, Drowning, Incapacitation
    has_casualty_markers = any(w in q_lower for w in [
        "விபத்து", "இறப்பு", "உயிரிழப்பு", "மூழ்கி", "காயம்", "மரணம்", "உடலுறுப்பு இழப்பு",
        "accident", "death", "drowning", "fatal", "incapacitation"
    ])
    is_casualty_cand = any(w in cand_str for w in [
        "temporary incapacitation", "drowning in water bodies", "accident - death", 
        "funeral assistance", "innocent buyer scheme", "uzhavar pathukappu thittam"
    ])
    if is_casualty_cand and not has_casualty_markers:
        return 1.0

    # 11. Student Harassment / Anti-Ragging vs General Citizen petition
    has_student_markers = any(w in q_lower for w in ["மாணவர்", "மாணவி", "ராகிங்", "கல்லூரி சேர்க்கை", "மாணவர் கட்டணம்", "student", "ragging"])
    is_student_cand = any(w in cand_str for w in ["students - tanuvas", "students - tnfu", "anti ragging", "harassment - tanuvas", "harassment - tnfu"])
    if is_student_cand and not has_student_markers:
        return 1.0

    # 12. Sports Materials / Youth Programme vs General Citizen petition
    has_sports_markers = any(w in q_lower for w in ["விளையாட்டு", "விளையாட்டு உபகரணங்கள்", "இளைஞர் நலம்", "sports", "nnyks", "youth"])
    is_sports_cand = any(w in cand_str for w in ["sports materials", "youth programme - nnyks", "sports materials - nnyks"])
    if is_sports_cand and not has_sports_markers:
        return 1.0

    # 13. Civic infrastructure / Water / Road vs Forest & Wildlife (ENVFOR)
    is_forest_cand = any(w in cand_str for w in ["environment, climate change and forests", "forest", "envfor", "wildlife", "social forestry"])
    has_forest_markers = any(w in q_lower for w in ["காடு", "வனத்துறை", "மரங்கள் வெட்டுதல்", "வனவிலங்கு", "forest", "wildlife"])
    if is_forest_cand and not has_forest_markers:
        return 1.0

    # 14. College / Higher Education Scholarship vs Pre-Matric (School) / Overseas / Specific Sub-Community
    has_college_signals = any(w in q_lower for w in ["கல்லூரி", "college", "degree", "diploma", "higher education", "உயர்கல்வி", "பல்கலைக்கழகம்"])
    has_school_signals = any(w in q_lower for w in ["பள்ளி", "school", "10th", "12th", "pre matric", "pre-matric"])
    is_pre_matric = any(w in cand_str for w in ["pre matric", "school students", "school girls"])
    is_overseas = "overseas" in cand_str
    has_overseas_signals = any(w in q_lower for w in ["overseas", "வெளிநாடு", "foreign", "study abroad"])

    if has_college_signals and not has_school_signals and is_pre_matric:
        return 0.85
    if is_overseas and not has_overseas_signals:
        return 0.85

    has_community_explicit = any(w in q_lower for w in ["ஆதிதிராவிடர்", "பழங்குடியினர்", "sc", "st", "adw", "tribal", "bc", "mbc"])
    is_specific_community_scholarship = any(w in cand_str for w in ["tribal", "unclean occupation"])
    if not has_community_explicit and is_specific_community_scholarship:
        return 0.70

    return 0.0


def _compute_incidental_keyword_penalty(
    candidate: Dict[str, Any],
    subject_line: str,
    prayer_section: str,
    full_doc_text: str
) -> float:
    """
    Penalizes candidates that only matched incidental terms in the body narrative
    when the actual subject line and prayer have completely different intent.
    """
    subj_lower = (subject_line or "").lower()
    prayer_lower = (prayer_section or "").lower()
    combined_primary = f"{subj_lower} {prayer_lower}"
    cand_str = f"{candidate.get('department', '')} {candidate.get('grievance_type', '')} {candidate.get('grievance_sub_type', '')}".lower()

    # Case A: Incidental 'விவசாயிகள்' in veterinary or civic infrastructure petition
    if any(w in cand_str for w in ["agriculture", "horti", "crop loss"]):
        if not any(w in combined_primary for w in ["பயிர்", "வேளாண்மை", "விவசாய கடன்", "நெல்", "உரம்", "விதை"]):
            if any(w in combined_primary for w in ["கால்நடை", "மருத்துவமனை", "பாதை", "சாலை", "கட்டிடம்"]):
                return 0.5

    # Case B: Incidental 'முதியவர்கள்' in road or pathway petition
    if any(w in cand_str for w in ["pension", "oap", "ignoaps", "dwps"]):
        if not any(w in combined_primary for w in ["ஓய்வூதியம்", "உதவித்தொகை", "பென்ஷன்"]):
            if any(w in combined_primary for w in ["பாதை", "மயானம்", "புதைகுழி", "சாலை", "குடிநீர்"]):
                return 0.8

    return 0.0


class SemanticPetitionClassifier:
    """
    Production-grade dynamic database-driven semantic petition classifier.
    Combines High-Recall Multi-Path Retrieval with Contextual Reranking
    against all 1,847 official DB taxonomy mappings.
    """

    def __init__(self):
        self._vector_store = None
        self.top_k = DEFAULT_TOP_K

    def _get_vector_store(self):
        """Lazy-load the vector store to avoid circular imports."""
        if self._vector_store is None:
            from services.vector_store import vector_store
            self._vector_store = vector_store
        return self._vector_store

    def build_query_representation(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
    ) -> Tuple[str, str, str]:
        """
        Builds weighted query representation and extracts structured subject & prayer.
        Priority: Subject line (4x) > Prayer (3x) > Relevant Body Context (1x).
        """
        subject_line = _extract_subject_line(zone_b_body or full_doc_text)
        prayer = _extract_prayer_section(zone_b_body or full_doc_text)

        body_snippet = (zone_b_body or full_doc_text or "")[:400].strip()
        combined_lower = f"{subject_line} {prayer} {body_snippet}".lower()
        expanded_concepts = []

        if _has_road_signals(combined_lower):
            expanded_concepts.append("road highways road repair laying new roads village road infrastructure street")

        # Explicit concept expansions bridging Tamil intent to DB search_text
        concept_terms_map = {
            ("கால்நடை", "கால்நடை மருத்துவமனை", "கால்நடை மருந்தகம்", "கால்நடை மருத்துவர்", "கால்நடை பராமரிப்பு", "ஆடு மாடு மருத்துவம்", "veterinary"): 
                "Animal Husbandry and Dairying and Fisheries and Fishermen Welfare Department AHFISH Director of Animal Husbandry and Veterinary Services AH Joint Director AHVS Services AH Other Petitions AH veterinary hospital dispensary",
            ("புதைகுழி", "மயானம்", "சுடுகாடு", "மயானப்பாதை", "மயானப் பாதை", "இறுதி ஊர்வலம்", "மயான வழி", "burial ground", "pathway to burial ground"): 
                "Social Justice Department SJD Directorate of Adi Dravidar Welfare Burial Ground Pathway To Burial Ground Burial Ground - ADW District Adi Dravidar Welfare Officer DADWO Rural Development RDPR Burial/Cremation Ground",
            ("நீர்வழிப்பாதை", "நீர்வழிப் பாதை", "நீர்வழி", "ஓடை ஆக்கிரமிப்பு", "நீர்நிலை ஆக்கிரமிப்பு", "கால்வாய் ஆக்கிரமிப்பு", "ஏரி ஆக்கிரமிப்பு", "மழைநீர் தேக்கம்"): 
                "Revenue and Disaster Management REV Encroachment - REV Tahsildar Water Resources Department WRD Removal of Encroachments - WRD Executive Engineer WRD water course water channel stream lake encroachment eviction",
            ("மருத்துவமனை கட்டிடம்", "அரசு கட்டிடம்", "கட்டிடம் பழுது", "கட்டிட சீரமைப்பு", "பழுதடைந்த கட்டிடம்", "rehabilitation of old building"): 
                "Public Works Department PWD PWD Buildings Repair and Rehabilitation of Old Building Demolition of old Building",
            ("குடிநீர்", "தண்ணீர் குழாய்", "மேல்நிலைத் தொட்டி", "குடிநீர் இணைப்பு"): 
                "drinking water water supply water connection TWAD CMA",
            ("கல்வி உதவித்தொகை", "கல்வி உதவித் தொகை", "post matric scholarship", "pre matric scholarship", "கல்விக் கட்டண சலுகை"): 
                "scholarship student financial aid post matric pre matric higher education scholarship",
            ("கல்லூரி", "பல்கலைக்கழகம்", "collegiate", "university"): 
                "higher education collegiate university",
            ("பள்ளிக்கூடம்", "பள்ளி கல்வி", "school education"): 
                "school education department",
            ("சமுதாய கூடம்", "சமூக கூடம்", "சமுதாயக்கூடம்", "சமுதாய பவன்", "community hall", "திருமண மண்டபம்"): 
                "community hall civic infrastructure hall",
            ("ஆதிதிராவிடர்", "ஆதி திராவிடர்", "adw", "dadw", "adi dravidar"): 
                "adi dravidar welfare ADW social justice",
            ("முதியோர் ஓய்வூதியம்", "முதியோர் உதவித்தொகை", "முதியோர் பென்ஷன்", "oap", "ignoaps"): 
                "(IGNOAPS) Commissioner of Revenue Administration Tahsildar SSS Revenue and Disaster Management REV Pension old age pension OAP",
            ("விதவை உதவித்தொகை", "ஆதரவற்ற விதவை", "விதவை ஓய்வூதியம்"): 
                "destitute widow pension scheme DWPS DWP",
            ("மாற்றுத்திறனாளி உதவித்தொகை", "மாற்றுத்திறனாளி ஓய்வூதியம்"): 
                "differently abled pension DAP disability assistance",
            ("மின்சாரம்", "மின் இணைப்பு", "மின்மாற்றி", "டிரான்ஸ்பார்மர்"): 
                "electricity supply tangedco energy power low voltage",
            ("பட்டா", "சிட்டா", "அடங்கல்", "உட்பிரிவு", "நத்தம் பட்டா"): 
                "patta transfer land records natham patta land administration survey",
            ("ஆக்கிரமிப்பு", "பொதுப்பாதை ஆக்கிரமிப்பு"): 
                "land encroachment eviction pathway government land",
            ("வடிகால்", "கழிவுநீர்", "சாக்கடை"): 
                "drainage storm water drain sewage desilting culverts",
            ("தெருவிளக்கு", "மின்விளக்கு"): 
                "street lights lighting",
            ("ரேஷன்", "குடும்ப அட்டை", "நியாய விலைக்கடை"): 
                "civil supplies ration card smart card PDS rice distribution",
            ("வாரிசு சான்றிதழ்", "இறப்பு சான்று"): 
                "legal heir certificate revenue administration",
            ("சாதி சான்றிதழ்", "சாதி சான்று"): 
                "community certificate social justice revenue",
            ("பயிர் சேதம்", "பயிர் காப்பீடு", "நெற்பயிர் சேதம்", "வறட்சி நிவாரணம்"): 
                "agriculture and farmers welfares department AGRI crop loss relief crop damage paddy relief farmer agriculture schemes"
        }

        for triggers, exp in concept_terms_map.items():
            if any(t in combined_lower for t in triggers):
                expanded_concepts.append(exp)

        query_parts = []
        if expanded_concepts:
            query_parts.append(" | ".join(expanded_concepts))
        if subject_line:
            query_parts.append(f"பொருள்: {subject_line}")
        if prayer:
            query_parts.append(f"கோரிக்கை: {prayer}")
        if body_snippet:
            query_parts.append(body_snippet)

        query_text = " \n ".join(query_parts).strip()
        if not query_text:
            query_text = (full_doc_text or "")[:500].strip() or "மனு"

        return query_text, subject_line, prayer

    def multi_path_retrieve(
        self,
        query_text: str,
        subject_line: str,
        prayer_section: str,
        zone_a_header: str,
        zone_b_body: str,
        top_per_path: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Executes High-Recall Multi-Path Retrieval against all 1,847 taxonomy records.
        Paths:
          - Path A: Semantic Vector Retrieval (Intent Query) -> Top 20
          - Path B: Subject Line Embedding & Keyword Retrieval -> Top 20
          - Path C: Prayer / Requested Action Retrieval -> Top 20
          - Path D: Domain Concept & Recipient Header Retrieval -> Top 20
          - Path E: Relevant Body Context Retrieval -> Top 20
        """
        from services.taxonomy_matcher import taxonomy_matcher

        if not taxonomy_matcher.taxonomy or taxonomy_matcher.taxonomy_embeddings is None or len(taxonomy_matcher.taxonomy_embeddings) == 0:
            try:
                taxonomy_matcher.load_taxonomy_sync()
            except Exception as e:
                logger.warning(f"Auto-load taxonomy note: {e}")

        records = taxonomy_matcher.taxonomy
        embeddings = taxonomy_matcher.taxonomy_embeddings

        if not records or embeddings is None or len(embeddings) == 0:
            logger.warning("Taxonomy records or embeddings not loaded.")
            return []

        vs = self._get_vector_store()
        candidates_by_id: Dict[int, Dict[str, Any]] = {}

        # ── PATH A: Semantic Intent Vector Search ──
        query_embs = vs.encode([query_text])
        if query_embs is not None and len(query_embs) > 0:
            q_vec = query_embs[0]
            scores_a = np.dot(embeddings, q_vec)
            top_idx_a = np.argsort(-scores_a)[:top_per_path]
            for idx in top_idx_a:
                rec = records[idx]
                cid = rec["id"]
                candidates_by_id.setdefault(cid, dict(rec))
                candidates_by_id[cid].setdefault("retrieval_paths", set()).add("semantic")
                candidates_by_id[cid]["path_a_score"] = float(scores_a[idx])

        # ── PATH B: Subject Line Vector & Keyword Retrieval ──
        if subject_line:
            subj_embs = vs.encode([subject_line])
            if subj_embs is not None and len(subj_embs) > 0:
                s_vec = subj_embs[0]
                scores_b = np.dot(embeddings, s_vec)
                top_idx_b = np.argsort(-scores_b)[:top_per_path]
                for idx in top_idx_b:
                    rec = records[idx]
                    cid = rec["id"]
                    candidates_by_id.setdefault(cid, dict(rec))
                    candidates_by_id[cid].setdefault("retrieval_paths", set()).add("subject_vector")
                    candidates_by_id[cid]["path_b_score"] = float(scores_b[idx])

            # Lexical subject matching
            subj_lower = subject_line.lower()
            subj_words = [w for w in re.split(r'[\s\-:,/()]+', subj_lower) if len(w) >= 3]
            for rec in records:
                s_text = rec.get("search_text", "").lower()
                matches = sum(1 for w in subj_words if w in s_text)
                if matches >= 2 or (subj_words and matches == len(subj_words)):
                    cid = rec["id"]
                    candidates_by_id.setdefault(cid, dict(rec))
                    candidates_by_id[cid].setdefault("retrieval_paths", set()).add("subject_lexical")

        # ── PATH C: Prayer / Requested Action Retrieval ──
        if prayer_section:
            prayer_embs = vs.encode([prayer_section])
            if prayer_embs is not None and len(prayer_embs) > 0:
                p_vec = prayer_embs[0]
                scores_c = np.dot(embeddings, p_vec)
                top_idx_c = np.argsort(-scores_c)[:top_per_path]
                for idx in top_idx_c:
                    rec = records[idx]
                    cid = rec["id"]
                    candidates_by_id.setdefault(cid, dict(rec))
                    candidates_by_id[cid].setdefault("retrieval_paths", set()).add("prayer_vector")
                    candidates_by_id[cid]["path_c_score"] = float(scores_c[idx])

        # ── PATH D: Domain Concept & Recipient Addressee Retrieval ──
        combined_text_lower = f"{zone_a_header} {subject_line} {prayer_section} {zone_b_body}".lower()
        active_domains = []
        for domain, keywords in DOMAIN_INDICATORS.items():
            if any(kw in combined_text_lower for kw in keywords):
                active_domains.append(domain)

        recipient_tokens = []
        if zone_a_header:
            recip_m = re.search(r'(?:பெறுநர்|To)\s*[:,\.\-]?\s*\n*([\s\S]+?)(?=\n\s*(?:அய்யா|ஐயா|வணக்கம்|பொருள்|$))', zone_a_header, re.IGNORECASE)
            if recip_m:
                r_text = recip_m.group(1).lower()
                if "ஆதிதிராவிடர்" in r_text or "adw" in r_text:
                    recipient_tokens.append("adi dravidar")
                if "வருவாய்" in r_text or "revenue" in r_text:
                    recipient_tokens.append("revenue")
                if "கால்நடை" in r_text or "animal" in r_text:
                    recipient_tokens.append("animal husbandry")
                if "நகராட்சி" in r_text or "மாநகராட்சி" in r_text or "maws" in r_text:
                    recipient_tokens.append("municipal")
                if "ஊராட்சி" in r_text or "rdpr" in r_text:
                    recipient_tokens.append("rural development")

        for rec in records:
            cand_str = f"{rec.get('department', '')} {rec.get('grievance_type', '')} {rec.get('grievance_sub_type', '')} {rec.get('search_text', '')}".lower()
            hit = False
            # Check domain matches
            if "animal_husbandry" in active_domains and any(w in cand_str for w in ["animal husbandry", "ahfish", "veterinary", "ahvs"]):
                hit = True
            elif "burial_ground" in active_domains and any(w in cand_str for w in ["burial ground", "pathway to burial ground", "cremation"]):
                hit = True
            elif "water_channel_encroachment" in active_domains and any(w in cand_str for w in ["encroachment - rev", "removal of encroachments - wrd", "water resources"]):
                hit = True
            elif "building_repair" in active_domains and any(w in cand_str for w in ["repair and rehabilitation of old building", "pwd buildings"]):
                hit = True

            # Check recipient addressee matches
            if recipient_tokens and any(rt in cand_str for rt in recipient_tokens):
                hit = True

            if hit:
                cid = rec["id"]
                candidates_by_id.setdefault(cid, dict(rec))
                candidates_by_id[cid].setdefault("retrieval_paths", set()).add("domain_recipient")

        # ── PATH E: Relevant Body Context Retrieval ──
        body_words = [w for w in re.split(r'[\s\-:,/()]+', zone_b_body.lower()) if len(w) >= 4]
        stop_words = {"நான்", "நாங்கள்", "எங்கள்", "பகுதி", "மற்றும்", "உள்ளது", "மிகவும்", "வேண்டும்", "உரிய", "நடவடிக்கை"}
        meaningful_body_words = [w for w in body_words if w not in stop_words][:25]
        for rec in records:
            s_text = rec.get("search_text", "").lower()
            matches = sum(1 for w in meaningful_body_words if w in s_text)
            if matches >= 3:
                cid = rec["id"]
                candidates_by_id.setdefault(cid, dict(rec))
                candidates_by_id[cid].setdefault("retrieval_paths", set()).add("body_context")

        return list(candidates_by_id.values())

    def contextual_rerank(
        self,
        candidates: List[Dict[str, Any]],
        subject_line: str,
        prayer_section: str,
        query_text: str,
        zone_a_header: str,
        full_doc_text: str
    ) -> List[Dict[str, Any]]:
        """
        Reranks unified candidates using intent, subject, prayer, domain signals,
        contradiction penalties, and incidental keyword penalties.
        """
        scored_candidates = []
        combined_intent = f"{subject_line} {prayer_section} {query_text}".lower()

        # Check recipient department match in header
        recip_dept_match = ""
        if zone_a_header:
            r_lower = zone_a_header.lower()
            if "ஆதிதிராவிடர்" in r_lower:
                recip_dept_match = "Social Justice Department (SJD)"
            elif "வருவாய்" in r_lower:
                recip_dept_match = "Revenue and Disaster Management (REV)"
            elif "கால்நடை" in r_lower:
                recip_dept_match = "Animal Husbandry and Dairying and Fisheries and Fishermen Welfare Department (AHFISH)"

        for cand in candidates:
            # 1. Semantic score
            semantic_score = float(cand.get("path_a_score", cand.get("semantic_score", 0.0)))
            semantic_score = max(0.0, min(1.0, semantic_score))

            # 2. Subject relevance score (Direct string match + Multi-token alignment + Bilingual concept matching)
            subject_score = 0.0
            if subject_line:
                cand_sub = (cand.get("grievance_sub_type") or "").lower()
                cand_type = (cand.get("grievance_type") or "").lower()
                cand_dept = (cand.get("department") or "").lower()
                cand_search = (cand.get("search_text") or "").lower()
                cand_combined = f"{cand_dept} {cand_type} {cand_sub} {cand_search}"
                s_lower = subject_line.lower()

                sub_align = _score_candidate_text_alignment(cand_sub, s_lower)
                type_align = _score_candidate_text_alignment(cand_type, s_lower)
                if sub_align >= 0.9:
                    subject_score = max(subject_score, sub_align)
                else:
                    subject_score = max(subject_score, 0.6 * sub_align + 0.4 * type_align)

                for ta_kw, en_syns in BILINGUAL_CONCEPT_MAP.items():
                    if ta_kw in s_lower:
                        if any(syn in cand_combined for syn in en_syns):
                            subject_score = max(subject_score, 0.85)

                if cand.get("path_b_score"):
                    subject_score = max(subject_score, float(cand["path_b_score"]))
            subject_score = min(1.0, subject_score)

            # 3. Prayer relevance score (Direct string match + Multi-token alignment + Bilingual concept matching)
            prayer_score = 0.0
            if prayer_section:
                cand_sub = (cand.get("grievance_sub_type") or "").lower()
                cand_type = (cand.get("grievance_type") or "").lower()
                cand_dept = (cand.get("department") or "").lower()
                cand_search = (cand.get("search_text") or "").lower()
                cand_combined = f"{cand_dept} {cand_type} {cand_sub} {cand_search}"
                p_lower = prayer_section.lower()

                sub_align_p = _score_candidate_text_alignment(cand_sub, p_lower)
                type_align_p = _score_candidate_text_alignment(cand_type, p_lower)
                if sub_align_p >= 0.9:
                    prayer_score = max(prayer_score, sub_align_p)
                else:
                    prayer_score = max(prayer_score, 0.6 * sub_align_p + 0.4 * type_align_p)

                for ta_kw, en_syns in BILINGUAL_CONCEPT_MAP.items():
                    if ta_kw in p_lower:
                        if any(syn in cand_combined for syn in en_syns):
                            prayer_score = max(prayer_score, 0.80)

                if cand.get("path_c_score"):
                    prayer_score = max(prayer_score, float(cand["path_c_score"]))
            prayer_score = min(1.0, prayer_score)

            # 4. Domain Context compatibility
            domain_score = 0.0
            cand_str = f"{cand.get('department', '')} {cand.get('grievance_type', '')} {cand.get('grievance_sub_type', '')}".lower()
            if any(w in combined_intent for w in DOMAIN_INDICATORS["animal_husbandry"]) and any(w in cand_str for w in ["animal husbandry", "ahvs", "veterinary"]):
                domain_score = 1.0
            elif any(w in combined_intent for w in DOMAIN_INDICATORS["burial_ground"]) and any(w in cand_str for w in ["burial ground", "pathway to burial ground"]):
                domain_score = 1.0
            elif any(w in combined_intent for w in DOMAIN_INDICATORS["water_channel_encroachment"]) and any(w in cand_str for w in ["encroachment - rev", "removal of encroachments - wrd"]):
                domain_score = 1.0
            elif any(w in combined_intent for w in DOMAIN_INDICATORS["building_repair"]) and any(w in cand_str for w in ["repair and rehabilitation of old building", "pwd buildings"]):
                domain_score = 0.9
            elif any(w in combined_intent for w in ["கல்லூரி", "college", "higher education", "உயர்கல்வி", "பல்கலைக்கழகம்"]) and any(w in cand_str for w in ["scholarship - high edu", "higher education department", "college students"]):
                domain_score = 1.0
            elif any(w in combined_intent for w in DOMAIN_INDICATORS["community_hall"]) and any(w in cand_str for w in ["community hall"]):
                domain_score = 1.0
            elif any(w in combined_intent for w in DOMAIN_INDICATORS["scholarship"]) and any(w in cand_str for w in ["scholarship"]):
                domain_score = 0.8

            # 5. Recipient Header Boost
            recipient_boost = 0.0
            if recip_dept_match and recip_dept_match.lower() in cand.get("department", "").lower():
                recipient_boost = RECIPIENT_BOOST

            # 6. Contradiction Penalty
            contradiction_penalty = _compute_contradiction_score(
                query_text=combined_intent,
                candidate=cand,
                subject_line=subject_line,
                prayer_section=prayer_section
            )

            # 7. Incidental Keyword Penalty
            incidental_penalty = _compute_incidental_keyword_penalty(
                candidate=cand,
                subject_line=subject_line,
                prayer_section=prayer_section,
                full_doc_text=full_doc_text
            )

            # Multi-signal final score calculation
            final_score = (
                SEMANTIC_WEIGHT * semantic_score
                + SUBJECT_WEIGHT * subject_score
                + PRAYER_WEIGHT * prayer_score
                + DOMAIN_WEIGHT * domain_score
                + recipient_boost
                - contradiction_penalty
                - incidental_penalty
            )
            final_score = max(0.0, min(1.0, round(final_score, 4)))

            paths = list(cand.get("retrieval_paths", []))
            scored_candidates.append({
                "Taxonomy_ID": cand.get("id"),
                "taxonomy_id": cand.get("id"),
                "Department": cand.get("department", ""),
                "department": cand.get("department", ""),
                "department_code": cand.get("department_code", ""),
                "Grievance Type": cand.get("grievance_type", ""),
                "grievance_type": cand.get("grievance_type", ""),
                "Grievance Sub Type": cand.get("grievance_sub_type", ""),
                "grievance_sub_type": cand.get("grievance_sub_type", ""),
                "Sub Department": cand.get("sub_department", ""),
                "sub_department": cand.get("sub_department", ""),
                "Responsible officer": cand.get("responsible_officer", ""),
                "responsible_officer": cand.get("responsible_officer", ""),
                "search_text": cand.get("search_text", ""),
                "semantic_score": semantic_score,
                "subject_score": subject_score,
                "prayer_score": prayer_score,
                "domain_score": domain_score,
                "recipient_boost": recipient_boost,
                "contradiction_penalty": contradiction_penalty,
                "incidental_penalty": incidental_penalty,
                "final_score": final_score,
                "retrieval_paths": paths,
            })

        # Sort descending by multi-signal final score
        scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return scored_candidates

    def classify(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        """
        Executes High-Recall Multi-Path Retrieval + Contextual Reranking
        to select the authoritative Top-10 taxonomy candidates.
        """
        query_text, subject_line, prayer = self.build_query_representation(
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            full_doc_text=full_doc_text
        )

        # 1. High-Recall Multi-Path Candidate Retrieval
        retrieved_candidates = self.multi_path_retrieve(
            query_text=query_text,
            subject_line=subject_line,
            prayer_section=prayer,
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            top_per_path=20
        )

        if not retrieved_candidates:
            logger.warning("No candidates retrieved from multi-path taxonomy search.")
            return self._empty_result(subject_line)

        # 2. Contextual Reranking
        scored_candidates = self.contextual_rerank(
            candidates=retrieved_candidates,
            subject_line=subject_line,
            prayer_section=prayer,
            query_text=query_text,
            zone_a_header=zone_a_header,
            full_doc_text=full_doc_text
        )

        # 3. Take Top-K candidates (Default Top 10)
        top_candidates = scored_candidates[:top_k]

        best = top_candidates[0]
        second = top_candidates[1] if len(top_candidates) > 1 else None

        best_score = best["final_score"]
        second_score = second["final_score"] if second else 0.0
        margin = round(best_score - second_score, 4)
        is_ambiguous = margin < RERANK_MARGIN_THRESHOLD

        top3_log = ", ".join(
            f"ID {c['taxonomy_id']} ({c['department']} - {c['grievance_sub_type']}): score={c['final_score']} (sem={c['semantic_score']}, sub={c['subject_score']}, pray={c['prayer_score']}, con={c['contradiction_penalty']})"
            for c in top_candidates[:3]
        )
        logger.info(
            f"🎯 Multi-Path Taxonomy Classification: ID={best['taxonomy_id']} | "
            f"Dept='{best['department']}' | SubType='{best['grievance_sub_type']}' | "
            f"score={best_score:.4f} (margin={margin:.4f}, ambiguous={is_ambiguous}) | Top3: {top3_log}"
        )

        label = f"{best['grievance_type']} / {best['grievance_sub_type']}"
        scores_map = {str(c["taxonomy_id"]): c["final_score"] for c in top_candidates[:5]}

        return {
            "taxonomy_id": best["taxonomy_id"],
            "category_key": f"tax_{best['taxonomy_id']}",
            "label": label,
            "department": best["department"],
            "department_code": best.get("department_code", ""),
            "grievance_type": best["grievance_type"],
            "grievance_subtype": best["grievance_sub_type"],
            "sub_department": best["sub_department"],
            "responsible_officer": best["responsible_officer"],
            "confidence": best_score,
            "confidence_gap": margin,
            "margin": margin,
            "is_ambiguous": is_ambiguous,
            "method": "high_recall_multipath",
            "subject_line": subject_line,
            "prayer_section": prayer,
            "candidates": top_candidates,
            "scores": scores_map,
            "classification_status": "resolved" if not is_ambiguous else "ambiguous",
        }

    def _empty_result(self, subject_line: str = "") -> Dict[str, Any]:
        """Safe fallback for empty retrieval state."""
        return {
            "taxonomy_id": None,
            "category_key": "tax_none",
            "label": "General Grievance / Public Grievance Redressal",
            "department": "General Administration",
            "department_code": "GAD",
            "grievance_type": "General Grievance",
            "grievance_subtype": "Public Grievance Redressal",
            "sub_department": "General Administration / பொது நிர்வாகம்",
            "responsible_officer": "துறை அலுவலர்",
            "confidence": 0.0,
            "confidence_gap": 0.0,
            "margin": 0.0,
            "is_ambiguous": True,
            "method": "empty_fallback",
            "subject_line": subject_line,
            "prayer_section": "",
            "candidates": [],
            "scores": {},
        }

    async def classify_with_rerank(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
        llm_client: Any = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        """
        Async interface for multi-path retrieval + contextual reranking.
        Ensures full backward compatibility with callers invoking classify_with_rerank.
        """
        return self.classify(
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            full_doc_text=full_doc_text,
            top_k=top_k,
        )


# Singleton instance
semantic_classifier = SemanticPetitionClassifier()
