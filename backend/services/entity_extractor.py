import re
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
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
from core.llm_client import llm_client, extract_json_object

logger = logging.getLogger(__name__)


class EntityExtractor:
    PATTERNS = {
        "phone": r'(?:\+91[\s\-]?)?(?:(?:செல்|தொலைபேசி|Phone|Ph|Cell)\s*[:\.]?\s*)?[6-9]\d{4}[\s\-]?\d{5}|(?:\+91[\s\-]?)?[6-9]\d{9}',
        "aadhaar": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        "survey_no": r'(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?)\s*:?[\s\-]*\b\d{1,4}(?:/\d{1,3}[A-Za-z0-9]*)?\b|\b\d{1,4}/\d{1,3}[A-Za-z0-9]*\b',
        "file_number": r'\b\d{1,6}/[A-Za-z0-9\-]{2,10}/\d{4}\b',
        "date_dmy": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b',
        "pincode": r'(?:Pin\s*[:\.]?\s*)?\b6\d{2}[\s\-]?\d{3}\b',
        "amount_inr": r'₹?\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?\s*(?:கோடி|லட்சம்|ரூபாய்|ரூ\.|Rs\.?)'
    }

    def __init__(self, llm=llm_client):
        self.llm = llm

    def _mask_aadhaar(self, aadhaar_str: str) -> str:
        """Aadhaar masking: Never store raw 12 digits. Keep only last 4 digits."""
        digits = re.sub(r'\D', '', aadhaar_str)
        if len(digits) == 12:
            return f"XXXX-XXXX-{digits[-4:]}"
        return aadhaar_str

    def _extract_regex(self, full_text: str, page_number: int, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        entities = []
        if not full_text:
            return entities

        for etype, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for m in matches:
                val = m.group(0).strip()
                # Clean up prefixes and internal spaces
                if etype == "phone":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) >= 10:
                        val = digits[-10:]
                elif etype == "pincode":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) == 6:
                        val = digits
                elif etype == "aadhaar":
                    val = self._mask_aadhaar(val)
                elif etype == "survey_no":
                    val = re.sub(r'^(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?)\s*:?[\s\-]*', '', val, flags=re.IGNORECASE).strip()

                entities.append({
                    "entity_type": etype,
                    "entity_value": val,
                    "confidence": 0.98,
                    "validation_status": "verified" if etype in ["phone", "pincode", "aadhaar"] else "pending",
                    "source_page": page_number,
                    "source_chunk_id": chunk_id,
                    "extracted_by": "regex",
                    "officer_corrected": False
                })
        return entities

    def _extract_structural_entities(self, full_text: str, page_number: int) -> List[Dict[str, Any]]:
        """Parses standard Tamil government petition sender, recipient, and subject blocks."""
        entities = []
        if not full_text:
            return entities

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        
        # 1. Look for Sender / மனுதாரர் / அனுப்புநர் section
        for i, line in enumerate(lines):
            if any(k in line for k in ["அனுப்புநர்", "அனுப்புனர்", "விண்ணப்பதாரர்", "மனுதாரர்"]):
                sender_lines = lines[i+1:i+8]
                for s_line in sender_lines:
                    if any(stop_k in s_line for stop_k in ["பெறுநர்", "பொருள்", "நாள் :", "நாள்:"]):
                        break
                    
                    # Petitioner Name extraction
                    if not any(e["entity_type"] == "petitioner_name" for e in entities):
                        clean_name = re.sub(r'^(?:திரு|திருமதி|செல்வி|மனுதாரர்|பெயர்|S/o|D/o|W/o)\s*[:\.]?\s*', '', s_line).strip()
                        if len(clean_name) > 2 and not any(c.isdigit() for c in clean_name[:4]) and not clean_name.lower().startswith("d.n"):
                            entities.append({
                                "entity_type": "petitioner_name",
                                "entity_value": clean_name.rstrip(","),
                                "confidence": 0.95,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })
                    
                    # Father/Husband name
                    if any(f_prefix in s_line for f_prefix in ["S/o", "D/o", "W/o", "Wo", "த/பெ", "க/பெ", "தந்தை", "கணவர்"]):
                        clean_f = re.sub(r'.*?(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|தந்தை|கணவர்)\s*(?:Late)?\s*[:\.]?\s*', '', s_line).strip()
                        if clean_f:
                            entities.append({
                                "entity_type": "father_husband_name",
                                "entity_value": clean_f.rstrip(","),
                                "confidence": 0.95,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })
                    
                    # Address line
                    if any(a_k in s_line for a_k in ["D.No", "D.N", "எண்", "வீதி", "Street", "தெரு", "பாளையம", "பாளையம்", "நகர்", "Nagar", "8/"]):
                        entities.append({
                            "entity_type": "address",
                            "entity_value": s_line.rstrip(","),
                            "confidence": 0.90,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

        # Dynamic Segment extraction for Taluk, District, Village, Door, Street
        for line in lines:
            segments = [s.strip() for s in re.split(r'[,;\n]', line) if s.strip()]
            for seg in segments:
                # Taluk extraction from segments with (Tk), (வட்டம்), வட்டம், Taluk
                t_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Tk\)|\(வட்டம்\)|வட்டம்|Taluk)', seg, re.IGNORECASE)
                if t_match:
                    t_val = t_match.group(1).strip().strip(":,")
                    if len(t_val) >= 2 and not any(e["entity_type"] == "taluk" and e["entity_value"] == t_val for e in entities):
                        entities.append({
                            "entity_type": "taluk",
                            "entity_value": t_val,
                            "confidence": 0.94,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

                # District extraction from segments with (Dt), (மாவட்டம்), மாவட்டம், District
                d_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Dt\)|\(மாவட்டம்\)|மாவட்டம்|District)', seg, re.IGNORECASE)
                if d_match:
                    d_val = d_match.group(1).strip().strip(":,")
                    if len(d_val) >= 2 and not any(e["entity_type"] == "district" and e["entity_value"] == d_val for e in entities):
                        entities.append({
                            "entity_type": "district",
                            "entity_value": d_val,
                            "confidence": 0.94,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

                # Village extraction from segments with (Po), (கிராமம்), கிராமம், Village, பாளையம்
                v_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Po\)|\(கிராமம்\)|கிராமம்|Village)', seg, re.IGNORECASE)
                if v_match:
                    v_val = v_match.group(1).strip().strip(":,")
                    if len(v_val) >= 2 and not any(e["entity_type"] == "village" and e["entity_value"] == v_val for e in entities):
                        entities.append({
                            "entity_type": "village",
                            "entity_value": v_val,
                            "confidence": 0.92,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

            # Grievance category extraction
            if any(g_k in line for g_k in ["குறையின் வகை", "பொருள்", "Land", "நில", "பட்டா", "முதியோர் உதவி", "சாலை", "குடிநீர்", "ஆக்கிரமிப்பு"]):
                clean_g = re.sub(r'^(?:குறையின் வகை|பொருள்)\s*[:\.]?\s*', '', line).strip()
                if clean_g and not any(e["entity_type"] == "grievance_type" for e in entities):
                    entities.append({
                        "entity_type": "grievance_type",
                        "entity_value": clean_g,
                        "confidence": 0.95,
                        "source_page": page_number,
                        "extracted_by": "regex",
                        "validation_status": "pending",
                        "officer_corrected": False
                    })

        return entities

    async def _extract_ai(self, text_content: str, page: int, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        prompt = f"""
கீழ்கண்ட தமிழ் மனு உரையிலிருந்து முக்கியமான நபர்கள், முகவரி மற்றும் இருப்பிட தகவல்களை மட்டும் பிரித்தெடு.
கற்பனை செய்யாதே. உரையில் உள்ளதை மட்டும் எழுது.

உரை:
{text_content[:2500]}

JSON வடிவம்:
{{
  "petitioner_name": "விண்ணப்பதாரர் பெயர் அல்லது null",
  "father_husband_name": "தந்தை அல்லது கணவர் பெயர் அல்லது null",
  "address": "முழு முகவரி அல்லது null",
  "village": "கிராமம் அல்லது null",
  "taluk": "வட்டம் அல்லது null",
  "district": "மாவட்டம் அல்லது null",
  "grievance_subject": "சுருக்கமான கோரிக்கை அல்லது null"
}}
"""
        response = await self.llm.achat(prompt, temperature=0.1, max_tokens=512, json_mode=True)
        parsed = extract_json_object(response) or {}
        
        if not parsed:
            # Heuristic extraction fallback
            for line in text_content.split("\n"):
                if "மனுதாரர்:" in line or "பெயர்:" in line:
                    parsed["petitioner_name"] = line.replace("மனுதாரர்:", "").replace("பெயர்:", "").strip()
                if "வட்டம்" in line:
                    parsed["taluk"] = line.strip()

        mappings = {
            "petitioner_name": "petitioner_name",
            "father_husband_name": "father_husband_name",
            "address": "address",
            "village": "village",
            "taluk": "taluk",
            "district": "district"
        }

        entities = []
        for key, etype in mappings.items():
            val = parsed.get(key)
            if val and val != "null" and not str(val).startswith("[தகவல்"):
                entities.append({
                    "entity_type": etype,
                    "entity_value": str(val).strip(),
                    "confidence": 0.88,
                    "source_page": page,
                    "source_chunk_id": chunk_id,
                    "extracted_by": "ai_ner",
                    "validation_status": "pending",
                    "officer_corrected": False
                })

        return entities

    async def _validate_locations(self, db: AsyncSession, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate village and taluk against master_locations table"""
        for e in entities:
            etype = e["entity_type"]
            val = e["entity_value"]

            if etype in ["village", "taluk", "district"]:
                sql = text("""
                    SELECT id, village_name_tamil, taluk_name_tamil, district_name_tamil
                    FROM master_locations
                    WHERE village_name_tamil ILIKE :val 
                       OR taluk_name_tamil ILIKE :val 
                       OR district_name_tamil ILIKE :val
                    LIMIT 1
                """)
                res = await db.execute(sql, {"val": f"%{val}%"})
                match = res.mappings().one_or_none()
                if match:
                    e["validation_status"] = "verified"
                    e["confidence"] = 0.99
                else:
                    e["validation_status"] = "suspect"

        return entities

    async def extract_all(self, db: AsyncSession, source_id: str) -> List[Dict[str, Any]]:
        # Fetch all OCR pages
        res = await db.execute(text("""
            SELECT page_number, full_text 
            FROM ocr_results 
            WHERE source_id = CAST(:source_id AS UUID)
            ORDER BY page_number
        """), {"source_id": source_id})
        pages = res.mappings().all()

        entities = []
        for p in pages:
            f_text = p["full_text"] or ""
            regex_ents = self._extract_regex(f_text, p["page_number"])
            entities.extend(regex_ents)

            struct_ents = self._extract_structural_entities(f_text, p["page_number"])
            entities.extend(struct_ents)

            if len(f_text) > 15:
                ai_ents = await self._extract_ai(f_text, p["page_number"])
                entities.extend(ai_ents)

        # Validate locations against master DB
        validated = await self._validate_locations(db, entities)

        # Delete prior entities if re-running
        await db.execute(text("DELETE FROM extracted_entities WHERE source_id = CAST(:source_id AS UUID)"), {"source_id": source_id})

        # Persist entities
        for e in validated:
            await db.execute(text("""
                INSERT INTO extracted_entities 
                    (source_id, entity_type, entity_value, confidence, validation_status, source_page, source_chunk_id, extracted_by, officer_corrected)
                VALUES 
                    (CAST(:source_id AS UUID), :type, :value, :conf, :status, :page, :chunk_id, :by, :corrected)
            """), {
                "source_id": source_id,
                "type": e["entity_type"],
                "value": e["entity_value"],
                "conf": e["confidence"],
                "status": e["validation_status"],
                "page": e.get("source_page"),
                "chunk_id": e.get("source_chunk_id"),
                "by": e["extracted_by"],
                "corrected": e.get("officer_corrected", False)
            })

        # Update source status
        await db.execute(text("""
            UPDATE sources SET status = 'entity_extracting', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        return validated


entity_extractor = EntityExtractor()
