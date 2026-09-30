import os
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

# Complete authoritative dataset of 486 villages across 10 taluks of Erode District
TALUK_VILLAGES_DATA = {
    "Anthiyur": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "அந்தியூர்",
        "sub_departments": ["Revenue Administration", "Forest & Tribal Welfare", "Rural Development"],
        "local_body": "Anthiyur Selection Grade Town Panchayat & Village Panchayats",
        "firkas": [
            ("Ammapettai", "அம்மாபேட்டை"),
            ("Anthiyur", "அந்தியூர்"),
            ("Athani", "ஆப்பக்கூடல் / ஆத்தானி"),
            ("Bargur", "பர்கூர்")
        ],
        "villages": [
            {"sno": 1, "name": "Ammapettai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 2, "name": "Ammapettai B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 3, "name": "Anthiyur", "category": "Rural", "gp": "Chinnathambipalayam, Michaelpalayam"},
            {"sno": 4, "name": "Anthiyur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 5, "name": "Ariyagoundanur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Athani", "category": "Urban", "gp": "Not applicable"},
            {"sno": 7, "name": "Attavanaipudur", "category": "Rural", "gp": "Attavanaipudur"},
            {"sno": 8, "name": "Bargur", "category": "Rural", "gp": "Burgur, Kuttaiyur"},
            {"sno": 9, "name": "Bargur B", "category": "Rural", "gp": "3 Gram Panchayats"},
            {"sno": 10, "name": "Boothapadi", "category": "Rural", "gp": "Bhootapadi"},
            {"sno": 11, "name": "Brammadesam", "category": "Rural", "gp": "Bramadesam"},
            {"sno": 12, "name": "Burgur (North R.F.)", "category": "Rural", "gp": "3 Gram Panchayats"},
            {"sno": 13, "name": "Burgur South R.F..", "category": "Rural", "gp": "Devarmalai"},
            {"sno": 14, "name": "Chennampatti", "category": "Rural", "gp": "Chennampatti"},
            {"sno": 15, "name": "Ennamangalam", "category": "Rural", "gp": "Ennamangalam"},
            {"sno": 16, "name": "Ennamangalam R.F.", "category": "Rural", "gp": "Ennamangalam"},
            {"sno": 17, "name": "Gettisamudram", "category": "Rural", "gp": "Gettisamudram"},
            {"sno": 18, "name": "Illippili", "category": "Rural", "gp": "Guruvareddiyur"},
            {"sno": 19, "name": "Kannapalli", "category": "Rural", "gp": "Kannapalli"},
            {"sno": 20, "name": "Kilwani", "category": "Rural", "gp": "Keelvani"},
            {"sno": 21, "name": "Komarayanur", "category": "Rural", "gp": "Komarayanur"},
            {"sno": 22, "name": "Kuppandampalayam", "category": "Rural", "gp": "Kuppandampalayam"},
            {"sno": 23, "name": "Kuthampoondi", "category": "Rural", "gp": "Koothampoondi"},
            {"sno": 24, "name": "Mathur", "category": "Rural", "gp": "Mathur"},
            {"sno": 25, "name": "Moongilpatti", "category": "Rural", "gp": "Moongilpatti"},
            {"sno": 26, "name": "Mukasipudur", "category": "Rural", "gp": "Muhasipudur"},
            {"sno": 27, "name": "Nagalur", "category": "Rural", "gp": "Nagalore"},
            {"sno": 28, "name": "Nagalur R.F.", "category": "Rural", "gp": "Nagalore"},
            {"sno": 29, "name": "Nerinjipettai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 30, "name": "Oddapalayam", "category": "Rural", "gp": "Oddapalayam"},
            {"sno": 31, "name": "Pachampalayam", "category": "Rural", "gp": "Pachampalayam"},
            {"sno": 32, "name": "Patlur", "category": "Rural", "gp": "Patlur"},
            {"sno": 33, "name": "Poonachi", "category": "Rural", "gp": "Poonachi"},
            {"sno": 34, "name": "Pudur", "category": "Rural", "gp": "Pudur"},
            {"sno": 35, "name": "Sankarapalayam", "category": "Rural", "gp": "Sankarapalayam"},
            {"sno": 36, "name": "Vellithiruppur", "category": "Rural", "gp": "Vellithiruppur"},
            {"sno": 37, "name": "Vembathi", "category": "Rural", "gp": "Vempathy"},
            {"sno": 38, "name": "Vempathi B", "category": "Rural", "gp": "Vempathy"}
        ]
    },
    "Bhavani": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "பவானி",
        "sub_departments": ["Revenue Administration", "Municipal Administration", "Irrigation & Water Resources"],
        "local_body": "Bhavani Municipality & Rural Village Panchayats",
        "firkas": [
            ("Bhavani", "பவானி"),
            ("Kavindapadi", "கவுந்தப்பாடி"),
            ("Kurichi", "குறிச்சி")
        ],
        "villages": [
            {"sno": 1, "name": "Alathur", "category": "Rural", "gp": "Alathur"},
            {"sno": 2, "name": "Andikulam", "category": "Rural", "gp": "Andikulam"},
            {"sno": 3, "name": "Appakudal", "category": "Urban", "gp": "Not applicable"},
            {"sno": 4, "name": "Bhavani", "category": "Rural", "gp": "Thottipalayam"},
            {"sno": 5, "name": "Bhavani B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Chinnapuliyur", "category": "Rural", "gp": "Chinnapuliyur"},
            {"sno": 7, "name": "Jambai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 8, "name": "Jambai B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 9, "name": "Kadappanallur", "category": "Rural", "gp": "Kadappanallur"},
            {"sno": 10, "name": "Kalpavi", "category": "Rural", "gp": "Kalpavi"},
            {"sno": 11, "name": "Kavandapadi", "category": "Rural", "gp": "Kavandapadi"},
            {"sno": 12, "name": "Kavindapadi B", "category": "Rural", "gp": "Kavandapadi"},
            {"sno": 13, "name": "Kavindapadi C", "category": "Rural", "gp": "Kavandapadi"},
            {"sno": 14, "name": "Kesarimangalam", "category": "Rural", "gp": "Kesarimangalam"},
            {"sno": 15, "name": "Kurichi", "category": "Rural", "gp": "Kurhichi, Manickampalayam"},
            {"sno": 16, "name": "Kurichi B", "category": "Rural", "gp": "Kurhichi"},
            {"sno": 17, "name": "Kuruppanaickenpalayam (Ct)", "category": "Rural", "gp": "Kuruppanaickenpalayam"},
            {"sno": 18, "name": "Mylambadi", "category": "Rural", "gp": "Mylambadi"},
            {"sno": 19, "name": "Odathurai", "category": "Rural", "gp": "Odathurai"},
            {"sno": 20, "name": "Odathurai B", "category": "Rural", "gp": "Odathurai"},
            {"sno": 21, "name": "Olagadam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 22, "name": "Oricheri", "category": "Rural", "gp": "Oricheri"},
            {"sno": 23, "name": "P.Mettupalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 24, "name": "P.Mettupalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 25, "name": "Padavalkalvai", "category": "Rural", "gp": "Padavalkalvai"},
            {"sno": 26, "name": "Paruvachi", "category": "Rural", "gp": "Paruvachi"},
            {"sno": 27, "name": "Periyapuliyur", "category": "Rural", "gp": "Periyapuliyur"},
            {"sno": 28, "name": "Perundalaiyur", "category": "Rural", "gp": "Perunthaliyur"},
            {"sno": 29, "name": "Punnam", "category": "Rural", "gp": "Punnam"},
            {"sno": 30, "name": "Salangapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 31, "name": "Salangapalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 32, "name": "Salangapalayam C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 33, "name": "Sanyasipatti", "category": "Rural", "gp": "Sanniyasipatti"},
            {"sno": 34, "name": "Settipalayam", "category": "Rural", "gp": "Periyapuliyur"},
            {"sno": 35, "name": "Singampettai", "category": "Rural", "gp": "Singampettai"},
            {"sno": 36, "name": "Thalakulam", "category": "Rural", "gp": "Varadhanallur"},
            {"sno": 37, "name": "Thamarakkarai R.F.", "category": "Rural", "gp": "Thamarakarai"},
            {"sno": 38, "name": "Urachikottai", "category": "Rural", "gp": "Kuruppanaickenpalayam"},
            {"sno": 39, "name": "Varadanallur", "category": "Rural", "gp": "Varadhanallur"},
            {"sno": 40, "name": "Vyramangalam", "category": "Rural", "gp": "Vairamangalam"}
        ]
    },
    "Erode": {
        "division": "Erode Division",
        "division_ta": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_ta": "ஈரோடு",
        "sub_departments": ["District Collectorate HQ", "Municipal Administration (Corporation)", "Revenue & Land Administration"],
        "local_body": "Erode City Municipal Corporation & Town Panchayats",
        "firkas": [
            ("Erode East", "ஈரோடு கிழக்கு"),
            ("Erode North", "ஈரோடு வடக்கு"),
            ("Erode South", "ஈரோடு தெற்கு"),
            ("Erode West", "ஈரோடு மேற்கு")
        ],
        "villages": [
            {"sno": 1, "name": "Anainasuvampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 2, "name": "Attayampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 3, "name": "B S Agraharam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 4, "name": "B.P.Agraharam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 5, "name": "Chithode", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Elavamalai", "category": "Rural", "gp": "Elavamalai"},
            {"sno": 7, "name": "Ellapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 8, "name": "Erode", "category": "Urban", "gp": "Not applicable"},
            {"sno": 9, "name": "Erode B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 10, "name": "Erode C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 11, "name": "Gangapuram", "category": "Urban", "gp": "Not applicable"},
            {"sno": 12, "name": "Gangapuram B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 13, "name": "Kadirampatti", "category": "Rural", "gp": "Kadhirampatty"},
            {"sno": 14, "name": "Karai Ellapalayam", "category": "Rural", "gp": "Elavamalai"},
            {"sno": 15, "name": "Koorapalayam", "category": "Rural", "gp": "Koorapalayam"},
            {"sno": 16, "name": "Kumilamparappu", "category": "Urban", "gp": "Not applicable"},
            {"sno": 17, "name": "Mettunasuvanpalayam (Ct)", "category": "Rural", "gp": "Mettunasuvampalayam"},
            {"sno": 18, "name": "Moolakarai", "category": "Rural", "gp": "Koorapalayam"},
            {"sno": 19, "name": "Muthampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 20, "name": "Muthampalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 21, "name": "Nallagoundampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 22, "name": "Nanjai Thalavaipalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 23, "name": "Nanjanapuram", "category": "Rural", "gp": "Kadhirampatty"},
            {"sno": 24, "name": "Nasiyanur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 25, "name": "Nasiyanur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 26, "name": "Nochipalayam", "category": "Rural", "gp": "Perode"},
            {"sno": 27, "name": "Pavalathampalayam", "category": "Rural", "gp": "Kadhirampatty"},
            {"sno": 28, "name": "Peelamedu", "category": "Urban", "gp": "Not applicable"},
            {"sno": 29, "name": "Periyasemur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 30, "name": "Periyasemur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 31, "name": "Perodu", "category": "Rural", "gp": "Perode"},
            {"sno": 32, "name": "Puthur Pudupalayam", "category": "Rural", "gp": "Pitchandampalayam"},
            {"sno": 33, "name": "Rayapalayam", "category": "Rural", "gp": "Koorapalayam"},
            {"sno": 34, "name": "Samigoundenpalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 35, "name": "Sarcar Chinna Agraharam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 36, "name": "Sarcar Periya Agraharam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 37, "name": "Surampatti", "category": "Urban", "gp": "Not applicable"},
            {"sno": 38, "name": "Suriyampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 39, "name": "Suriyampalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 40, "name": "Thairpalayam", "category": "Rural", "gp": "Perode"},
            {"sno": 41, "name": "Thindal (Ct)", "category": "Urban", "gp": "Not applicable"},
            {"sno": 42, "name": "Thindal M", "category": "Urban", "gp": "Not applicable"},
            {"sno": 43, "name": "Thindal V", "category": "Urban", "gp": "Not applicable"},
            {"sno": 44, "name": "Thottani", "category": "Rural", "gp": "Koorapalayam"},
            {"sno": 45, "name": "Vairapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 46, "name": "Vendipalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 47, "name": "Veppampalayam", "category": "Rural", "gp": "Pitchandampalayam"},
            {"sno": 48, "name": "Vettaiperiyapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 49, "name": "Villarasampatti", "category": "Urban", "gp": "Not applicable"},
            {"sno": 50, "name": "Villarasampatti B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 51, "name": "Villarasampatti C", "category": "Urban", "gp": "Not applicable"}
        ]
    },
    "Gobichettipalayam": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "கோபிசெட்டிபாளையம்",
        "sub_departments": ["Revenue Administration", "Agricultural Extension & Sericulture", "Rural Development"],
        "local_body": "Gobichettipalayam Municipality & Town Panchayats",
        "firkas": [
            ("Gobichettipalayam", "கோபிசெட்டிபாளையம்"),
            ("Kasipalayam", "காசிபாளையம் (கோபி)"),
            ("Kugalur", "கூகலூர்"),
            ("Siruvalur", "சிறுவலூர்"),
            ("Vaniputhur", "வாணிபுத்தூர்")
        ],
        "villages": [
            {"sno": 1, "name": "Agraharakarai", "category": "Rural", "gp": "Pariyur"},
            {"sno": 2, "name": "Akkaraikodiveri", "category": "Rural", "gp": "Akkaraikodivery"},
            {"sno": 3, "name": "Alukuli", "category": "Rural", "gp": "Alukkuli"},
            {"sno": 4, "name": "Alukuzhi B", "category": "Rural", "gp": "Alukkuli"},
            {"sno": 5, "name": "Ammapalayam", "category": "Rural", "gp": "Ammapalayam"},
            {"sno": 6, "name": "Arakkankottaikarai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 7, "name": "Arrakkankottaigramam", "category": "Rural", "gp": "Arakkankottai"},
            {"sno": 8, "name": "Ayalur", "category": "Rural", "gp": "Ayalur"},
            {"sno": 9, "name": "Bodichinnampalayam", "category": "Rural", "gp": "Alukkuli"},
            {"sno": 10, "name": "Chandrapuram", "category": "Rural", "gp": "Chandrapuram"},
            {"sno": 11, "name": "Chenrayampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 12, "name": "Chinnakodiveri", "category": "Urban", "gp": "Not applicable"},
            {"sno": 13, "name": "Kadukkampalayam", "category": "Rural", "gp": "Kadukkampalayam"},
            {"sno": 14, "name": "Kalingiyam", "category": "Rural", "gp": "Kalingiyam"},
            {"sno": 15, "name": "Kalingiyam B", "category": "Rural", "gp": "Kalingiyam"},
            {"sno": 16, "name": "Kanakampalayam", "category": "Rural", "gp": "Kanakkampalayam"},
            {"sno": 17, "name": "Kavandampalayam", "category": "Rural", "gp": "Kongarpalayam"},
            {"sno": 18, "name": "Kolappalur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 19, "name": "Kondayampalayam", "category": "Rural", "gp": "Kondayampalayam"},
            {"sno": 20, "name": "Kongarpalayam", "category": "Rural", "gp": "Kongarpalayam"},
            {"sno": 21, "name": "Konkara Palayam B", "category": "Rural", "gp": "Kongarpalayam"},
            {"sno": 22, "name": "Kottupullampalayam", "category": "Rural", "gp": "Kottupullampalayam"},
            {"sno": 23, "name": "Kugalur", "category": "Rural", "gp": "Bommanaickenpalayam"},
            {"sno": 24, "name": "Kugalur B", "category": "Rural", "gp": "Bommanaickenpalayam"},
            {"sno": 25, "name": "Kugalur C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 26, "name": "Kullampalayam", "category": "Rural", "gp": "Kullampalayam"},
            {"sno": 27, "name": "Lakkampatti", "category": "Urban", "gp": "Not applicable"},
            {"sno": 28, "name": "Mevani", "category": "Rural", "gp": "Mevani"},
            {"sno": 29, "name": "Modachur", "category": "Rural", "gp": "Modachur"},
            {"sno": 30, "name": "Nagadevampalayam", "category": "Rural", "gp": "Nagadevampalayam"},
            {"sno": 31, "name": "Nagadevampalayam B", "category": "Rural", "gp": "Nagadevampalayam"},
            {"sno": 32, "name": "Nanjaigopi", "category": "Rural", "gp": "Nanjai Gobi"},
            {"sno": 33, "name": "Nanjaipuliampatti", "category": "Rural", "gp": "Nanjaipuliampatty"},
            {"sno": 34, "name": "Nanjaithuraiampalayam", "category": "Rural", "gp": "Punjaithuraiyampalayam"},
            {"sno": 35, "name": "Nathipalayam", "category": "Rural", "gp": "Nathipalayam"},
            {"sno": 36, "name": "Odayagoundanpalayam", "category": "Rural", "gp": "Odayagoundenpalayam"},
            {"sno": 37, "name": "Palayapariyurkarai", "category": "Rural", "gp": "Pariyur"},
            {"sno": 38, "name": "Pariyur", "category": "Rural", "gp": "Pariyur"},
            {"sno": 39, "name": "Periyakodiveri", "category": "Urban", "gp": "Not applicable"},
            {"sno": 40, "name": "Perumugai", "category": "Rural", "gp": "Perumugai"},
            {"sno": 41, "name": "Perumugai B", "category": "Rural", "gp": "Perumugai"},
            {"sno": 42, "name": "Pettaikarai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 43, "name": "Pulavakalipalayam", "category": "Rural", "gp": "Polavakkalipalayam"},
            {"sno": 44, "name": "Pullappanaickenpalayam", "category": "Rural", "gp": "Pullappanaickenpalayam"},
            {"sno": 45, "name": "Punjaithuraipalayam", "category": "Rural", "gp": "Punjaithuraiyampalayam"},
            {"sno": 46, "name": "Punjaithuraiyampalayam B", "category": "Rural", "gp": "Punjaithuraiyampalayam"},
            {"sno": 47, "name": "Puthukkarai", "category": "Rural", "gp": "Nanjai Gobi"},
            {"sno": 48, "name": "Savandapur", "category": "Rural", "gp": "Savandappur"},
            {"sno": 49, "name": "Savandapur B", "category": "Rural", "gp": "Savandappur"},
            {"sno": 50, "name": "Senkalarai Karai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 51, "name": "Seyyampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 52, "name": "Singiripalayam", "category": "Rural", "gp": "Akkaraikodivery"},
            {"sno": 53, "name": "Siruvalur", "category": "Rural", "gp": "Siruvalur"},
            {"sno": 54, "name": "Solamadevikarai", "category": "Rural", "gp": "Alukkuli"},
            {"sno": 55, "name": "Thadapalli Gramam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 56, "name": "Thadapallikarai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 57, "name": "Vanipudur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 58, "name": "Vanipudur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 59, "name": "Veerapandi", "category": "Urban", "gp": "Not applicable"},
            {"sno": 60, "name": "Vellalapalayam", "category": "Rural", "gp": "Vellalapalayam"},
            {"sno": 61, "name": "Vellankovil", "category": "Rural", "gp": "Vellankoil"}
        ]
    },
    "Kodumudi": {
        "division": "Erode Division",
        "division_ta": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_ta": "கொடுமுடி",
        "sub_departments": ["Revenue Administration", "Cauvery Delta Agriculture", "Rural Development"],
        "local_body": "Kodumudi Town Panchayat & Rural Village Panchayats",
        "firkas": [
            ("Kilambadi", "கீழம்பாடி"),
            ("Kodumudi", "கொடுமுடி"),
            ("Sivagiri", "சிவகிரி")
        ],
        "villages": [
            {"sno": 1, "name": "Anjur", "category": "Rural", "gp": "Anjur"},
            {"sno": 2, "name": "Anjur B", "category": "Rural", "gp": "Anjur"},
            {"sno": 3, "name": "Avudayaparai", "category": "Rural", "gp": "Avudaiyarparai"},
            {"sno": 4, "name": "Ayyampalayam", "category": "Rural", "gp": "Ayyampalayam"},
            {"sno": 5, "name": "Chennasamudram", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Chennasamudram B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 7, "name": "Devakiammapuram", "category": "Rural", "gp": "Elunoothimangalam"},
            {"sno": 8, "name": "Elunoothimangalam", "category": "Rural", "gp": "Elunoothimangalam"},
            {"sno": 9, "name": "Elunuthimangalam B", "category": "Rural", "gp": "Elunoothimangalam"},
            {"sno": 10, "name": "Ichipalayam", "category": "Rural", "gp": "Ichippalayam"},
            {"sno": 11, "name": "Ichipalayam B", "category": "Rural", "gp": "Ichippalayam"},
            {"sno": 12, "name": "Kodumudi", "category": "Urban", "gp": "Not applicable"},
            {"sno": 13, "name": "Kodumudi B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 14, "name": "Kolathupalayam", "category": "Rural", "gp": "Kolathupalayam"},
            {"sno": 15, "name": "Kolathupalayam B", "category": "Rural", "gp": "Kolathupalayam"},
            {"sno": 16, "name": "Kollankoil", "category": "Urban", "gp": "Not applicable"},
            {"sno": 17, "name": "Kollankoil B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 18, "name": "Kondalam", "category": "Rural", "gp": "Konthalam"},
            {"sno": 19, "name": "Kongudayampalayam", "category": "Rural", "gp": "Kongudaiyampalayam"},
            {"sno": 20, "name": "Konthalam B", "category": "Rural", "gp": "Konthalam"},
            {"sno": 21, "name": "Murungiyampalayam", "category": "Rural", "gp": "Anjur"},
            {"sno": 22, "name": "Nagamanaickenpalayam", "category": "Rural", "gp": "Avudaiyarparai"},
            {"sno": 23, "name": "Nanjaikilampadi", "category": "Urban", "gp": "Not applicable"},
            {"sno": 24, "name": "Nanjaikolanalli", "category": "Rural", "gp": "N.Kolanalli"},
            {"sno": 25, "name": "Pasur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 26, "name": "Punjai Kilampadi", "category": "Urban", "gp": "Not applicable"},
            {"sno": 27, "name": "Punjai Kilampadi B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 28, "name": "Punjaikolanalli", "category": "Urban", "gp": "Not applicable"},
            {"sno": 29, "name": "Punjaikolanalli B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 30, "name": "Sivagiri", "category": "Urban", "gp": "Not applicable"},
            {"sno": 31, "name": "Sivagiri B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 32, "name": "Sivagiri C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 33, "name": "Unjalur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 34, "name": "Vadivullamangalam", "category": "Rural", "gp": "Ayyampalayam"},
            {"sno": 35, "name": "Vallipuram", "category": "Rural", "gp": "Vallipuram"},
            {"sno": 36, "name": "Venkambur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 37, "name": "Venkambur B", "category": "Urban", "gp": "Not applicable"}
        ]
    },
    "Modakkurichi": {
        "division": "Erode Division",
        "division_ta": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_ta": "மொடக்குறிச்சி",
        "sub_departments": ["Revenue Administration", "Canal Irrigation & Agriculture", "Rural Development"],
        "local_body": "Modakkurichi Town Panchayat & Village Panchayats",
        "firkas": [
            ("Arachalur", "அரச்சலூர்"),
            ("Modakkurichi", "மொடக்குறிச்சி"),
            ("Poondurai", "பூந்துறை")
        ],
        "villages": [
            {"sno": 1, "name": "Arachalur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 2, "name": "Arachalur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 3, "name": "Arachalur C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 4, "name": "Attavanai Anumanpalli B", "category": "Rural", "gp": "Attavanai Anumanpalli"},
            {"sno": 5, "name": "Attavanai Hanuman Palli", "category": "Rural", "gp": "Attavanai Anumanpalli"},
            {"sno": 6, "name": "Aval Poondurai B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 7, "name": "Aval Poondurai C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 8, "name": "Avalpoondurai", "category": "Rural", "gp": "Kulur"},
            {"sno": 9, "name": "Ellaikadai", "category": "Rural", "gp": "Villakkethy"},
            {"sno": 10, "name": "Elumathur", "category": "Rural", "gp": "Anandampalayam, Elumathur"},
            {"sno": 11, "name": "Elumathur B", "category": "Rural", "gp": "Elumathur"},
            {"sno": 12, "name": "Injampalli", "category": "Rural", "gp": "Enjampalli"},
            {"sno": 13, "name": "Injampalli B", "category": "Rural", "gp": "Enjampalli"},
            {"sno": 14, "name": "Kagam", "category": "Rural", "gp": "Kagam"},
            {"sno": 15, "name": "Kanagapuram", "category": "Rural", "gp": "Kanagapuram"},
            {"sno": 16, "name": "Kanagapuram B", "category": "Rural", "gp": "Kanagapuram"},
            {"sno": 17, "name": "Kangayampalayam", "category": "Rural", "gp": "Nanjai Uthukuli"},
            {"sno": 18, "name": "Kaspapettai B", "category": "Rural", "gp": "Modavandi Sathiyamangalam"},
            {"sno": 19, "name": "Kulavilakku", "category": "Rural", "gp": "Kulavilakku"},
            {"sno": 20, "name": "Kulavilakku B", "category": "Rural", "gp": "Kulavilakku"},
            {"sno": 21, "name": "Kurukkapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 22, "name": "Modakkurichi", "category": "Urban", "gp": "Not applicable"},
            {"sno": 23, "name": "Modakkurichi B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 24, "name": "Modavandi Sathyamangalam", "category": "Rural", "gp": "Modavandi Sathiyamangalam"},
            {"sno": 25, "name": "Mukasi Anumanpalli B", "category": "Rural", "gp": "Mugasi Anumanpalli"},
            {"sno": 26, "name": "Mukasi Hanuman Palli", "category": "Rural", "gp": "Mugasi Anumanpalli"},
            {"sno": 27, "name": "Nanjai Uthukuli B", "category": "Rural", "gp": "Nanjai Uthukuli"},
            {"sno": 28, "name": "Nanjaikalamangalam", "category": "Rural", "gp": "Nanjai Kalamangalam"},
            {"sno": 29, "name": "Nanjailakkapuram", "category": "Rural", "gp": "Lakkapuram"},
            {"sno": 30, "name": "Nanjaiuthukuli", "category": "Rural", "gp": "Muthugoundampalayam, Nanjai Uthukuli"},
            {"sno": 31, "name": "Palamangalam", "category": "Rural", "gp": "Palamangalam"},
            {"sno": 32, "name": "Pudur", "category": "Rural", "gp": "46 Pudur"},
            {"sno": 33, "name": "Pudur B", "category": "Rural", "gp": "46 Pudur"},
            {"sno": 34, "name": "Punduraisemur", "category": "Rural", "gp": "Poondurai Semur"},
            {"sno": 35, "name": "Punjai Kalamangalam", "category": "Rural", "gp": "Ganapathipalayam, Punjai Kalamangalam"},
            {"sno": 36, "name": "Punjai Kalamangalam B", "category": "Rural", "gp": "Punjai Kalamangalam"},
            {"sno": 37, "name": "Punjailakkapuram", "category": "Rural", "gp": "Lakkapuram"},
            {"sno": 38, "name": "Sathambur", "category": "Rural", "gp": "Nanjai Uthukuli"},
            {"sno": 39, "name": "Thanathampalayam", "category": "Rural", "gp": "Enjampalli"},
            {"sno": 40, "name": "Thuyyampoondurai", "category": "Rural", "gp": "3 Gram Panchayats"},
            {"sno": 41, "name": "Thuyyampoondurai B", "category": "Rural", "gp": "Thuyyampoondurai"},
            {"sno": 42, "name": "Thuyyampoondurai C", "category": "Rural", "gp": "Thuyyampoondurai"},
            {"sno": 43, "name": "Vadugapatti", "category": "Urban", "gp": "Not applicable"},
            {"sno": 44, "name": "Vadugapatti B", "category": "Unmapped", "gp": "Not available"},
            {"sno": 45, "name": "Vadugapatti C", "category": "Urban", "gp": "Not applicable"},
            {"sno": 46, "name": "Velampalayam", "category": "Rural", "gp": "Kanagapuram"},
            {"sno": 47, "name": "Velampalayam (60)", "category": "Rural", "gp": "60 Velampalayam"},
            {"sno": 48, "name": "Velampalayam B", "category": "Rural", "gp": "60 Velampalayam"},
            {"sno": 49, "name": "Vilakethi", "category": "Rural", "gp": "Villakkethy"},
            {"sno": 50, "name": "Vilakkethi B", "category": "Rural", "gp": "Villakkethy"}
        ]
    },
    "Nambiyur": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "நம்பியூர்",
        "sub_departments": ["Revenue Administration", "Agricultural Extension", "Rural Development"],
        "local_body": "Nambiyur Selection Grade Town Panchayat & Rural Village Panchayats",
        "firkas": [
            ("Nambiyur", "நம்பியூர்"),
            ("Kadathur", "கடத்தூர்"),
            ("Kosanam", "கோசணம்")
        ],
        "villages": [
            {"sno": 1, "name": "Andipalayam", "category": "Rural", "gp": "Andipalayam"},
            {"sno": 2, "name": "Anjanur", "category": "Rural", "gp": "Anjanur"},
            {"sno": 3, "name": "Avalampalayam", "category": "Rural", "gp": "Getticheviyur"},
            {"sno": 4, "name": "Elathur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 5, "name": "Ellathur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Emmampoondi", "category": "Rural", "gp": "Emmampoondi"},
            {"sno": 7, "name": "Emmampoondi B", "category": "Rural", "gp": "Emmampoondi"},
            {"sno": 8, "name": "Gudakkarai", "category": "Rural", "gp": "Gudakkarai"},
            {"sno": 9, "name": "Irugalur", "category": "Rural", "gp": "Anjanur"},
            {"sno": 10, "name": "Kadasellipalayam", "category": "Rural", "gp": "Koshanam"},
            {"sno": 11, "name": "Kadathur", "category": "Rural", "gp": "Kadathur"},
            {"sno": 12, "name": "Karapadi", "category": "Rural", "gp": "Karapadi"},
            {"sno": 13, "name": "Karattupalayam", "category": "Rural", "gp": "Karattupalayam"},
            {"sno": 14, "name": "Karattupalayam B", "category": "Rural", "gp": "Karattupalayam"},
            {"sno": 15, "name": "Kavilipalayam", "category": "Rural", "gp": "Kavilipalayam"},
            {"sno": 16, "name": "Kosanam", "category": "Rural", "gp": "Koshanam"},
            {"sno": 17, "name": "Kosanam B", "category": "Rural", "gp": "Koshanam"},
            {"sno": 18, "name": "Kurumandur", "category": "Rural", "gp": "Kurumandur"},
            {"sno": 19, "name": "Lagampalayam", "category": "Rural", "gp": "Lagampalayam"},
            {"sno": 20, "name": "Mottanam", "category": "Rural", "gp": "Polavapalayam"},
            {"sno": 21, "name": "Nambiyur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 22, "name": "Nambiyur B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 23, "name": "Nichampalayam", "category": "Rural", "gp": "Getticheviyur"},
            {"sno": 24, "name": "Olalakovil", "category": "Rural", "gp": "Olalakoil"},
            {"sno": 25, "name": "Polavapalayam", "category": "Rural", "gp": "Polavapalayam"},
            {"sno": 26, "name": "Santhipalayam", "category": "Rural", "gp": "Getticheviyur"},
            {"sno": 27, "name": "Sellapampalayam", "category": "Rural", "gp": "Karapadi"},
            {"sno": 28, "name": "Sinnaripalayam", "category": "Rural", "gp": "Getticheviyur"},
            {"sno": 29, "name": "Sundakkampalayam", "category": "Rural", "gp": "Sundakkampalayam"},
            {"sno": 30, "name": "Talguni", "category": "Rural", "gp": "Talguni"},
            {"sno": 31, "name": "Varapalayam", "category": "Rural", "gp": "Varappalayam"},
            {"sno": 32, "name": "Vemandampalayam", "category": "Rural", "gp": "Vemandampalayam"},
            {"sno": 33, "name": "Vemandampalyam B", "category": "Rural", "gp": "Vemandampalayam"}
        ]
    },
    "Perundurai": {
        "division": "Erode Division",
        "division_ta": "ஈரோடு வருவாய் கோட்டம்",
        "taluk_ta": "பெருந்துறை",
        "sub_departments": ["Revenue Administration", "SIPCOT Industrial Complex", "Textile & Rural Development"],
        "local_body": "Perundurai & Chennimalai Town Panchayats & Village Panchayats",
        "firkas": [
            ("Chennimalai", "சென்னிமலை"),
            ("Kanjikoil", "காஞ்சிக்கோவில்"),
            ("Perundurai", "பெருந்துறை"),
            ("Thingalore", "திங்களூர்"),
            ("Vellodu", "வெள்ளோடு")
        ],
        "villages": [
            {"sno": 1, "name": "Agrahara Vijayamangalam", "category": "Rural", "gp": "Vijayapuri"},
            {"sno": 2, "name": "Attavanaipidariyur", "category": "Rural", "gp": "Ottaparai"},
            {"sno": 3, "name": "Ayegoundanpalayam", "category": "Rural", "gp": "Seenapuram"},
            {"sno": 4, "name": "Chennimalai", "category": "Rural", "gp": "Paniyampalli"},
            {"sno": 5, "name": "Chennimalai B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 6, "name": "Chennimalai R.F.", "category": "Rural", "gp": "Ekkettampalayam, Ottaparai"},
            {"sno": 7, "name": "Chinnamallampalayam", "category": "Rural", "gp": "Thudupathi"},
            {"sno": 8, "name": "Chinnavirasangili", "category": "Rural", "gp": "Chinnaveerasangili"},
            {"sno": 9, "name": "Ekkattampalayam", "category": "Rural", "gp": "Ekkettampalayam"},
            {"sno": 10, "name": "Ekkattampalayam B", "category": "Rural", "gp": "Ekkettampalayam"},
            {"sno": 11, "name": "Ellaigramam", "category": "Rural", "gp": "Ellaigramam"},
            {"sno": 12, "name": "Ingur", "category": "Rural", "gp": "Ingur"},
            {"sno": 13, "name": "Ingur B", "category": "Rural", "gp": "Ingur"},
            {"sno": 14, "name": "Kallakulam", "category": "Rural", "gp": "Kallakulam"},
            {"sno": 15, "name": "Kambiliampatti", "category": "Rural", "gp": "Kambuliampatty"},
            {"sno": 16, "name": "Kandampalayam", "category": "Rural", "gp": "Kandampalayam"},
            {"sno": 17, "name": "Kanjikoil", "category": "Urban", "gp": "Not applicable"},
            {"sno": 18, "name": "Kanjikoil B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 19, "name": "Karandipalayam", "category": "Rural", "gp": "Karandipalayam"},
            {"sno": 20, "name": "Karukkapalayam", "category": "Rural", "gp": "Karukkupalayam"},
            {"sno": 21, "name": "Karumandisellipalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 22, "name": "Karumandisellipalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 23, "name": "Kavundichipalayam", "category": "Rural", "gp": "Kavundachipalayam"},
            {"sno": 24, "name": "Kavundichipalayam B", "category": "Rural", "gp": "Kavundachipalayam"},
            {"sno": 25, "name": "Kodumanal", "category": "Rural", "gp": "Kodumanal"},
            {"sno": 26, "name": "Kongampalayam", "category": "Rural", "gp": "Varapalayam"},
            {"sno": 27, "name": "Koyilpalayam", "category": "Rural", "gp": "Moongilpalayam"},
            {"sno": 28, "name": "Kullampalayam", "category": "Rural", "gp": "Kullampalayam"},
            {"sno": 29, "name": "Kuppuchipalayam", "category": "Rural", "gp": "Kuppichipalayam"},
            {"sno": 30, "name": "Kuthampalayam", "category": "Rural", "gp": "Koothampalayam"},
            {"sno": 31, "name": "Madathupalayam", "category": "Rural", "gp": "Madathupalayam"},
            {"sno": 32, "name": "Marappanaickampalayam", "category": "Rural", "gp": "Moongilpalayam"},
            {"sno": 33, "name": "Mettupudur", "category": "Rural", "gp": "Mettupudur"},
            {"sno": 34, "name": "Moongilpalayam", "category": "Rural", "gp": "Moongilpalayam"},
            {"sno": 35, "name": "Mugasipidariyur B", "category": "Rural", "gp": "Mukasipidariyur"},
            {"sno": 36, "name": "Mukasi Pulavapalayam", "category": "Rural", "gp": "Mugasipulavanpalayam"},
            {"sno": 37, "name": "Mukasipidariyur (Ct)", "category": "Rural", "gp": "Mukasipidariyur"},
            {"sno": 38, "name": "Mullampatti", "category": "Rural", "gp": "Mullampatty"},
            {"sno": 39, "name": "Murungatholuvu", "category": "Rural", "gp": "Murungatholuvu"},
            {"sno": 40, "name": "Murungatholuvu B", "category": "Rural", "gp": "Murungatholuvu"},
            {"sno": 41, "name": "Nallampatti", "category": "Urban", "gp": "Not applicable"},
            {"sno": 42, "name": "Nanjai Palatholuvu", "category": "Rural", "gp": "Punjai Palatholuvu"},
            {"sno": 43, "name": "Nichampalayam", "category": "Rural", "gp": "Nichampalayam"},
            {"sno": 44, "name": "Nimittipalayam", "category": "Rural", "gp": "Seenapuram"},
            {"sno": 45, "name": "Olapalayam", "category": "Rural", "gp": "Periyavilamalai"},
            {"sno": 46, "name": "Orathupalayam", "category": "Rural", "gp": "Ellaigramam"},
            {"sno": 47, "name": "Ottapparai (Ct)", "category": "Rural", "gp": "Ottaparai"},
            {"sno": 48, "name": "Palakarai", "category": "Rural", "gp": "Thudupathi"},
            {"sno": 49, "name": "Pallapalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 50, "name": "Pallapalyam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 51, "name": "Pandiampalayam", "category": "Rural", "gp": "Pandiyampalayam"},
            {"sno": 52, "name": "Pandiyampalayam B", "category": "Rural", "gp": "Pandiyampalayam"},
            {"sno": 53, "name": "Pappampalayam", "category": "Rural", "gp": "Pappampalayam"},
            {"sno": 54, "name": "Pasuvapatti", "category": "Rural", "gp": "Basuvapatti"},
            {"sno": 55, "name": "Pasuvapatti B", "category": "Rural", "gp": "Basuvapatti"},
            {"sno": 56, "name": "Pattackarampalayam", "category": "Rural", "gp": "Pattakaranpalayam"},
            {"sno": 57, "name": "Periyaveerasangili", "category": "Rural", "gp": "Periaveerasangili"},
            {"sno": 58, "name": "Periyavilamalai", "category": "Rural", "gp": "Periyavilamalai"},
            {"sno": 59, "name": "Perundurai", "category": "Urban", "gp": "Not applicable"},
            {"sno": 60, "name": "Perundurai B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 61, "name": "Pethampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 62, "name": "Pethampalayam B", "category": "Urban", "gp": "Not applicable"},
            {"sno": 63, "name": "Polanaickampalayam", "category": "Rural", "gp": "Polanaickenpalayam"},
            {"sno": 64, "name": "Ponmudi", "category": "Rural", "gp": "Ponmudi"},
            {"sno": 65, "name": "Poovampalayam", "category": "Rural", "gp": "Thiruvachi"},
            {"sno": 66, "name": "Pudupalayam .", "category": "Rural", "gp": "Pudupalayam"},
            {"sno": 67, "name": "Pungampadi", "category": "Rural", "gp": "Pungampadi"},
            {"sno": 68, "name": "Punjai Palatholuvu", "category": "Rural", "gp": "Punjai Palatholuvu"},
            {"sno": 69, "name": "Seenapuram", "category": "Rural", "gp": "Seenapuram"},
            {"sno": 70, "name": "Sellappampalayam", "category": "Rural", "gp": "Sellappampalayam"},
            {"sno": 71, "name": "Singanallur", "category": "Rural", "gp": "Singanallur"},
            {"sno": 72, "name": "Singanallur B", "category": "Rural", "gp": "Singanallur"},
            {"sno": 73, "name": "Sinnavilamalai", "category": "Rural", "gp": "Periyavilamalai"},
            {"sno": 74, "name": "Sirukkalanchi", "category": "Rural", "gp": "Sirukalanji"},
            {"sno": 75, "name": "Sullipalayam", "category": "Rural", "gp": "Sullipalayam"},
            {"sno": 76, "name": "Sungakarampalayam", "category": "Rural", "gp": "Vettaiyankinar"},
            {"sno": 77, "name": "Talayampalayam", "category": "Rural", "gp": "Seenapuram"},
            {"sno": 78, "name": "Thenmugam Vellode", "category": "Rural", "gp": "Kumaravalasu"},
            {"sno": 79, "name": "Thenmugam Vellode B", "category": "Rural", "gp": "Vadamugam Vellodu"},
            {"sno": 80, "name": "Thingalur", "category": "Rural", "gp": "Thingalore"},
            {"sno": 81, "name": "Thiruvachi", "category": "Rural", "gp": "Thiruvachi"},
            {"sno": 82, "name": "Thiruvachi B", "category": "Rural", "gp": "Thiruvachi"},
            {"sno": 83, "name": "Thoranavavi", "category": "Rural", "gp": "Thoranavavi"},
            {"sno": 84, "name": "Thuduppathi", "category": "Rural", "gp": "Thudupathi"},
            {"sno": 85, "name": "Unjapalayam", "category": "Rural", "gp": "Kallakulam"},
            {"sno": 86, "name": "Vadamugam Vellode", "category": "Rural", "gp": "Kuttapalayam, Vadamugam Vellodu"},
            {"sno": 87, "name": "Vadamugam Vellode B", "category": "Rural", "gp": "Vadamugam Vellodu"},
            {"sno": 88, "name": "Varapalayam", "category": "Rural", "gp": "Varapalayam"},
            {"sno": 89, "name": "Vettaiankinar", "category": "Rural", "gp": "Vettaiyankinar"},
            {"sno": 90, "name": "Vijayapuri (Ct)", "category": "Rural", "gp": "Vijayapuri"},
            {"sno": 91, "name": "Voipadi", "category": "Rural", "gp": "Voipadi"}
        ]
    },
    "Sathyamangalam": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "சத்தியமங்கலம்",
        "sub_departments": ["Revenue Administration", "Forest Range & Wildlife Sanctuary", "Tribal Welfare"],
        "local_body": "Sathyamangalam & Punjai Puliyampatti Municipalities & Village Panchayats",
        "firkas": [
            ("Arasur", "அரசூர்"),
            ("Bhavanisagar", "பவானிசாகர்"),
            ("Gudhiyalathur", "குத்தியாலத்தூர்"),
            ("Punjai Puliyampatti", "புஞ்சை புளியம்பட்டி"),
            ("Sathyamangalam", "சத்தியமங்கலம்")
        ],
        "villages": [
            {"sno": 1, "name": "Akkarainegamam", "category": "Rural", "gp": "Konamoolai"},
            {"sno": 2, "name": "Akkaraithathappalli", "category": "Rural", "gp": "Uthandiyur"},
            {"sno": 3, "name": "Akkurinjieri Extn. R.F.", "category": "Rural", "gp": "Bynapuram, Thiginarai"},
            {"sno": 4, "name": "Akkurinjieri R.F.", "category": "Rural", "gp": "Bynapuram, Thiginarai"},
            {"sno": 5, "name": "Alathucombai", "category": "Rural", "gp": "Sadmugai"},
            {"sno": 6, "name": "Arasur", "category": "Rural", "gp": "Arasur"},
            {"sno": 7, "name": "Ariyappampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 8, "name": "Ayyampalayam", "category": "Rural", "gp": "Periyakallipatti"},
            {"sno": 9, "name": "Baguthampalayam", "category": "Rural", "gp": "Kothamangalam"},
            {"sno": 10, "name": "Barabetta Rf", "category": "Rural", "gp": "Pavalakuttai"},
            {"sno": 11, "name": "Boosaripalayam", "category": "Rural", "gp": "Uthandiyur"},
            {"sno": 12, "name": "Chikkarasampalayam", "category": "Rural", "gp": "Chikkarasampalayam"},
            {"sno": 13, "name": "Dasaripalayam", "category": "Rural", "gp": "Komarapalayam"},
            {"sno": 14, "name": "Dhoddampalayam", "category": "Rural", "gp": "Thoppampalayam"},
            {"sno": 15, "name": "Gundri", "category": "Rural", "gp": "Gundri"},
            {"sno": 16, "name": "Guthiyalathur", "category": "Rural", "gp": "5 Gram Panchayats"},
            {"sno": 17, "name": "Guthiyalathur (Addition) R.F.", "category": "Rural", "gp": "Iruttipalayam, Kadambur"},
            {"sno": 18, "name": "Guthiyalathur Extension Rf", "category": "Rural", "gp": "Iruttipalayam"},
            {"sno": 19, "name": "Ikkarainegamam", "category": "Rural", "gp": "Ikkarainagamam"},
            {"sno": 20, "name": "Ikkaraithathapalli", "category": "Rural", "gp": "Kothamangalam"},
            {"sno": 21, "name": "Indiampalayam", "category": "Rural", "gp": "Indiyampalayam"},
            {"sno": 22, "name": "Karidoddampalayam", "category": "Rural", "gp": "Uthandiyur"},
            {"sno": 23, "name": "Kembanaickanpalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 24, "name": "Komarapalayam", "category": "Rural", "gp": "Komarapalayam"},
            {"sno": 25, "name": "Konamoolai", "category": "Rural", "gp": "Konamoolai"},
            {"sno": 26, "name": "Kondappanaickanpalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 27, "name": "Koothampalayam", "category": "Rural", "gp": "Koothampalayam"},
            {"sno": 28, "name": "Kothamangalam", "category": "Rural", "gp": "Kothamangalam"},
            {"sno": 29, "name": "Kottuveerampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 30, "name": "Kurumbapalayam", "category": "Rural", "gp": "Vinnapalli"},
            {"sno": 31, "name": "Madampalayam", "category": "Rural", "gp": "Mathampalayam"},
            {"sno": 32, "name": "Makkinancombai", "category": "Rural", "gp": "Maccinamcombai"},
            {"sno": 33, "name": "Malayadipudur", "category": "Rural", "gp": "Komarapalayam"},
            {"sno": 34, "name": "Marayeepalayam", "category": "Rural", "gp": "Mathampalayam"},
            {"sno": 35, "name": "Mudukkanthurai", "category": "Rural", "gp": "Mudukkanthurai"},
            {"sno": 36, "name": "Nallur", "category": "Rural", "gp": "Nallur"},
            {"sno": 37, "name": "Panayampalli", "category": "Rural", "gp": "Panniyampalli"},
            {"sno": 38, "name": "Pattavarthiayyampalayam", "category": "Rural", "gp": "Chikkarasampalayam"},
            {"sno": 39, "name": "Pazhayakalaiyanur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 40, "name": "Periyakallipatti", "category": "Rural", "gp": "Periyakallipatti"},
            {"sno": 41, "name": "Pudupeerkadavu", "category": "Rural", "gp": "Pudupeerkadavu"},
            {"sno": 42, "name": "Pungampalli", "category": "Rural", "gp": "Desipalayam"},
            {"sno": 43, "name": "Pungar", "category": "Rural", "gp": "Pungur"},
            {"sno": 44, "name": "Punjaipuliampatti", "category": "Rural", "gp": "Nochikuttai"},
            {"sno": 45, "name": "Puthukalaiyanur", "category": "Urban", "gp": "Not applicable"},
            {"sno": 46, "name": "Rajan Nagar", "category": "Rural", "gp": "Rajannagar"},
            {"sno": 47, "name": "Rangasamudram", "category": "Urban", "gp": "Not applicable"},
            {"sno": 48, "name": "Sadumugai", "category": "Rural", "gp": "Sadmugai"},
            {"sno": 49, "name": "Sathyamangalam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 50, "name": "Sellipalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 51, "name": "Senbagapudur B", "category": "Rural", "gp": "Shenbagapudur"},
            {"sno": 52, "name": "Shenbagapudur", "category": "Rural", "gp": "Shenbagapudur"},
            {"sno": 53, "name": "Sunkakaranpalayam", "category": "Rural", "gp": "Desipalayam"},
            {"sno": 54, "name": "Thatchaperumapalayam", "category": "Rural", "gp": "Desipalayam"},
            {"sno": 55, "name": "Thingalur", "category": "Rural", "gp": "Germalam, Thingalur"},
            {"sno": 56, "name": "Thingalur B", "category": "Rural", "gp": "Thingalur"},
            {"sno": 57, "name": "Thoppampalayam", "category": "Rural", "gp": "Thoppampalayam"},
            {"sno": 58, "name": "Ukkaram", "category": "Rural", "gp": "Ukkaram"},
            {"sno": 59, "name": "Ukkaram B", "category": "Rural", "gp": "Ukkaram"},
            {"sno": 60, "name": "Ukkaram C", "category": "Rural", "gp": "Ukkaram"},
            {"sno": 61, "name": "Ullepalayam (R.F.)", "category": "Rural", "gp": "Karalayam"},
            {"sno": 62, "name": "Varathappampalayam", "category": "Urban", "gp": "Not applicable"},
            {"sno": 63, "name": "Velamundi(R.F.)", "category": "Rural", "gp": "Vinnapalli"},
            {"sno": 64, "name": "Vinnappalli", "category": "Rural", "gp": "Vinnapalli"}
        ]
    },
    "Thalavadi": {
        "division": "Gobichettipalayam Division",
        "division_ta": "கோபிசெட்டிபாளையம் வருவாய் கோட்டம்",
        "taluk_ta": "தாளவாடி",
        "sub_departments": ["Revenue Administration", "Hill Area Development Desk", "Tribal Welfare"],
        "local_body": "Tribal Hill Panchayats",
        "firkas": [
            ("Thalavadi", "தாளவாடி")
        ],
        "villages": [
            {"sno": 1, "name": "Arulavadi", "category": "Rural", "gp": "Mallanguli"},
            {"sno": 2, "name": "Byannapuram", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 3, "name": "Chikkahajanur", "category": "Rural", "gp": "Thalavady"},
            {"sno": 4, "name": "Dhoddahajanur", "category": "Rural", "gp": "Dhottakaajanoor"},
            {"sno": 5, "name": "Dhoddamudukkarai", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 6, "name": "Erahanahalli", "category": "Rural", "gp": "Thiginarai"},
            {"sno": 7, "name": "Gettavadi", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 8, "name": "Hassanur", "category": "Rural", "gp": "Asanur"},
            {"sno": 9, "name": "Iggalore", "category": "Rural", "gp": "Iggalur"},
            {"sno": 10, "name": "Karalavadi", "category": "Rural", "gp": "Thiginarai"},
            {"sno": 11, "name": "Kongahalli", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 12, "name": "Madahalli", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 13, "name": "Mallankuli", "category": "Rural", "gp": "Mallanguli"},
            {"sno": 14, "name": "Marur", "category": "Rural", "gp": "Dhottakaajanoor, Thalavady"},
            {"sno": 15, "name": "Neithalapuram", "category": "Rural", "gp": "Neithalapuram"},
            {"sno": 16, "name": "Panahahalli", "category": "Rural", "gp": "Bynapuram"},
            {"sno": 17, "name": "Talamalai", "category": "Rural", "gp": "Talamalai"},
            {"sno": 18, "name": "Talamalai Extn.(R.F.)", "category": "Rural", "gp": "Talamalai"},
            {"sno": 19, "name": "Talamalai R.F.", "category": "Rural", "gp": "Talamalai"},
            {"sno": 20, "name": "Talavadi", "category": "Rural", "gp": "Thalavady"},
            {"sno": 21, "name": "Thiginarai", "category": "Rural", "gp": "Thiginarai"}
        ]
    }
}


class NumberedCanvas(canvas.Canvas):
    """Adds running header and footer with total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#0f766e")) # Teal primary

        # Top running header
        self.drawString(40, 810, "GOVERNMENT OF TAMIL NADU • REVENUE & DISASTER MANAGEMENT DEPARTMENT")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(555, 810, "ERODE DISTRICT COLLECTORATE")

        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.75)
        self.line(40, 804, 555, 804)

        # Bottom running footer
        self.line(40, 45, 555, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(40, 32, "GDP Assistant Official Directory • Leaf-to-Root Administrative Hierarchy")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(555, 32, page_str)
        self.restoreState()


def generate_authoritative_pdf(output_path: str):
    """Builds a pixel-perfect, official Tamil Nadu Government PDF document."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0f172a"),
        alignment=1, # Center
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f766e"),
        alignment=1,
        spaceAfter=12
    )
    meta_style = ParagraphStyle(
        'MetaBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=10,
        spaceAfter=6
    )
    taluk_title_style = ParagraphStyle(
        'TalukTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a")
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0
    )

    elements = []

    # Title and Metadata Banner
    elements.append(Paragraph("ERODE DISTRICT COLLECTORATE", subtitle_style))
    elements.append(Paragraph("Administrative Hierarchy & Comprehensive Village Directory", title_style))
    elements.append(Paragraph("Authoritative 10-Taluk Jurisdiction Master Directory for Public Grievance AI Resolution (2026)", ParagraphStyle('SubSub', parent=subtitle_style, fontSize=9, textColor=colors.HexColor("#475569"))))
    elements.append(Spacer(1, 6))

    # Summary Statistics Box
    total_taluks = len(TALUK_VILLAGES_DATA)
    total_villages = sum(len(t["villages"]) for t in TALUK_VILLAGES_DATA.values())
    total_urban = sum(sum(1 for v in t["villages"] if v["category"] == "Urban") for t in TALUK_VILLAGES_DATA.values())
    total_rural = sum(sum(1 for v in t["villages"] if v["category"] == "Rural") for t in TALUK_VILLAGES_DATA.values())
    total_firkas = sum(len(t["firkas"]) for t in TALUK_VILLAGES_DATA.values())

    summary_data = [
        [
            Paragraph(f"<b>District:</b> Erode (ஈரோடு)", meta_style),
            Paragraph(f"<b>Divisions:</b> 2 (Erode & Gobichettipalayam)", meta_style),
            Paragraph(f"<b>Total Taluks:</b> {total_taluks}", meta_style)
        ],
        [
            Paragraph(f"<b>Total Revenue Firkas:</b> {total_firkas}", meta_style),
            Paragraph(f"<b>Total Revenue Villages:</b> {total_villages}", meta_style),
            Paragraph(f"<b>Classification:</b> {total_urban} Urban • {total_rural} Rural", meta_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[170, 180, 165])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # Taluk Summary Overview Table
    elements.append(Paragraph("1. Taluk Overview & Statistical Summary", section_heading))
    overview_rows = [[
        Paragraph("Sl.", table_header),
        Paragraph("Taluk Name", table_header),
        Paragraph("Revenue Division", table_header),
        Paragraph("Firkas", table_header),
        Paragraph("Villages", table_header),
        Paragraph("Urban / Rural", table_header),
        Paragraph("Local Body Governance", table_header)
    ]]

    for idx, (t_name, t_info) in enumerate(TALUK_VILLAGES_DATA.items(), 1):
        v_list = t_info["villages"]
        u_cnt = sum(1 for v in v_list if v["category"] == "Urban")
        r_cnt = sum(1 for v in v_list if v["category"] == "Rural")
        overview_rows.append([
            Paragraph(str(idx), table_cell_bold),
            Paragraph(f"<b>{t_name}</b> ({t_info['taluk_ta']})", table_cell),
            Paragraph(t_info["division"].replace(" Division", ""), table_cell),
            Paragraph(str(len(t_info["firkas"])), table_cell),
            Paragraph(f"<b>{len(v_list)}</b>", table_cell_bold),
            Paragraph(f"{u_cnt} U / {r_cnt} R", table_cell),
            Paragraph(t_info["local_body"], table_cell)
        ])

    overview_table = Table(overview_rows, colWidths=[24, 110, 85, 38, 42, 60, 156])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f766e")),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
    ]))
    elements.append(overview_table)
    elements.append(Spacer(1, 14))

    # Detailed Directory per Taluk
    elements.append(Paragraph("2. Authoritative Village Directory by Taluk", section_heading))

    for t_name, t_info in TALUK_VILLAGES_DATA.items():
        v_list = t_info["villages"]
        firkas_str = ", ".join([f"{f_en} ({f_ta})" for f_en, f_ta in t_info["firkas"]])
        
        taluk_header_block = [
            Paragraph(f"<b>Taluk: {t_name} ({t_info['taluk_ta']})</b> — {len(v_list)} Total Villages", taluk_title_style),
            Paragraph(f"<font color='#64748b'>Division:</font> {t_info['division']} | <font color='#64748b'>Firkas ({len(t_info['firkas'])}):</font> {firkas_str}", meta_style),
            Spacer(1, 4)
        ]

        v_rows = [[
            Paragraph("Sl. No.", table_header),
            Paragraph("Village Name", table_header),
            Paragraph("Category", table_header),
            Paragraph("Gram Panchayat / Local Body Coverage", table_header)
        ]]

        for v in v_list:
            cat_color = "#0369a1" if v["category"] == "Urban" else "#15803d"
            cat_html = f"<font color='{cat_color}'><b>{v['category']}</b></font>"
            v_rows.append([
                Paragraph(str(v["sno"]), table_cell_bold),
                Paragraph(f"<b>{v['name']}</b>", table_cell),
                Paragraph(cat_html, table_cell),
                Paragraph(v["gp"], table_cell)
            ])

        v_table = Table(v_rows, colWidths=[40, 175, 75, 225])
        v_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
        ]))

        elements.append(KeepTogether(taluk_header_block + [v_table, Spacer(1, 12)]))

    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Generated official PDF document at: {output_path}")


def export_json_and_artifacts():
    """Exports the complete hierarchy structure to data/ and backend/data/ directories."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backend_data_dir = os.path.join(repo_root, "backend", "data")
    root_data_dir = os.path.join(repo_root, "data")

    os.makedirs(backend_data_dir, exist_ok=True)
    os.makedirs(root_data_dir, exist_ok=True)

    # 1. Export PDF to both locations
    pdf_backend = os.path.join(backend_data_dir, "erode_administrative_hierarchy_villages.pdf")
    pdf_root = os.path.join(root_data_dir, "erode_administrative_hierarchy_villages.pdf")
    generate_authoritative_pdf(pdf_backend)
    generate_authoritative_pdf(pdf_root)

    # 2. Export structured JSON to both locations
    json_backend = os.path.join(backend_data_dir, "erode_village_directory.json")
    json_root = os.path.join(root_data_dir, "erode_village_directory.json")

    export_payload = {
        "district": {"name_en": "Erode", "name_ta": "ஈரோடு"},
        "taluks_count": len(TALUK_VILLAGES_DATA),
        "villages_count": sum(len(t["villages"]) for t in TALUK_VILLAGES_DATA.values()),
        "taluks": TALUK_VILLAGES_DATA
    }

    with open(json_backend, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, ensure_ascii=False, indent=2)
    with open(json_root, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] Exported village directory JSON to:\n  - {json_backend}\n  - {json_root}")


if __name__ == "__main__":
    export_json_and_artifacts()
