import pytest
from services.location_matcher import location_matcher
from services.entity_extractor import extract_header_entities


def test_hierarchy_loading():
    """Verifies that all administrative levels, local bodies, and ward entities load dynamically."""
    assert len(location_matcher.taluk_to_division) > 0
    assert len(location_matcher.firka_keywords) > 0
    assert len(location_matcher.local_body_entries) > 0
    assert len(location_matcher.all_wards) >= 60


def test_corporation_ward_entities():
    """Verifies urban locality strings dynamically resolve their entity ward name and parent hierarchy."""
    cases = [
        ("2/15, பாரதி வீதி, சூரம்பட்டி வலசு மேற்கு, ஈரோடு - 638 009", "சூரம்பட்டி வலசு மேற்கு", "Erode City Municipal Corporation", "Corporation", "ஈரோடு தெற்கு"),
        ("மாவட்ட ஆட்சியர் அலுவலக வளாகம், சம்பத் நகர், ஈரோடு - 638 011", "சம்பத் நகர் மற்றும் கலெக்டரேட் வளாகம்", "Erode City Municipal Corporation", "Corporation", "ஈரோடு மேற்கு"),
        ("12, பார்க் ரோடு, பெரியார் நகர், ஈரோடு மாநகராட்சி", "பெரியார் நகர் மத்தி மற்றும் பார்க் ரோடு", "Erode City Municipal Corporation", "Corporation", "ஈரோடு கிழக்கு"),
        ("மணிக்கம்பாளையம் ஹவுசிங் போர்டு காலனி, ஈரோடு", "மணிக்கம்பாளையம் ஹவுசிங் போர்டு காலனி", "Erode City Municipal Corporation", "Corporation", "ஈரோடு தெற்கு"),
        ("மரப்பாலம் கிழக்கு பகுதி, ஈரோடு", "மரப்பாலம் கிழக்கு", "Erode City Municipal Corporation", "Corporation", "ஈரோடு கிழக்கு"),
        ("நொச்சிப்பாளையம் மற்றும் சோலார் புதிய பேருந்து நிலையம் ரோடு, ஈரோடு", "நொச்சிப்பாளையம் மற்றும் சோலார் புதிய பேருந்து நிலையம்", "Erode City Municipal Corporation", "Corporation", "ஈரோடு தெற்கு"),
    ]

    for addr, expected_ward, expected_muni, expected_lb, expected_firka in cases:
        res = location_matcher.match_hierarchy(address_text=addr)
        assert res["ward"] == expected_ward, f"Failed ward for {addr}: got {res['ward']}"
        assert res["municipality_ward"] == expected_muni
        assert res["local_body_type"] == expected_lb
        assert res["firka"] == expected_firka
        assert res["taluk"] == "ஈரோடு"


def test_municipality_ward_entities():
    """Verifies municipalities outside the Corporation map to their respective municipal wards."""
    res_bhavani = location_matcher.match_hierarchy("பவானி நகராட்சி வார்டு 27, பவானி மெயின் ரோடு")
    assert res_bhavani["ward"] == "பவானி வார்டு 27"
    assert res_bhavani["municipality_ward"] == "Bhavani Municipality"
    assert res_bhavani["local_body_type"] == "Municipality"
    assert res_bhavani["taluk"] == "பவானி"

    res_gobi = location_matcher.match_hierarchy("கோபிசெட்டிபாளையம் நகராட்சி வார்டு 1, கோபி")
    assert res_gobi["ward"] == "கோபி வார்டு 1"
    assert res_gobi["municipality_ward"] == "Gobichettipalayam Municipality"
    assert res_gobi["local_body_type"] == "Municipality"
    assert res_gobi["taluk"] == "கோபிசெட்டிபாளையம்"


def test_rural_invariants():
    """Verifies rural petitions do NOT get assigned corporation or municipal wards and stay Village Panchayat."""
    res_vellode = location_matcher.match_hierarchy("2/17, காளியம்மன் கோவில் தெரு, வெள்ளோடு (Po), பவானி (TK), ஈரோடு மாவட்டம் - 638 302")
    assert res_vellode["ward"] is None
    assert res_vellode["municipality_ward"] is None
    assert res_vellode["local_body_type"] == "Village Panchayat"
    assert res_vellode["firka"] == "வெள்ளோடு"

    res_semmapatti = location_matcher.match_hierarchy("செம்மாபட்டி கிராமம், ஈரோடு மாவட்டம்")
    assert res_semmapatti["ward"] is None
    assert res_semmapatti["municipality_ward"] is None
    assert res_semmapatti["local_body_type"] == "Village Panchayat"


def test_entity_extractor_integration():
    """Verifies header entity extractor populates ward, municipality, and local body."""
    sample_text = """
    அனுப்புநர்
    M. சிவராமன்
    கிருஷ்ணா டாக்கீஸ் ரோடு மற்றும் பஜார் பகுதி
    ஈரோடு மாநகராட்சி - 638001
    செல் : 98427 12345
    """
    extracted = extract_header_entities(sample_text)
    assert extracted.get("ward") == "கிருஷ்ணா டாக்கீஸ் ரோடு மற்றும் பஜார் பகுதி"
    assert extracted.get("municipality_ward") == "Erode City Municipal Corporation"
    assert extracted.get("local_body_type") == "Corporation"
    assert extracted.get("taluk") == "ஈரோடு"
