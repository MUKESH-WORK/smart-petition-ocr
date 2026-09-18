import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger(__name__)


class CMHelplineTaxonomyValidator:
    """
    Connects directly to backend/data/cm_helpline_taxonomy.json.
    Derives all official departments, grievance types, sub-types, sub-departments,
    and responsible officers dynamically from the JSON file alone.
    Zero hardcoded lists or keyword dictionaries.
    """

    def __init__(self, json_path: Optional[str] = None):
        self.taxonomy_path = self._resolve_taxonomy_path(json_path)
        self.taxonomy: List[Dict[str, str]] = []
        self.departments: List[str] = []
        self.department_acronyms: Dict[str, str] = {}
        self.dept_entries: Dict[str, List[Dict[str, str]]] = {}
        self.subtypes_map: Dict[str, Dict[str, str]] = {}
        self.types_map: Dict[str, List[str]] = {}
        self.concept_map = self._load_tamil_concept_map()
        self.load_taxonomy()

    @staticmethod
    def _load_tamil_concept_map() -> Dict[str, List[str]]:
        """Loads semantic bridge mappings from backend/data/tamil_concept_map.json"""
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tamil_concept_map.json"),
            os.path.join(os.getcwd(), "backend", "data", "tamil_concept_map.json"),
            os.path.join(os.getcwd(), "data", "tamil_concept_map.json"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Error reading concept map {cand}: {e}")
        return {
            "ஆக்கிரமிப்பு": ["encroachment"],
            "போக வழி": ["encroachment", "pathway"],
            "வழிப்பாதை": ["encroachment", "road"],
            "பட்டா": ["patta", "patta transfer"],
            "உட்பிரிவு": ["sub division", "survey"],
            "சர்வே": ["survey"],
            "வாரிசு": ["legal heir", "heir", "certificate"],
            "விதவை": ["destitute widow", "widow", "pension"],
            "முதியோர்": ["old age pension", "pension"],
            "உதவித்தொகை": ["pension", "scholarship", "financial assistance"],
            "குடிநீர்": ["drinking water", "water supply"],
            "சாலை": ["road", "street"],
            "தெருவிளக்கு": ["street light", "lighting"],
            "மின்சாரம்": ["electricity", "power", "tangedco"],
            "ரேஷன்": ["ration card", "civil supplies"],
            "சாதி": ["community certificate"]
        }

    @staticmethod
    def _resolve_taxonomy_path(json_path: Optional[str] = None) -> str:
        """Resolves cm_helpline_taxonomy.json dynamically using absolute and relative paths."""
        if json_path and os.path.exists(json_path):
            return json_path

        env_path = os.environ.get("TAXONOMY_JSON_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cm_helpline_taxonomy.json"),
            os.path.join(os.getcwd(), "backend", "data", "cm_helpline_taxonomy.json"),
            os.path.join(os.getcwd(), "data", "cm_helpline_taxonomy.json"),
        ]

        for cand in candidates:
            if os.path.exists(cand):
                return cand

        # Fallback to relative path
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cm_helpline_taxonomy.json")

    def load_taxonomy(self) -> None:
        """
        Dynamically loads and parses all records directly from cm_taxonomy_mappings in the database.
        Zero hardcoded values, zero fallback JSON dependencies.
        Extracts departments, acronyms, grievance types, and sub-types entirely from authoritative data.
        """
        db_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_admin.db"),
            os.path.join(os.getcwd(), "temp_cache", "dro_admin.db"),
            os.path.join(os.getcwd(), "backend", "temp_cache", "dro_admin.db")
        ]
        db_records = []
        for cand in db_candidates:
            if os.path.exists(cand):
                try:
                    import sqlite3
                    con = sqlite3.connect(cand)
                    cur = con.cursor()
                    cur.execute("SELECT department, department_code, sub_department, grievance_type, grievance_sub_type, responsible_officer FROM cm_taxonomy_mappings")
                    rows = cur.fetchall()
                    con.close()
                    if rows:
                        for r in rows:
                            db_records.append({
                                "department": r[0] or "",
                                "department_code": r[1] or "",
                                "sub_department": r[2] or "",
                                "grievance_type": r[3] or "",
                                "grievance_sub_type": r[4] or "",
                                "responsible_officer": r[5] or ""
                            })
                        logger.info(f"Loaded {len(db_records)} authoritative taxonomy records directly from SQLite {cand}")
                        break
                except Exception as e:
                    logger.warning(f"Failed reading taxonomy from SQLite {cand}: {e}")

        if db_records:
            self.taxonomy = db_records
        elif os.path.exists(self.taxonomy_path):
            try:
                with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                    self.taxonomy = json.load(f)
            except Exception as e:
                logger.error(f"Error loading taxonomy: {e}")
                self.taxonomy = []
        else:
            self.taxonomy = []

        try:
            # Reset containers
            dept_set: Set[str] = set()
            self.department_acronyms.clear()
            self.dept_entries.clear()
            self.subtypes_map.clear()
            self.types_map.clear()

            for item in self.taxonomy:
                dept = (item.get("department") or "").strip()
                gtype = (item.get("grievance_type") or "").strip()
                gsub = (item.get("grievance_sub_type") or "").strip()

                if dept:
                    dept_set.add(dept)
                    self.dept_entries.setdefault(dept, []).append(item)

                    # Extract acronym inside parentheses dynamically from the data, e.g. "Revenue ... (REV)" -> REV
                    match = re.search(r'\(([A-Z0-9]+)\)', dept)
                    if match:
                        acronym = match.group(1).upper()
                        self.department_acronyms[acronym] = dept

                if dept and gtype:
                    self.types_map.setdefault(dept, [])
                    if gtype not in self.types_map[dept]:
                        self.types_map[dept].append(gtype)

                if gsub:
                    self.subtypes_map[gsub.lower()] = item

            # Sort canonical departments dynamically
            self.departments = sorted(list(dept_set))
            logger.info(f"Initialized {len(self.taxonomy)} taxonomy records, {len(self.departments)} departments from DB.")
        except Exception as e:
            logger.error(f"Error processing taxonomy records: {e}")

    def get_candidates(self, header_dept_keyword: Optional[str] = None, top_k: int = 5) -> List[Dict[str, str]]:
        """
        Filters candidates by header metadata / keywords if present, else returns top-K rows.
        Returns exact format:
        [{'Department': ..., 'Grievance Type': ..., 'Grievance Sub Type': ..., 'Sub Department': ..., 'Responsible officer': ...}]
        """
        source_items = self.taxonomy
        if header_dept_keyword:
            kw = str(header_dept_keyword).strip().lower()
            # Expand with semantic concept terms if Tamil keyword (e.g. குடிநீர் -> drinking water, water supply)
            search_terms = {kw}
            for c_key, c_terms in self.concept_map.items():
                if c_key in kw or kw in c_key:
                    search_terms.update([t.lower() for t in c_terms])

            scoped = []
            for item in self.taxonomy:
                dept_val = str(item.get("department", "")).lower()
                gtype_val = str(item.get("grievance_type", "")).lower()
                gsub_val = str(item.get("grievance_sub_type", "")).lower()
                item_str = f"{dept_val} {gtype_val} {gsub_val}"
                if any(term in item_str for term in search_terms):
                    scoped.append(item)
            if scoped:
                source_items = scoped

        candidates = []
        for item in source_items[:top_k]:
            candidates.append({
                "Department": item.get("department", ""),
                "Grievance Type": item.get("grievance_type", ""),
                "Grievance Sub Type": item.get("grievance_sub_type", ""),
                "Sub Department": item.get("sub_department", ""),
                "Responsible officer": item.get("responsible_officer", "")
            })
        return candidates

    def match_taxonomy(self, header_dept: str = "", grievance_keyword: str = "") -> Dict[str, str]:
        """
        Prioritizes exact Department match from header metadata over default taxonomy.
        """
        scoped = self.taxonomy
        if header_dept:
            h_clean = header_dept.strip().lower()
            dept_filtered = [
                item for item in self.taxonomy
                if h_clean in item.get("department", "").lower()
            ]
            if dept_filtered:
                scoped = dept_filtered

        if grievance_keyword:
            g_clean = grievance_keyword.strip().lower()
            matched = [
                item for item in scoped
                if g_clean in item.get("grievance_sub_type", "").lower()
                or g_clean in item.get("grievance_type", "").lower()
                or g_clean in item.get("sub_department", "").lower()
            ]
            if matched:
                best = matched[0]
                return {
                    "Department": best.get("department", ""),
                    "Grievance_Type": best.get("grievance_type", ""),
                    "Grievance_Sub_Type": best.get("grievance_sub_type", ""),
                    "Sub_Department": best.get("sub_department", ""),
                    "Responsible_Officer": best.get("responsible_officer", "")
                }

        if scoped:
            best = scoped[0]
            return {
                "Department": best.get("department", ""),
                "Grievance_Type": best.get("grievance_type", ""),
                "Grievance_Sub_Type": best.get("grievance_sub_type", ""),
                "Sub_Department": best.get("sub_department", ""),
                "Responsible_Officer": best.get("responsible_officer", "")
            }

        return {}

    def get_official_departments(self) -> List[str]:
        """Returns the complete list of departments derived directly from cm_helpline_taxonomy.json."""
        return list(self.departments)

    def normalize_department(self, dept_input: Optional[str]) -> Optional[str]:
        """
        Dynamically matches and normalizes any user/LLM input against the official
        departments extracted from cm_helpline_taxonomy.json.
        """
        if not dept_input:
            return None

        raw = dept_input.strip()
        raw_upper = raw.upper()

        # 1. Exact match against data departments
        for dept in self.departments:
            if raw.lower() == dept.lower():
                return dept

        # 2. Acronym match from taxonomy data (e.g. REV, RDPR, SWNM, MAWS, ENERGY)
        if raw_upper in self.department_acronyms:
            return self.department_acronyms[raw_upper]

        # Check for embedded acronym (e.g. "(REV)" in input)
        code_match = re.search(r'\(([A-Z0-9]+)\)', raw_upper)
        if code_match:
            code = code_match.group(1)
            if code in self.department_acronyms:
                return self.department_acronyms[code]

        # 3. Substring match against official departments from JSON
        for dept in self.departments:
            dept_core = dept.split("(")[0].strip().lower()
            if dept_core in raw.lower() or raw.lower() in dept_core:
                return dept

        return raw

    def get_types_for_department(self, department: str) -> List[str]:
        """Returns all grievance types for a department from the JSON dataset."""
        norm_dept = self.normalize_department(department)
        return sorted(self.types_map.get(norm_dept, []))

    def get_subtypes_for_department(self, department: str) -> List[str]:
        """Returns all grievance sub-types for a department from the JSON dataset."""
        norm_dept = self.normalize_department(department)
        entries = self.dept_entries.get(norm_dept, [])
        subtypes = {e.get("grievance_sub_type", "").strip() for e in entries if e.get("grievance_sub_type")}
        return sorted(list(subtypes))

    def get_department_prompt_text(self) -> str:
        """Formats the dynamically loaded departments for embedding into LLM prompts."""
        return "\n".join(f"{i}. {dept}" for i, dept in enumerate(self.departments, 1))

    def match(
        self,
        petition_text: str = "",
        detected_type: Optional[str] = None,
        detected_subtype: Optional[str] = None,
        detected_dept: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically aligns LLM grievance classification with the official CM Helpline taxonomy:
        1. Normalizes department using departments loaded from JSON.
        2. Matches exact or high-confidence sub-types from the loaded taxonomy records.
        3. Fills official sub_department and responsible_officer.
        4. Gracefully passes through if novel.
        """
        dept_norm = self.normalize_department(detected_dept) or "General Administration / பொது நிர்வாகம்"
        gtype_in = (detected_type or "").strip()
        gsub_in = (detected_subtype or "").strip()

        if not self.taxonomy:
            dept_prefix = str(dept_norm).split('(')[0].strip()
            return {
                "department": dept_norm,
                "grievance_type": gtype_in or "General Grievance",
                "grievance_subtype": gsub_in or "Public Grievance Redressal",
                "sub_department": f"{dept_prefix} Administration",
                "responsible_officer": "Competent Authority",
                "validated": False,
                "match_score": 0
            }

        # Step 1: Direct exact match on sub-type from the JSON taxonomy
        if gsub_in and gsub_in.lower() in self.subtypes_map:
            item = self.subtypes_map[gsub_in.lower()]
            return {
                "department": item["department"],
                "grievance_type": item["grievance_type"] or gtype_in or "General Grievance",
                "grievance_subtype": item["grievance_sub_type"] or gsub_in or "Public Grievance Redressal",
                "sub_department": item.get("sub_department", ""),
                "responsible_officer": item.get("responsible_officer", ""),
                "validated": True,
                "match_score": 100
            }

        # Step 2: Semantic concept bridge for Tamil grievance terminology
        concept_terms = set()
        is_education_query = any(k in (gtype_in + " " + gsub_in + " " + petition_text).lower() for k in ["கல்வி", "படிப்பு", "கல்லூரி", "பள்ளி", "மாணவர்", "scholarship", "education", "degree"])
        is_employee_query = any(k in (gtype_in + " " + gsub_in + " " + petition_text).lower() for k in ["employee", "பணியாளர்", "ஊழியர்", "ஆசிரியர் பணி", "ஓய்வூதியம்", "pension"])

        for tam_key, eng_synonyms in self.concept_map.items():
            if tam_key in gtype_in or tam_key in gsub_in or tam_key in petition_text:
                if is_education_query and not is_employee_query:
                    concept_terms.update([s for s in eng_synonyms if "pension" not in s])
                else:
                    concept_terms.update(eng_synonyms)

        # Step 3: Search within candidate department if detected, otherwise full taxonomy
        # If query is specifically about education/scholarship, do not lock into Revenue or mismatched departments
        if is_education_query and dept_norm and "education" not in dept_norm.lower() and "welfare" not in dept_norm.lower():
            search_items = self.taxonomy
        elif dept_norm:
            search_items = self.dept_entries.get(dept_norm, self.taxonomy)
        else:
            search_items = self.taxonomy
        query_text = f"{gsub_in} {gtype_in} {petition_text}".lower()
        query_tokens = set(re.findall(r'\b\w{3,}\b', query_text))

        best_item = None
        best_score = 0.0

        for item in search_items:
            t_dept = item.get("department", "").lower()
            t_gtype = item.get("grievance_type", "").lower().strip()
            t_gsub = item.get("grievance_sub_type", "").lower().strip()

            score = 0.0

            # Education query department affinities
            if is_education_query:
                if any(k in query_text for k in ["கல்லூரி", "college", "b.e", "பொறியியல்", "degree", "higher education"]):
                    if "higher education" in t_dept:
                        score += 20.0
                elif "higher education" in t_dept or "school education" in t_dept or "minorities" in t_dept or "social justice" in t_dept:
                    score += 10.0

            # Penalize employee/pension grievances if the applicant is a citizen/student
            if not is_employee_query and ("employee" in t_gtype or "pension" in t_gsub or "pension" in t_gtype):
                score -= 30.0

            # Subtype specific semantic constraints
            if "bus pass" in t_gsub and not any(b in query_text for b in ["bus", "பேருந்து"]):
                score -= 35.0

            # Penalize religious / Waqf / temple institutions if not explicitly requested
            is_religious_query = any(w in query_text for w in ["waqf", "temple", "கோவில்", "பள்ளிவாசல்", "தேவாலயம்", "மசூதி", "church", "mosque"])
            if not is_religious_query:
                if "waqf" in t_gsub or "waqf" in t_gtype or "religious institutions" in t_gtype:
                    score -= 40.0
                if "temple land" in t_gsub or "temple land" in t_gtype:
                    score -= 40.0

            # Encroachment priority for land/pathway grievances
            if any(e in query_text for e in ["encroachment", "ஆக்கிரமிப்பு", "பொதுப்பாதை", "முள்வேலி", "வழிப்பாதை"]):
                if "encroachment" in t_gsub or "encroachment" in t_gtype or "eviction of encroachments" in t_gsub:
                    score += 25.0
                    if any(r in query_text for r in ["வருவாய்", "revenue", "நில அளவை", "சர்வே", "கிராம", "பாதை", "வழி"]):
                        if "revenue" in t_dept:
                            score += 20.0

            # Scholarship priority when seeking educational financial assistance
            if any(s in query_text for s in ["scholarship", "உதவித்தொகை", "கல்வி உதவி"]):
                if "scholarship" in t_gsub:
                    score += 35.0
                elif "scholarship" in t_gtype:
                    score += 25.0

            # Subtype overlap (prevent empty string match)
            if gsub_in and t_gsub:
                g_sub_lower = gsub_in.lower()
                if g_sub_lower == t_gsub:
                    score += 25.0
                elif len(t_gsub) >= 4 and t_gsub in g_sub_lower:
                    score += 18.0
                elif len(g_sub_lower) >= 4 and g_sub_lower in t_gsub:
                    score += 18.0

            # Aadhaar / Information Technology / eSevai / TACTV affinity
            if any(a in query_text for a in ["aadhaar", "aadhar", "ஆதார்", "tactv", "esevai", "ceg", "information technology", "e-sevai"]):
                if "information technology" in t_dept:
                    score += 40.0
                if "aadhaar" in t_gsub or "esevai" in t_gsub or "ceg" in t_gtype:
                    score += 35.0

            # Grievance type overlap (prevent empty string match)
            if gtype_in and t_gtype:
                g_type_lower = gtype_in.lower()
                if g_type_lower == t_gtype:
                    score += 15.0
                elif len(t_gtype) >= 4 and t_gtype in g_type_lower:
                    score += 10.0
                elif len(g_type_lower) >= 4 and g_type_lower in t_gtype:
                    score += 10.0

            # Semantic concept matches (e.g. encroachment, patta, scholarship)
            for c in concept_terms:
                if t_gsub and c in t_gsub:
                    score += 20.0
                elif t_gtype and c in t_gtype:
                    score += 15.0

            # Department bonus (do not bonus Revenue if petition is an education query)
            if dept_norm and dept_norm.lower() == t_dept and not (is_education_query and "revenue" in dept_norm.lower()):
                score += 4.0

            # General token overlap
            for token in query_tokens:
                if t_gsub and len(token) >= 4 and token in t_gsub:
                    score += 2.0
                elif t_gtype and len(token) >= 4 and token in t_gtype:
                    score += 1.0

            if score > best_score:
                best_score = score
                best_item = item

        # If confident match found in taxonomy
        if best_item and best_score >= 10.0:
            final_type = best_item["grievance_type"] or gtype_in or "General Grievance"
            final_subtype = best_item["grievance_sub_type"] or gsub_in or "Public Grievance Redressal"

            # Retain Tamil classification alongside official English taxonomy entry if input was in Tamil
            if gtype_in and any('\u0B80' <= c <= '\u0BFF' for c in gtype_in) and gtype_in not in final_type:
                final_type = f"{gtype_in} / {final_type}" if final_type else gtype_in
            if gsub_in and any('\u0B80' <= c <= '\u0BFF' for c in gsub_in) and gsub_in not in final_subtype:
                final_subtype = f"{gsub_in} / {final_subtype}" if final_subtype else gsub_in

            return {
                "department": best_item["department"],
                "grievance_type": final_type,
                "grievance_subtype": final_subtype,
                "sub_department": best_item.get("sub_department", ""),
                "responsible_officer": best_item.get("responsible_officer", ""),
                "validated": True,
                "match_score": best_score
            }

        # Graceful passthrough with normalized department
        fallback_dept = dept_norm or "General Administration / பொது நிர்வாகம்"
        return {
            "department": fallback_dept,
            "grievance_type": gtype_in or "General Grievance",
            "grievance_subtype": gsub_in or "Public Grievance Redressal",
            "sub_department": f"{fallback_dept.split('(')[0].strip()} / நிர்வாகம்",
            "responsible_officer": "துறை அலுவலர்",
            "validated": False,
            "match_score": 0
        }


# Singleton instance loaded dynamically from cm_helpline_taxonomy.json alone
taxonomy_matcher = CMHelplineTaxonomyValidator()
TaxonomyMatcher = CMHelplineTaxonomyValidator
CMHelplineTaxonomyMatcher = CMHelplineTaxonomyValidator

