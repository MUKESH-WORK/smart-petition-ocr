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
        self.load_taxonomy()

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
            r"e:\test_rat\GDP_Assistant\backend\data\cm_helpline_taxonomy.json",
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
        Dynamically loads and parses all records from cm_helpline_taxonomy.json.
        Extracts departments, acronyms, grievance types, and sub-types entirely from the data.
        """
        if not os.path.exists(self.taxonomy_path):
            logger.warning(f"Taxonomy JSON not found at {self.taxonomy_path}.")
            return

        try:
            with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                self.taxonomy = json.load(f)

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
            logger.info(f"Loaded {len(self.taxonomy)} taxonomy records, {len(self.departments)} departments from {self.taxonomy_path}")
        except Exception as e:
            logger.error(f"Error loading taxonomy from {self.taxonomy_path}: {e}")

    def get_official_departments(self) -> List[str]:
        """Returns the complete list of departments derived directly from cm_helpline_taxonomy.json."""
        return list(self.departments)

    def normalize_department(self, dept_input: Optional[str]) -> str:
        """
        Dynamically matches and normalizes any user/LLM input against the official
        departments extracted from cm_helpline_taxonomy.json.
        """
        if not dept_input:
            # If no department provided, return first department or REV if available
            return self.department_acronyms.get("REV") or (self.departments[0] if self.departments else "Revenue and Disaster Management (REV)")

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
        dept_norm = self.normalize_department(detected_dept)
        gtype_in = (detected_type or "").strip()
        gsub_in = (detected_subtype or "").strip()

        if not self.taxonomy:
            return {
                "department": dept_norm,
                "grievance_type": gtype_in or "General Grievance",
                "grievance_subtype": gsub_in or "Public Grievance Redressal",
                "sub_department": f"{dept_norm.split('(')[0].strip()} Administration",
                "responsible_officer": "Competent Authority",
                "validated": False,
                "match_score": 0
            }

        # Step 1: Direct exact match on sub-type from the JSON taxonomy
        if gsub_in and gsub_in.lower() in self.subtypes_map:
            item = self.subtypes_map[gsub_in.lower()]
            return {
                "department": item["department"],
                "grievance_type": item["grievance_type"],
                "grievance_subtype": item["grievance_sub_type"],
                "sub_department": item.get("sub_department", ""),
                "responsible_officer": item.get("responsible_officer", ""),
                "validated": True,
                "match_score": 100
            }

        # Step 2: Search within candidate department if detected, otherwise full taxonomy
        search_items = self.dept_entries.get(dept_norm, self.taxonomy)
        query_text = f"{gsub_in} {gtype_in} {petition_text}".lower()
        query_tokens = set(re.findall(r'\b\w{3,}\b', query_text))

        best_item = None
        best_score = 0.0

        for item in search_items:
            t_dept = item.get("department", "").lower()
            t_gtype = item.get("grievance_type", "").lower()
            t_gsub = item.get("grievance_sub_type", "").lower()

            score = 0.0

            # Subtype overlap
            if gsub_in:
                g_sub_lower = gsub_in.lower()
                if g_sub_lower in t_gsub or t_gsub in g_sub_lower:
                    score += 15.0

            # Grievance type overlap
            if gtype_in:
                g_type_lower = gtype_in.lower()
                if g_type_lower in t_gtype or t_gtype in g_type_lower:
                    score += 8.0

            # Department bonus
            if dept_norm and dept_norm.lower() == t_dept:
                score += 5.0

            # Token overlap
            for token in query_tokens:
                if token in t_gsub:
                    score += 3.0
                elif token in t_gtype:
                    score += 1.5

            if score > best_score:
                best_score = score
                best_item = item

        # If confident match found in taxonomy
        if best_item and best_score >= 8.0:
            return {
                "department": best_item["department"],
                "grievance_type": best_item["grievance_type"],
                "grievance_subtype": best_item["grievance_sub_type"],
                "sub_department": best_item.get("sub_department", ""),
                "responsible_officer": best_item.get("responsible_officer", ""),
                "validated": True,
                "match_score": best_score
            }

        # Graceful passthrough with normalized department
        return {
            "department": dept_norm,
            "grievance_type": gtype_in or "General Grievance",
            "grievance_subtype": gsub_in or "Public Grievance Redressal",
            "sub_department": f"{dept_norm.split('(')[0].strip()} / நிர்வாகம்",
            "responsible_officer": "வட்டாட்சியர் / துறை அலுவலர்",
            "validated": False,
            "match_score": 0
        }


# Singleton instance loaded dynamically from cm_helpline_taxonomy.json alone
taxonomy_matcher = CMHelplineTaxonomyValidator()
