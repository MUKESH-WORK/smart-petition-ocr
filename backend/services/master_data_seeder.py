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
    },
    {
        "division_name_en": "Gobichettipalayam Division",
        "division_name_tamil": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_name_en": "Nambiyur",
        "taluk_name_tamil": "நம்பியூர்",
        "sub_departments": "Revenue Administration, Agricultural Extension, Rural Development",
        "local_body_type": "Nambiyur Selection Grade Town Panchayat & Rural Village Panchayats",
        "firkas": [
            ("Nambiyur", "நம்பியூர்"),
            ("Kadathur", "கடத்தூர்"),
            ("Kosanam", "கோசணம்")
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

        # 4. 60 Corporation Wards of Erode City Municipal Corporation
        corporation_wards_data = [
            # Zone 1 (Suriyampalayam) Wards 1-15
            (1, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 1 (Suriyampalayam North)", "வார்டு 1 (சூரியம்பாளையம் வடக்கு)", "Erode North", "ஈரோடு வடக்கு", "638005", "Suriyampalayam, சூரியம்பாளையம், ஆர்.என்.புதூர், R.N.Pudur"),
            (2, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 2 (Suriyampalayam South)", "வார்டு 2 (சூரியம்பாளையம் தெற்கு)", "Erode North", "ஈரோடு வடக்கு", "638005", "Suriyampalayam, சூரியம்பாளையம்"),
            (3, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 3 (Bhavani Road)", "வார்டு 3 (பவானி ரோடு)", "Erode North", "ஈரோடு வடக்கு", "638005", "Bhavani Road, பவானி ரோடு"),
            (4, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 4 (Chithode Link)", "வார்டு 4 (சித்தோடு இணைப்பு)", "Erode North", "ஈரோடு வடக்கு", "638005", "Chithode Link, சித்தோடு"),
            (5, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 5 (Kalingarayanpalayam)", "வார்டு 5 (காலிங்கராயன்பாளையம்)", "Erode North", "ஈரோடு வடக்கு", "638007", "Kalingarayanpalayam, காலிங்கராயன்பாளையம்"),
            (6, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 6 (Brammana Periya Agraharam)", "வார்டு 6 (பிராமண பெரிய அக்ரஹாரம்)", "Erode North", "ஈரோடு வடக்கு", "638005", "BP Agraharam, பிராமண பெரிய அக்ரஹாரம், பி.பி.அக்ரஹாரம்"),
            (7, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 7 (BP Agraharam Central)", "வார்டு 7 (பி.பி.அக்ரஹாரம் மத்தி)", "Erode North", "ஈரோடு வடக்கு", "638005", "BP Agraharam Central, பி.பி.அக்ரஹாரம்"),
            (8, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 8 (Pallipalayam Road)", "வார்டு 8 (பள்ளிபாளையம் ரோடு)", "Erode North", "ஈரோடு வடக்கு", "638005", "Pallipalayam Road, பள்ளிபாளையம் ரோடு, காவிரி கரை"),
            (9, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 9 (Vairapalayam)", "வார்டு 9 (வைரப்பாளையம்)", "Erode North", "ஈரோடு வடக்கு", "638003", "Vairapalayam, வைரப்பாளையம்"),
            (10, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 10 (Cauvery Nagar)", "வார்டு 10 (காவேரி நகர்)", "Erode North", "ஈரோடு வடக்கு", "638003", "Cauvery Nagar, காவேரி நகர்"),
            (11, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 11 (Karungalpalayam North)", "வார்டு 11 (கருங்கல்பாளையம் வடக்கு)", "Erode North", "ஈரோடு வடக்கு", "638003", "Karungalpalayam North, கருங்கல்பாளையம்"),
            (12, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 12 (Karungalpalayam Central)", "வார்டு 12 (கருங்கல்பாளையம் மத்தி)", "Erode North", "ஈரோடு வடக்கு", "638003", "Karungalpalayam Central, கருங்கல்பாளையம்"),
            (13, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 13 (Kamaraj Nagar)", "வார்டு 13 (காமராஜ் நகர்)", "Erode North", "ஈரோடு வடக்கு", "638003", "Kamaraj Nagar, காமராஜ் நகர்"),
            (14, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 14 (Krishna Talkies Road)", "வார்டு 14 (கிருஷ்ணா டாக்கீஸ் ரோடு)", "Erode North", "ஈரோடு வடக்கு", "638001", "Krishna Talkies Road, பஜார், கிருஷ்ணா டாக்கீஸ் ரோடு மற்றும் பஜார் பகுதி"),
            (15, "Zone 1 (Suriyampalayam HQ)", "மண்டலம் 1 (சூரியம்பாளையம்)", "Ward 15 (Netaji Road)", "வார்டு 15 (நேதாஜி ரோடு)", "Erode North", "ஈரோடு வடக்கு", "638001", "Netaji Road, நேதாஜி ரோடு, மணிக்கூண்டு"),
            # Zone 2 (Periyasemur) Wards 16-30
            (16, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 16 (Periyasemur North)", "வார்டு 16 (பெரியசேமூர் வடக்கு)", "Erode West", "ஈரோடு மேற்கு", "638004", "Periyasemur, பெரியசேமூர்"),
            (17, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 17 (Periyasemur Central)", "வார்டு 17 (பெரியசேமூர் மத்தி)", "Erode West", "ஈரோடு மேற்கு", "638004", "Periyasemur Central, பெரியசேமூர்"),
            (18, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 18 (Veerappanchatram North)", "வார்டு 18 (வீரப்பன்சத்திரம் வடக்கு)", "Erode West", "ஈரோடு மேற்கு", "638004", "Veerappanchatram, வீரப்பன்சத்திரம்"),
            (19, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 19 (Veerappanchatram Central)", "வார்டு 19 (வீரப்பன்சத்திரம் மத்தி)", "Erode West", "ஈரோடு மேற்கு", "638004", "Veerappanchatram Central, வீரப்பன்சத்திரம்"),
            (20, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 20 (Veerappanchatram South)", "வார்டு 20 (வீரப்பன்சத்திரம் தெற்கு)", "Erode West", "ஈரோடு மேற்கு", "638004", "Veerappanchatram South, வீரப்பன்சத்திரம்"),
            (21, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 21 (Manickampalayam Housing Board)", "வார்டு 21 (மணிக்கம்பாளையம் ஹவுசிங் போர்டு)", "Erode West", "ஈரோடு மேற்கு", "638011", "Manickampalayam Housing Board Colony, மணிக்கம்பாளையம் ஹவுசிங் போர்டு காலனி"),
            (22, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 22 (Manickampalayam Central)", "வார்டு 22 (மணிக்கம்பாளையம் மத்தி)", "Erode West", "ஈரோடு மேற்கு", "638011", "Manickampalayam, மணிக்கம்பாளையம்"),
            (23, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 23 (Kumalan Kuttai)", "வார்டு 23 (குமலன் குட்டை)", "Erode West", "ஈரோடு மேற்கு", "638011", "Kumalan Kuttai, குமலன் குட்டை"),
            (24, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 24 (Sampath Nagar)", "வார்டு 24 (சம்பத் நகர்)", "Erode West", "ஈரோடு மேற்கு", "638011", "Sampath Nagar and Collectorate Complex, சம்பத் நகர் மற்றும் கலெக்டரேட் வளாகம், ஆட்சியர் அலுவலகம்"),
            (25, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 25 (Gandhiji Road)", "வார்டு 25 (காந்திஜி ரோடு)", "Erode West", "ஈரோடு மேற்கு", "638001", "Gandhiji Road, காந்திஜி ரோடு"),
            (26, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 26 (Mettur Road)", "வார்டு 26 (மேட்டூர் ரோடு)", "Erode West", "ஈரோடு மேற்கு", "638011", "Mettur Road, மேட்டூர் ரோடு, பஸ் நிலையம்"),
            (27, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 27 (Sathy Road North)", "வார்டு 27 (சத்தி ரோடு வடக்கு)", "Erode West", "ஈரோடு மேற்கு", "638004", "Sathy Road, சத்தி ரோடு"),
            (28, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 28 (Sathy Road South)", "வார்டு 28 (சத்தி ரோடு தெற்கு)", "Erode West", "ஈரோடு மேற்கு", "638004", "Sathy Road South, சத்தி ரோடு"),
            (29, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 29 (Marapalam East)", "வார்டு 29 (மரப்பாலம் கிழக்கு)", "Erode West", "ஈரோடு மேற்கு", "638001", "Marapalam East, மரப்பாலம் கிழக்கு, மரப்பாலம் கிழக்கு பகுதி"),
            (30, "Zone 2 (Periyasemur HQ)", "மண்டலம் 2 (பெரியசேமூர்)", "Ward 30 (Marapalam West)", "வார்டு 30 (மரப்பாலம் மேற்கு)", "Erode West", "ஈரோடு மேற்கு", "638001", "Marapalam West, மரப்பாலம் மேற்கு"),
            # Zone 3 (Surampatti) Wards 31-45
            (31, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 31 (Surampatti Valasu North)", "வார்டு 31 (சூரம்பட்டி வலசு வடக்கு)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Surampatti Valasu North, சூரம்பட்டி வலசு"),
            (32, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 32 (Surampatti Valasu West)", "வார்டு 32 (சூரம்பட்டி வலசு மேற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Surampatti Valasu West, பாரதி வீதி, சூரம்பட்டி வலசு மேற்கு"),
            (33, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 33 (Surampatti Central)", "வார்டு 33 (சூரம்பட்டி மத்தி)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Surampatti Central, சூரம்பட்டி"),
            (34, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 34 (Surampatti South)", "வார்டு 34 (சூரம்பட்டி தெற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Surampatti South, சூரம்பட்டி"),
            (35, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 35 (Sengodampalayam)", "வார்டு 35 (செங்கோடம்பாளையம்)", "Erode East", "ஈரோடு கிழக்கு", "638012", "Sengodampalayam, செங்கோடம்பாளையம்"),
            (36, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 36 (Thindal West)", "வார்டு 36 (திண்டல் மேற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638012", "Thindal West, திண்டல் மேற்கு, திண்டல் மலை"),
            (37, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 37 (Periyar Nagar Central & Park Road)", "வார்டு 37 (பெரியார் நகர் மத்தி மற்றும் பார்க் ரோடு)", "Erode East", "ஈரோடு கிழக்கு", "638001", "Periyar Nagar, Park Road, பார்க் ரோடு, பெரியார் நகர், பெரியார் நகர் மத்தி மற்றும் பார்க் ரோடு, ஈரோடு மாநகராட்சி"),
            (38, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 38 (Periyar Nagar South)", "வார்டு 38 (பெரியார் நகர் தெற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638001", "Periyar Nagar South, பெரியார் நகர் தெற்கு"),
            (39, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 39 (Railway Colony North)", "வார்டு 39 (ரயில்வே காலனி வடக்கு)", "Erode East", "ஈரோடு கிழக்கு", "638002", "Railway Colony, ரயில்வே காலனி, ரயில் நிலையம்"),
            (40, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 40 (Railway Colony South)", "வார்டு 40 (ரயில்வே காலனி தெற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638002", "Railway Colony South, ரயில்வே காலனி"),
            (41, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 41 (Chennimalai Road)", "வார்டு 41 (சென்னிமலை ரோடு)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Chennimalai Road, சென்னிமலை ரோடு, ரங்கம்பாளையம்"),
            (42, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 42 (Rangampalayam Central)", "வார்டு 42 (ரங்கம்பாளையம் மத்தி)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Rangampalayam, ரங்கம்பாளையம்"),
            (43, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 43 (Rangampalayam South)", "வார்டு 43 (ரங்கம்பாளையம் தெற்கு)", "Erode East", "ஈரோடு கிழக்கு", "638009", "Rangampalayam South, ரங்கம்பாளையம்"),
            (44, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 44 (Shastri Nagar)", "வார்டு 44 (சாஸ்திரி நகர்)", "Erode East", "ஈரோடு கிழக்கு", "638002", "Shastri Nagar, சாஸ்திரி நகர்"),
            (45, "Zone 3 (Surampatti HQ)", "மண்டலம் 3 (சூரம்பட்டி)", "Ward 45 (Solar Bypass)", "வார்டு 45 (சோலார் பைபாஸ்)", "Erode East", "ஈரோடு கிழக்கு", "638002", "Solar Bypass, சோலார்"),
            # Zone 4 (Kasipalayam) Wards 46-60
            (46, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 46 (Kasipalayam North)", "வார்டு 46 (காசிபாளையம் வடக்கு)", "Erode South", "ஈரோடு தெற்கு", "638009", "Kasipalayam North, காசிபாளையம்"),
            (47, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 47 (Kasipalayam Central)", "வார்டு 47 (காசிபாளையம் மத்தி)", "Erode South", "ஈரோடு தெற்கு", "638009", "Kasipalayam Central, காசிபாளையம்"),
            (48, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 48 (Kasipalayam South)", "வார்டு 48 (காசிபாளையம் தெற்கு)", "Erode South", "ஈரோடு தெற்கு", "638009", "Kasipalayam South, காசிபாளையம்"),
            (49, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 49 (Moolapalayam North)", "வார்டு 49 (மூலப்பாளையம் வடக்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Moolapalayam North, மூலப்பாளையம்"),
            (50, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 50 (Moolapalayam Central)", "வார்டு 50 (மூலப்பாளையம் மத்தி)", "Erode South", "ஈரோடு தெற்கு", "638002", "Moolapalayam Central, மூலப்பாளையம்"),
            (51, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 51 (Moolapalayam South)", "வார்டு 51 (மூலப்பாளையம் தெற்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Moolapalayam South, மூலப்பாளையம்"),
            (52, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 52 (Nochipalayam & Solar Bus Stand)", "வார்டு 52 (நொச்சிப்பாளையம் மற்றும் சோலார் புதிய பேருந்து நிலையம்)", "Erode South", "ஈரோடு தெற்கு", "638002", "Nochipalayam, Solar New Bus Stand, நொச்சிப்பாளையம் மற்றும் சோலார் புதிய பேருந்து நிலையம் ரோடு"),
            (53, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 53 (Solar Central)", "வார்டு 53 (சோலார் மத்தி)", "Erode South", "ஈரோடு தெற்கு", "638002", "Solar Central, சோலார்"),
            (54, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 54 (Solar South)", "வார்டு 54 (சோலார் தெற்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Solar South, சோலார்"),
            (55, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 55 (Lakkapuram North)", "வார்டு 55 (லக்காபுரம் வடக்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Lakkapuram North, லக்காபுரம்"),
            (56, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 56 (Lakkapuram South)", "வார்டு 56 (லக்காபுரம் தெற்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Lakkapuram South, லக்காபுரம்"),
            (57, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 57 (Kollampalayam North)", "வார்டு 57 (கொல்லம்பாளையம் வடக்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Kollampalayam North, கொல்லம்பாளையம்"),
            (58, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 58 (Kollampalayam Central)", "வார்டு 58 (கொல்லம்பாளையம் மத்தி)", "Erode South", "ஈரோடு தெற்கு", "638002", "Kollampalayam Central, கொல்லம்பாளையம்"),
            (59, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 59 (Kollampalayam South)", "வார்டு 59 (கொல்லம்பாளையம் தெற்கு)", "Erode South", "ஈரோடு தெற்கு", "638002", "Kollampalayam South, கொல்லம்பாளையம்"),
            (60, "Zone 4 (Kasipalayam HQ)", "மண்டலம் 4 (காசிபாளையம்)", "Ward 60 (Vendipalayam)", "வார்டு 60 (வெண்டிபாளையம்)", "Erode South", "ஈரோடு தெற்கு", "638002", "Vendipalayam, வெண்டிபாளையம், ரயில்வே கேட்")
        ]

        for w_no, z_en, z_ta, w_en, w_ta, f_en, f_ta, pin, extra_kws in corporation_wards_data:
            stext = f"District Erode ஈரோடு Taluk Erode ஈரோடு Firka {f_en} {f_ta} Zone {z_en} {z_ta} Ward {w_no} வார்டு {w_no} {w_en} {w_ta} Pincode {pin} {extra_kws}"
            records.append({
                "div_en": "Erode Division", "div_ta": "ஈரோடு வருவாய் கோட்டம்",
                "taluk_en": "Erode", "taluk_ta": "ஈரோடு",
                "firka_en": f_en, "firka_ta": f_ta,
                "sub_depts": "Erode City Municipal Corporation", "local_body": "Ward",
                "ward_no": w_no, "ward_name_en": w_en, "ward_name_ta": w_ta,
                "village_code": None, "village_name_en": None, "village_name_ta": None,
                "pincode": pin, "search_text": stext
            })

        # 5. Authentic Revenue Villages across all 9 Taluks
        authentic_villages_by_taluk = [
            ("Sathyamangalam", "சத்தியமங்கலம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Ukkaram", "உக்கரம்", "Sathyamangalam", "சத்தியமங்கலம்", "638402", "உக்கரம் கிராமம் ukkaram village main road"),
                ("Vandipalayam", "வண்டிபாளையம்", "Sathyamangalam", "சத்தியமங்கலம்", "638401", "வண்டிபாளையம் vandipalayam"),
                ("Bhavanisagar", "பவானிசாகர்", "Bhavanisagar", "பவானிசாகர்", "638451", "பவானிசாகர் அணை bhavanisagar dam"),
                ("Punjai Puliyampatti", "புஞ்சை புளியம்பட்டி", "Punjai Puliyampatti", "புஞ்சை புளியம்பட்டி", "638459", "புளியம்பட்டி puliyampatti"),
                ("Arasur", "அரசூர்", "Arasur", "அரசூர்", "638454", "அரசூர் arasur"),
                ("Gudhiyalathur", "குத்தியாலத்தூர்", "Gudhiyalathur", "குத்தியாலத்தூர்", "638503", "குத்தியாலத்தூர் மலை gudhiyalathur hill"),
                ("Shenbagapudur", "செண்பகபுதூர்", "Sathyamangalam", "சத்தியமங்கலம்", "638402", "செண்பகபுதூர் shenbagapudur"),
                ("Ikkarai Negamam", "இக்கர Negamam", "Sathyamangalam", "சத்தியமங்கலம்", "638401", "இக்கர நெகமம்"),
            ]),
            ("Bhavani", "பவானி", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Vellode", "வெள்ளோடு", "Bhavani", "பவானி", "638302", "வெள்ளோடு காளியம்மன் கோவில் தெரு vellode"),
                ("Kavindapadi", "கவுந்தப்பாடி", "Kavindapadi", "கவுந்தப்பாடி", "638455", "கவுந்தப்பாடி சர்க்கரை kavindapadi"),
                ("Kurichi", "குறிச்சி", "Kurichi", "குறிச்சி", "638314", "குறிச்சி kurichi"),
                ("Appakudal", "ஆப்பக்கூடல்", "Bhavani", "பவானி", "638315", "ஆப்பக்கூடல் appakudal"),
                ("Mylambadi", "மைலம்பாடி", "Bhavani", "பவானி", "638314", "மைலம்பாடி mylambadi"),
                ("Periyapuliyur", "பெரியபுலியூர்", "Bhavani", "பவானி", "638455", "பெரியபுலியூர் periyapuliyur"),
            ]),
            ("Perundurai", "பெருந்துறை", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", [
                ("Chennimalai", "சென்னிமலை", "Chennimalai", "சென்னிமலை", "638051", "சென்னிமலை முருகன் கோவில் chennimalai"),
                ("Kanjikoil", "காஞ்சிக்கோவில்", "Kanjikoil", "காஞ்சிக்கோவில்", "638116", "காஞ்சிக்கோவில் kanjikoil"),
                ("Perundurai Rural", "பெருந்துறை ஊரகம்", "Perundurai", "பெருந்துறை", "638052", "சிப்காட் sipcot industrial"),
                ("Thingalore", "திங்களூர்", "Thingalore", "திங்களூர்", "638055", "திங்களூர் thingalore"),
                ("Vellode Perundurai", "வெள்ளோடு பெருந்துறை", "Vellodu", "வெள்ளோடு", "638112", "வெள்ளோடு பறவைகள் சரணாலயம் vellode bird sanctuary"),
                ("Vijayamangalam", "விஜயமங்கலம்", "Perundurai", "பெருந்துறை", "638056", "விஜயமங்கலம் vijayamangalam toll"),
            ]),
            ("Gobichettipalayam", "கோபிசெட்டிபாளையம்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Kasipalayam Gobi", "காசிபாளையம் (கோபி)", "Kasipalayam", "காசிபாளையம் (கோபி)", "638454", "காசிபாளையம் kasipalayam"),
                ("Kugalur", "கூகலூர்", "Kugalur", "கூகலூர்", "638313", "கூகலூர் வாய்க்கால் kugalur"),
                ("Siruvalur", "சிறுவலூர்", "Siruvalur", "சிறுவலூர்", "638054", "சிறுவலூர் siruvalur"),
                ("Vaniputhur", "வாணிபுத்தூர்", "Vaniputhur", "வாணிபுத்தூர்", "638506", "வாணிபுத்தூர் vaniputhur"),
                ("Lakkampatti", "லக்கம்பட்டி", "Gobichettipalayam", "கோபிசெட்டிபாளையம்", "638313", "லக்கம்பட்டி lakkampatti"),
            ]),
            ("Anthiyur", "அந்தியூர்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Ammapettai", "அம்மாபேட்டை", "Ammapettai", "அம்மாபேட்டை", "638311", "அம்மாபேட்டை ammapettai"),
                ("Anthiyur Rural", "அந்தியூர் ஊரகம்", "Anthiyur", "அந்தியூர்", "638501", "அந்தியூர் குதிரை சந்தை anthiyur"),
                ("Athani", "ஆத்தானி", "Athani", "ஆப்பக்கூடல் / ஆத்தானி", "638502", "ஆத்தானி athani"),
                ("Bargur", "பர்கூர்", "Bargur", "பர்கூர்", "638501", "பர்கூர் மலை bargur hills"),
            ]),
            ("Kodumudi", "கொடுமுடி", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", [
                ("Kilambadi", "கீழம்பாடி", "Kilambadi", "கீழம்பாடி", "638151", "கீழம்பாடி kilambadi"),
                ("Kodumudi Rural", "கொடுமுடி ஊரகம்", "Kodumudi", "கொடுமுடி", "638151", "கொடுமுடி மகுடேஸ்வரர் kodumudi"),
                ("Sivagiri", "சிவகிரி", "Sivagiri", "சிவகிரி", "638109", "சிவகிரி sivagiri"),
            ]),
            ("Modakkurichi", "மொடக்குறிச்சி", "Erode Division", "ஈரோடு வருவாய் கோட்டம்", [
                ("Arachalur", "அரச்சலூர்", "Arachalur", "அரச்சலூர்", "638101", "அரச்சலூர் சமணர் மலை arachalur"),
                ("Modakkurichi Rural", "மொடக்குறிச்சி ஊரகம்", "Modakkurichi", "மொடக்குறிச்சி", "638104", "மொடக்குறிச்சி modakkurichi"),
                ("Poondurai", "பூந்துறை", "Poondurai", "பூந்துறை", "638115", "எழுமாத்தூர் பூந்துறை poondurai"),
            ]),
            ("Thalavadi", "தாளவாடி", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Thalavadi Central", "தாளவாடி மத்தி", "Thalavadi", "தாளவாடி", "638461", "தாளவாடி மலைப்பகுதி thalavadi"),
                ("Hassanur", "ஆசனூர்", "Thalavadi", "தாளவாடி", "638461", "ஆசனூர் hassanur ghat"),
            ]),
            ("Nambiyur", "நம்பியூர்", "Gobichettipalayam Division", "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்", [
                ("Nambiyur Central", "நம்பியூர் மத்தி", "Nambiyur", "நம்பியூர்", "638458", "நம்பியூர் nambiyur"),
                ("Kadathur", "கடத்தூர்", "Kadathur", "கடத்தூர்", "638454", "கடத்தூர் காளிங்கராயன் kadathur"),
                ("Kosanam", "கோசணம்", "Kosanam", "கோசணம்", "638458", "கோசணம் kosanam"),
            ]),
        ]

        v_idx = 1
        for t_en, t_ta, div_en, div_ta, vill_list in authentic_villages_by_taluk:
            for v_en, v_ta, f_en, f_ta, pin, extra in vill_list:
                stext = f"District Erode ஈரோடு Division {div_en} {div_ta} Taluk {t_en} {t_ta} Firka {f_en} {f_ta} Revenue Village கிராமம் {v_en} {v_ta} Pincode {pin} {extra}"
                records.append({
                    "div_en": div_en, "div_ta": div_ta,
                    "taluk_en": t_en, "taluk_ta": t_ta,
                    "firka_en": f_en, "firka_ta": f_ta,
                    "sub_depts": "Revenue Administration", "local_body": "Village",
                    "ward_no": None, "ward_name_en": None, "ward_name_ta": None,
                    "village_code": f"{v_idx:04d}", "village_name_en": v_en, "village_name_ta": v_ta,
                    "pincode": pin, "search_text": stext
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

