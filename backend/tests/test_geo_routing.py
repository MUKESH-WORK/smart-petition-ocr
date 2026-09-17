import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from services.geo_validator import process_petition_geo, validate_geo_payload
from services.court_checker import check_court_jurisdiction, check_court_jurisdictional_blockage
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestGeoValidator:
    """Test suite for master geo-configuration layout and dynamic validation logic."""

    def test_urban_corporation_ward_match(self):
        """Test urban address dynamically matches exact corporation ward, zone, and pincode."""
        payload = {
            "petition_id": "TEST-URBAN-01",
            "address": "15, பார்க் ரோடு, பெரியார் நகர், ஈரோடு மாநகராட்சி - 638001",
            "pincode": "638001",
            "taluk": "ஈரோடு",
            "village": ""
        }
        res = process_petition_geo(payload)

        assert res["boundary_type"] == "Urban"
        assert res["local_body_type"] == "Corporation"
        assert res["local_body_name"] == "Erode City Municipal Corporation"
        assert res["ward_no"] == 37
        assert res["zone_no"] == 3
        assert "Surampatti" in res["zone_name"]
        assert res["taluk_en"] == "Erode"

    def test_rural_panchayat_ukkaram(self):
        """
        Test rural territory Sathyamangalam -> Ukkaram:
        - ward_no must be explicitly None (null in JSON)
        - ward_name_en must be 'Not Applicable (Rural Panchayat Area)'
        - local_body_type must be 'Village Panchayat (Ukkaram)'
        """
        payload = {
            "petition_id": "TEST-RURAL-UKK",
            "address": "மெயின் ரோடு, உக்கரம் கிராமம், சத்தியமங்கலம் வட்டம்",
            "taluk": "சத்தியமங்கலம்",
            "village": "உக்கரம்",
            "pincode": "638402"
        }
        res = process_petition_geo(payload)

        assert res["boundary_type"] == "Rural"
        assert res["ward_no"] is None
        assert res["ward_name_en"] == "Not Applicable (Rural Panchayat Area)"
        assert res["local_body_type"] == "Village Panchayat (Ukkaram)"
        assert res["taluk_en"] == "Sathyamangalam"
        assert res["village_en"] == "Ukkaram"

    def test_rural_panchayat_vandipalayam(self):
        """Test rural territory Sathyamangalam -> Vandipalayam."""
        payload = {
            "petition_id": "TEST-RURAL-VANDI",
            "address": "வண்டிபாளையம், சத்தியமங்கலம் தாலுகா, ஈரோடு",
            "taluk": "Sathyamangalam",
            "village": "Vandipalayam",
            "pincode": "638401"
        }
        res = process_petition_geo(payload)

        assert res["boundary_type"] == "Rural"
        assert res["ward_no"] is None
        assert res["ward_name_en"] == "Not Applicable (Rural Panchayat Area)"
        assert res["local_body_type"] == "Village Panchayat (Vandipalayam)"
        assert res["taluk_en"] == "Sathyamangalam"

    def test_rural_panchayat_vellode(self):
        """Test rural territory Bhavani -> Vellode."""
        payload = {
            "petition_id": "TEST-RURAL-VELLODE",
            "address": "2/17, காளியம்மன் கோவில் தெரு, வெள்ளோடு, பவானி தாலுகா - 638302",
            "taluk": "பவானி",
            "village": "வெள்ளோடு",
            "pincode": "638302"
        }
        res = process_petition_geo(payload)

        assert res["boundary_type"] == "Rural"
        assert res["ward_no"] is None
        assert res["ward_name_en"] == "Not Applicable (Rural Panchayat Area)"
        assert res["local_body_type"] == "Village Panchayat (Vellode)"
        assert res["taluk_en"] == "Bhavani"

    def test_empty_payload_graceful_handling(self):
        """Test missing fields don't raise exceptions and return valid structure."""
        res = process_petition_geo({})
        assert res["status"] in ["matched", "unmatched_fallback"]
        assert "boundary_type" in res


class TestCourtChecker:
    """Test suite for dynamic court jurisdictional blockage and dispute detection."""

    def test_civil_court_tamil_keywords_detected(self):
        """Intercepts Tamil keywords indicating shared property or inheritance disputes from config."""
        text = "எங்கள் தந்தை காலத்திற்கு பிறகு தம்பி பட்டாவும் அனுபவத்தில் உள்ளது என தகராறு செய்கிறார்."
        res = check_court_jurisdictional_blockage(text)

        assert res["is_civil_court_pending"] is True
        assert res["court_blockage_detected"] is True
        assert len(res["matched_court_keywords"]) >= 2
        assert "தம்பி பட்டாவும்" in res["matched_court_keywords"]
        assert "அனுபவத்தில் உள்ளது" in res["matched_court_keywords"]
        assert res["recommended_routing"] == "SPECIALIZED_ADMINISTRATIVE_DRO_REVIEW"
        assert res["alert_notice"] is not None

    def test_civil_suit_case_number_detected(self):
        """Detects explicit civil suit and court case identifiers from regex patterns."""
        text = "This property is subject to a civil suit in OS No. 142/2023 currently pending case."
        res = check_court_jurisdictional_blockage(text)

        assert res["is_civil_court_pending"] is True
        assert res["court_blockage_detected"] is True
        assert any(kw in ["civil suit", "pending case"] for kw in res["matched_court_keywords"])
        assert len(res["case_identifiers"]) >= 1

    def test_clean_petition_no_court_blockage(self):
        """Asserts clean petitions are not falsely flagged for court disputes."""
        text = "எங்கள் பகுதியில் உள்ள தெரு விளக்குகள் பழுதாகி உள்ளது. உடனே சரிசெய்து தர வேண்டுகிறேன்."
        res = check_court_jurisdictional_blockage(text)

        assert res["is_civil_court_pending"] is False
        assert res["court_blockage_detected"] is False
        assert res["alert_notice"] is None
        assert res["recommended_routing"] == "STANDARD_PROCESSING"


class TestFastAPIRoutingEndpoint:
    """Test suite for the /api/v1/petitions/process-routing FastAPI route."""

    def test_api_urban_petition_routing(self, client):
        """Test API endpoint processes urban petition and returns compliant response."""
        payload = {
            "petition_id": "PET-TEST-API-01",
            "taluk": "ஈரோடு",
            "village": "",
            "pincode": "638001",
            "address": "12, பார்க் ரோடு, பெரியார் நகர், ஈரோடு மாநகராட்சி - 638001",
            "description": "குடிநீர் இணைப்பு வழங்குமாறு கேட்டுக்கொள்கிறேன்."
        }
        response = client.post("/api/v1/petitions/process-routing", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["petition_id"] == "PET-TEST-API-01"
        assert data["geo_resolution"]["boundary_type"] == "Urban"
        assert data["geo_resolution"]["ward_no"] == 37
        assert data["court_review"]["is_civil_court_pending"] is False
        assert data["operational_routing"]["target_authority"] == "Erode City Municipal Corporation"
        assert data["operational_routing"]["priority"] == "NORMAL"

    def test_api_rural_petition_with_court_litigation(self, client):
        """Test API endpoint processes rural petition with civil litigation."""
        payload = {
            "petition_id": "PET-TEST-API-02",
            "taluk": "சத்தியமங்கலம்",
            "village": "உக்கரம்",
            "pincode": "638402",
            "address": "உக்கரம் கிராமம், சத்தியமங்கலம்",
            "description": "பூர்வீக நிலத்தில் ஒரிジナல் பட்டா தராமல் civil suit தொடர்ந்துள்ளனர்."
        }
        response = client.post("/api/v1/petitions/process-routing", json=payload)
        assert response.status_code == 200

        data = response.json()
        geo = data["geo_resolution"]
        court = data["court_review"]

        # Rural assertions
        assert geo["boundary_type"] == "Rural"
        assert geo["ward_no"] is None
        assert geo["ward_name_en"] == "Not Applicable (Rural Panchayat Area)"
        assert geo["local_body_type"] == "Village Panchayat (Ukkaram)"

        # Court blockage assertions
        assert court["is_civil_court_pending"] is True
        assert court["court_blockage_detected"] is True
        assert data["operational_routing"]["priority"] == "HIGH"
        assert data["operational_routing"]["requires_legal_scrutiny"] is True
        assert data["operational_routing"]["target_authority"] == "DRO_SPECIAL_LEGAL_CELL"
