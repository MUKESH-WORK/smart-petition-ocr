"""
CM Grievance Redressal RAG & Adjudication Engine
================================================
Authoritative retrieval and deterministic routing engine for the Tamil Nadu
CM Helpline Grievance Redressal System (CM Helpline Grievances Mapping).

Architecture:
  [Citizen / Natural Language Input]
                 │
                 ▼
  [Geographic Context Extraction & Resolution]
  (Master Locations: Village, Town, Ward, Firka, Taluk, Block)
                 │
                 ▼
  [3-Tier Adjudication Pathing & Hybrid RAG Retrieval]
  Tier 1: Revenue & Land Administration (REV -> Tahsildar / RDO / DRO)
  Tier 2: Civic Amenities (Urban MAWS vs Rural RDPR)
  Tier 3: Public Safety, Health, Agriculture, Education & Specialized PSUs
                 │
                 ▼
  [Deterministic 5-Level Mapping Output]
  1. Department (Level 1)
  2. Grievance Type (Level 2)
  3. Grievance Sub-Type (Level 3)
  4. Sub-Department / Board / PSU (Level 4)
  5. Responsible Officer (Level 5)
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy import text
from models.database import AdminAsyncSessionLocal, is_admin_sqlite
from services.vector_store import vector_store

logger = logging.getLogger("cm_grievance_rag")


class CMGrievanceRAGEngine:
    """
    RAG Engine that queries live SQLite/PostgreSQL `cm_taxonomy_mappings`
    and `master_locations` tables without relying on static JSON files.
    """

    def __init__(self):
        self._cached_embeddings = None
        self._cached_records = None
        self._lock = asyncio.Lock()

    async def _load_taxonomy_cache(self, db):
        """Loads and caches taxonomy mappings into memory for low-latency vector cosine scoring."""
        if self._cached_records is not None:
            return self._cached_records, self._cached_embeddings

        async with self._lock:
            if self._cached_records is not None:
                return self._cached_records, self._cached_embeddings

            rows = (await db.execute(text("""
                SELECT id, department, department_code, sub_department, 
                       grievance_type, grievance_sub_type, responsible_officer, 
                       search_text, embedding
                FROM cm_taxonomy_mappings
            """))).fetchall()

            records = []
            embeddings = []
            for r in rows:
                rec = {
                    "id": r[0],
                    "department": r[1],
                    "department_code": r[2],
                    "sub_department": r[3],
                    "grievance_type": r[4],
                    "grievance_sub_type": r[5],
                    "responsible_officer": r[6],
                    "search_text": r[7] or ""
                }
                emb_raw = r[8]
                if emb_raw:
                    try:
                        emb = json.loads(emb_raw) if isinstance(emb_raw, str) else list(emb_raw)
                        records.append(rec)
                        embeddings.append(emb)
                    except Exception:
                        continue
                else:
                    records.append(rec)
                    embeddings.append([0.0] * 384)

            self._cached_records = records
            self._cached_embeddings = np.array(embeddings, dtype=np.float32) if embeddings else None
            logger.info(f"Loaded {len(records)} CM Grievance Taxonomy records into RAG memory cache.")
            return self._cached_records, self._cached_embeddings

    def _rule_based_tier_routing(self, query_lower: str, location_meta: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Applies Tamil Nadu Governance 3-Tier Resolution Rules:
        Tier 1: Revenue & Land (REV)
        Tier 2: Civic Amenities (Urban MAWS vs Rural RDPR)
        Tier 3: Police (HOMEEXE), Health (HEALTH), Electricity (ENERGY), Agriculture (AGRI), Ration (FOODCO)
        """
        loc_type = (location_meta or {}).get("local_body_type", "").lower()

        # ── Tier 1: Revenue & Land Administration ──────────────────────────
        rev_triggers = [
            "patta", "பட்டா", "chitta", "சிட்டா", "adangal", "அடங்கல்",
            "boundary", "எல்லை", "fmb", "subdivision", "உட்பிரிவு",
            "dispute", "தகராறு", "encroachment", "ஆக்கிரமிப்பு",
            "oap", "முதியோர்", "old age pension",
            "legal heir", "வாரிசு", "community certificate", "சாதி சான்றிதழ்",
            "tahsildar", "தாசில்தார்", "வட்டாட்சியர்"
        ]
        if any(w in query_lower for w in rev_triggers):
            return {
                "department": "Revenue and Disaster Management Department",
                "department_code": "REV",
                "sub_department": "Revenue Administration and Land Records",
                "priority_dept": True,
                "default_officer": "Tahsildar"
            }

        # ── Tier 2: Civic Amenities (Dual Urban / Rural Branch) ────────────
        urban_triggers = [
            "corporation", "மாநகராட்சி", "municipality", "நகராட்சி",
            "underground drainage", "ugd", "பாதாள சாக்கடை",
            "metro water", "குடிநீர் வடிகால்", "town panchayat", "பேரூராட்சி"
        ]
        rural_triggers = [
            "village panchayat", "ஊராட்சி", "கிராம ஊராட்சி",
            "100 days work", "100 நாள் வேலை", "mgnregs",
            "overhead tank", "மேல்நிலை நீர்", "panchayat secretary", "ஊராட்சி செயலாளர்"
        ]

        is_urban_context = "corporation" in loc_type or "municipality" in loc_type or "town" in loc_type or any(u in query_lower for u in urban_triggers)
        is_rural_context = "village" in loc_type or "rural" in loc_type or any(r in query_lower for r in rural_triggers)

        # Drinking water & drainage routing
        water_civic_triggers = [
            "drinking water", "குடிநீர்", "pipeline", "குழாய்",
            "drainage", "சாக்கடை", "garbage", "குப்பை",
            "street light", "தெருவிளக்கு", "streetlights"
        ]
        if any(w in query_lower for w in water_civic_triggers):
            if is_urban_context and not is_rural_context:
                return {
                    "department": "Municipal Administration and Water Supply",
                    "department_code": "MAWS",
                    "sub_department": "TWAD Board / Municipal Administration",
                    "priority_dept": True,
                    "default_officer": "Municipal Commissioner / Executive Officer (Town Panchayat)"
                }
            else:
                return {
                    "department": "Rural Development and Panchayat Raj Department",
                    "department_code": "RDPR",
                    "sub_department": "Directorate of Rural Development",
                    "priority_dept": True,
                    "default_officer": "Block Development Officer (BDO - Village Panchayat)"
                }

        # ── Tier 3: Law & Order, Health, Power, Food ──────────────────────
        # Police & Excise
        police_triggers = ["police", "போலீஸ்", "theft", "திருட்டு", "fir", "முதல் தகவல்", "cyber", "சைபர்", "tasmac", "டாஸ்மாக்", "harassment", "கொலை", "கற்பழிப்பு"]
        if any(w in query_lower for w in police_triggers):
            return {
                "department": "Home, Prohibition and Excise Department",
                "department_code": "HOMEEXE",
                "sub_department": "Tamil Nadu Police",
                "priority_dept": True,
                "default_officer": "Inspector of Police (Station House Officer)"
            }

        # Health
        health_triggers = ["hospital", "மருத்துவமனை", "gh", "doctor", "மருத்துவர்", "nurse", "செவிலியர்", "phc", "ஆரம்ப சுகாதார", "cmchis", "மருத்துவ காப்பீடு"]
        if any(w in query_lower for w in health_triggers):
            return {
                "department": "Health and Family Welfare Department",
                "department_code": "HEALTH",
                "sub_department": "Directorate of Public Health / DME",
                "priority_dept": True,
                "default_officer": "Joint Director of Health Services / DPH"
            }

        # Energy / TANGEDCO
        power_triggers = ["electricity", "மின்சாரம்", "power", "tangedco", "மின்சார வாரியம்", "transformer", "டிரான்ஸ்பார்மர்", "eb", "இபி"]
        if any(w in query_lower for w in power_triggers):
            return {
                "department": "Energy Department",
                "department_code": "ENERGY",
                "sub_department": "TANGEDCO",
                "priority_dept": True,
                "default_officer": "Section Officer (Distribution) - TANGEDCO"
            }

        # Civil Supplies & Ration
        ration_triggers = ["ration", "ரேஷன்", "smart card", "குடும்ப அட்டை", "fair price", "நியாய விலைக்கடை", "pds", "rice", "அரிசி"]
        if any(w in query_lower for w in ration_triggers):
            return {
                "department": "Co-operation, Food and Consumer Protection Department",
                "department_code": "FOODCO",
                "sub_department": "Civil Supplies and Consumer Protection",
                "priority_dept": True,
                "default_officer": "District Supply Officer (DSO) / Taluk Supply Officer (TSO)"
            }

        # Agriculture
        agri_triggers = ["pm-kisan", "விவசாயம்", "farmer", "உழவர்", "fertilizer", "உரம்", "paddy", "நெல் கொள்முதல்", "dpc", "seed", "விதை"]
        if any(w in query_lower for w in agri_triggers):
            return {
                "department": "Agriculture and Farmers Welfares Department",
                "department_code": "AGRI",
                "sub_department": "Directorate of Agriculture",
                "priority_dept": True,
                "default_officer": "Joint Director of Agriculture"
            }

        return None

    async def search_grievance(
        self,
        query_text: str,
        location_context: Optional[Dict[str, Any]] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid semantic search + deterministic adjudication pathing
        against `cm_taxonomy_mappings`. Returns top matching records with scores.
        """
        if not query_text or not query_text.strip():
            return []

        clean_query = query_text.strip().lower()

        # Step 1: Check Deterministic Resolution Rules
        tier_rule = self._rule_based_tier_routing(clean_query, location_context)

        # Step 2: Compute Query Vector
        try:
            query_embeddings = await vector_store.aencode([query_text])
            query_emb = np.array(query_embeddings[0], dtype=np.float32)
        except Exception as e:
            logger.warning(f"Embedding computation note: {e}")
            query_emb = None

        # Step 3: Cosine Similarity Scoring from Cache
        async with AdminAsyncSessionLocal() as db:
            records, embeddings = await self._load_taxonomy_cache(db)

        if not records:
            return []

        scores = np.zeros(len(records), dtype=np.float32)

        # Dense Vector Cosine Similarity
        if query_emb is not None and embeddings is not None and len(embeddings) == len(records):
            norms = np.linalg.norm(embeddings, axis=1) * (np.linalg.norm(query_emb) + 1e-9)
            norms[norms == 0] = 1.0
            scores += (np.dot(embeddings, query_emb) / norms) * 0.65

        # Sparse Keyword / Token Scoring & Tier Boost
        query_tokens = [w for w in clean_query.split() if len(w) > 2]
        for idx, r in enumerate(records):
            stext = (r["search_text"] or "").lower()
            sub_type = (r["grievance_sub_type"] or "").lower()
            g_type = (r["grievance_type"] or "").lower()
            dept = (r["department"] or "").lower()

            # Token overlap boost
            overlap = 0
            for t in query_tokens:
                if t in sub_type:
                    overlap += 0.25
                elif t in g_type:
                    overlap += 0.15
                elif t in stext:
                    overlap += 0.08
            scores[idx] += min(overlap, 0.40)

            # Rule Tier Boost
            if tier_rule:
                if r.get("department_code") == tier_rule.get("department_code") or r.get("department") == tier_rule.get("department"):
                    scores[idx] += 0.35

        # Rank and return top_k
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for rank, i in enumerate(top_indices, 1):
            item = dict(records[i])
            item["confidence_score"] = float(round(scores[i], 4))
            item["rank"] = rank
            if tier_rule and not item.get("responsible_officer"):
                item["responsible_officer"] = tier_rule.get("default_officer")
            results.append(item)

        return results

    async def resolve_location(self, text_snippet: str) -> Optional[Dict[str, Any]]:
        """
        Resolves village, town, ward, firka, or taluk from text to the
        exact administrative hierarchy using `master_locations`.
        """
        if not text_snippet or not text_snippet.strip():
            return None

        clean = text_snippet.strip().lower()

        async with AdminAsyncSessionLocal() as db:
            # 1. Exact or partial match on village, town, ward, or firka
            sql = """
                SELECT id, district_name_en, district_name_tamil,
                       division_name_en, division_name_tamil,
                       taluk_name_en, taluk_name_tamil,
                       firka_name_en, firka_name_tamil,
                       block_name_en, block_name_tamil,
                       village_name_en, village_name_tamil,
                       local_body_type, ward_no, pincode, sub_departments
                FROM master_locations
                WHERE LOWER(village_name_en) = :val
                   OR LOWER(village_name_tamil) = :val
                   OR LOWER(taluk_name_en) = :val
                   OR LOWER(firka_name_en) = :val
                   OR LOWER(block_name_en) = :val
                LIMIT 1
            """
            row = (await db.execute(text(sql), {"val": clean})).fetchone()

            if not row:
                # 2. Substring search if exact match fails
                sql_sub = """
                    SELECT id, district_name_en, district_name_tamil,
                           division_name_en, division_name_tamil,
                           taluk_name_en, taluk_name_tamil,
                           firka_name_en, firka_name_tamil,
                           block_name_en, block_name_tamil,
                           village_name_en, village_name_tamil,
                           local_body_type, ward_no, pincode, sub_departments
                    FROM master_locations
                    WHERE (village_name_en IS NOT NULL AND INSTR(:val, LOWER(village_name_en)) > 0)
                       OR (taluk_name_en IS NOT NULL AND INSTR(:val, LOWER(taluk_name_en)) > 0)
                       OR (firka_name_en IS NOT NULL AND INSTR(:val, LOWER(firka_name_en)) > 0)
                    ORDER BY LENGTH(COALESCE(village_name_en, taluk_name_en)) DESC
                    LIMIT 1
                """
                row = (await db.execute(text(sql_sub), {"val": clean})).fetchone()

            if row:
                return {
                    "id": row[0],
                    "district": row[1],
                    "district_tamil": row[2],
                    "division": row[3],
                    "division_tamil": row[4],
                    "taluk": row[5],
                    "taluk_tamil": row[6],
                    "firka": row[7],
                    "firka_tamil": row[8],
                    "block": row[9],
                    "block_tamil": row[10],
                    "village": row[11],
                    "village_tamil": row[12],
                    "local_body_type": row[13],
                    "ward_no": row[14],
                    "pincode": row[15],
                    "sub_departments": row[16]
                }

        return None

    async def get_all_intake_channels(self) -> List[Dict[str, Any]]:
        """Returns all 21 intake channels grouped from cm_grievance_channels."""
        async with AdminAsyncSessionLocal() as db:
            rows = (await db.execute(text("""
                SELECT id, category, channel_name, channel_code, is_active, description
                FROM cm_grievance_channels
                ORDER BY id ASC
            """))).fetchall()

            return [{
                "id": r[0],
                "category": r[1],
                "channel_name": r[2],
                "channel_code": r[3],
                "is_active": bool(r[4]),
                "description": r[5] or ""
            } for r in rows]


# Singleton instance
cm_grievance_rag = CMGrievanceRAGEngine()
