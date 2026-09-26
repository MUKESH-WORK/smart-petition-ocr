"""
Data Engineering Ingestion Pipeline: Nambiyur Taluk, 14 Development Blocks & 21 Intake Channels
=============================================================================================
Ingests:
1. Missing Nambiyur Taluk (நம்பியூர்) under Gobichettipalayam Division.
2. 3 Firkas of Nambiyur (Nambiyur, Kadathur, Kosanam).
3. All 33 Revenue Villages of Nambiyur Taluk from villageinfo.in with Rural/Urban classifications and pincodes.
4. All 14 Development Blocks of Erode District.
5. 21 Authoritative Ingestion Channels into cm_grievance_channels table.
6. Computes 384-dimensional semantic embeddings for all location entities.
"""

import sys
import os
import asyncio
import json
import logging
from typing import List, Dict, Any

# Ensure backend root is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models.database import AdminAsyncSessionLocal, init_db_schema, is_admin_sqlite
from services.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_nambiyur_pipeline")

NAMBIYUR_TALUK_DATA = {
    "division_name_en": "Gobichettipalayam Division",
    "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
    "division_code": "DIV_GOB",
    "taluk_name_en": "Nambiyur",
    "taluk_name_tamil": "நம்பியூர்",
    "taluk_code": "TAL_NAM",
    "block_name_en": "Nambiyur",
    "block_name_tamil": "நம்பியூர்",
    "block_code": "BLK_NAM",
    "sub_departments": "Revenue Administration, Agricultural Extension, Rural Development, Civil Supplies",
    "local_body_type": "Nambiyur Selection Grade Town Panchayat & Rural Village Panchayats",
    "firkas": [
        ("Nambiyur", "நம்பியூர்", "FRK_NAM_01"),
        ("Kadathur", "கடத்தூர்", "FRK_NAM_02"),
        ("Kosanam", "கோசணம்", "FRK_NAM_03")
    ]
}

# 33 Revenue Villages from villageinfo.in (Tamil Nadu -> Erode -> Nambiyur)
NAMBIYUR_VILLAGES = [
    {"en": "Andipalayam", "ta": "ஆண்டிபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Anjanur", "ta": "அஞ்சனூர்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Arasur", "ta": "அரசூர்", "pin": "638454", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Avalampalayam", "ta": "அவலம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Elathur", "ta": "எலத்தூர்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Emmampoondi", "ta": "எம்மம்பூண்டி", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Gudakkarai", "ta": "கூடக்கரை", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Irugalur", "ta": "இருகளூர்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Kadasellipalayam", "ta": "கடசெல்லிபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Kadathur", "ta": "கடத்தூர்", "pin": "638454", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Karapadi", "ta": "காரப்பாடி", "pin": "638459", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Karattupalayam", "ta": "கரட்டுப்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Kavilipalayam", "ta": "காவிலிபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Kosanam", "ta": "கோசணம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Kurumandur", "ta": "குருமந்தூர்", "pin": "638457", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Lagampalayam", "ta": "லகம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Mottanam", "ta": "மொட்டணம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Nambiyur", "ta": "நம்பியூர்", "pin": "638458", "type": "Selection Grade Town Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Nichampalayam", "ta": "நிச்சம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Olalakovil", "ta": "ஒலலக்கோவில்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Palamangalam", "ta": "பாலமங்கலம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Polavapalayam", "ta": "போலவபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Santhipalayam", "ta": "சாந்திபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Sellapampalayam", "ta": "செல்லப்பம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Sengapalli", "ta": "செங்கப்பள்ளி", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Sinnaripalayam", "ta": "சின்னரிபாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Sundakkampalayam", "ta": "சுண்டக்கம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Talguni", "ta": "தால்குனி", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Talaimalai", "ta": "தலைமலை", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Thoppampalayam", "ta": "தோப்பம்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"},
    {"en": "Varapalayam", "ta": "வரப்பாளையம்", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Nambiyur", "firka_ta": "நம்பியூர்"},
    {"en": "Vemandampalayam", "ta": "வேமண்டம்பாளையம்", "pin": "638462", "type": "Rural Village Panchayat", "firka": "Kosanam", "firka_ta": "கோசணம்"},
    {"en": "Vinnappalli", "ta": "விண்ணப்பள்ளி", "pin": "638458", "type": "Rural Village Panchayat", "firka": "Kadathur", "firka_ta": "கடத்தூர்"}
]

# 14 Development Blocks across Erode District
ERODE_14_BLOCKS = [
    {"en": "Ammapet", "ta": "அம்மாபேட்டை", "code": "BLK_AMM", "taluk": "Anthiyur"},
    {"en": "Anthiyur", "ta": "அந்தியூர்", "code": "BLK_ANT", "taluk": "Anthiyur"},
    {"en": "Bhavani", "ta": "பவானி", "code": "BLK_BHA", "taluk": "Bhavani"},
    {"en": "Bhavanisagar", "ta": "பவானிசாகர்", "code": "BLK_BHS", "taluk": "Sathyamangalam"},
    {"en": "Chennimalai", "ta": "சென்னிமலை", "code": "BLK_CHE", "taluk": "Perundurai"},
    {"en": "Erode", "ta": "ஈரோடு", "code": "BLK_ERD", "taluk": "Erode"},
    {"en": "Gobichettipalayam", "ta": "கோபிசெட்டிபாளையம்", "code": "BLK_GOB", "taluk": "Gobichettipalayam"},
    {"en": "Kodumudi", "ta": "கொடுமுடி", "code": "BLK_KOD", "taluk": "Kodumudi"},
    {"en": "Modakkurichi", "ta": "மொடக்குறிச்சி", "code": "BLK_MOD", "taluk": "Modakkurichi"},
    {"en": "Nambiyur", "ta": "நம்பியூர்", "code": "BLK_NAM", "taluk": "Nambiyur"},
    {"en": "Perundurai", "ta": "பெருந்துறை", "code": "BLK_PER", "taluk": "Perundurai"},
    {"en": "Sathyamangalam", "ta": "சத்தியமங்கலம்", "code": "BLK_SAT", "taluk": "Sathyamangalam"},
    {"en": "Thalavadi", "ta": "தாளவாடி", "code": "BLK_THA", "taluk": "Thalavadi"},
    {"en": "Thoockanaickenpalaiyam", "ta": "தூக்கநாயக்கன்பாளையம்", "code": "BLK_TNP", "taluk": "Gobichettipalayam"}
]

# 21 Official CM Grievance Ingestion Channels across 5 Vectors
CM_INTAKE_CHANNELS = [
    # Vector 1: Digital Direct (3)
    {"category": "digital_direct", "channel_name": "Call Center (CC)", "channel_code": "CC", "description": "Toll-free 1100 Integrated Citizen Call Center Helpline"},
    {"category": "digital_direct", "channel_name": "Citizen Web Portal (PORTAL)", "channel_code": "PORTAL", "description": "Tamil Nadu CM Helpline Citizen Online Web Portal"},
    {"category": "digital_direct", "channel_name": "E-mail Intake (EMAIL)", "channel_code": "EMAIL", "description": "Official State Grievance Redressal Direct Inbound E-mail"},

    # Vector 2: Executive Leadership (5)
    {"category": "executive_leadership", "channel_name": "Chief Minister Special Cell (CMCELL)", "channel_code": "CMCELL", "description": "Hon'ble Chief Minister's Special Grievance Redressal Cell"},
    {"category": "executive_leadership", "channel_name": "Chief Minister Camp Office (CMCAMP)", "channel_code": "CMCAMP", "description": "Chief Minister Camp Office Direct Citizen Petitions"},
    {"category": "executive_leadership", "channel_name": "Chief Secretary Office (CS)", "channel_code": "CS", "description": "Chief Secretary Secretariat Inward Grievance Monitoring Desk"},
    {"category": "executive_leadership", "channel_name": "Secretaries to CM (CMSECY)", "channel_code": "CMSECY", "description": "Secretaries to Hon'ble Chief Minister Specialized Desk"},
    {"category": "executive_leadership", "channel_name": "Ministers Office (MINOFF)", "channel_code": "MINOFF", "description": "Cabinet Ministers' Constituency & Departmental Petitions"},

    # Vector 3: Legislative (2)
    {"category": "legislative", "channel_name": "Member of Legislative Assembly (MLA)", "channel_code": "MLA", "description": "Constituency Grievance Submissions via State MLA Reference"},
    {"category": "legislative", "channel_name": "Member of Parliament (MPLS)", "channel_code": "MPLS", "description": "Member of Parliament (Lok Sabha / Rajya Sabha) Official Reference"},

    # Vector 4: District Grievance Days (5)
    {"category": "district_grievance_days", "channel_name": "Collectorate Monday Grievance Day (COLLMGDP)", "channel_code": "COLLMGDP", "description": "Weekly Monday Collectorate Grievance Redressal Day (DRO / Collector)"},
    {"category": "district_grievance_days", "channel_name": "Differently Abled Grievance Day (COLLDIFF)", "channel_code": "COLLDIFF", "description": "Monthly Dedicated Differently Abled Welfare Grievance Session"},
    {"category": "district_grievance_days", "channel_name": "Agriculture Grievance Day (COLLAGRI)", "channel_code": "COLLAGRI", "description": "Monthly District Farmers' Redressal Day Chaired by Collector"},
    {"category": "district_grievance_days", "channel_name": "Jamabandhi Revenue Audits (JMB)", "channel_code": "JMB", "description": "Annual Taluk-level Revenue Account Verification Jamabandhi"},
    {"category": "district_grievance_days", "channel_name": "Mass Contact Program (MCPCOLL)", "channel_code": "MCPCOLL", "description": "Manu Neethi Thittam / District Collectorate Mass Outreach Camp"},

    # Vector 5: Field Outreach Camps & Counters (6)
    {"category": "field_outreach_camps", "channel_name": "Makkaludan Mudhalvar Rural (MMR)", "channel_code": "MMR", "description": "Makkaludan Mudhalvar Village Panchayat Outreach Redressal Camps"},
    {"category": "field_outreach_camps", "channel_name": "Makkaludan Mudhalvar Urban (MMU)", "channel_code": "MMU", "description": "Makkaludan Mudhalvar Urban Municipal / Corporation Ward Outreach Camps"},
    {"category": "field_outreach_camps", "channel_name": "MM Camp General (MMC)", "channel_code": "MMC", "description": "Makkaludan Mudhalvar General Public Service Redressal Camp"},
    {"category": "field_outreach_camps", "channel_name": "MM Camp Special (MMCR)", "channel_code": "MMCR", "description": "Makkaludan Mudhalvar Special Target Redressal Camp"},
    {"category": "counters_walkin", "channel_name": "e-Sevai Facilitation Counter (ESEVAI)", "channel_code": "ESEVAI", "description": "Village / Urban TNeGA e-Sevai Service Center Walk-in Desk"},
    {"category": "counters_walkin", "channel_name": "Taluk Office Reception Counter (TALUK_COUNTER)", "channel_code": "TALUK_COUNTER", "description": "Direct In-person Submission at Taluk Revenue Office"}
]


async def run_pipeline():
    logger.info("Starting Nambiyur & Administrative Data Engineering Pipeline...")
    await init_db_schema()

    async with AdminAsyncSessionLocal() as db:
        # ── Step 1: Ingest 21 CM Grievance Channels ───────────────────────
        logger.info("Ingesting 21 CM Grievance Ingestion Channels into cm_grievance_channels...")
        for ch in CM_INTAKE_CHANNELS:
            existing = (await db.execute(
                text("SELECT id FROM cm_grievance_channels WHERE channel_code = :code"),
                {"code": ch["channel_code"]}
            )).scalar_one_or_none()

            if not existing:
                await db.execute(text("""
                    INSERT INTO cm_grievance_channels (category, channel_name, channel_code, is_active, description)
                    VALUES (:category, :channel_name, :channel_code, :is_active, :description)
                """), {**ch, "is_active": True})
        await db.commit()
        ch_count = (await db.execute(text("SELECT COUNT(*) FROM cm_grievance_channels"))).scalar_one()
        logger.info(f"Total CM Grievance Ingestion Channels in DB: {ch_count}")

        # ── Step 2: Check if Nambiyur Taluk already exists ───────────────
        nambiyur_existing = (await db.execute(
            text("SELECT COUNT(*) FROM master_locations WHERE taluk_name_en = 'Nambiyur'")
        )).scalar_one()

        if nambiyur_existing > 0:
            logger.info(f"Nambiyur locations already present ({nambiyur_existing} rows). Refreshing/updating...")
            await db.execute(text("DELETE FROM master_locations WHERE taluk_name_en = 'Nambiyur'"))
            await db.commit()

        # ── Step 3: Build records for Nambiyur Taluk, Firkas, and 33 Villages ──
        logger.info("Building location records for Nambiyur Taluk, 3 Firkas & 33 Revenue Villages...")
        new_records = []

        # A. Taluk HQ Record
        taluk_search = f"District Erode ஈரோடு Division Gobichettipalayam Division கோபிசெட்டிபாளையம் வருவாய் கோட்டம் Taluk Nambiyur நம்பியூர் Sub-Departments: {NAMBIYUR_TALUK_DATA['sub_departments']} Local Body: {NAMBIYUR_TALUK_DATA['local_body_type']} Pincode 638458"
        new_records.append({
            "district_code": "ERD", "district_name_tamil": "ஈரோடு", "district_name_en": "Erode",
            "division_code": "DIV_GOB", "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", "division_name_en": "Gobichettipalayam Division",
            "taluk_code": "TAL_NAM", "taluk_name_tamil": "நம்பியூர்", "taluk_name_en": "Nambiyur",
            "firka_code": "FRK_NAM", "firka_name_tamil": "நம்பியூர்", "firka_name_en": "Nambiyur",
            "block_code": "BLK_NAM", "block_name_tamil": "நம்பியூர்", "block_name_en": "Nambiyur",
            "village_code": "VIL_NAM_HQ", "village_name_tamil": "நம்பியூர்", "village_name_en": "Nambiyur Taluk Headquarters",
            "local_body_type": "Taluk HQ", "ward_no": None, "ward_name_tamil": None, "ward_name_en": None,
            "pincode": "638458", "search_text": taluk_search, "sub_departments": NAMBIYUR_TALUK_DATA["sub_departments"]
        })

        # B. 3 Firka Records
        for firka_en, firka_ta, firka_code in NAMBIYUR_TALUK_DATA["firkas"]:
            firka_search = f"District Erode ஈரோடு Division Gobichettipalayam Division கோபிசெட்டிபாளையம் வருவாய் கோட்டம் Taluk Nambiyur நம்பியூர் Firka {firka_en} {firka_ta} Sub-Departments: {NAMBIYUR_TALUK_DATA['sub_departments']} Local Body: Firka"
            new_records.append({
                "district_code": "ERD", "district_name_tamil": "ஈரோடு", "district_name_en": "Erode",
                "division_code": "DIV_GOB", "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", "division_name_en": "Gobichettipalayam Division",
                "taluk_code": "TAL_NAM", "taluk_name_tamil": "நம்பியூர்", "taluk_name_en": "Nambiyur",
                "firka_code": firka_code, "firka_name_tamil": firka_ta, "firka_name_en": firka_en,
                "block_code": "BLK_NAM", "block_name_tamil": "நம்பியூர்", "block_name_en": "Nambiyur",
                "village_code": None, "village_name_tamil": None, "village_name_en": None,
                "local_body_type": "Firka", "ward_no": None, "ward_name_tamil": None, "ward_name_en": None,
                "pincode": "638458", "search_text": firka_search, "sub_departments": NAMBIYUR_TALUK_DATA["sub_departments"]
            })

        # C. 33 Revenue Villages
        for idx, v in enumerate(NAMBIYUR_VILLAGES, 1):
            v_code = f"VIL_NAM_{idx:03d}"
            v_search = f"District Erode ஈரோடு Division Gobichettipalayam Division கோபிசெட்டிபாளையம் வருவாய் கோட்டம் Taluk Nambiyur நம்பியூர் Firka {v['firka']} {v['firka_ta']} Village {v['en']} {v['ta']} Local Body: {v['type']} Block Nambiyur நம்பியூர் Pincode {v['pin']}"
            new_records.append({
                "district_code": "ERD", "district_name_tamil": "ஈரோடு", "district_name_en": "Erode",
                "division_code": "DIV_GOB", "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", "division_name_en": "Gobichettipalayam Division",
                "taluk_code": "TAL_NAM", "taluk_name_tamil": "நம்பியூர்", "taluk_name_en": "Nambiyur",
                "firka_code": "FRK_NAM", "firka_name_tamil": v["firka_ta"], "firka_name_en": v["firka"],
                "block_code": "BLK_NAM", "block_name_tamil": "நம்பியூர்", "block_name_en": "Nambiyur",
                "village_code": v_code, "village_name_tamil": v["ta"], "village_name_en": v["en"],
                "local_body_type": v["type"], "ward_no": None, "ward_name_tamil": None, "ward_name_en": None,
                "pincode": v["pin"], "search_text": v_search, "sub_departments": NAMBIYUR_TALUK_DATA["sub_departments"]
            })

        # D. 14 Blocks (ensure all 14 exist in master_locations)
        for b in ERODE_14_BLOCKS:
            b_exists = (await db.execute(
                text("SELECT COUNT(*) FROM master_locations WHERE local_body_type = 'Development Block' AND block_name_en = :bname"),
                {"bname": b["en"]}
            )).scalar_one()

            if b_exists == 0:
                b_search = f"District Erode ஈரோடு Development Block ஊராட்சி ஒன்றியம் {b['en']} {b['ta']} Taluk {b['taluk']}"
                new_records.append({
                    "district_code": "ERD", "district_name_tamil": "ஈரோடு", "district_name_en": "Erode",
                    "division_code": "DIV_GOB" if b["taluk"] in ["Gobichettipalayam", "Anthiyur", "Bhavani", "Sathyamangalam", "Thalavadi", "Nambiyur"] else "DIV_ERD",
                    "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்" if b["taluk"] in ["Gobichettipalayam", "Anthiyur", "Bhavani", "Sathyamangalam", "Thalavadi", "Nambiyur"] else "ஈரோடு வருவாய் கோட்டம்",
                    "division_name_en": "Gobichettipalayam Division" if b["taluk"] in ["Gobichettipalayam", "Anthiyur", "Bhavani", "Sathyamangalam", "Thalavadi", "Nambiyur"] else "Erode Division",
                    "taluk_code": f"TAL_{b['taluk'][:3].upper()}", "taluk_name_tamil": b["ta"], "taluk_name_en": b["taluk"],
                    "firka_code": None, "firka_name_tamil": None, "firka_name_en": None,
                    "block_code": b["code"], "block_name_tamil": b["ta"], "block_name_en": b["en"],
                    "village_code": None, "village_name_tamil": None, "village_name_en": None,
                    "local_body_type": "Development Block", "ward_no": None, "ward_name_tamil": None, "ward_name_en": None,
                    "pincode": None, "search_text": b_search, "sub_departments": "Rural Development and Panchayat Raj Department (RDPR)"
                })

        logger.info(f"Total new location entities to encode and insert: {len(new_records)}")

        # ── Step 4: Compute 384-dimensional Vector Embeddings ─────────────
        search_texts = [r["search_text"] for r in new_records]
        logger.info(f"Computing 384-d neural embeddings via SentenceTransformer for {len(search_texts)} records...")
        embeddings = await vector_store.aencode(search_texts)

        # ── Step 5: Insert records into master_locations ──────────────────
        for r, emb in zip(new_records, embeddings):
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
                    pincode, search_text, embedding, sub_departments
                ) VALUES (
                    :district_code, :district_name_tamil, :district_name_en,
                    :division_code, :division_name_tamil, :division_name_en,
                    :taluk_code, :taluk_name_tamil, :taluk_name_en,
                    :firka_code, :firka_name_tamil, :firka_name_en,
                    :block_code, :block_name_tamil, :block_name_en,
                    :village_code, :village_name_tamil, :village_name_en,
                    :local_body_type, :ward_no, :ward_name_tamil, :ward_name_en,
                    :pincode, :search_text, :embedding, :sub_departments
                )
            """), {**r, "embedding": emb_val})

        await db.commit()

        # ── Step 6: Log activity into admin_activity_log ──────────────────
        import uuid
        await db.execute(text("""
            INSERT INTO admin_activity_log (id, type, detail, date)
            VALUES (:id, 'CREATE', :detail, CURRENT_TIMESTAMP)
        """), {
            "id": str(uuid.uuid4())[:8],
            "detail": f"Ingested Nambiyur Taluk (33 villages), 14 Development Blocks, and 21 Intake Channels into Master System."
        })
        await db.commit()

        # Verification statistics
        total_locs = (await db.execute(text("SELECT COUNT(*) FROM master_locations"))).scalar_one()
        nam_count = (await db.execute(text("SELECT COUNT(*) FROM master_locations WHERE taluk_name_en = 'Nambiyur'"))).scalar_one()
        taluks = (await db.execute(text("SELECT DISTINCT taluk_name_en FROM master_locations ORDER BY taluk_name_en"))).scalars().all()
        blocks = (await db.execute(text("SELECT DISTINCT block_name_en FROM master_locations WHERE block_name_en IS NOT NULL ORDER BY block_name_en"))).scalars().all()

        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION SUCCESSFUL")
        logger.info(f"Total Locations in DB: {total_locs}")
        logger.info(f"Nambiyur entities in DB: {nam_count}")
        logger.info(f"Total Taluks ({len(taluks)}): {taluks}")
        logger.info(f"Total Blocks ({len(blocks)}): {blocks}")
        logger.info(f"Total Intake Channels: {ch_count}")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
