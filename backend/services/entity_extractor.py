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
        "survey_no": r'(?:SF|புல\s*எண்|சர்வே\s*எண்|SF\s*No\.?|Survey\s*No\.?)\s*:?[\s\-]*\b\d{1,4}(?:/\d{1,3}[A-Za-z0-9]*)?\b',
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
        "விண்ணப்பதாரர்", "பொதுமக்கள்", "-", "--", "none", "unknown",
        "மாவட்ட ஆட்சியர்", "மாவட்ட ஆட்சியர் அவர்கள்", "மாவட்ட ஆட்சித்தலைவர்", "ஆட்சியர்", "ஆட்சியர் அவர்கள்",
        "மாவட்ட வருவாய் அலுவலர்", "வருவாய் கோட்டாட்சியர்", "வட்டாட்சியர்", "வட்டாட்சியர் அவர்கள்",
        "துணை ஆட்சியர்", "முதலமைச்சர்", "அரசு செயலாளர்", "காவல் கண்காணிப்பாளர்", "ஆணையர்",
        "அலுவலர்", "அலுவலர் அவர்கள்", "பொறுப்பு அலுவலர்", "பெறுநர்", "பெறுநர்:", "பெறுதல்",
        "அனுப்புநர்", "அனுப்புநர்:", "அனுப்புதல்", "அனுப்புதல்:", "நாள்", "தேதி", "Date", "DATE",
        "ந.க", "கடித எண்", "மனு நாள்", "மனு எண்", "விவரம்", "பொருள்", "Subject", "ஐயா",
        "வணக்கம்", "நன்றி", "இப்படிக்கு", "இவண்", "தங்கள் உண்மையுள்ள", "வசித்து வருகிறோம்", "வசித்து வருகிறேன்"
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
        if any(auth in v for auth in [
            "மாவட்ட ஆட்சியர்", "ஆட்சியர் அவர்கள்", "ஆட்சியர்", "வட்டாட்சியர்", "முதலமைச்சர்",
            "அரசு செயலாளர்", "காவல் கண்காணிப்பாளர்", "துணை ஆட்சியர்", "கோட்டாட்சியர்",
            "பொறுப்பு அலுவலர்", "பெறுநர்", "பெறநர்", "பெறுதல்", "அனுப்புநர்", "அனுப்புதல்", "மனு நீதி நாள்",
            "வருவாய் கோட்டாட்சியர்", "வருவாய் அலுவலர்", "DRO", "தாசில்தார்",
            "வசித்து வருகிறோ", "வசித்து வருகிறே"
        ]):
            return True
        if v in ["-", "--", "null", "none", "n/a", "", "நாள்", "தேதி"]:
            return True
        # Reject date strings (e.g. 24.08.2026 or 12/09/2026)
        if re.match(r'^\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}$', v):
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

        # 0. Primary Sender Block Extraction (அனுப்புநர் / அனுப்புதல் / மனுதாரர் / விண்ணப்பதாரர்)
        for idx_line, l in enumerate(lines):
            clean_hdr = self._clean_text_artifacts(l)
            if any(clean_hdr.startswith(h) for h in ["அனுப்புநர்", "அனுப்புதல்", "மனுதாரர்", "விண்ணப்பதாரர்", "From", "FROM"]):
                sub_name = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|மனுதாரர்|விண்ணப்பதாரர்|From|FROM)\s*[:\.\-]?\s*', '', clean_hdr).strip()
                sub_name = re.sub(r'\(\d+\)|\d+', '', sub_name).strip(',.-: ')
                cand_lines = [sub_name] if sub_name else []
                for n_idx in range(idx_line + 1, min(idx_line + 6, len(lines))):
                    next_raw = self._clean_text_artifacts(lines[n_idx])
                    if any(next_raw.startswith(stop_h) for stop_h in ["பெறுநர்", "பெறுதல்", "பொருள்", "வணக்கம்", "மதிப்பிற்குரிய", "To", "TO", "Subject"]):
                        break
                    if next_raw:
                        cand_lines.append(next_raw)

                for cand in cand_lines:
                    clean_c = re.sub(r'\(\d+\)|\d+', '', cand).strip(',.-: ')
                    so_m = re.search(r'(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband)\s*[:\.]?\s*([^\n,;]+)', clean_c, re.IGNORECASE)
                    if so_m:
                        rel_val = re.sub(r'^(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband|காலஞ்சென்ற|Late)\s*[:\.\-]?\s*', '', so_m.group(1), flags=re.IGNORECASE)
                        rel_val = re.sub(r'[0-9]', '', rel_val).strip(' ,.-:')
                        if rel_val and not any(w in rel_val for w in ["தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது", "தெரு", "நகர்", "ரோடு", "வட்டம்", "மாவட்டம்", "கிராமம்", "காலனி", "ஊராட்சி", "Street", "Road", "Nagar"]):
                            if 2 <= len(rel_val) <= 40 and not self._is_invalid_value(rel_val) and not any(e["entity_type"] == "father_husband_name" for e in entities):
                                entities.append({
                                    "entity_type": "father_husband_name",
                                    "entity_value": rel_val,
                                    "confidence": 0.98,
                                    "source_page": page_number,
                                    "extracted_by": "sender_block",
                                    "validation_status": "pending",
                                    "officer_corrected": False
                                })
                        p_prefix = clean_c[:so_m.start()].strip(' ,.-:')
                        if p_prefix and 2 <= len(p_prefix) <= 40 and not self._is_invalid_value(p_prefix) and not any(e["entity_type"] == "petitioner_name" for e in entities):
                            entities.append({
                                "entity_type": "petitioner_name",
                                "entity_value": p_prefix,
                                "confidence": 0.98,
                                "source_page": page_number,
                                "extracted_by": "sender_block",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })
                    elif not any(skip in clean_c for skip in ["தெரு", "வட்டம்", "மாவட்டம்", "கிராமம்", "நகர்", "காலனி", "ரோடு", "TK", "Dt", "செல்", "Phone", "Pin", "அலைபேசி"]):
                        if 2 <= len(clean_c) <= 40 and not self._is_invalid_value(clean_c) and not any(e["entity_type"] == "petitioner_name" for e in entities):
                            entities.append({
                                "entity_type": "petitioner_name",
                                "entity_value": clean_c,
                                "confidence": 0.98,
                                "source_page": page_number,
                                "extracted_by": "sender_block",
                                "validation_status": "pending",
                                "officer_corrected": False
                            })
                break

        for line_idx, line in enumerate(lines):
            clean_l = self._clean_text_artifacts(line)
            if not clean_l or self._is_invalid_value(clean_l):
                continue

            # 1. Combined Petitioner & Relationship Extraction (e.g. "மு. கார்த்திகேயன், த/பெ முருகேசன்")
            # Skip narrative sentences that describe family circumstances (e.g. "எனது தந்தை தினக்கூலி தொழிலாளி")
            is_narrative = any(narr in clean_l for narr in ["எனது", "எங்கள்", "குடும்ப", "சேர்ந்தவன்", "சேர்ந்தவர்", "தொழிலாளி", "விவசாயி", "கூலி", "வசித்து", "வருகிறேன்", "உள்ளது", "இறந்து", "படிப்பு", "படித்து"])
            rel_match = None if is_narrative else re.search(r'([^\n,:]+?)\s*[,;\s]\s*(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband|மகன்|மனைவி)\s*[:\.]?\s*([^\n,;]+)', clean_l, re.IGNORECASE)
            if rel_match:
                cand_p = rel_match.group(1).strip()
                cand_rel = rel_match.group(2).strip()
                cand_p = re.sub(r'^(?:அனுப்புநர்|அனுப்புதல்|விண்ணப்பதாரர்|மனுதாரர்)\s*[:\.\-]?\s*', '', cand_p).strip()
                cand_p = re.sub(r'[0-9]', '', cand_p).strip()
                cand_rel = re.sub(r'[0-9]', '', cand_rel).strip()
                # Ensure cand_rel is not an occupation, verb, or address
                if cand_rel and not any(w in cand_rel for w in ["தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது", "தெரு", "நகர்", "ரோடு", "வட்டம்", "மாவட்டம்", "கிராமம்", "காலனி", "ஊராட்சி", "Street", "Road", "Nagar"]):
                    if cand_p and 3 <= len(cand_p) <= 40 and not self._is_invalid_value(cand_p) and not any(e["entity_type"] == "petitioner_name" for e in entities):
                        entities.append({
                            "entity_type": "petitioner_name",
                            "entity_value": cand_p,
                            "confidence": 0.96,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })
                    if cand_rel and 3 <= len(cand_rel) <= 40 and not self._is_invalid_value(cand_rel) and not any(e["entity_type"] == "father_husband_name" for e in entities):
                        entities.append({
                            "entity_type": "father_husband_name",
                            "entity_value": cand_rel,
                            "confidence": 0.96,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

            # Standalone Relationship Extraction
            elif not is_narrative and any(f_prefix in clean_l for f_prefix in ["S/o", "D/o", "W/o", "Wo", "த/பெ", "க/பெ", r"த/\s*ப", "தந்தை", "கணவர்", "Father", "Husband"]):
                clean_f = re.sub(
                    r'.*?(?:S/o|D/o|W/o|Wo|த/பெ|க/பெ|த/\s*ப|தந்தை|கணவர்|Father|Husband)\s*(?:Late)?\s*[:\.]?\s*',
                    '', clean_l, flags=re.IGNORECASE
                ).strip()
                clean_f = re.sub(r'[0-9]', '', clean_f).strip().split(',')[0].strip()
                if clean_f and not any(w in clean_f for w in ["தொழிலாளி", "கூலி", "விவசாயி", "இறந்து", "இல்லை", "காலமானார்", "உள்ளது", "தெரு", "நகர்", "ரோடு", "வட்டம்", "மாவட்டம்", "கிராமம்", "காலனி", "ஊராட்சி", "Street", "Road", "Nagar"]):
                    if clean_f and 3 <= len(clean_f) <= 40 and not self._is_invalid_value(clean_f) and not any(e["entity_type"] == "father_husband_name" for e in entities):
                        entities.append({
                            "entity_type": "father_husband_name",
                            "entity_value": clean_f,
                            "confidence": 0.95,
                            "source_page": page_number,
                            "extracted_by": "regex",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })

            # 2. Petitioner Name extraction from title lines
            if not any(e["entity_type"] == "petitioner_name" for e in entities):
                title_match = re.search(r'(?:^|[\s,])(?:திரு|திருமதி|செல்வி|Mr\.?|Mrs\.?|Ms\.?|Smt\.?|Thiru)\.?\s+([A-Za-z\u0B80-\u0BFF\.\s]{3,35})', clean_l, re.IGNORECASE)
                if title_match:
                    clean_name = title_match.group(1).strip().split(',')[0].strip()
                    if 3 <= len(clean_name) <= 40 and not self._is_invalid_value(clean_name):
                        entities.append({
                            "entity_type": "petitioner_name",
                            "entity_value": clean_name,
                            "confidence": 0.95,
                            "source_page": page_number,
                            "extracted_by": "regex",
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

        # 5. Extract Door Number and Street Name from sender address block
        if not any(e["entity_type"] == "door_no" for e in entities):
            door_street_match = re.search(r'(?:^|\n)\s*(\d{1,4}/\d{1,4}[A-Za-z0-9\-]*)\s*,\s*([^\n,]+?(?:தெரு|street|road|nagar|நகர்|காலனி|colony|salai|சாலை))', full_text, re.IGNORECASE)
            if door_street_match:
                d_val = door_street_match.group(1).strip()
                s_val = self._clean_text_artifacts(door_street_match.group(2)).strip(":, ")
                entities.append({
                    "entity_type": "door_no",
                    "entity_value": d_val,
                    "confidence": 0.97,
                    "source_page": page_number,
                    "extracted_by": "structural",
                    "validation_status": "pending",
                    "officer_corrected": False
                })
                if s_val and not any(e["entity_type"] == "street_name" for e in entities):
                    entities.append({
                        "entity_type": "street_name",
                        "entity_value": s_val,
                        "confidence": 0.96,
                        "source_page": page_number,
                        "extracted_by": "structural",
                        "validation_status": "pending",
                        "officer_corrected": False
                    })

        # 6. Extract Village / Residential Locality (e.g. சின்னத்தம்பாளையம், காளிபாளையம்)
        if not any(e["entity_type"] == "village" for e in entities):
            for l in lines:
                v_match = re.search(r'([A-Za-z\u0B80-\u0BFF\s]+(?:பாளையம்|பட்டி|நகர்|புரம்|ஊர்|குப்பம்|கிராமம்|சேரி))', l)
                if v_match:
                    v_val = self._clean_text_artifacts(v_match.group(1)).strip(":, ")
                    if len(v_val) >= 3 and not self._is_invalid_value(v_val) and not any(skip in v_val for skip in ["வட்டம்", "மாவட்டம்"]):
                        entities.append({
                            "entity_type": "village",
                            "entity_value": v_val,
                            "confidence": 0.94,
                            "source_page": page_number,
                            "extracted_by": "structural",
                            "validation_status": "pending",
                            "officer_corrected": False
                        })
                        break

        # 7. Extract Petitioner Name from Sign-off block (e.g. இப்படிக்கு, ... (மு. கார்த்திக்))
        # 7. Extract Petitioner Name from Sign-off block (bracketed or unbracketed)
        if not any(e["entity_type"] == "petitioner_name" for e in entities):
            idx_sig = full_text.find("இப்படிக்கு")
            if idx_sig == -1:
                idx_sig = full_text.find("இவண்")
            closing_block = full_text[idx_sig:] if idx_sig != -1 else full_text[-500:]
            sig_matches = re.finditer(r'\(\s*([A-Za-z\u0B80-\u0BFF\.\s]{2,35})\s*\)', closing_block)
            found_sig = None
            for sm in sig_matches:
                cand_sig = self._clean_text_artifacts(sm.group(1)).strip("() ")
                if (
                    cand_sig and len(cand_sig) >= 3 and
                    not self._is_invalid_value(cand_sig) and
                    not any(skip in cand_sig for skip in ["TK", "Dt", "District", "Taluk", "Scholarship", "கணினி", "சான்றிதழ்", "நகல்", "பட்டியல்"])
                ):
                    found_sig = cand_sig
                    break

            if not found_sig and idx_sig != -1:
                sig_lines = [l.strip() for l in closing_block.split("\n") if l.strip()]
                for sl in sig_lines[1:5]:
                    cs = re.sub(r'\(\d+\)|\d+', '', sl).strip(',.-:() ')
                    if (
                        cs and 2 <= len(cs) <= 35 and not self._is_invalid_value(cs) and
                        not any(cs.startswith(w) for w in ["தங்கள்", "உண்மையுள்ள", "வணக்கம்", "நன்றி", "நாள்", "தேதி", "செல்", "போன்"]) and
                        not any(skip in cs for skip in ["TK", "Dt", "District", "Taluk", "வட்டம்", "மாவட்டம்"])
                    ):
                        found_sig = cs
                        break

            if found_sig:
                entities.append({
                    "entity_type": "petitioner_name",
                    "entity_value": found_sig,
                    "confidence": 0.98,
                    "source_page": page_number,
                    "extracted_by": "structural_signature",
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
        from app.config import settings
        prompt = f"""Extract all structured administrative entities from this Tamil petition text into a JSON object:
{{
  "petitioner_name": "Full legal name of the applicant/petitioner, or null",
  "father_husband_name": "Father or husband name if stated, or null",
  "gender": "Male or Female, or null",
  "phone": "10-digit mobile number, or null",
  "alternate_phone": "Alternate phone number, or null",
  "door_no": "Door/House number, or null",
  "street_name": "Street or road name, or null",
  "village": "Village, town, or residential area, or null",
  "taluk": "Taluk name, or null",
  "district": "District name, or null",
  "pincode": "6-digit postal pincode, or null",
  "survey_no": "Survey number or SF No, or null",
  "grievance_type": "Primary grievance category (e.g. கல்வி உதவித்தொகை / Scholarship, வாரிசு சான்றிதழ், பட்டா மாறுதல், ஓய்வூதியம், ஆக்கிரமிப்பு, குடிநீர், சாலை, மின்சாரம்)",
  "grievance_subtype": "Specific grievance sub-type or scheme name",
  "full_address": "Complete residential address, or null"
}}

IMPORTANT RULES:
1. Do NOT hallucinate. Only extract values present in the petition text.
2. CRITICAL: The addressee/officer under 'பெறுநர்' (e.g., 'மாவட்ட ஆட்சியர் அவர்கள்' / District Collector, 'வட்டாட்சியர்' / Tahsildar) is the government official receiving the petition, NEVER the petitioner! Do NOT extract recipient officers as petitioner_name.
3. The applicant/petitioner is under 'அனுப்புநர்' (Sender) or signed in parentheses at the end under 'இப்படிக்கு, (பெயர்)'.
4. Extract the applicant's home address from 'அனுப்புநர்', NOT the Collector's office under 'பெறுநர்'.
5. If applicant is 'Maragatham W/o Chinnasamy', petitioner_name is 'Maragatham' and father_husband_name is 'Chinnasamy'.
6. Never output pronouns like 'நான்', 'நாங்கள்', 'மனுதாரர்', or punctuation '-' as a name or category.
7. Respond ONLY with valid JSON.

Petition Text:
{text_content[:1400]}
"""
        try:
            import asyncio
            ai_timeout = float(getattr(settings, "LLM_FAST_TIMEOUT", 120.0))
            response = await asyncio.wait_for(
                self.llm.achat(prompt, temperature=0.1, max_tokens=280, json_mode=True),
                timeout=ai_timeout
            )
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
        struct_ents_count = 0

        for p in pages:
            f_text = p["full_text"] or ""
            if not f_text.strip():
                continue

            # Deterministic number/code extraction (< 1ms)
            regex_ents = self._extract_regex(f_text, p["page_number"])
            entities.extend(regex_ents)

            # High-speed structural extraction (< 5ms)
            struct_ents = self._extract_structural_entities(f_text, p["page_number"])
            entities.extend(struct_ents)
            struct_ents_count += len(struct_ents)

        # Single-pass Cognitive LLM extraction over concatenated pages (avoids CPU timeout from per-page LLM looping)
        has_petitioner_name = any(e["entity_type"] == "petitioner_name" for e in entities)
        if struct_ents_count < 2 or not has_petitioner_name:
            concat_pages = [
                f"--- பக்கம் {p['page_number']} ---\n{p['full_text'] or ''}"
                for p in pages if (p["full_text"] or "").strip()
            ]
            if concat_pages:
                concat_text = "\n\n".join(concat_pages)
                ai_ents = await self._extract_ai(concat_text, page=1)
                entities.extend(ai_ents)

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
                    "by": str(e.get("extracted_by", "regex"))[:20],
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
            UPDATE sources SET status = 'entity_extracted', updated_at = NOW() WHERE source_id = CAST(:source_id AS UUID)
        """), {"source_id": source_id})
        await db.commit()

        return deduped


entity_extractor = EntityExtractor()
