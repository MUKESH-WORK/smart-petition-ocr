import asyncio
import json
import uuid
import re
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
else:
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import text
    except ImportError:
        AsyncSession = Any
        text = lambda x: x

from app.config import settings
from core.llm_client import llm_client, SYSTEM_PROMPT_TAMIL, extract_json_object
from services.taxonomy_matcher import taxonomy_matcher
from services.location_matcher import location_matcher
from services.verification_barrier import verification_barrier
from services.prompt_builder import prompt_builder, SYSTEM_PROMPT_COGNITIVE
from services.entity_extractor import (
    segment_petition_zones,
    parse_petition_zones,
    extract_petitioner_phone,
    extract_header_entities,
    parse_tamil_location,
    parse_tamil_address_and_location,
    extract_gdp_form_metadata,
    is_same_person_or_invalid
)
from services.semantic_classifier import semantic_classifier

logger = logging.getLogger(__name__)



def datetime_suffix_short() -> str:
    return datetime.now(timezone.utc).strftime("%d%b%y").upper()


class AIAnalyzer:
    """
    Production-grade AI Grievance Analyzer:
    - Analyzes full high-fidelity OCR text (from Datalab Chandra OCR)
    - Directly extracts petitioner info, address hierarchy, grievance classifications, and summaries via LLM
    - Populates all grievance draft fields without brittle regex limitations
    - Grounding and anti-hallucination verification
    - Master location code validation
    """

    def __init__(self, llm=llm_client):
        self.llm = llm

    @staticmethod
    def is_noisy_ocr_text(val: str) -> bool:
        if not val or not isinstance(val, str):
            return True
        v = val.strip()
        if v.startswith("[Page") or "#H-" in v or "Coaning" in v or "Opடiyelu" in v or "HgB" in v:
            return True
        tokens = v.split()
        if len(tokens) > 5:
            gibberish_count = sum(1 for t in tokens if len(t) <= 2 or re.search(r'[A-Za-z0-9][\u0B80-\u0BFF]|[\u0B80-\u0BFF][A-Za-z0-9]', t))
            if gibberish_count / len(tokens) > 0.35:
                return True
        return False

    def _verify_claims(self, analysis: Dict[str, Any], doc_text: Any) -> Dict[str, Any]:
        """
        Anti-Hallucination Barrier v2:
        A claim is verified only if:
        1. >= 60% of its content words (>3 chars, stopwords removed) appear in the SAME source chunk.
        2. Every digit-sequence in the claim exists in the document text.
        Otherwise verified=False, confidence=0.0.
        Post-check: scan summary for ungrounded digit sequences -> block and flag.
        """
        STOPWORDS = {
            "மற்றும்", "ஆகிய", "என்ற", "சார்ந்த", "கொண்டு", "மூலம்", "உள்ள", "குறித்து", "செய்து",
            "உள்ளது", "வசித்து", "வருகிறார்", "கோரி", "மனு", "அளித்துள்ளார்", "நடவடிக்கை",
            "the", "and", "for", "with", "from", "that", "this", "have", "has", "was", "are", "been"
        }
        
        claims = analysis.get("claims", [])
        if not claims:
            summary = analysis.get("description_summary_tamil", "")
            if summary:
                claims = [{"text": summary[:140], "source_page": 1, "confidence": 0.90}]
            else:
                claims = []

        # Prepare chunk strings
        chunks: List[str] = []
        if isinstance(doc_text, list):
            for c in doc_text:
                t = c.get("chunk_text", "") if isinstance(c, dict) else str(c)
                if t:
                    chunks.append(t)
        else:
            raw_s = str(doc_text or "")
            # Split into natural paragraph/page chunks if single string
            split_chunks = [p.strip() for p in raw_s.split("--- பக்கம் ") if p.strip()]
            chunks = split_chunks if split_chunks else [raw_s]

        full_doc_str = " ".join(chunks)
        doc_lower = full_doc_str.lower()
        verified_count = 0

        for claim in claims:
            claim_text = str(claim.get("text", "")).strip()
            if not claim_text:
                claim["verified"] = False
                claim["confidence"] = 0.0
                continue

            # 1. Strict Digit Sequence Check: Every digit sequence in claim must exist in full_doc_str
            claim_digits = re.findall(r'\d+', claim_text)
            digits_ok = all(d in full_doc_str for d in claim_digits)
            if not digits_ok:
                claim["verified"] = False
                claim["confidence"] = 0.0
                continue

            # 2. Content Word Grounding Check (>= 60% in the SAME source chunk)
            words = [w for w in re.findall(r'[\w\u0B80-\u0BFF]+', claim_text.lower()) if len(w) > 3 and w not in STOPWORDS]
            if not words:
                is_sub = claim_text.lower() in doc_lower
                claim["verified"] = is_sub
                claim["confidence"] = 1.0 if is_sub else 0.0
                if is_sub:
                    verified_count += 1
                continue

            max_chunk_ratio = 0.0
            for ch in chunks:
                ch_lower = ch.lower()
                matched_in_chunk = sum(1 for w in words if w in ch_lower)
                ratio = matched_in_chunk / len(words)
                if ratio > max_chunk_ratio:
                    max_chunk_ratio = ratio

            if max_chunk_ratio >= 0.60:
                claim["verified"] = True
                claim["confidence"] = round(max_chunk_ratio, 2)
                verified_count += 1
            else:
                claim["verified"] = False
                claim["confidence"] = 0.0

        # Post-check: regex-scan entire AI summary for ungrounded digit sequences
        summary_all = f"{analysis.get('description_summary_tamil', '')} {analysis.get('description_summary_english', '')}"
        summary_digits = re.findall(r'\d+', summary_all)
        unverified_digits = [d for d in summary_digits if d not in full_doc_str]
        if unverified_digits:
            analysis["flagged_unverified_digits"] = unverified_digits
            logger.warning(f"Anti-hallucination post-check blocked unverified digits in AI summary: {unverified_digits}")

        total = len(claims) if claims else 1
        hallucination_score = round((total - verified_count) / total, 2)
        if unverified_digits:
            hallucination_score = min(1.0, round(hallucination_score + 0.25, 2))

        analysis["claims"] = claims
        analysis["hallucination_score"] = max(0.0, min(1.0, hallucination_score))
        analysis["grounding_score"] = round(1.0 - analysis["hallucination_score"], 2)
        return analysis

    def _build_grounded_fallback(self, doc_text: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Precomputes an objective rule-based fallback if LLM is temporarily unreachable."""
        entity_map = {e["entity_type"]: e["entity_value"] for e in entities}

        pet_name = entity_map.get("petitioner_name", "")
        if pet_name in ["நான்", "நாங்கள்", "அவர்கள்", "இவர்", "மனுதாரர்", "விண்ணப்பதாரர்", "பொதுமக்கள்", "-", "--", "none", "unknown"] or len(pet_name) <= 2:
            pet_name = ""

        # Secondary check for sender in doc_text if pet_name was empty or filtered
        if not pet_name:
            sender_m = re.search(r'(?:^|\n)\s*(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்|From)\s*[:\.\-]?\s*\n+([^\n,]+)', doc_text, re.IGNORECASE)
            if sender_m:
                cs = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', sender_m.group(1)).strip()
                cs = re.sub(r'[\(\)0-9#*]', '', cs).strip(',.-: ')
                if len(cs) >= 2 and not any(skip in cs for skip in ["நான்", "நாங்கள்", "-", "--", "பெறுநர்", "ஆட்சியர்"]):
                    pet_name = cs

        if not pet_name:
            wo_match = re.search(r'(?:^|\n)\s*([^\n:]+?)\s*(?:\(\d+\))?\s*\n+\s*(?:w/o|w\.o|க/பெ|க\.பெ|மனைவி)\s+([^\n,]+)', doc_text, re.IGNORECASE)
            if wo_match:
                cw = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', wo_match.group(1)).strip()
                cw = re.sub(r'\(\d+\)|\d+', '', cw).strip(',.-: ')
                if len(cw) >= 2 and cw not in ["நான்", "நாங்கள்", "-", "--"]:
                    pet_name = cw

        if not pet_name:
            so_match = re.search(r'(?:^|\n)\s*([^\n:]+?)\s*(?:\(\d+\))?\s*\n+\s*(?:s/o|s\.o|த/பெ|த\.பெ|ம/பெ|மகன்)\s+([^\n,]+)', doc_text, re.IGNORECASE)
            if so_match:
                cs = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', so_match.group(1)).strip()
                cs = re.sub(r'\(\d+\)|\d+', '', cs).strip(',.-: ')
                if len(cs) >= 2 and cs not in ["நான்", "நாங்கள்", "-", "--"]:
                    pet_name = cs

        if not pet_name:
            idx_sig = doc_text.find("இப்படிக்கு")
            if idx_sig == -1:
                idx_sig = doc_text.find("இவண்")
            if idx_sig != -1:
                sig_lines = [l.strip() for l in doc_text[idx_sig:].split("\n") if l.strip()]
                for sl in sig_lines[1:5]:
                    if any(skip in sl for skip in ["இணைப்பு", "நகல்", "சான்றிதழ்", "மனு", "மக்கள்", "புகைப்படம்", "ஆதார்"]):
                        continue
                    cs = re.sub(r'[\(\)0-9#*]', '', sl).strip(',.-:() ')
                    if (
                        cs and 2 <= len(cs) <= 35 and
                        not any(cs.startswith(w) for w in ["தங்கள்", "உண்மையுள்ள", "வணக்கம்", "நன்றி", "நாள்", "தேதி", "செல்", "போன்", "இணைப்பு"]) and
                        not any(skip in cs for skip in ["TK", "Dt", "District", "Taluk", "வட்டம்", "மாவட்டம்", "இணைப்பு", "நகல்"])
                    ):
                        pet_name = cs
                        break

        raw_g = entity_map.get("grievance_type") or entity_map.get("petition_subject") or ""
        if not raw_g or raw_g in ["பொது குறை", "-", "--", "None", "none", "unknown"] or len(raw_g) <= 2:
            detected_category = None
        elif len(raw_g) > 40 or any(m in raw_g for m in ["கோருதல்", "வேண்டி", "குறித்து", "தொடர்பாக", "விண்ணப்பம்", "அபாயம்", "பணிகளால்", "."]):
            # Long sentence or subject phrase; do not use as taxonomy category
            detected_category = None
        else:
            detected_category = raw_g

        # ────────────────────────────────────────────────────────────────────
        # Pillar 1 + 2: Semantic Classification (Subject Line Priority + Vector Embeddings)
        # Uses meaning-aware classification instead of fragile keyword matching.
        # The semantic classifier:
        #   1. Extracts the பொருள் (Subject) line and gives it 3x weight
        #   2. Extracts the prayer/request section and gives it 2x weight
        #   3. Compares embeddings against pre-computed category centroids
        # ────────────────────────────────────────────────────────────────────
        semantic_result = None
        try:
            zones = segment_petition_zones(doc_text)
            semantic_result = semantic_classifier.classify(
                zone_a_header=zones.get("zone_a_header", ""),
                zone_b_body=zones.get("zone_b_body", ""),
                full_doc_text=doc_text,
            )
            if semantic_result and semantic_result.get("confidence", 0) >= 0.15 and semantic_result.get("label"):
                detected_category = semantic_result["label"]
                logger.info(
                    f"🎯 Pillar 1+2 Semantic Classification: '{detected_category}' "
                    f"(confidence={semantic_result['confidence']}, method={semantic_result.get('method')}, "
                    f"subject='{semantic_result.get('subject_line', '')[:60]}')"
                )
        except Exception as sem_err:
            logger.debug(f"Semantic classifier fallback note: {sem_err}")

        # Keyword fallback: Only used when semantic classifier confidence is too low
        if not detected_category or detected_category == "பொது குறை":
            logger.info("📎 Falling back to keyword classification (semantic confidence too low)")
            # Check financial assistance / pension FIRST before civic utilities
            if any(k in doc_text.lower() for k in [
                "உதவித்தொகை", "உதவித் தொகை", "உதவி தொகை", "நிதி உதவி", "நிதியுதவி",
                "வயது மூப்பு", "முதியோர்", "ஓய்வூதியம்", "வேலைக்கு செல்ல முடியவில்லை",
                "மகனோ", "மகளோ உதவி இல்லை", "oap", "pension", "financial assistance"
            ]):
                if any(w in doc_text.lower() for w in ["விதவை", "widow", "dwps", "ஆதரவற்ற விதவை"]):
                    detected_category = "விதவை ஓய்வூதியம் / உதவித்தொகை"
                elif any(w in doc_text.lower() for w in ["கல்வி", "scholarship", "கல்லூரி", "மாணவர்", "மாணவி"]):
                    detected_category = "கல்வி உதவித்தொகை"
                elif any(w in doc_text.lower() for w in ["மாற்றுத்திறனாளி", "differently abled", "ஊனம்", "dap"]):
                    detected_category = "மாற்றுத்திறனாளி ஓய்வூதியம்"
                elif any(w in doc_text.lower() for w in ["முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "oap", "old age", "senior citizen"]):
                    detected_category = "முதியோர் உதவித்தொகை / ஓய்வூதியம்"
                else:
                    detected_category = "பொது நிதி உதவி"
            elif any(k in doc_text.lower() for k in ["குடிநீர்", "தண்ணீர்", "குடிநீர் இணைப்பு", "drinking water", "water connection", "water supply"]):
                detected_category = "குடிநீர் வசதி"
            elif any(k in doc_text.lower() for k in ["தெருவிளக்கு", "பழுதடைந்த தெருவிளக்கு", "street light"]):
                detected_category = "தெருவிளக்கு வசதி"
            elif any(k in doc_text.lower() for k in ["கழிவுநீர்", "வடிகால்", "சாக்கடை", "drainage", "storm water", "sewage"]):
                detected_category = "கழிவுநீர் / வடிகால் வசதி"
            elif any(k in doc_text.lower() for k in ["சாலைப்பணி", "சாலை பணி", "சாலை சீரமைப்பு", "சாலை பராமரிப்பு", "நெடுஞ்சாலை பணி", "விபத்து அபாயம்", "பழுதடைந்த சாலை"]):
                detected_category = "சாலை வசதி / பராமரிப்பு"

        if not detected_category:
            for cat, keywords in {
                "முதியோர் உதவித்தொகை / ஓய்வூதியம்": ["முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "oap", "old age", "senior citizen"],
                "விதவை ஓய்வூதியம் / உதவித்தொகை": ["ஆதரவற்ற விதவை", "விதவை", "widow", "dwps", "dwp"],
                "கல்வி உதவித்தொகை": ["கல்வி உதவித்தொகை", "கல்வி உதவி", "scholarship", "கல்லூரி உதவி", "மாணவர் கல்வி", "கல்வி"],
                "மாற்றுத்திறனாளி உதவித்தொகை": ["மாற்றுத்திறனாளி", "differently abled", "ஊனம்", "dap"],
                "பொது நிதி உதவி": ["உதவித்தொகை", "உதவித் தொகை", "உதவி தொகை", "நிதி உதவி", "நிதியுதவி", "financial assistance"],
                "குடிநீர் வசதி": ["குடிநீர்", "தண்ணீர்", "நீர் வசதி", "water connection", "drinking water"],
                "கழிவுநீர் / வடிகால் வசதி": ["கழிவுநீர்", "வடிகால்", "சாக்கடை", "drainage", "storm water", "sewage", "தூர்வார"],
                "தெருவிளக்கு வசதி": ["தெருவிளக்கு", "விளக்குகள்", "மின்விளக்கு", "street light", "lighting"],
                "நில ஆக்கிரமிப்பு அகற்றுதல்": ["ஆக்கிரமிப்பு", "போக வழி", "வழி ஆக்கிரமிப்பு", "பாதை ஆக்கிரமிப்பு", "encroachment"],
                "வாரிசு சான்றிதழ்": ["வாரிசு", "இறப்பு", "சான்று", "சான்றிதழ்", "heir"],
                "பட்டா மாறுதல்": ["பட்டா மாறுதல்", "பட்டா பெயர் மாற்றம்", "உட்பிரிவு", "patta transfer"],
                "பட்டா / நிலம்": ["நில", "பட்டா", "சர்வே", "land", "patta", "நத்தம்"],
                "சாலை வசதி": ["சாலைப்பணி", "சாலை பராமரிப்பு", "சாலை சீரமைப்பு", "விபத்து அபாயம்"],
                "மின்சார வசதி": ["மின்", "electric", "electricity", "eb"],
                "ஆதார் / பெயர் மாற்றம்": ["ஆதார் திருத்தம்", "ஆதார் பெயர் மாற்றம்", "ஆதார் அட்டை சேர்க்கை"],
                "வருவாய்த்துறை": ["வருவாய்", "revenue"],
                "சுகாதாரம்": ["சுகாதாரம்", "சாக்கடை", "குப்பை"]
            }.items():
                if any(k.lower() in doc_text.lower() for k in keywords):
                    detected_category = cat
                    break

        detected_category = detected_category or "பொது குறை"
        if detected_category in ["-", "--", ""]:
            detected_category = "பொது குறை"

        loc = entity_map.get("village") or entity_map.get("taluk") or ""
        if loc in ["-", "--", "None"]:
            loc = ""

        surv = entity_map.get("survey_no", "")
        if surv in ["-", "--", "None"] or re.search(r'^\d+/\d+$', surv):
            surv = ""

        # Derive department ONLY from official CM helpline taxonomy matcher
        tax_match = taxonomy_matcher.match(
            petition_text=f"{detected_category} {doc_text[:400]}",
            detected_type=detected_category
        )
        f_subdept = None
        f_respoff = None
        if tax_match and tax_match.get("validated"):
            dept = tax_match["department"]
            f_gtype = tax_match["grievance_type"]
            f_gsub = tax_match["grievance_subtype"]
            f_subdept = tax_match.get("sub_department")
            f_respoff = tax_match.get("responsible_officer")
        elif any(w in (detected_category + " " + doc_text).lower() for w in ["முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "old age", "senior citizen", "oap"]):
            dept = "Revenue and Disaster Management (REV)"
            f_gtype = "Social Security Schemes (SSS)"
            f_gsub = "Old Age Pension (OAP)"
            f_subdept = "Social Security Schemes (SSS) / Revenue Administration"
            f_respoff = "Special Tahsildar (SSS) / Tahsildar"
        elif "குடிநீர்" in (detected_category + " " + doc_text) or "தண்ணீர்" in (detected_category + " " + doc_text) or "water" in doc_text.lower():
            dept = "Municipal Administration and Water Supply (MAWS)"
            f_gtype = "Drinking Water"
            f_gsub = "New Water Connection - Household Water Connection" if any(w in doc_text for w in ["இணைப்பு", "connection", "புதிய"]) else "Insufficient Water Supply"
            f_subdept = "Commissionerate of Municipal Administration (CMA)"
            f_respoff = "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
        elif "தெருவிளக்கு" in detected_category or "street light" in doc_text.lower() or "தெருவிளக்கு" in doc_text:
            dept = "Municipal Administration and Water Supply (MAWS)"
            f_gtype = "Street Lights - MAWS"
            f_gsub = "Street Lights - MAWS"
            f_subdept = "Commissionerate of Municipal Administration (CMA)"
            f_respoff = "Commissioner Municipality, Commissioner Municipal Corporation"
        elif "வடிகால்" in (detected_category + " " + doc_text) or "கழிவுநீர்" in (detected_category + " " + doc_text) or "drain" in doc_text.lower():
            dept = "Municipal Administration and Water Supply (MAWS)"
            f_gtype = "Storm Water Drains - MAWS"
            f_gsub = "Storm Water Drains - MAWS"
            f_subdept = "Commissionerate of Municipal Administration (CMA)"
            f_respoff = "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
        elif "விதவை" in (detected_category + " " + doc_text) or "dwps" in doc_text.lower() or "widow" in doc_text.lower():
            dept = "Revenue and Disaster Management (REV)"
            f_gtype = "Destitute Widow Pension Scheme (DWPS) / Social Security Schemes"
            f_gsub = "Destitute Widow Pension (DWP)"
            f_subdept = "Social Security Schemes (SSS) / Revenue Administration"
            f_respoff = "Special Tahsildar (SSS) / Tahsildar"
        elif "கல்வி" in (detected_category + " " + doc_text) or "scholarship" in doc_text.lower() or "கல்வி உதவி" in doc_text:
            dept = "Higher Education Department (HIGHEDU)"
            f_gtype = "Scholarship - High Edu"
            f_gsub = "Scholarship - High Edu"
            f_subdept = "Director Of Collegiate Education"
            f_respoff = "Joint Director of Collegiate Education"
        else:
            dept = "General Administration"
            f_gtype = "General Grievance"
            f_gsub = "Public Grievance Redressal"
            f_subdept = "General Administration / பொது நிர்வாகம்"
            f_respoff = "துறை அலுவலர்"

        if "கல்வி" in detected_category or "scholarship" in doc_text.lower() or "கல்வி உதவி" in doc_text:
            summary_ta = f"மனுதாரர் {pet_name or ''} ஏழை குடும்பத்தைச் சேர்ந்தவர். குடும்ப வறுமை சூழ்நிலையில் கல்லூரி படிப்பைத் தொடர அரசு முதலமைச்சரின் கல்வி உதவித்தொகை (Scholarship) திட்டத்தின் கீழ் நிதி உதவி வழங்குமாறு கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} from an economically disadvantaged family has requested financial assistance under the Chief Minister's Scholarship Scheme to continue higher education studies."
        elif any(w in (detected_category + " " + doc_text) for w in ["முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "old age", "oap"]):
            summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}, வயது மூப்பு மற்றும் உடல்நலக்குறைவு காரணமாக வேலைக்குச் செல்ல இயலாத நிலையில் உள்ளதாலும், ஆதரவளிக்க மகன், மகள் எவரும் இல்லாததாலும், வாழ்வாதாரத்திற்கு அரசின் சமூக பாதுகாப்பு திட்டத்தின் கீழ் முதியோர் உதவித்தொகை (Old Age Pension) வழங்கிடக் கோரி மனு அளித்துள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'}, unable to work due to advanced age and ill health with no family support, has requested financial assistance / Old Age Pension (OAP) under the government Social Security Schemes."
        elif "குடிநீர்" in (detected_category + " " + doc_text) or "தண்ணீர்" in (detected_category + " " + doc_text) or "water" in doc_text.lower():
            loc_str = f"{loc} பகுதியில்" if loc else "பகுதியில்"
            summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}, {loc_str} போதிய குடிநீர் விநியோகம் இல்லாததால், முறையான குடிநீர் இணைப்பு வழங்கி தினசரி தடையின்றி குடிநீர் விநியோகம் செய்யுமாறு உரிய நடவடிக்கை கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} has requested proper drinking water connection and regular daily water supply in {loc or 'the area'}."
        elif "தெருவிளக்கு" in detected_category or "street light" in doc_text.lower() or "தெருவிளக்கு" in doc_text:
            loc_str = f"{loc} பகுதியில்" if loc else "பகுதியில்"
            summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}, {loc_str} பழுதடைந்து எரியாமல் உள்ள தெருவிளக்குகளை ஆய்வு செய்து புதிய விளக்குகள் பொருத்தி சீரமைத்து தருமாறு உரிய நடவடிக்கை கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} has requested inspection and repair of damaged street lights in {loc or 'the area'}."
        elif "வடிகால்" in (detected_category + " " + doc_text) or "கழிவுநீர்" in (detected_category + " " + doc_text) or "drain" in doc_text.lower():
            loc_str = f"{loc} பகுதியில்" if loc else "பகுதியில்"
            summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}, {loc_str} கழிவுநீர் மற்றும் மழைநீர் தேங்கி சுகாதாரக் கேடு ஏற்படுவதால், அடைபட்டுள்ள வடிகால்களைத் தூர்வாரி புதிய வடிகால் வசதி அமைத்துத் தருமாறு உரிய நடவடிக்கை கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} has requested desilting of clogged drains and construction of new drainage facilities in {loc or 'the area'} to prevent sewage stagnation."
        elif any(k in (detected_category + " " + doc_text).lower() for k in ["சாலைப்பணி", "சாலை பணி", "சாலை சீரமைப்பு", "சாலை பராமரிப்பு", "விபத்து அபாயம்"]):
            loc_str = f"{loc} பகுதியில்" if loc else "பகுதியில்"
            summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}, {loc_str} சாலை பணிகளால் ஏற்படும் விபத்து அபாயத்தைத் தடுத்து, தகுந்த எச்சரிக்கைப் பலகைகள் / வேகத்தடைகள் அமைத்து சாலையை விரைந்து சீரமைக்க உரிய நடவடிக்கை கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} has requested necessary road safety measures, warning signs/speed breakers, and expeditious completion of road works in {loc or 'the area'} to prevent accidents."
        else:
            parts = []
            if pet_name:
                parts.append(f"மனுதாரர் {pet_name}")
            else:
                parts.append("மனுதாரர்")
            if loc:
                parts.append(f"{loc} பகுதி")
            if surv:
                parts.append(f"புல எண் {surv} சார்ந்து")
            parts.append(f"{detected_category} தொடர்பாக நடவடிக்கை கோரியுள்ளார்.")
            summary_ta = " ".join(parts)
            summary_en = f"Petitioner {pet_name or 'Applicant'} has requested administrative action regarding {detected_category} in {loc or 'the district'}."

        return {
            "grievance_type": f_gtype,
            "grievance_subtype": f_gsub,
            "department": dept,
            "sub_department": f_subdept,
            "responsible_officer": f_respoff,
            "priority": "MEDIUM",
            "description_summary_tamil": summary_ta,
            "description_summary_english": summary_en,
            "action_items": [
                {"action": f"சம்பந்தப்பட்ட {dept} அலுவலர் மனு மீது உரிய பரிசீலனை மேற்கொள்ளுதல்", "department": dept, "deadline_hint": "15 நாட்கள்"},
                {"action": "மனு மீது உரிய தீர்வு காண உத்தரவு பிறப்பித்தல்", "department": dept, "deadline_hint": "30 நாட்கள்"}
            ],
            "claims": [
                {"text": summary_ta[:100], "source_page": 1, "confidence": 0.95}
            ],
            "hallucination_score": 0.0,
            "grounding_score": 1.0
        }

    async def resolve_classification(
        self,
        doc_context: str,
        zone_a: str = "",
        zone_b: str = "",
        initial_gtype: str = "",
        initial_gsub: str = "",
        initial_dept: str = "",
        tax_row: Optional[Dict[str, Any]] = None,
        gdp_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Authoritative CM Grievance Taxonomy Resolution:
        1. Segment zones if not provided
        2. Dynamic multi-signal vector retrieval against 1,847 DB embeddings
        3. Ambiguity detection & conditional LLM validation (Top-3 candidates)
        4. Authoritative DB taxonomy lookup from cm_taxonomy_mappings
        5. Fallback legacy keyword routing ONLY when tax_row is None
        6. Return strictly resolved department, type, subtype, and taxonomy_id
        """
        if not zone_a or not zone_b:
            zones = segment_petition_zones(doc_context)
            zone_a = zones.get("zone_a_header", "")
            zone_b = zones.get("zone_b_body", "")

        gdp_meta = gdp_meta or {}
        p_dept = initial_dept or "General Administration"
        p_gtype = initial_gtype or "General Grievance"
        p_gsub = initial_gsub or "Public Grievance Redressal"
        p_subdept = None
        p_resp_off = None

        sem_cls = None
        try:
            sem_cls = await semantic_classifier.classify_with_rerank(
                zone_a_header=zone_a,
                zone_b_body=zone_b,
                full_doc_text=doc_context,
                llm_client=self.llm,
            )
            is_generic = (p_gtype in ["General Grievance", "பொது குறை", ""] or p_gsub in ["Public Grievance Redressal", "பொது", ""])
            if (not tax_row or is_generic) and sem_cls:
                if sem_cls.get("classification_status") == "ambiguous":
                    tax_row = None
                    p_dept = "General Administration"
                    p_gtype = "Ambiguous / Needs Manual Review"
                    p_gsub = "Ambiguous Classification"
                    p_subdept = "General Administration / பொது நிர்வாகம்"
                    p_resp_off = "துறை அலுவலர்"
                    logger.info("⚠️ Multi-candidate ambiguity detected: safely marked for manual review")
                elif sem_cls.get("taxonomy_id"):
                    top_id = sem_cls["taxonomy_id"]
                    tax_row = taxonomy_matcher.get_taxonomy_by_id(top_id)
                    if tax_row:
                        p_dept = tax_row["department"]
                        p_gtype = tax_row["grievance_type"]
                        p_gsub = tax_row["grievance_sub_type"]
                        p_subdept = tax_row.get("sub_department") or p_subdept
                        if not gdp_meta.get("responsible_officer") and tax_row.get("responsible_officer"):
                            p_resp_off = tax_row["responsible_officer"]
                        logger.info(f"🎯 Assigned top multi-signal DB taxonomy ID {top_id}: dept='{p_dept}', type='{p_gtype}', sub='{p_gsub}'")
            elif tax_row:
                p_dept = tax_row["department"]
                p_gtype = tax_row["grievance_type"]
                p_gsub = tax_row["grievance_sub_type"]
                p_subdept = tax_row.get("sub_department") or p_subdept
                if not gdp_meta.get("responsible_officer") and tax_row.get("responsible_officer"):
                    p_resp_off = tax_row["responsible_officer"]
                logger.info(f"✅ Authoritative DB taxonomy confirmed from selection: ID {tax_row['id']} ('{p_dept}' - '{p_gsub}')")
        except Exception as sem_err:
            logger.debug(f"Semantic taxonomy resolution note: {sem_err}")

        # CRITICAL FIX 2: NEVER overwrite a valid DB taxonomy with legacy keyword routing.
        if tax_row is None and p_gtype != "Ambiguous / Needs Manual Review":
            logger.info("ℹ️ No authoritative DB taxonomy resolved; executing fallback legacy keyword routing")
            if any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in [
                "dwps", "ஆதரவற்ற விதவை", "விதவை உதவி", "விதவை ஓய்வூதியம்", "destitute widow", "widow pension",
                "முதியோர்", "oap", "old age pension", "வயது மூப்பு", "முதியவர்",
                "வேலைக்கு செல்ல முடியவில்லை", "மகனோ, மகளோ உதவி இல்லை", "differently abled", "மாற்றுத்திறனாளி"
            ]) and not any(w in doc_context.lower() for w in ["கல்வி", "scholarship", "கல்லூரி", "மாணவர்", "மாணவி", "பள்ளி", "படிப்பு"]):
                if any(w in (p_gtype + " " + p_gsub + " " + doc_context).lower() for w in ["விதவை", "widow", "dwps", "ஆதரவற்ற விதவை"]):
                    p_dept = "Revenue and Disaster Management (REV)"
                    p_gtype = "Destitute Widow Pension Scheme (DWPS) / Social Security Schemes"
                    p_gsub = "Destitute Widow Pension (DWP)"
                    p_subdept = "Social Security Schemes (SSS) / Revenue Administration"
                    p_resp_off = "Special Tahsildar (SSS) / Tahsildar"
                elif any(w in (p_gtype + " " + p_gsub + " " + doc_context).lower() for w in ["differently abled", "மாற்றுத்திறனாளி", "ஊனம்", "dap"]):
                    p_dept = "Revenue and Disaster Management (REV)"
                    p_gtype = "Social Security Schemes (SSS)"
                    p_gsub = "Differently Abled Pension (DAP)"
                    p_subdept = "Social Security Schemes (SSS) / Revenue Administration"
                    p_resp_off = "Special Tahsildar (SSS) / Tahsildar"
                elif any(w in (p_gtype + " " + p_gsub + " " + doc_context).lower() for w in ["முதியோர்", "oap", "old age", "வயது மூப்பு", "முதியவர்"]):
                    p_dept = "Revenue and Disaster Management (REV)"
                    p_gtype = "Social Security Schemes (SSS)"
                    p_gsub = "Old Age Pension (OAP)"
                    p_subdept = "Social Security Schemes (SSS) / Revenue Administration"
                    p_resp_off = "Special Tahsildar (SSS) / Tahsildar"
            elif any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["free hsd", "hsd", "house site", "வீட்டு மனை", "natham patta"]):
                p_dept = "Revenue and Disaster Management (REV)"
                p_gtype = "Natham Patta /Free House Site Patta"
                p_gsub = "Natham Patta /Free House Site Patta"
                p_subdept = "Revenue Administration / நில நிர்வாகம்"
                p_resp_off = "Tahsildar, Erode"
            elif any(k in doc_context for k in ["வழி ஆக்கிரமிப்பு", "பாதை ஆக்கிரமிப்பு", "போக வழி", "ஆக்கிரமிப்பை அகற்ற"]) and ("ஆக்கிரமிப்பு" not in p_gtype):
                if "பட்டா" in p_gtype or p_gtype in ["பொது குறை", "நிலம்", "பொது"]:
                    p_gtype = "நில ஆக்கிரமிப்பு அகற்றுதல்"
                    p_gsub = "பொதுப்பாதை / வழிப்பாதை ஆக்கிரமிப்பு அகற்றுதல்"
            elif any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["குடிநீர்", "தண்ணீர்", "குடிநீர் இணைப்பு", "drinking water", "water connection", "water supply"]):
                if any(p in doc_context for p in ["பஞ்சாயத்து", "ஊராட்சி ஒன்றிய", "ஊராட்சி", "கிராம ஊராட்சி"]):
                    p_dept = "Rural Development and Panchayat Raj Department (RDPR)"
                    p_gtype = "Village Infrastructure"
                    p_gsub = "Drinking Water Supply - RD"
                    p_subdept = "Rural Development and Panchayat Raj"
                    p_resp_off = "Block Development Officer - Village Panchayat"
                else:
                    p_dept = "Municipal Administration and Water Supply (MAWS)"
                    p_gtype = "Drinking Water"
                    has_water_conn = any(w in doc_context for w in [
                        "குடிநீர் இணைப்பு", "புதிய இணைப்பு", "வீட்டு இணைப்பு", "குழாய் இணைப்பு", 
                        "water connection", "new connection", "household water connection"
                    ])
                    p_gsub = "New Water Connection - Household Water Connection" if has_water_conn else "Insufficient Water Supply"
                    p_subdept = "Commissionerate of Municipal Administration (CMA)"
                    p_resp_off = "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
            elif any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["தெருவிளக்கு", "street light", "விளக்குகள்", "மின்விளக்கு", "பழுதடைந்த தெருவிளக்கு"]):
                if any(p in doc_context for p in ["பஞ்சாயத்து", "ஊராட்சி", "கிராம"]):
                    p_dept = "Rural Development and Panchayat Raj Department (RDPR)"
                    p_gtype = "Village Infrastructure"
                    p_gsub = "Street Light - RD"
                    p_subdept = "Rural Development and Panchayat Raj"
                    p_resp_off = "Block Development Officer - Village Panchayat"
                else:
                    p_dept = "Municipal Administration and Water Supply (MAWS)"
                    p_gtype = "Street Lights - MAWS"
                    p_gsub = "Street Lights - MAWS"
                    p_subdept = "Commissionerate of Municipal Administration (CMA)"
                    p_resp_off = "Commissioner Municipal Corporation / Municipality, Erode"
            elif any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["கழிவுநீர்", "வடிகால்", "சாக்கடை", "drainage", "storm water", "sewage", "தூர்வார"]):
                if any(p in doc_context for p in ["பஞ்சாயத்து", "ஊராட்சி ஒன்றிய"]):
                    p_dept = "Rural Development and Panchayat Raj Department (RDPR)"
                    p_gtype = "Village Infrastructure"
                    p_gsub = "Drainage and Sewage Issues"
                    p_subdept = "Rural Development and Panchayat Raj"
                    p_resp_off = "Block Development Officer - Village Panchayat"
                else:
                    p_dept = "Municipal Administration and Water Supply (MAWS)"
                    p_gtype = "Storm Water Drains - MAWS"
                    p_gsub = "Storm Water Drains - MAWS"
                    p_subdept = "Commissionerate of Municipal Administration (CMA)"
                    p_resp_off = "Commissioner Municipal Corporation / Municipality, Erode"
            elif any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["scholarship", "கல்வி உதவி", "கல்வி உதவித்தொகை", "கல்லூரி படிப்பு", "பல்கலைக்கழக"]):
                if "higher education" not in (p_dept or "").lower() and "social justice" not in (p_dept or "").lower() and "minorities" not in (p_dept or "").lower():
                    p_dept = "Higher Education Department (HIGHEDU)"
                p_gtype = "Scholarship - High Edu"
                p_gsub = "Scholarship - High Edu"
                p_subdept = "Director Of Collegiate Education"
                p_resp_off = "Joint Director of Collegiate Education"
            elif (
                any(k in (p_gtype + " " + p_gsub).lower() for k in ["aadhar", "aadhaar", "tactv", "esevai", "ceg", "information technology"]) or
                any(k in doc_context.lower() for k in ["ஆதார் திருத்தம்", "ஆதார் அட்டை பெயர் மாற்றம்", "ஆதார் பதிவு", "ஆதார் சேர்க்கை", "இ-சேவை மையம்", "esevai center", "aadhaar enrolment", "aadhaar correction"])
            ):
                if "information technology" not in (p_dept or "").lower():
                    p_dept = "Information Technology Department (IT)"
                    p_gtype = "Application Related Complaints - CeG"
                    p_gsub = "eSevai - Complaint related to Aadhaar Enrolment"
                    p_subdept = "Commissionerate of eGovernance/Tamil Nadu e-Governance Agency"
                    p_resp_off = "e-sevai helpdesk"

        return {
            "department": p_dept,
            "department_code": tax_row.get("department_code", "") if tax_row else (sem_cls.get("department_code") if sem_cls else ""),
            "grievance_type": p_gtype,
            "grievance_sub_type": p_gsub,
            "sub_department": p_subdept,
            "responsible_officer": p_resp_off,
            "taxonomy_id": tax_row["id"] if tax_row else (sem_cls.get("taxonomy_id") if sem_cls else None),
            "classification_status": sem_cls.get("classification_status") if sem_cls else ("resolved" if tax_row else "ambiguous"),
            "tax_row": tax_row,
            "sem_cls": sem_cls,
        }

    async def analyze(self, db: AsyncSession, source_id: str) -> Dict[str, Any]:
        """
        Comprehensive document analysis using full high-fidelity OCR text:
        1. Fetch all OCR pages from ocr_results (produced by Datalab Chandra OCR)
        2. Prompt LLM for complete structured extraction (petitioner info, full address, hierarchy, grievance, summary)
        3. Upsert grievance_drafts with exact extracted values
        4. Populate extracted_entities table
        """
        # 1. Gather all OCR pages text
        ocr_res = await db.execute(text("""
            SELECT page_number, full_text FROM ocr_results
            WHERE source_id = :source_id
            ORDER BY page_number
        """), {"source_id": source_id})
        pages = ocr_res.mappings().all()

        if pages:
            context_parts = []
            for p in pages:
                p_num = p['page_number']
                raw_t = (p['full_text'] or "").strip()
                if not raw_t:
                    continue
                # Normalize Hindi/Devanagari OCR artifacts (e.g. ईரோடு -> ஈரோடு)
                clean_t = raw_t.replace("\u0908", "\u0B88")

                # Filter out court fee stamp noise if page is predominantly Malayalam characters
                malayalam_count = len(re.findall(r'[\u0D00-\u0D7F]', clean_t))
                if p_num == 1 and len(clean_t) > 50 and (malayalam_count / len(clean_t)) > 0.35:
                    # Keep only non-Malayalam lines (such as date, phone number, stamps)
                    filtered_lines = [l for l in clean_t.split("\n") if not re.search(r'[\u0D00-\u0D7F]{3,}', l) and l.strip()]
                    clean_t = "\n".join(filtered_lines)

                if clean_t.strip():
                    context_parts.append(f"--- பக்கம் {p_num} ---\n{clean_t}")

            # Intelligent Multi-Page Context Budgeting:
            # Preserve Page 1 (header/salutation), intermediate narrative, and Final Page (signature/prayer)
            if len(context_parts) <= 2:
                doc_context = "\n\n".join(context_parts)[:3200]
            else:
                first_p = context_parts[0][:1200]
                last_p = context_parts[-1][:1200]
                middle_pages = "\n\n".join(context_parts[1:-1])[:1000]
                doc_context = f"{first_p}\n\n{middle_pages}\n\n{last_p}"
        else:
            doc_context = ""

        # Gather any regex pre-extracted entities (e.g. phone, aadhaar)
        ent_result = await db.execute(text("""
            SELECT entity_type, entity_value, source_page FROM extracted_entities 
            WHERE source_id = :source_id
            ORDER BY source_page ASC, confidence DESC
        """), {"source_id": source_id})
        existing_entities: List[Dict[str, Any]] = [dict(e) for e in ent_result.mappings().all()]
        existing_entity_dict = {e["entity_type"]: e["entity_value"] for e in existing_entities}

        # Stage-C verified deterministic entities (read-only context for LLM)
        verified_entity_dict = {}
        for e in existing_entities:
            etype = e.get("entity_type")
            eval_ = e.get("entity_value")
            if etype in ["phone", "alternate_phone", "survey_no", "file_number", "petition_no", "date_dmy", "pincode", "aadhaar"] and eval_:
                verified_entity_dict[etype] = eval_

        verified_entities_json = json.dumps(verified_entity_dict, ensure_ascii=False)

        # 1. Zonal Segmentation to isolate Header (Zone A), Body (Zone B), and Accused (Zone C)
        zones = segment_petition_zones(doc_context)
        zone_a = zones.get("zone_a_header", "")
        zone_b = zones.get("zone_b_body", "")
        zone_c = zones.get("zone_c_accused", "")

        # Strict extraction of petitioner phone, parent name, applicant name, and complainant signatory from Zone A / doc_context
        phone_from_zone_a = extract_petitioner_phone(zone_a)
        header_ents = extract_header_entities(zone_a, doc_context)
        header_father = header_ents.get("father_husband_name")
        header_petitioner = header_ents.get("petitioner_name")
        header_signatory = header_ents.get("complainant_signatory")
        gdp_meta = extract_gdp_form_metadata(doc_context)

        # 3. Clean and normalize helper functions
        INVALID_VALUES = {
            "null", "none", "n/a", "தெரியவில்லை", "இல்லை", "விண்ணப்பதாரர் பெயர்",
            "தந்தை அல்லது கணவர் பெயர்", "முழு முகவரி", "கிராமம்", "வட்டம்", "மாவட்டம்",
            "நான்", "நாங்கள்", "அவர்கள்", "இவர்", "மனுதாரர்", "விண்ணப்பதாரர்", "பொதுமக்கள்",
            "-", "--", "none", "unknown", "[தகவல் இல்லை]",
            "மாவட்ட ஆட்சியர்", "மாவட்ட ஆட்சியர் அவர்கள்", "மாவட்ட ஆட்சித்தலைவர்", "ஆட்சியர்",
            "வட்டாட்சியர்", "கோட்டாட்சியர்", "வருவாய் கோட்டாட்சியர்", "வருவாய் அலுவலர்", "முதலமைச்சர்",
            "அரசு செயலாளர்", "காவல் கண்காணிப்பாளர்", "துணை ஆட்சியர்", "DRO", "தாசில்தார்",
            "ஆணையர்", "அலுவலர்", "அலுவலர் அவர்கள்", "பெறுநர்", "பெறுநர்:", "பெறநர்", "பெறநர்:",
            "அனுப்புநர்", "அனுப்புநர்:", "நாள்", "தேதி", "Date", "DATE", "ந.க", "கடித எண்"
        }

        def clean_field(val: Any) -> Optional[str]:
            if not val or not isinstance(val, str):
                return None
            s = val.strip()
            if s.lower() in INVALID_VALUES or s.startswith("[தகவல்") or "அல்லது null" in s or s in ["-", "--"]:
                return None
            if any(auth in s for auth in [
                "மாவட்ட ஆட்சியர்", "ஆட்சியர் அவர்கள்", "ஆட்சியர்", "வட்டாட்சியர்", "கோட்டாட்சியர்",
                "வருவாய் கோட்டாட்சியர்", "வருவாய் அலுவலர்", "அலுவலர்", "முதலமைச்சர்", "அரசு செயலாளர்",
                "காவல் கண்காணிப்பாளர்", "துணை ஆட்சியர்", "DRO", "தாசில்தார்", "பெறுநர்", "பெறநர்", "அவர்களுக்கு"
            ]):
                return None
            if re.match(r'^\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}$', s) or s in ["நாள்", "தேதி"]:
                return None
            return s

        # Ensure dynamic master taxonomy is loaded from DB if not already initialized
        if not taxonomy_matcher.taxonomy:
            try:
                await taxonomy_matcher.load_taxonomy()
            except Exception as tex_err:
                logger.debug(f"Taxonomy auto-load notice: {tex_err}")

        # 1. Fast Dynamic DB Taxonomy Classification (runs in ~25ms against 1,847 DB embeddings)
        pre_classification = semantic_classifier.classify(
            zone_a_header=zone_a or "",
            zone_b_body=zone_b or "",
            full_doc_text=doc_context or "",
            top_k=5
        )
        pre_tax_id = pre_classification.get("taxonomy_id")
        is_ambiguous = pre_classification.get("is_ambiguous", False)
        auth_taxonomy = None
        if not is_ambiguous and pre_tax_id:
            auth_taxonomy = taxonomy_matcher.get_taxonomy_by_id(pre_tax_id)
            if not auth_taxonomy and pre_classification.get("candidates"):
                for c in pre_classification["candidates"]:
                    if c.get("taxonomy_id") == pre_tax_id or c.get("Taxonomy_ID") == pre_tax_id:
                        auth_taxonomy = c
                        break
            if not auth_taxonomy and pre_classification.get("department"):
                auth_taxonomy = {
                    "id": pre_tax_id,
                    "taxonomy_id": pre_tax_id,
                    "department": pre_classification.get("department", ""),
                    "department_code": pre_classification.get("department_code", ""),
                    "grievance_type": pre_classification.get("grievance_type", ""),
                    "grievance_sub_type": pre_classification.get("grievance_subtype") or pre_classification.get("grievance_sub_type", ""),
                    "sub_department": pre_classification.get("sub_department", ""),
                    "responsible_officer": pre_classification.get("responsible_officer", ""),
                }

            if auth_taxonomy:
                dept_name = auth_taxonomy.get("department") or auth_taxonomy.get("Department") or ""
                sub_type = auth_taxonomy.get("grievance_sub_type") or auth_taxonomy.get("grievance_subtype") or auth_taxonomy.get("Grievance Sub Type") or ""
                logger.info(f"🎯 Decisive DB taxonomy pre-resolved: ID={pre_tax_id} ('{dept_name}' - '{sub_type}')")
                top_candidates = pre_classification.get("candidates", [])[:5]
            else:
                top_candidates = pre_classification.get("candidates", [])[:5]
                is_ambiguous = True
                logger.warning(f"⚠️ Pre-classification suggested ID={pre_tax_id} but record could not be resolved. Scoping Top-5 candidates for LLM.")
        else:
            top_candidates = pre_classification.get("candidates", [])[:5]
            logger.info(f"⚖️ Ambiguity detected in DB pre-classification (margin={pre_classification.get('margin', 0):.4f}). Scoping Top-5 candidates for LLM.")

        fallback_analysis = self._build_grounded_fallback(doc_context, existing_entities)

        # 2. Compact Structured LLM Prompt (Focused entity extraction only, no 400-token summaries)
        prompt = prompt_builder.build_analysis_prompt(
            zone_a_header=zone_a or doc_context[:400],
            zone_b_body=zone_b or doc_context[400:1000],
            authoritative_taxonomy=auth_taxonomy,
            candidates=top_candidates if is_ambiguous else None
        )

        fast_timeout = float(getattr(settings, "LLM_FAST_TIMEOUT", 75.0))
        llm_data: Dict[str, Any] = {}
        raw_response = ""

        # 2a. Check AI Semantic Cache (bypasses LLM in ~30ms if >=0.92 cosine match found and enabled)
        try:
            from services.semantic_cache import semantic_cache
            cache_hit = await semantic_cache.lookup(db, prompt, source_id=source_id)
            if cache_hit and cache_hit.get("data"):
                logger.info(
                    f"⚡ [SEMANTIC CACHE HIT] Bypassing LLM for source {source_id}: "
                    f"{cache_hit.get('cache_type')} (sim={cache_hit.get('similarity')}, "
                    f"cache_id={cache_hit.get('cache_id')})"
                )
                llm_data = cache_hit["data"]
        except Exception as c_err:
            logger.debug(f"Semantic cache lookup note: {c_err}")

        if not llm_data:
            try:
                logger.info(f"🤖 Sending document ({len(doc_context)} chars) to LLM for extraction (timeout={fast_timeout}s)...")
                llm_max_t = min(getattr(settings, "LLM_MAX_TOKENS", 320), 320)
                # HTTP timeout must exceed asyncio.wait_for timeout so the coroutine
                # cancellation (from wait_for) fires first, ensuring clean shutdown.
                http_timeout = fast_timeout + 15.0
                raw_response = await asyncio.wait_for(
                    self.llm.achat(prompt, system_prompt=SYSTEM_PROMPT_COGNITIVE, temperature=0.1, max_tokens=llm_max_t, json_mode=True, timeout=http_timeout),
                    timeout=fast_timeout
                )
                parsed = extract_json_object(raw_response)
                if parsed and isinstance(parsed, dict):
                    llm_data = parsed
                    logger.info(f"✅ LLM successfully extracted details for petitioner: {llm_data.get('Petitioner_Name') or llm_data.get('petitioner_name')}")
                    # Asynchronously populate semantic cache
                    try:
                        from services.semantic_cache import semantic_cache
                        await semantic_cache.store(db, prompt, parsed)
                    except Exception as s_err:
                        logger.debug(f"Semantic cache store notice: {s_err}")
            except asyncio.TimeoutError:
                logger.warning(f"Notice: LLM extraction timed out after {fast_timeout}s. Utilizing fallback grounding.")
                llm_data = fallback_analysis
            except Exception as e:
                logger.warning(f"Notice: LLM extraction returned error: {repr(e)}. Utilizing fallback grounding.", exc_info=True)
                llm_data = fallback_analysis

        # Extract & prioritize Zone A applicant name / verified Stage-C entities, falling back to LLM values
        cand_llm_name = clean_field(llm_data.get("Petitioner_Name")) or clean_field(llm_data.get("petitioner_name"))
        if cand_llm_name:
            norm_doc = re.sub(r'[\s\.\,\(\)\-\:\'\"]', '', doc_context).lower()
            norm_cand = re.sub(r'[\s\.\,\(\)\-\:\'\"]', '', cand_llm_name).lower()
            # If cand_llm_name does not appear in doc_context, reject hallucination!
            if norm_cand not in norm_doc and not any(t in norm_doc for t in re.split(r'[\s\.]', cand_llm_name) if len(t) >= 3):
                logger.warning(f"Rejecting ungrounded LLM petitioner name hallucination: '{cand_llm_name}'")
                cand_llm_name = None

        p_name = (
            clean_field(header_petitioner) or
            clean_field(verified_entity_dict.get("petitioner_name")) or
            clean_field(existing_entity_dict.get("petitioner_name")) or
            cand_llm_name
        )
        if p_name:
            p_name = re.sub(r'[\(\)0-9#*]', '', p_name).strip(',.-: ')
            if len(p_name) < 2 or p_name.lower() in INVALID_VALUES:
                p_name = None

        # Dual-Applicant Complainant Signatory extraction (e.g. S. செல்வி on behalf of தர்ஷிதன் சா.)
        p_complainant = (
            clean_field(header_signatory) or
            clean_field(llm_data.get("Complainant_Signatory")) or
            clean_field(llm_data.get("complainant_signatory"))
        )
        if p_complainant:
            p_complainant = re.sub(r'[\(\)0-9#*]', '', p_complainant).strip(',.-: ')
            if is_same_person_or_invalid(p_complainant, p_name):
                if p_complainant and not any(skip in p_complainant for skip in INVALID_VALUES):
                    # If complainant/signatory has initials at the front (e.g. ச. க. பிரித்தி) and p_name has trailing (பிரித்தி . க)
                    if re.search(r'^[A-Za-z\u0B80-\u0BFF][\.\s]+', p_complainant) or len(p_complainant) >= len(p_name or ""):
                        p_name = p_complainant
                p_complainant = None
            elif (
                len(p_complainant) < 2 or
                p_complainant.lower() in INVALID_VALUES or
                p_complainant == p_name
            ):
                p_complainant = None

        # Prioritize Zone A header parent match (e.g. த/பெ. சாமிநாதன் / த/பெ. துரைராஜ்)
        f_name = (
            header_father or
            clean_field(llm_data.get("Father_Husband_Name")) or
            clean_field(llm_data.get("father_husband_name")) or
            clean_field(existing_entity_dict.get("father_husband_name"))
        )
        if f_name:
            f_name = re.sub(r'^(?:s/o|s\.o|த/பெ|த\.பெ|w/o|w\.o|க/பெ|க\.பெ|ம/பெ|மகன்|மனைவி|தந்தை|கணவர்|காலஞ்சென்ற|Late)\s*[:\.\-]?\s*', '', f_name, flags=re.IGNORECASE).strip(',.-: ')
            f_name = re.sub(r'[\(\)0-9#*]', '', f_name).strip(',.-: ')
            if (
                len(f_name) < 2 or f_name.lower() in INVALID_VALUES or
                any(w in f_name for w in [
                    "தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது",
                    "தெரு", "நகர்", "ரோடு", "வட்டம்", "மாவட்டம்", "கிராமம்", "காலனி", "ஊராட்சி",
                    "பகுதி", "Street", "Road", "Nagar", "Village", "Taluk", "District",
                    "என்ற பெயரை", "பெயர் மாற்றம்", "ஆகிய நான்", "எனது மகன்", "எனது மகள்"
                ])
            ):
                f_name = header_father if header_father else None

        if f_name:
            norm_f = re.sub(r'[\s\.\,\(\)\-\:\'\"]', '', f_name).lower()
            norm_p = re.sub(r'[\s\.\,\(\)\-\:\'\"]', '', p_name or '').lower()
            norm_c = re.sub(r'[\s\.\,\(\)\-\:\'\"]', '', p_complainant or '').lower()
            if (
                f_name == p_name or f_name == p_complainant or
                (norm_p and norm_f == norm_p) or (norm_c and norm_f == norm_c) or
                f_name.strip() in (p_name or "") or
                ("murugan" in norm_f and "முருகன்" in (p_name or ""))
            ):
                f_name = None

        p_gender = clean_field(llm_data.get("Gender")) or clean_field(llm_data.get("gender")) or None

        # 1. Disambiguate Petitioner vs Father/Husband relationships:
        cand_wife = None
        cand_hubby = None
        wo_same = re.search(r'([^\n,:]+?)[^\S\r\n]+(?:w/o|w\.o|க/பெ|க\.பெ|மனைவி)[^\S\r\n]+([^\n,]+)', doc_context, re.IGNORECASE)
        if wo_same and wo_same.group(1).strip() and not any(wo_same.group(1).strip().startswith(h) for h in ["அனுப்புநர்", "அனுப்புதல்"]):
            cand_wife = re.sub(r'\(\d+\)|\d+', '', wo_same.group(1)).strip(',.-: ')
            cand_hubby = re.sub(r'[\(\)0-9]', '', wo_same.group(2)).strip(',.-: ')
        else:
            wo_multi = re.search(r'(?:^|\n)\s*([^\n:]+?)\s*\n+\s*(?:w/o|w\.o|க/பெ|க\.பெ|மனைவி)\s+([^\n,]+)', doc_context, re.IGNORECASE)
            if wo_multi:
                cw = wo_multi.group(1).strip()
                cw = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', cw).strip()
                cw = re.sub(r'\(\d+\)|\d+', '', cw).strip(',.-: ')
                if cw:
                    cand_wife = cw
                    cand_hubby = re.sub(r'[\(\)0-9]', '', wo_multi.group(2)).strip(',.-: ')

        if cand_hubby:
            cand_hubby = re.sub(r'^(?:w/o|w\.o|க/பெ|க\.பெ|மனைவி|கணவர்|காலஞ்சென்ற|Late)\s*[:\.\-]?\s*', '', cand_hubby, flags=re.IGNORECASE).strip(',.-: ')
            if any(w in cand_hubby for w in ["தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை"]):
                cand_hubby = None

        if cand_wife or cand_hubby:
            p_gender = "Female"
            if cand_hubby and (not f_name or f_name in INVALID_VALUES):
                f_name = cand_hubby
            if cand_wife and (not p_name or p_name in INVALID_VALUES or p_name == cand_hubby or (cand_hubby and cand_hubby in p_name) or any(t in (p_name or "") for t in ["ஆட்சியர்", "அலுவலர்", "கோட்டாட்சியர்", "DRO"])):
                p_name = cand_wife
            elif not p_name and cand_wife:
                p_name = cand_wife

        cand_son = None
        cand_father = None
        so_same = re.search(r'([^\n,:]+?)[^\S\r\n]+(?:s/o|s\.o|த/பெ|த\.பெ|ம/பெ|மகன்)[^\S\r\n]+([^\n,]+)', doc_context, re.IGNORECASE)
        if so_same and so_same.group(1).strip() and not so_same.group(1).strip().startswith("அனுப்புநர்"):
            cand_son = re.sub(r'\(\d+\)|\d+', '', so_same.group(1)).strip(',.-: ')
            cand_father = re.sub(r'\(\d+\)|\d+', '', so_same.group(2)).strip(',.-: ')
        else:
            so_multi = re.search(r'(?:^|\n)\s*([^\n:]+?)\s*\n+\s*(?:s/o|s\.o|த/பெ|த\.பெ|ம/பெ|மகன்)\s+([^\n,]+)', doc_context, re.IGNORECASE)
            if so_multi:
                cs = so_multi.group(1).strip()
                cs = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', cs).strip()
                cs = re.sub(r'\(\d+\)|\d+', '', cs).strip(',.-: ')
                if cs:
                    cand_son = cs
                    cand_father = re.sub(r'\(\d+\)|\d+', '', so_multi.group(2)).strip(',.-: ')

        if cand_father:
            cand_father = re.sub(r'^(?:s/o|s\.o|த/பெ|த\.பெ|ம/பெ|மகன்|தந்தை)\s*[:\.\-]?\s*', '', cand_father, flags=re.IGNORECASE).strip(',.-: ')
            if any(w in cand_father for w in ["தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது"]):
                cand_father = None

        if (cand_son or cand_father) and not (cand_wife or cand_hubby):
            if cand_son and any(w in cand_son for w in ["குடும்ப", "சேர்ந்தவன்", "சேர்ந்தவர்", "வசித்து", "வருகிறேன்"]):
                cand_son = None

            if cand_father and (not f_name or f_name in INVALID_VALUES):
                f_name = cand_father
                p_gender = "Male"
            if cand_son and (not p_name or p_name in INVALID_VALUES or p_name == cand_father or (cand_father and cand_father in p_name)):
                p_name = cand_son
                p_gender = "Male"
            elif not p_name and cand_son:
                p_name = cand_son
                p_gender = "Male"

        if not p_gender and p_name:
            clean_n = re.sub(r'^(?:[A-Za-z\u0B80-\u0BFF][\.\s]+)+', '', p_name).strip()
            clean_n = re.sub(r'(?:[\.\s]+[A-Za-z\u0B80-\u0BFF])+$', '', clean_n).strip()
            if any(clean_n.endswith(suffix) for suffix in ["தி", "வி", "தா", "யா", "மா", "ரி", "ள்", "அம்மாள்", "அம்மா", "மேரி", "பிரித்தி"]):
                p_gender = "Female"
            elif any(clean_n.endswith(suffix) for suffix in ["ன்", "ர்", "அன்", "குமார்", "ராஜா", "சாமி", "நாதன்", "வேல்"]):
                p_gender = "Male"

        # Signature fallback: Scan closing block (near இப்படிக்கு or last lines)
        idx_sig = doc_context.find("இப்படிக்கு")
        if idx_sig == -1:
            idx_sig = doc_context.find("இவண்")
        if idx_sig != -1:
            sig_block = doc_context[idx_sig:]
            found_sig = None
            sig_matches = re.finditer(r'\(\s*([A-Za-z\u0B80-\u0BFF\.\s]{2,35})\s*\)', sig_block)
            for sm in sig_matches:
                cand_sig = clean_field(sm.group(1).strip("() "))
                if (
                    cand_sig and len(cand_sig) >= 3 and not self.is_noisy_ocr_text(cand_sig) and
                    not any(skip in cand_sig for skip in ["TK", "Dt", "District", "Taluk", "Scholarship", "கணினி", "சான்றிதழ்", "நகல்", "பட்டியல்"])
                ):
                    found_sig = cand_sig
                    break
            if not found_sig:
                for sl in [l.strip() for l in sig_block.split("\n")[1:5] if l.strip()]:
                    cs = re.sub(r'\(\d+\)|\d+', '', sl).strip(',.-:() ')
                    if (
                        cs and 2 <= len(cs) <= 35 and cs not in INVALID_VALUES and
                        not any(cs.startswith(w) for w in ["தங்கள்", "உண்மையுள்ள", "வணக்கம்", "நன்றி", "நாள்", "தேதி", "செல்", "போன்"]) and
                        not any(skip in cs for skip in ["TK", "Dt", "District", "Taluk", "வட்டம்", "மாவட்டம்"])
                    ):
                        found_sig = cs
                        break
            if found_sig and (not p_name or p_name in INVALID_VALUES or p_name.startswith("ந.க") or any(auth in p_name for auth in ["மாவட்ட ஆட்சியர்", "ஆட்சியர்", "வட்டாட்சியர்"])):
                p_name = found_sig

        # Parse official GDP Form Metadata Table if present (e.g. Revenue Dept, Free HSD, Tahsildar, Erode)
        gdp_meta = extract_gdp_form_metadata(doc_context)

        sel_tax = llm_data.get("Selected_Taxonomy") if isinstance(llm_data.get("Selected_Taxonomy"), dict) else {}

        # Identifiers MUST come from Zone A / Stage-C verified entities; never accused section numbers
        phone_from_zone = extract_petitioner_phone(zone_a) or extract_petitioner_phone(doc_context)
        p_phone = (
            header_ents.get("phone_number") or
            phone_from_zone or
            clean_field(llm_data.get("Phone_Number")) or
            clean_field(llm_data.get("phone")) or
            verified_entity_dict.get("phone")
        )
        p_alt_phone = verified_entity_dict.get("alternate_phone") or clean_field(existing_entity_dict.get("alternate_phone"))
        p_survey = verified_entity_dict.get("survey_no") or clean_field(existing_entity_dict.get("survey_no"))
        
        # Reference ID: Check form metadata table (#18860075#) or verified petition number
        raw_ref_digits = (
            gdp_meta.get("ref_number") or
            verified_entity_dict.get("petition_no") or
            clean_field(llm_data.get("Reference_Number")) or
            clean_field(llm_data.get("ref_number")) or
            clean_field(existing_entity_dict.get("petition_no"))
        )
        if raw_ref_digits:
            raw_ref_digits = re.sub(r'\D', '', str(raw_ref_digits))

        p_door = header_ents.get("door_no") or clean_field(llm_data.get("door_no")) or clean_field(existing_entity_dict.get("door_no"))
        p_street = header_ents.get("street_name") or clean_field(llm_data.get("street_name")) or clean_field(existing_entity_dict.get("street_name"))
        p_village = (
            header_ents.get("village") or
            clean_field(llm_data.get("Village")) or
            clean_field(llm_data.get("village")) or
            clean_field(existing_entity_dict.get("village"))
        )
        p_firka = header_ents.get("firka") or clean_field(llm_data.get("firka")) or clean_field(existing_entity_dict.get("firka"))
        p_taluk = (
            header_ents.get("taluk") or
            clean_field(llm_data.get("Taluk")) or
            clean_field(llm_data.get("taluk")) or
            clean_field(existing_entity_dict.get("taluk"))
        )
        p_district = (
            header_ents.get("district") or
            clean_field(llm_data.get("District")) or
            clean_field(llm_data.get("district")) or
            clean_field(existing_entity_dict.get("district"))
        )
        if p_district:
            p_district = p_district.replace("\u0908", "\u0B88")
        p_pincode = verified_entity_dict.get("pincode") or clean_field(llm_data.get("pincode")) or clean_field(existing_entity_dict.get("pincode"))
        p_addr = (
            header_ents.get("address") or
            clean_field(llm_data.get("Address")) or
            clean_field(llm_data.get("full_address")) or
            existing_entity_dict.get("full_address") or
            existing_entity_dict.get("address")
        )
        if p_addr:
            p_addr = p_addr.replace("\u0908", "\u0B88")

        # Village extraction fallback from full address string / header (e.g. புஞ்சைபாலத் தொழுவு, கூரப்பாளையம்)
        if not p_village or p_village.lower() in INVALID_VALUES or p_village in ["-", "--"]:
            v_search = re.search(r'([A-Za-z\u0B80-\u0BFF\s]+(?:தொழுவு|மேடு|காடு|வலசு|பாளையம்|பளையம்|பட்டி|நகர்|புரம்|ஊர்|குப்பம்|கிராமம்|சேரி))', (p_addr or "") + " " + zone_a)
            if v_search:
                cand_v = clean_field(v_search.group(1).strip(":, "))
                if cand_v and len(cand_v) >= 3 and not any(skip in cand_v for skip in ["வட்டம்", "மாவட்டம்", "தெரு", "சாலை", "ரோடு"]):
                    p_village = cand_v

        # Only construct addr_segments if p_addr is completely missing
        if not p_addr:
            addr_segments = [s for s in [p_door, p_street, p_village, p_firka, p_taluk if p_taluk != p_village else None, p_district if p_district != p_taluk else None, f"Pin - {p_pincode}" if p_pincode else None] if s and s != "-"]
            if addr_segments:
                p_addr = ", ".join(addr_segments)

        # Parse & sanitize location to eliminate duplicate village repetition, preserve landmark streets, and properly map Taluk vs Village
        if p_addr:
            parsed_loc = parse_tamil_address_and_location(p_addr)
            p_addr = parsed_loc.get("full_address") or parsed_loc.get("address", p_addr)
            if parsed_loc.get("village") and parsed_loc["village"] != "Not found":
                p_village = parsed_loc["village"]
            if not p_taluk or p_taluk == p_village or p_taluk in INVALID_VALUES or p_taluk == "Not found":
                p_taluk = parsed_loc.get("taluk", p_district)
            if not p_district or p_district in INVALID_VALUES or p_district == "Not found":
                p_district = parsed_loc.get("district")

        def sanitize_loc(val: Optional[str]) -> Optional[str]:
            if not val or not isinstance(val, str):
                return val
            s = re.sub(r'[\(\[\{]?(?:TK|Tk|T\.K|வட்டம்|Po|PO|P\.O|அஞ்சல்|Dt|DT|D\.T|மாவட்டம்)[\)\]\}]?', '', val, flags=re.IGNORECASE).strip(' :,.-')
            return s if s else val

        p_village = sanitize_loc(p_village)
        p_taluk = sanitize_loc(p_taluk)
        p_district = sanitize_loc(p_district)

        # Dynamically resolve administrative hierarchy (Division, Taluk, Firka, District) from database-driven matcher
        loc_hier = location_matcher.match_hierarchy(
            address_text=p_addr or "",
            village=p_village,
            street=p_street,
            detected_taluk=p_taluk
        )
        p_rev_div = loc_hier.get("revenue_division") or (location_matcher.taluk_to_division.get(p_taluk) if p_taluk else None)
        if loc_hier.get("taluk"):
            p_taluk = loc_hier["taluk"]
        if loc_hier.get("firka"):
            p_firka = loc_hier["firka"]
        if loc_hier.get("district"):
            p_district = loc_hier["district"]

        # Resolve authoritative taxonomy:
        # If DB pre-classification was decisive, auth_taxonomy is already the authoritative source of truth
        tax_row = auth_taxonomy
        if not tax_row:
            sel_tax = llm_data.get("Selected_Taxonomy") or llm_data.get("selected_taxonomy") or {}
            sel_tax_id = llm_data.get("Selected_Taxonomy_ID") or sel_tax.get("Taxonomy_ID") or sel_tax.get("taxonomy_id")
            tax_row = taxonomy_matcher.get_taxonomy_by_id(sel_tax_id) if sel_tax_id else None

        # If LLM returned text instead of an integer ID, attempt matching against dynamic candidates
        if not tax_row and (llm_data.get("Selected_Taxonomy") or llm_data.get("selected_taxonomy")):
            sel_tax = llm_data.get("Selected_Taxonomy") or llm_data.get("selected_taxonomy") or {}
            s_dept = (sel_tax.get("Department") or "").strip().lower()
            s_type = (sel_tax.get("Grievance_Type") or "").strip().lower()
            s_sub = (sel_tax.get("Grievance_Sub_Type") or "").strip().lower()
            for cand in top_candidates:
                cand_sub = (cand.get("grievance_sub_type") or "").strip().lower()
                cand_type = (cand.get("grievance_type") or "").strip().lower()
                cand_dept = (cand.get("department") or "").strip().lower()
                if (s_sub and s_sub == cand_sub) or (s_type and s_type == cand_type and (s_dept in cand_dept or cand_dept in s_dept)):
                    tax_row = taxonomy_matcher.get_taxonomy_by_id(cand["taxonomy_id"]) or cand
                    break

        p_subdept = None
        sel_tax = llm_data.get("Selected_Taxonomy") or llm_data.get("selected_taxonomy") or {}
        p_resp_off = (
            (tax_row.get("responsible_officer") if tax_row else None) or
            clean_field(sel_tax.get("Responsible_officer")) or
            clean_field(sel_tax.get("responsible_officer")) or
            clean_field(llm_data.get("Responsible_officer")) or
            clean_field(llm_data.get("responsible_officer")) or
            None
        )

        # Grievance categorization prioritizing official GDP form metadata table
        p_gtype = (
            gdp_meta.get("grievance_type") or
            (tax_row.get("grievance_type") if tax_row else None) or
            clean_field(sel_tax.get("Grievance_Type")) or
            clean_field(llm_data.get("grievance_type")) or
            fallback_analysis["grievance_type"]
        )
        p_gsub = (
            gdp_meta.get("grievance_subtype") or
            (tax_row.get("grievance_sub_type") if tax_row else None) or
            clean_field(sel_tax.get("Grievance_Sub_Type")) or
            clean_field(llm_data.get("grievance_subtype")) or
            fallback_analysis["grievance_subtype"]
        )
        p_dept = (
            gdp_meta.get("department") or
            (tax_row.get("department") if tax_row else None) or
            taxonomy_matcher.normalize_department(
                clean_field(sel_tax.get("Department")) or
                clean_field(llm_data.get("department")) or
                fallback_analysis["department"]
            )
        ) or "General Administration"

        # ────────────────────────────────────────────────────────────────────
        # Authoritative Dynamic DB Taxonomy Classification & Resolution:
        # If not already decisively resolved from DB, execute multi-signal ranking.
        # ────────────────────────────────────────────────────────────────────
        cls_res: Dict[str, Any] = {}
        if not tax_row:
            cls_res = await self.resolve_classification(
                doc_context=doc_context,
                zone_a=zone_a,
                zone_b=zone_b,
                initial_gtype=p_gtype,
                initial_gsub=p_gsub,
                initial_dept=p_dept,
                tax_row=tax_row,
                gdp_meta=gdp_meta,
            )
            p_dept = cls_res["department"]
            p_gtype = cls_res["grievance_type"]
            p_gsub = cls_res["grievance_sub_type"]
            p_subdept = cls_res.get("sub_department") or p_subdept
            if not p_resp_off and cls_res.get("responsible_officer"):
                p_resp_off = cls_res["responsible_officer"]
            tax_row = cls_res.get("tax_row")
        else:
            p_dept = tax_row.get("department", p_dept)
            p_gtype = tax_row.get("grievance_type", p_gtype)
            p_gsub = tax_row.get("grievance_sub_type") or tax_row.get("grievance_subtype", p_gsub)
            p_subdept = tax_row.get("sub_department") or p_subdept
            p_resp_off = tax_row.get("responsible_officer") or p_resp_off

        p_subdept = (
            gdp_meta.get("sub_department") or
            (tax_row.get("sub_department") if tax_row else None) or
            clean_field(sel_tax.get("Sub_Department")) or
            clean_field(llm_data.get("sub_department")) or
            p_subdept or
            f"{p_dept} / நிர்வாகம்"
        )
        if tax_row is None and p_dept == "Municipal Administration and Water Supply (MAWS)" and "Drinking Water" in p_gtype:
            p_subdept = "Commissionerate of Municipal Administration (CMA)"
            p_resp_off = "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"

        p_priority = clean_field(llm_data.get("priority")) or "MEDIUM"

        # Format Reference ID
        dept_code = "REV" if "revenue" in (p_dept or "").lower() else ("IT" if "information technology" in (p_dept or "").lower() else ("RDPR" if "rural development" in (p_dept or "").lower() else ("MAWS" if "municipal" in (p_dept or "").lower() else "GAD")))
        subdept_code = "DRO" if dept_code == "REV" else ("TACTV" if dept_code == "IT" else ("BDO" if dept_code == "RDPR" else ("CMA" if dept_code == "MAWS" else "CELL")))
        date_code = gdp_meta.get("date_code", "24AUG26")
        if raw_ref_digits:
            p_ref_no = f"TN/{dept_code}/{subdept_code}/{date_code}/{raw_ref_digits}"
        else:
            p_ref_no = verified_entity_dict.get("file_number") or verified_entity_dict.get("petition_no") or clean_field(existing_entity_dict.get("file_number"))

        summary_ta = (
            clean_field(llm_data.get("Description")) or
            clean_field(llm_data.get("description_summary_tamil")) or
            fallback_analysis["description_summary_tamil"]
        )
        summary_en = clean_field(llm_data.get("description_summary_english")) or fallback_analysis["description_summary_english"]

        # Enforce formal third-person administrative Tamil summary and discard OCR noise
        OCR_JUNK_TOKENS = ["பிளூப்ரீவ்", "ப்ளூப்ரிண்ட்", "வட்டாராசிரியர்", "ராஷ்ட்ர கலா", "தோட்டாரன்", "டி. சி. பட்டணம்", "அடிசூ", "ஷாவ்", "ரயல்"]
        is_scholarship = (
            any(k in (p_gtype + " " + p_gsub).lower() for k in ["scholarship", "technical edu", "education", "கல்வி", "மாணவ"]) or
            any(k in doc_context.lower() for k in ["கல்வி உதவித்தொகை", "கல்வி உதவி", "scholarship", "கல்லூரி கட்டணம்", "பொறியியல் கல்லூரி"])
        )
        is_oap_elderly = (
            any(k in (p_gtype + " " + p_gsub).lower() for k in ["old age pension", "oap", "முதியோர்"]) or
            (any(k in doc_context.lower() for k in ["முதியோர்", "வயது மூப்பு", "முதியவர்", "மூத்த குடிமக்கள்", "oap", "old age"]) and not is_scholarship)
        )
        is_widow = any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["dwps", "dwp", "விதவை", "ஆதரவற்ற விதவை", "destitute widow", "widow pension"])
        is_dap = any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["dap", "மாற்றுத்திறனாளி", "differently abled", "ஊனம்"])
        is_road_work = any(k in (p_gtype + " " + p_gsub).lower() for k in ["road", "highway", "சாலை"]) or any(k in doc_context.lower() for k in ["சாலைப்பணி", "சாலை பணி", "சாலை பராமரிப்பு", "சாலை சீரமைப்பு", "விபத்து அபாயம்", "பழுதடைந்த சாலை", "தார் சாலை"])
        is_drinking_water = ("drinking water" in (p_gtype + " " + p_gsub).lower() or "குடிநீர்" in (p_gtype + " " + p_gsub)) and not is_road_work
        is_street_light = any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["தெருவிளக்கு", "street light", "விளக்குகள்", "மின்விளக்கு"])
        is_drainage = any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["கழிவுநீர்", "வடிகால்", "சாக்கடை", "drainage", "storm water", "sewage"]) and not is_road_work
        is_financial_help = any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["உதவித்தொகை", "நிதி உதவி", "நிதியுதவி", "financial assistance"])

        # General English administrative summary fallback if missing
        if not summary_en or summary_en == "Not found":
            summary_en = f"Petitioner {p_name or 'Applicant'} has requested official administrative action regarding {p_gsub or p_gtype}."

        tahsildar_match = None
        # Check for official Tahsildar / Office stamp in doc_context or metadata
        if gdp_meta.get("responsible_officer"):
            p_resp_off = gdp_meta["responsible_officer"]
        elif not p_resp_off:
            tahsildar_match = re.search(r'Tahsildar\s*,\s*([A-Za-z\u0B80-\u0BFF]+)', doc_context, re.IGNORECASE)
            if not tahsildar_match:
                tahsildar_match = re.search(r'([A-Za-z\u0B80-\u0BFF]+)\s*(?:வருவாய்\s*)?வட்டாட்சியர்', doc_context)

            if tahsildar_match:
                cand_taluk = tahsildar_match.group(1).strip()
                p_taluk = cand_taluk
                p_resp_off = f"வட்டாட்சியர், {cand_taluk}"
            else:
                p_resp_off = clean_field(llm_data.get("responsible_officer"))

        # Dynamic Alignment with official CM Helpline Grievance Taxonomy ONLY IF NO VALID TAXONOMY RESOLVED
        if tax_row is None:
            try:
                tax_match = taxonomy_matcher.match(
                    petition_text=f"{summary_ta} {summary_en} {doc_context[:300]}",
                    detected_type=p_gtype,
                    detected_subtype=p_gsub,
                    detected_dept=p_dept
                )
                if tax_match and tax_match.get("validated"):
                    p_dept = tax_match["department"]
                    p_gtype = tax_match["grievance_type"]
                    p_gsub = tax_match["grievance_subtype"]
                    if tax_match.get("sub_department"):
                        p_subdept = tax_match["sub_department"]
                    if tax_match.get("responsible_officer") and not tahsildar_match:
                        raw_off = tax_match["responsible_officer"]
                        if raw_off.lower() == "tahsildar":
                            p_resp_off = f"வட்டாட்சியர், {p_taluk}" if p_taluk else "வட்டாட்சியர்"
                        else:
                            p_resp_off = raw_off
            except Exception as e:
                logger.warning(f"Taxonomy alignment notice: {e}")

        if p_subdept:
            if "Commissionerate of Municipal Administration" in p_subdept or "CMA" in p_subdept:
                p_subdept = "Commissionerate of Municipal Administration (CMA)"
            elif "\n" in p_subdept:
                p_subdept = re.sub(r'\s+', ' ', p_subdept).strip()

        if p_resp_off:
            if "Commissioner Municipality" in p_resp_off or "Municipal Corporation" in p_resp_off:
                p_resp_off = "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
            elif "\n" in p_resp_off:
                p_resp_off = ", ".join(re.sub(r'[\r\n]+', ' ', l.strip().rstrip(',')) for l in p_resp_off.split("\n") if l.strip())

        # Master Location verification (Deterministic leaf-to-root validation)
        loc_status = "resolved"
        if p_village and p_village not in INVALID_VALUES and p_village != "Not found":
            try:
                # If taluk is already known, scope search by taluk to prevent cross-taluk collisions
                if p_taluk and p_taluk not in INVALID_VALUES and p_taluk != "Not found":
                    loc_res = await db.execute(text("""
                        SELECT district_name_tamil, taluk_name_tamil, division_name_tamil, firka_name_tamil, village_name_tamil
                        FROM master_locations
                        WHERE (village_name_tamil ILIKE :village OR search_text ILIKE :village_search)
                          AND taluk_name_tamil = :taluk
                    """), {"village": f"%{p_village}%", "village_search": f"%{p_village}%", "taluk": p_taluk})
                else:
                    loc_res = await db.execute(text("""
                        SELECT district_name_tamil, taluk_name_tamil, division_name_tamil, firka_name_tamil, village_name_tamil
                        FROM master_locations
                        WHERE village_name_tamil ILIKE :village OR search_text ILIKE :village_search
                    """), {"village": f"%{p_village}%", "village_search": f"%{p_village}%"})

                matched_rows = loc_res.mappings().all()
                if matched_rows:
                    taluk_set = {r["taluk_name_tamil"] for r in matched_rows if r.get("taluk_name_tamil")}
                    if len(taluk_set) == 1:
                        resolved_taluk = taluk_set.pop()
                        p_taluk = resolved_taluk
                        p_district = matched_rows[0]["district_name_tamil"] or p_district
                        p_rev_div = matched_rows[0]["division_name_tamil"] or p_rev_div

                        # Check firka agreement among matched village rows
                        firka_set = {r["firka_name_tamil"] for r in matched_rows if r.get("firka_name_tamil") and r["firka_name_tamil"] not in ["கிழக்கு", "மேற்கு", "வடக்கு", "தெற்கு"]}
                        if len(firka_set) == 1:
                            p_firka = firka_set.pop()
                    elif len(taluk_set) > 1 and not p_taluk:
                        loc_status = "ambiguous"
            except Exception as e:
                logger.warning(f"Master location village query notice: {e}")

        # Deterministic Taluk validation against master_locations (strictly 1-to-1 for District & Division)
        if p_taluk and p_taluk not in INVALID_VALUES and p_taluk != "Not found":
            try:
                taluk_res = await db.execute(text("""
                    SELECT DISTINCT district_name_tamil, taluk_name_tamil, division_name_tamil
                    FROM master_locations
                    WHERE taluk_name_tamil = :taluk
                """), {"taluk": p_taluk})
                taluk_match = taluk_res.mappings().one_or_none()
                if taluk_match:
                    p_district = taluk_match["district_name_tamil"] or p_district
                    p_rev_div = taluk_match["division_name_tamil"] or p_rev_div
                else:
                    # Taluk not found in master locations for district
                    loc_status = "ambiguous"
            except Exception as e:
                logger.warning(f"Master location taluk query notice: {e}")

        def sanitize_short_field(val: Any, max_len: int = 50) -> Optional[str]:
            if not val or val == "-":
                return None
            s = str(val).strip()
            for marker in ["பகுதி ", "வட்டம் ", "வட்டத்திற்குட்பட்ட ", "வசிக்கும் "]:
                if marker in s:
                    s = s.split(marker)[-1].strip()
            s = s.strip(" .,-()[]{}:;")
            return s[:max_len].strip() if len(s) > max_len else (s if s else None)

        p_district = sanitize_short_field(p_district, 50)
        p_village = sanitize_short_field(p_village, 50)
        p_taluk = sanitize_short_field(p_taluk, 50)

        # If taluk mistakenly identical to village, reset taluk to district headquarters
        if p_taluk and p_village and p_taluk == p_village:
            p_taluk = p_district

        # Final address cleaning to remove duplicate village repetitions
        if p_addr:
            parsed_loc = parse_tamil_address_and_location(p_addr)
            p_addr = parsed_loc.get("full_address") or parsed_loc.get("address", p_addr)

        # Dynamically resolve administrative hierarchy (Division, Taluk, Firka, Block)
        loc_hier_final = location_matcher.match_hierarchy(
            address_text=p_addr or "",
            village=p_village,
            street=p_street,
            detected_taluk=p_taluk
        )
        if not p_rev_div and loc_hier_final.get("revenue_division"):
            p_rev_div = loc_hier_final["revenue_division"]
        elif not p_rev_div and p_taluk:
            p_rev_div = location_matcher.taluk_to_division.get(p_taluk)

        if not p_firka and loc_hier_final.get("firka"):
            p_firka = loc_hier_final["firka"]
        if p_firka in ["கிழக்கு", "மேற்கு", "வடக்கு", "தெற்கு", "-", "--", "None", None] and p_taluk:
            p_firka = p_taluk

        # Deterministic Development Block resolution from database
        p_block = (
            loc_hier_final.get("block") or
            location_matcher.resolve_block(p_taluk, p_firka, p_village) or
            (f"{p_taluk} ஒன்றியம்" if p_taluk else "-")
        )

        p_ward = (
            loc_hier_final.get("ward") or
            verified_entity_dict.get("ward") or
            existing_entity_dict.get("ward") or
            clean_field(llm_data.get("ward"))
        )
        p_muni_ward = (
            loc_hier_final.get("municipality_ward") or
            verified_entity_dict.get("municipality_ward") or
            existing_entity_dict.get("municipality_ward") or
            clean_field(llm_data.get("municipality_ward"))
        )
        if loc_hier_final.get("local_body_type"):
            p_lbody = loc_hier_final["local_body_type"]
        else:
            p_lbody = sanitize_short_field(clean_field(llm_data.get("local_body_type")), 100) or "Village Panchayat"

        p_ward = sanitize_short_field(p_ward, 255)
        p_muni_ward = sanitize_short_field(p_muni_ward, 255)
        p_lbody = sanitize_short_field(p_lbody, 100)
        p_firka = sanitize_short_field(p_firka, 100)
        p_door = sanitize_short_field(p_door, 50)
        p_street = sanitize_short_field(p_street, 150)
        p_block = sanitize_short_field(p_block, 50)
        p_rev_div = sanitize_short_field(p_rev_div, 100)

        if not p_resp_off or p_resp_off == "வட்டாட்சியர்":
            if "revenue" in (p_dept or "").lower() or ("வருவாய்" in (p_dept or "")):
                p_resp_off = f"வட்டாட்சியர், {p_taluk}" if p_taluk else "வட்டாட்சியர்"
            else:
                p_resp_off = clean_field(sel_tax.get("Responsible_officer")) or clean_field(sel_tax.get("responsible_officer")) or "துறை அலுவலர்"
        p_resp_off = sanitize_short_field(p_resp_off, 150)

        # Preserve clean petitioner_name and avoid concatenating English signatory into Tamil name

        # Safeguard and sanitize taxonomy fields against runaway text / narrative sentences
        def sanitize_taxonomy_field(val: Any, default_val: Optional[str] = None, max_len: int = 120) -> Optional[str]:
            if not val or val == "-":
                return default_val
            s = str(val).strip()
            # Collapse any line-wraps from PDF table extraction into a single clean line
            s = re.sub(r'[\r\n\t]+', ' ', s).strip()
            s = re.sub(r'\s+', ' ', s)
            narrative_markers = [
                "கோருதல்", "வேண்டி", "குறித்து", "தொடர்பாக", "பொருள் :", "பொருள்:", 
                "விண்ணப்பம்", "நடவடிக்கை எடுக்க", "விபத்து அபாயம்", "சாலைப்பணிகளால்", "சாலைப் பணிகளால்"
            ]
            if len(s) > max_len or any(m in s for m in narrative_markers):
                logger.warning(f"Rejecting narrative sentence from taxonomy field: '{s[:60]}...' -> falling back to '{default_val}'")
                return default_val
            s = s.strip(" .,-:;")
            return s[:max_len].strip() if len(s) > max_len else (s if s else default_val)

        p_gtype = sanitize_taxonomy_field(p_gtype, default_val="General Grievance", max_len=100)
        p_gsub = sanitize_taxonomy_field(p_gsub, default_val="Public Grievance Redressal", max_len=100)
        p_dept = sanitize_taxonomy_field(p_dept, default_val="General Administration", max_len=100)
        p_subdept = sanitize_taxonomy_field(p_subdept, default_val=f"{p_dept} / நிர்வாகம்", max_len=100)
        p_name = (p_name or "")[:150].strip() or None
        f_name = (f_name or "")[:150].strip() or None
        p_father = f_name
        p_phone = (p_phone or "")[:20].strip() or None
        p_alt_phone = (p_alt_phone or "")[:20].strip() or None
        p_gender = (p_gender or "")[:20].strip() or None
        p_ref_no = (p_ref_no or "")[:100].strip() or None
        p_priority = (p_priority or "MEDIUM")[:20].strip()

        # Build verified structured facts for Field 9 and Field 10
        verified_facts = {
            "petitioner_name": p_name,
            "father_husband_name": f_name,
            "door_no": p_door,
            "street_name": p_street,
            "village": p_village,
            "firka": p_firka,
            "taluk": p_taluk,
            "district": p_district,
            "revenue_division": p_rev_div,
            "block": p_block,
            "department": p_dept,
            "sub_department": p_subdept,
            "grievance_type": p_gtype,
            "grievance_subtype": p_gsub,
            "local_body_type": p_lbody,
            "requested_action": verified_entity_dict.get("requested_action") or clean_field(llm_data.get("requested_action")),
            "grievance_subject": verified_entity_dict.get("petition_subject") or existing_entity_dict.get("petition_subject") or clean_field(llm_data.get("Grievance_Subject"))
        }

        # Field 9: Dynamic multi-signal Community vs Individual Scope Classification
        from services.grievance_scope_classifier import classify_grievance_scope
        tax_scope_meta = tax_row or {
            "department": p_dept,
            "grievance_type": p_gtype,
            "grievance_sub_type": p_gsub,
            "scope_type": sel_tax.get("scope_type") or (tax_row.get("scope_type") if tax_row else None)
        }
        scope_result = classify_grievance_scope(
            doc_context=doc_context,
            taxonomy_meta=tax_scope_meta,
            extracted_facts=verified_facts
        )
        p_community_or_indiv = scope_result.get("classification") or "Unknown"

        # Field 10: Official Administrative Tamil Summary Normalization & Grounding Validation
        from services.summary_normalizer import (
            normalize_administrative_tamil_summary,
            validate_summary_grounding,
            build_factual_administrative_summary
        )
        if not summary_ta or not summary_ta.startswith("மனுதாரர்") or "கோரிக்கை விடுத்துள்ளார்" not in summary_ta:
            summary_ta = build_factual_administrative_summary(verified_facts)
        summary_ta = normalize_administrative_tamil_summary(summary_ta, verified_facts)
        if not validate_summary_grounding(summary_ta, verified_facts, doc_context):
            logger.info("Summary grounding validation triggered fallback to factual administrative summary.")
            summary_ta = build_factual_administrative_summary(verified_facts)

        # Diagnostic logging for AI analysis mapping
        logger.info(
            f"📊 [AI ANALYSIS RESULT] source_id={source_id}\n"
            f"  • Raw LLM Grievance Type: {llm_data.get('grievance_type') or sel_tax.get('Grievance_Type')}\n"
            f"  • Raw LLM Subtype: {llm_data.get('grievance_subtype') or sel_tax.get('Grievance_Sub_Type')}\n"
            f"  • Raw Petition Subject: {verified_entity_dict.get('petition_subject') or existing_entity_dict.get('petition_subject')}\n"
            f"  • Mapped Dept: {p_dept}\n"
            f"  • Mapped Grievance Type: {p_gtype}\n"
            f"  • Mapped Subtype: {p_gsub}\n"
            f"  • Scope (Field 9): {p_community_or_indiv} (score: pub={scope_result.get('public_score')}, ind={scope_result.get('individual_score')})\n"
            f"  • Priority: {p_priority}\n"
            f"  • Summary (TA): {summary_ta}\n"
            f"  • Summary (EN): {summary_en}"
        )

        aligned_action_items = llm_data.get("action_items") or [
            {"action": f"சம்பந்தப்பட்ட {p_dept} அலுவலர் மனு மீது உரிய பரிசீலனை மேற்கொள்ளுதல்", "department": p_dept, "deadline_hint": "15 நாட்கள்"},
            {"action": "மனு மீது உரிய தீர்வு காண உத்தரவு பிறப்பித்தல்", "department": p_dept, "deadline_hint": "30 நாட்கள்"}
        ]

        analysis_result = {
            "petitioner_name": p_name,
            "father_husband_name": f_name,
            "complainant_signatory": p_complainant,
            "gender": p_gender,
            "phone": p_phone,
            "alternate_phone": p_alt_phone,
            "address": p_addr,
            "door_no": p_door,
            "street_name": p_street,
            "village": p_village,
            "firka": p_firka,
            "taluk": p_taluk,
            "revenue_division": p_rev_div,
            "district": p_district,
            "block": p_block,
            "ward": p_ward,
            "municipality_ward": p_muni_ward,
            "local_body_type": p_lbody,
            "community_or_individual": p_community_or_indiv,
            "grievance_scope": scope_result,
            "pincode": p_pincode,
            "ref_number": p_ref_no,
            "responsible_officer": p_resp_off,
            "grievance_type": p_gtype,
            "grievance_subtype": p_gsub,
            "department": p_dept,
            "sub_department": p_subdept,
            "taxonomy_id": (tax_row.get("id") if tax_row else None) or (cls_res.get("taxonomy_id") if cls_res else None),
            "priority": p_priority,
            "due_date": "15 Days from Receipt",
            "description_summary_tamil": summary_ta,
            "description_summary_english": summary_en,
            "location_status": loc_status,
            "action_items": aligned_action_items,
            "claims": llm_data.get("claims") or fallback_analysis["claims"]
        }

        # Anti-hallucination claim verification
        analysis_result = self._verify_claims(analysis_result, doc_context)

        # 4. Upsert ai_analysis table
        await db.execute(text("DELETE FROM ai_analysis WHERE source_id = :source_id"), {"source_id": source_id})
        await db.execute(text("""
            INSERT INTO ai_analysis 
                (source_id, grievance_type_suggested, grievance_subtype_suggested, 
                 department_suggested, priority_suggested, description_summary_tamil,
                 description_summary_english, action_items, claims, hallucination_score, 
                 grounding_score, raw_ai_response)
            VALUES 
                (:source_id, :gt, :gst, :dept, :pri, :sum_ta, :sum_en, :actions, :claims, :hall, :ground, :raw)
        """), {
            "source_id": source_id,
            "gt": p_gtype,
            "gst": p_gsub,
            "dept": p_dept,
            "pri": p_priority,
            "sum_ta": summary_ta,
            "sum_en": summary_en,
            "actions": json.dumps(analysis_result.get("action_items", []), ensure_ascii=False),
            "claims": json.dumps(analysis_result.get("claims", []), ensure_ascii=False),
            "hall": analysis_result.get("hallucination_score", 0.0),
            "ground": analysis_result.get("grounding_score", 1.0),
            "raw": json.dumps({"prompt": prompt[:400], "response": raw_response[:400]}, ensure_ascii=False)
        })

        # 5. Upsert grievance_drafts table (ref_number from regex only; dro_grievance_id NULL until push_to_dro)
        existing_draft = await db.execute(
            text("SELECT id FROM grievance_drafts WHERE source_id = :source_id"),
            {"source_id": source_id}
        )
        draft_row = existing_draft.mappings().one_or_none()

        if draft_row:
            await db.execute(text("""
                UPDATE grievance_drafts SET
                    petitioner_name = :name,
                    father_husband_name = :father,
                    complainant_signatory = :complainant,
                    gender = :gender,
                    phone = :phone,
                    alternate_phone = :alt_phone,
                    address = :addr,
                    door_no = :door,
                    street_name = :street,
                    village = :village,
                    firka = :firka,
                    taluk = :taluk,
                    district = :district,
                    block = :block,
                    revenue_division = :rev_div,
                    ward = :ward,
                    municipality_ward = :muni_ward,
                    local_body_type = :local_body_type,
                    community_or_individual = :community_or_individual,
                    responsible_officer = :resp_off,
                    ref_number = :ref_no,
                    grievance_type = :g_type,
                    grievance_subtype = :g_sub,
                    department = :dept,
                    sub_department = :sub_dept,
                    description = :desc,
                    priority = :priority,
                    updated_at = NOW()
                WHERE source_id = :source_id
            """), {
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
                "complainant": p_complainant,
                "gender": p_gender,
                "phone": p_phone,
                "alt_phone": p_alt_phone,
                "addr": p_addr,
                "door": p_door,
                "street": p_street,
                "village": p_village,
                "firka": p_firka,
                "taluk": p_taluk,
                "district": p_district,
                "block": p_block,
                "rev_div": p_rev_div,
                "ward": p_ward,
                "muni_ward": p_muni_ward,
                "local_body_type": p_lbody,
                "community_or_individual": p_community_or_indiv,
                "resp_off": p_resp_off,
                "ref_no": p_ref_no,
                "g_type": p_gtype,
                "g_sub": p_gsub,
                "dept": p_dept,
                "sub_dept": p_subdept,
                "desc": summary_ta,
                "priority": p_priority
            })
        else:
            draft_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO grievance_drafts (
                    id, source_id, petitioner_name, father_husband_name, complainant_signatory, email, phone,
                    is_own_phone, alternate_phone, address, gender, is_differently_abled,
                    community_or_individual, description, grievance_source, ref_number,
                    department, sub_department, local_body_type, grievance_type, grievance_subtype,
                    district, revenue_division, taluk, firka, block, village, ward, municipality_ward,
                    street_name, door_no, responsible_officer, dro_grievance_id, priority,
                    status, dro_status, is_whatsapp_appeal, is_whatsapp_tracking, is_whatsapp_receipt,
                    ex_servicemen_relationship, officer_approved
                ) VALUES (
                    :id, :source_id, :name, :father, :complainant, NULL, :phone,
                    :is_own_phone, :alt_phone, :addr, :gender, NULL,
                    :community_or_individual, :desc, 'DRO Camp / மாவட்ட வருவாய் அலுவலர் முகாம்', :ref_no,
                    :dept, :sub_dept, :local_body_type, :g_type, :g_sub,
                    :district, :rev_div, :taluk, :firka, :block, :village, :ward, :muni_ward,
                    :street, :door, :resp_off, NULL, :priority,
                    NULL, 'draft', FALSE, FALSE, FALSE,
                    NULL, FALSE
                )
            """), {
                "id": draft_id,
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
                "complainant": p_complainant,
                "gender": p_gender,
                "phone": p_phone,
                "is_own_phone": None,
                "alt_phone": p_alt_phone,
                "addr": p_addr,
                "desc": summary_ta,
                "ref_no": p_ref_no,
                "dept": p_dept,
                "sub_dept": p_subdept,
                "local_body_type": p_lbody,
                "community_or_individual": p_community_or_indiv,
                "g_type": p_gtype,
                "g_sub": p_gsub,
                "district": p_district,
                "rev_div": p_rev_div,
                "taluk": p_taluk,
                "firka": p_firka,
                "block": p_block,
                "village": p_village,
                "ward": p_ward,
                "muni_ward": p_muni_ward,
                "street": p_street,
                "door": p_door,
                "resp_off": p_resp_off,
                "priority": p_priority
            })

        # 6. Synchronize AI-suggested entities into extracted_entities WITHOUT deleting regex/master_db entities
        sync_items = [
            ("petitioner_name", p_name),
            ("father_husband_name", f_name),
            ("complainant_signatory", p_complainant),
            ("gender", p_gender),
            ("phone", p_phone),
            ("door_no", p_door),
            ("street_name", p_street),
            ("village", p_village),
            ("firka", p_firka),
            ("taluk", p_taluk),
            ("district", p_district),
            ("ward", p_ward),
            ("municipality_ward", p_muni_ward),
            ("local_body_type", p_lbody),
            ("pincode", p_pincode),
            ("address", p_addr),
            ("survey_no", p_survey),
            ("grievance_type", p_gtype)
        ]

        ai_grounding = analysis_result.get("grounding_score", 0.75)
        for e_type, e_val in sync_items:
            if e_val and e_val != "-":
                await db.execute(text("""
                    INSERT INTO extracted_entities (source_id, entity_type, entity_value, confidence, validation_status, extracted_by)
                    VALUES (:source_id, :type, :val, :conf, 'pending', 'ai_ner')
                    ON CONFLICT DO NOTHING
                """), {"source_id": source_id, "type": e_type, "val": e_val, "conf": ai_grounding})

        # Update source flags
        await db.execute(text("""
            UPDATE sources SET 
                status = 'draft_ready', 
                updated_at = NOW() 
            WHERE source_id = :source_id
        """), {"source_id": source_id})

        await db.commit()
        return analysis_result


ai_analyzer = AIAnalyzer()
