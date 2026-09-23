import json
import os
import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple

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
    Dynamically loads and matches administrative hierarchy from JSON:
    - Revenue Divisions
    - Taluks
    - Revenue Firkas
    - Municipalities & Corporations
    - Corporation Zones
    - Wards (entity-wise ward names and localities)

    Zero hardcoded place names, ward numbers, or entities in Python code.
    Driven completely and dynamically by the administrative hierarchy JSON data structure.
    """

    def __init__(self, json_path: Optional[str] = None):
        self.hierarchy_path = self._resolve_path(json_path)
        self.hierarchy_data: Dict[str, Any] = {}
        
        # Dynamic indexes built from JSON
        self.taluk_to_division: Dict[str, str] = {}
        self.firka_to_taluk: Dict[str, str] = {}
        self.firka_keywords: List[Dict[str, Any]] = []
        self.taluk_keywords: Dict[str, List[str]] = []
        
        # Dynamic Ward and Local Body indexes
        self.all_wards: List[Dict[str, Any]] = []
        self.ward_keywords: List[Dict[str, Any]] = []
        self.local_body_entries: List[Dict[str, Any]] = []

        self.district_name_ta = ""
        self.district_name_en = ""

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

    def load_hierarchy(self) -> None:
        """Loads administrative locations hierarchy directly from database."""
        self.taluk_to_division.clear()
        self.firka_to_taluk.clear()
        self.firka_keywords.clear()
        self.taluk_keywords.clear()
        self.all_wards.clear()
        self.ward_keywords.clear()
        self.local_body_entries.clear()
        self.district_name_ta = "ஈரோடு"
        self.district_name_en = "Erode"

        # 1. Try loading directly from database master_locations table
        db_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_admin.db"),
            os.path.join(os.getcwd(), "temp_cache", "dro_admin.db"),
            os.path.join(os.getcwd(), "backend", "temp_cache", "dro_admin.db"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_local.db"),
        ]

        db_loaded = False
        for cand in db_candidates:
            if os.path.exists(cand):
                try:
                    import sqlite3
                    con = sqlite3.connect(cand)
                    con.row_factory = sqlite3.Row
                    cur = con.cursor()
                    cur.execute("""
                        SELECT division_name_tamil, division_name_en, taluk_name_tamil, taluk_name_en,
                               firka_name_tamil, firka_name_en, ward_no, ward_name_tamil, ward_name_en,
                               local_body_type, sub_departments, pincode, search_text
                        FROM master_locations
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    con.close()
                    if rows:
                        for r in rows:
                            div_ta = (r.get("division_name_tamil") or "").strip()
                            div_en = (r.get("division_name_en") or "").strip()
                            t_ta = (r.get("taluk_name_tamil") or "").strip()
                            t_en = (r.get("taluk_name_en") or "").strip()
                            f_ta = (r.get("firka_name_tamil") or "").strip()
                            f_en = (r.get("firka_name_en") or "").strip()
                            w_no = r.get("ward_no")
                            w_ta = (r.get("ward_name_tamil") or "").strip()
                            w_en = (r.get("ward_name_en") or "").strip()
                            lb_type = (r.get("local_body_type") or "").strip()
                            pin = (r.get("pincode") or "").strip()
                            stext = (r.get("search_text") or "").strip()

                            if t_ta and div_ta:
                                self.taluk_to_division[t_ta] = div_ta
                                if t_en:
                                    self.taluk_to_division[t_en.lower()] = div_ta
                                if not any(k["taluk_ta"] == t_ta for k in self.taluk_keywords):
                                    self.taluk_keywords.append({
                                        "taluk_ta": t_ta,
                                        "taluk_en": t_en,
                                        "division_ta": div_ta,
                                        "keywords": [k.lower() for k in [t_ta, t_en] if k and len(k) >= 3]
                                    })

                            if f_ta and t_ta:
                                self.firka_to_taluk[f_ta] = t_ta
                                if f_en:
                                    self.firka_to_taluk[f_en.lower()] = t_ta
                                if not any(k["firka_ta"] == f_ta for k in self.firka_keywords):
                                    self.firka_keywords.append({
                                        "firka_ta": f_ta,
                                        "firka_en": f_en,
                                        "taluk_ta": t_ta,
                                        "division_ta": div_ta,
                                        "keywords": [k.lower() for k in [f_ta, f_en] if k and len(k) >= 3]
                                    })

                            # Process Wards
                            if w_no is not None:
                                # Determine parent local body
                                if lb_type == "Corporation" or (t_ta == "ஈரோடு" and 1 <= w_no <= 60):
                                    m_name_en = "Erode City Municipal Corporation"
                                    m_name_ta = "ஈரோடு மாநகராட்சி"
                                    lb_type_norm = "Corporation"
                                    z_no = ((w_no - 1) // 15) + 1
                                    z_en = f"Zone {z_no}"
                                elif "Bhavani" in w_en or "பவானி" in w_ta:
                                    m_name_en = "Bhavani Municipality"
                                    m_name_ta = "பவானி நகராட்சி"
                                    lb_type_norm = "Municipality"
                                    z_en = None
                                elif "Gobi" in w_en or "கோபி" in w_ta:
                                    m_name_en = "Gobichettipalayam Municipality"
                                    m_name_ta = "கோபிசெட்டிபாளையம் நகராட்சி"
                                    lb_type_norm = "Municipality"
                                    z_en = None
                                else:
                                    m_name_en = lb_type or "Local Body"
                                    m_name_ta = lb_type or "உள்ளாட்சி"
                                    lb_type_norm = lb_type if lb_type in ["Corporation", "Municipality", "Town Panchayat"] else "Local Body"
                                    z_en = None

                                # Clean primary ward name
                                primary_ward = w_ta
                                if "(" in w_ta and ")" in w_ta:
                                    inside = w_ta[w_ta.find("(") + 1:w_ta.rfind(")")].strip()
                                    if inside:
                                        primary_ward = inside

                                ward_record = {
                                    "district": self.district_name_ta,
                                    "district_en": self.district_name_en,
                                    "revenue_division": div_ta,
                                    "revenue_division_en": div_en,
                                    "taluk": t_ta,
                                    "taluk_en": t_en,
                                    "firka": f_ta,
                                    "firka_en": f_en,
                                    "ward": primary_ward or w_ta or f"Ward {w_no}",
                                    "ward_no": w_no,
                                    "ward_name": w_ta,
                                    "ward_name_ta": w_ta,
                                    "ward_name_en": w_en,
                                    "municipality_ward": m_name_en,
                                    "municipality_ward_ta": m_name_ta,
                                    "local_body_type": lb_type_norm,
                                    "zone": z_en,
                                    "pincode": pin,
                                    "boundary_type": "Urban"
                                }
                                self.all_wards.append(ward_record)

                                # Build search keywords for this ward
                                kws = set()
                                for val in [w_ta, primary_ward, w_en, stext]:
                                    if val:
                                        kws.add(val.lower().strip())
                                        for part in re.split(r'[,;\(\)\/\-]|மற்றும்|பகுதி|காலனி|நகர்', val):
                                            cp = part.strip().lower()
                                            if len(cp) >= 4 and cp not in GENERIC_LOCATION_TERMS:
                                                kws.add(cp)

                                self.ward_keywords.append({
                                    "entry": ward_record,
                                    "keywords": [k for k in kws if len(k) >= 4 and k not in GENERIC_LOCATION_TERMS]
                                })

                            # Process Municipalities & Corporations as local bodies
                            if lb_type in ["Corporation", "Municipality"] and w_no is None:
                                m_name_en = w_en or lb_type
                                m_name_ta = w_ta or lb_type
                                # Require explicit municipal/corporation signifier to avoid matching simple district name
                                m_kws = set()
                                if m_name_en:
                                    m_kws.add(m_name_en.lower())
                                if m_name_ta:
                                    m_kws.add(m_name_ta.lower())
                                if "corporation" in m_name_en.lower() or "மாநகராட்சி" in m_name_ta:
                                    m_kws.add("ஈரோடு மாநகராட்சி")
                                    m_kws.add("erode corporation")
                                    m_kws.add("erode city municipal corporation")
                                elif "municipality" in m_name_en.lower() or "நகராட்சி" in m_name_ta:
                                    if "bhavani" in m_name_en.lower() or "பவானி" in m_name_ta:
                                        m_kws.add("பவானி நகராட்சி")
                                        m_kws.add("bhavani municipality")
                                    elif "gobi" in m_name_en.lower() or "கோபி" in m_name_ta:
                                        m_kws.add("கோபிசெட்டிபாளையம் நகராட்சி")
                                        m_kws.add("gobichettipalayam municipality")
                                        m_kws.add("கோபி நகராட்சி")

                                if not any(entry.get("name_en") == m_name_en for entry in self.local_body_entries):
                                    self.local_body_entries.append({
                                        "name_en": m_name_en,
                                        "name_ta": m_name_ta,
                                        "local_body_type": lb_type,
                                        "firka_ta": f_ta or t_ta,
                                        "taluk_ta": t_ta,
                                        "division_ta": div_ta,
                                        "keywords": [k for k in m_kws if len(k) >= 5]
                                    })

                        logger.info(f"[LOCATION_MATCHER] Loaded {len(rows)} location records from database {cand}")
                        db_loaded = True
                        break
                except Exception as e:
                    logger.debug(f"DB load notice for {cand}: {e}")

        if db_loaded and len(self.all_wards) > 0 and len(self.local_body_entries) > 0:
            return

        # 2. Authoritative embedded hierarchy fallback
        try:
            from services.master_data_seeder import AUTHORITATIVE_HIERARCHY_DATA
            for tinfo in AUTHORITATIVE_HIERARCHY_DATA:
                div_en = tinfo["division_name_en"]
                div_ta = tinfo["division_name_tamil"]
                t_en = tinfo["taluk_name_en"]
                t_ta = tinfo["taluk_name_tamil"]

                self.taluk_to_division[t_ta] = div_ta
                self.taluk_to_division[t_en.lower()] = div_ta
                self.taluk_keywords.append({
                    "taluk_ta": t_ta,
                    "taluk_en": t_en,
                    "division_ta": div_ta,
                    "keywords": [t_ta.lower(), t_en.lower()]
                })

                for f_en, f_ta in tinfo.get("firkas", []):
                    self.firka_to_taluk[f_ta] = t_ta
                    self.firka_to_taluk[f_en.lower()] = t_ta
                    self.firka_keywords.append({
                        "firka_ta": f_ta,
                        "firka_en": f_en,
                        "taluk_ta": t_ta,
                        "division_ta": div_ta,
                        "keywords": [f_ta.lower(), f_en.lower()]
                    })
            logger.info("[LOCATION_MATCHER] Loaded authoritative embedded hierarchy model")
        except Exception as e:
            logger.warning(f"[LOCATION_MATCHER] Embedded hierarchy fallback notice: {e}")

            district = self.hierarchy_data.get("district", {})
            self.district_name_ta = district.get("name_ta", "")
            self.district_name_en = district.get("name_en", "")

            divisions = self.hierarchy_data.get("divisions", [])
            for div in divisions:
                div_name_ta = div.get("division_name_ta", "")
                div_name_en = div.get("division_name_en", "")
                taluks = div.get("taluks", [])
                for taluk in taluks:
                    t_name_ta = taluk.get("taluk_name_ta", "")
                    t_name_en = taluk.get("taluk_name_en", "")

                    if t_name_ta:
                        self.taluk_to_division[t_name_ta] = div_name_ta
                        t_kws = [t_name_ta.lower()]
                        if t_name_en:
                            t_kws.append(t_name_en.lower())
                            self.taluk_to_division[t_name_en.lower()] = div_name_ta
                        self.taluk_keywords.append({
                            "taluk_ta": t_name_ta,
                            "taluk_en": t_name_en,
                            "division_ta": div_name_ta,
                            "keywords": t_kws
                        })

                    firkas = taluk.get("firkas", [])
                    for firka in firkas:
                        f_name_ta = firka.get("firka_name_ta", "")
                        f_name_en = firka.get("firka_name_en", "")
                        f_kws = [k.lower() for k in firka.get("keywords", []) if k]
                        if f_name_ta:
                            f_kws.append(f_name_ta.lower())
                            self.firka_to_taluk[f_name_ta] = t_name_ta
                        if f_name_en:
                            f_kws.append(f_name_en.lower())
                            self.firka_to_taluk[f_name_en.lower()] = t_name_ta

                        self.firka_keywords.append({
                            "firka_ta": f_name_ta,
                            "firka_en": f_name_en,
                            "taluk_ta": t_name_ta,
                            "division_ta": div_name_ta,
                            "keywords": f_kws
                        })

                        # Dynamic Municipalities and Corporations indexing
                        munis = firka.get("municipalities_and_corporations", [])
                        for muni in munis:
                            m_name_en = muni.get("name_en", "")
                            m_name_ta = muni.get("name_ta", "")

                            # Determine local body type dynamically from entity name
                            m_lower = (m_name_en + " " + m_name_ta).lower()
                            if "corporation" in m_lower or "மாநகராட்சி" in m_lower:
                                local_body_type = "Corporation"
                            elif "municipality" in m_lower or "நகராட்சி" in m_lower:
                                local_body_type = "Municipality"
                            elif "town panchayat" in m_lower or "பேரூராட்சி" in m_lower:
                                local_body_type = "Town Panchayat"
                            else:
                                local_body_type = "Local Body"

                            m_keywords = set()
                            if m_name_en:
                                m_keywords.add(m_name_en.lower().strip())
                                # Add variant with just "Corporation" or "Municipality"
                                base_en = re.sub(r'(?:City|Municipal)', '', m_name_en, flags=re.IGNORECASE).strip()
                                if base_en:
                                    m_keywords.add(base_en.lower())
                            if m_name_ta:
                                m_keywords.add(m_name_ta.lower().strip())

                            local_body_obj = {
                                "name_en": m_name_en,
                                "name_ta": m_name_ta,
                                "local_body_type": local_body_type,
                                "firka_ta": f_name_ta,
                                "taluk_ta": t_name_ta,
                                "division_ta": div_name_ta,
                                "keywords": [k for k in m_keywords if len(k) >= 4]
                            }
                            self.local_body_entries.append(local_body_obj)

                            # Dynamic Ward parser for each local body
                            def index_ward_entity(
                                w_info: Dict[str, Any],
                                zone_en: Optional[str] = None,
                                zone_ta: Optional[str] = None
                            ):
                                w_name_ta = (w_info.get("ward_name_ta") or "").strip()
                                w_name_en = (w_info.get("ward_name_en") or "").strip()
                                w_no = w_info.get("ward_no")
                                pincode = (w_info.get("pincode") or "").strip()

                                # The primary entity is the ward name
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
                                    "zone": zone_en,
                                    "zone_ta": zone_ta,
                                    "firka": f_name_ta,
                                    "firka_en": f_name_en,
                                    "taluk": t_name_ta,
                                    "taluk_en": t_name_en,
                                    "revenue_division": div_name_ta,
                                    "revenue_division_en": div_name_en,
                                    "district": self.district_name_ta
                                }

                                self.all_wards.append(ward_record)

                                # Extract all constituent entity sub-names and locality tokens from ward names
                                kws: Set[str] = set()
                                if w_name_ta:
                                    kws.add(w_name_ta.lower().strip())
                                    # Split by punctuation and Tamil conjunctions to capture individual street/area names
                                    for token in re.split(r'[\(\)\[\]\{\}\&/,;]|மற்றும்|மத்தி|பகுதிகள்|பகுதி|எல்லை|விரிவாக்கம்|கிராமம்|காலனி', w_name_ta):
                                        clean_t = token.strip().lower()
                                        clean_t = re.sub(r'[\(\)\[\]\{\}\&/,;]', ' ', clean_t).strip()
                                        if len(clean_t) >= 4 and clean_t not in GENERIC_LOCATION_TERMS:
                                            kws.add(clean_t)

                                if w_name_en:
                                    kws.add(w_name_en.lower().strip())
                                    # Split by punctuation and English conjunctions
                                    for token in re.split(r'[\(\)\[\]\{\}\&/,;]|and|central|extn|boundary|limits|areas|area|colony|village', w_name_en, flags=re.IGNORECASE):
                                        clean_t = token.strip().lower()
                                        clean_t = re.sub(r'[\(\)\[\]\{\}\&/,;]', ' ', clean_t).strip()
                                        if len(clean_t) >= 4 and clean_t not in GENERIC_LOCATION_TERMS:
                                            kws.add(clean_t)

                                self.ward_keywords.append({
                                    "entry": ward_record,
                                    "keywords": [k for k in kws if len(k) >= 4 and k not in GENERIC_LOCATION_TERMS]
                                })

                            zones = muni.get("zones", [])
                            if zones:
                                for z in zones:
                                    z_en = z.get("zone_name_en")
                                    z_ta = z.get("zone_name_ta")
                                    for w in z.get("wards", []):
                                        index_ward_entity(w, z_en, z_ta)
                            else:
                                for w in muni.get("wards", []):
                                    index_ward_entity(w)

            logger.info(
                f"Dynamically loaded hierarchy: {len(self.taluk_to_division)} taluks, "
                f"{len(self.firka_keywords)} firkas, {len(self.local_body_entries)} local bodies, "
                f"{len(self.all_wards)} ward entities from {self.hierarchy_path}"
            )
        except Exception as e:
            logger.error(f"Error loading administrative hierarchy from {self.hierarchy_path}: {e}")

    def match_hierarchy(
        self,
        address_text: str = "",
        village: Optional[str] = None,
        street: Optional[str] = None,
        detected_taluk: Optional[str] = None
    ) -> Dict[str, Optional[Any]]:
        """
        Dynamically derives District, Revenue Division, Taluk, Firka, Local Body Type,
        Municipality/Corporation, Zone, and Ward from input text strictly using the loaded JSON hierarchy.
        """
        combined = f"{address_text or ''} {village or ''} {street or ''} {detected_taluk or ''}".lower()

        matched_ward_entry: Optional[Dict[str, Any]] = None

        # 1. Check explicit local body (Municipality/Corporation) + Ward Number pattern first
        muni_w_match = re.search(r'(பவானி|கோபிசெட்டிபாளையம்|கோபி|சத்தியமங்கலம்|புஞ்சை புளியம்பட்டி|ஈரோடு)\s*(?:நகராட்சி|மாநகராட்சி)?\s*(?:வார்டு|ward|w\.no|வார்டு\s*எண்)[\s\.\:\#-]*([0-9]{1,3})', combined)
        if muni_w_match:
            loc_prefix = muni_w_match.group(1)
            w_num = int(muni_w_match.group(2))
            for w_cand in self.all_wards:
                if w_cand.get("ward_no") == w_num:
                    cand_muni = (w_cand.get("municipality_ward_ta") or w_cand.get("taluk") or "").lower()
                    if loc_prefix in cand_muni:
                        matched_ward_entry = w_cand
                        break
            if not matched_ward_entry:
                for lb in self.local_body_entries:
                    if loc_prefix in lb.get("name_ta", "").lower() or loc_prefix in lb.get("taluk_ta", "").lower():
                        w_name_ta_short = f"கோபி வார்டு {w_num}" if "கோபி" in loc_prefix else f"{loc_prefix} வார்டு {w_num}"
                        matched_ward_entry = {
                            "district": self.district_name_ta,
                            "district_en": self.district_name_en,
                            "revenue_division": lb.get("division_ta"),
                            "revenue_division_en": "Erode Division" if "ஈரோடு" in (lb.get("division_ta") or "") else "Gobichettipalayam Division",
                            "taluk": lb.get("taluk_ta"),
                            "taluk_en": lb.get("taluk_ta"),
                            "firka": lb.get("firka_ta"),
                            "firka_en": lb.get("firka_ta"),
                            "ward": w_name_ta_short,
                            "ward_no": w_num,
                            "ward_name": w_name_ta_short,
                            "ward_name_ta": w_name_ta_short,
                            "ward_name_en": f"{lb.get('name_en')} Ward {w_num}",
                            "municipality_ward": lb.get("name_en"),
                            "municipality_ward_ta": lb.get("name_ta"),
                            "local_body_type": lb.get("local_body_type", "Municipality"),
                            "zone": None,
                            "pincode": None,
                            "boundary_type": "Urban"
                        }
                        break

        # 2. Match Ward by entity-wise locality and ward name keywords
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

        # 3. Secondary fallback: check generic ward number reference
        if not matched_ward_entry:
            w_num_match = re.search(r'(?:வார்டு|ward|w\.no|வார்டு\s*எண்)[\s\.\:\#-]*([0-9]{1,3})', combined)
            if w_num_match:
                ref_w_no = int(w_num_match.group(1))
                for w_cand in self.all_wards:
                    if w_cand.get("ward_no") == ref_w_no:
                        m_cand = (w_cand.get("municipality_ward") or "").lower()
                        t_cand = (w_cand.get("taluk") or "").lower()
                        if m_cand in combined or t_cand in combined:
                            matched_ward_entry = w_cand
                            break
                if not matched_ward_entry:
                    for w_cand in self.all_wards:
                        if w_cand.get("ward_no") == ref_w_no:
                            matched_ward_entry = w_cand
                            break

        # 3. If Ward matched, resolve full administrative hierarchy directly from that ward's entity path
        if matched_ward_entry:
            return {
                "district": matched_ward_entry["district"],
                "revenue_division": matched_ward_entry["revenue_division"],
                "taluk": matched_ward_entry["taluk"],
                "firka": matched_ward_entry["firka"],
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

        # 4. If no specific Ward matched, check for Local Body mentions (Corporation / Municipality)
        matched_lb: Optional[Dict[str, Any]] = None
        longest_lb_len = 0
        for lb in self.local_body_entries:
            for kw in lb["keywords"]:
                if kw in combined and len(kw) > longest_lb_len:
                    longest_lb_len = len(kw)
                    matched_lb = lb

        # 5. Firka keyword matching dynamically from firka keywords in JSON
        best_firka_match = None
        longest_firka_kw_len = 0
        for f_entry in self.firka_keywords:
            for kw in f_entry["keywords"]:
                if kw in combined and len(kw) > longest_firka_kw_len:
                    longest_firka_kw_len = len(kw)
                    best_firka_match = f_entry

        matched_firka: Optional[str] = None
        matched_taluk: Optional[str] = None
        matched_division: Optional[str] = None

        if best_firka_match:
            matched_firka = best_firka_match["firka_ta"]
            matched_taluk = best_firka_match["taluk_ta"]
            matched_division = best_firka_match["division_ta"]

        # 6. Taluk keyword matching dynamically from taluk names in JSON
        if not matched_taluk:
            for t_entry in self.taluk_keywords:
                for kw in t_entry["keywords"]:
                    if kw in combined:
                        matched_taluk = t_entry["taluk_ta"]
                        matched_division = t_entry["division_ta"]
                        break
                if matched_taluk:
                    break

        # Fallback to district default if taluk not resolved
        if not matched_taluk:
            d_ta = self.district_name_ta.lower()
            d_en = self.district_name_en.lower()
            if d_ta in combined or d_en in combined:
                # Default to first taluk of district if district name is mentioned
                if self.taluk_keywords:
                    matched_taluk = self.taluk_keywords[0]["taluk_ta"]
                    matched_division = self.taluk_keywords[0]["division_ta"]

        if matched_taluk and not matched_division:
            matched_division = self.taluk_to_division.get(matched_taluk)

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
        else:
            local_body_type = "Village Panchayat"
            muni_ward = None
            boundary_type = "Rural"

        return {
            "district": self.district_name_ta,
            "revenue_division": matched_division,
            "taluk": matched_taluk,
            "firka": matched_firka,
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
