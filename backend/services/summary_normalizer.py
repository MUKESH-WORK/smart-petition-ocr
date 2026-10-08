"""
Summary Normalizer & Grounding Validator: Generates and normalizes concise,
factual, official administrative Tamil grievance descriptions (Field 10)
grounded strictly in verified facts without conversational artifacts or hallucinations.
"""

import re
from typing import Dict, Any, Optional, List


def build_factual_administrative_summary(facts: Dict[str, Any]) -> str:
    """
    Constructs a concise, factual, official administrative Tamil summary
    grounded exclusively in verified facts when LLM output is missing or fails grounding validation.
    Works generally across all departments and grievance categories dynamically without
    hard-coded category-specific if/elif branching.
    """
    raw_name = facts.get("petitioner_name") or "மனுதாரர்"
    # Clean redundant prefixes
    p_name = re.sub(r'^(?:மனுதாரர்\s+)+', '', str(raw_name)).strip() or "மனுதாரர்"

    district = facts.get("district")
    taluk = facts.get("taluk")
    village = facts.get("village")
    street = facts.get("street_name") or facts.get("street")
    action_or_subject = (
        facts.get("requested_action")
        or facts.get("grievance_subject")
        or facts.get("grievance_subtype")
        or facts.get("grievance_type")
        or "குறைதீர்ப்பு"
    )

    # Assemble administrative location hierarchy
    loc_parts = []
    if district:
        loc_parts.append(f"{district} மாவட்டம்")
    if taluk and taluk != district:
        loc_parts.append(f"{taluk} வட்டம்")
    if village and village != taluk and village != district:
        loc_parts.append(f"{village}")
    if street:
        st_clean = street.strip()
        # Clean redundant village or district repetitions from street
        if village:
            st_clean = re.sub(rf'\b{re.escape(village)}\b', '', st_clean).strip(" ,-")
        if district:
            st_clean = re.sub(rf'\b{re.escape(district)}\b', '', st_clean).strip(" ,-")
        if st_clean and st_clean != village and st_clean != district:
            loc_parts.append(st_clean)

    loc_str = " ".join(loc_parts).strip()
    if loc_str:
        loc_str = f"{loc_str} பகுதியில் "
    else:
        loc_str = ""

    # Clean action/subject if it contains raw headers or suffixes
    action_clean = re.sub(r'^(?:பொருள்\s*[:\.\-]?|மனு\s*[:\.\-]?)\s*', '', str(action_or_subject)).strip()
    action_clean = re.sub(r'\s*-\s*தொடர்பாக\.?$', '', action_clean).strip()

    # Formulate natural administrative sentence
    infinitive_request_endings = (
        "வழங்க", "வழங்கிட", "அமைக்க", "அமைத்திட", "சீரமைக்க", "சீரமைத்திட",
        "பழுதுபார்க்க", "நீக்க", "செய்திட", "தீர்வு காண", "நடவடிக்கை எடுக்க"
    )

    if action_clean.endswith("கோரிக்கை"):
        summary = f"மனுதாரர் {p_name}, {loc_str}{action_clean} தொடர்பாக உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
    elif any(action_clean.endswith(end) for end in infinitive_request_endings):
        summary = f"மனுதாரர் {p_name}, {loc_str}{action_clean} உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
    else:
        summary = f"மனுதாரர் {p_name}, {loc_str}{action_clean} தொடர்பாக உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."

    # Collapse any double spaces
    summary = re.sub(r'\s+', ' ', summary).strip()
    return summary


def normalize_administrative_tamil_summary(summary_ta: str, facts: Optional[Dict[str, Any]] = None) -> str:
    """
    Safely normalizes generated Tamil summary into official administrative Tamil (அலுவலக நடை).
    Removes awkward conversational generation artifacts (e.g., 'செய்து கூறியவர்')
    without deleting legitimate administrative phrasing or distorting substantive meaning.
    """
    if not summary_ta or not isinstance(summary_ta, str):
        return build_factual_administrative_summary(facts or {})

    s = summary_ta.strip()

    # Normalize unicode encoding issues (e.g., Hindi EE -> Tamil EE)
    s = s.replace("\u0908", "\u0B88").replace("ஈ. ரோடு", "ஈரோடு")

    # 1. Clean first-person informal narrative beginnings and ensure standard petitioner header
    p_name = None
    if facts and facts.get("petitioner_name"):
        p_name = re.sub(r'^(?:மனுதாரர்\s+)+', '', str(facts["petitioner_name"])).strip()
    p_name = p_name or "மனுதாரர்"

    # Strip conversational self-introductions e.g. "நான், P. லோகேஷ், வீரபாண்டி பகுதியைச் சேர்ந்த பொதுமகன்."
    s = re.sub(r'^(?:நான்|நாங்கள்)[,\s]+(?:[A-Za-z0-9\u0B80-\u0BFF\.\s]+(?:சேர்ந்த\s+பொதுமகன்|வசிக்கும்\s+பொதுமகன்|வசிப்பவர்|சேர்ந்தவர்|பொதுமகன்)[,\.]*\s*)', '', s)
    s = re.sub(r'^(?:நான்|நாங்கள்)\s+(?:மேலே\s+குறிப்பிட்ட\s+முகவரியில்\s+வசிக்கும்\s+[^.]+\.\s*)?', '', s)
    s = re.sub(r'^(?:நான்|நாங்கள்)[,\s]+', '', s)
    s = s.replace("எங்கள் பகுதியில்", "அப்பகுதியில்").replace("எங்கள் ஊரில்", "அவ்வூரில்").replace("எங்கள் தெருவில்", "அத்தெருவில்")
    s = s.replace("கோருகிறேன்", "கோரிக்கை விடுத்துள்ளார்").replace("கோருகிறோம்", "கோரிக்கை விடுத்துள்ளனர்")

    if not s.startswith("மனுதாரர்"):
        s = f"மனுதாரர் {p_name}, {s}"
    s = re.sub(r'^மனுதாரர்\s+மனுதாரர்\b', 'மனுதாரர்', s)

    # 2. Repair awkward conversational participle suffixes from LLM / OCR parsing
    s = re.sub(r'தீரும்மாறு\s+கோரிக்கை\s+செய்து\s+கூறியவர்[,\s]*', '', s)
    s = re.sub(r'கோரிக்கை\s+செய்து\s+கூறியவர்[,\s]*', 'கோரிக்கை விடுத்துள்ளார். ', s)
    s = re.sub(r'வசதி\s+ஏற்படுத்துவதாக\s+கூறியவர்[.\s]*', 'வசதி அமைத்துத் தருமாறு கோரிக்கை விடுத்துள்ளார்.', s)
    s = re.sub(r'ஏற்படுத்துவதாக\s+கூறியவர்[.\s]*', 'ஏற்படுத்தித் தருமாறு கோரிக்கை விடுத்துள்ளார்.', s)
    s = re.sub(r'(?:செய்து\s+)?தருவதாக\s+கூறியவர்[.\s]*', 'தருமாறு கோரிக்கை விடுத்துள்ளார்.', s)
    s = re.sub(r'செய்ததாக\s+கூறியவர்[.\s]*', 'செய்துள்ளார்.', s)
    s = re.sub(r'என்று\s+கூறியவர்[.\s]*', 'என்று தெரிவித்துள்ளார்.', s)
    s = re.sub(r'வழங்குவதாக\s+கூறியவர்[.\s]*', 'வழங்கிடக் கோரிக்கை விடுத்துள்ளார்.', s)
    s = re.sub(r'அமைப்பதாக\s+கூறியவர்[.\s]*', 'அமைத்துத் தருமாறு கோரிக்கை விடுத்துள்ளார்.', s)

    # Ensure comma after petitioner name e.g. "மனுதாரர் மு. கார்த்திக், "
    s = re.sub(r'^(மனுதாரர்\s+[^\s,]+(?:\s+[^\s,]+)?)\s*,?\s*', r'\1, ', s)

    # Isolated trailing conversational participle (preserve legitimate கூறியுள்ளார்கள் / தெரிவித்துள்ளார்)
    s = re.sub(r'\s+கூறியவர்[.\s]*$', ' நடவடிக்கை கோரியுள்ளார்.', s)
    s = re.sub(r'\s+தெரிவித்தவர்[.\s]*$', ' தெரிவித்துள்ளார்.', s)

    # 3. Standardize humble / passive verbs into formal active administrative verbs
    s = s.replace("தங்களிடம் தாழ்மையுடன் கேட்டுக்கொள்கிறேன்", "கோரிக்கை விடுத்துள்ளார்")
    s = s.replace("தாழ்மையுடன் கேட்டுக்கொள்கிறேன்", "கோரிக்கை விடுத்துள்ளார்")
    s = s.replace("கேட்டுக்கொள்கிறேன்", "கோரிக்கை விடுத்துள்ளார்")
    s = s.replace("கேட்டுக் கொள்கிறேன்", "கோரிக்கை விடுத்துள்ளார்")
    s = s.replace("வசித்து வருகிறேன்", "வசித்து வரும் நிலையில்")
    s = s.replace("வசித்து வருகின்றேன்", "வசித்து வரும் நிலையில்")
    s = s.replace("வசித்து வருகிறோம்", "வசித்து வரும் நிலையில்")

    # 4. Standardize repeated phrases
    s = re.sub(r'(?:(?:தேவையான|உரிய)\s+நடவடிக்கை\s+எடுக்குமாறு\s+)+(?:உரிய\s+)?', 'உரிய நடவடிக்கை எடுக்குமாறு ', s)
    s = re.sub(r'([A-Za-z\u0B80-\u0BFF]{2,}(?:\s+[A-Za-z\u0B80-\u0BFF]{2,})?)\s+\1\b', r'\1', s)

    # 5. Ensure valid sentence ending
    s = s.strip(' ,-:')
    valid_endings = (
        ".", "!", "?",
        "கோரிக்கை விடுத்துள்ளார்.",
        "நடவடிக்கை கோரியுள்ளார்.",
        "மனு அளித்துள்ளார்.",
        "தெரிவித்துள்ளார்.",
        "விண்ணப்பித்துள்ளார்."
    )
    if not any(s.endswith(end) for end in valid_endings):
        if s.endswith("கோரிக்கை விடுத்துள்ளார்") or s.endswith("நடவடிக்கை கோரியுள்ளார்") or s.endswith("மனு அளித்துள்ளார்"):
            s += "."
        elif s.endswith(" என") or s.endswith(" என்று") or s.endswith(" ஆக"):
            s = s.rsplit(' ', 1)[0] + " உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
        else:
            s += " நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."

    # Collapse any multi-spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def validate_summary_grounding(
    summary_ta: str,
    facts: Dict[str, Any],
    doc_context: str
) -> bool:
    """
    Rigorously validates that the generated summary is grounded strictly in verified facts
    and document context. Detects unsupported:
    - Person names (hallucinated petitioner names)
    - Locations (unverified districts, taluks, villages, streets)
    - Administrative departments not present in facts or document
    - Dates / Years not present in facts or document
    - Unverified numerical claims or beneficiary group figures
    - Prohibited conversational generation artifacts
    """
    if not summary_ta or len(summary_ta) < 35:
        return False

    # Must contain administrative intent or requested action
    core_grievance_terms = ["கோரிக்கை", "நடவடிக்கை", "மனு", "சீரமைக்க", "வழங்க", "அமைக்க", "பழுது", "நீக்க", "ஆக்கிரமிப்பு", "உதவித்தொகை"]
    if not any(term in summary_ta for term in core_grievance_terms):
        return False

    # Detect truncated single-word verb fragments before நடவடிக்கை e.g. "பவா நடவடிக்கை"
    if re.search(r'[,\s][\u0B80-\u0BFF]{1,3}\s+நடவடிக்கை', summary_ta):
        return False

    norm_corpus = (doc_context or "") + " " + " ".join(str(v) for v in facts.values() if v)
    norm_corpus = norm_corpus.replace("\u0908", "\u0B88").lower()

    # 1. Reject if known OCR junk tokens are present
    OCR_JUNK_TOKENS = ["பிளூப்ரீவ்", "ப்ளூப்ரிண்ட்", "வட்டாராசிரியர்", "தோட்டாரன்", "ஷாவ்", "ரயல்"]
    if any(junk in summary_ta for junk in OCR_JUNK_TOKENS):
        return False

    # 2. Check for prohibited raw conversational/LLM artifacts
    PROHIBITED_ARTIFACTS = [
        "செய்து கூறியவர்", "ஏற்படுத்துவதாக கூறியவர்", "செய்ததாக கூறியவர்",
        "தாழ்மையுடன் கேட்டுக்கொள்கிறேன்", "வசித்து வருகிறேன்"
    ]
    if any(art in summary_ta for art in PROHIBITED_ARTIFACTS):
        return False

    # 3. Petitioner Name Grounding
    # If summary specifies a petitioner name, it must be grounded in facts or context
    name_match = re.search(r'மனுதாரர்\s+([^\s,]+(?:\s+[^\s,]+)?)\s*,', summary_ta)
    if name_match:
        cand_name = name_match.group(1).strip()
        # Strip honorifics
        cand_name_clean = re.sub(r'^(?:திரு|திருமதி|செல்வி)\.?\s*', '', cand_name).lower()
        if cand_name_clean and cand_name_clean != "மனுதாரர்":
            # Check if candidate name is in petitioner_name or norm_corpus
            fact_p_name = str(facts.get("petitioner_name") or "").lower()
            name_tokens = [tok for tok in re.split(r'[\s\.]+', cand_name_clean) if len(tok) >= 2]
            if name_tokens:
                name_grounded = any(tok in fact_p_name or tok in norm_corpus for tok in name_tokens)
                if not name_grounded:
                    # Hallucinated person name detected
                    return False

    # 4. Location Grounding
    # Check candidate Tamil proper nouns or locations from summary
    places_in_summary = re.findall(
        r'([A-Za-z\u0B80-\u0BFF]{3,})\s+(?:மாவட்டம்|வட்டம்|நகர்|தெரு|வீதி|கிராமம்|ஊராட்சி|பேரூராட்சி)',
        summary_ta
    )
    for place in places_in_summary:
        if place.lower() not in norm_corpus:
            # Unverified place hallucination detected
            return False

    # 5. Department Grounding
    # Check if summary explicitly mentions an administrative department in Tamil that is unsupported
    TAMIL_DEPARTMENT_KEYWORDS = {
        "காவல்துறை": ["police", "காவல்", "home"],
        "மின்சார வாரியம்": ["tneb", "electricity", "மின்சாரம்", "மின்"],
        "தீயணைப்புத்துறை": ["fire", "தீயணைப்பு"],
        "நெடுஞ்சாலைத்துறை": ["highway", "நெடுஞ்சாலை", "highways"],
        "வனத்துறை": ["forest", "வனம்"],
        "போக்குவரத்துத்துறை": ["transport", "போக்குவரத்து"],
        "மருத்துவத்துறை": ["health", "மருத்துவம்", "medical"]
    }
    for dept_kw, valid_patterns in TAMIL_DEPARTMENT_KEYWORDS.items():
        if dept_kw in summary_ta:
            dept_grounded = any(
                pat in norm_corpus
                for pat in valid_patterns + [dept_kw]
            )
            if not dept_grounded:
                # Unsupported administrative department hallucinated
                return False

    # 6. Dates and Years Grounding
    # Any 4-digit year or formatted date in summary must be present in facts or document context
    years_in_summary = re.findall(r'\b(19\d\d|20\d\d)\b', summary_ta)
    for yr in years_in_summary:
        if yr not in norm_corpus:
            # Hallucinated year detected
            return False

    dates_in_summary = re.findall(r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b', summary_ta)
    for dt in dates_in_summary:
        if dt not in norm_corpus:
            # Hallucinated date detected
            return False

    # 7. Unsupported Quantitative Claims
    # Check for specific quantities like "1000 குடும்பங்கள்", "500 பேர்"
    quantities = re.findall(r'\b(\d+)\s*(?:குடும்பங்கள்|பேர்|நபர்கள்|மாணவர்கள்|கிராமங்கள்|வீடுகள்)\b', summary_ta)
    for q in quantities:
        if q not in norm_corpus:
            return False

    # 8. Authoritative Taxonomy & Domain Consistency Grounding
    # The summary MUST NOT claim an unrelated grievance domain that contradicts the verified taxonomy
    g_type = str(facts.get("grievance_type") or "").lower()
    g_sub = str(facts.get("grievance_subtype") or "").lower()
    dept = str(facts.get("department") or "").lower()
    verified_tax_str = f"{dept} {g_type} {g_sub}"

    s_lower = summary_ta.lower()

    # If verified taxonomy is NOT Pension, reject pension claims in summary
    is_pension_tax = any(w in verified_tax_str for w in ["pension", "sss", "oap", "dwp", "முதியோர்", "விதவை"])
    if not is_pension_tax and any(w in s_lower for w in ["old age pension", "முதியோர் உதவித்தொகை", "விதவை உதவித்தொகை", "ஓய்வூதியம் வழங்கிட", "பென்ஷன் வழங்கிட"]):
        return False

    # If verified taxonomy is NOT Drinking Water, reject drinking water claims in summary
    is_water_tax = any(w in verified_tax_str for w in ["drinking water", "water connection", "water supply", "குடிநீர்"])
    if not is_water_tax and any(w in s_lower for w in ["குடிநீர் விநியோகம்", "குடிநீர் இணைப்பு", "முறையான குடிநீர்"]):
        return False

    # If verified taxonomy is NOT Certificate Verification, reject certificate verification claims in summary
    is_cert_tax = any(w in verified_tax_str for w in ["genuiness", "genuineness", "community certificate", "சரிபார்ப்பு"])
    if not is_cert_tax and any(w in s_lower for w in ["genuiness", "genuineness verification", "st community genuiness", "சரிபார்ப்பு தொடர்பாக"]):
        return False

    # If verified taxonomy is NOT Scholarship, reject scholarship claims in summary
    is_scholarship_tax = any(w in verified_tax_str for w in ["scholarship", "கல்வி உதவி"])
    if not is_scholarship_tax and any(w in s_lower for w in ["முதலமைச்சரின் கல்வி உதவித்தொகை", "கல்வி உதவித்தொகை (scholarship) திட்டத்தின் கீழ்"]):
        return False

    return True
