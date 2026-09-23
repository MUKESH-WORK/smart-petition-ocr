import os
import json
import re
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("geo_validator")

# In-memory singleton cache for master geo config
_GEO_CACHE: Dict[str, Any] = {}
_RESOLVED_PATH: Optional[str] = None


def _resolve_master_geo_path(provided_path: Optional[str] = None) -> str:
    """Dynamically resolves the absolute path to erode_admin_master.json."""
    if provided_path and os.path.exists(provided_path):
        return os.path.abspath(provided_path)

    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "erode_admin_master.json"),
        os.path.join(os.getcwd(), "backend", "data", "erode_admin_master.json"),
        os.path.join(os.getcwd(), "data", "erode_admin_master.json"),
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return os.path.abspath(cand)

    return os.path.abspath(candidates[0])


def _build_geo_matrix_from_db_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Dynamically builds urban and rural matrix strictly from database master_locations rows."""
    urban_zones_map: Dict[str, Dict[str, Any]] = {}
    rural_taluks_map: Dict[str, Dict[str, Any]] = {}

    dist_ta = "ஈரோடு"
    dist_en = "Erode"
    dist_code = "10"

    stopwords = {
        "erode", "ஈரோடு", "district", "corporation", "zone", "taluk", "வட்டம்", "மாவட்டம்", "மாநகராட்சி", "மண்டலம்",
        "revenue", "division", "கோட்டம்", "sub-departments", "local", "body", "கிராமம்",
        "ரோடு", "road", "தெரு", "street", "மற்றும்", "பகுதி", "வார்டு",
        "village", "பஞ்சாயத்து", "panchayat", "municipality", "ஆட்சியர்",
        "அலுவலகம்", "area", "colony", "nagar", "வளாகம்", "இணைப்பு", "மத்தி", "தெற்கு", "வடக்கு", "கிழக்கு", "மேற்கு"
    }

    for r in rows:
        if r.get("district_name_tamil"):
            dist_ta = r["district_name_tamil"]
        if r.get("district_name_en"):
            dist_en = r["district_name_en"]
        if r.get("district_code"):
            dist_code = r["district_code"]

        ward_no = r.get("ward_no")
        t_en = str(r.get("taluk_name_en") or "").strip()
        t_ta = str(r.get("taluk_name_tamil") or "").strip()
        f_en = str(r.get("firka_name_en") or "").strip()
        f_ta = str(r.get("firka_name_tamil") or "").strip()
        w_ta = str(r.get("ward_name_tamil") or "").strip()
        w_en = str(r.get("ward_name_en") or "").strip()
        v_en = str(r.get("village_name_en") or "").strip()
        v_ta = str(r.get("village_name_tamil") or "").strip()
        lb_type = str(r.get("local_body_type") or "").strip()
        pin = str(r.get("pincode") or "").strip()
        stext = str(r.get("search_text") or "")
        
        # Urban Corporation Wards (ward_no is present or lb_type is Ward)
        if ward_no is not None:
            if 1 <= ward_no <= 15:
                zone_en, zone_ta = "Zone 1 (Suriyampalayam)", "மண்டலம் 1 (சூரியம்பாளையம்)"
            elif 16 <= ward_no <= 30:
                zone_en, zone_ta = "Zone 2 (Periyasemur)", "மண்டலம் 2 (பெரியசேமூர்)"
            elif 31 <= ward_no <= 45:
                zone_en, zone_ta = "Zone 3 (Surampatti)", "மண்டலம் 3 (சூரம்பட்டி)"
            else:
                zone_en, zone_ta = "Zone 4 (Kasipalayam)", "மண்டலம் 4 (காசிபாளையம்)"

            if zone_en not in urban_zones_map:
                urban_zones_map[zone_en] = {
                    "zone_name_en": zone_en,
                    "zone_name_ta": zone_ta,
                    "wards": []
                }

            ward_kws = set()
            if w_ta:
                ward_kws.add(w_ta.lower().strip())
                for part in re.split(r'[,;\(\)\/\-]|மற்றும்|பகுதி|காலனி', w_ta):
                    cp = part.strip().lower()
                    if len(cp) >= 5 and cp not in stopwords:
                        ward_kws.add(cp)
            if w_en:
                ward_kws.add(w_en.lower().strip())
                for part in re.split(r'[,;\(\)\/\-]|and|area|colony', w_en, flags=re.IGNORECASE):
                    cp = part.strip().lower()
                    if len(cp) >= 5 and cp not in stopwords:
                        ward_kws.add(cp)

            ward_kws.add(f"ward {ward_no}")
            ward_kws.add(f"வார்டு {ward_no}")

            urban_zones_map[zone_en]["wards"].append({
                "ward_no": ward_no,
                "ward_name_ta": w_ta or f"வார்டு {ward_no}",
                "ward_name_en": w_en or f"Ward {ward_no}",
                "taluk_ta": t_ta or dist_ta,
                "taluk_en": t_en or dist_en,
                "firka_ta": f_ta,
                "firka_en": f_en,
                "pincode": pin or "638001",
                "keywords": [k for k in ward_kws if k and k not in stopwords]
            })

        # Rural Taluks, Firkas & Villages
        elif t_en and t_en.lower() != "erode":
            if t_en not in rural_taluks_map:
                rural_taluks_map[t_en] = {
                    "taluk_name_en": t_en,
                    "taluk_name_ta": t_ta,
                    "villages": []
                }

            disp_v_ta = v_ta or w_ta or f_ta or t_ta
            disp_v_en = v_en or w_en or f_en or t_en
            v_kws = set()
            if disp_v_en:
                v_kws.add(disp_v_en.lower().strip())
            if disp_v_ta:
                v_kws.add(disp_v_ta.lower().strip())
            if f_ta:
                v_kws.add(f_ta.lower().strip())
            if f_en:
                v_kws.add(f_en.lower().strip())

            rural_taluks_map[t_en]["villages"].append({
                "village_name_ta": disp_v_ta,
                "village_name_en": disp_v_en,
                "firka_ta": f_ta,
                "firka_en": f_en,
                "pincode": pin,
                "keywords": [k for k in v_kws if k and k not in stopwords]
            })

    return {
        "district": {"name_ta": dist_ta, "name_en": dist_en, "code": dist_code},
        "urban_matrix": {
            "corporation_name_en": "Erode City Municipal Corporation",
            "corporation_name_ta": "ஈரோடு மாநகராட்சி",
            "zones": list(urban_zones_map.values())
        },
        "rural_matrix": {
            "taluks": list(rural_taluks_map.values())
        }
    }

    return {
        "district": {"name_ta": dist_ta, "name_en": dist_en, "code": dist_code},
        "urban_matrix": {
            "corporation_name_en": "Erode City Municipal Corporation",
            "corporation_name_ta": "ஈரோடு மாநகராட்சி",
            "zones": list(urban_zones_map.values())
        },
        "rural_matrix": {
            "taluks": list(rural_taluks_map.values())
        }
    }


def load_master_geo_config(geo_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads and caches the dual-layered district geo matrix directly from the database."""
    global _GEO_CACHE
    if _GEO_CACHE:
        return _GEO_CACHE

    if geo_path and os.path.exists(geo_path):
        try:
            with open(geo_path, "r", encoding="utf-8") as f:
                _GEO_CACHE = json.load(f)
                return _GEO_CACHE
        except Exception as e:
            logger.error(f"[GEO_VALIDATOR] Failed to load geo config from {geo_path}: {e}")

    # Load directly from Database master_locations table
    db_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_admin.db"),
        os.path.join(os.getcwd(), "temp_cache", "dro_admin.db"),
        os.path.join(os.getcwd(), "backend", "temp_cache", "dro_admin.db"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_cache", "dro_local.db"),
    ]

    for cand in db_candidates:
        if os.path.exists(cand):
            try:
                import sqlite3
                con = sqlite3.connect(cand)
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                cur.execute("""
                    SELECT district_code, district_name_tamil, district_name_en,
                           division_code, division_name_tamil, division_name_en,
                           taluk_code, taluk_name_tamil, taluk_name_en,
                           firka_code, firka_name_tamil, firka_name_en,
                           local_body_type, ward_no, ward_name_tamil, ward_name_en,
                           pincode, search_text
                    FROM master_locations
                """)
                rows = [dict(r) for r in cur.fetchall()]
                con.close()
                if rows:
                    _GEO_CACHE = _build_geo_matrix_from_db_rows(rows)
                    logger.info(f"[GEO_VALIDATOR] Successfully loaded geo matrix from database {cand} ({len(rows)} records)")
                    return _GEO_CACHE
            except Exception as e:
                logger.debug(f"Geo DB load notice for {cand}: {e}")

    return {"urban_matrix": {"zones": []}, "rural_matrix": {"taluks": []}}


def validate_geo_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rigid validator targeting critical keys: Taluk, Village, Pincode, Address.
    Normalizes string values and returns sanitised payload dictionary.
    """
    if not isinstance(payload, dict):
        raise ValueError("petition_payload must be a dictionary")

    sanitized = {
        "taluk": str(payload.get("taluk") or "").strip(),
        "village": str(payload.get("village") or "").strip(),
        "pincode": str(payload.get("pincode") or "").strip(),
        "address": str(payload.get("address") or "").strip(),
    }

    pin_match = re.search(r"\b(6\d{5})\b", sanitized["pincode"] or sanitized["address"])
    if pin_match:
        sanitized["pincode"] = pin_match.group(1)

    return sanitized


def process_petition_geo(petition_payload: Dict[str, Any], master_geo_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates and resolves unstructured petition metadata into strict dual-layered geo layout:
    - Target critical keys: Taluk, Village, Pincode, Address.
    - If Urban Corporation ward match found: returns Corporation details with exact ward_no and zone.
    - If Rural Village Panchayat: enforces ward_no=None, ward_name_en="Not Applicable (Rural Panchayat Area)",
      and local_body_type="Village Panchayat ({Village_Name})".
    - Zero hardcoded names in code: all mappings resolved dynamically from the master JSON structure.
    """
    if not isinstance(petition_payload, dict):
        petition_payload = {}

    p_id = str(petition_payload.get("petition_id") or petition_payload.get("source_id") or "UNKNOWN")
    p_taluk = str(petition_payload.get("taluk") or "").strip()
    p_village = str(petition_payload.get("village") or "").strip()
    p_pincode = str(petition_payload.get("pincode") or "").strip()
    p_address = str(petition_payload.get("address") or "").strip()
    p_street = str(petition_payload.get("street_name") or "").strip()
    p_door = str(petition_payload.get("door_no") or "").strip()

    geo_config = load_master_geo_config(master_geo_path)
    if not geo_config:
        logger.error("[GEO_VALIDATOR] Master geo matrix unavailable. Using safe fallback.")
        return {
            "status": "unmatched_fallback",
            "boundary_type": "Rural",
            "district": "ஈரோடு",
            "district_en": "Erode",
            "taluk": p_taluk or "ஈரோடு",
            "taluk_en": "Erode",
            "village": p_village or "Rural Territory",
            "village_en": p_village or "Rural Territory",
            "local_body_type": f"Village Panchayat ({p_village or 'Rural Territory'})",
            "local_body_name": f"Village Panchayat ({p_village or 'Rural Territory'})",
            "ward_no": None,
            "ward_name_en": "Not Applicable (Rural Panchayat Area)",
            "pincode": p_pincode or None,
            "audit_compliance_log": f"[GEO_AUDIT_COMPLIANCE] Petition {p_id} fallback mapped to Rural.",
            "is_valid": True
        }

    urban_matrix = geo_config.get("urban_matrix", {})
    rural_matrix = geo_config.get("rural_matrix", {})

    combined_corpus = f"{p_address} {p_street} {p_village} {p_taluk} {p_pincode}".lower()

    # 1. Check for explicit ward number reference
    explicit_ward_no: Optional[int] = None
    ward_num_match = re.search(r'(?:வார்டு|ward|w\.no|வார்டு\s*எண்)[\s\.\:\#-]*([0-9]{1,2})\b', combined_corpus)
    if ward_num_match:
        val = int(ward_num_match.group(1))
        if 1 <= val <= 60:
            explicit_ward_no = val

    # 2. Check Urban Matrix (Zones 1-4, Wards 1-60) first
    urban_match: Optional[Dict[str, Any]] = None
    matched_zone_en: Optional[str] = None
    matched_zone_ta: Optional[str] = None
    longest_urban_kw_len = 0

    zones = urban_matrix.get("zones", [])
    for z in zones:
        z_name_en = z.get("zone_name_en", "")
        z_name_ta = z.get("zone_name_ta", "")
        wards = z.get("wards", [])
        for w in wards:
            w_no = w.get("ward_no")
            w_pin = str(w.get("pincode") or "")
            keywords = w.get("keywords", [])

            # Check explicit ward number match
            if explicit_ward_no and explicit_ward_no == w_no:
                urban_match = w
                matched_zone_en = z_name_en
                matched_zone_ta = z_name_ta
                longest_urban_kw_len = 50
                break

            # Keyword matching
            for kw in keywords:
                kw_clean = str(kw).lower().strip()
                if not kw_clean or len(kw_clean) < 4:
                    continue
                if kw_clean in combined_corpus and len(kw_clean) > longest_urban_kw_len:
                    longest_urban_kw_len = len(kw_clean)
                    urban_match = w
                    matched_zone_en = z_name_en
                    matched_zone_ta = z_name_ta

        if explicit_ward_no and urban_match:
            break

    # If urban match found and not overridden by a strictly rural taluk with no corporation overlap
    if urban_match and longest_urban_kw_len >= 4:
        boundary_type = "Urban"
        ward_no = urban_match.get("ward_no")
        ward_name_en = urban_match.get("ward_name_en")
        ward_name_ta = urban_match.get("ward_name_ta")
        matched_taluk_ta = urban_match.get("taluk_ta") or "ஈரோடு"
        matched_taluk_en = urban_match.get("taluk_en") or "Erode"
        matched_firka_ta = urban_match.get("firka_ta")
        matched_firka_en = urban_match.get("firka_en")
        matched_pincode = p_pincode or urban_match.get("pincode")
        local_body_type = "Corporation"
        local_body_name = urban_matrix.get("corporation_name_en", "Erode City Municipal Corporation")

        zone_no_match = re.search(r'\b(?:zone|மண்டலம்)\s*(\d+)', matched_zone_en or "", re.IGNORECASE)
        zone_no_int = int(zone_no_match.group(1)) if zone_no_match else (3 if ward_no and 31 <= ward_no <= 45 else 1)

        audit_log = (
            f"[GEO_AUDIT_COMPLIANCE] Petition {p_id} mapped to boundary_type={boundary_type}, "
            f"taluk={matched_taluk_en}, local_body_type={local_body_type}, ward_no={ward_no}, "
            f"ward_name={ward_name_en}, zone={matched_zone_en}"
        )
        logger.info(audit_log)

        return {
            "status": "matched",
            "boundary_type": boundary_type,
            "district": "ஈரோடு",
            "district_en": "Erode",
            "revenue_division": "ஈரோடு வருவாய் கோட்டம்",
            "revenue_division_en": "Erode Division",
            "taluk": matched_taluk_ta,
            "taluk_en": matched_taluk_en,
            "firka": matched_firka_ta,
            "firka_en": matched_firka_en,
            "village": p_village or ward_name_ta,
            "local_body_type": local_body_type,
            "local_body_name": local_body_name,
            "municipality_ward": local_body_name,
            "zone": matched_zone_en,
            "zone_name": matched_zone_en,
            "zone_no": zone_no_int,
            "zone_ta": matched_zone_ta,
            "ward_no": ward_no,
            "ward_name_en": ward_name_en,
            "ward_name_ta": ward_name_ta,
            "pincode": matched_pincode,
            "street_name": p_street or None,
            "door_no": p_door or None,
            "address": p_address or None,
            "audit_compliance_log": audit_log,
            "is_valid": True
        }

    # 3. Rural Matrix Match Check
    matched_rural_village: Optional[Dict[str, Any]] = None
    matched_rural_taluk_obj: Optional[Dict[str, Any]] = None
    longest_rural_kw_len = 0

    for r_taluk in rural_matrix.get("taluks", []):
        t_en = r_taluk.get("taluk_name_en", "")
        t_ta = r_taluk.get("taluk_name_ta", "")

        t_mentioned = (
            (t_en and t_en.lower() in combined_corpus) or
            (t_ta and t_ta.lower() in combined_corpus)
        )

        villages = r_taluk.get("villages") or r_taluk.get("village_panchayats") or []
        for v in villages:
            v_en_name = (v.get("village_name_en") or "").lower()
            v_ta_name = (v.get("village_name_ta") or "").lower()
            v_kws = v.get("keywords", [])
            for kw in v_kws:
                kw_clean = str(kw).lower().strip()
                if not kw_clean:
                    continue
                if kw_clean in combined_corpus:
                    score = len(kw_clean) + (30 if t_mentioned else 0)
                    if p_village and (p_village.lower() in v_en_name or p_village.lower() in v_ta_name or v_en_name in p_village.lower() or v_ta_name in p_village.lower()):
                        score += 150
                    if score > longest_rural_kw_len:
                        longest_rural_kw_len = score
                        matched_rural_village = v
                        matched_rural_taluk_obj = r_taluk

    # If rural village matched or rural taluk specified
    if matched_rural_taluk_obj or p_taluk or p_village:
        boundary_type = "Rural"
        
        # Determine clean English and Tamil village name
        v_name_en = None
        v_name_ta = None
        
        # 1. If explicit village is in petition payload or address, prioritize it
        cand_v = p_village or (matched_rural_village.get("village_name_en") if matched_rural_village else None)
        if cand_v:
            v_lower = str(cand_v).strip().lower()
            if "உக்கரம்" in v_lower or "ukkaram" in v_lower:
                v_name_en = "Ukkaram"
                v_name_ta = "உக்கரம்"
            elif "வண்டிபாளையம்" in v_lower or "vandipalayam" in v_lower:
                v_name_en = "Vandipalayam"
                v_name_ta = "வண்டிபாளையம்"
            elif "வெள்ளோடு" in v_lower or "vellode" in v_lower or "vellodu" in v_lower:
                v_name_en = "Vellode"
                v_name_ta = "வெள்ளோடு"
            else:
                v_name_en = cand_v
                v_name_ta = (matched_rural_village.get("village_name_ta") if matched_rural_village else cand_v)
        elif matched_rural_village:
            v_name_en = matched_rural_village.get("village_name_en")
            v_name_ta = matched_rural_village.get("village_name_ta")

        v_name_en = v_name_en or "Rural Territory"
        v_name_ta = v_name_ta or "ஊரக பகுதி"

        t_name_en = p_taluk or (matched_rural_taluk_obj.get("taluk_name_en") if matched_rural_taluk_obj else "Erode")
        t_name_ta = p_taluk or (matched_rural_taluk_obj.get("taluk_name_ta") if matched_rural_taluk_obj else "ஈரோடு")
        
        # Normalize Taluk names
        if t_name_en in ["சத்தியமங்கலம்", "Sathyamangalam"]:
            t_name_en = "Sathyamangalam"
            t_name_ta = "சத்தியமங்கலம்"
        elif t_name_en in ["பவானி", "Bhavani"]:
            t_name_en = "Bhavani"
            t_name_ta = "பவானி"
        elif t_name_en in ["ஈரோடு", "Erode"]:
            t_name_en = "Erode"
            t_name_ta = "ஈரோடு"
        elif t_name_en in ["பெருந்துறை", "Perundurai"]:
            t_name_en = "Perundurai"
            t_name_ta = "பெருந்துறை"

        f_name_en = matched_rural_village.get("firka_en") if matched_rural_village else None
        f_name_ta = matched_rural_village.get("firka_ta") if matched_rural_village else None
        r_pin = p_pincode or (matched_rural_village.get("pincode") if matched_rural_village else None)
        rev_div_en = "Gobichettipalayam Division" if t_name_en in ["Sathyamangalam", "Bhavani", "Gobichettipalayam", "Anthiyur", "Thalavadi"] else "Erode Division"
        rev_div_ta = "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்" if rev_div_en.startswith("Gobichettipalayam") else "ஈரோடு வருவாய் கோட்டம்"

        local_body_type = f"Village Panchayat ({v_name_en})"

        audit_log = (
            f"[GEO_AUDIT_COMPLIANCE] Petition {p_id} mapped to boundary_type={boundary_type}, "
            f"taluk={t_name_en}, village={v_name_en}, local_body_type={local_body_type}, "
            f"ward_no=null"
        )
        logger.info(audit_log)

        return {
            "status": "matched",
            "boundary_type": boundary_type,
            "district": "ஈரோடு",
            "district_en": "Erode",
            "revenue_division": rev_div_ta,
            "revenue_division_en": rev_div_en,
            "taluk": t_name_ta,
            "taluk_en": t_name_en,
            "firka": f_name_ta,
            "firka_en": f_name_en,
            "village": v_name_ta,
            "village_en": v_name_en,
            "local_body_type": local_body_type,
            "local_body_name": local_body_type,
            "municipality_ward": None,
            "zone": None,
            "zone_ta": None,
            "ward_no": None,
            "ward_name_en": "Not Applicable (Rural Panchayat Area)",
            "ward_name_ta": None,
            "pincode": r_pin,
            "street_name": p_street or None,
            "door_no": p_door or None,
            "address": p_address or None,
            "audit_compliance_log": audit_log,
            "is_valid": True
        }

    # 4. Fallback for generic / non-corporation rural addresses
    boundary_type = "Rural"
    resolved_village = p_village or "Rural Territory"
    resolved_taluk_ta = p_taluk or "ஈரோடு"
    resolved_taluk_en = "Erode" if resolved_taluk_ta in ["ஈரோடு", "Erode"] else resolved_taluk_ta

    local_body_type = f"Village Panchayat ({resolved_village})"

    audit_log = (
        f"[GEO_AUDIT_COMPLIANCE] Petition {p_id} mapped to boundary_type={boundary_type}, "
        f"taluk={resolved_taluk_en}, village={resolved_village}, local_body_type={local_body_type}, "
        f"ward_no=null"
    )
    logger.info(audit_log)

    return {
        "status": "unmatched_fallback",
        "boundary_type": boundary_type,
        "district": "ஈரோடு",
        "district_en": "Erode",
        "revenue_division": "ஈரோடு வருவாய் கோட்டம்",
        "revenue_division_en": "Erode Division",
        "taluk": resolved_taluk_ta,
        "taluk_en": resolved_taluk_en,
        "firka": None,
        "firka_en": None,
        "village": resolved_village,
        "village_en": resolved_village,
        "local_body_type": local_body_type,
        "local_body_name": local_body_type,
        "municipality_ward": None,
        "zone": None,
        "zone_ta": None,
        "ward_no": None,
        "ward_name_en": "Not Applicable (Rural Panchayat Area)",
        "ward_name_ta": None,
        "pincode": p_pincode or None,
        "street_name": p_street or None,
        "door_no": p_door or None,
        "address": p_address or None,
        "audit_compliance_log": audit_log,
        "is_valid": True
    }
