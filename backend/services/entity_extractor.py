import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple, TYPE_CHECKING

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
    """
    Production-grade Tamil Grievance Entity Extractor:
    - Regex pattern matcher for structured data (Phone, Aadhaar with masking, Survey No, Pincode, INR)
    - Structural parser for Tamil government petition salutations (From, To, Subject, Details)
    - Bilingual entity recognition (Tamil & English)
    - Fast deduplication & batch database persistence
    - Master location verification
    """

    PATTERNS = {
        "phone": r'(?:\+91[\s\-]?)?(?:(?:செல்|தொலைபேசி|Phone|Ph|Cell|Mobile)\s*[:\.]?\s*)?[6-9]\d{4}[\s\-]?\d{5}|(?:\+91[\s\-]?)?[6-9]\d{9}',
        "aadhaar": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        "survey_no": r'(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*\b\d{1,4}(?:/\d{1,3}[A-Za-z0-9]*)?\b|\b\d{1,4}/\d{1,3}[A-Za-z0-9]*\b',
        "file_number": r'\b\d{1,6}/[A-Za-z0-9\-]{2,10}/\d{4}\b',
        "date_dmy": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b',
        "pincode": r'(?:Pin|Pincode|பின்கோடு)\s*[:\.]?\s*\b6\d{2}[\s\-]?\d{3}\b|\b6\d{2}\s?\d{3}\b',
        "amount_inr": r'₹?\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?\s*(?:கோடி|லட்சம்|ரூபாய்|ரூ\.|Rs\.?|INR)'
    }

    SENDER_HEADERS = [
        "அனுப்புநர்", "அனுப்புனர்", "விண்ணப்பதாரர்", "மனுதாரர்",
        "மனுவழங்குபவர்", "இடமிருந்து", "From", "Sender", "Petitioner"
    ]

    STOP_HEADERS = [
        "பெறுநர்", "பெறுனர்", "பொருள்", "நாள் :", "நாள்:", "பார்வை",
        "அய்யா", "ஐயா", "வணக்கம்", "Sir", "Madam", "Sub:", "Ref:", "To:"
    ]

    def __init__(self, llm=llm_client):
        self.llm = llm

    def _mask_aadhaar(self, aadhaar_str: str) -> str:
        """Aadhaar masking: Never store raw 12 digits. Keep only last 4 digits (XXXX-XXXX-1234)."""
        digits = re.sub(r'\D', '', aadhaar_str)
        if len(digits) == 12:
            return f"XXXX-XXXX-{digits[-4:]}"
        return aadhaar_str

    def _clean_text_artifacts(self, text_val: str) -> str:
        """Removes OCR scanner noise, pipe symbols, brackets, and spurious characters."""
        cleaned = re.sub(r'[|{}\[\]<>~`@#$%^&*()_=+]', '', text_val)
        return " ".join(cleaned.split()).strip()

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
                    val = re.sub(
                        r'^(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*',
                        '', val, flags=re.IGNORECASE
                    ).strip()

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
        """Parses standard Tamil and bilingual petition headers (From, To, Subject, Details)."""
        entities = []
        if not full_text:
            return entities

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]

        # 1. Sender Section Detection
        for i, line in enumerate(lines):
            if any(k in line for k in self.SENDER_HEADERS):
                sender_lines = lines[i + 1:i + 10]
                for s_line in sender_lines:
                    if any(stop_k in s_line for stop_k in self.STOP_HEADERS):
                        break

                    # Petitioner Name extraction
                    if not any(e["entity_type"] == "petitioner_name" for e in entities):
                        clean_name = re.sub(
                            r'^(?:திரு|திருமதி|செல்வி|மனுதாரர்|பெயர்|விண்ணப்பதாரர்|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Thiru)\s*[:\.]?\s*',
                            '', s_line, flags=re.IGNORECASE
                        ).strip()
                        # Clean OCR artifacts: stray digits, pipes, punctuation
                        clean_name = re.sub(r'[|{}\[\]<>~`@#$%^&*()_=+0-9]', '', clean_name).strip().rstrip(",")
                        if len(clean_name) >= 3 and not clean_name.lower().startswith("d.n") and not clean_name.lower().startswith("no"):
                            entities.append({
                                "entity_type": "petitioner_name",
                                "entity_value": clean_name,
                                "confidence": 0.95,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })

                    # Father/Husband Name
                    if any(f_prefix in s_line for f_prefix in ["S/o", "D/o", "W/o", "Wo", "த/பெ", "க/பெ", "தந்தை", "கணவர்", "Father", "Husband"]):
                        clean_f = re.sub(
                            r'.*?(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|தந்தை|கணவர்|Father|Husband)\s*(?:Late)?\s*[:\.]?\s*',
                            '', s_line, flags=re.IGNORECASE
                        ).strip()
                        clean_f = re.sub(r'[|{}\[\]<>~`@#$%^&*()_=+0-9]', '', clean_f).strip().rstrip(",")
                        if clean_f and len(clean_f) >= 3:
                            entities.append({
                                "entity_type": "father_husband_name",
                                "entity_value": clean_f,
                                "confidence": 0.95,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })

                    # Address Line
                    if any(a_k in s_line for a_k in [
                        "D.No", "D.N", "எண்", "வீதி", "Street", "தெரு", "பாளையம",
                        "பாளையம்", "நகர்", "Nagar", "8/", "Road", "Lane", "Main"
                    ]):
                        addr_val = self._clean_text_artifacts(s_line.rstrip(","))
                        if len(addr_val) >= 5:
                            entities.append({
                                "entity_type": "address",
                                "entity_value": addr_val,
                                "confidence": 0.90,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })

        # Dynamic Segment extraction for Taluk, District, Village
        for line in lines:
            segments = [s.strip() for s in re.split(r'[,;\n]', line) if s.strip()]
            for seg in segments:
                # District extraction first
                d_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Dt\)|\(மாவட்டம்\)|மாவட்டம்|District)', seg, re.IGNORECASE)
                if d_match:
                    d_val = self._clean_text_artifacts(d_match.group(1)).strip(":, ")
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
                # Taluk extraction (strictly excluding மாவட்டம் segments)
                elif not any(k in seg for k in ["மாவட்டம்", "(Dt)", "District"]):
                    t_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Tk\)|\(வட்டம்\)|வட்டம்|Taluk)', seg, re.IGNORECASE)
                    if t_match:
                        t_val = self._clean_text_artifacts(t_match.group(1)).strip(":, ")
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

                # Village extraction
                v_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Po\)|\(கிராமம்\)|கிராமம்|Village)', seg, re.IGNORECASE)
                if v_match:
                    v_val = self._clean_text_artifacts(v_match.group(1)).strip(":, ")
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
            if any(g_k in line for g_k in ["குறையின் வகை", "பொருள்", "Subject", "Land", "நில", "பட்டா", "முதியோர் உதவி", "சாலை", "குடிநீர்", "ஆக்கிரமிப்பு"]):
                clean_g = re.sub(r'^(?:குறையின் வகை|பொருள்|Subject)\s*[:\.]?\s*', '', line, flags=re.IGNORECASE).strip()
                clean_g = self._clean_text_artifacts(clean_g)
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
                clean_val = self._clean_text_artifacts(str(val))
                if clean_val:
                    entities.append({
                        "entity_type": etype,
                        "entity_value": clean_val,
                        "confidence": 0.88,
                        "source_page": page,
                        "source_chunk_id": chunk_id,
                        "extracted_by": "ai_ner",
                        "validation_status": "pending",
                        "officer_corrected": False
                    })

        return entities

    async def _validate_locations(self, db: AsyncSession, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate village, taluk, and district against master_locations table in PostgreSQL"""
        loc_entities = [e for e in entities if e["entity_type"] in ["village", "taluk", "district"]]
        if not loc_entities:
            return entities

        for e in loc_entities:
            val = e["entity_value"]
            if not val or len(val) < 2:
                continue
            try:
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
            except Exception as ex:
                logger.warning(f"Error validating location '{val}': {ex}")

        return entities

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates extracted entities across regex, structural, and AI extraction passes.
        Prefers verified status and higher confidence.
        """
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for e in entities:
            etype = e["entity_type"]
            val_norm = e["entity_value"].strip().lower()[:40]
            key = (etype, val_norm)

            if key not in seen:
                seen[key] = e
            else:
                existing = seen[key]
                # Upgrade if current has higher confidence or verified status
                if e.get("validation_status") == "verified" and existing.get("validation_status") != "verified":
                    seen[key] = e
                elif e.get("confidence", 0) > existing.get("confidence", 0):
                    seen[key] = e

        return list(seen.values())

    async def extract_all(self, db: AsyncSession, source_id: str) -> List[Dict[str, Any]]:
        # 1. Fetch all OCR pages
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

        # 2. Location Validation
        validated = await self._validate_locations(db, entities)

        # 3. Deduplicate
        deduped = self._deduplicate_entities(validated)

        # 4. Clean previous entities for this source
        await db.execute(
            text("DELETE FROM extracted_entities WHERE source_id = CAST(:source_id AS UUID)"),
            {"source_id": source_id}
        )

        # 5. Batch Persist using SQLAlchemy execute batch
        if deduped:
            batch_params = [
                {
                    "source_id": source_id,
                    "type": e["entity_type"],
                    "value": e["entity_value"],
                    "conf": e["confidence"],
                    "status": e.get("validation_status", "pending"),
                    "page": e.get("source_page"),
                    "chunk_id": e.get("source_chunk_id"),
                    "by": e.get("extracted_by", "regex"),
                    "corrected": e.get("officer_corrected", False)
                }
                for e in deduped
            ]
            await db.execute(text("""
                INSERT INTO extracted_entities 
                    (source_id, entity_type, entity_value, confidence, validation_status, source_page, source_chunk_id, extracted_by, officer_corrected)
                VALUES 
                    (CAST(:source_id AS UUID), :type, :value, :conf, :status, :page, :chunk_id, :by, :corrected)
            """), batch_params)

        # 6. Update source status
        await db.execute(text("""
            UPDATE sources SET status = 'entity_extracting', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        return deduped


entity_extractor = EntityExtractor()
