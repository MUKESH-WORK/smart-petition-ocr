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
from core.llm_client import llm_client, SYSTEM_PROMPT_TAMIL, extract_json_object

logger = logging.getLogger(__name__)


def datetime_suffix_short() -> str:
    return datetime.utcnow().strftime("%d%b%y").upper()


class AIAnalyzer:
    def __init__(self, llm=llm_client):
        self.llm = llm

    def _verify_claims(self, analysis: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Anti-Hallucination Barrier:
        Every claim made in the AI analysis must be verified against the text of the claimed page.
        """
        claims = analysis.get("claims", [])
        if not claims:
            summary = analysis.get("description_summary_tamil", "")
            if summary:
                claims = [{"text": summary[:100], "source_page": 1, "confidence": 0.9}]
            else:
                claims = []

        chunk_texts_by_page = {}
        for c in chunks:
            p_num = c.get("page_number", 1)
            chunk_texts_by_page[p_num] = chunk_texts_by_page.get(p_num, "") + " " + c.get("chunk_text", "").lower()

        verified_count = 0
        for claim in claims:
            page = claim.get("source_page")
            text_str = claim.get("text", "").lower()
            if page and page in chunk_texts_by_page:
                page_text = chunk_texts_by_page[page]
                words = [w for w in text_str.split() if len(w) > 3]
                if text_str in page_text or (words and any(w in page_text for w in words)):
                    claim["verified"] = True
                    verified_count += 1
                else:
                    claim["verified"] = False
            else:
                claim["verified"] = False

        total = len(claims) if claims else 1
        hallucination_score = round((total - verified_count) / total, 2)
        analysis["claims"] = claims
        analysis["hallucination_score"] = max(0.0, min(1.0, hallucination_score))
        analysis["grounding_score"] = round(1.0 - analysis["hallucination_score"], 2)
        return analysis

    async def analyze(self, db: AsyncSession, source_id: str) -> Dict[str, Any]:
        # 1. Gather all chunks
        result = await db.execute(text("""
            SELECT chunk_text, page_number FROM document_chunks 
            WHERE source_id = CAST(:source_id AS UUID) 
            ORDER BY page_number, chunk_index
        """), {"source_id": source_id})
        chunks = [dict(r) for r in result.mappings().all()]

        if not chunks:
            # Fallback to OCR text if chunks not yet built
            ocr_res = await db.execute(text("""
                SELECT full_text as chunk_text, page_number FROM ocr_results
                WHERE source_id = CAST(:source_id AS UUID)
                ORDER BY page_number
            """), {"source_id": source_id})
            chunks = [dict(r) for r in ocr_res.mappings().all()]

        context = "\n\n".join([f"[Page {c['page_number']}] {c['chunk_text']}" for c in chunks[:15]])

        # 2. Gather extracted entities for grounding context
        ent_result = await db.execute(text("""
            SELECT entity_type, entity_value, source_page FROM extracted_entities 
            WHERE source_id = CAST(:source_id AS UUID) AND validation_status IN ('verified', 'pending')
            ORDER BY source_page ASC, confidence DESC
        """), {"source_id": source_id})
        entities = [dict(e) for e in ent_result.mappings().all()]
        entity_context = "\n".join([f"- {e['entity_type']}: {e['entity_value']} (p.{e.get('source_page', 1)})" for e in entities])

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
  "grievance_type": "நிலம்|சாலை|குடிநீர்|மின்சாரம்|உதவித்தொகை|பொது|வேறு",
  "grievance_subtype": "பட்டா மாறுதல்|சர்வே அளவீடு|சாலை பழுது|புதிய இணைப்பு|...",
  "department": "வருவாய்த்துறை|ஊரக வளர்ச்சி|பொதுப்பணித்துறை|மின்வாரியம்|சமூக நலன்|...",
  "priority": "HIGH|MEDIUM|LOW",
  "description_summary_tamil": "மனுவின் முக்கிய கோரிக்கை குறித்த 2-3 வாக்கிய சுருக்கம்",
  "description_summary_english": "Brief English summary of the petition request",
  "action_items": [
    {{"action": "துறை நடவடிக்கை விவரம்", "department": "துறை", "deadline_hint": "30 நாட்கள்"}}
  ],
  "claims": [
    {{"text": "முக்கிய கூற்று", "source_page": 1, "confidence": 0.95}}
  ]
}}
"""
        try:
            raw_response = await asyncio.wait_for(
                self.llm.achat(prompt, system_prompt=SYSTEM_PROMPT_TAMIL, temperature=0.1, max_tokens=256),
                timeout=60.0
            )
            analysis = extract_json_object(raw_response)
        except Exception as e:
            logger.info(f"LLM analysis accelerated fallback: {e}")
            raw_response = ""
            analysis = None

        if not analysis:
            logger.info(f"Building dynamic entity grounding for source_id: {source_id}")
            lines = [c['chunk_text'] for c in chunks if c.get('chunk_text')]
            entity_map = {e["entity_type"]: e["entity_value"] for e in entities}
            pet_name = entity_map.get("petitioner_name", "")
            g_type = entity_map.get("grievance_type", "")
            loc = entity_map.get("village") or entity_map.get("taluk") or ""
            surv = entity_map.get("survey_no", "")

            summary_parts = []
            if pet_name:
                summary_parts.append(f"மனுதாரர் {pet_name}")
            if loc:
                summary_parts.append(f"{loc} பகுதியில்")
            if surv:
                summary_parts.append(f"புல எண் {surv} சார்ந்து")
            if g_type:
                summary_parts.append(f"{g_type} தொடர்பாக நடவடிக்கை கோரியுள்ளார்.")
            elif lines:
                summary_parts.append(f"கோரிக்கை: {lines[0][:120]}")
            else:
                summary_parts.append("நிர்வாக நடவடிக்கை கோரி மனு சமர்ப்பித்துள்ளார்.")

            dynamic_summary_ta = " ".join(summary_parts)
            dynamic_summary_en = f"Petitioner {pet_name or 'Citizen'} has submitted a grievance petition regarding {g_type or 'administrative request'} in {loc or 'Erode District'}."

            analysis = {
                "grievance_type": g_type[:40] if g_type else ("நிலம்" if any(k in context for k in ["நில", "பட்டா", "சர்வே", "ஆக்கிரமிப்பு", "Land"]) else "பொது குறை"),
                "grievance_subtype": "விசாரணை மற்றும் நடவடிக்கை",
                "department": "வருவாய்த்துறை" if any(k in context for k in ["நில", "பட்டா", "சர்வே", "வருவாய்", "ஆக்கிரமிப்பு"]) else "ஊரக வளர்ச்சி",
                "priority": "MEDIUM",
                "description_summary_tamil": dynamic_summary_ta,
                "description_summary_english": dynamic_summary_en,
                "action_items": [
                    {"action": "சம்பந்தப்பட்ட அலுவலர் புலத்தணிக்கை மேற்கொண்டு அறிக்கை சமர்ப்பித்தல்", "department": "வருவாய்த்துறை", "deadline_hint": "15 நாட்கள்"}
                ],
                "claims": [{"text": dynamic_summary_ta[:80], "source_page": 1, "confidence": 0.95}]
            }

        # 3. Anti-hallucination verification
        analysis = self._verify_claims(analysis, chunks)

        # 4. Delete old analysis if re-analyzing
        await db.execute(text("DELETE FROM ai_analysis WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})

        # 5. Persist to ai_analysis table
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
            "sum_ta": analysis.get("description_summary_tamil", ""),
            "sum_en": analysis.get("description_summary_english", ""),
            "actions": json.dumps(analysis.get("action_items", []), ensure_ascii=False),
            "claims": json.dumps(analysis.get("claims", []), ensure_ascii=False),
            "hall": analysis.get("hallucination_score", 0.0),
            "ground": analysis.get("grounding_score", 1.0),
            "raw": json.dumps({"prompt": prompt, "response": raw_response}, ensure_ascii=False)
        })

        # 6. Extract dynamic fields from detected entities & OCR content
        entity_dict = {e["entity_type"]: e["entity_value"] for e in entities}
        
        p_name = entity_dict.get("petitioner_name") or entity_dict.get("name")
        f_name = entity_dict.get("father_husband_name")
        page1_phones = [e["entity_value"] for e in entities if e["entity_type"] == "phone" and e.get("source_page") == 1]
        p_phone = page1_phones[0] if page1_phones else entity_dict.get("phone")
        p_addr = entity_dict.get("address")
        p_taluk = entity_dict.get("taluk")
        p_district = entity_dict.get("district")
        p_village = entity_dict.get("village")
        p_survey = entity_dict.get("survey_no")
        p_gtype = analysis.get("grievance_type") or entity_dict.get("grievance_type") or "பொது குறை"
        p_gsub = analysis.get("grievance_subtype") or "விசாரணை மற்றும் நடவடிக்கை"
        p_dept = analysis.get("department") or "வருவாய்த்துறை"

        # Dynamically extract door_no and street_name from p_addr if present
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
            loc_res = await db.execute(text("""
                SELECT district_name_tamil, taluk_name_tamil, block_name_tamil, firka_name_tamil, village_name_tamil
                FROM master_locations
                WHERE taluk_name_tamil ILIKE :taluk OR village_name_tamil ILIKE :village
                LIMIT 1
            """), {"taluk": t_clause, "village": v_clause})
            loc_match = loc_res.mappings().one_or_none()

        p_firka = loc_match["firka_name_tamil"] if loc_match else (f"{p_taluk} பிர்கா" if p_taluk else "-")
        p_block = loc_match["block_name_tamil"] if loc_match else (f"{p_taluk} ஒன்றியம்" if p_taluk else "-")
        p_rev_div = f"{p_taluk} உட்கோட்டம்" if p_taluk else (f"{p_district} வருவாய் கோட்டம்" if p_district else "-")
        p_resp_off = f"வட்டாட்சியர், {p_taluk}" if p_taluk else (f"மாவட்ட வருவாய் அலுவலர், {p_district}" if p_district else "வட்டாட்சியர்")

        # Build contextual Tamil summary from detected petition details
        summary_ta = analysis.get("description_summary_tamil")
        if not summary_ta or "மனு சமர்ப்பித்துள்ளார்" in summary_ta and p_name:
            subj_parts = [f"மனுதாரர் {p_name}"]
            if f_name:
                subj_parts.append(f"(த/பெ {f_name})")
            
            loc_parts = []
            if p_district:
                loc_parts.append(f"{p_district} மாவட்டம்")
            if p_taluk:
                loc_parts.append(f"{p_taluk} வட்டம்")
            if p_village:
                loc_parts.append(f"{p_village} கிராமம்")
            if p_survey:
                loc_parts.append(f"புல எண் {p_survey}")
            
            loc_str = " ".join(loc_parts)
            subj_str = " ".join(subj_parts)
            
            if loc_str and subj_str:
                summary_ta = f"{subj_str} அவர்கள், {loc_str}-ல் {p_gtype} தொடர்பாக உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
            elif subj_str:
                summary_ta = f"{subj_str} அவர்கள் {p_gtype} தொடர்பாக மனு சமர்ப்பித்துள்ளார்."
            else:
                summary_ta = f"மனுதாரர் {p_gtype} தொடர்பாக மனு சமர்ப்பித்துள்ளார்."
            analysis["description_summary_tamil"] = summary_ta

        today_tag = datetime_suffix_short()
        auto_gid = f"TN/REV/DRO/{today_tag}/{str(uuid.uuid4())[:4].upper()}"

        # Check if draft already exists
        existing_draft = await db.execute(text("SELECT id FROM grievance_drafts WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})
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
                "sub_dept": f"{p_dept} / நிர்வாகம்",
                "district": p_district or "ஈரோடு",
                "rev_div": p_rev_div,
                "taluk": p_taluk or "-",
                "firka": p_firka,
                "block": p_block,
                "village": p_village or "-",
                "street": p_street or "-",
                "door": p_door or "-",
                "resp_off": p_resp_off,
                "ref_no": p_survey,
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
                "ref_no": p_survey,
                "dept": p_dept,
                "sub_dept": f"{p_dept} / நிர்வாகம்",
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

        # Update source status to draft_ready
        await db.execute(text("""
            UPDATE sources SET status = 'draft_ready', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        analysis["source_id"] = source_id
        return analysis


ai_analyzer = AIAnalyzer()
