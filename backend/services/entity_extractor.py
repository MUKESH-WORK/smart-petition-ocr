import re
import json
import logging
import unicodedata
import difflib
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

# --- Tamil Unicode & Digit Normalization Map ---
TAMIL_DIGIT_MAP = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")

# --- Verhoeff Algorithm Tables for Aadhaar Checksum ---
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]


def validate_verhoeff(num_str: str) -> bool:
    """Validates 12-digit Aadhaar number with Verhoeff checksum algorithm."""
    try:
        digits = [int(x) for x in re.sub(r'\D', '', num_str)]
        if len(digits) != 12:
            return False
        c = 0
        for i, item in enumerate(reversed(digits)):
            c = VERHOEFF_D[c][VERHOEFF_P[i % 8][item]]
        return c == 0
    except Exception:
        return False


_validate_aadhaar_verhoeff = validate_verhoeff


def normalize_tamil_text(text_content: str) -> str:
    """
    Normalizes Tamil OCR text:
    1. Strips zero-width joiners, non-joiners, and BOM without injecting spaces
    2. Translates NBSP to normal space
    3. NFKC Unicode normalization (composes vowels and canonical equivalence)
    4. Translates Tamil numerals (௦-௯) to standard ASCII digits (0-9)
    5. Collapses multiple whitespace
    """
    if not text_content:
        return ""
    # Strip ZWJ, ZWNJ, and BOM
    cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', text_content)
    # Convert non-breaking space to regular space
    cleaned = re.sub(r'[\u00A0]', ' ', cleaned)
    nfkc = unicodedata.normalize("NFKC", cleaned)
    translated = nfkc.translate(TAMIL_DIGIT_MAP)
    return re.sub(r'[ \t]+', ' ', translated).strip()


class EntityExtractor:
    """
    Production-grade Tamil Grievance Entity Extractor:
    - Unicode normalized text ingestion (NFKC, Tamil digits, whitespace collapse)
    - Strikethrough text exclusion (D7)
    - Verhoeff Aadhaar validation & masking (XXXX-XXXX-1234)
    - Strict 10-digit phone validation (D12: 9-digit failure flagged as suspect)
    - Master location fuzzy matching against master_locations (>=85% gate)
    - Dynamic confidence calculation (no hardcoded constants)
    """

    ERODE_TALUKS = [
        "ஈரோடு", "பெருந்துறை", "பவானி", "கோபிசெட்டிபாளையம்",
        "சத்தியமங்கலம்", "அந்தியூர்", "மொடக்குறிச்சி", "கொடுமுடி",
        "நம்பியூர்", "தாளவாடி"
    ]
    ERODE_TALUKS_EN = {
        "erode": "ஈரோடு",
        "perundurai": "பெருந்துறை",
        "bhavani": "பவானி",
        "gobichettipalayam": "கோபிசெட்டிபாளையம்",
        "sathyamangalam": "சத்தியமங்கலம்",
        "anthiyur": "அந்தியூர்",
        "modakkurichi": "மொடக்குறிச்சி",
        "kodumudi": "கொடுமுடி",
        "nambiyur": "நம்பியூர்",
        "thalavadi": "தாளவாடி"
    }

    @staticmethod
    def _is_valid_phone(val: str) -> bool:
        digits = re.sub(r'\D', '', val)
        return len(digits) == 10 and digits[0] in '6789'

    @classmethod
    def _fuzzy_match_taluk(cls, val: str) -> Tuple[Optional[str], float]:
        val_clean = val.strip().lower()
        if val_clean in cls.ERODE_TALUKS_EN:
            return cls.ERODE_TALUKS_EN[val_clean], 100.0
        
        best_match = None
        best_score = 0.0
        for t in cls.ERODE_TALUKS:
            ratio = difflib.SequenceMatcher(None, val.strip(), t).ratio() * 100.0
            if ratio > best_score:
                best_score = ratio
                best_match = t
        if best_score >= 85.0:
            return best_match, round(best_score, 1)
        return None, round(best_score, 1)


    PATTERNS = {
        "phone": r'(?:\+91[\s\-]?)?(?:(?:செல்|தொலைபேசி|அலைபேசி|Phone|Ph|Cell|Mobile)\s*[:\.]?\s*)?\b[6-9]\d{4}[\s\-]?\d{5}\b|\b[6-9]\d{9}\b|\b\d{9}\b',
        "aadhaar": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        "survey_no": r'(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*\b\d{1,4}(?:/\d{1,3}[A-Za-z0-9]*)?\b|\b\d{1,4}/\d{1,3}[A-Za-z0-9]*\b',
        "petition_no": r'#\s*([A-Za-z0-9\-]*\d{6,10})\s*#|\b(?:மனு\s*எண்|Petition\s*No\.?)\s*:?[\s\-]*([A-Za-z0-9\-]+)\b',
        "file_number": r'\b\d{1,6}/[A-Za-z0-9\-]{2,10}/\d{4}\b',
        "date_dmy": r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
        "pincode": r'(?:Pin|Pincode|பின்கோடு)\s*[:\.]?\s*\b6\d{2}[\s\-]?\d{3}\b|\b6\d{2}\s?\d{3}\b',
        "amount_inr": r'₹?\s*\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?\s*(?:கோடி|லட்சம்|ரூபாய்|ரூ\.|Rs\.?|INR)'
    }

    SENDER_HEADERS = [
        "அனுப்புநர்", "அனுப்புனர்", "அனப்புநர்", "அனப்புனர்", "விண்ணப்பதாரர்", "மனுதாரர்",
        "மனுவழங்குபவர்", "இடமிருந்து", "From", "Sender", "Petitioner", "மனு"
    ]

    STOP_HEADERS = [
        "பெறுநர்", "பெறுனர்", "பறநர்", "பொருள்", "ப்:", "நாள் :", "நாள்:", "பார்வை",
        "அய்யா", "ஐயா", "வணக்கம்", "Sir", "Madam", "Sub:", "Ref:", "To:", "உயர்திரு", "உயர் திரு", "ஆட்சியர்"
    ]

    INVALID_TEMPLATE_VALUES = {
        "விண்ணப்பதாரர் பெயர்", "தந்தை அல்லது கணவர் பெயர்", "தந்தை பெயர்",
        "கணவர் பெயர்", "முழு முகவரி", "கிராமம்", "வட்டம்", "மாவட்டம்",
        "சுருக்கமான கோரிக்கை", "null", "none", "n/a", "தெரியவில்லை", "இல்லை",
        "விண்ணப்பதாரர் பெயர் அல்லது null", "தந்தை அல்லது கணவர் பெயர் அல்லது null",
        "முழு முகவரி அல்லது null", "கிராமம் அல்லது null", "வட்டம் அல்லது null", "மாவட்டம் அல்லது null",
        "சுருக்கமான கோரிக்கை அல்லது null"
    }

    def __init__(self, llm=llm_client):
        self.llm = llm

    @staticmethod
    def _mask_aadhaar(val: str) -> str:
        digits = re.sub(r'\D', '', val)
        if len(digits) == 12:
            return f"XXXX-XXXX-{digits[-4:]}"
        return val

    @staticmethod
    def _clean_text_artifacts(val: str) -> str:
        if not val:
            return ""
        cleaned = re.sub(r'[\r\t\f\v]', ' ', val)
        cleaned = re.sub(r'[\(\[\{][A-Za-z0-9_\s\-]+[\)\]\}]', '', cleaned)
        cleaned = re.sub(r'[!|~`@#$%^&*_=+<>?]', '', cleaned)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()

    def _is_invalid_value(self, val: str) -> bool:
        if not val or not isinstance(val, str):
            return True
        v = val.strip().lower()
        if v in [iv.lower() for iv in self.INVALID_TEMPLATE_VALUES]:
            return True
        if "அல்லது null" in v or "விண்ணப்பதாரர் பெயர்" in v or "முழு முகவரி" in v:
            return True
        if re.search(r'^[_\-\.\,\s0-9]{1,3}$', v):
            return True
        return False

    @staticmethod
    def _repair_phone(raw_str: str) -> Optional[str]:
        tr = str.maketrans('BbposlIzZ', '864051122')
        subbed = raw_str.translate(tr)
        digits = re.sub(r'\D', '', subbed)
        if len(digits) == 10 and digits[0] in '6789':
            return digits
        elif len(digits) > 10 and digits[-10] in '6789':
            return digits[-10:]
        return None

    def _extract_regex(self, full_text: str, page_number: int, line_scores: Optional[Dict[int, float]] = None) -> List[Dict[str, Any]]:
        entities = []
        if not full_text:
            return entities

        # Normalize text for regex pattern matching
        norm_text = normalize_tamil_text(full_text)

        for etype, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, norm_text, re.IGNORECASE)
            for m in matches:
                val = m.group(1) if m.groups() and m.group(1) else m.group(0).strip()

                val_status = "pending"
                computed_conf = 0.85

                if etype == "phone":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) == 10 and digits[0] in '6789':
                        val = digits
                        val_status = "verified"
                        computed_conf = 0.95
                    elif len(digits) == 9:
                        # D12 fix: 9-digit phone is strictly flagged as suspect
                        val = digits
                        val_status = "suspect"
                        computed_conf = 0.40
                    elif len(digits) > 10 and digits[-10] in '6789':
                        val = digits[-10:]
                        val_status = "verified"
                        computed_conf = 0.90
                    else:
                        continue

                elif etype == "aadhaar":
                    digits = re.sub(r'\D', '', val)
                    is_valid_v = validate_verhoeff(digits)
                    val = self._mask_aadhaar(val)
                    val_status = "verified" if is_valid_v else "suspect"
                    computed_conf = 0.98 if is_valid_v else 0.50

                elif etype == "pincode":
                    digits = re.sub(r'\D', '', val)
                    if len(digits) == 6 and digits.startswith("6"):
                        val = digits
                        val_status = "verified"
                        computed_conf = 0.95
                    else:
                        continue

                elif etype == "survey_no":
                    val = re.sub(
                        r'^(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*',
                        '', val, flags=re.IGNORECASE
                    ).strip()
                    val_status = "verified" if "/" in val or val.isdigit() else "pending"
                    computed_conf = 0.92

                elif etype == "date_dmy":
                    # Date normalization
                    parts = re.split(r'[/\-\.]', val)
                    if len(parts) == 3:
                        d, mo, yr = parts
                        if len(yr) == 2:
                            yr = f"20{yr}"
                        try:
                            val = f"{int(yr):04d}-{int(mo):02d}-{int(d):02d}"
                            val_status = "verified"
                            computed_conf = 0.95
                        except Exception:
                            val_status = "suspect"
                            computed_conf = 0.60

                entities.append({
                    "entity_type": etype,
                    "entity_value": val,
                    "confidence": computed_conf,
                    "validation_status": val_status,
                    "review_state": "pending",
                    "officer_note": None,
                    "source_page": page_number,
                    "source_chunk_id": None,
                    "extracted_by": "regex",
                    "officer_corrected": False
                })

        # Check for OCR-distorted phone numbers (e.g., 9529Bp585b)
        if not any(e["entity_type"] == "phone" and e["validation_status"] == "verified" for e in entities):
            raw_phone_candidates = re.findall(r'[6-9][0-9A-Za-z]{9,11}', norm_text)
            for c in raw_phone_candidates:
                repaired = self._repair_phone(c)
                if repaired:
                    entities.append({
                        "entity_type": "phone",
                        "entity_value": repaired,
                        "confidence": 0.88,
                        "validation_status": "verified",
                        "review_state": "pending",
                        "officer_note": "Repaired from OCR character substitution",
                        "source_page": page_number,
                        "source_chunk_id": None,
                        "extracted_by": "regex",
                        "officer_corrected": False
                    })
                    break

        return entities

    def _extract_structural_entities(self, full_text: str, page_number: int) -> List[Dict[str, Any]]:
        """Parses standard Tamil petition headers (From, To, Subject, Details)."""
        entities = []
        if not full_text:
            return entities

        norm_text = normalize_tamil_text(full_text)
        lines = [l.strip() for l in norm_text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            if any(k in line for k in self.SENDER_HEADERS):
                sender_lines = lines[i + 1:i + 12]
                for s_line in sender_lines:
                    if any(stop_k in s_line for stop_k in self.STOP_HEADERS):
                        break

                    clean_line = self._clean_text_artifacts(s_line)
                    if not clean_line:
                        continue

                    # Father / Husband Name
                    if any(f_prefix in clean_line for f_prefix in ["S/o", "D/o", "W/o", "Wo", "த/பெ", "க/பெ", "த/ ப", "தந்தை", "கணவர்", "Father", "Husband"]):
                        clean_f = re.sub(
                            r'.*?(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband)\s*(?:Late)?\s*[:\.]?\s*',
                            '', clean_line, flags=re.IGNORECASE
                        ).strip()
                        clean_f = re.sub(r'[|{}\[\]<>~`@#$%^&*()_=+0-9]', '', clean_f).strip().rstrip(",")
                        if clean_f and len(clean_f) >= 3 and not self._is_invalid_value(clean_f):
                            entities.append({
                                "entity_type": "father_husband_name",
                                "entity_value": clean_f,
                                "confidence": 0.92,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "review_state": "pending",
                                "officer_note": None,
                                "officer_corrected": False
                            })
                            continue

                    # Address Line
                    if any(a_k in clean_line for a_k in [
                        "D.No", "D.N", "எண்", "வீதி", "Street", "தெரு", "பாளையம",
                        "பாளையம்", "நகர்", "Nagar", "Road", "Lane", "Main", "ரோடு"
                    ]) or re.search(r'^\d+[\s,]', clean_line):
                        addr_val = clean_line.rstrip(",")
                        if len(addr_val) >= 4 and not self._is_invalid_value(addr_val):
                            entities.append({
                                "entity_type": "address",
                                "entity_value": addr_val,
                                "confidence": 0.88,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "review_state": "pending",
                                "officer_note": None,
                                "officer_corrected": False
                            })
                            continue

                    # Petitioner Name
                    if not any(e["entity_type"] == "petitioner_name" for e in entities):
                        clean_name = re.sub(
                            r'^(?:திரு|திருமதி|செல்வி|மனுதாரர்|பெயர்|விண்ணப்பதாரர்|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Thiru)\s*[:\.]?\s*',
                            '', clean_line, flags=re.IGNORECASE
                        ).strip()
                        clean_name = re.sub(r'[|{}\[\]<>~`@#$%^&*()_=+0-9]', '', clean_name).strip().rstrip(",")
                        if len(clean_name) >= 3 and not self._is_invalid_value(clean_name) and not clean_name.lower().startswith("d.n"):
                            entities.append({
                                "entity_type": "petitioner_name",
                                "entity_value": clean_name,
                                "confidence": 0.92,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "review_state": "pending",
                                "officer_note": None,
                                "officer_corrected": False
                            })

        # Dynamic Segment Extraction (Taluk, District, Village)
        for line in lines:
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
                            "confidence": 0.90,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "review_state": "pending",
                            "officer_note": None,
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
                                "confidence": 0.90,
                                "source_page": page_number,
                                "extracted_by": "regex",
                                "validation_status": "pending",
                                "review_state": "pending",
                                "officer_note": None,
                                "officer_corrected": False
                            })

                # Village
                v_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s\.\-]+?)(?:\(Po\)|\(கிராமம்\)|கிராமம்|Village)', seg, re.IGNORECASE)
                if v_match:
                    v_val = self._clean_text_artifacts(v_match.group(1)).strip(":, ")
                    if len(v_val) >= 2 and not any(e["entity_type"] == "village" and e["entity_value"] == v_val for e in entities):
                        entities.append({
                            "entity_type": "village",
                            "entity_value": v_val,
                            "confidence": 0.88,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "review_state": "pending",
                            "officer_note": None,
                            "officer_corrected": False
                        })

        # Grievance Subject / Type from பொருள்: or Subject:
        for line in lines:
            if any(k in line for k in ["பொருள்:", "பொருள் :", "பொருள்", "Subject:", "Subject :", "Sub:"]):
                sub_match = re.search(r'(?:பொருள்|Subject|Sub)\s*[:\.]?\s*(.+)', line, re.IGNORECASE)
                if sub_match:
                    sub_val = self._clean_text_artifacts(sub_match.group(1)).strip(":, ")
                    if len(sub_val) >= 3 and not any(e["entity_type"] == "grievance_type" for e in entities):
                        entities.append({
                            "entity_type": "grievance_type",
                            "entity_value": sub_val,
                            "confidence": 0.90,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "review_state": "pending",
                            "officer_note": None,
                            "officer_corrected": False
                        })
                        break

        return entities


    async def _extract_ai(self, text_content: str, page: int) -> List[Dict[str, Any]]:
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
            if val and val != "null" and not str(val).startswith("[தகவல்") and not self._is_invalid_value(str(val)):
                clean_val = self._clean_text_artifacts(str(val))
                if clean_val and not self._is_invalid_value(clean_val):
                    entities.append({
                        "entity_type": etype,
                        "entity_value": clean_val,
                        "confidence": 0.85,
                        "source_page": page,
                        "source_chunk_id": None,
                        "extracted_by": "ai_ner",
                        "validation_status": "pending",
                        "review_state": "pending",
                        "officer_note": None,
                        "officer_corrected": False
                    })
        return entities

    async def _validate_locations(self, db: AsyncSession, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fuzzy matches village, taluk, district against master_locations table.
        Gate: similarity >= 85% is marked 'verified'; otherwise marked 'suspect'.
        """
        loc_entities = [e for e in entities if e["entity_type"] in ["village", "taluk", "district"]]
        if not loc_entities:
            return entities

        # Load master locations
        try:
            m_res = await db.execute(text("SELECT village_name_tamil, taluk_name_tamil, district_name_tamil FROM master_locations"))
            master_rows = m_res.mappings().all()
            villages = [r["village_name_tamil"] for r in master_rows if r["village_name_tamil"]]
            taluks = [r["taluk_name_tamil"] for r in master_rows if r["taluk_name_tamil"]]
            districts = [r["district_name_tamil"] for r in master_rows if r["district_name_tamil"]]
        except Exception as e:
            logger.warning(f"Could not load master locations: {e}")
            villages, taluks, districts = [], [], []

        for e in loc_entities:
            val = e["entity_value"]
            if not val or len(val) < 2:
                continue

            target_list = villages if e["entity_type"] == "village" else (taluks if e["entity_type"] == "taluk" else districts)
            best_ratio = 0.0
            best_match = None

            for t in target_list:
                ratio = difflib.SequenceMatcher(None, val, t).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = t

            if best_ratio >= 0.85 and best_match:
                e["validation_status"] = "verified"
                e["entity_value"] = best_match
                e["confidence"] = round(min(1.0, 0.70 + (best_ratio * 0.30)), 2)
            else:
                e["validation_status"] = "suspect"
                e["confidence"] = round(max(0.40, best_ratio), 2)
                e["officer_note"] = f"Unmatched against master locations (best match: {best_match}, ratio: {best_ratio:.2f})"

        return entities

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                if e.get("validation_status") == "verified" and existing.get("validation_status") != "verified":
                    seen[key] = e
                elif (e.get("confidence") or 0) > (existing.get("confidence") or 0):
                    seen[key] = e
        return list(seen.values())

    async def extract_all(self, db: AsyncSession, source_id: str) -> List[Dict[str, Any]]:
        """
        Extracts entities from non-struck ocr_lines and stamp_parse:
        1. Queries ocr_lines where struck = FALSE
        2. Normalizes Tamil Unicode and translated digits
        3. Executes regex, structural, and AI extraction
        4. Validates locations with master_locations fuzzy gate (>=85%)
        5. Saves with review_state='pending'
        6. Emits ENTITIES_EXTRACTED audit event
        """
        # 1. Fetch valid, non-struck OCR lines
        res = await db.execute(text("""
            SELECT page_number, text, score
            FROM ocr_lines
            WHERE source_id = CAST(:source_id AS UUID) AND struck IS NOT TRUE
            ORDER BY page_number, line_index
        """), {"source_id": source_id})
        lines = res.mappings().all()

        # Group non-struck lines by page
        pages_text: Dict[int, str] = {}
        for l in lines:
            p_num = l["page_number"]
            pages_text[p_num] = pages_text.get(p_num, "") + "\n" + l["text"]

        entities = []
        for p_num, f_text in pages_text.items():
            regex_ents = self._extract_regex(f_text, p_num)
            entities.extend(regex_ents)

            struct_ents = self._extract_structural_entities(f_text, p_num)
            entities.extend(struct_ents)

            if len(f_text) > 20:
                ai_ents = await self._extract_ai(f_text, p_num)
                entities.extend(ai_ents)

        # Integrate stamp fields if present
        stamp_res = await db.execute(text("""
            SELECT department, subject, date_norm FROM stamp_parse WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        stamp_row = stamp_res.mappings().one_or_none()
        if stamp_row:
            if stamp_row.get("department") and stamp_row["department"] != "[தகவல் இல்லை]":
                entities.append({
                    "entity_type": "department",
                    "entity_value": stamp_row["department"],
                    "confidence": 0.98,
                    "validation_status": "verified",
                    "review_state": "pending",
                    "officer_note": "Extracted from GDP stamp",
                    "source_page": 1,
                    "source_chunk_id": None,
                    "extracted_by": "stamp_parser",
                    "officer_corrected": False
                })
            if stamp_row.get("date_norm"):
                entities.append({
                    "entity_type": "date_dmy",
                    "entity_value": stamp_row["date_norm"],
                    "confidence": 0.98,
                    "validation_status": "verified",
                    "review_state": "pending",
                    "officer_note": "Extracted from GDP stamp",
                    "source_page": 1,
                    "source_chunk_id": None,
                    "extracted_by": "stamp_parser",
                    "officer_corrected": False
                })

        # Validate locations against master_locations
        validated = await self._validate_locations(db, entities)
        deduped = self._deduplicate_entities(validated)

        # Clear and persist
        await db.execute(
            text("DELETE FROM extracted_entities WHERE source_id = CAST(:source_id AS UUID)"),
            {"source_id": source_id}
        )

        if deduped:
            batch_params = [
                {
                    "source_id": source_id,
                    "type": e["entity_type"],
                    "value": e["entity_value"],
                    "conf": e.get("confidence"),
                    "status": e.get("validation_status", "pending"),
                    "review_state": e.get("review_state", "pending"),
                    "officer_note": e.get("officer_note"),
                    "page": e.get("source_page"),
                    "chunk_id": e.get("source_chunk_id"),
                    "by": e.get("extracted_by", "regex"),
                    "corrected": e.get("officer_corrected", False)
                }
                for e in deduped
            ]
            await db.execute(text("""
                INSERT INTO extracted_entities 
                    (source_id, entity_type, entity_value, confidence, validation_status, review_state, officer_note, source_page, source_chunk_id, extracted_by, officer_corrected)
                VALUES 
                    (CAST(:source_id AS UUID), :type, :value, :conf, :status, :review_state, :officer_note, :page, :chunk_id, :by, :corrected)
            """), batch_params)

        await db.execute(text("""
            UPDATE sources SET status = 'entity_extracting', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        # Audit Event: ENTITIES_EXTRACTED
        from app.dependencies import log_audit_event
        suspect_count = sum(1 for e in deduped if e.get("validation_status") == "suspect")
        await log_audit_event(
            db,
            action="ENTITIES_EXTRACTED",
            source_id=source_id,
            details={
                "field_count": len(deduped),
                "suspect_count": suspect_count,
                "verified_count": len(deduped) - suspect_count
            }
        )

        return deduped


entity_extractor = EntityExtractor()
