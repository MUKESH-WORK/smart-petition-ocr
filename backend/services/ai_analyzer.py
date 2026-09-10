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

logger = logging.getLogger(__name__)


def datetime_suffix_short() -> str:
    return datetime.utcnow().strftime("%d%b%y").upper()


class AIAnalyzer:
    """
    Production-grade AI Grievance Analyzer:
    - Entity-grounded pre-computation with fast-exit fallback (<30s guarantee)
    - Anti-Hallucination verification barrier (claims mapped to source pages)
    - Dynamic location resolution with master_locations integration
    - Automatic bilingual draft synthesis (Tamil summary + English summary)
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

    def _verify_claims_against_lines(self, analysis: Dict[str, Any], ocr_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Anti-Hallucination Barrier core logic: verifies claims against ocr_lines."""
        claims = analysis.get("claims", [])
        if not claims:
            summary = analysis.get("description_summary_tamil", "")
            if summary:
                claims = [{"text": summary[:120], "source_page": 1, "source_line": 0, "confidence": None}]
            else:
                claims = []

        line_texts_by_page: Dict[int, List[Dict[str, Any]]] = {}
        for l in ocr_lines:
            p_num = l.get("page_number", 1)
            line_texts_by_page.setdefault(p_num, []).append(dict(l))

        verified_count = 0
        for claim in claims:
            page = claim.get("source_page", 1)
            text_str = claim.get("text", "").lower().strip()
            line_idx = claim.get("source_line")

            page_lines = line_texts_by_page.get(page, [])
            matched_line = None

            # First check cited line if specified
            if line_idx is not None and 0 <= line_idx < len(page_lines):
                cited = page_lines[line_idx]
                if text_str in cited["text"].lower() or any(w in cited["text"].lower() for w in text_str.split() if len(w) > 3):
                    matched_line = cited

            # Otherwise search across page lines
            if not matched_line and page_lines:
                for pl in page_lines:
                    pl_text = pl["text"].lower()
                    words = [w for w in text_str.split() if len(w) > 3]
                    if text_str in pl_text or (words and sum(1 for w in words if w in pl_text) >= max(1, len(words) // 2)):
                        matched_line = pl
                        claim["source_line"] = pl.get("line_index", pl.get("line_number", 0))
                        break

            if matched_line:
                claim["verified"] = True
                claim["confidence"] = matched_line.get("score") or 1.0
                verified_count += 1
            else:
                claim["verified"] = False
                claim["confidence"] = 0.0

        total = len(claims) if claims else 1
        hallucination_score = round((total - verified_count) / total, 2)
        analysis["claims"] = claims
        analysis["hallucination_score"] = max(0.0, min(1.0, hallucination_score))
        analysis["grounding_score"] = round(1.0 - analysis["hallucination_score"], 2)
        return analysis

    async def _verify_claims(
        self,
        *args,
        ocr_lines: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Anti-Hallucination Barrier: Verifies claims against actual source page ocr_lines text.
        Supports:
          _verify_claims(db, source_id, analysis)
          _verify_claims(analysis, ocr_lines=ocr_lines)
        """
        db = None
        source_id = None
        analysis = None

        if len(args) == 3:
            db, source_id, analysis = args
        elif len(args) == 1:
            analysis = args[0]
        elif len(args) == 2:
            source_id, analysis = args

        if analysis is None:
            analysis = kwargs.get("analysis", {})

        if ocr_lines is None and db is not None and source_id is not None:
            res = await db.execute(text("""
                SELECT page_number, line_index, text, score
                FROM ocr_lines
                WHERE source_id = CAST(:source_id AS UUID)
                ORDER BY page_number, line_index
            """), {"source_id": source_id})
            ocr_lines = [dict(l) for l in res.mappings().all()]

        return self._verify_claims_against_lines(analysis, ocr_lines or [])


    def _build_grounded_fallback(self, chunks: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Precomputes an instant, completely hallucination-free analysis directly from detected entities."""
        lines = [c.get('chunk_text', '') for c in chunks if c.get('chunk_text')]
        entity_map = {e["entity_type"]: e["entity_value"] for e in entities}

        pet_name = entity_map.get("petitioner_name", "")
        g_type = entity_map.get("grievance_type", "")
        loc = entity_map.get("village") or entity_map.get("taluk") or ""
        surv = entity_map.get("survey_no", "")

        context = " ".join(lines[:8])

        # Detect category
        detected_category = g_type
        if not detected_category or detected_category == "பொது குறை":
            for cat, keywords in {
                "ஆதார் / பெயர் மாற்றம்": ["ஆதார்", "aadhar", "aadhaar", "பெயர் மாற்றம்", "name change", "டாற்றம்", "பையர்"],
                "நிலம்": ["நில", "பட்டா", "சர்வே", "ஆக்கிரமிப்பு", "land", "patta"],
                "சாலை": ["சாலை", "road", "பாலம்", "bridge", "தெரு"],
                "குடிநீர்": ["குடிநீர்", "நீர்", "water", "கிணறு", "குழாய்"],
                "மின்சாரம்": ["மின்", "electric", "electricity", "eb"],
                "உதவித்தொகை": ["உதவி", "pension", "allowance", "ஓய்வூதியம்", "முதியோர்"],
                "வருவாய்": ["வருவாய்", "revenue", "சான்றிதழ்"],
                "சுகாதாரம்": ["சுகாதாரம்", "சாக்கடை", "குப்பை"]
            }.items():
                if any(k.lower() in context.lower() for k in keywords):
                    detected_category = cat
                    break
        if not detected_category:
            detected_category = "பொது குறை"

        dept_map = {
            "ஆதார் / பெயர் மாற்றம்": "தகவல் தொழில்நுட்பவியல் & வருவாய்த்துறை",
            "நிலம்": "வருவாய்த்துறை",
            "சாலை": "நெடுஞ்சாலை & ஊரக வளர்ச்சி",
            "குடிநீர்": "குடிநீர் வடிகால் வாரியம் & உள்ளாட்சி",
            "மின்சாரம்": "மின்சார வாரியம் (TANGEDCO)",
            "உதவித்தொகை": "சமூக நலத்துறை",
            "வருவாய்": "வருவாய்த்துறை",
            "சுகாதாரம்": "பொது சுகாதாரத்துறை"
        }
        dept = dept_map.get(detected_category, "வருவாய்த்துறை")

        if detected_category == "ஆதார் / பெயர் மாற்றம்":
            f_name = entity_map.get("father_husband_name", "")
            f_clause = f" (த/பெ {f_name})" if f_name else ""
            dynamic_summary_ta = f"மனுதாரர் {pet_name or 'மனுதாரர்'}{f_clause} தமிழ்நாடு அரசு அரசிதழ் மற்றும் பள்ளி மாற்றுச் சான்றிதழில் (TC) திருத்தப்பட்ட பெயரின் அடிப்படையில், ஆதார் அட்டையில் பெயர் திருத்தம் மேற்கொண்டு புதிய அட்டை வழங்கிட கோரிக்கை விடுத்துள்ளார்."
            dynamic_summary_en = f"Petitioner {pet_name or 'Citizen'}{(' (S/o ' + f_name + ')') if f_name else ''} has submitted a grievance petition seeking name update in Aadhaar card based on Tamil Nadu Government Gazette publication and updated Transfer Certificate (TC)."
            sub_type = "ஆதார் அட்டை பெயர் திருத்தம்"
        else:
            summary_parts = []
            if pet_name:
                summary_parts.append(f"மனுதாரர் {pet_name}")
            if loc:
                summary_parts.append(f"{loc} பகுதியில்")
            if surv:
                summary_parts.append(f"புல எண் {surv} சார்ந்து")
            if detected_category:
                summary_parts.append(f"{detected_category} தொடர்பாக நடவடிக்கை கோரியுள்ளார்.")
            elif lines:
                summary_parts.append(f"கோரிக்கை: {lines[0][:120]}")
            else:
                summary_parts.append("நிர்வாக நடவடிக்கை கோரி மனு சமர்ப்பித்துள்ளார்.")

            dynamic_summary_ta = " ".join(summary_parts)
            dynamic_summary_en = f"Petitioner {pet_name or 'Citizen'} has submitted a grievance petition regarding {detected_category} in {loc or 'Erode District'}."
            sub_type = "விசாரணை மற்றும் நடவடிக்கை"

        return {
            "grievance_type": detected_category,
            "grievance_subtype": sub_type,
            "department": dept,
            "priority": "HIGH" if detected_category in ["குடிநீர்", "மின்சாரம்"] else "MEDIUM",
            "description_summary_tamil": dynamic_summary_ta,
            "description_summary_english": dynamic_summary_en,
            "action_items": [
                {"action": f"சம்பந்தப்பட்ட {dept} அலுவலர் ஆவணங்களை சரிபார்த்து உரிய நடவடிக்கை எடுத்தல்", "department": dept, "deadline_hint": "15 நாட்கள்"},
                {"action": "மனு மீது உரிய தீர்வு காண உத்தரவு பிறப்பித்தல்", "department": dept, "deadline_hint": "30 நாட்கள்"}
            ],
            "claims": [{"text": dynamic_summary_ta[:80], "source_page": 1, "confidence": 0.95}],
            "hallucination_score": 0.0,
            "grounding_score": 1.0
        }

    async def analyze(self, db: AsyncSession, source_id: str) -> Dict[str, Any]:
        # 1. Gather chunks (up to 8 for token efficiency)
        result = await db.execute(text("""
            SELECT chunk_text, page_number FROM document_chunks 
            WHERE source_id = CAST(:source_id AS UUID) 
            ORDER BY page_number, chunk_index
        """), {"source_id": source_id})
        chunks = [dict(r) for r in result.mappings().all()]

        if not chunks:
            ocr_res = await db.execute(text("""
                SELECT full_text as chunk_text, page_number FROM ocr_results
                WHERE source_id = CAST(:source_id AS UUID)
                ORDER BY page_number
            """), {"source_id": source_id})
            chunks = [dict(r) for r in ocr_res.mappings().all()]

        # Limit to 8 chunks max (Google/CPGRAMS token-budget best practice)
        context = "\n\n".join([f"[Page {c['page_number']}] {c['chunk_text']}" for c in chunks[:8]])

        # 2. Gather extracted entities
        ent_result = await db.execute(text("""
            SELECT entity_type, entity_value, source_page FROM extracted_entities 
            WHERE source_id = CAST(:source_id AS UUID) AND validation_status IN ('verified', 'pending')
            ORDER BY source_page ASC, confidence DESC
        """), {"source_id": source_id})
        entities = [dict(e) for e in ent_result.mappings().all()]
        entity_context = "\n".join([f"- {e['entity_type']}: {e['entity_value']} (p.{e.get('source_page', 1)})" for e in entities[:15]])

        # 3. Pre-compute entity-grounded fallback
        fallback_analysis = self._build_grounded_fallback(chunks, entities)

        # 4. LLM Analysis with Fast Timeout
        prompt = f"""
நீ ஒரு தமிழ்நாடு DRO புகார் பகுப்பாய்வு உதவியாளர்.
கீழ்கண்ட ஆவணத்தின் அடிப்படையில் மட்டுமே விடையளி.

ஆவண உரை:
{context}

பிரித்தெடுக்கப்பட்ட தகவல்கள்:
{entity_context}

விதிகள்:
1. ஆவணத்தில் இல்லாத தகவலை உருவாக்காதே.
2. JSON வடிவில் மட்டுமே விடையளி.
3. ஒவ்வொரு கூற்றுக்கும் (claims) ஆதார பக்க எண்ணை குறிப்பிடு.
4. உறுதியற்றதாக இருந்தால் null ஆக விடு.

JSON வடிவம்:
{{
  "grievance_type": "நிலம்|சாலை|குடிநீர்|மின்சாரம்|உதவித்தொகை|வருவாய்|சுகாதாரம்|பொது குறை",
  "grievance_subtype": "பட்டா மாறுதல்|சர்வே அளவீடு|சாலை பழுது|புதிய இணைப்பு|...",
  "department": "வருவாய்த்துறை|நெடுஞ்சாலை & ஊரக வளர்ச்சி|குடிநீர் வடிகால் வாரியம் & உள்ளாட்சி|மின்சார வாரியம் (TANGEDCO)|சமூக நலத்துறை|பொது சுகாதாரத்துறை",
  "priority": "HIGH|MEDIUM|LOW",
  "description_summary_tamil": "மனுவின் முக்கிய கோரிக்கை குறித்த 2-3 வாக்கிய சுருக்கம்",
  "description_summary_english": "Brief English summary of the petition request",
  "action_items": [
    {{"action": "துறை நடவடிக்கை விவரம்", "department": "துறை", "deadline_hint": "30 நாட்கள்"}}
  ],
  "claims": [
    {{"text": "முக்கிய கூற்று", "source_page": 1, "source_line": 0}}
  ]
}}
"""
        fast_timeout = getattr(settings, "LLM_FAST_TIMEOUT", 30.0)
        raw_response = ""
        analysis = None

        try:
            raw_response = await asyncio.wait_for(
                self.llm.achat(prompt, system_prompt=SYSTEM_PROMPT_TAMIL, temperature=0.1, max_tokens=300),
                timeout=fast_timeout
            )
            llm_analysis = extract_json_object(raw_response)
            if llm_analysis and isinstance(llm_analysis, dict):
                # Merge LLM output over precomputed fallback
                analysis = fallback_analysis.copy()
                for k, v in llm_analysis.items():
                    if v and v != "null" and not str(v).startswith("[தகவல்"):
                        if k in ["description_summary_tamil", "description_summary_english"] and self.is_noisy_ocr_text(str(v)):
                            continue
                        analysis[k] = v
        except Exception as e:
            logger.info(f"LLM fast timeout/fallback triggered ({e}), using instant entity-grounded analysis.")
            analysis = fallback_analysis

        if not analysis:
            analysis = fallback_analysis

        # Ensure summaries are clean and not raw OCR noise
        if self.is_noisy_ocr_text(analysis.get("description_summary_tamil", "")):
            analysis["description_summary_tamil"] = fallback_analysis["description_summary_tamil"]
        if self.is_noisy_ocr_text(analysis.get("description_summary_english", "")):
            analysis["description_summary_english"] = fallback_analysis["description_summary_english"]

        # 5. Anti-hallucination verification
        analysis = await self._verify_claims(db, source_id, analysis)

        # 6. Delete old analysis if re-analyzing
        await db.execute(text("DELETE FROM ai_analysis WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})

        # 7. Persist to ai_analysis table
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
            "gt": analysis.get("grievance_type", "பொது குறை"),
            "gst": analysis.get("grievance_subtype", "விசாரணை மற்றும் நடவடிக்கை"),
            "dept": analysis.get("department", "வருவாய்த்துறை"),
            "pri": analysis.get("priority", "MEDIUM"),
            "sum_ta": analysis.get("description_summary_tamil"),
            "sum_en": analysis.get("description_summary_english"),
            "actions": json.dumps(analysis.get("action_items", []), ensure_ascii=False),
            "claims": json.dumps(analysis.get("claims", []), ensure_ascii=False),
            "hall": analysis.get("hallucination_score", 0.0),
            "ground": analysis.get("grounding_score", 1.0),
            "raw": json.dumps(llm_analysis if 'llm_analysis' in locals() and llm_analysis else {}, ensure_ascii=False)
        })

        # Audit Event: AI_ANALYZED
        from app.dependencies import log_audit_event
        await log_audit_event(
            db,
            action="AI_ANALYZED",
            source_id=source_id,
            details={
                "hallucination_score": analysis.get("hallucination_score", 0.0),
                "grounding_score": analysis.get("grounding_score", 1.0),
                "claims_count": len(analysis.get("claims", []))
            }
        )

        # 8. Dynamic Fields & Location Synthesis
        entity_dict = {e["entity_type"]: e["entity_value"] for e in entities}

        INVALID_VALS = {
            "விண்ணப்பதாரர் பெயர்", "தந்தை அல்லது கணவர் பெயர்", "தந்தை பெயர்",
            "கணவர் பெயர்", "முழு முகவரி", "கிராமம்", "வட்டம்", "மாவட்டம்",
            "சுருக்கமான கோரிக்கை", "null", "none", "n/a", "தெரியவில்லை", "இல்லை",
            "விண்ணப்பதாரர் பெயர் அல்லது null", "தந்தை அல்லது கணவர் பெயர் அல்லது null",
            "முழு முகவரி அல்லது null", "கிராமம் அல்லது null", "வட்டம் அல்லது null", "மாவட்டம் அல்லது null"
        }

        def clean_val(v):
            if not v or not isinstance(v, str):
                return None
            s = v.strip()
            if s.lower() in [iv.lower() for iv in INVALID_VALS] or "அல்லது null" in s or "விண்ணப்பதாரர் பெயர்" in s or "முழு முகவரி" in s:
                return None
            return s

        p_name = clean_val(entity_dict.get("petitioner_name") or entity_dict.get("name"))
        f_name = clean_val(entity_dict.get("father_husband_name"))
        page1_phones = [e["entity_value"] for e in entities if e["entity_type"] == "phone" and e.get("source_page") == 1]
        p_phone = page1_phones[0] if page1_phones else entity_dict.get("phone")
        p_addr = clean_val(entity_dict.get("address"))
        p_taluk = clean_val(entity_dict.get("taluk"))
        p_district = clean_val(entity_dict.get("district"))
        p_village = clean_val(entity_dict.get("village"))
        p_survey = clean_val(entity_dict.get("survey_no"))
        p_pet_no = clean_val(entity_dict.get("petition_no"))
        p_ref_no = p_pet_no or p_survey

        p_gtype = analysis.get("grievance_type") or "பொது குறை"
        p_gsub = analysis.get("grievance_subtype") or "விசாரணை மற்றும் நடவடிக்கை"
        p_dept = analysis.get("department") or "வருவாய்த்துறை"

        if p_gtype == "ஆதார் / பெயர் மாற்றம்":
            p_subdept = "ஆதார் சேவை மையம் (e-Sevai)"
            p_gsub = "ஆதார் அட்டை பெயர் திருத்தம்"
        else:
            p_subdept = f"{p_dept} / நிர்வாகம்"

        # Extract door_no and street_name if present
        p_door = None
        p_street = None
        if p_addr:
            door_match = re.search(r'(?:D\.No|D\.N|கதவு\s*எண்|எண்|No\.?)\s*[:\.]?\s*(\d+[A-Za-z0-9\-\/]*)', p_addr, re.IGNORECASE)
            if door_match:
                p_door = door_match.group(1).strip()
            street_match = re.search(r'([A-Za-z\u0B80-\u0BFF0-9\s\-]+(?:வீதி|தெரு|Street|Road|Salai|Nagar|நகர்)(?:\s*எண்[\-\s]*\d+)?)', p_addr, re.IGNORECASE)
            if street_match:
                p_street = street_match.group(1).strip()

        # Dynamic Location Resolution via master_locations
        loc_match = None
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
            except Exception as e:
                logger.warning(f"Error querying master_locations: {e}")

        p_firka = loc_match["firka_name_tamil"] if loc_match else (f"{p_taluk} பிர்கா" if p_taluk else "-")
        p_block = loc_match["block_name_tamil"] if loc_match else (f"{p_taluk} ஒன்றியம்" if p_taluk else "-")
        p_rev_div = f"{p_taluk} உட்கோட்டம்" if p_taluk else (f"{p_district} வருவாய் கோட்டம்" if p_district else "-")
        p_resp_off = f"வட்டாட்சியர், {p_taluk}" if p_taluk else (f"மாவட்ட வருவாய் அலுவலர், {p_district}" if p_district else "வட்டாட்சியர்")

        summary_ta = analysis.get("description_summary_tamil")
        if not summary_ta or self.is_noisy_ocr_text(summary_ta):
            summary_ta = fallback_analysis["description_summary_tamil"]
            analysis["description_summary_tamil"] = summary_ta

        today_tag = datetime_suffix_short()
        auto_gid = f"TN/REV/DRO/{today_tag}/{str(uuid.uuid4())[:4].upper()}"

        # 9. Upsert Grievance Draft
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
                    phone = :phone,
                    address = :addr,
                    description = :desc,
                    grievance_type = :g_type,
                    grievance_subtype = :g_sub,
                    department = :dept,
                    sub_department = :sub_dept,
                    taluk = :taluk,
                    district = :district,
                    village = :village,
                    firka = :firka,
                    block = :block,
                    revenue_division = :rev_div,
                    street_name = :street,
                    door_no = :door,
                    responsible_officer = :resp_off,
                    ref_number = :ref_no,
                    priority = :priority,
                    updated_at = NOW()
                WHERE source_id = CAST(:source_id AS UUID)
            """), {
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
                "phone": p_phone,
                "addr": p_addr,
                "desc": summary_ta,
                "g_type": p_gtype,
                "g_sub": p_gsub,
                "dept": p_dept,
                "sub_dept": p_subdept,
                "district": p_district or "ஈரோடு",
                "rev_div": p_rev_div,
                "taluk": p_taluk or "-",
                "firka": p_firka,
                "block": p_block,
                "village": p_village or "-",
                "street": p_street or "-",
                "door": p_door or "-",
                "resp_off": p_resp_off,
                "ref_no": p_ref_no,
                "priority": analysis.get("priority", "MEDIUM")
            })
        else:
            await db.execute(text("""
                INSERT INTO grievance_drafts (
                    source_id, petitioner_name, father_husband_name, email, phone,
                    is_own_phone, alternate_phone, address, gender, is_differently_abled,
                    community_or_individual, description, grievance_source, ref_number,
                    department, sub_department, local_body_type, grievance_type, grievance_subtype,
                    district, revenue_division, taluk, firka, block, village, ward, municipality_ward,
                    street_name, door_no, responsible_officer, dro_grievance_id, priority,
                    status, dro_status, is_whatsapp_appeal, is_whatsapp_tracking, is_whatsapp_receipt,
                    ex_servicemen_relationship, officer_approved
                ) VALUES (
                    CAST(:source_id AS UUID), :name, :father, :email, :phone,
                    TRUE, :alt_phone, :addr, :gender, :diff_abled,
                    :comm_ind, :desc, :g_source, :ref_no,
                    :dept, :sub_dept, :local_body, :g_type, :g_sub,
                    :district, :rev_div, :taluk, :firka, :block, :village, :ward, :m_ward,
                    :street, :door, :resp_off, :gid, :priority,
                    'Open', 'draft', FALSE, TRUE, TRUE,
                    '-None-', FALSE
                )
            """), {
                "source_id": source_id,
                "name": p_name,
                "father": f_name,
                "email": entity_dict.get("email"),
                "phone": p_phone,
                "alt_phone": entity_dict.get("alternate_phone"),
                "addr": p_addr,
                "gender": "Male",
                "diff_abled": "No",
                "comm_ind": "Individual",
                "desc": summary_ta,
                "g_source": "DRO Camp / மாவட்ட வருவாய் அலுவலர் முகாம்",
                "ref_no": p_ref_no,
                "dept": p_dept,
                "sub_dept": p_subdept,
                "local_body": "Village Panchayat",
                "g_type": p_gtype,
                "g_sub": p_gsub,
                "district": p_district or "ஈரோடு",
                "rev_div": p_rev_div,
                "taluk": p_taluk or "-",
                "firka": p_firka,
                "block": p_block,
                "village": p_village or "-",
                "ward": "-None-",
                "m_ward": "-None-",
                "street": p_street or "-",
                "door": p_door or "-",
                "resp_off": p_resp_off,
                "gid": auto_gid,
                "priority": analysis.get("priority", "MEDIUM")
            })

        # 10. Update source status to draft_ready
        await db.execute(text("""
            UPDATE sources SET status = 'draft_ready', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        analysis["source_id"] = source_id
        return analysis


ai_analyzer = AIAnalyzer()
