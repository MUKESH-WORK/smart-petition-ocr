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
    Intelligent Cognitive Entity Extractor:
    - LLM-first cognitive extraction for dynamic, format-agnostic petition parsing
    - Zero hardcoded sender/stop header gates to eliminate pipeline deadlocks across diverse formats
    - Strict anti-hallucination barrier with text grounding validation against source OCR
    - Deterministic syntactic extraction for universal tokens (phone, masked Aadhaar, pincode)
    - Master location database validation against official Tamil Nadu revenue locations
    """

    # Deterministic syntactic patterns for numbers/codes
    PATTERNS = {
        "phone": r'(?:\+91[\s\-]?)?(?:(?:செல்|தொலைபேசி|அலைபேசி|Phone|Ph|Cell|Mobile)\s*[:\.]?\s*)?\b[6-9]\d{4}[\s\-]?\d{5}\b|\b[6-9]\d{9}\b',
        "aadhaar": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        "survey_no": r'(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*\b\d{1,4}(?:/\d{1,3}[A-Za-z0-9]*)?\b|\b\d{1,4}/\d{1,3}[A-Za-z0-9]*\b',
        "petition_no": r'#\s*([A-Za-z0-9\-]*\d{6,10})\s*#|\b(?:மனு\s*எண்|Petition\s*No\.?)\s*:?[\s\-]*([A-Za-z0-9\-]+)\b',
        "file_number": r'\b\d{1,6}/[A-Za-z0-9\-]{2,10}/\d{4}\b',
        "date_dmy": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b',
        "pincode": r'(?:Pin|Pincode|பின்கோடு)\s*[:\.]?\s*\b6\d{2}[\s\-]?\d{3}\b|\b6\d{2}\s?\d{3}\b',
        "amount_inr": r'₹?\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?\s*(?:கோடி|லட்சம்|ரூபாய்|ரூ\.|Rs\.?|INR)'
    }

    # Strict anti-hallucination & negative template filter
    INVALID_TEMPLATE_VALUES = {
        "விண்ணப்பதாரர் பெயர்", "தந்தை அல்லது கணவர் பெயர்", "தந்தை பெயர்",
        "கணவர் பெயர்", "முழு முகவரி", "கிராமம்", "வட்டம்", "மாவட்டம்",
        "சுருக்கமான கோரிக்கை", "null", "none", "n/a", "தெரியவில்லை", "இல்லை",
        "விண்ணப்பதாரர் பெயர் அல்லது null", "தந்தை அல்லது கணவர் பெயர் அல்லது null",
        "முழு முகவரி அல்லது null", "கிராமம் அல்லது null", "வட்டம் அல்லது null", "மாவட்டம் அல்லது null",
        "சுருக்கமான கோரிக்கை அல்லது null", "நான்", "நாங்கள்", "அவர்கள்", "இவர்", "மனுதாரர்",
        "விண்ணப்பதாரர்", "பொதுமக்கள்", "-", "--", "none", "unknown"
    }

    def __init__(self, llm=llm_client):
        self.llm = llm

    @staticmethod
    def _repair_phone(raw_str: str) -> Optional[str]:
        tr = str.maketrans('BbposlIzZ', '864051122')
        subbed = raw_str.translate(tr)
        digits = re.sub(r'\D', '', subbed)
        if len(digits) >= 10 and digits[-10] in '6789':
            return digits[-10:]
        return None

    def _is_invalid_value(self, val: str) -> bool:
        if not val or not isinstance(val, str):
            return True
        v = val.strip().lower()
        if v in [iv.lower() for iv in self.INVALID_TEMPLATE_VALUES]:
            return True
        if "அல்லது null" in v or "விண்ணப்பதாரர் பெயர்" in v or "முழு முகவரி" in v:
            return True
        if v in ["-", "--", "null", "none", "n/a", ""]:
            return True
        return False

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

    def _is_grounded_in_text(self, val: str, full_text: str) -> bool:
        """
        Anti-Hallucination Barrier: Verifies if the extracted value is actually grounded in source text.
        Returns True if the full string or majority of its non-stop words exist in source text.
        """
        if not val or not full_text:
            return False
        v_clean = re.sub(r'[^\w\s]', '', val).strip().lower()
        f_clean = re.sub(r'[^\w\s]', '', full_text).lower()

        if v_clean in f_clean:
            return True

        # Check word-level overlap for multi-word phrases (e.g. addresses or full names)
        words = [w for w in v_clean.split() if len(w) >= 3 and w not in ["the", "and", "வட்டம்", "மாவட்டம்", "கிராமம்"]]
        if not words:
            return v_clean in f_clean

        matched_words = sum(1 for w in words if w in f_clean)
        return (matched_words / len(words)) >= 0.5

    def _extract_regex(self, full_text: str, page_number: int, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Deterministic syntactic extraction for structured numbers/codes."""
        entities = []
        if not full_text:
            return entities

        for etype, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for m in matches:
                val = m.group(1) if m.groups() and m.group(1) else m.group(0).strip()
                if etype == "phone":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) >= 10:
                        val = digits[-10:]
                    else:
                        continue
                elif etype == "petition_no":
                    val = re.sub(r'[#\s]', '', val).strip()
                    if not val or len(val) < 5:
                        continue
                elif etype == "pincode":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) == 6:
                        val = digits
                    else:
                        continue
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
                    "validation_status": "verified" if etype in ["phone", "pincode", "aadhaar", "petition_no"] else "pending",
                    "source_page": page_number,
                    "source_chunk_id": chunk_id,
                    "extracted_by": "regex",
                    "officer_corrected": False
                })

        # Scan for handwritten phone numbers with OCR substitutions (e.g., 9529Bp585b)
        if not any(e["entity_type"] == "phone" for e in entities):
            raw_phone_candidates = re.findall(r'[6-9][0-9A-Za-z]{9,11}', full_text)
            for c in raw_phone_candidates:
                repaired = self._repair_phone(c)
                if repaired:
                    entities.append({
                        "entity_type": "phone",
                        "entity_value": repaired,
                        "confidence": 0.92,
                        "validation_status": "verified",
                        "source_page": page_number,
                        "source_chunk_id": chunk_id,
                        "extracted_by": "regex_repaired",
                        "officer_corrected": False
                    })
                    break

        return entities

    def _extract_structural_entities(self, full_text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Resilient structural scanner without rigid sender/stop header gating.
        Scans lines directly for relationships (S/o, W/o, D/o), addresses, taluks, districts, and subjects.
        """
        entities = []
        if not full_text:
            return entities

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]

        for line_idx, line in enumerate(lines):
            clean_l = self._clean_text_artifacts(line)
            if not clean_l or self._is_invalid_value(clean_l):
                continue

            # 1. Father/Husband Relationship Extraction (e.g. S/o, W/o, D/o, த/பெ, க/பெ, மகன், மனைவி)
            if any(f_prefix in clean_l for f_prefix in ["S/o", "D/o", "W/o", "Wo", "த/பெ", "க/பெ", "த/\s*ப", "தந்தை", "கணவர்", "Father", "Husband", "மகன்", "மனைவி"]):
                clean_f = re.sub(
                    r'.*?(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband|மகன்|மனைவி)\s*(?:Late)?\s*[:\.]?\s*',
                    '', clean_l, flags=re.IGNORECASE
                ).strip()
                clean_f = re.sub(r'[0-9]', '', clean_f).strip().rstrip(",")
                clean_f = re.sub(r'(?<=[\u0B80-\u0BFF])\s+(?=[\u0B80-\u0BFF])', '', clean_f)
                if clean_f and len(clean_f) >= 3 and not self._is_invalid_value(clean_f):
                    entities.append({
                        "entity_type": "father_husband_name",
                        "entity_value": clean_f,
                        "confidence": 0.95,
                        "source_page": page_number,
                        "extracted_by": "structural",
                        "validation_status": "pending",
                        "officer_corrected": False
                    })

            # 2. Petitioner Name extraction from sender-like lines
            if not any(e["entity_type"] == "petitioner_name" for e in entities):
                # Detect lines with personal titles or top non-header lines
                if any(k in clean_l for k in ["திரு", "திருமதி", "செல்வி", "Mr.", "Mrs.", "Ms.", "Smt.", "Thiru"]):
                    clean_name = re.sub(
                        r'^(?:திரு|திருமதி|செல்வி|மனுதாரர்|பெயர்|விண்ணப்பதாரர்|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Thiru)\s*[:\.]?\s*',
                        '', clean_l, flags=re.IGNORECASE
                    ).strip()
                    clean_name = re.sub(r'\(\d+\)|\d+', '', clean_name).strip()
                    clean_name = re.sub(r'(?<=[\u0B80-\u0BFF])\s+(?=[\u0B80-\u0BFF])', '', clean_name)
                    if len(clean_name) >= 3 and not self._is_invalid_value(clean_name):
                        entities.append({
                            "entity_type": "petitioner_name",
                            "entity_value": clean_name,
                            "confidence": 0.95,
                            "source_page": page_number,
                            "extracted_by": "structural",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

            # 3. District & Taluk segment extraction
            segments = [s.strip() for s in re.split(r'[,;\n]', line) if s.strip()]
            for seg in segments:
                # District
                d_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Dt\)|\(மாவட்டம்\)|மாவட்டம்|District)', seg, re.IGNORECASE)
                if d_match:
                    d_val = self._clean_text_artifacts(d_match.group(1)).strip(":, ")
                    if len(d_val) >= 2 and not any(e["entity_type"] == "district" and e["entity_value"] == d_val for e in entities):
                        entities.append({
                            "entity_type": "district",
                            "entity_value": d_val,
                            "confidence": 0.94,
                            "source_page": page_number,
                            "extracted_by": "structural",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })
                # Taluk
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
                                "extracted_by": "structural",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })

            # 4. Grievance Subject extraction
            if any(g_k in line for g_k in ["குறையின் வகை", "பொருள்", "ப்:", "Subject", "Land", "நில", "பட்டா", "முதியோர் உதவி", "சாலை", "குடிநீர்", "ஆக்கிரமிப்பு", "ஆதார்", "வாரிசு"]):
                clean_g = re.sub(r'^(?:குறையின் வகை|பொருள்|ப்:|Subject)\s*[:\.\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                clean_g = self._clean_text_artifacts(clean_g).strip(":- ")
                if not clean_g or self._is_invalid_value(clean_g) or clean_g in ["-", "--"]:
                    # Look at next line for subject
                    for next_l in lines[line_idx + 1:line_idx + 4]:
                        clean_cand = self._clean_text_artifacts(next_l).strip(":- ")
                        if clean_cand and not self._is_invalid_value(clean_cand):
                            clean_g = clean_cand
                            break

                if clean_g and not self._is_invalid_value(clean_g) and clean_g not in ["-", "--"] and not any(e["entity_type"] == "grievance_type" for e in entities):
                    entities.append({
                        "entity_type": "grievance_type",
                        "entity_value": clean_g,
                        "confidence": 0.95,
                        "source_page": page_number,
                        "extracted_by": "structural",
                        "validation_status": "pending",
                        "officer_corrected": False
                    })

        return entities

    async def _extract_ai(self, text_content: str, page: int, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Primary Cognitive Extraction Engine (LLM/VLM style):
        Dynamically extracts all petition entities without brittle regex or header assumptions.
        Enforces strict grounding against the source OCR text.
        """
        prompt = f"""Extract all structured administrative entities from this Tamil petition text into a JSON object:
{{
  "petitioner_name": "Full legal name of the applicant/petitioner, or null",
  "father_husband_name": "Father or husband name if stated, or null",
  "gender": "Male or Female",
  "phone": "10-digit mobile number, or null",
  "alternate_phone": "Alternate phone number, or null",
  "door_no": "Door/House number, or null",
  "street_name": "Street or road name, or null",
  "village": "Village, town, or residential area, or null",
  "taluk": "Taluk name, or null",
  "district": "District name, or null",
  "pincode": "6-digit postal pincode, or null",
  "survey_no": "Survey number or SF No, or null",
  "grievance_type": "Primary grievance category (e.g. வாரிசு சான்றிதழ், பட்டா மாறுதல், ஓய்வூதியம், ஆக்கிரமிப்பு, குடிநீர், சாலை, மின்சாரம்)",
  "grievance_subtype": "Specific grievance sub-type or scheme name",
  "full_address": "Complete residential address, or null"
}}

IMPORTANT RULES:
1. Do NOT hallucinate. Only extract values present in the petition text.
2. If applicant is 'Maragatham W/o Chinnasamy', petitioner_name is 'Maragatham' and father_husband_name is 'Chinnasamy'.
3. Never output pronouns like 'நான்', 'நாங்கள்', 'மனுதாரர்', or punctuation '-' as a name or category.
4. Respond ONLY with valid JSON.

Petition Text:
{text_content[:2500]}
"""
        try:
            response = await self.llm.achat(prompt, temperature=0.1, max_tokens=768, json_mode=True)
            parsed = extract_json_object(response) or {}
        except Exception as e:
            logger.warning(f"AI entity extraction call notice: {e}")
            parsed = {}

        mappings = {
            "petitioner_name": "petitioner_name",
            "father_husband_name": "father_husband_name",
            "phone": "phone",
            "alternate_phone": "alternate_phone",
            "door_no": "door_no",
            "street_name": "street_name",
            "village": "village",
            "taluk": "taluk",
            "district": "district",
            "pincode": "pincode",
            "survey_no": "survey_no",
            "grievance_type": "grievance_type",
            "grievance_subtype": "grievance_subtype",
            "full_address": "address"
        }

        entities = []
        for key, etype in mappings.items():
            val = parsed.get(key)
            if not val or val == "null" or str(val).startswith("[தகவல்") or self._is_invalid_value(str(val)):
                continue

            clean_val = self._clean_text_artifacts(str(val))
            if not clean_val or self._is_invalid_value(clean_val):
                continue

            # Anti-hallucination verification: Ensure entity is grounded in text content
            is_grounded = self._is_grounded_in_text(clean_val, text_content)
            if not is_grounded:
                # If value is not found in source text, reject hallucination
                logger.debug(f"Rejecting ungrounded AI entity: {etype}='{clean_val}'")
                continue

            # Syntactic normalizations
            if etype in ["phone", "alternate_phone"]:
                digits = re.sub(r'\D', '', clean_val)
                if len(digits) >= 10 and digits[-10] in '6789':
                    clean_val = digits[-10:]
                else:
                    continue
            elif etype == "pincode":
                digits = re.sub(r'\D', '', clean_val)
                if len(digits) == 6:
                    clean_val = digits
                else:
                    continue
            elif etype == "petitioner_name":
                clean_val = re.sub(r'\(\d+\)|\d+', '', clean_val).strip()
                if self._is_invalid_value(clean_val):
                    continue

            entities.append({
                "entity_type": etype,
                "entity_value": clean_val,
                "confidence": 0.96,
                "source_page": page,
                "source_chunk_id": chunk_id,
                "extracted_by": "ai_ner",
                "validation_status": "verified" if etype in ["phone", "pincode"] else "pending",
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
        Prefers verified status, AI extraction, and higher confidence.
        """
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for e in entities:
            if self._is_invalid_value(e.get("entity_value", "")):
                continue
            etype = e["entity_type"]
            val_norm = e["entity_value"].strip().lower()[:40]
            key = (etype, val_norm)

            if key not in seen:
                seen[key] = e
            else:
                existing = seen[key]
                # Upgrade if current has verified status or higher confidence
                if e.get("validation_status") == "verified" and existing.get("validation_status") != "verified":
                    seen[key] = e
                elif e.get("extracted_by") == "ai_ner" and existing.get("extracted_by") != "ai_ner" and existing.get("validation_status") != "verified":
                    seen[key] = e
                elif e.get("confidence", 0) > existing.get("confidence", 0):
                    seen[key] = e

        return list(seen.values())

    async def extract_all(self, db: AsyncSession, source_id: str) -> List[Dict[str, Any]]:
        """
        Executes end-to-end cognitive extraction:
        1. Universal syntactic regex tokens (phone, masked Aadhaar, pincode)
        2. Primary cognitive LLM extraction with strict grounding
        3. Resilient structural fallback if needed
        4. Location verification against master database
        5. Deduplication and batch persistence
        """
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
            if not f_text.strip():
                continue

            # Deterministic number/code extraction
            regex_ents = self._extract_regex(f_text, p["page_number"])
            entities.extend(regex_ents)

            # Primary cognitive LLM extraction
            ai_ents = await self._extract_ai(f_text, p["page_number"])
            entities.extend(ai_ents)

            # Resilient structural fallback if AI returned sparse entities
            if len(ai_ents) < 2:
                struct_ents = self._extract_structural_entities(f_text, p["page_number"])
                entities.extend(struct_ents)

        # 2. Location Validation against master PostgreSQL table
        validated = await self._validate_locations(db, entities)

        # 3. Deduplicate prioritizing verified/grounded entities
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
                    "by": e.get("extracted_by", "ai_ner"),
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
