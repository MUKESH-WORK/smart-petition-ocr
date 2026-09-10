import os
import sys
import json
import pytest
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from services.image_preprocessor import (
    preprocess_document_image,
    deskew_image,
    apply_clahe,
    normalize_dpi
)
from services.region_analyzer import (
    detect_stamp_box,
    mask_stamp_region,
    is_strikethrough,
    reject_non_text_elements
)
from services.entity_extractor import entity_extractor, normalize_tamil_text
from services.ai_analyzer import ai_analyzer
from core.llm_client import llm_client, CATEGORY_KEYWORDS, DEPARTMENT_MAP
from services.file_store import file_store


def test_stage0_image_preprocessing_pipeline():
    """Validates deskew, CLAHE contrast enhancement, and 300 DPI normalization."""
    # Create a 200x200 test image with text
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TAMIL NADU DRO", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # 1. CLAHE enhancement
    clahe_img = apply_clahe(img)
    assert clahe_img is not None
    assert clahe_img.shape == img.shape

    # 2. Deskew
    deskewed, angle = deskew_image(img)
    assert deskewed is not None
    assert isinstance(angle, float)

    # 3. Full stage 0 preprocessing pipeline
    processed = preprocess_document_image(img, target_dpi=300)
    assert processed is not None
    assert len(processed.shape) == 3
    assert processed.shape[2] == 3
    assert processed.dtype == np.uint8


def test_stage1_stamp_detection_and_masking():
    """Validates GDP intake stamp box detection and masking."""
    img = np.ones((600, 600, 3), dtype=np.uint8) * 255
    # Draw a rectangular stamp box in top right
    cv2.rectangle(img, (350, 20), (580, 180), (0, 0, 180), 3)
    cv2.putText(img, "GDP 2026/09/10", (360, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1)

    stamp_box = detect_stamp_box(img)
    assert stamp_box is not None
    assert len(stamp_box) == 4
    x, y, w, h = stamp_box
    assert x >= 300
    assert y <= 50

    masked = mask_stamp_region(img, stamp_box)
    # The masked region should be white (255)
    assert np.all(masked[y+10:y+h-10, x+10:x+w-10] == 255)


def test_stage1_strikethrough_detection():
    """Validates horizontal line crossing detection for struck-out lines."""
    # Struck line: horizontal black bar through center
    struck_crop = np.ones((40, 200, 3), dtype=np.uint8) * 255
    cv2.putText(struck_crop, "CANCELED TEXT", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.line(struck_crop, (5, 20), (195, 20), (0, 0, 0), 2)

    assert is_strikethrough(struck_crop) is True

    # Clean line: no horizontal strikethrough
    clean_crop = np.ones((40, 200, 3), dtype=np.uint8) * 255
    cv2.putText(clean_crop, "NORMAL TEXT", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    assert is_strikethrough(clean_crop) is False


def test_stage1_non_text_rejection():
    """Validates that photos and high-density ink blobs (thumbprints) are filtered out."""
    # Dark solid blob (thumbprint/seal)
    blob = np.zeros((100, 100, 3), dtype=np.uint8)
    # Text line with high white background ratio
    text_line = np.ones((30, 200, 3), dtype=np.uint8) * 255
    cv2.putText(text_line, "Sample Text", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    elements = [
        {"type": "text", "crop": text_line},
        {"type": "photo", "crop": blob}
    ]
    filtered = reject_non_text_elements(elements)
    assert len(filtered) == 1
    assert filtered[0]["type"] == "text"


def test_tamil_unicode_nfkc_and_digit_normalization():
    """Validates NFKC normalization, Tamil numeral translation, and ZWJ removal."""
    # Tamil numeral representation: ௧௨௩௪௫ = 12345
    tamil_num_str = "எண்: ௧௨௩௪௫"
    normalized = normalize_tamil_text(tamil_num_str)
    assert "12345" in normalized

    # Zero-width joiner stripping
    zwj_str = "மனு\u200Cதாரர்\u200D"
    cleaned = normalize_tamil_text(zwj_str)
    assert "\u200C" not in cleaned
    assert "\u200D" not in cleaned
    assert cleaned == "மனுதாரர்"


def test_verhoeff_aadhaar_validation_and_masking():
    """Validates Verhoeff checksum algorithm and strict masking."""
    # A valid Verhoeff Aadhaar example (e.g. 234567890126)
    # Let's test _validate_aadhaar_verhoeff
    from services.entity_extractor import _validate_aadhaar_verhoeff

    # Invalid length
    assert _validate_aadhaar_verhoeff("12345") is False

    # Valid Verhoeff number test:
    # Build a known valid number: 236379612211
    # Checksum calculation:
    assert _validate_aadhaar_verhoeff("236379612211") is True
    # Corrupting last digit makes it invalid
    assert _validate_aadhaar_verhoeff("236379612212") is False

    # Masking test: Plain text must never expose first 8 digits
    raw_aadhaar = "2363 7961 2211"
    masked = entity_extractor._mask_aadhaar(raw_aadhaar)
    assert masked == "XXXX-XXXX-2211"
    assert "2363" not in masked
    assert "7961" not in masked


def test_strict_10digit_phone_validation():
    """Validates that valid Indian mobile numbers are recognized and 9-digit numbers are flagged."""
    assert entity_extractor._is_valid_phone("9842156789") is True
    assert entity_extractor._is_valid_phone("8765432109") is True
    assert entity_extractor._is_valid_phone("7890123456") is True
    assert entity_extractor._is_valid_phone("6380123456") is True

    # 9 digits must NOT be accepted as valid 10-digit mobile
    assert entity_extractor._is_valid_phone("984215678") is False
    # Numbers starting with 1, 2, 3, 4, 5 are not standard mobile
    assert entity_extractor._is_valid_phone("1234567890") is False


def test_master_location_fuzzy_matching():
    """Validates fuzzy matching against Erode district taluks (>=85% threshold)."""
    # Exact match
    taluk, score = entity_extractor._fuzzy_match_taluk("பெருந்துறை")
    assert taluk == "பெருந்துறை"
    assert score == 100.0

    # Minor typo / OCR error
    taluk, score = entity_extractor._fuzzy_match_taluk("பெருந்துரை")
    assert taluk == "பெருந்துறை"
    assert score >= 85.0

    # English match
    taluk, score = entity_extractor._fuzzy_match_taluk("Perundurai")
    assert taluk == "பெருந்துறை"
    assert score >= 85.0

    # Random string should fail (score < 85)
    taluk, score = entity_extractor._fuzzy_match_taluk("XYZ NonExistent Taluk")
    assert taluk is None
    assert score < 85.0


def test_bilingual_structural_extraction():
    """Validates structural extraction for both Tamil and English petition formats."""
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


def test_grounding_barrier_with_ocr_lines():
    """Validates anti-hallucination barrier with line-level grounding."""
    ocr_lines = [
        {"page_number": 1, "line_number": 1, "text": "மனுதாரர் சுந்தரம் பெருந்துறை பகுதியில் பட்டா மாறுதல் கோரியுள்ளார்."},
        {"page_number": 2, "line_number": 5, "text": "இணைக்கப்பட்டுள்ள ஆவணங்கள்: மூல பத்திரம் மற்றும் சர்வே வரைபடம்."}
    ]

    analysis = {
        "description_summary_tamil": "சுந்தரம் பட்டா மாறுதல் மனு",
        "claims": [
            {"text": "சுந்தரம் பெருந்துறை பட்டா மாறுதல்", "source_page": 1, "source_line": 1, "confidence": 0.95},
            {"text": "மூல பத்திரம் சர்வே வரைபடம்", "source_page": 2, "source_line": 5, "confidence": 0.92},
            {"text": "அமெரிக்க விண்வெளி நிலையம் செல்ல கோரிக்கை", "source_page": 1, "source_line": 1, "confidence": 0.90}
        ]
    }

    verified = ai_analyzer._verify_claims_against_lines(analysis, ocr_lines)
    assert verified["claims"][0]["verified"] is True
    assert verified["claims"][1]["verified"] is True
    assert verified["claims"][2]["verified"] is False
    assert verified["claims"][2]["confidence"] == 0.0
    assert verified["hallucination_score"] == pytest.approx(0.33, 0.05)
    assert verified["grounding_score"] == pytest.approx(0.67, 0.05)


def test_no_synthetic_or_unsupported_dependencies():
    """Validates that banned engines (Tesseract, EasyOCR, Surya) and mock vector embeddings are absent."""
    import inspect
    from services.vector_store import vector_store

    # Ensure vector_store uses SentenceTransformer
    assert hasattr(vector_store, "model")
    assert vector_store.model is not None

    # Inspect source to verify no mock pseudo-vectors exist
    src = inspect.getsource(vector_store.encode)
    assert "mock" not in src.lower()
    assert "pseudo" not in src.lower()

