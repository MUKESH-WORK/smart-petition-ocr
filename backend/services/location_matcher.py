import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from sqlalchemy import text

logger = logging.getLogger(__name__)

GENERIC_LOCATION_TERMS = {
    "ரோடு", "தெரு", "சாலை", "நகர்", "வட்டம்", "மாவட்டம்", "அஞ்சல்", "கிராமம்", "கிராம",
    "பகுதி", "பகுதிகள்", "எல்லை", "மேற்கு", "கிழக்கு", "வடக்கு", "தெற்கு", "மத்தி",
    "மற்றும்", "காலனி", "விரிவாக்கம்", "நகரம்", "பழைய", "புதிய", "வணிக", "மேல்",
    "ஈரோடு", "erode", "ஹவுசிங்", "யூனிட்",
    "road", "street", "nagar", "taluk", "district", "post", "village", "area",
    "areas", "boundary", "limits", "west", "east", "north", "south", "central",
    "and", "colony", "extn", "extension", "town", "old", "new", "commercial",
    "upper", "lower", "main", "housing", "unit"
}


class ErodeLocationHierarchyMatcher:
    """
    Database-driven Administrative Hierarchy Resolver.
    
    Dynamically loads and matches administrative hierarchy from the PostgreSQL
    `master_locations` table:
    - Revenue Divisions (division_name_tamil, division_name_en)
    - Taluks (taluk_name_tamil, taluk_name_en)
    - Development Blocks (block_name_tamil, block_name_en)
    - Revenue Firkas (firka_name_tamil, firka_name_en)
    - Municipalities & Corporations (local_body_type)
    - Corporation Zones & Wards (ward_no, ward_name_tamil, ward_name_en)
    - Revenue Villages (village_name_tamil, village_name_en)

    All administrative relationships are derived 100% from database records.
    Zero hardcoded if/elif taluk->division or taluk->block business logic in code.
    """

    def __init__(self, json_path: Optional[str] = None):
        self.hierarchy_path = self._resolve_path(json_path)
        self.hierarchy_data: Dict[str, Any] = {}
        
        # Dynamic database-driven indexes
        self.taluk_to_division: Dict[str, str] = {}
        self.taluk_to_division_en: Dict[str, str] = {}
        self.taluk_to_blocks: Dict[str, List[str]] = {}
        self.firka_to_taluk: Dict[str, str] = {}
        self.firka_to_block: Dict[str, str] = {}
        self.village_to_block: Dict[str, str] = {}
        self.firka_keywords: List[Dict[str, Any]] = []
        self.taluk_keywords: List[Dict[str, Any]] = []
        
        # Dynamic Ward, Local Body and Revenue Village indexes
        self.all_wards: List[Dict[str, Any]] = []
        self.ward_keywords: List[Dict[str, Any]] = []
        self.local_body_entries: List[Dict[str, Any]] = []
        self.village_keywords: List[Dict[str, Any]] = []

        self.district_name_ta: Optional[str] = None
        self.district_name_en: Optional[str] = None

        # Load initial hierarchy if local JSON exists
        self.load_hierarchy()

    @staticmethod
    def _resolve_path(json_path: Optional[str] = None) -> str:
        if json_path and os.path.exists(json_path):
            return json_path

        env_path = os.environ.get("ERODE_HIERARCHY_JSON_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "erode_administrative_hierarchy.json"),
            os.path.join(os.getcwd(), "backend", "data", "erode_administrative_hierarchy.json"),
            os.path.join(os.getcwd(), "data", "erode_administrative_hierarchy.json"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                return cand

        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "erode_administrative_hierarchy.json")

    def sync_from_rows(self, rows: List[Dict[str, Any]]) -> int:
        """
        Dynamically builds all indexing structures directly from PostgreSQL
        `master_locations` rows without any hardcoded Python classification logic.
        """
        if not rows:
            return 0

        self.taluk_to_division.clear()
        self.taluk_to_division_en.clear()
        self.taluk_to_blocks.clear()
        self.firka_to_taluk.clear()
        self.firka_to_block.clear()
        self.village_to_block.clear()
        self.firka_keywords.clear()
        self.taluk_keywords.clear()
        self.all_wards.clear()
        self.ward_keywords.clear()
        self.local_body_entries.clear()
        self.village_keywords.clear()

        for r in rows:
            dist_ta = str(r.get("district_name_tamil") or "").strip()
            dist_en = str(r.get("district_name_en") or "").strip()
            div_ta = str(r.get("division_name_tamil") or "").strip()
            div_en = str(r.get("division_name_en") or "").strip()
            t_ta = str(r.get("taluk_name_tamil") or "").strip()
            t_en = str(r.get("taluk_name_en") or "").strip()
            f_ta = str(r.get("firka_name_tamil") or "").strip()
            f_en = str(r.get("firka_name_en") or "").strip()
            b_ta = str(r.get("block_name_tamil") or "").strip()
            b_en = str(r.get("block_name_en") or "").strip()
            v_ta = str(r.get("village_name_tamil") or "").strip()
            v_en = str(r.get("village_name_en") or "").strip()
            lb_type = str(r.get("local_body_type") or "").strip()
            w_no = r.get("ward_no")
            w_ta = str(r.get("ward_name_tamil") or "").strip()
            w_en = str(r.get("ward_name_en") or "").strip()
            pincode = str(r.get("pincode") or "").strip()

            if dist_ta and not self.district_name_ta:
                self.district_name_ta = dist_ta
            if dist_en and not self.district_name_en:
                self.district_name_en = dist_en

            # 1. Taluk -> Division mapping (100% database derived)
            if t_ta and div_ta:
                self.taluk_to_division[t_ta] = div_ta
                if t_en:
                    self.taluk_to_division[t_en.lower()] = div_ta
                if div_en:
                    self.taluk_to_division_en[t_ta] = div_en
                    if t_en:
                        self.taluk_to_division_en[t_en.lower()] = div_en

                if not any(k.get("taluk_ta") == t_ta for k in self.taluk_keywords):
                    t_kws = [t_ta.lower()]
                    if t_en:
                        t_kws.append(t_en.lower())
                    self.taluk_keywords.append({
                        "taluk_ta": t_ta,
                        "taluk_en": t_en,
                        "division_ta": div_ta,
                        "division_en": div_en,
                        "keywords": t_kws
                    })

            # 2. Taluk -> Development Blocks mapping (100% database derived)
            if t_ta and b_ta:
                if t_ta not in self.taluk_to_blocks:
                    self.taluk_to_blocks[t_ta] = []
                if b_ta not in self.taluk_to_blocks[t_ta]:
                    self.taluk_to_blocks[t_ta].append(b_ta)
                if t_en:
                    if t_en.lower() not in self.taluk_to_blocks:
                        self.taluk_to_blocks[t_en.lower()] = []
                    if b_ta not in self.taluk_to_blocks[t_en.lower()]:
                        self.taluk_to_blocks[t_en.lower()].append(b_ta)

            # 3. Firka -> Taluk and Firka -> Block mapping
            if f_ta:
                if t_ta:
                    self.firka_to_taluk[f_ta] = t_ta
                    if f_en:
                        self.firka_to_taluk[f_en.lower()] = t_ta
                if b_ta:
                    self.firka_to_block[f_ta] = b_ta
                    if f_en:
                        self.firka_to_block[f_en.lower()] = b_ta

                if not any(fk.get("firka_ta") == f_ta and fk.get("taluk_ta") == t_ta for fk in self.firka_keywords):
                    raw_kws = [f_ta.lower()]
                    if f_en:
                        raw_kws.append(f_en.lower())
                    clean_ta_base = re.sub(r'\(.*?\)', '', f_ta).strip().lower()
                    if clean_ta_base and len(clean_ta_base) >= 4:
                        raw_kws.append(clean_ta_base)
                    for part in re.split(r'[/]', f_ta):
                        p_clean = part.strip().lower()
                        if len(p_clean) >= 4:
                            raw_kws.append(p_clean)

                    clean_kws = [k for k in set(raw_kws) if k and k not in ["கிழக்கு", "மேற்கு", "வடக்கு", "தெற்கு", "east", "west", "north", "south"]]
                    if not clean_kws and f_ta:
                        clean_kws = [f"{t_ta} {f_ta}".lower()]

                    self.firka_keywords.append({
                        "firka_ta": f_ta,
                        "firka_en": f_en,
                        "taluk_ta": t_ta,
                        "taluk_en": t_en,
                        "division_ta": div_ta,
                        "division_en": div_en,
                        "block_ta": b_ta,
                        "keywords": clean_kws
                    })

            # 4. Village leaf indexing
            if v_ta:
                if b_ta:
                    self.village_to_block[v_ta] = b_ta
                    if v_en:
                        self.village_to_block[v_en.lower()] = b_ta

                v_kws = [v_ta.lower()]
                if v_en:
                    v_kws.append(v_en.lower())
                if " " in v_ta:
                    for p in v_ta.split():
                        if len(p) >= 4 and p.lower() not in GENERIC_LOCATION_TERMS:
                            v_kws.append(p.lower())

                if not any(vk.get("village_name") == v_ta and vk.get("taluk_ta") == t_ta for vk in self.village_keywords):
                    self.village_keywords.append({
                        "village_name": v_ta,
                        "village_name_en": v_en,
                        "category": "Rural" if "Panchayat" in lb_type or "Rural" in lb_type else "Urban",
                        "gram_panchayat": v_ta if "Panchayat" in lb_type else "Not applicable",
                        "taluk_ta": t_ta,
                        "taluk_en": t_en,
                        "division_ta": div_ta,
                        "division_en": div_en,
                        "firka_ta": f_ta,
                        "firka_en": f_en,
                        "block_ta": b_ta,
                        "block_en": b_en,
                        "district_ta": dist_ta,
                        "district_en": dist_en,
                        "keywords": list(set(v_kws))
                    })

            # 5. Local Body & Ward indexing
            if w_no is not None or (lb_type and lb_type not in ["Development Block", "Village Panchayat", "Rural"]):
                primary_ward_name = w_ta or w_en or (f"Ward {w_no}" if w_no is not None else "")
                ward_record = {
                    "ward": primary_ward_name,
                    "ward_name": w_ta,
                    "ward_name_ta": w_ta,
                    "ward_name_en": w_en,
                    "ward_no": w_no,
                    "pincode": pincode,
                    "municipality_ward": lb_type,
                    "municipality_ward_ta": lb_type,
                    "local_body_type": lb_type or "Local Body",
                    "zone": None,
                    "zone_ta": None,
                    "firka": f_ta,
                    "firka_en": f_en,
                    "taluk": t_ta,
                    "taluk_en": t_en,
                    "revenue_division": div_ta,
                    "revenue_division_en": div_en,
                    "district": dist_ta
                }
                self.all_wards.append(ward_record)

                w_kws = set()
                if w_ta:
                    w_kws.add(w_ta.lower().strip())
                    for token in re.split(r'[\(\)\[\]\{\}\&/,;]|மற்றும்|மத்தி|பகுதிகள்|பகுதி|எல்லை|விரிவாக்கம்|கிராமம்|காலனி', w_ta):
                        clean_t = token.strip().lower()
                        if len(clean_t) >= 4 and clean_t not in GENERIC_LOCATION_TERMS:
                            w_kws.add(clean_t)
                if w_en:
                    w_kws.add(w_en.lower().strip())

                self.ward_keywords.append({
                    "entry": ward_record,
                    "keywords": [k for k in w_kws if len(k) >= 4 and k not in GENERIC_LOCATION_TERMS]
                })

        logger.info(
            f"[LOCATION_MATCHER] Synced from database rows: {len(self.taluk_to_division)} taluks, "
            f"{len(self.firka_keywords)} firkas, {len(self.village_keywords)} villages, "
            f"{len(self.all_wards)} wards."
        )
        return len(rows)

    async def load_from_db(self, db: Optional[Any] = None) -> int:
        """
        Asynchronously loads all authoritative location hierarchy directly from PostgreSQL `master_locations`.
        """
        try:
            if db is not None:
                res = await db.execute(text("""
                    SELECT 
                        district_code, district_name_tamil, district_name_en,
                        division_code, division_name_tamil, division_name_en,
                        taluk_code, taluk_name_tamil, taluk_name_en,
                        firka_code, firka_name_tamil, firka_name_en,
                        block_code, block_name_tamil, block_name_en,
                        village_code, village_name_tamil, village_name_en,
                        local_body_type, ward_no, ward_name_tamil, ward_name_en,
                        pincode, search_text, sub_departments
                    FROM master_locations
                    ORDER BY id
                """))
                rows = res.mappings().all()
                return self.sync_from_rows([dict(r) for r in rows])
            else:
                from models.database import AdminAsyncSessionLocal
                async with AdminAsyncSessionLocal() as session:
                    res = await session.execute(text("""
                        SELECT 
                            district_code, district_name_tamil, district_name_en,
                            division_code, division_name_tamil, division_name_en,
                            taluk_code, taluk_name_tamil, taluk_name_en,
                            firka_code, firka_name_tamil, firka_name_en,
                            block_code, block_name_tamil, block_name_en,
                            village_code, village_name_tamil, village_name_en,
                            local_body_type, ward_no, ward_name_tamil, ward_name_en,
                            pincode, search_text, sub_departments
                        FROM master_locations
                        ORDER BY id
                    """))
                    rows = res.mappings().all()
                    return self.sync_from_rows([dict(r) for r in rows])
        except Exception as e:
            logger.warning(f"[LOCATION_MATCHER] Live DB load notice: {e}. Relying on cached/JSON state.")
            return len(self.taluk_keywords)

    def load_hierarchy(self) -> None:
        """Loads administrative locations hierarchy from JSON file if available."""
        if not os.path.exists(self.hierarchy_path):
            return

        try:
            with open(self.hierarchy_path, "r", encoding="utf-8") as f:
                self.hierarchy_data = json.load(f)

            district: Dict[str, Any] = self.hierarchy_data.get("district", {})
            self.district_name_ta = str(district.get("name_ta", "")) or None
            self.district_name_en = str(district.get("name_en", "")) or None

            divisions: List[Dict[str, Any]] = self.hierarchy_data.get("divisions", [])
            for div in divisions:
                div_name_ta: str = str(div.get("division_name_ta", ""))
                div_name_en: str = str(div.get("division_name_en", ""))
                taluks: List[Dict[str, Any]] = div.get("taluks", [])
                for taluk in taluks:
                    t_name_ta: str = str(taluk.get("taluk_name_ta", ""))
                    t_name_en: str = str(taluk.get("taluk_name_en", ""))

                    if t_name_ta:
                        self.taluk_to_division[t_name_ta] = div_name_ta
                        t_kws = [t_name_ta.lower()]
                        if t_name_en:
                            t_kws.append(t_name_en.lower())
                            self.taluk_to_division[t_name_en.lower()] = div_name_ta
                        if div_name_en:
                            self.taluk_to_division_en[t_name_ta] = div_name_en
                            if t_name_en:
                                self.taluk_to_division_en[t_name_en.lower()] = div_name_en

                        self.taluk_keywords.append({
                            "taluk_ta": t_name_ta,
                            "taluk_en": t_name_en,
                            "division_ta": div_name_ta,
                            "division_en": div_name_en,
                            "keywords": t_kws
                        })

                    firkas: List[Dict[str, Any]] = taluk.get("firkas", [])
                    for firka in firkas:
                        f_name_ta: str = str(firka.get("firka_name_ta", ""))
                        f_name_en: str = str(firka.get("firka_name_en", ""))
                        f_kws = [str(k).lower() for k in firka.get("keywords", []) if k]
                        if f_name_ta:
                            f_kws.append(f_name_ta.lower())
                            self.firka_to_taluk[f_name_ta] = t_name_ta
                        if f_name_en:
                            f_kws.append(f_name_en.lower())
                            self.firka_to_taluk[f_name_en.lower()] = t_name_ta

                        clean_f_kws = [k for k in f_kws if k and k not in ["கிழக்கு", "மேற்கு", "வடக்கு", "தெற்கு", "east", "west", "north", "south"]]
                        if not clean_f_kws and f_name_ta:
                            clean_f_kws = [f"{t_name_ta} {f_name_ta}".lower()]

                        self.firka_keywords.append({
                            "firka_ta": f_name_ta,
                            "firka_en": f_name_en,
                            "taluk_ta": t_name_ta,
                            "division_ta": div_name_ta,
                            "keywords": clean_f_kws
                        })

                    # Municipalities & Local Bodies
                    munis: List[Dict[str, Any]] = taluk.get("municipalities", [])
                    for muni in munis:
                        m_name_en: str = str(muni.get("municipality_name_en", ""))
                        m_name_ta: str = str(muni.get("municipality_name_ta", ""))
                        local_body_type = "Corporation" if "மாநகராட்சி" in m_name_ta or "Corporation" in m_name_en else "Municipality"
                        
                        m_keywords = set()
                        if m_name_en:
                            m_keywords.add(m_name_en.lower().strip())
                        if m_name_ta:
                            m_keywords.add(m_name_ta.lower().strip())

                        self.local_body_entries.append({
                            "name_en": m_name_en,
                            "name_ta": m_name_ta,
                            "local_body_type": local_body_type,
                            "firka_ta": None,
                            "taluk_ta": t_name_ta,
                            "division_ta": div_name_ta,
                            "division_en": div_name_en,
                            "keywords": [k for k in m_keywords if len(k) >= 4]
                        })

                        zones = muni.get("zones", [])
                        for z in zones:
                            z_en = z.get("zone_name_en")
                            z_ta = z.get("zone_name_ta")
                            for w in z.get("wards", []):
                                w_name_ta = (w.get("ward_name_ta") or "").strip()
                                w_name_en = (w.get("ward_name_en") or "").strip()
                                w_no = w.get("ward_no")
                                pincode = (w.get("pincode") or "").strip()
                                primary_ward_name = w_name_ta or w_name_en or (f"Ward {w_no}" if w_no is not None else "")

                                ward_record = {
                                    "ward": primary_ward_name,
                                    "ward_name": w_name_ta,
                                    "ward_name_ta": w_name_ta,
                                    "ward_name_en": w_name_en,
                                    "ward_no": w_no,
                                    "pincode": pincode,
                                    "municipality_ward": m_name_en,
                                    "municipality_ward_ta": m_name_ta,
                                    "local_body_type": local_body_type,
                                    "zone": z_en,
                                    "zone_ta": z_ta,
                                    "firka": None,
                                    "firka_en": None,
                                    "taluk": t_name_ta,
                                    "taluk_en": t_name_en,
                                    "revenue_division": div_name_ta,
                                    "revenue_division_en": div_name_en,
                                    "district": self.district_name_ta
                                }
                                self.all_wards.append(ward_record)

                                w_kws = set()
                                if w_name_ta:
                                    w_kws.add(w_name_ta.lower().strip())
                                    for token in re.split(r'[\(\)\[\]\{\}\&/,;]|மற்றும்|மத்தி|பகுதிகள்|பகுதி|எல்லை|விரிவாக்கம்|கிராமம்|காலனி', w_name_ta):
                                        clean_t = token.strip().lower()
                                        if len(clean_t) >= 4 and clean_t not in GENERIC_LOCATION_TERMS:
                                            w_kws.add(clean_t)
                                if w_name_en:
                                    w_kws.add(w_name_en.lower().strip())

                                self.ward_keywords.append({
                                    "entry": ward_record,
                                    "keywords": [k for k in w_kws if len(k) >= 4 and k not in GENERIC_LOCATION_TERMS]
                                })
            logger.info(f"[LOCATION_MATCHER] Loaded from JSON fallback: {len(self.taluk_to_division)} taluks")
        except Exception as e:
            logger.debug(f"[LOCATION_MATCHER] JSON load notice: {e}")

    def resolve_block(
        self,
        taluk: Optional[str],
        firka: Optional[str] = None,
        village: Optional[str] = None
    ) -> Optional[str]:
        """
        Dynamically resolves Development Block from database relationships.
        Zero hardcoded if/elif statements. Fully driven by master_locations.
        """
        if not taluk or taluk in ["-", "Not found", "None", "Unassigned"]:
            return None

        t = taluk.strip()
        f = (firka or "").strip()
        v = (village or "").strip()

        # 1. Check exact village to block mapping from database
        if v and v in self.village_to_block:
            return self.village_to_block[v]

        # 2. Check exact firka to block mapping from database
        if f and f in self.firka_to_block:
            return self.firka_to_block[f]

        # 3. Check taluk to blocks mapping from database
        blocks = self.taluk_to_blocks.get(t) or self.taluk_to_blocks.get(t.lower())
        if blocks:
            if len(blocks) == 1:
                return blocks[0]
            # If multi-block taluk, search for village or firka tokens within block candidate names
            for b in blocks:
                b_clean = re.sub(r'ஒன்றியம்|வட்டார|வட்டம்|Block', '', b).strip()
                if (v and b_clean in v) or (f and b_clean in f):
                    return b
            return blocks[0]

        return None

    def match_hierarchy(
        self,
        address_text: str = "",
        village: Optional[str] = None,
        street: Optional[str] = None,
        detected_taluk: Optional[str] = None
    ) -> Dict[str, Optional[Any]]:
        """
        Dynamically derives District, Revenue Division, Taluk, Firka, Block, Local Body Type,
        Municipality/Corporation, Zone, and Ward using database-derived indexes.
        
        Zero hardcoded fallbacks to Erode. Missing fields return None.
        """
        combined = f"{address_text or ''} {village or ''} {street or ''} {detected_taluk or ''}".lower()

        matched_ward_entry: Optional[Dict[str, Any]] = None

        # 1. Match local body ward by municipality/ward token pattern
        for lb in self.local_body_entries:
            for kw in lb["keywords"]:
                if kw in combined:
                    w_match = re.search(r'(?:வார்டு|ward|w\.no|வார்டு\s*எண்)[\s\.\:\#-]*([0-9]{1,3})', combined)
                    if w_match:
                        w_num = int(w_match.group(1))
                        for w_cand in self.all_wards:
                            if w_cand.get("ward_no") == w_num and w_cand.get("taluk") == lb.get("taluk_ta"):
                                matched_ward_entry = w_cand
                                break

        # 2. Match Ward by locality / ward name keywords
        if not matched_ward_entry:
            best_ward_match = None
            longest_ward_kw_len = 0
            for item in self.ward_keywords:
                for kw in item["keywords"]:
                    if kw in combined and len(kw) > longest_ward_kw_len:
                        longest_ward_kw_len = len(kw)
                        best_ward_match = item["entry"]
            if best_ward_match:
                matched_ward_entry = best_ward_match

        # 3. If Ward matched, return full leaf-to-root hierarchy from ward entry
        if matched_ward_entry:
            w_taluk = matched_ward_entry["taluk"]
            w_firka = matched_ward_entry["firka"]
            w_div = matched_ward_entry.get("revenue_division") or self.taluk_to_division.get(w_taluk)
            return {
                "district": matched_ward_entry["district"] or self.district_name_ta,
                "revenue_division": w_div,
                "taluk": w_taluk,
                "firka": w_firka,
                "block": self.resolve_block(w_taluk, w_firka),
                "village": None,
                "gram_panchayat": None,
                "ward": matched_ward_entry["ward"],
                "ward_no": matched_ward_entry["ward_no"],
                "ward_name": matched_ward_entry["ward_name"],
                "ward_name_en": matched_ward_entry["ward_name_en"],
                "municipality_ward": matched_ward_entry["municipality_ward"],
                "local_body_type": matched_ward_entry["local_body_type"],
                "zone": matched_ward_entry["zone"],
                "pincode": matched_ward_entry["pincode"],
                "boundary_type": "Urban"
            }

        # 4. Check Local Body mentions (Corporation / Municipality)
        matched_lb: Optional[Dict[str, Any]] = None
        longest_lb_len = 0
        for lb in self.local_body_entries:
            for kw in lb["keywords"]:
                if kw in combined and len(kw) > longest_lb_len:
                    longest_lb_len = len(kw)
                    matched_lb = lb

        # 5. Check Database Revenue Villages leaf-to-root match
        best_village_match = None
        longest_village_kw_len = 0
        for v_entry in self.village_keywords:
            for kw in v_entry["keywords"]:
                if kw in combined and len(kw) > longest_village_kw_len:
                    longest_village_kw_len = len(kw)
                    best_village_match = v_entry

        matched_village: Optional[str] = None
        matched_gp: Optional[str] = None
        matched_firka: Optional[str] = None
        matched_taluk: Optional[str] = detected_taluk
        matched_division: Optional[str] = self.taluk_to_division.get(detected_taluk) if detected_taluk else None
        matched_district: Optional[str] = self.district_name_ta

        if best_village_match:
            if not detected_taluk or best_village_match["taluk_ta"] == detected_taluk:
                matched_village = best_village_match["village_name"]
                matched_gp = best_village_match["gram_panchayat"]
                matched_firka = best_village_match["firka_ta"]
                matched_taluk = best_village_match["taluk_ta"]
                matched_division = best_village_match["division_ta"]
                if best_village_match.get("district_ta"):
                    matched_district = best_village_match["district_ta"]

        # 6. Firka keyword matching dynamically from database firkas
        if not matched_firka:
            best_firka_match = None
            longest_firka_kw_len = 0
            firka_pool = [f for f in self.firka_keywords if f.get("taluk_ta") == detected_taluk] if detected_taluk else self.firka_keywords
            
            specific_firkas = [f for f in firka_pool if f.get("firka_ta") != detected_taluk]
            taluk_firkas = [f for f in firka_pool if f.get("firka_ta") == detected_taluk]

            for f_entry in specific_firkas:
                for kw in f_entry["keywords"]:
                    if kw in combined and len(kw) > longest_firka_kw_len:
                        # Street pattern guardrail to avoid mapping "கிழக்கு தெரு" as "ஈரோடு கிழக்கு"
                        street_pattern = rf'{re.escape(kw)}\s*(?:தெரு|வீதி|சாலை|ரோடு|நகர்|சந்து|லேன்|காலனி|street|road|lane|nagar|colony)'
                        if re.search(street_pattern, combined):
                            continue
                        longest_firka_kw_len = len(kw)
                        best_firka_match = f_entry

            if best_firka_match:
                matched_firka = best_firka_match["firka_ta"]
                if not matched_taluk:
                    matched_taluk = best_firka_match["taluk_ta"]
                if not matched_division:
                    matched_division = best_firka_match["division_ta"]
            elif taluk_firkas and detected_taluk:
                matched_firka = taluk_firkas[0]["firka_ta"]
            elif detected_taluk:
                matched_firka = detected_taluk

        # 7. Taluk keyword matching dynamically from database taluks
        if not matched_taluk:
            for t_entry in self.taluk_keywords:
                for kw in t_entry["keywords"]:
                    if kw in combined:
                        # Street name guardrail (e.g. 'ஈரோடு ரோடு')
                        kw_esc = re.escape(kw)
                        street_pat = re.compile(rf'{kw_esc}\s*(?:ரோடு|சாலை|தெரு|வீதி|road|street)', re.IGNORECASE)
                        all_matches = list(re.finditer(kw_esc, combined, re.IGNORECASE))
                        st_matches = list(street_pat.finditer(combined))
                        if len(all_matches) > 0 and len(all_matches) == len(st_matches):
                            continue
                        matched_taluk = t_entry["taluk_ta"]
                        matched_division = t_entry["division_ta"]
                        break
                if matched_taluk:
                    break

        if matched_taluk and not matched_division:
            matched_division = self.taluk_to_division.get(matched_taluk) or self.taluk_to_division.get(matched_taluk.lower())

        # Determine Local Body Type and Municipality Ward
        if matched_lb:
            local_body_type = matched_lb["local_body_type"]
            muni_ward = matched_lb["name_en"]
            boundary_type = "Urban" if any(x in local_body_type for x in ["Corporation", "Municipality"]) else "Rural"
            if not matched_firka:
                matched_firka = matched_lb["firka_ta"]
            if not matched_taluk:
                matched_taluk = matched_lb["taluk_ta"]
            if not matched_division:
                matched_division = matched_lb["division_ta"]
        elif best_village_match:
            boundary_type = best_village_match["category"]
            muni_ward = None
            if boundary_type == "Rural" and matched_gp and matched_gp != "Not applicable":
                local_body_type = f"Gram Panchayat ({matched_gp})"
            else:
                local_body_type = f"{boundary_type} Local Area"
        else:
            local_body_type = "Village Panchayat" if matched_taluk else None
            muni_ward = None
            boundary_type = "Rural" if matched_taluk else None

        matched_block = self.resolve_block(matched_taluk, matched_firka, matched_village)

        return {
            "district": matched_district if (matched_taluk or matched_village or matched_lb) else None,
            "revenue_division": matched_division,
            "taluk": matched_taluk,
            "firka": matched_firka,
            "block": matched_block,
            "village": matched_village,
            "gram_panchayat": matched_gp,
            "ward": None,
            "ward_no": None,
            "ward_name": None,
            "ward_name_en": "Not Applicable (Rural Panchayat Area)" if boundary_type == "Rural" else None,
            "municipality_ward": muni_ward,
            "local_body_type": local_body_type,
            "zone": None,
            "pincode": None,
            "boundary_type": boundary_type
        }


location_matcher = ErodeLocationHierarchyMatcher()
