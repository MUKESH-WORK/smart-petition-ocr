"""
Semantic Petition Classifier — Pillar 1 + Pillar 2
====================================================
Pillar 1 (Subject Line Priority / Zonal Intent Parsing):
  - Extracts the பொருள் (Subject) line and கோரிக்கை (Prayer) section
  - Gives 3x weight to these authoritative zones for classification
  - Falls back to full-text only when subject/prayer are absent or vague

Pillar 2 (Semantic Vector Embedding Classification):
  - Pre-computes vector embeddings for every taxonomy category
  - Compares petition text embedding against category embeddings via cosine similarity
  - Understands *meaning*, not just word presence
  - "சாலையில் தண்ணீர் தேங்கி" → closer to "road damage" than "water supply"
"""

import re
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomy Category Definitions with Representative Tamil + English Phrases
# Each category has "anchor texts" — representative phrases that define what
# that category MEANS semantically. The classifier embeds these and compares
# against the petition text.
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_ANCHORS: Dict[str, Dict[str, Any]] = {
    "social_security_oap": {
        "label": "முதியோர் உதவித்தொகை / ஓய்வூதியம்",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Social Security Schemes (SSS)",
        "grievance_subtype": "Old Age Pension (OAP)",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar",
        "anchors": [
            "முதியோர் உதவித்தொகை வழங்க கோரிக்கை",
            "வயது மூப்பு காரணமாக வேலைக்கு செல்ல முடியவில்லை நிதி உதவி கோரி",
            "ஓய்வூதியம் வழங்கக் கோரி மனு",
            "old age pension financial assistance social security",
            "உதவித்தொகை வழங்கிட கோரிக்கை",
            "மகன் மகள் ஆதரவு இல்லாததால் அரசு உதவி",
        ]
    },
    "widow_pension": {
        "label": "விதவை ஓய்வூதியம் / உதவித்தொகை",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Destitute Widow Pension Scheme (DWPS) / Social Security Schemes",
        "grievance_subtype": "Destitute Widow Pension (DWP)",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar",
        "anchors": [
            "ஆதரவற்ற விதவை ஓய்வூதியம் கோரிக்கை",
            "கணவர் இறந்ததால் விதவை உதவித்தொகை கோரி",
            "destitute widow pension scheme DWPS",
            "விதவை நிதி உதவி",
        ]
    },
    "differently_abled_pension": {
        "label": "மாற்றுத்திறனாளி ஓய்வூதியம்",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Social Security Schemes (SSS)",
        "grievance_subtype": "Differently Abled Pension (DAP)",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar",
        "anchors": [
            "மாற்றுத்திறனாளி ஓய்வூதியம் கோரிக்கை",
            "ஊனமுற்றவர் உதவித்தொகை வழங்கக் கோரி",
            "differently abled pension DAP disability assistance",
        ]
    },
    "drinking_water": {
        "label": "குடிநீர் வசதி",
        "department": "Municipal Administration and Water Supply (MAWS)",
        "grievance_type": "Drinking Water",
        "grievance_subtype": "Insufficient Water Supply",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "responsible_officer": "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat",
        "anchors": [
            "குடிநீர் வசதி செய்து தரக் கோரிக்கை",
            "குடிநீர் இணைப்பு வழங்க கோரி மனு",
            "தண்ணீர் விநியோகம் சரிவர நடைபெறாததால் குடிநீர் கோரி",
            "drinking water supply connection request",
            "போதிய குடிநீர் விநியோகம் இல்லை",
            "குடிநீர் குழாய் இணைப்பு வழங்க வேண்டும்",
            "எங்கள் பகுதியில் குடிநீர் வசதி செய்து தருமாறு கோரிக்கை மனு",
            "தினசரி குடிநீர் விநியோகம் செய்ய நடவடிக்கை எடுக்க கோரிக்கை",
            "குடிநீர் விநியோகம் சீராக கிடைக்க புதிய குழாய் இணைப்பு மேல்நிலைத் தொட்டி",
            "தண்ணீர் பற்றாக்குறை குடிநீர் தட்டுப்பாடு தீர்க்க கோரி மனு",
            "ஊராட்சி குடிநீர் விநியோகம் சரிவர கிடைக்க நடவடிக்கை",
            "வாரத்திற்கு ஒருமுறை மட்டுமே தண்ணீர் வருவதால் குடிநீர் தட்டுப்பாடு",
        ]
    },
    "road_maintenance": {
        "label": "சாலை வசதி / பராமரிப்பு",
        "department": "Highways and Minor Ports Department (HMP)",
        "grievance_type": "Road Maintenance and Safety",
        "grievance_subtype": "Road Repair / Resurfacing",
        "sub_department": "Highways Department",
        "responsible_officer": "District Highway Engineer / Divisional Engineer",
        "anchors": [
            "சாலை பழுதடைந்துள்ளதால் சீரமைத்து தருமாறு கோரிக்கை",
            "சாலை சீரமைப்பு பணி மேற்கொள்ள கோரி",
            "சாலை பராமரிப்பு செய்யாததால் விபத்து அபாயம்",
            "road repair resurfacing maintenance damaged road",
            "பழுதடைந்த சாலையை சீரமைக்க கோரிக்கை",
            "சாலை குண்டும் குழியுமாக உள்ளதால் சீரமைக்க",
            "தார் சாலை அமைத்து தர கோரிக்கை மனு",
            "மண் சாலையை தார் சாலையாக சீரமைக்க கோரி",
            "தெரு சாலை பழுது நீக்கி புதிய தார் சாலை அமைக்க",
            "போக்குவரத்து பாதிக்கப்படும் வகையில் சாலை சேதம்",
        ]
    },
    "street_lights": {
        "label": "தெருவிளக்கு வசதி",
        "department": "Municipal Administration and Water Supply (MAWS)",
        "grievance_type": "Street Lights - MAWS",
        "grievance_subtype": "Street Lights - MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "responsible_officer": "Commissioner Municipal Corporation / Municipality, Erode",
        "anchors": [
            "தெருவிளக்கு பழுதடைந்துள்ளதால் சீரமைக்க கோரிக்கை",
            "தெருவிளக்கு வசதி செய்து தர கோரி மனு",
            "street light repair installation request",
            "மின்விளக்கு எரியாமல் உள்ளதால் புதிய விளக்கு",
        ]
    },
    "drainage_sewage": {
        "label": "கழிவுநீர் / வடிகால் வசதி",
        "department": "Municipal Administration and Water Supply (MAWS)",
        "grievance_type": "Storm Water Drains - MAWS",
        "grievance_subtype": "Storm Water Drains - MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "responsible_officer": "Commissioner Municipal Corporation / Municipality, Erode",
        "anchors": [
            "கழிவுநீர் வடிகால் வசதி செய்து தரக் கோரிக்கை",
            "வடிகால் அடைப்பு நீக்கி தூர்வாரக் கோரி",
            "சாக்கடை நீர் தேங்கி சுகாதாரக் கேடு",
            "drainage sewage storm water drain clogged",
            "மழைநீர் வடிகால் அமைக்க கோரிக்கை",
        ]
    },
    "land_encroachment": {
        "label": "நில ஆக்கிரமிப்பு அகற்றுதல்",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Land Encroachment",
        "grievance_subtype": "Eviction of Encroachments on Government Land / Pathway",
        "sub_department": "Revenue Administration",
        "responsible_officer": "Tahsildar / Revenue Divisional Officer (RDO)",
        "anchors": [
            "ஆக்கிரமிப்பு அகற்ற நடவடிக்கை கோரிக்கை",
            "போக வழி ஆக்கிரமிப்பு நீக்கக் கோரி",
            "வழிப்பாதை ஆக்கிரமிப்பு அகற்றுதல் encroachment removal",
            "அரசு நிலம் ஆக்கிரமிப்பு",
        ]
    },
    "patta_transfer": {
        "label": "பட்டா மாறுதல்",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Land Administration and Patta Transfer",
        "grievance_subtype": "Patta Transfer - Individual / Sub-division",
        "sub_department": "Revenue Administration / Land Records",
        "responsible_officer": "Tahsildar / Zonal Deputy Tahsildar",
        "anchors": [
            "பட்டா மாறுதல் செய்து தரக் கோரிக்கை",
            "பட்டா பெயர் மாற்றம் செய்ய கோரி",
            "patta transfer name change land record",
            "உட்பிரிவு பட்டா வழங்கக் கோரி",
        ]
    },
    "free_house_site_patta": {
        "label": "இலவச வீட்டு மனைப் பட்டா",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Natham Patta /Free House Site Patta",
        "grievance_subtype": "Free House Site Patta (HSD)",
        "sub_department": "Revenue Administration / நில நிர்வாகம்",
        "responsible_officer": "Tahsildar, Erode",
        "anchors": [
            "இலவச வீட்டு மனைப் பட்டா வழங்கக் கோரிக்கை",
            "free house site patta HSD natham patta",
            "வீட்டு மனை பட்டா வழங்க கோரி",
        ]
    },
    "heir_certificate": {
        "label": "வாரிசு சான்றிதழ்",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Certificates and Verification",
        "grievance_subtype": "Legal Heir Certificate / Community Certificate",
        "sub_department": "Revenue Administration",
        "responsible_officer": "Tahsildar / Zonal Deputy Tahsildar",
        "anchors": [
            "வாரிசு சான்றிதழ் வழங்க கோரிக்கை",
            "இறப்பு சான்றிதழ் வாரிசு பதிவு",
            "legal heir certificate community certificate request",
        ]
    },
    "scholarship": {
        "label": "கல்வி உதவித்தொகை",
        "department": "Higher Education Department (HIGHEDU)",
        "grievance_type": "Scholarship - High Edu",
        "grievance_subtype": "Scholarship - High Edu",
        "sub_department": "Director Of Collegiate Education",
        "responsible_officer": "Joint Director of Collegiate Education",
        "anchors": [
            "கல்வி உதவித்தொகை வழங்கக் கோரிக்கை",
            "கல்லூரி படிப்புக்கு நிதி உதவி scholarship",
            "மாணவர் கல்வி உதவி scholarship education grant",
        ]
    },
    "electricity": {
        "label": "மின்சார வசதி",
        "department": "Energy Department (ENERGY)",
        "grievance_type": "Electricity Supply and Metering",
        "grievance_subtype": "Low Voltage / Power Fluctuation / Transformer Repair",
        "sub_department": "TANGEDCO",
        "responsible_officer": "Section Officer (Distribution) - TANGEDCO",
        "anchors": [
            "மின்சார வசதி செய்து தரக் கோரிக்கை",
            "மின் இணைப்பு வழங்க கோரி transformer repair",
            "electricity supply low voltage power TANGEDCO",
        ]
    },
    "ration_services": {
        "label": "ரேஷன் கார்டு சேவை",
        "department": "Co-operation, Food and Consumer Protection Department (FOODCO)",
        "grievance_type": "Civil Supplies and Ration Services",
        "grievance_subtype": "Smart Card / Ration Card Services / PDS Supplies",
        "sub_department": "Civil Supplies and Consumer Protection",
        "responsible_officer": "District Supply Officer (DSO) / Taluk Supply Officer (TSO)",
        "anchors": [
            "ரேஷன் கார்டு வழங்கக் கோரிக்கை",
            "ration card smart card PDS rice distribution",
            "உணவுப் பொருள் விநியோகம் சரிவர நடைபெறவில்லை",
        ]
    },
    "aadhaar_esevai": {
        "label": "ஆதார் / இ-சேவை",
        "department": "Information Technology Department (IT)",
        "grievance_type": "Application Related Complaints - CeG",
        "grievance_subtype": "eSevai - Complaint related to Aadhaar Enrolment",
        "sub_department": "Commissionerate of eGovernance/Tamil Nadu e-Governance Agency",
        "responsible_officer": "e-sevai helpdesk",
        "anchors": [
            "ஆதார் திருத்தம் செய்ய கோரிக்கை",
            "ஆதார் அட்டை பெயர் மாற்றம்",
            "aadhaar enrolment correction eSevai center",
            "இ-சேவை மையம் சார்ந்த புகார்",
        ]
    },
    "public_relief_fund": {
        "label": "பொது நிவாரண நிதி",
        "department": "Revenue and Disaster Management (REV)",
        "grievance_type": "Public Relief Fund / Financial Assistance",
        "grievance_subtype": "Chief Minister's Public Relief Fund (CMPRF)",
        "sub_department": "Revenue Administration",
        "responsible_officer": "District Collector / District Revenue Officer (DRO)",
        "anchors": [
            "முதலமைச்சர் பொது நிவாரண நிதி கோரிக்கை",
            "chief minister public relief fund CMPRF financial help",
            "நிவாரண உதவி வழங்கக் கோரி",
        ]
    },
}


def _extract_subject_line(zone_b_body: str) -> str:
    """
    Pillar 1: Extract the பொருள் (Subject) line from Zone B.
    This is the most authoritative single sentence for classification.
    """
    if not zone_b_body:
        return ""
    
    # Match "பொருள் :" followed by the subject text (may span multiple lines until next section)
    subject_match = re.search(
        r'பொருள்\s*:\s*(.+?)(?:\n\s*(?:மதிப்பிற்குரிய|மாண்புமிகு|வணக்கம்|அன்புடன்|ஐயா|நான்|எங்கள்)\b|$)',
        zone_b_body,
        re.DOTALL | re.IGNORECASE
    )
    if subject_match:
        subject = subject_match.group(1).strip()
        # Clean up multiline subjects
        subject = re.sub(r'\s+', ' ', subject).strip(' .,;:-')
        return subject
    
    # Fallback: Try alternate subject patterns
    alt_match = re.search(
        r'(?:Subject|பொருள்|Porul)\s*[:：]\s*(.+?)(?:\n|$)',
        zone_b_body,
        re.IGNORECASE
    )
    if alt_match:
        return alt_match.group(1).strip(' .,;:-')
    
    return ""


def _extract_prayer_section(text: str) -> str:
    """
    Pillar 1: Extract the prayer/request section (கோரிக்கை / பிரார்த்தனை).
    This is the petitioner's formal request — the ground truth of what they want.
    """
    if not text:
        return ""

    # Avoid matching "கோரிக்கை மனு" in the subject line (பொருள்)
    search_text = text
    subj_match = re.search(r'(?:பொருள்|Subject|Porul)\s*[:：].*?(?:\n|$)', text, re.IGNORECASE)
    if subj_match:
        search_text = text[subj_match.end():]

    # Look for explicit prayer markers in the remaining body
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

    # Fallback: extract last meaningful paragraph before signature
    sig_idx = search_text.find("இப்படிக்கு")
    if sig_idx == -1:
        sig_idx = search_text.find("இவண்")
    if sig_idx > 100:
        last_section = search_text[max(0, sig_idx - 500):sig_idx].strip()
        sentences = [s.strip() for s in re.split(r'[.।\n]', last_section) if len(s.strip()) > 20]
        if sentences:
            return sentences[-1]

    return ""


class SemanticPetitionClassifier:
    """
    Production-grade semantic petition classifier combining:
    - Pillar 1: Subject Line Priority (3x weight on பொருள் and கோரிக்கை zones)
    - Pillar 2: Semantic Vector Embedding similarity (understands meaning, not just words)
    """

    def __init__(self):
        self._category_embeddings: Dict[str, np.ndarray] = {}
        self._vector_store = None
        self._initialized = False
    
    def _get_vector_store(self):
        """Lazy-load the vector store to avoid circular imports."""
        if self._vector_store is None:
            from services.vector_store import vector_store
            self._vector_store = vector_store
        return self._vector_store
    
    def _ensure_initialized(self):
        """Pre-compute embeddings for all category anchor texts."""
        if self._initialized:
            return
        
        try:
            vs = self._get_vector_store()
            
            for cat_key, cat_info in CATEGORY_ANCHORS.items():
                anchor_texts = cat_info["anchors"]
                # Encode all anchor texts for this category
                anchor_embeddings = vs.encode(anchor_texts)
                # Average all anchor embeddings to get a single category centroid
                centroid = np.mean(anchor_embeddings, axis=0).astype(np.float32)
                norm = float(np.linalg.norm(centroid))
                if norm > 0:
                    centroid = centroid / norm
                self._category_embeddings[cat_key] = centroid
            
            self._initialized = True
            logger.info(
                f"✅ Semantic Classifier initialized with {len(self._category_embeddings)} "
                f"category embeddings (Backend: {vs._active_backend})"
            )
        except Exception as e:
            logger.warning(f"Semantic classifier initialization note: {e}")
            self._initialized = False
    
    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        min_len = min(len(vec_a), len(vec_b))
        a = vec_a[:min_len]
        b = vec_b[:min_len]
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)
    
    def classify(
        self,
        zone_a_header: str = "",
        zone_b_body: str = "",
        full_doc_text: str = "",
    ) -> Dict[str, Any]:
        """
        Classify a petition using Pillar 1 + Pillar 2.
        
        Returns:
            {
                "category_key": str,
                "label": str,
                "department": str,
                "grievance_type": str,
                "grievance_subtype": str,
                "sub_department": str,
                "responsible_officer": str,
                "confidence": float,
                "method": str,          # "subject_line" | "semantic_vector" | "fallback"
                "subject_line": str,
                "scores": dict,         # all category scores for debugging
            }
        """
        self._ensure_initialized()
        
        # ── Pillar 1: Extract Subject Line and Prayer ──
        subject_line = _extract_subject_line(zone_b_body)
        prayer = _extract_prayer_section(full_doc_text)
        
        logger.info(f"📋 Pillar 1 — Subject Line: '{subject_line[:80]}...' | Prayer: '{prayer[:60]}...'")
        
        if not self._category_embeddings:
            # If embeddings failed to initialize, fall back to keyword-only
            logger.warning("Semantic embeddings not available, returning empty classification")
            return {
                "category_key": None,
                "label": None,
                "confidence": 0.0,
                "method": "fallback",
                "subject_line": subject_line,
                "scores": {},
            }
        
        vs = self._get_vector_store()
        
        # ── Pillar 2: Compute weighted semantic similarity ──
        # Build text segments with zone-based weights
        # Subject line gets 4.0x weight, Prayer gets 2.5x weight, Body gets 0.5x weight
        segments: List[Tuple[str, float]] = []
        
        if subject_line and len(subject_line) > 5:
            segments.append((subject_line, 4.0))
        
        if prayer and len(prayer) > 10:
            segments.append((prayer, 2.5))
        
        # Use first 300 chars of body for context (avoid noise from long documents)
        body_text = (zone_b_body or full_doc_text or "")[:300]
        if body_text and len(body_text) > 10:
            segments.append((body_text, 0.5))
        
        if not segments:
            return {
                "category_key": None,
                "label": None,
                "confidence": 0.0,
                "method": "fallback",
                "subject_line": subject_line,
                "scores": {},
            }
        
        # Compute embeddings for all text segments
        segment_texts = [s[0] for s in segments]
        segment_weights = [s[1] for s in segments]
        segment_embeddings = vs.encode(segment_texts)
        
        # Compute weighted similarity score for each category
        category_scores: Dict[str, float] = {}
        
        for cat_key, cat_centroid in self._category_embeddings.items():
            # Weighted average of similarities across all text segments
            weighted_sim_sum = 0.0
            weight_sum = 0.0
            
            for emb, weight in zip(segment_embeddings, segment_weights):
                emb_arr = np.array(emb, dtype=np.float32)
                sim = self._cosine_similarity(emb_arr, cat_centroid)
                weighted_sim_sum += sim * weight
                weight_sum += weight
            
            category_scores[cat_key] = weighted_sim_sum / weight_sum if weight_sum > 0 else 0.0
        
        # Sort categories by score (descending)
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        best_key, best_score = sorted_categories[0]
        second_key, second_score = sorted_categories[1] if len(sorted_categories) > 1 else (None, 0.0)
        
        # Determine classification method
        if subject_line and len(subject_line) > 5:
            method = "subject_line_semantic"
        else:
            method = "body_semantic"
        
        # Build result
        best_cat = CATEGORY_ANCHORS[best_key]
        
        # Log top 3 scores for debugging
        top3 = sorted_categories[:3]
        top3_str = ", ".join(
            "{0}={1:.4f}".format(CATEGORY_ANCHORS[k]["label"], s) for k, s in top3
        )
        logger.info(
            f"🎯 Semantic Classification: {best_cat['label']} "
            f"(score={best_score:.4f}, method={method}) | "
            f"Top3: {top3_str}"
        )

        
        return {
            "category_key": best_key,
            "label": best_cat["label"],
            "department": best_cat["department"],
            "grievance_type": best_cat["grievance_type"],
            "grievance_subtype": best_cat["grievance_subtype"],
            "sub_department": best_cat["sub_department"],
            "responsible_officer": best_cat["responsible_officer"],
            "confidence": round(best_score, 4),
            "confidence_gap": round(best_score - second_score, 4),
            "method": method,
            "subject_line": subject_line,
            "scores": {k: round(s, 4) for k, s in sorted_categories[:5]},
        }


# Module-level singleton
semantic_classifier = SemanticPetitionClassifier()
