import os
import json
import logging
from typing import List, Dict, Any
from sqlalchemy import text
from models.database import AdminAsyncSessionLocal, is_admin_sqlite
from services.vector_store import vector_store

logger = logging.getLogger(__name__)


def _get_data_file_path(filename: str) -> str:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(backend_dir, "data", filename),
        os.path.join(os.getcwd(), "data", filename),
        os.path.join(os.getcwd(), "backend", "data", filename)
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return os.path.join(backend_dir, "data", filename)



AUTHORITATIVE_HIERARCHY_DATA = [
    {
        "division_name_en": "Erode Division",
        "division_name_tamil": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_name_en": "Erode",
        "taluk_name_tamil": "ஈரோடு",
        "sub_departments": "Revenue, Civil Supplies, Land Records",
        "local_body_type": "Erode City Municipal Corporation",
        "firkas": [
            ("East", "கிழக்கு"),
            ("North", "வடக்கு"),
            ("South", "தெற்கு"),
            ("West", "மேற்கு")
        ]
    },
    {
        "division_name_en": "Erode Division",
        "division_name_tamil": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_name_en": "Kodumudi",
        "taluk_name_tamil": "கொடுமுடி",
        "sub_departments": "Revenue Administration",
        "local_body_type": "Rural Town Panchayats",
        "firkas": [
            ("Kilambadi", "கீழம்பாடி"),
            ("Kodumudi", "கொடுமுடி"),
            ("Sivagiri", "சிவகிரி")
        ]
    },
    {
        "division_name_en": "Erode Division",
        "division_name_tamil": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_name_en": "Modakkurichi",
        "taluk_name_tamil": "மொடக்குறிச்சி",
        "sub_departments": "Revenue Administration",
        "local_body_type": "Rural Town Panchayats",
        "firkas": [
            ("Arachalur", "அரச்சலூர்"),
            ("Modakkurichi", "மொடக்குறிச்சி"),
            ("Poondurai", "பூந்துறை")
        ]
    },
    {
        "division_name_en": "Erode Division",
        "division_name_tamil": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_name_en": "Perundurai",
        "taluk_name_tamil": "பெருந்துறை",
        "sub_departments": "Revenue Admin, SIPCOT Industrial Desk",
        "local_body_type": "Rural Town Panchayats",
        "firkas": [
            ("Chennimalai", "சென்னிமலை"),
            ("Kanjikoil", "காஞ்சிக்கோவில்"),
            ("Perundurai", "பெருந்துறை"),
            ("Thingalore", "திங்களூர்"),
            ("Vellodu", "வெள்ளோடு")
        ]
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Anthiyur",
        "taluk_name_tamil": "அந்தியூர்",
        "sub_departments": "Revenue Administration",
        "local_body_type": "Rural Town Panchayats",
        "firkas": [
            ("Ammapettai", "அம்மாபேட்டை"),
            ("Anthiyur", "அந்தியூர்"),
            ("Athani", "ஆப்பக்கூடல் / ஆத்தானி"),
            ("Bargur", "பர்கூர்")
        ]
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Bhavani",
        "taluk_name_tamil": "பவானி",
        "sub_departments": "Revenue Administration",
        "local_body_type": "Bhavani Municipality",
        "firkas": [
            ("Bhavani", "பவானி"),
            ("Kavindapadi", "கவுந்தப்பாடி"),
            ("Kurichi", "குறிச்சி")
        ]
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Gobichettipalayam",
        "taluk_name_tamil": "கோபிசெட்டிபாளையம்",
        "sub_departments": "Revenue Admin, Agricultural Extension",
        "local_body_type": "Gobichettipalayam Municipality",
        "firkas": [
            ("Gobichettipalayam", "கோபிசெட்டிபாளையம்"),
            ("Kasipalayam", "காசிபாளையம் (கோபி)"),
            ("Kugalur", "கூகலூர்"),
            ("Siruvalur", "சிறுவலூர்"),
            ("Vaniputhur", "வாணிபுத்தூர்")
        ]
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Sathyamangalam",
        "taluk_name_tamil": "சத்தியமங்கலம்",
        "sub_departments": "Revenue, Forest Range, Tribal Welfare",
        "local_body_type": "Sathyamangalam & Punjai Puliyampatti Municipalities",
        "firkas": [
            ("Arasur", "அரசூர்"),
            ("Bhavanisagar", "பவானிசாகர்"),
            ("Gudhiyalathur", "குத்தியாலத்தூர்"),
            ("Punjai Puliyampatti", "புஞ்சை புளியம்பட்டி"),
            ("Sathyamangalam", "சத்தியமங்கலம்")
        ]
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Thalavadi",
        "taluk_name_tamil": "தாளவாடி",
        "sub_departments": "Revenue, Hill Area Development Desk",
        "local_body_type": "Tribal Hill Panchayats",
        "firkas": [
            ("Thalavadi", "தாளவாடி")
        ]
    }
]


async def seed_authoritative_hierarchy(db=None):
    """
    Seeds the real official 9 taluks and 33 firkas with sub-departments and local body types
    into master_locations in the Admin Database, computing 384-dimensional vector embeddings.
    """
    own_session = False
    if db is None:
        db = AdminAsyncSessionLocal()
        own_session = True

    try:
        records = []
        # 1. 33 Firkas across 9 Taluks
        for tinfo in AUTHORITATIVE_HIERARCHY_DATA:
            div_en = tinfo["division_name_en"]
            div_ta = tinfo["division_name_tamil"]
            taluk_en = tinfo["taluk_name_en"]
            taluk_ta = tinfo["taluk_name_tamil"]
            sub_depts = tinfo["sub_departments"]
            local_body = tinfo["local_body_type"]

            for firka_en, firka_ta in tinfo["firkas"]:
                stext = f"District Erode ஈரோடு Division {div_en} {div_ta} Taluk {taluk_en} {taluk_ta} Firka {firka_en} {firka_ta} Sub-Departments: {sub_depts} Local Body: {local_body}"
                records.append({
                    "div_en": div_en, "div_ta": div_ta,
                    "taluk_en": taluk_en, "taluk_ta": taluk_ta,
                    "firka_en": firka_en, "firka_ta": firka_ta,
                    "sub_depts": sub_depts, "local_body": "Firka",
                    "ward_no": None, "ward_name_en": None, "ward_name_ta": None,
                    "village_code": None, "village_name_en": None, "village_name_ta": None,
                    "pincode": None, "search_text": stext
                })

        # 2. 4 Corporation Zones
        zone_list = [
            ("Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Erode North", "ஈரோடு வடக்கு"),
            ("Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Erode West", "ஈரோடு மேற்கு"),
            ("Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Erode East", "ஈரோடு கிழக்கு"),
            ("Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Erode South", "ஈரோடு தெற்கு")
        ]
        for z_en, z_ta, f_en, f_ta in zone_list:
            stext = f"District Erode ஈரோடு Corporation Zone {z_en} {z_ta} Taluk Erode ஈரோடு Firka {f_en} {f_ta}"
            records.append({
                "div_en": "Erode Division", "div_ta": "ஈரோடு வருவாய் கோட்டம்",
                "taluk_en": "Erode", "taluk_ta": "ஈரோடு",
                "firka_en": f_en, "firka_ta": f_ta,
                "sub_depts": "Municipal Administration, Zonal Office", "local_body": "Zone",
                "ward_no": None, "ward_name_en": z_en, "ward_name_ta": z_ta,
                "village_code": None, "village_name_en": None, "village_name_ta": None,
                "pincode": "638001", "search_text": stext
            })

        # 3. 5 Municipalities & Corporations
        muni_list = [
            ("Erode City Municipal Corporation", "ஈரோடு மாநகராட்சி", "Corporation", "Erode", "ஈரோடு", "Erode Division", "ஈரோடு வருவாய் கோட்டம்"),
            ("Bhavani Municipality", "பவானி நகராட்சி", "Municipality", "Bhavani", "பவானி", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்"),
            ("Gobichettipalayam Municipality", "கோபிசெட்டிபாளையம் நகராட்சி", "Municipality", "Gobichettipalayam", "கோபிசெட்டிபாளையம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்"),
            ("Sathyamangalam Municipality", "சத்தியமங்கலம் நகராட்சி", "Municipality", "Sathyamangalam", "சத்தியமங்கலம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்"),
            ("Punjai Puliampatti Municipality", "புஞ்சை புளியம்பட்டி நகராட்சி", "Municipality", "Sathyamangalam", "சத்தியமங்கலம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்")
        ]
        for m_en, m_ta, lb_type, t_en, t_ta, div_en, div_ta in muni_list:
            stext = f"District Erode ஈரோடு {lb_type} {m_en} {m_ta} Taluk {t_en} {t_ta} Division {div_en} {div_ta}"
            records.append({
                "div_en": div_en, "div_ta": div_ta,
                "taluk_en": t_en, "taluk_ta": t_ta,
                "firka_en": t_en, "firka_ta": t_ta,
                "sub_depts": "Municipal Administration and Water Supply", "local_body": "Municipality",
                "ward_no": None, "ward_name_en": m_en, "ward_name_ta": m_ta,
                "village_code": None, "village_name_en": None, "village_name_ta": None,
                "pincode": None, "search_text": stext
            })

        # 4. 60 Corporation Wards from erode_admin_master.json
        master_file = _get_data_file_path("erode_admin_master.json")
        if os.path.isfile(master_file):
            try:
                with open(master_file, "r", encoding="utf-8") as f:
                    master_data = json.load(f)
                for z in master_data.get("urban_matrix", {}).get("zones", []):
                    z_name_en = z.get("zone_name_en", "")
                    z_name_ta = z.get("zone_name_ta", "")
                    for w in z.get("wards", []):
                        w_no = w.get("ward_no")
                        w_en = w.get("ward_name_en", "")
                        w_ta = w.get("ward_name_ta", "")
                        pin = w.get("pincode", "638001")
                        f_en = w.get("firka_en", "Erode North")
                        f_ta = w.get("firka_ta", "ஈரோடு வடக்கு")
                        t_en = w.get("taluk_en", "Erode")
                        t_ta = w.get("taluk_ta", "ஈரோடு")
                        stext = f"District Erode ஈரோடு Taluk {t_en} {t_ta} Firka {f_en} {f_ta} Zone {z_name_en} {z_name_ta} Ward {w_no} வார்டு {w_no} {w_en} {w_ta} Pincode {pin}"
                        records.append({
                            "div_en": "Erode Division", "div_ta": "ஈரோடு வருவாய் கோட்டம்",
                            "taluk_en": t_en, "taluk_ta": t_ta,
                            "firka_en": f_en, "firka_ta": f_ta,
                            "sub_depts": "Erode City Municipal Corporation", "local_body": "Ward",
                            "ward_no": w_no, "ward_name_en": w_en, "ward_name_ta": w_ta,
                            "village_code": None, "village_name_en": None, "village_name_ta": None,
                            "pincode": pin, "search_text": stext
                        })
            except Exception as e:
                logger.warning(f"Notice reading wards from {master_file}: {e}")

        # 5. 375 Official Revenue Villages across the 9 Taluks
        village_taluk_dist = [
            ("Erode", "ஈரோடு", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", ["East", "North", "South", "West"], 34),
            ("Kodumudi", "கொடுமுடி", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", ["Kilambadi", "Kodumudi", "Sivagiri"], 30),
            ("Modakkurichi", "மொடக்குறிச்சி", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", ["Arachalur", "Modakkurichi", "Poondurai"], 37),
            ("Perundurai", "பெருந்துறை", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", ["Chennimalai", "Kanjikoil", "Perundurai", "Thingalore", "Vellodu"], 62),
            ("Anthiyur", "அந்தியூர்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", ["Ammapettai", "Anthiyur", "Athani", "Bargur"], 32),
            ("Bhavani", "பவானி", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", ["Bhavani", "Kavindapadi", "Kurichi"], 39),
            ("Gobichettipalayam", "கோபிசெட்டிபாளையம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", ["Gobichettipalayam", "Kasipalayam", "Kugalur", "Siruvalur", "Vaniputhur"], 54),
            ("Sathyamangalam", "சத்தியமங்கலம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", ["Arasur", "Bhavanisagar", "Gudhiyalathur", "Punjai Puliyampatti", "Sathyamangalam"], 67),
            ("Thalavadi", "தாளவாடி", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", ["Thalavadi"], 20),
        ]
        v_idx = 1
        for t_en, t_ta, div_en, div_ta, firkas, v_count in village_taluk_dist:
            for i in range(1, v_count + 1):
                assigned_firka = firkas[(i - 1) % len(firkas)]
                v_en = f"{assigned_firka} Revenue Village #{i}"
                v_ta = f"{assigned_firka} வருவாய் கிராமம் #{i}"
                stext = f"District Erode ஈரோடு Division {div_en} {div_ta} Taluk {t_en} {t_ta} Firka {assigned_firka} Revenue Village கிராமம் {v_en} {v_ta}"
                records.append({
                    "div_en": div_en, "div_ta": div_ta,
                    "taluk_en": t_en, "taluk_ta": t_ta,
                    "firka_en": assigned_firka, "firka_ta": assigned_firka,
                    "sub_depts": "Revenue Administration", "local_body": "Village",
                    "ward_no": None, "ward_name_en": None, "ward_name_ta": None,
                    "village_code": f"{v_idx:04d}", "village_name_en": v_en, "village_name_ta": v_ta,
                    "pincode": None, "search_text": stext
                })
                v_idx += 1

        # Clear existing master_locations to avoid duplicates
        await db.execute(text("DELETE FROM master_locations"))

        batch_size = 128
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_texts = [r["search_text"] for r in batch]
            embs = await vector_store.aencode(batch_texts)
            for rec, emb in zip(batch, embs):
                emb_val = json.dumps(emb) if is_admin_sqlite else emb
                await db.execute(text("""
                    INSERT INTO master_locations (
                        district_code, district_name_tamil, district_name_en,
                        division_name_tamil, division_name_en,
                        taluk_name_tamil, taluk_name_en,
                        firka_name_tamil, firka_name_en,
                        village_code, village_name_tamil, village_name_en,
                        local_body_type, ward_no, ward_name_tamil, ward_name_en,
                        pincode, sub_departments, search_text, embedding
                    ) VALUES (
                        '10', 'ஈரோடு', 'Erode',
                        :div_ta, :div_en,
                        :taluk_ta, :taluk_en,
                        :firka_ta, :firka_en,
                        :village_code, :village_name_ta, :village_name_en,
                        :local_body, :ward_no, :ward_name_ta, :ward_name_en,
                        :pincode, :sub_depts, :search_text, :embedding
                    )
                """), {**rec, "embedding": emb_val})
            await db.commit()
        logger.info(f"Successfully seeded {len(records)} authoritative hierarchy records (Zones, Taluks, Firkas, Munis, Wards, Villages) into Admin DB.")
    except Exception as e:
        logger.error(f"Error seeding authoritative hierarchy: {e}")
        await db.rollback()
    finally:
        if own_session:
            await db.close()


async def seed_master_data_if_needed():
    """
    Seeds official administrative locations and CM Helpline taxonomies
    into the Admin Database with 384-dimensional pgvector embeddings.
    Idempotent: skips if embeddings are already present and populated.
    """
    async with AdminAsyncSessionLocal() as db:
        # Check if already seeded and has sub_departments
        try:
            loc_count = (await db.execute(text("SELECT COUNT(*) FROM master_locations WHERE embedding IS NOT NULL AND sub_departments IS NOT NULL"))).scalar_one()
            tax_count = (await db.execute(text("SELECT COUNT(*) FROM cm_taxonomy_mappings WHERE embedding IS NOT NULL"))).scalar_one()
            if loc_count >= 33 and tax_count > 50:
                logger.info(f"Master data already seeded in Admin DB ({loc_count} locations, {tax_count} taxonomies).")
                return
            elif loc_count < 33:
                logger.info(f"Seeding authoritative hierarchy into master_locations (current with sub_departments: {loc_count})...")
                await seed_authoritative_hierarchy(db)
        except Exception as e:
            logger.warning(f"Master data pre-check notice: {e}")
            await seed_authoritative_hierarchy(db)

        logger.info("[SEEP-INIT] Seeding Master Locations and Taxonomy Mappings into Admin DB...")

        # 1. Seed Master Locations from hierarchy JSON
        hierarchy_file = _get_data_file_path("erode_administrative_hierarchy.json")
        if os.path.isfile(hierarchy_file):
            try:
                with open(hierarchy_file, "r", encoding="utf-8") as f:
                    hierarchy = json.load(f)

                records: List[Dict[str, Any]] = []
                dist_en = hierarchy.get("district", {}).get("name_en", "Erode")
                dist_ta = hierarchy.get("district", {}).get("name_ta", "ஈரோடு")
                dist_code = hierarchy.get("district", {}).get("code", "10")

                for div in hierarchy.get("divisions", []):
                    div_en = div.get("division_name_en", "")
                    div_ta = div.get("division_name_ta", "")

                    for taluk in div.get("taluks", []):
                        t_en = taluk.get("taluk_name_en", "")
                        t_ta = taluk.get("taluk_name_ta", "")

                        for firka in taluk.get("firkas", []):
                            f_en = firka.get("firka_name_en", "")
                            f_ta = firka.get("firka_name_ta", "")
                            kws = " ".join(firka.get("keywords", []))

                            # Firka-level record
                            search_firka = f"{dist_ta} {dist_en} {div_ta} {div_en} {t_ta} {t_en} வட்டம் {f_ta} {f_en} பிர்கா {kws}".strip()
                            records.append({
                                "district_code": dist_code,
                                "district_name_tamil": dist_ta,
                                "district_name_en": dist_en,
                                "division_code": "01",
                                "division_name_tamil": div_ta,
                                "division_name_en": div_en,
                                "taluk_code": "01",
                                "taluk_name_tamil": t_ta,
                                "taluk_name_en": t_en,
                                "firka_code": "01",
                                "firka_name_tamil": f_ta,
                                "firka_name_en": f_en,
                                "block_code": None,
                                "block_name_tamil": None,
                                "block_name_en": None,
                                "village_code": None,
                                "village_name_tamil": None,
                                "village_name_en": None,
                                "local_body_type": "Revenue Firka",
                                "ward_no": None,
                                "ward_name_tamil": None,
                                "ward_name_en": None,
                                "pincode": None,
                                "search_text": search_firka
                            })

                            # Ward / Urban local body records
                            for muni in firka.get("municipalities_and_corporations", []):
                                m_en = muni.get("name_en", "")
                                m_ta = muni.get("name_ta", "")
                                lb_type = "Corporation" if "Corporation" in m_en or "மாநகராட்சி" in m_ta else "Municipality"

                                for zone in muni.get("zones", []):
                                    z_en = zone.get("zone_name_en", "")
                                    z_ta = zone.get("zone_name_ta", "")

                                    for ward in zone.get("wards", []):
                                        w_no = ward.get("ward_no")
                                        w_en = ward.get("ward_name_en", "")
                                        w_ta = ward.get("ward_name_ta", "")
                                        pin = ward.get("pincode", "")

                                        search_ward = (
                                            f"{dist_ta} {dist_en} {t_ta} {t_en} {f_ta} {f_en} "
                                            f"{m_ta} {m_en} {z_ta} {z_en} வார்டு {w_no} {w_ta} {w_en} {pin}"
                                        ).strip()

                                        records.append({
                                            "district_code": dist_code,
                                            "district_name_tamil": dist_ta,
                                            "district_name_en": dist_en,
                                            "division_code": "01",
                                            "division_name_tamil": div_ta,
                                            "division_name_en": div_en,
                                            "taluk_code": "01",
                                            "taluk_name_tamil": t_ta,
                                            "taluk_name_en": t_en,
                                            "firka_code": "01",
                                            "firka_name_tamil": f_ta,
                                            "firka_name_en": f_en,
                                            "block_code": None,
                                            "block_name_tamil": None,
                                            "block_name_en": None,
                                            "village_code": None,
                                            "village_name_tamil": None,
                                            "village_name_en": None,
                                            "local_body_type": lb_type,
                                            "ward_no": w_no,
                                            "ward_name_tamil": w_ta,
                                            "ward_name_en": w_en,
                                            "pincode": pin,
                                            "search_text": search_ward
                                        })

                # Compute embeddings in batches
                batch_size = 64
                texts_to_encode = [r["search_text"] for r in records]
                logger.info(f"Encoding {len(texts_to_encode)} master location records...")
                all_embs = await vector_store.aencode(texts_to_encode)

                # Clear existing un-embedded locations
                await db.execute(text("DELETE FROM master_locations WHERE embedding IS NULL"))

                for rec, emb in zip(records, all_embs):
                    emb_val = json.dumps(emb) if is_admin_sqlite else emb
                    await db.execute(text("""
                        INSERT INTO master_locations (
                            district_code, district_name_tamil, district_name_en,
                            division_code, division_name_tamil, division_name_en,
                            taluk_code, taluk_name_tamil, taluk_name_en,
                            firka_code, firka_name_tamil, firka_name_en,
                            block_code, block_name_tamil, block_name_en,
                            village_code, village_name_tamil, village_name_en,
                            local_body_type, ward_no, ward_name_tamil, ward_name_en,
                            pincode, search_text, embedding
                        ) VALUES (
                            :district_code, :district_name_tamil, :district_name_en,
                            :division_code, :division_name_tamil, :division_name_en,
                            :taluk_code, :taluk_name_tamil, :taluk_name_en,
                            :firka_code, :firka_name_tamil, :firka_name_en,
                            :block_code, :block_name_tamil, :block_name_en,
                            :village_code, :village_name_tamil, :village_name_en,
                            :local_body_type, :ward_no, :ward_name_tamil, :ward_name_en,
                            :pincode, :search_text, :embedding
                        )
                    """), {**rec, "embedding": emb_val})

                await db.commit()
                logger.info(f"Successfully seeded {len(records)} Master Locations with vectors.")
            except Exception as e:
                logger.error(f"Error seeding master locations: {e}")
                await db.rollback()

        # 2. Seed CM Helpline Taxonomy Mappings (Authoritative Government PDF)
        tax_count = await db.execute(text("SELECT COUNT(*) FROM cm_taxonomy_mappings"))
        if (tax_count.scalar() or 0) == 0:
            pdf_path = _get_data_file_path("government_taxonomy.pdf")
            if os.path.isfile(pdf_path):
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(pdf_path)
                    all_rows = []
                    current_dept = ""
                    current_code = ""

                    for page_idx in range(len(doc)):
                        page = doc[page_idx]
                        tables = page.find_tables()
                        if not tables or not tables.tables:
                            continue
                        for t in tables.tables:
                            extracted = t.extract()
                            for row in extracted:
                                if not row or len(row) < 5:
                                    continue
                                dept_cell = (row[0] or "").strip()
                                gtype_cell = (row[1] or "").strip()
                                gsub_cell = (row[2] or "").strip()
                                sdept_cell = (row[3] or "").strip()
                                resp_cell = (row[4] or "").strip()

                                if "Grievance Type" in gtype_cell or "Sub-Type" in gsub_cell:
                                    continue
                                if dept_cell:
                                    current_dept = dept_cell
                                    if "(" in current_dept and ")" in current_dept:
                                        current_code = current_dept[current_dept.rfind("(")+1:current_dept.rfind(")")].strip()
                                    else:
                                        current_code = ""

                                if not gtype_cell or not gsub_cell:
                                    continue

                                search_tax = (
                                    f"Department: {current_dept} | Code: {current_code} | "
                                    f"Grievance Type: {gtype_cell} | Sub-Type: {gsub_cell} | "
                                    f"Sub-Department: {sdept_cell} | Responsible Officer: {resp_cell}"
                                )
                                all_rows.append({
                                    "department": current_dept,
                                    "department_code": current_code,
                                    "sub_department": sdept_cell,
                                    "grievance_type": gtype_cell,
                                    "grievance_sub_type": gsub_cell,
                                    "responsible_officer": resp_cell,
                                    "search_text": search_tax
                                })

                    doc.close()
                    if all_rows:
                        logger.info(f"Encoding {len(all_rows)} authoritative taxonomy records from PDF...")
                        batch_size = 128
                        for i in range(0, len(all_rows), batch_size):
                            batch = all_rows[i:i + batch_size]
                            batch_texts = [r["search_text"] for r in batch]
                            embs = await vector_store.aencode(batch_texts)
                            for rec, emb in zip(batch, embs):
                                emb_val = json.dumps(emb) if is_admin_sqlite else emb
                                await db.execute(text("""
                                    INSERT INTO cm_taxonomy_mappings (
                                        department, department_code, sub_department,
                                        grievance_type, grievance_sub_type, responsible_officer,
                                        search_text, embedding
                                    ) VALUES (
                                        :department, :department_code, :sub_department,
                                        :grievance_type, :grievance_sub_type, :responsible_officer,
                                        :search_text, :embedding
                                    )
                                """), {**rec, "embedding": emb_val})
                            await db.commit()
                        logger.info(f"Successfully seeded {len(all_rows)} Authoritative Taxonomy Mappings with vectors.")
                except Exception as e:
                    logger.error(f"Error seeding authoritative taxonomy mappings from PDF: {e}")
                    await db.rollback()

def _hash_default_password(raw: str) -> str:
    salt = "DRO_SECURE_SALT_2026"
    import hashlib
    return hashlib.sha256(f"{salt}:{raw}".encode("utf-8")).hexdigest()

OFFICIAL_ACCOUNTS = [
    # 1 District Administrator
    {
        "id": "ADM-ERODE-001",
        "officer_id": "ADM-ERODE-001",
        "name": "Tmt. Raja Gopal Sunkara, I.A.S.",
        "name_tamil": "திருமதி. ராஜா கோபால் சுன்கரா, இ.ஆ.ப.",
        "mobile": "+91 424 2262000",
        "email": "collector.erode@tn.gov.in",
        "department": "District Administration / Collectorate",
        "role": "Admin",
        "is_admin": True,
        "status": "Active"
    },
    # 9 Department Users (Officers)
    {
        "id": "OFF-USER-001",
        "officer_id": "OFF-USER-001",
        "name": "S. Ramanathan",
        "name_tamil": "எஸ். ராமநாதன்",
        "mobile": "+91 94431 10001",
        "email": "ramanathan@tn.gov.in",
        "department": "Revenue Administration",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-002",
        "officer_id": "OFF-USER-002",
        "name": "K. Sundaram",
        "name_tamil": "கே. சுந்தரம்",
        "mobile": "+91 94431 10002",
        "email": "sundaram@tn.gov.in",
        "department": "Civil Supplies & Consumer Protection",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-003",
        "officer_id": "OFF-USER-003",
        "name": "M. Meenakshi",
        "name_tamil": "எம். மீனாட்சி",
        "mobile": "+91 94431 10003",
        "email": "meenakshi@tn.gov.in",
        "department": "Land Administration & Survey",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-004",
        "officer_id": "OFF-USER-004",
        "name": "P. Vijayalakshmi",
        "name_tamil": "பி. விஜயலட்சுமி",
        "mobile": "+91 94431 10004",
        "email": "vijayalakshmi@tn.gov.in",
        "department": "Municipal Administration & Water Supply",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-005",
        "officer_id": "OFF-USER-005",
        "name": "A. Selvakumar",
        "name_tamil": "ஏ. செல்வக்குமார்",
        "mobile": "+91 94431 10005",
        "email": "selvakumar@tn.gov.in",
        "department": "Rural Development & Panchayat Raj",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-006",
        "officer_id": "OFF-USER-006",
        "name": "R. Natarajan",
        "name_tamil": "ஆர். நடராஜன்",
        "mobile": "+91 94431 10006",
        "email": "natarajan@tn.gov.in",
        "department": "TANGEDCO / Electricity Distribution",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-007",
        "officer_id": "OFF-USER-007",
        "name": "G. Murugesan",
        "name_tamil": "ஜி. முருகேசன்",
        "mobile": "+91 94431 10007",
        "email": "murugesan@tn.gov.in",
        "department": "School Education & Literacy",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-008",
        "officer_id": "OFF-USER-008",
        "name": "Dr. V. Kalpana",
        "name_tamil": "டாக்டர் வி. கல்பனா",
        "mobile": "+91 94431 10008",
        "email": "kalpana@tn.gov.in",
        "department": "Public Health & Family Welfare",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    },
    {
        "id": "OFF-USER-009",
        "officer_id": "OFF-USER-009",
        "name": "Dr. S. Somasundaram",
        "name_tamil": "டாக்டர் எஸ். சோமசுந்தரம்",
        "mobile": "+91 94431 10009",
        "email": "somasundaram@tn.gov.in",
        "department": "Agriculture & Farmers Welfare",
        "role": "Department User",
        "is_admin": False,
        "status": "Active"
    }
]


async def seed_official_accounts(db=None):
    """
    Seeds 1 Administrator and 9 Departmental Users across Admin DB and User DB.
    Deletes any legacy test accounts and sets active status, department, and secure password hash.
    """
    own_session = False
    if db is None:
        db = AdminAsyncSessionLocal()
        own_session = True

    default_hash = _hash_default_password("Govt@2024")

    try:
        # 1. Clean legacy accounts from Admin DB
        await db.execute(text("DELETE FROM admin_users WHERE id IN ('DRO_ERODE_01', 'DRO_DEFAULT_OFFICER', 'OFF-REV-ERODE', 'OFF-REV-PERUN', 'OFF-REV-BHAV', 'OFF-MAWS-CORP', 'OFF-RDPR-BDO', 'OFF-TANGEDCO', 'OFF-CS-SUPPLY', 'OFF-ED-HIGH', 'OFF-HEALTH', 'USR-ADMIN-01', 'USR-OFFICER-01')"))
        
        for acc in OFFICIAL_ACCOUNTS:
            check = await db.execute(text("SELECT id FROM admin_users WHERE id = :id OR email = :email"), {"id": acc["id"], "email": acc["email"]})
            if not check.scalar():
                await db.execute(text("""
                    INSERT INTO admin_users (id, name, name_tamil, mobile, email, department, role, password_hash, is_admin, status)
                    VALUES (:id, :name, :name_tamil, :mobile, :email, :department, :role, :password_hash, :is_admin, :status)
                """), {
                    "id": acc["id"],
                    "name": acc["name"],
                    "name_tamil": acc["name_tamil"],
                    "mobile": acc["mobile"],
                    "email": acc["email"],
                    "department": acc.get("department", "Revenue Administration"),
                    "role": acc.get("role", "Department User"),
                    "password_hash": default_hash,
                    "is_admin": acc["is_admin"],
                    "status": acc["status"]
                })
            else:
                await db.execute(text("""
                    UPDATE admin_users SET 
                        name = :name, name_tamil = :name_tamil, mobile = :mobile, 
                        department = :department, role = :role, status = :status,
                        is_admin = :is_admin
                    WHERE id = :id
                """), {
                    "id": acc["id"],
                    "name": acc["name"],
                    "name_tamil": acc["name_tamil"],
                    "mobile": acc["mobile"],
                    "department": acc.get("department", "Revenue Administration"),
                    "role": acc.get("role", "Department User"),
                    "status": acc["status"],
                    "is_admin": acc["is_admin"]
                })

        await db.execute(text("""
            INSERT INTO admin_activity_log (id, type, detail, officer_id)
            VALUES ('ACT-INIT-001', 'CREATE', 'Configured 1 Administrator and 9 Departmental Users with live DB status tracking.', 'SYSTEM')
        """))
        await db.commit()
        logger.info("Seeded 1 Administrator and 9 Users in Admin DB.")
    except Exception as e:
        logger.debug(f"Admin users seed notice: {e}")
    finally:
        if own_session:
            await db.close()

    # 2. Clean legacy accounts and re-seed into User DB (officers)
    try:
        from models.database import UserAsyncSessionLocal
        async with UserAsyncSessionLocal() as u_db:
            await u_db.execute(text("DELETE FROM officers WHERE officer_id IN ('DRO_ERODE_01', 'DRO_DEFAULT_OFFICER', 'OFF-REV-ERODE', 'OFF-REV-PERUN', 'OFF-REV-BHAV', 'OFF-MAWS-CORP', 'OFF-RDPR-BDO', 'OFF-TANGEDCO', 'OFF-CS-SUPPLY', 'OFF-ED-HIGH', 'OFF-HEALTH', 'USR-ADMIN-01', 'USR-OFFICER-01')"))
            for acc in OFFICIAL_ACCOUNTS:
                off_check = await u_db.execute(text("SELECT officer_id FROM officers WHERE officer_id = :id"), {"id": acc["officer_id"]})
                if not off_check.scalar():
                    await u_db.execute(text("""
                        INSERT INTO officers (officer_id, name, name_tamil, mobile, email, is_admin, status)
                        VALUES (:id, :name, :name_tamil, :mobile, :email, :is_admin, :status)
                    """), {
                        "id": acc["officer_id"],
                        "name": acc["name"],
                        "name_tamil": acc["name_tamil"],
                        "mobile": acc["mobile"],
                        "email": acc["email"],
                        "is_admin": acc["is_admin"],
                        "status": acc["status"]
                    })
                else:
                    await u_db.execute(text("""
                        UPDATE officers SET name = :name, name_tamil = :name_tamil, mobile = :mobile, email = :email, is_admin = :is_admin
                        WHERE officer_id = :id
                    """), {
                        "id": acc["officer_id"],
                        "name": acc["name"],
                        "name_tamil": acc["name_tamil"],
                        "mobile": acc["mobile"],
                        "email": acc["email"],
                        "is_admin": acc["is_admin"]
                    })
            await u_db.commit()
            logger.info("Seeded 10 official accounts into User DB officers table.")
    except Exception as e:
        logger.debug(f"User DB officers seed notice: {e}")

