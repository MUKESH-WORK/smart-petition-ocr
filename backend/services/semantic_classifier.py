"""
Dynamic Database-Driven Semantic Petition Classifier
====================================================
Replaces static 16-anchor classification with vector retrieval against all
1,847 official database taxonomy rows in cm_taxonomy_mappings.

Architecture:
  - Pillar 1 (Zonal Intent Extraction):
      Extracts பொருள் (Subject) and கோரிக்கை (Prayer) sections for high-fidelity intent.
  - Pillar 2 (In-Memory 1,847 Taxonomy Vector Retrieval):
      Encodes petition text into 384-dim normalized vector via sentence-transformers,
      then computes fast vectorized cosine similarity against all 1,847 DB taxonomy embeddings.
  - Pillar 3 (Multi-Signal Candidate Ranking):
      Combines Semantic (0.40) + Fuzzy/Lexical (0.20) + Context (0.25) - Contradiction (0.30)
      to eliminate false positives (e.g. scholarship -> OAP, road with water -> drinking water).
  - Pillar 4 (Decision Margin & Ambiguity Detection):
      Measures margin = top_score - second_score (threshold = 0.08).
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configurable Heuristic Ranking Weights (Section 14 of Spec)
# ─────────────────────────────────────────────────────────────────────────────
SEMANTIC_WEIGHT = 0.40
FUZZY_WEIGHT = 0.20
CONTEXT_WEIGHT = 0.25
CONTRADICTION_WEIGHT = 0.30
RERANK_MARGIN_THRESHOLD = 0.08
DEFAULT_TOP_K = 12


def _extract_subject_line(zone_b_body: str) -> str:
    """
    Pillar 1: Extract the பொருள் (Subject) line from Zone B.
    This is the most authoritative single sentence for classification.
    """
    if not zone_b_body:
        return ""

    subject_match = re.search(
        r'(?:பொருள்|Subject|Porul)\s*[:：]\s*(.+?)(?:\n|$)',
        zone_b_body,
        re.IGNORECASE
    )
    if subject_match:
        subject = subject_match.group(1).strip()
        subject = re.sub(r'\s+', ' ', subject).strip(' .,;:-')
        return subject

    return ""


def _extract_prayer_section(text: str) -> str:
    """
    Pillar 1: Extract the prayer/request section (கோரிக்கை / பிரார்த்தனை).
    This is the petitioner's formal request — the ground truth of what they want.
    """
    if not text:
        return ""

    search_text = text
    subj_match = re.search(r'(?:பொருள்|Subject|Porul)\s*[:：].*?(?:\n|$)', text, re.IGNORECASE)
    if subj_match:
        search_text = text[subj_match.end():]

    prayer_patterns = [
        r'(?:^|\n)\s*(?:கோரிக்கைகள்?|பிரார்த்தனை|வேண்டுகோள்)\s*[:：]\s*(.+?)(?:\n\s*(?:இப்படிக்கு|இவண்|நன்றி|நாள்|தேதி)|$)',
        r'(?:^|\n)\s*(?:எனவே|ஆகவே|ஆதலால்)\s*[,]?\s*(.+?)(?:கேட்டுக்\s*கொள்கிறேன்|வேண்டுகிறேன்|கோருகிறேன்|அளித்துள்ளார்|$)',
    ]

    for pattern in prayer_patterns:
        match = re.search(pattern, search_text, re.DOTALL | re.IGNORECASE)
        if match:
            prayer = match.group(1).strip()
            prayer = re.sub(r'\s+', ' ', prayer).strip(' .,;:-')
            if len(prayer) > 10:
                return prayer

    sig_idx = search_text.find("இப்படிக்கு")
    if sig_idx == -1:
        sig_idx = search_text.find("இவண்")
    if sig_idx > 100:
        last_section = search_text[max(0, sig_idx - 500):sig_idx].strip()
        sentences = [s.strip() for s in re.split(r'[.।\n]', last_section) if len(s.strip()) > 20]
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
    # For 'ரோடு' or 'road', require road action/problem context so it doesn't trigger on bare street addresses
    if re.search(r'(?:ரோடு|road)\s*(?:சீரமைக்க|பழுது|அமைக்க|பராமரிப்பு|குழி|சேதம்|விளக்கு|வசதி|பணி|repair|maintenance|laying|damaged|condition|pothole)', cleaned):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Domain Keyword Lexicons for Context & Contradiction Scoring
# ─────────────────────────────────────────────────────────────────────────────
DOMAIN_INDICATORS = {
    "scholarship": [
        "scholarship", "கல்வி உதவித்தொகை", "கல்வி உதவித் தொகை", "கல்வி உதவி தொகை",
        "உதவித்தொகை", "உதவித் தொகை", "உதவி தொகை", "scholarship amount",
        "scholarship application", "post matric scholarship", "pre matric scholarship",
        "கல்விக் கட்டண சலுகை", "கல்வி உதவி"
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
        "முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "senior citizen", 
        "old age", "வாழ்வாதாரம் இல்லாமல்", "வேலைக்கு செல்ல முடியவில்லை", "வயதாகிவிட்டது", 
        "மகனோ மகளோ", "ஆதரவற்ற முதியோர்", "oap"
    ],
    "widow_pension": [
        "விதவை", "ஆதரவற்ற விதவை", "கணவர் இறந்த", "widow", "dwps", "dwp", "விதவை உதவி"
    ],
    "disability_pension": [
        "மாற்றுத்திறனாளி", "ஊனம்", "உடல் ஊனம்", "differently abled", "handicapped", "dap", "ஊனமுற்ற"
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
        "வடிகால்", "கழிவுநீர்", "சாக்கடை", "தூர்வார", "drainage", "storm water", "sewage", "கால்வாய்"
    ],
    "patta_land": [
        "பட்டா", "சிட்டா", "அடங்கல்", "உட்பிரிவு", "நில அளவை", "சர்வே", "patta", 
        "sub division", "survey", "நத்தம்", "வீட்டு மனை"
    ],
    "encroachment": [
        "ஆக்கிரமிப்பு", "பொதுப்பாதை ஆக்கிரமிப்பு", "வழி ஆக்கிரமிப்பு", "முள்வேலி", "encroachment"
    ],
    "ration_pds": [
        "ரேஷன்", "ரேஷன் அட்டை", "குடும்ப அட்டை", "நியாய விலைக்கடை", "smart card", "ration card", "pds"
    ],
    "certificates": [
        "வாரிசு சான்றிதழ்", "சாதி சான்றிதழ்", "இருப்பிட சான்றிதழ்", "வருமான சான்றிதழ்", 
        "legal heir", "community certificate"
    ],
    "agriculture": [
        "விவசாய", "விவசாயி", "பயிர்", "நெற்பயிர்", "வேளாண்மை", "உழவர்", "பயிர் காப்பீடு", 
        "பயிர் சேதம்", "வறட்சி நிவாரணம்", "மழை வெள்ள நிவாரணம்", "விவசாய கடன்",
        "crop", "farmer", "agriculture", "horticulture", "harvest", "crop loss relief",
        "நெல்", "பயிர் இழப்பீடு"
    ]
}


def _compute_fuzzy_score(query_text: str, candidate: Dict[str, Any]) -> float:
    """
    Computes lexical / token overlap score between query and candidate taxonomy fields.
    Returns float in [0.0, 1.0].
    """
    q_lower = query_text.lower()
    t_sub = (candidate.get("grievance_sub_type") or "").lower()
    t_type = (candidate.get("grievance_type") or "").lower()
    t_dept = (candidate.get("department") or "").lower()
    t_search = (candidate.get("search_text") or "").lower()

    score = 0.0

    # Subtype exact / substring matches
    if t_sub:
        if t_sub in q_lower:
            score += 0.45
        elif "ignoaps" in t_sub and any(w in q_lower for w in ["oap", "முதியோர்", "வயது மூப்பு", "old age"]):
            score += 0.45
        elif "scholarship" in t_sub and any(w in q_lower for w in DOMAIN_INDICATORS["scholarship"]):
            if "technical" in t_sub and not any(w in q_lower for w in ["technical", "தொழில்நுட்ப", "engineering", "பொறியியல்", "polytechnic", "பாலிடெக்னிக்"]):
                score += 0.25
            else:
                score += 0.45
        elif "community hall" in t_sub and any(w in q_lower for w in DOMAIN_INDICATORS["community_hall"]):
            score += 0.45
        else:
            tokens = [tok for tok in re.split(r'[\s\/\-\(\)]+', t_sub) if len(tok) >= 3]
            matches = sum(1 for tok in tokens if tok in q_lower)
            if tokens:
                score += 0.35 * (matches / len(tokens))

    # Type exact / substring matches
    if t_type:
        if t_type in q_lower:
            score += 0.30
        elif "scholarship" in t_type and any(w in q_lower for w in DOMAIN_INDICATORS["scholarship"]):
            if "technical" in t_type and not any(w in q_lower for w in ["technical", "தொழில்நுட்ப", "engineering", "பொறியியல்", "polytechnic", "பாலிடெக்னிக்"]):
                score += 0.15
            else:
                score += 0.30
        elif "community hall" in t_type and any(w in q_lower for w in DOMAIN_INDICATORS["community_hall"]):
            score += 0.30
        else:
            tokens = [tok for tok in re.split(r'[\s\/\-\(\)]+', t_type) if len(tok) >= 3]
            matches = sum(1 for tok in tokens if tok in q_lower)
            if tokens:
                score += 0.20 * (matches / len(tokens))

    # Department matches
    dept_core = t_dept.split("(")[0].strip().lower()
    if dept_core and (dept_core in q_lower or any(word in q_lower for word in dept_core.split() if len(word) >= 4)):
        score += 0.15

    # Acronym match (e.g. REV, HIGHEDU, RDPR, SJD)
    acronym_match = re.search(r'\(([A-Z0-9]+)\)', t_dept)
    if acronym_match and acronym_match.group(1).lower() in q_lower:
        score += 0.10

    return min(1.0, round(score, 4))


def _compute_context_score(query_text: str, candidate: Dict[str, Any]) -> float:
    """
    Computes domain context compatibility between petition and candidate taxonomy.
    Returns float in [0.0, 1.0].
    """
    q_lower = query_text.lower()
    t_sub = (candidate.get("grievance_sub_type") or "").lower()
    t_type = (candidate.get("grievance_type") or "").lower()
    t_dept = (candidate.get("department") or "").lower()
    cand_str = f"{t_dept} {t_type} {t_sub}"

    # 1. Scholarship context: Requires explicit scholarship evidence
    has_scholarship_query = any(w in q_lower for w in DOMAIN_INDICATORS["scholarship"])
    cand_has_scholarship = "scholarship" in cand_str or "கல்வி உதவி" in cand_str

    if cand_has_scholarship:
        if has_scholarship_query:
            return 1.0
        # If candidate is a scholarship candidate, but query has NO explicit scholarship evidence:
        return 0.0

    # 2. General non-scholarship Education context
    has_edu_query = any(w in q_lower for w in DOMAIN_INDICATORS["education"])
    cand_is_edu = any(w in cand_str for w in ["higher education", "collegiate", "education", "school", "university"])
    if has_edu_query and cand_is_edu and not cand_has_scholarship:
        return 1.0

    # 3. Community Hall context
    has_hall_query = any(w in q_lower for w in DOMAIN_INDICATORS["community_hall"])
    cand_is_hall = "community hall" in cand_str or "சமுதாய கூடம்" in cand_str
    if has_hall_query and cand_is_hall:
        has_adw_query = any(w in q_lower for w in ["adi dravidar", "adw", "dadw", "ஆதிதிராவிடர்", "ஆதி திராவிடர்", "social justice", "sjd"])
        if has_adw_query and any(w in cand_str for w in ["adw", "adi dravidar", "social justice", "sjd"]):
            return 1.0
        has_maws_query = any(w in q_lower for w in ["maws", "corporation", "municipality", "மாநகராட்சி", "நகராட்சி"])
        if has_maws_query and any(w in cand_str for w in ["maws", "municipal"]):
            return 1.0
        has_rdpr_query = any(w in q_lower for w in ["rdpr", "panchayat", "ஊராட்சி", "ஒன்றியம்", "village panchayat"])
        if has_rdpr_query and any(w in cand_str for w in ["rdpr", "rural development"]):
            return 1.0
        return 1.0

    # Elderly / OAP context
    has_oap_query = any(w in q_lower for w in DOMAIN_INDICATORS["old_age_pension"])
    cand_is_oap = any(w in cand_str for w in ["old age pension", "oap", "ignoaps", "social security schemes (sss)"]) and not any(w in cand_str for w in ["widow", "differently abled", "destitute", "exsmwel", "sdat", "sp"])
    if has_oap_query and cand_is_oap:
        return 1.0

    # Destitute Widow context
    has_widow_query = any(w in q_lower for w in DOMAIN_INDICATORS["widow_pension"])
    cand_is_widow = any(w in cand_str for w in ["destitute widow", "dwps", "dwp", "widow"])
    if has_widow_query and cand_is_widow:
        return 1.0

    # Disability context
    has_disability_query = any(w in q_lower for w in DOMAIN_INDICATORS["disability_pension"])
    cand_is_disability = any(w in cand_str for w in ["differently abled", "dap", "disability"])
    if has_disability_query and cand_is_disability:
        return 1.0

    # Road Maintenance context
    has_road_query = _has_road_signals(q_lower)
    cand_is_road = any(w in cand_str for w in ["road", "highway", "சாலை", "பாதை"])
    if has_road_query and cand_is_road:
        return 1.0

    # Drinking Water context
    has_water_query = any(w in q_lower for w in DOMAIN_INDICATORS["drinking_water"])
    cand_is_water = any(w in cand_str for w in ["drinking water", "water supply", "twad"])
    if has_water_query and cand_is_water:
        return 1.0

    # Street Lights context
    has_lights_query = any(w in q_lower for w in DOMAIN_INDICATORS["street_lights"])
    cand_is_lights = any(w in cand_str for w in ["street light", "street lights"])
    if has_lights_query and cand_is_lights:
        return 1.0

    # Electricity context
    has_eb_query = any(w in q_lower for w in DOMAIN_INDICATORS["electricity"])
    cand_is_eb = any(w in cand_str for w in ["energy", "electricity", "tangedco", "power"])
    if has_eb_query and cand_is_eb:
        return 1.0

    # Drainage context
    has_drain_query = any(w in q_lower for w in DOMAIN_INDICATORS["drainage"])
    cand_is_drain = any(w in cand_str for w in ["drainage", "storm water", "sewage"])
    if has_drain_query and cand_is_drain:
        return 1.0

    # Encroachment context
    has_encroach_query = any(w in q_lower for w in DOMAIN_INDICATORS["encroachment"])
    cand_is_encroach = any(w in cand_str for w in ["encroachment", "eviction"])
    if has_encroach_query and cand_is_encroach:
        return 1.0

    # Patta / Land context
    has_patta_query = any(w in q_lower for w in DOMAIN_INDICATORS["patta_land"])
    cand_is_patta = any(w in cand_str for w in ["patta", "land records", "land administration"])
    if has_patta_query and cand_is_patta:
        return 1.0

    # Ration / PDS context
    has_ration_query = any(w in q_lower for w in DOMAIN_INDICATORS["ration_pds"])
    cand_is_ration = any(w in cand_str for w in ["civil supplies", "ration", "pds", "foodco"])
    if has_ration_query and cand_is_ration:
        return 1.0

    # Agriculture / Farmer context
    has_agri_query = any(w in q_lower for w in DOMAIN_INDICATORS["agriculture"])
    cand_is_agri = any(w in cand_str for w in ["agriculture", "crop loss relief", "crop insurance", "farmer", "வேளாண்மை", "horticulture", "agricultural engineering", "agri", "paddy procurement"])
    if has_agri_query and cand_is_agri:
        return 1.0

    return 0.0


def _compute_contradiction_score(query_text: str, candidate: Dict[str, Any]) -> float:
    """
    Computes contradiction penalty where a candidate strongly clashes with petition intent.
    Returns float in [0.0, 1.0].
    """
    q_lower = query_text.lower()
    t_sub = (candidate.get("grievance_sub_type") or "").lower()
    t_type = (candidate.get("grievance_type") or "").lower()
    t_dept = (candidate.get("department") or "").lower()
    cand_str = f"{t_dept} {t_type} {t_sub}"

    # 1. Community Hall intent vs Scholarship/Pension contradiction
    has_hall_intent = any(w in q_lower for w in DOMAIN_INDICATORS["community_hall"])
    if has_hall_intent:
        if any(w in cand_str for w in ["scholarship", "old age pension", "oap", "destitute widow", "dwps", "differently abled pension"]):
            return 1.0

    # 2. Explicit Scholarship intent vs non-scholarship candidates
    has_scholarship_intent = any(w in q_lower for w in DOMAIN_INDICATORS["scholarship"])
    if has_scholarship_intent:
        if "community hall" in cand_str:
            return 1.0
        if "scholarship" not in cand_str and any(w in cand_str for w in ["ragging", "disciplinary", "grievances - technical", "anti-ragging"]):
            return 0.9

    # 3. Critical Failure Case: Education Petition vs Social Security / Pension
    # If the petition is about a student, college, degree, or educational scholarship,
    # penalize Old Age Pension, Destitute Widow Pension, and general Social Security!
    has_edu_signals = any(w in q_lower for w in DOMAIN_INDICATORS["education"])
    is_pension_cand = any(w in cand_str for w in ["old age pension", "oap", "destitute widow", "dwps", "differently abled pension", "social security schemes (sss)"])
    if has_edu_signals and is_pension_cand:
        return 1.0

    # 4. Critical Regression Case: Road Repair with water puddle vs Drinking Water
    # If the petition is about damaged roads / potholes, even if "தண்ணீர்" (water stagnation)
    # is mentioned, penalize Drinking Water candidates!
    has_road_signals = _has_road_signals(q_lower)
    is_drinking_water_cand = any(w in cand_str for w in ["drinking water", "water connection", "insufficient water supply"])
    if has_road_signals and is_drinking_water_cand:
        return 1.0

    # 5. Drinking Water Petition vs Road Maintenance
    # If petition is asking for drinking water pipe/connection and mentions no road repair:
    has_water_signals = any(w in q_lower for w in DOMAIN_INDICATORS["drinking_water"])
    is_road_cand = any(w in cand_str for w in ["road maintenance", "road repair", "highways"])
    if has_water_signals and not has_road_signals and is_road_cand:
        return 0.9

    # 6. Non-widow petition vs Destitute Widow Pension
    has_widow_signals = any(w in q_lower for w in DOMAIN_INDICATORS["widow_pension"])
    is_widow_cand = any(w in cand_str for w in ["destitute widow", "dwps", "dwp"])
    if not has_widow_signals and is_widow_cand:
        return 0.6

    # 7. Non-disability petition vs Differently Abled Pension
    has_disability_signals = any(w in q_lower for w in DOMAIN_INDICATORS["disability_pension"])
    is_disability_cand = any(w in cand_str for w in ["differently abled", "dap"])
    if not has_disability_signals and is_disability_cand:
        return 0.6

    # 8. Non-senior citizen petition vs Old Age Pension
    has_oap_signals = any(w in q_lower for w in DOMAIN_INDICATORS["old_age_pension"])
    is_oap_cand = any(w in cand_str for w in ["old age pension", "oap", "ignoaps"])
    if not has_oap_signals and is_oap_cand:
        return 0.5
    if has_oap_signals:
        if not any(w in q_lower for w in ["ராணுவம்", "படைவீரர்", "ex-servicemen", "military"]) and "exsmwel" in cand_str:
            return 0.8
        if not any(w in q_lower for w in ["விளையாட்டு", "sports"]) and "sdat" in cand_str:
            return 0.8

    # 9. Agriculture petition vs Pension
    has_agri_signals = any(w in q_lower for w in DOMAIN_INDICATORS["agriculture"])
    if has_agri_signals and is_pension_cand:
        return 1.0

    return 0.0


class SemanticPetitionClassifier:
    """
    Production-grade dynamic database-driven semantic petition classifier.
    Leverages in-memory vector cosine similarity against all 1,847 DB taxonomy mappings
    and multi-signal heuristic ranking.
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
        Builds weighted query text for embedding representation.
        Order of priority: Subject line (4x) + Prayer (2.5x) + Body Context (0.5x).
        """
        subject_line = _extract_subject_line(zone_b_body)
        prayer = _extract_prayer_section(full_doc_text or zone_b_body)

        # Cross-lingual concept expansion: bridges Tamil intent to English DB search_text
        body_snippet = (zone_b_body or full_doc_text or "")[:400].strip()
        combined_lower = f"{subject_line} {prayer} {body_snippet}".lower()
        expanded_concepts = []
        if _has_road_signals(combined_lower):
            expanded_concepts.append("road highways road repair laying new roads village road infrastructure street")

        concept_terms_map = {
            ("குடிநீர்", "தண்ணீர் குழாய்", "மேல்நிலைத் தொட்டி"): "drinking water water supply water connection TWAD CMA",
            # Explicit scholarship intent only:
            ("கல்வி உதவித்தொகை", "கல்வி உதவித் தொகை", "கல்வி உதவி தொகை", "உதவித்தொகை", "உதவித் தொகை", "உதவி தொகை", "scholarship", "scholarship amount", "scholarship application", "post matric scholarship", "pre matric scholarship", "கல்விக்கட்டண சலுகை", "கல்வி உதவி"): "scholarship student financial aid post matric pre matric higher education scholarship",
            # General higher education / college without scholarship:
            ("கல்லூரி", "பல்கலைக்கழகம்", "collegiate", "university"): "higher education collegiate university",
            # General school education without scholarship:
            ("பள்ளிக்கூடம்", "பள்ளி கல்வி", "school education"): "school education department",
            # General students without scholarship:
            ("மாணவர்", "மாணவி", "மாணவர்கள்", "மாணவிகள்", "student", "students"): "students youth",
            # Community Hall / Civic Infrastructure:
            ("சமுதாய கூடம்", "சமூக கூடம்", "சமுதாயக்கூடம்", "சமுதாய பவன்", "community hall", "திருமண மண்டபம்", "சமுதாய நலக்கூடம்"): "community hall civic infrastructure hall",
            # Adi Dravidar Welfare / ADW:
            ("ஆதிதிராவிடர்", "ஆதி திராவிடர்", "ஆதிதிராவிடர் நலத்துறை", "ஆதி திராவிடர் நலத்துறை", "adw", "dadw", "adi dravidar"): "adi dravidar welfare ADW social justice",
            ("தொழில்நுட்ப", "பாலிடெக்னிக்", "பொறியியல்", "polytechnic", "engineering"): "technical education diploma engineering",
            ("முதியோர்", "வயது மூப்பு", "முதியவர்", "ஓய்வூதியம்"): "(IGNOAPS) Commissioner of Revenue Administration Tahsildar SSS Revenue and Disaster Management REV Pension old age pension OAP",
            ("விதவை", "ஆதரவற்ற விதவை"): "destitute widow pension scheme DWPS DWP",
            ("மாற்றுத்திறனாளி", "ஊனம்"): "differently abled pension DAP disability assistance",
            ("மின்சாரம்", "மின் இணைப்பு", "மின்மாற்றி"): "electricity supply tangedco energy power low voltage",
            ("பட்டா", "சிட்டா", "அடங்கல்", "உட்பிரிவு"): "patta transfer land records natham patta land administration survey",
            ("ஆக்கிரமிப்பு", "பொதுப்பாதை"): "land encroachment eviction pathway government land",
            ("வடிகால்", "கழிவுநீர்", "சாக்கடை"): "drainage storm water drain sewage desilting culverts",
            ("தெருவிளக்கு", "மின்விளக்கு"): "street lights lighting",
            ("ரேஷன்", "குடும்ப அட்டை"): "civil supplies ration card smart card PDS rice distribution",
            ("வாரிசு", "இறப்பு சான்று"): "legal heir certificate revenue administration",
            ("சாதி சான்றிதழ்", "சாதி சான்று"): "community certificate social justice revenue",
            ("விவசாய", "விவசாயி", "பயிர்", "நெற்பயிர்", "வேளாண்மை", "உழவர்", "பயிர் சேதம்"): "agriculture and farmers welfares department AGRI crop loss relief crop damage paddy relief farmer horticulture agriculture schemes"
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

    def get_top_candidates(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
        top_k: int = DEFAULT_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves and ranks the top-K database taxonomy candidates for LLM prompt context.
        """
        res = self.classify(
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            full_doc_text=full_doc_text,
            top_k=top_k
        )
        return res.get("candidates") or []

    def classify(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        """
        Dynamically classifies a petition against the 1,847 database taxonomy rows.
        
        Returns:
            {
                "taxonomy_id": int,
                "label": str,
                "department": str,
                "grievance_type": str,
                "grievance_subtype": str,
                "sub_department": str,
                "responsible_officer": str,
                "confidence": float,
                "confidence_gap": float,
                "margin": float,
                "is_ambiguous": bool,
                "method": "db_taxonomy_vector",
                "subject_line": str,
                "candidates": list,
                "scores": dict,
            }
        """
        from services.taxonomy_matcher import taxonomy_matcher

        query_text, subject_line, prayer = self.build_query_representation(
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            full_doc_text=full_doc_text
        )

        vs = self._get_vector_store()
        query_embs = vs.encode([query_text])
        if not query_embs:
            logger.warning("Failed to generate query embedding for petition.")
            return self._empty_result(subject_line)

        query_vec = query_embs[0]

        # Vector search against all 1,847 DB taxonomy embeddings
        raw_candidates = taxonomy_matcher.search_candidates_by_vector(query_vec, top_k=top_k)
        if not raw_candidates:
            logger.warning("No candidates returned from taxonomy vector search.")
            return self._empty_result(subject_line)

        # Multi-signal scoring for each candidate
        scored_candidates = []
        for cand in raw_candidates:
            semantic_score = max(0.0, min(1.0, cand.get("semantic_score", 0.0)))
            fuzzy_score = _compute_fuzzy_score(f"{subject_line} {prayer} {query_text}", cand)
            context_score = _compute_context_score(f"{subject_line} {prayer} {query_text}", cand)
            contradiction_score = _compute_contradiction_score(f"{subject_line} {prayer} {query_text}", cand)

            final_score = (
                SEMANTIC_WEIGHT * semantic_score
                + FUZZY_WEIGHT * fuzzy_score
                + CONTEXT_WEIGHT * context_score
                - CONTRADICTION_WEIGHT * contradiction_score
            )
            final_score = max(0.0, min(1.0, round(final_score, 4)))

            scored_item = {
                "Taxonomy_ID": cand.get("taxonomy_id"),
                "taxonomy_id": cand.get("taxonomy_id"),
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
                "semantic_score": semantic_score,
                "fuzzy_score": fuzzy_score,
                "context_score": context_score,
                "contradiction_score": contradiction_score,
                "final_score": final_score,
            }
            scored_candidates.append(scored_item)

        # Sort descending by multi-signal final score
        scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)

        best = scored_candidates[0]
        second = scored_candidates[1] if len(scored_candidates) > 1 else None

        best_score = best["final_score"]
        second_score = second["final_score"] if second else 0.0
        margin = round(best_score - second_score, 4)
        is_ambiguous = margin < RERANK_MARGIN_THRESHOLD

        top3_log = ", ".join(
            f"ID {c['taxonomy_id']} ({c['department']} - {c['grievance_sub_type']}): score={c['final_score']} (sem={c['semantic_score']}, fuz={c['fuzzy_score']}, ctx={c['context_score']}, con={c['contradiction_score']})"
            for c in scored_candidates[:3]
        )
        logger.info(
            f"🎯 Dynamic DB Taxonomy Classification: ID={best['taxonomy_id']} | "
            f"Dept='{best['department']}' | SubType='{best['grievance_sub_type']}' | "
            f"score={best_score:.4f} (margin={margin:.4f}, ambiguous={is_ambiguous}) | Top3: {top3_log}"
        )

        label = f"{best['grievance_type']} / {best['grievance_sub_type']}"
        scores_map = {str(c["taxonomy_id"]): c["final_score"] for c in scored_candidates[:5]}

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
            "method": "db_taxonomy_vector",
            "subject_line": subject_line,
            "candidates": scored_candidates,
            "scores": scores_map,
            "classification_status": "resolved" if not is_ambiguous else "ambiguous",
        }

    async def classify_with_rerank(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
        top_k: int = DEFAULT_TOP_K,
        llm_client: Any = None
    ) -> Dict[str, Any]:
        """
        Classifies petition using dynamic DB vector retrieval and multi-signal ranking.
        If decisive (margin >= RERANK_MARGIN_THRESHOLD), returns immediately without LLM delay.
        If ambiguous (margin < RERANK_MARGIN_THRESHOLD) and LLM is provided, passes Top-3 candidates
        to the LLM for focused candidate validation.
        If still ambiguous or LLM cannot resolve, returns safe state:
        {"classification_status": "ambiguous", "taxonomy_id": None}.
        """
        from services.taxonomy_matcher import taxonomy_matcher
        import asyncio

        res = self.classify(
            zone_a_header=zone_a_header,
            zone_b_body=zone_b_body,
            full_doc_text=full_doc_text,
            top_k=top_k
        )

        # Clear case: No extra LLM reranking required
        if not res.get("is_ambiguous") or llm_client is None:
            res["classification_status"] = "resolved" if res.get("taxonomy_id") else "ambiguous"
            return res

        candidates = res.get("candidates") or []
        if len(candidates) < 2:
            res["classification_status"] = "resolved" if res.get("taxonomy_id") else "ambiguous"
            return res

        # Ambiguous case: Top 3 candidates validated with LLM
        top3 = candidates[:3]
        valid_ids = [c["taxonomy_id"] for c in top3 if c.get("taxonomy_id") is not None]
        candidates_text = "\n".join([
            f"Candidate {idx}: ID={c['taxonomy_id']}, Department=\"{c['department']}\", Grievance Type=\"{c['grievance_type']}\", Sub-Type=\"{c['grievance_sub_type']}\""
            for idx, c in enumerate(top3, 1)
        ])

        petition_snippet = (zone_b_body or full_doc_text or "")[:800].strip()
        rerank_prompt = (
            f"You are an administrative classifier for Tamil Nadu government petitions.\n"
            f"The petition text is:\n{petition_snippet}\n\n"
            f"Here are the top candidate categories from the official taxonomy:\n{candidates_text}\n\n"
            f"Task: Select the single candidate ID that best represents the primary purpose of the petition.\n"
            f"You MUST select ONLY one of the supplied candidate IDs ({valid_ids}).\n"
            f"Do not invent new departments or types. If none match or the petition is genuinely ambiguous, return null.\n\n"
            f"Respond in JSON format:\n"
            f'{{"selected_candidate_id": <int or null>, "confidence": <float 0.0-1.0>, "reason": "<short explanation>"}}'
        )

        try:
            logger.info(f"⚖️ Ambiguity detected (margin={res.get('margin', 0):.4f} < {RERANK_MARGIN_THRESHOLD}). Invoking LLM candidate validation...")
            raw_response = await asyncio.wait_for(
                llm_client.achat(
                    rerank_prompt,
                    system_prompt="You are a strict administrative petition classifier. Output only valid JSON.",
                    temperature=0.1,
                    max_tokens=150,
                    json_mode=True,
                    timeout=15.0
                ),
                timeout=16.0
            )
            parsed = None
            if raw_response:
                from core.llm_client import extract_json_object
                parsed = extract_json_object(raw_response)

            sel_id = parsed.get("selected_candidate_id") if parsed else None
            confidence = float(parsed.get("confidence", 0.0)) if parsed else 0.0

            # Validate that LLM selected an ID from the supplied candidate list
            if sel_id is not None and int(sel_id) in valid_ids and confidence >= 0.40:
                selected_tax = taxonomy_matcher.get_taxonomy_by_id(int(sel_id))
                if selected_tax:
                    logger.info(f"✅ LLM validation resolved ambiguous case: ID {sel_id} ('{selected_tax['department']}' - '{selected_tax['grievance_sub_type']}')")
                    res["taxonomy_id"] = selected_tax["id"]
                    res["category_key"] = f"tax_{selected_tax['id']}"
                    res["label"] = f"{selected_tax['grievance_type']} / {selected_tax['grievance_sub_type']}"
                    res["department"] = selected_tax["department"]
                    res["department_code"] = selected_tax.get("department_code", "")
                    res["grievance_type"] = selected_tax["grievance_type"]
                    res["grievance_subtype"] = selected_tax["grievance_sub_type"]
                    res["sub_department"] = selected_tax.get("sub_department", "")
                    res["responsible_officer"] = selected_tax.get("responsible_officer", "")
                    res["confidence"] = confidence
                    res["classification_status"] = "resolved"
                    res["method"] = "llm_reranked_vector"
                    return res
        except Exception as ex:
            logger.warning(f"LLM candidate validation exception: {ex}")

        # Safe fallback for unresolved ambiguous cases: DO NOT force an arbitrary category
        logger.warning(f"⚠️ Ambiguous classification could not be decisively resolved. Setting classification_status='ambiguous'.")
        res["classification_status"] = "ambiguous"
        res["taxonomy_id"] = None
        res["department"] = "General Administration"
        res["department_code"] = "GAD"
        res["grievance_type"] = "General Grievance"
        res["grievance_subtype"] = "Pending Classification / Manual Review"
        res["sub_department"] = "General Administration / பொது நிர்வாகம்"
        res["responsible_officer"] = "துறை அலுவலர்"
        return res

    def _empty_result(self, subject_line: str = "") -> Dict[str, Any]:
        return {
            "taxonomy_id": None,
            "category_key": None,
            "label": None,
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
            "method": "fallback",
            "subject_line": subject_line,
            "candidates": [],
            "scores": {},
        }


# Module-level singleton
semantic_classifier = SemanticPetitionClassifier()
