import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Set, Union
import numpy as np

logger = logging.getLogger(__name__)


CANONICAL_PREDEFINED_TAXONOMY: List[Dict[str, str]] = [
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "grievance_type": "Social Security Schemes (SSS)",
        "grievance_sub_type": "Old Age Pension (OAP)",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "grievance_type": "Destitute Widow Pension Scheme (DWPS) / Social Security Schemes",
        "grievance_sub_type": "Destitute Widow Pension (DWP)",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Social Security Schemes (SSS) / Revenue Administration",
        "grievance_type": "Social Security Schemes (SSS)",
        "grievance_sub_type": "Differently Abled Pension (DAP)",
        "responsible_officer": "Special Tahsildar (SSS) / Tahsildar"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Revenue Administration",
        "grievance_type": "Public Relief Fund / Financial Assistance",
        "grievance_sub_type": "Chief Minister's Public Relief Fund (CMPRF)",
        "responsible_officer": "District Collector / District Revenue Officer (DRO)"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Revenue Administration / Land Records",
        "grievance_type": "Land Administration and Patta Transfer",
        "grievance_sub_type": "Patta Transfer - Individual / Sub-division",
        "responsible_officer": "Tahsildar / Zonal Deputy Tahsildar"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Revenue Administration / நில நிர்வாகம்",
        "grievance_type": "Natham Patta /Free House Site Patta",
        "grievance_sub_type": "Free House Site Patta (HSD)",
        "responsible_officer": "Tahsildar, Erode"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Revenue Administration",
        "grievance_type": "Land Encroachment",
        "grievance_sub_type": "Eviction of Encroachments on Government Land / Pathway",
        "responsible_officer": "Tahsildar / Revenue Divisional Officer (RDO)"
    },
    {
        "department": "Revenue and Disaster Management (REV)",
        "department_code": "REV",
        "sub_department": "Revenue Administration",
        "grievance_type": "Certificates and Verification",
        "grievance_sub_type": "Legal Heir Certificate / Community Certificate",
        "responsible_officer": "Tahsildar / Zonal Deputy Tahsildar"
    },
    {
        "department": "Municipal Administration and Water Supply (MAWS)",
        "department_code": "MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "grievance_type": "Drinking Water",
        "grievance_sub_type": "New Water Connection - Household Water Connection",
        "responsible_officer": "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
    },
    {
        "department": "Municipal Administration and Water Supply (MAWS)",
        "department_code": "MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "grievance_type": "Drinking Water",
        "grievance_sub_type": "Insufficient Water Supply",
        "responsible_officer": "Commissioner Municipality, Commissioner Municipal Corporation, Executive Officer - Town Panchayat"
    },
    {
        "department": "Municipal Administration and Water Supply (MAWS)",
        "department_code": "MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "grievance_type": "Street Lights - MAWS",
        "grievance_sub_type": "Street Lights - MAWS",
        "responsible_officer": "Commissioner Municipal Corporation / Municipality, Erode"
    },
    {
        "department": "Municipal Administration and Water Supply (MAWS)",
        "department_code": "MAWS",
        "sub_department": "Commissionerate of Municipal Administration (CMA)",
        "grievance_type": "Storm Water Drains - MAWS",
        "grievance_sub_type": "Storm Water Drains - MAWS",
        "responsible_officer": "Commissioner Municipal Corporation / Municipality, Erode"
    },
    {
        "department": "Rural Development and Panchayat Raj Department (RDPR)",
        "department_code": "RDPR",
        "sub_department": "Rural Development and Panchayat Raj",
        "grievance_type": "Village Infrastructure",
        "grievance_sub_type": "Drinking Water Supply - RD",
        "responsible_officer": "Block Development Officer - Village Panchayat"
    },
    {
        "department": "Rural Development and Panchayat Raj Department (RDPR)",
        "department_code": "RDPR",
        "sub_department": "Rural Development and Panchayat Raj",
        "grievance_type": "Village Infrastructure",
        "grievance_sub_type": "Street Light - RD",
        "responsible_officer": "Block Development Officer - Village Panchayat"
    },
    {
        "department": "Rural Development and Panchayat Raj Department (RDPR)",
        "department_code": "RDPR",
        "sub_department": "Rural Development and Panchayat Raj",
        "grievance_type": "Village Infrastructure",
        "grievance_sub_type": "Drainage and Sewage Issues",
        "responsible_officer": "Block Development Officer - Village Panchayat"
    },
    {
        "department": "Higher Education Department (HIGHEDU)",
        "department_code": "HIGHEDU",
        "sub_department": "Director Of Collegiate Education",
        "grievance_type": "Scholarship - High Edu",
        "grievance_sub_type": "Scholarship - High Edu",
        "responsible_officer": "Joint Director of Collegiate Education"
    },
    {
        "department": "Information Technology Department (IT)",
        "department_code": "IT",
        "sub_department": "Commissionerate of eGovernance/Tamil Nadu e-Governance Agency",
        "grievance_type": "Application Related Complaints - CeG",
        "grievance_sub_type": "eSevai - Complaint related to Aadhaar Enrolment",
        "responsible_officer": "e-sevai helpdesk"
    },
    {
        "department": "Energy Department (ENERGY)",
        "department_code": "ENERGY",
        "sub_department": "TANGEDCO",
        "grievance_type": "Electricity Supply and Metering",
        "grievance_sub_type": "Low Voltage / Power Fluctuation / Transformer Repair",
        "responsible_officer": "Section Officer (Distribution) - TANGEDCO"
    },
    {
        "department": "Co-operation, Food and Consumer Protection Department (FOODCO)",
        "department_code": "FOODCO",
        "sub_department": "Civil Supplies and Consumer Protection",
        "grievance_type": "Civil Supplies and Ration Services",
        "grievance_sub_type": "Smart Card / Ration Card Services / PDS Supplies",
        "responsible_officer": "District Supply Officer (DSO) / Taluk Supply Officer (TSO)"
    },
    {
        "department": "General Administration",
        "department_code": "GAD",
        "sub_department": "General Administration / பொது நிர்வாகம்",
        "grievance_type": "General Grievance",
        "grievance_sub_type": "Public Grievance Redressal",
        "responsible_officer": "துறை அலுவலர்"
    }
]


class CMHelplineTaxonomyValidator:
    """
    Loads official CM Helpline mappings from cm_taxonomy_mappings, which is
    populated from backend/data/government_taxonomy.pdf.
    Derives all official departments, grievance types, sub-types, sub-departments,
    and responsible officers dynamically from those database rows.
    """

    def __init__(self):
        self.taxonomy: List[Dict[str, Any]] = []
        self.taxonomy_by_id: Dict[int, Dict[str, Any]] = {}
        self.taxonomy_embeddings: Optional[np.ndarray] = None
        self.taxonomy_metadata: List[Dict[str, Any]] = []
        self.departments: List[str] = []
        self.department_acronyms: Dict[str, str] = {}
        self.dept_entries: Dict[str, List[Dict[str, Any]]] = {}
        self.subtypes_map: Dict[str, Dict[str, Any]] = {}
        self.types_map: Dict[str, List[str]] = {}
        self.concept_map = self._load_tamil_concept_map()

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
            "வழிப்பாதை": ["encroachment", "pathway"],
            "பட்டா": ["patta", "patta transfer"],
            "உட்பிரிவு": ["sub division", "survey"],
            "சர்வே": ["survey"],
            "வாரிசு": ["legal heir", "heir", "certificate"],
            "விதவை": ["destitute widow", "widow", "pension", "dwps"],
            "முதியோர்": ["old age pension", "pension", "oap", "social security"],
            "உதவித்தொகை": ["financial assistance", "assistance", "grant", "scholarship", "aid"],
            "உதவித் தொகை": ["financial assistance", "assistance", "grant", "scholarship", "aid"],
            "உதவி தொகை": ["financial assistance", "assistance", "grant", "scholarship", "aid"],
            "நிதி உதவி": ["financial assistance", "grant", "aid"],
            "வயது மூப்பு": ["old age pension", "pension", "oap", "social security"],
            "குடிநீர்": ["drinking water", "water supply"],
            "சாலை": ["road", "street"],
            "தெருவிளக்கு": ["street light", "lighting"],
            "மின்சாரம்": ["electricity", "power", "tangedco"],
            "ரேஷன்": ["ration card", "civil supplies"],
            "சாதி": ["community certificate"],
            "சமுதாய கூடம்": ["community hall"],
            "சமூக கூடம்": ["community hall"],
            "ஆதிதிராவிடர்": ["adi dravidar", "adw"],
            "ஆதி திராவிடர்": ["adi dravidar", "adw"]
        }

    async def load_taxonomy(self) -> int:
        """Load all PDF-seeded records from cm_taxonomy_mappings including precomputed embeddings."""
        from sqlalchemy import text
        from models.database import AdminAsyncSessionLocal

        async with AdminAsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT id, department, department_code, sub_department, grievance_type,
                       grievance_sub_type, responsible_officer, search_text, embedding
                FROM cm_taxonomy_mappings
                ORDER BY id
            """))
            records = []
            embeddings = []
            for row in result.mappings().all():
                rec = {
                    "id": row["id"],
                    "department": row["department"] or "",
                    "department_code": row["department_code"] or "",
                    "sub_department": row["sub_department"] or "",
                    "grievance_type": row["grievance_type"] or "",
                    "grievance_sub_type": row["grievance_sub_type"] or "",
                    "responsible_officer": row["responsible_officer"] or "",
                    "search_text": row["search_text"] or "",
                }
                emb_raw = row["embedding"]
                emb_vec = None
                if emb_raw:
                    try:
                        parsed = json.loads(emb_raw) if isinstance(emb_raw, str) else list(emb_raw)
                        if parsed and len(parsed) == 384:
                            emb_vec = np.array(parsed, dtype=np.float32)
                            norm = float(np.linalg.norm(emb_vec))
                            if norm > 0:
                                emb_vec = emb_vec / norm
                    except Exception as e:
                        logger.warning(f"Error parsing embedding for taxonomy id {row['id']}: {e}")
                if emb_vec is None:
                    emb_vec = np.zeros(384, dtype=np.float32)

                records.append(rec)
                embeddings.append(emb_vec)

        self._set_taxonomy(records, embeddings)
        logger.info("Loaded %s PDF-seeded taxonomy records (with %s vectors) from Admin DB.", len(records), len(embeddings))
        return len(records)

    def load_taxonomy_sync(self) -> int:
        """Synchronous loader for standalone scripts, testing, or sync execution paths."""
        if self.taxonomy and self.taxonomy_embeddings is not None and len(self.taxonomy_embeddings) > 0:
            return len(self.taxonomy)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.load_taxonomy())
                return future.result()
        else:
            return loop.run_until_complete(self.load_taxonomy())

    def _set_taxonomy(self, records: List[Dict[str, Any]], embeddings: Optional[List[np.ndarray]] = None) -> None:
        """Build lookup indexes and vector matrix from the database taxonomy rows."""
        self.taxonomy = records
        self.taxonomy_metadata = records
        self.taxonomy_by_id = {r["id"]: r for r in records if "id" in r}

        if embeddings is not None and len(embeddings) > 0:
            self.taxonomy_embeddings = np.array(embeddings, dtype=np.float32)
        elif self.taxonomy_embeddings is None:
            self.taxonomy_embeddings = np.zeros((len(records), 384), dtype=np.float32)

        try:
            # Reset containers
            dept_set: Set[str] = set()
            self.department_acronyms.clear()
            self.dept_entries.clear()
            self.subtypes_map.clear()
            self.types_map.clear()

            for item in self.taxonomy:
                dept = re.sub(r'\s+', ' ', (item.get("department") or "")).strip()
                gtype = re.sub(r'\s+', ' ', (item.get("grievance_type") or "")).strip()
                gsub = re.sub(r'\s+', ' ', (item.get("grievance_sub_type") or "")).strip()
                item["department"] = dept
                item["grievance_type"] = gtype
                item["grievance_sub_type"] = gsub
                if not item.get("scope_type"):
                    from services.grievance_scope_classifier import deduce_taxonomy_scope
                    item["scope_type"] = deduce_taxonomy_scope(dept, gtype, gsub)

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
            logger.info(f"Initialized {len(self.taxonomy)} taxonomy records, {len(self.departments)} departments.")
        except Exception as e:
            logger.error(f"Error processing taxonomy records: {e}")

    def search_candidates_by_vector(self, query_embedding: Union[List[float], np.ndarray], top_k: int = 12) -> List[Dict[str, Any]]:
        """
        Fast in-memory cosine similarity search against all 1,847 DB taxonomy embeddings.
        Returns top-K matching taxonomy candidates with similarity scores.
        """
        if self.taxonomy_embeddings is None or len(self.taxonomy_embeddings) == 0:
            logger.warning("Taxonomy embeddings matrix is empty or uninitialized.")
            return []

        q = np.array(query_embedding, dtype=np.float32)
        if q.ndim > 1:
            q = q.squeeze()
        if len(q) != 384:
            logger.warning(f"Query embedding dimension mismatch: expected 384, got {len(q)}")
            return []

        norm = float(np.linalg.norm(q))
        if norm > 0:
            q = q / norm
        else:
            return []

        # Vectorized dot product against all N normalized taxonomy embeddings
        scores = np.dot(self.taxonomy_embeddings, q)
        k_val = min(top_k, len(scores))
        top_indices = np.argsort(-scores)[:k_val]

        candidates = []
        for idx in top_indices:
            meta = self.taxonomy_metadata[idx]
            candidates.append({
                "taxonomy_id": meta["id"],
                "Department": meta.get("department", ""),
                "department": meta.get("department", ""),
                "department_code": meta.get("department_code", ""),
                "Grievance Type": meta.get("grievance_type", ""),
                "grievance_type": meta.get("grievance_type", ""),
                "Grievance Sub Type": meta.get("grievance_sub_type", ""),
                "grievance_sub_type": meta.get("grievance_sub_type", ""),
                "Sub Department": meta.get("sub_department", ""),
                "sub_department": meta.get("sub_department", ""),
                "Responsible officer": meta.get("responsible_officer", ""),
                "responsible_officer": meta.get("responsible_officer", ""),
                "search_text": meta.get("search_text", ""),
                "semantic_score": round(float(scores[idx]), 4),
            })
        return candidates

    def get_taxonomy_by_id(self, taxonomy_id: Optional[Union[int, str]]) -> Optional[Dict[str, Any]]:
        """Returns the authoritative DB taxonomy row for the given ID."""
        if taxonomy_id is None:
            return None
        try:
            return self.taxonomy_by_id.get(int(taxonomy_id))
        except (ValueError, TypeError):
            return None

    def get_candidates(self, header_dept_keyword: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Filters candidates by header metadata / keywords if present, else returns top-K rows.
        Returns format with both standard keys and Taxonomy_ID.
        """
        source_items = self.taxonomy
        if header_dept_keyword:
            kw = header_dept_keyword.strip().lower()
            # Expand with semantic concept terms if Tamil keyword (e.g. குடிநீர் -> drinking water, water supply)
            search_terms = {kw}
            for c_key, c_terms in self.concept_map.items():
                if c_key in kw or kw in c_key:
                    search_terms.update([t.lower() for t in c_terms])

            scoped = []
            for item in self.taxonomy:
                dept_val = item.get("department", "").lower()
                gtype_val = item.get("grievance_type", "").lower()
                gsub_val = item.get("grievance_sub_type", "").lower()
                item_str = f"{dept_val} {gtype_val} {gsub_val}"
                if any(term in item_str for term in search_terms):
                    scoped.append(item)
            if scoped:
                source_items = scoped

        candidates = []
        for item in source_items[:top_k]:
            candidates.append({
                "Taxonomy_ID": item.get("id"),
                "taxonomy_id": item.get("id"),
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
        """Returns departments present in the PDF-seeded Admin DB taxonomy."""
        return list(self.departments)

    def normalize_department(self, dept_input: Optional[str]) -> str:
        """
        Dynamically matches and normalizes any user/LLM input against the official
        departments present in the PDF-seeded Admin DB taxonomy.
        """
        if not dept_input:
            return "General Administration"

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

        # 4. Keyword / concept routing to official departments
        raw_lower = raw.lower()
        if any(k in raw_lower for k in ["revenue", "வருவாய்", "நில நிர்வாகம்", "social security", "சமூக பாதுகாப்பு", "ஓய்வூதியம்", "pension"]):
            return self.department_acronyms.get("REV", "Revenue and Disaster Management (REV)")
        if any(k in raw_lower for k in ["municipal", "water supply", "cma", "twad", "மாநகராட்சி", "நகராட்சி", "குடிநீர்"]):
            return self.department_acronyms.get("MAWS", "Municipal Administration and Water Supply (MAWS)")
        if any(k in raw_lower for k in ["rural", "panchayat", "ஊராட்சி", "பஞ்சாயத்து"]):
            return self.department_acronyms.get("RDPR", "Rural Development and Panchayat Raj Department (RDPR)")
        if any(k in raw_lower for k in ["education", "collegiate", "scholarship", "கல்வி", "கல்லூரி"]):
            return self.department_acronyms.get("HIGHEDU", "Higher Education Department (HIGHEDU)")
        if any(k in raw_lower for k in ["energy", "electricity", "tangedco", "மின்"]):
            return self.department_acronyms.get("ENERGY", "Energy Department (ENERGY)")
        if any(k in raw_lower for k in ["police", "home", "காவல்"]):
            return self.department_acronyms.get("HOMEEXE", "Home, Prohibition and Excise Department (HOMEEXE)")
        if any(k in raw_lower for k in ["civil supplies", "food", "ration", "ரேஷன்", "உணவு"]):
            return self.department_acronyms.get("FOODCO", "Co-operation, Food and Consumer Protection Department (FOODCO)")
        if any(k in raw_lower for k in ["technology", "it", "esevai", "ceg", "ஆதார்"]):
            return self.department_acronyms.get("IT", "Information Technology Department (IT)")

        # Reject unrecognized / hallucinated strings (e.g. "தேவாலய மாநாடு")
        logger.warning(f"Unrecognized department '{raw}' rejected -> defaulting to 'General Administration'")
        return "General Administration"

    def get_types_for_department(self, department: str) -> List[str]:
        """Returns grievance types present for a DB taxonomy department."""
        norm_dept = self.normalize_department(department)
        return sorted(self.types_map.get(norm_dept, []))

    def get_subtypes_for_department(self, department: str) -> List[str]:
        """Returns grievance sub-types present for a DB taxonomy department."""
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
        1. Normalizes department using departments loaded from the PDF-seeded DB rows.
        2. Matches exact or high-confidence sub-types from the loaded taxonomy records.
        3. Fills official sub_department and responsible_officer.
        4. Gracefully passes through if novel.
        """
        dept_norm = self.normalize_department(detected_dept) or "General Administration"
        gtype_in = (detected_type or "").strip()
        gsub_in = (detected_subtype or "").strip()

        if not self.taxonomy:
            dept_prefix = dept_norm.split('(')[0].strip()
            return {
                "department": dept_norm,
                "grievance_type": gtype_in or "General Grievance",
                "grievance_subtype": gsub_in or "Public Grievance Redressal",
                "sub_department": f"{dept_prefix} Administration",
                "responsible_officer": "Competent Authority",
                "scope_type": "UNKNOWN",
                "validated": False,
                "match_score": 0
            }

        # Step 1: Direct exact match on sub-type from the JSON taxonomy
        if gsub_in and gsub_in.lower() in self.subtypes_map:
            item = self.subtypes_map[gsub_in.lower()]
            return {
                "department": item["department"],
                "grievance_type": item["grievance_type"] or "General Grievance",
                "grievance_subtype": item["grievance_sub_type"] or "Public Grievance Redressal",
                "sub_department": item.get("sub_department", ""),
                "responsible_officer": item.get("responsible_officer", ""),
                "validated": True,
                "match_score": 100
            }

        # Step 2: Semantic concept bridge for Tamil grievance terminology
        concept_terms = set()
        is_education_query = any(k in (gtype_in + " " + gsub_in + " " + petition_text).lower() for k in ["கல்வி", "படிப்பு", "கல்லூரி", "பள்ளி", "மாணவர்", "scholarship", "education", "degree"])
        is_employee_query = any(k in (gtype_in + " " + gsub_in + " " + petition_text).lower() for k in ["employee", "பணியாளர்", "ஊழியர்", "ஆசிரியர் பணி"])

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
        elif dept_norm and dept_norm != "General Administration" and dept_norm in self.dept_entries:
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
            if not is_employee_query and ("employee" in t_gtype or "pension" in t_gsub or "pension" in t_gtype) and is_education_query:
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

            # Financial assistance / Old Age Pension / Social Security Schemes priority
            if any(s in query_text for s in ["வயது மூப்பு", "முதியோர்", "முதியவர்", "வேலைக்கு செல்ல முடியவில்லை", "வாழ்வாதாரம்", "old age pension", "oap"]):
                if "social security" in t_gtype or "old age pension" in t_gsub or "oap" in t_gsub or "pension" in t_gsub:
                    score += 40.0
                if "revenue" in t_dept:
                    score += 20.0

            # Encroachment priority for land/pathway grievances
            if any(e in query_text for e in ["encroachment", "ஆக்கிரமிப்பு", "பொதுப்பாதை", "முள்வேலி", "வழிப்பாதை"]):
                if "encroachment" in t_gsub or "encroachment" in t_gtype or "eviction of encroachments" in t_gsub:
                    score += 25.0
                    if any(r in query_text for r in ["வருவாய்", "revenue", "நில அளவை", "சர்வே", "கிராம", "பாதை", "வழி"]):
                        if "revenue" in t_dept:
                            score += 20.0

            # Scholarship priority when seeking educational financial assistance
            if any(s in query_text for s in ["scholarship", "கல்வி உதவித்தொகை", "கல்வி உதவி", "படிப்பு", "கல்லூரி", "மாணவர்", "மாணவி"]):
                if "scholarship" in t_gsub or "கல்வி" in t_gsub:
                    score += 35.0
                elif "scholarship" in t_gtype or "கல்வி" in t_gtype:
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
            final_type = best_item["grievance_type"] or "General Grievance"
            final_subtype = best_item["grievance_sub_type"] or "Public Grievance Redressal"

            return {
                "department": best_item["department"],
                "grievance_type": final_type,
                "grievance_subtype": final_subtype,
                "sub_department": best_item.get("sub_department", ""),
                "responsible_officer": best_item.get("responsible_officer", ""),
                "scope_type": best_item.get("scope_type", "UNKNOWN"),
                "validated": True,
                "match_score": best_score
            }

        # Graceful passthrough with normalized department
        fallback_dept = dept_norm or "General Administration"
        return {
            "department": fallback_dept,
            "grievance_type": "General Grievance",
            "grievance_subtype": "Public Grievance Redressal",
            "sub_department": f"{fallback_dept.split('(')[0].strip()} / நிர்வாகம்",
            "responsible_officer": "துறை அலுவலர்",
            "scope_type": "UNKNOWN",
            "validated": False,
            "match_score": 0
        }


# Backward compatibility and new CM Grievance Mapper aliases
CMGrievanceMapper = CMHelplineTaxonomyValidator
TaxonomyMatcher = CMHelplineTaxonomyValidator
CMHelplineTaxonomyMatcher = CMHelplineTaxonomyValidator

# Singleton instance loaded dynamically from database alone
taxonomy_matcher = CMHelplineTaxonomyValidator()
cm_grievance_mapper = taxonomy_matcher

