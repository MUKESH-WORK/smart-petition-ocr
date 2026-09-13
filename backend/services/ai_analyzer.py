import asyncio
import json
import uuid
import re
from datetime import datetime
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
from services.verification_barrier import verification_barrier
from services.prompt_builder import prompt_builder

logger = logging.getLogger(__name__)


def datetime_suffix_short() -> str:
    return datetime.utcnow().strftime("%d%b%y").upper()


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
                    cs = re.sub(r'\(\d+\)|\d+', '', sl).strip(',.-:() ')
                    if (
                        cs and 2 <= len(cs) <= 35 and
                        not any(cs.startswith(w) for w in ["தங்கள்", "உண்மையுள்ள", "வணக்கம்", "நன்றி", "நாள்", "தேதி", "செல்", "போன்"]) and
                        not any(skip in cs for skip in ["TK", "Dt", "District", "Taluk", "வட்டம்", "மாவட்டம்"])
                    ):
                        pet_name = cs
                        break

        g_type = entity_map.get("grievance_type", "")
        if not g_type or g_type in ["பொது குறை", "-", "--", "None", "none", "unknown"] or len(g_type) <= 2:
            detected_category = None
        else:
            detected_category = g_type

        if not detected_category:
            for cat, keywords in {
                "கல்வி உதவித்தொகை": ["கல்வி உதவி", "உதவித்தொகை", "scholarship", "கல்வி", "படிப்பு", "கல்லூரி", "மாணவர்"],
                "நில ஆக்கிரமிப்பு அகற்றுதல்": ["ஆக்கிரமிப்பு", "போக வழி", "வழி ஆக்கிரமிப்பு", "பாதை ஆக்கிரமிப்பு", "encroachment"],
                "வாரிசு சான்றிதழ்": ["வாரிசு", "இறப்பு", "சான்று", "சான்றிதழ்", "heir"],
                "பட்டா மாறுதல்": ["பட்டா மாறுதல்", "பட்டா பெயர் மாற்றம்", "உட்பிரிவு", "patta transfer"],
                "பட்டா / நிலம்": ["நில", "பட்டா", "சர்வே", "land", "patta", "நத்தம்"],
                "ஆதார் / பெயர் மாற்றம்": ["ஆதார்", "aadhar", "aadhaar", "பெயர் மாற்றம்", "name change"],
                "சாலை வசதி": ["சாலை", "road", "பாலம்", "bridge", "தெரு"],
                "குடிநீர் வசதி": ["குடிநீர்", "நீர்", "water", "கிணறு", "குழாய்"],
                "மின்சார வசதி": ["மின்", "electric", "electricity", "eb"],
                "ஓய்வூதியம் / உதவித்தொகை": ["ஓய்வூதியம்", "முதியோர்", "விதவை", "pension"],
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
        if tax_match and tax_match.get("validated"):
            dept = tax_match["department"]
            f_gtype = tax_match["grievance_type"]
            f_gsub = tax_match["grievance_subtype"]
        else:
            dept = "Higher Education Department (HIGHEDU)" if "கல்வி" in (detected_category + " " + doc_text) else "General Administration"
            f_gtype = detected_category
            f_gsub = f"{detected_category} கோரிக்கை"

        if "கல்வி" in detected_category or "scholarship" in doc_text.lower() or "கல்வி உதவி" in doc_text:
            summary_ta = f"மனுதாரர் {pet_name or ''} ஏழை குடும்பத்தைச் சேர்ந்தவர். குடும்ப வறுமை சூழ்நிலையில் கல்லூரி படிப்பைத் தொடர அரசு முதலமைச்சரின் கல்வி உதவித்தொகை (Scholarship) திட்டத்தின் கீழ் நிதி உதவி வழங்குமாறு கோரியுள்ளார்."
            summary_en = f"Petitioner {pet_name or 'Applicant'} from an economically disadvantaged family has requested financial assistance under the Chief Minister's Scholarship Scheme to continue higher education studies."
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
            WHERE source_id = CAST(:source_id AS UUID)
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
            WHERE source_id = CAST(:source_id AS UUID)
            ORDER BY source_page ASC, confidence DESC
        """), {"source_id": source_id})
        existing_entities = [dict(e) for e in ent_result.mappings().all()]
        existing_entity_dict = {e["entity_type"]: e["entity_value"] for e in existing_entities}

        # Stage-C verified deterministic entities (read-only context for LLM)
        verified_entity_dict = {}
        for e in existing_entities:
            etype = e.get("entity_type")
            eval_ = e.get("entity_value")
            if etype in ["phone", "alternate_phone", "survey_no", "file_number", "petition_no", "date_dmy", "pincode", "aadhaar"] and eval_:
                verified_entity_dict[etype] = eval_

        verified_entities_json = json.dumps(verified_entity_dict, ensure_ascii=False)

        fallback_analysis = self._build_grounded_fallback(doc_context, existing_entities)

        # 2. Comprehensive LLM Prompt for Dynamic Zero-Hardcoding Extraction
        prompt = prompt_builder.build_analysis_prompt(doc_context, verified_entity_dict)

        fast_timeout = float(getattr(settings, "LLM_FAST_TIMEOUT", 120.0))
        llm_data: Dict[str, Any] = {}
        raw_response = ""

        try:
            logger.info(f"🤖 Sending document ({len(doc_context)} chars) to LLM for extraction...")
            raw_response = await asyncio.wait_for(
                self.llm.achat(prompt, system_prompt=SYSTEM_PROMPT_TAMIL, temperature=0.1, max_tokens=320, json_mode=True),
                timeout=fast_timeout
            )
            parsed = extract_json_object(raw_response)
            if parsed and isinstance(parsed, dict):
                llm_data = parsed
                logger.info(f"✅ LLM successfully extracted details for petitioner: {llm_data.get('petitioner_name')}")
        except Exception as e:
            logger.warning(f"Notice: LLM extraction timed out or returned error: {e}. Utilizing fallback grounding.", exc_info=True)
            llm_data = fallback_analysis

        # 3. Clean and normalize extracted values
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

        # Extract & prioritize LLM values, falling back to Stage-C entities
        p_name = clean_field(llm_data.get("petitioner_name")) or clean_field(existing_entity_dict.get("petitioner_name"))
        if p_name:
            p_name = re.sub(r'\(\d+\)|\d+', '', p_name).strip(',.-: ')
            if len(p_name) < 2 or p_name.lower() in INVALID_VALUES:
                p_name = None

        f_name = clean_field(llm_data.get("father_husband_name")) or clean_field(existing_entity_dict.get("father_husband_name"))
        if f_name:
            f_name = re.sub(r'^(?:s/o|s\.o|த/பெ|த\.பெ|w/o|w\.o|க/பெ|க\.பெ|ம/பெ|மகன்|மனைவி|தந்தை|கணவர்|காலஞ்சென்ற|Late)\s*[:\.\-]?\s*', '', f_name, flags=re.IGNORECASE).strip(',.-: ')
            f_name = re.sub(r'\(\d+\)|\d+', '', f_name).strip(',.-: ')
            if (
                len(f_name) < 2 or f_name.lower() in INVALID_VALUES or
                any(w in f_name for w in [
                    "தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது",
                    "தெரு", "நகர்", "ரோடு", "வட்டம்", "மாவட்டம்", "கிராமம்", "காலனி", "ஊராட்சி",
                    "பகுதி", "Street", "Road", "Nagar", "Village", "Taluk", "District"
                ])
            ):
                f_name = None

        p_gender = clean_field(llm_data.get("gender")) or None

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

        # Identifiers MUST come from Stage-C verified entities only; never re-extracted/fabricated by LLM
        p_phone = verified_entity_dict.get("phone") or clean_field(existing_entity_dict.get("phone"))
        p_alt_phone = verified_entity_dict.get("alternate_phone") or clean_field(existing_entity_dict.get("alternate_phone"))
        p_survey = verified_entity_dict.get("survey_no") or clean_field(existing_entity_dict.get("survey_no"))
        p_ref_no = (
            verified_entity_dict.get("file_number") or
            verified_entity_dict.get("petition_no") or
            clean_field(existing_entity_dict.get("file_number")) or
            clean_field(existing_entity_dict.get("petition_no"))
        )

        p_door = clean_field(llm_data.get("door_no")) or clean_field(existing_entity_dict.get("door_no"))
        p_street = clean_field(llm_data.get("street_name")) or clean_field(existing_entity_dict.get("street_name"))
        p_village = clean_field(llm_data.get("village")) or clean_field(existing_entity_dict.get("village"))
        p_firka = clean_field(llm_data.get("firka")) or clean_field(existing_entity_dict.get("firka"))
        p_taluk = clean_field(llm_data.get("taluk")) or clean_field(existing_entity_dict.get("taluk"))
        p_district = clean_field(llm_data.get("district")) or clean_field(existing_entity_dict.get("district"))
        if p_district:
            p_district = p_district.replace("\u0908", "\u0B88")
        p_pincode = verified_entity_dict.get("pincode") or clean_field(llm_data.get("pincode")) or clean_field(existing_entity_dict.get("pincode"))
        p_addr = clean_field(llm_data.get("full_address"))
        if p_addr:
            p_addr = p_addr.replace("\u0908", "\u0B88")

        # Build clean full address combining all parts if available
        addr_segments = [s for s in [p_door, p_street, p_village, p_firka, p_taluk, p_district, f"Pin - {p_pincode}" if p_pincode else None] if s and s != "-"]
        if len(addr_segments) >= 2:
            p_addr = ", ".join(addr_segments)
        elif not p_addr:
            p_addr = ", ".join(addr_segments) if addr_segments else None

        p_gtype = clean_field(llm_data.get("grievance_type")) or fallback_analysis["grievance_type"]
        p_gsub = clean_field(llm_data.get("grievance_subtype")) or fallback_analysis["grievance_subtype"]

        # If petition is praying for encroachment removal on pathway, prioritize over annexure mentions
        if any(k in doc_context for k in ["வழி ஆக்கிரமிப்பு", "பாதை ஆக்கிரமிப்பு", "போக வழி", "ஆக்கிரமிப்பை அகற்ற"]) and ("ஆக்கிரமிப்பு" not in p_gtype):
            if "பட்டா" in p_gtype or p_gtype in ["பொது குறை", "நிலம்", "பொது"]:
                p_gtype = "நில ஆக்கிரமிப்பு அகற்றுதல்"
                p_gsub = "பொதுப்பாதை / வழிப்பாதை ஆக்கிரமிப்பு அகற்றுதல்"

        p_dept = taxonomy_matcher.normalize_department(clean_field(llm_data.get("department")) or fallback_analysis["department"])

        # Domain routing: Higher Education Scholarship
        if any(k in (p_gtype + " " + p_gsub + " " + doc_context).lower() for k in ["scholarship", "கல்வி உதவி", "கல்வி உதவித்தொகை", "கல்லூரி படிப்பு", "பல்கலைக்கழக"]):
            if "higher education" not in p_dept.lower() and "social justice" not in p_dept.lower() and "minorities" not in p_dept.lower():
                p_dept = "Higher Education Department (HIGHEDU)"
                if "scholarship" not in p_gsub.lower():
                    p_gsub = "Scholarship - High Edu"

        p_subdept = clean_field(llm_data.get("sub_department")) or f"{p_dept} / நிர்வாகம்"
        p_priority = clean_field(llm_data.get("priority")) or "MEDIUM"

        summary_ta = clean_field(llm_data.get("description_summary_tamil")) or fallback_analysis["description_summary_tamil"]
        summary_en = clean_field(llm_data.get("description_summary_english")) or fallback_analysis["description_summary_english"]

        # Enforce formal third-person administrative Tamil summary
        if summary_ta:
            summary_ta = summary_ta.replace("\u0908", "\u0B88")
            summary_ta = re.sub(r'^(?:நான்|நாங்கள்)\s+', f"மனுதாரர் {p_name or ''} ", summary_ta).strip()
            summary_ta = summary_ta.replace(" உத்தரவு பிறப்பித்தேன்", " உத்தரவு பிறப்பித்து நடவடிக்கை எடுக்கக் கோரியுள்ளார்")
            summary_ta = summary_ta.replace(" உத்தரவிட்டேன்", " உத்தரவிட்டு நடவடிக்கை எடுக்கக் கோரியுள்ளார்")
            summary_ta = summary_ta.replace("நாம் ", "மனுதாரர் ")
            summary_ta = summary_ta.replace("செய்தேன்", "செய்துள்ளார்")
            summary_ta = summary_ta.replace("கேட்டுக் கொள்கிறேன்", "கேட்டுக் கொண்டுள்ளார்")

        # Check for official Tahsildar / Office stamp in doc_context
        tahsildar_match = re.search(r'Tahsildar\s*,\s*([A-Za-z\u0B80-\u0BFF]+)', doc_context, re.IGNORECASE)
        if not tahsildar_match:
            tahsildar_match = re.search(r'([A-Za-z\u0B80-\u0BFF]+)\s*(?:வருவாய்\s*)?வட்டாட்சியர்', doc_context)

        if tahsildar_match:
            cand_taluk = tahsildar_match.group(1).strip()
            p_taluk = cand_taluk
            p_resp_off = f"வட்டாட்சியர், {cand_taluk}"
        else:
            p_resp_off = clean_field(llm_data.get("responsible_officer"))

        # Dynamic Alignment with official CM Helpline Grievance Taxonomy
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

        # Master Location verification (if present in master DB)
        if p_taluk or p_village:
            t_clause = f"%{p_taluk}%" if p_taluk else "NONE"
            v_clause = f"%{p_village}%" if p_village else "NONE"
            try:
                loc_res = await db.execute(text("""
                    SELECT district_name_tamil, taluk_name_tamil, block_name_tamil, firka_name_tamil, village_name_tamil
                    FROM master_locations
                    WHERE taluk_name_tamil ILIKE :taluk OR village_name_tamil ILIKE :village
                    LIMIT 1
                """), {"taluk": t_clause, "village": v_clause})
                loc_match = loc_res.mappings().one_or_none()
                if loc_match:
                    p_district = loc_match["district_name_tamil"] or p_district
                    if not tahsildar_match:
                        p_taluk = loc_match["taluk_name_tamil"] or p_taluk
                    p_village = loc_match["village_name_tamil"] or p_village
                    p_firka = loc_match["firka_name_tamil"] or p_firka
            except Exception as e:
                logger.warning(f"Master location query notice: {e}")

        def sanitize_short_field(val: Any, max_len: int = 50) -> Optional[str]:
            if not val or val == "-":
                return None
            s = str(val).strip()
            for marker in ["பகுதி ", "வட்டம் ", "வட்டத்திற்குட்பட்ட ", "வசிக்கும் "]:
                if marker in s:
                    s = s.split(marker)[-1].strip()
            s = s.strip(" .,-()[]{}:;")
            return s[:max_len].strip() if len(s) > max_len else (s if s else None)

        p_taluk = sanitize_short_field(p_taluk, 50)
        p_district = sanitize_short_field(p_district, 50)
        p_village = sanitize_short_field(p_village, 50)
        p_firka = sanitize_short_field(p_firka, 50)
        p_door = sanitize_short_field(p_door, 50)
        p_street = sanitize_short_field(p_street, 150)
        p_block = sanitize_short_field(f"{p_taluk} ஒன்றியம்" if p_taluk else "-", 50)
        p_rev_div = sanitize_short_field(f"{p_taluk} வருவாய் கோட்டம்" if p_taluk else "-", 50)

        if not p_resp_off or p_resp_off == "வட்டாட்சியர்":
            if "revenue" in p_dept.lower() or "வருவாய்" in p_dept:
                p_resp_off = f"வட்டாட்சியர், {p_taluk}" if p_taluk else "வட்டாட்சியர்"
            else:
                p_resp_off = tax_match.get("responsible_officer") if (tax_match and tax_match.get("responsible_officer")) else "துறை அலுவலர்"
        p_resp_off = sanitize_short_field(p_resp_off, 150)

        # Safeguard field lengths against runaway strings
        p_name = (p_name or "")[:150].strip() or None
        f_name = (f_name or "")[:150].strip() or None
        p_father = f_name
        p_phone = (p_phone or "")[:20].strip() or None
        p_alt_phone = (p_alt_phone or "")[:20].strip() or None
        p_gender = (p_gender or "")[:20].strip() or None
        p_ref_no = (p_ref_no or "")[:100].strip() or None
        p_priority = (p_priority or "MEDIUM")[:20].strip()
        p_lbody = sanitize_short_field(clean_field(llm_data.get("local_body_type")), 50)
        if p_dept and len(p_dept) > 150:
            p_dept = p_dept[:150].strip()
        if p_gtype and len(p_gtype) > 150:
            p_gtype = p_gtype[:150].strip()
        if p_gsub and len(p_gsub) > 150:
            p_gsub = p_gsub[:150].strip()
        if p_subdept and len(p_subdept) > 150:
            p_subdept = p_subdept[:150].strip()

        analysis_result = {
            "grievance_type": p_gtype,
            "grievance_subtype": p_gsub,
            "department": p_dept,
            "priority": p_priority,
            "description_summary_tamil": summary_ta,
            "description_summary_english": summary_en,
            "action_items": llm_data.get("action_items") or fallback_analysis["action_items"],
            "claims": llm_data.get("claims") or fallback_analysis["claims"]
        }

        # Anti-hallucination claim verification
        analysis_result = self._verify_claims(analysis_result, doc_context)

        # 4. Upsert ai_analysis table
        await db.execute(text("DELETE FROM ai_analysis WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
        await db.execute(text("""
            INSERT INTO ai_analysis 
                (source_id, grievance_type_suggested, grievance_subtype_suggested, 
                 department_suggested, priority_suggested, description_summary_tamil,
                 description_summary_english, action_items, claims, hallucination_score, 
                 grounding_score, raw_ai_response)
            VALUES 
                (CAST(:source_id AS UUID), :gt, :gst, :dept, :pri, :sum_ta, :sum_en, :actions, :claims, :hall, :ground, :raw)
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
            text("SELECT id FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"),
            {"source_id": source_id}
        )
        draft_row = existing_draft.mappings().one_or_none()

        if draft_row:
            await db.execute(text("""
                UPDATE grievance_drafts SET
                    petitioner_name = :name,
                    father_husband_name = :father,
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
                    responsible_officer = :resp_off,
                    ref_number = :ref_no,
                    grievance_type = :g_type,
                    grievance_subtype = :g_sub,
                    department = :dept,
                    sub_department = :sub_dept,
                    description = :desc,
                    priority = :priority,
                    updated_at = NOW()
                WHERE source_id = CAST(:source_id AS UUID)
            """), {
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
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
                    id, source_id, petitioner_name, father_husband_name, email, phone,
                    is_own_phone, alternate_phone, address, gender, is_differently_abled,
                    community_or_individual, description, grievance_source, ref_number,
                    department, sub_department, local_body_type, grievance_type, grievance_subtype,
                    district, revenue_division, taluk, firka, block, village, ward, municipality_ward,
                    street_name, door_no, responsible_officer, dro_grievance_id, priority,
                    status, dro_status, is_whatsapp_appeal, is_whatsapp_tracking, is_whatsapp_receipt,
                    ex_servicemen_relationship, officer_approved
                ) VALUES (
                    CAST(:id AS UUID), CAST(:source_id AS UUID), :name, :father, NULL, :phone,
                    :is_own_phone, :alt_phone, :addr, :gender, NULL,
                    'Individual', :desc, 'DRO Camp / மாவட்ட வருவாய் அலுவலர் முகாம்', :ref_no,
                    :dept, :sub_dept, :local_body_type, :g_type, :g_sub,
                    :district, :rev_div, :taluk, :firka, :block, :village, NULL, NULL,
                    :street, :door, :resp_off, NULL, :priority,
                    NULL, 'draft', FALSE, FALSE, FALSE,
                    NULL, FALSE
                )
            """), {
                "id": draft_id,
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
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
                "g_type": p_gtype,
                "g_sub": p_gsub,
                "district": p_district,
                "rev_div": p_rev_div,
                "taluk": p_taluk,
                "firka": p_firka,
                "block": p_block,
                "village": p_village,
                "street": p_street,
                "door": p_door,
                "resp_off": p_resp_off,
                "priority": p_priority
            })

        # 6. Synchronize AI-suggested entities into extracted_entities WITHOUT deleting regex/master_db entities
        sync_items = [
            ("petitioner_name", p_name),
            ("father_husband_name", f_name),
            ("gender", p_gender),
            ("phone", p_phone),
            ("door_no", p_door),
            ("street_name", p_street),
            ("village", p_village),
            ("firka", p_firka),
            ("taluk", p_taluk),
            ("district", p_district),
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
                    VALUES (CAST(:source_id AS UUID), :type, :val, :conf, 'pending', 'ai_ner')
                    ON CONFLICT DO NOTHING
                """), {"source_id": source_id, "type": e_type, "val": e_val, "conf": ai_grounding})

        # Update source flags
        await db.execute(text("""
            UPDATE sources SET 
                status = 'draft_ready', 
                updated_at = NOW() 
            WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})

        await db.commit()
        return analysis_result


ai_analyzer = AIAnalyzer()
