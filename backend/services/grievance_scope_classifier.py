"""
Grievance Scope Classifier: Determines whether a petition is 'Public' (Community)
or 'Individual' (Personal benefit) based on multiple signals:
1. Authoritative taxonomy metadata (from cm_taxonomy_mappings / PostgreSQL)
2. Collective vs. Individual beneficiary markers in petition text
3. Scope of requested administrative action
4. Preserves 'Unknown' / 'Manual Review' for ambiguous or balanced mixed cases
"""

import re
from typing import Dict, Any, Optional

# Administrative public infrastructure / community domain patterns in taxonomy
PUBLIC_TAXONOMY_PATTERNS = [
    r"road", r"bridge", r"drainage", r"storm water", r"street light",
    r"drinking water", r"water supply", r"sanitation", r"sewage",
    r"village infrastructure", r"civic amenities", r"solid waste",
    r"encroachment", r"burial ground", r"pathway to burial ground", r"pathway",
    r"community hall", r"public park", r"public toilet", r"bus service",
    r"transport", r"lake", r"pond", r"channel", r"river", r"culvert",
    r"waterbody", r"library", r"salai", r"panchayat raj", r"local body",
    r"ration shop", r"school", r"infrastructure", r"building maintenance",
    r"repairs to.*building", r"veterinary", r"animal husbandry", r"hospital",
    r"மருத்துவமனை", r"கால்நடை", r"மயானம்", r"சுடுகாடு", r"புதைகுழி",
    r"நீர்வழிப்பாதை", r"நீர்வழிப் பாதை", r"ஆக்கிரமிப்பு", r"பாதை"
]

# Personal welfare entitlement patterns in taxonomy
INDIVIDUAL_TAXONOMY_PATTERNS = [
    r"pension", r"oap", r"widow", r"destitute", r"differently abled",
    r"scholarship", r"patta transfer", r"sub-division", r"patta copy",
    r"name transfer", r"financial assistance", r"medical assistance",
    r"marriage assistance", r"house site patta", r"free patta",
    r"individual household", r"ihhl", r"compensation", r"land acquisition",
    r"chief minister.*relief", r"cmrf", r"welfare board", r"educational loan",
    r"personal", r"individual"
]

# Collective / Community beneficiary markers in Tamil
PUBLIC_BENEFICIARY_MARKERS = [
    r"பொதுமக்கள்", r"கிராம மக்கள்", r"ஊர் மக்கள்", r"பகுதி மக்கள்",
    r"குடியிருப்பாளர்கள்", r"பள்ளி மாணவர்கள்", r"மாணவ மாணவியர்",
    r"மாணவ", r"மாணவர்", r"மாணவியர்", r"பாதசாரிகள்", r"வாகன ஓட்டிகள்",
    r"தெரு மக்கள்", r"விவசாயிகள்", r"எங்கள் பகுதி", r"எங்கள் தெரு",
    r"எங்கள் கிராமம்", r"இப்பகுதி", r"பொது சாலை", r"பொது வழி",
    r"பொது பயன்பாட்டு", r"பொது பாதை", r"பொது மயானம்", r"பொது கழிப்பிடம்",
    r"பொது விநியோக", r"சமூக", r"பொதுமக்கள் பயன்பாடு", r"பொதுப்பயன்பாடு",
    r"பொதுமக்கள் சிரமம்", r"பொதுமகன்", r"பொது மக்கள்"
]

# Individual / Personal welfare markers in Tamil
INDIVIDUAL_BENEFICIARY_MARKERS = [
    r"எனக்கு\b", r"எனது\b", r"என் குடும்ப", r"எனது குடும்ப",
    r"என் வாழ்வாதாரத்திற்கு", r"எனக்கு உதவித்தொகை", r"முதியோர் உதவித்தொகை",
    r"விதவை உதவித்தொகை", r"கல்வி உதவித்தொகை", r"நான் ஒரு ஏழை",
    r"எனது தந்தை", r"எனது கணவர்", r"எனது நிலம்", r"எனது பட்டா",
    r"பட்டா மாறுதல்", r"உரிமை மாற்றம்", r"தனிநபர்", r"என் பெயரில்"
]

# Administrative action markers in Tamil
PUBLIC_ACTION_MARKERS = [
    r"சீரமை", r"அமைக்க", r"பழுது", r"கட்ட\b", r"கட்டி", r"வடிகால்",
    r"விளக்கு", r"சாலை", r"தூர்வார", r"போக்குவரத்து", r"வகுப்பறை"
]

INDIVIDUAL_ACTION_MARKERS = [
    r"வழங்க\b", r"உதவித்தொகை", r"பட்டா வழங்க", r"பெயர் மாற்றம்",
    r"நிதி உதவி", r"முதியோர்", r"விதவை", r"ஓய்வூதியம்", r"வாரிசு"
]


def deduce_taxonomy_scope(
    department: str = "",
    grievance_type: str = "",
    grievance_subtype: str = ""
) -> str:
    """
    Fallback inference for scope_type ('PUBLIC', 'INDIVIDUAL', 'MIXED', 'UNKNOWN')
    derived dynamically from taxonomy strings when explicit database scope_type is missing or UNKNOWN.
    """
    tax_str = f"{department} {grievance_type} {grievance_subtype}".lower()

    is_pub = any(re.search(pat, tax_str, re.IGNORECASE) for pat in PUBLIC_TAXONOMY_PATTERNS)
    is_ind = any(re.search(pat, tax_str, re.IGNORECASE) for pat in INDIVIDUAL_TAXONOMY_PATTERNS)

    if is_pub and not is_ind:
        return "PUBLIC"
    if is_ind and not is_pub:
        return "INDIVIDUAL"
    if is_pub and is_ind:
        return "MIXED"
    return "UNKNOWN"


def classify_grievance_scope(
    doc_context: str,
    taxonomy_meta: Optional[Dict[str, Any]] = None,
    extracted_facts: Optional[Dict[str, Any]] = None,
    llm_scope_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Multi-signal classifier for Field 9 (Community vs Individual).
    Authoritative hierarchy:
      1. Explicit database scope_type from cm_taxonomy_mappings (PUBLIC, INDIVIDUAL, MIXED)
      2. If missing or UNKNOWN, fallback to deduce_taxonomy_scope()
      3. Beneficiary scope markers from petition text
      4. Requested action scope markers
      5. Strict ambiguity handling: balanced mixed evidence returns 'Unknown' (Manual Review).

    Returns:
    {
        "classification": "Public" | "Individual" | "Unknown",
        "scope_type": "PUBLIC" | "INDIVIDUAL" | "MIXED" | "UNKNOWN",
        "public_score": float,
        "individual_score": float,
        "reason": str
    }
    """
    taxonomy_meta = taxonomy_meta or {}
    extracted_facts = extracted_facts or {}
    text = (doc_context or "") + " " + str(extracted_facts.get("grievance_subject") or "")

    dept = str(taxonomy_meta.get("department") or extracted_facts.get("department") or "")
    gtype = str(taxonomy_meta.get("grievance_type") or extracted_facts.get("grievance_type") or "")
    gsub = str(taxonomy_meta.get("grievance_sub_type") or extracted_facts.get("grievance_subtype") or "")

    # 1. Authoritative Taxonomy Scope Precedence:
    # Explicit DB scope ALWAYS takes priority over inferred scope.
    raw_db_scope = str(taxonomy_meta.get("scope_type") or "").upper().strip()
    is_explicit_db = raw_db_scope in ("PUBLIC", "INDIVIDUAL", "MIXED")

    if is_explicit_db:
        effective_scope = raw_db_scope
        scope_source = "database"
    else:
        inferred = deduce_taxonomy_scope(dept, gtype, gsub)
        if inferred in ("PUBLIC", "INDIVIDUAL", "MIXED"):
            effective_scope = inferred
            scope_source = "inferred"
        else:
            effective_scope = "UNKNOWN"
            scope_source = "unknown"

    pub_score = 0.0
    ind_score = 0.0
    evidence_reasons = []

    # Taxonomy base weight:
    # Explicit DB scope carries authoritative 0.50 weight; inferred carries 0.40.
    if effective_scope == "PUBLIC":
        weight = 0.50 if is_explicit_db else 0.40
        pub_score += weight
        evidence_reasons.append(
            f"Taxonomy ({scope_source}) classifies as public infrastructure/civic amenities"
        )
    elif effective_scope == "INDIVIDUAL":
        weight = 0.50 if is_explicit_db else 0.40
        ind_score += weight
        evidence_reasons.append(
            f"Taxonomy ({scope_source}) classifies as personal welfare/individual entitlement"
        )
    elif effective_scope == "MIXED":
        pub_score += 0.15
        ind_score += 0.15
        evidence_reasons.append("Taxonomy scope is mixed/dual-purpose; requires contextual evaluation")

    # 2. Beneficiary Context Weight: up to 0.35
    pub_marker_matches = [m for m in PUBLIC_BENEFICIARY_MARKERS if re.search(m, text)]
    ind_marker_matches = [m for m in INDIVIDUAL_BENEFICIARY_MARKERS if re.search(m, text)]

    if pub_marker_matches and not ind_marker_matches:
        pub_score += 0.35
        evidence_reasons.append(f"Contains collective beneficiary markers ({', '.join(pub_marker_matches[:2])})")
    elif ind_marker_matches and not pub_marker_matches:
        ind_score += 0.35
        evidence_reasons.append(f"Contains individual entitlement markers ({', '.join(ind_marker_matches[:2])})")
    elif pub_marker_matches and ind_marker_matches:
        pub_ratio = len(pub_marker_matches) / (len(pub_marker_matches) + len(ind_marker_matches))
        pub_score += 0.35 * pub_ratio
        ind_score += 0.35 * (1.0 - pub_ratio)
        evidence_reasons.append("Contains both collective and individual beneficiary markers")

    # 3. Action / Target Scope Weight: up to 0.20
    has_pub_action = any(re.search(p, text) for p in PUBLIC_ACTION_MARKERS)
    has_ind_action = any(re.search(p, text) for p in INDIVIDUAL_ACTION_MARKERS)

    if has_pub_action and not has_ind_action:
        pub_score += 0.20
        evidence_reasons.append("Requested action concerns public facility maintenance/installation")
    elif has_ind_action and not has_pub_action:
        ind_score += 0.20
        evidence_reasons.append("Requested action concerns individual entitlement disbursement")
    elif has_pub_action and has_ind_action:
        pub_score += 0.10
        ind_score += 0.10
        evidence_reasons.append("Requested action includes both public facility and personal elements")

    # 4. LLM Verification Hint Weight: up to 0.15
    if llm_scope_hint:
        hint_clean = llm_scope_hint.strip().upper()
        if any(h in hint_clean for h in ("PUBLIC", "COMMUNITY", "பொது")):
            pub_score += 0.15
            evidence_reasons.append("LLM verification confirmed public/community infrastructure scope")
        elif any(h in hint_clean for h in ("INDIVIDUAL", "PERSONAL", "தனிநபர்")):
            ind_score += 0.15
            evidence_reasons.append("LLM verification confirmed individual entitlement scope")

    # Normalize total scores for transparent inspection
    total = pub_score + ind_score
    if total > 0:
        norm_pub = round(pub_score / max(total, 1.0), 2)
        norm_ind = round(ind_score / max(total, 1.0), 2)
    else:
        norm_pub = 0.50
        norm_ind = 0.50

    # Decision & Confidence Threshold Logic
    classification = "Unknown"
    final_scope = "UNKNOWN"

    if effective_scope == "MIXED":
        # For mixed taxonomy, inspect actual context signals
        context_pub = pub_score - 0.15
        context_ind = ind_score - 0.15
        if context_pub >= 0.25 and (context_pub - context_ind) >= 0.15:
            classification = "Public"
            final_scope = "PUBLIC"
        elif context_ind >= 0.25 and (context_ind - context_pub) >= 0.15:
            classification = "Individual"
            final_scope = "INDIVIDUAL"
        else:
            # Evidence is balanced or weak -> do not force classification
            classification = "Unknown"
            final_scope = "MIXED"
    elif effective_scope == "PUBLIC":
        # Check if overwhelming contradictory individual evidence exists
        if ind_score > pub_score and (ind_score - pub_score) >= 0.15:
            classification = "Individual"
            final_scope = "INDIVIDUAL"
        elif pub_score >= 0.40 and (pub_score - ind_score) >= 0.10:
            classification = "Public"
            final_scope = "PUBLIC"
        elif is_explicit_db and not ind_marker_matches:
            # Authoritative DB scope with no contrary markers
            classification = "Public"
            final_scope = "PUBLIC"
        else:
            classification = "Unknown"
            final_scope = "UNKNOWN"
    elif effective_scope == "INDIVIDUAL":
        # Check if overwhelming contradictory public evidence exists
        if pub_score > ind_score and (pub_score - ind_score) >= 0.15:
            classification = "Public"
            final_scope = "PUBLIC"
        elif ind_score >= 0.40 and (ind_score - pub_score) >= 0.10:
            classification = "Individual"
            final_scope = "INDIVIDUAL"
        elif is_explicit_db and not pub_marker_matches:
            # Authoritative DB scope with no contrary markers
            classification = "Individual"
            final_scope = "INDIVIDUAL"
        else:
            classification = "Unknown"
            final_scope = "UNKNOWN"
    else:
        # Effective scope is UNKNOWN: classify purely from robust multi-signal context
        if pub_score >= 0.35 and (pub_score - ind_score) >= 0.15:
            classification = "Public"
            final_scope = "PUBLIC"
        elif ind_score >= 0.35 and (ind_score - pub_score) >= 0.15:
            classification = "Individual"
            final_scope = "INDIVIDUAL"
        else:
            classification = "Unknown"
            final_scope = "UNKNOWN"

    return {
        "classification": classification,
        "scope_type": final_scope,
        "public_score": norm_pub,
        "individual_score": norm_ind,
        "reason": "; ".join(evidence_reasons) if evidence_reasons else "Inconclusive grievance scope signals"
    }
