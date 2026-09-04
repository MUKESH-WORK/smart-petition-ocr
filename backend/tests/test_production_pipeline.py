import os
import sys
import json
import pytest
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from services.ocr_router import _preprocess_image
from services.entity_extractor import entity_extractor
from services.ai_analyzer import ai_analyzer
from core.llm_client import llm_client, CATEGORY_KEYWORDS, DEPARTMENT_MAP
from services.file_store import file_store


def test_opencv_preprocessing_pipeline():
    """Validates OpenCV adaptive binarization, deskew, and denoising."""
    # Create a 200x200 test image with synthetic text line
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TAMIL NADU", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    processed = _preprocess_image(img)
    assert processed is not None
    assert processed.shape == (200, 200, 3)
    assert processed.dtype == np.uint8

    # Verify channels remain BGR for PaddleOCR
    assert len(processed.shape) == 3
    assert processed.shape[2] == 3


def test_bilingual_structural_extraction():
    """Validates structural extraction for both Tamil and English petition formats."""
    # 1. Tamil petition format
    tamil_petition = """
    அனுப்புநர்:
    திரு. கே. ராமலிங்கம்,
    த/பெ கருப்பண்ணன்,
    எண் 45, காந்தி நகர், பெருந்துறை (வட்டம்),
    ஈரோடு (மாவட்டம்).
    பொருள்: நில பட்டா மாறுதல் கோரி விண்ணப்பம்.
    """
    struct_ents_ta = entity_extractor._extract_structural_entities(tamil_petition, page_number=1)
    ta_map = {e["entity_type"]: e["entity_value"] for e in struct_ents_ta}

    assert "petitioner_name" in ta_map
    assert "ராமலிங்கம்" in ta_map["petitioner_name"]
    assert "father_husband_name" in ta_map
    assert "கருப்பண்ணன்" in ta_map["father_husband_name"]
    assert "taluk" in ta_map
    assert "பெருந்துறை" in ta_map["taluk"]
    assert "district" in ta_map
    assert "ஈரோடு" in ta_map["district"]
    assert "grievance_type" in ta_map
    assert "பட்டா" in ta_map["grievance_type"]

    # 2. Bilingual / English petition format
    eng_petition = """
    From:
    Mr. S. Murugesan,
    S/o Shanmugam,
    No. 12, Anna Street, Pollachi Taluk,
    Coimbatore District.
    Subject: Drinking water connection repair request.
    """
    struct_ents_en = entity_extractor._extract_structural_entities(eng_petition, page_number=1)
    en_map = {e["entity_type"]: e["entity_value"] for e in struct_ents_en}

    assert "petitioner_name" in en_map
    assert "Murugesan" in en_map["petitioner_name"]
    assert "father_husband_name" in en_map
    assert "Shanmugam" in en_map["father_husband_name"]
    assert "taluk" in en_map
    assert "Pollachi" in en_map["taluk"]
    assert "district" in en_map
    assert "Coimbatore" in en_map["district"]


def test_ocr_artifact_cleaning_and_deduplication():
    """Validates cleaning of spurious characters (|{}[]) and entity deduplication."""
    noisy_name = "திரு. |{கே. ராமலிங்கம்}#"
    cleaned = entity_extractor._clean_text_artifacts(noisy_name)
    assert "|" not in cleaned
    assert "{" not in cleaned
    assert "#" not in cleaned

    # Test deduplication prioritizing verified over pending
    duplicate_entities = [
        {"entity_type": "taluk", "entity_value": "பெருந்துறை", "confidence": 0.85, "validation_status": "pending"},
        {"entity_type": "taluk", "entity_value": "பெருந்துறை", "confidence": 0.99, "validation_status": "verified"},
        {"entity_type": "phone", "entity_value": "9842156789", "confidence": 0.98, "validation_status": "verified"},
        {"entity_type": "phone", "entity_value": "9842156789", "confidence": 0.90, "validation_status": "pending"}
    ]
    deduped = entity_extractor._deduplicate_entities(duplicate_entities)
    assert len(deduped) == 2

    taluk_ent = next(e for e in deduped if e["entity_type"] == "taluk")
    assert taluk_ent["validation_status"] == "verified"
    assert taluk_ent["confidence"] == 0.99


def test_strict_aadhaar_security_masking():
    """Security check: raw 12-digit Aadhaar must never be stored plain."""
    raw_aadhaar = "9876 5432 1098"
    masked = entity_extractor._mask_aadhaar(raw_aadhaar)
    assert masked == "XXXX-XXXX-1098"
    assert "9876" not in masked
    assert "5432" not in masked


def test_seven_category_heuristic_classification():
    """Validates that all 7 government grievance categories correctly map to departments."""
    test_cases = [
        ("பட்டா பெயர் மாற்றம் மற்றும் சர்வே எண் அளவீடு", "நிலம்", "வருவாய்த்துறை"),
        ("கிராம தார் சாலை சேதமடைந்துள்ளது உடனே சீரமைக்கவும்", "சாலை", "நெடுஞ்சாலை & ஊரக வளர்ச்சி"),
        ("குடிநீர் குழாய் உடைப்பு ஏற்பட்டு நீர் விநியோகம் தடை", "குடிநீர்", "குடிநீர் வடிகால் வாரியம் & உள்ளாட்சி"),
        ("மின்கம்பம் சாய்ந்து மின்சாரம் தடைபட்டுள்ளது", "மின்சாரம்", "மின்சார வாரியம் (TANGEDCO)"),
        ("முதியோர் உதவித்தொகை (OAP Pension) வேண்டி மனு", "உதவித்தொகை", "சமூக நலத்துறை"),
        ("வருமான சான்றிதழ் மற்றும் வாரிசு சான்றிதழ் பெற மனு", "வருவாய்", "வருவாய்த்துறை"),
        ("சாக்கடை கழிவுநீர் தேங்கி கொசு மற்றும் சுகாதார சீர்கேடு", "சுகாதாரம்", "பொது சுகாதாரத்துறை")
    ]

    for text, expected_cat, expected_dept in test_cases:
        prompt = f"ஆவண உரை: {text} கீழ்கண்ட JSON வடிவில் விடையளி: JSON:"
        res_json_str = llm_client._heuristic_fallback(prompt)
        parsed = json.loads(res_json_str)
        assert parsed["grievance_type"] == expected_cat, f"Failed for {text}"
        assert parsed["department"] == expected_dept, f"Failed department for {text}"


def test_anti_hallucination_barrier():
    """Validates claim verification and grounding score computation against page chunks."""
    chunks = [
        {"page_number": 1, "chunk_text": "மனுதாரர் சுந்தரம் பெருந்துறை பகுதியில் பட்டா மாறுதல் கோரியுள்ளார்."},
        {"page_number": 2, "chunk_text": "இணைக்கப்பட்டுள்ள ஆவணங்கள்: மூல பத்திரம் மற்றும் சர்வே வரைபடம்."}
    ]

    analysis = {
        "description_summary_tamil": "சுந்தரம் பட்டா மாறுதல் மனு",
        "claims": [
            {"text": "சுந்தரம் பெருந்துறை பட்டா மாறுதல்", "source_page": 1, "confidence": 0.95},
            {"text": "மூல பத்திரம் சர்வே வரைபடம்", "source_page": 2, "confidence": 0.92},
            {"text": "அமெரிக்க விண்வெளி நிலையம் செல்ல கோரிக்கை", "source_page": 1, "confidence": 0.90}
        ]
    }

    verified = ai_analyzer._verify_claims(analysis, chunks)
    assert verified["claims"][0]["verified"] is True
    assert verified["claims"][1]["verified"] is True
    assert verified["claims"][2]["verified"] is False
    assert verified["hallucination_score"] == pytest.approx(0.33, 0.05)
    assert verified["grounding_score"] == pytest.approx(0.67, 0.05)


def test_file_store_image_dimension_validation(tmp_path):
    """Checks that corrupt or sub-dimension images are rejected early."""
    tiny_img_path = str(tmp_path / "tiny.png")
    tiny_img = Image.new("RGB", (30, 30), color=(255, 255, 255))
    tiny_img.save(tiny_img_path)

    import asyncio
    with pytest.raises(ValueError, match="Image too small"):
        asyncio.run(file_store.convert_document_to_images("test-src", tiny_img_path, "png"))


def test_enterprise_health_endpoint():
    """Checks that /health endpoint is operational with structured components."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "ocr" in data["components"]
        assert "storage" in data["components"]
        assert data["components"]["ocr"]["engine"].startswith("PaddleOCR")
        assert data["components"]["ocr"]["dpi"] == 200
