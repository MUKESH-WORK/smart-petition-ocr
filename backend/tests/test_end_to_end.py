import os
import sys
import io
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from services.tamil_chunker import tamil_chunker
from services.entity_extractor import entity_extractor
from services.vector_store import vector_store
from services.ai_analyzer import ai_analyzer


def create_test_image_bytes() -> bytes:
    """Creates a synthetic Tamil document image for live end-to-end test"""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "TAMIL NADU DRO GRIEVANCE PETITION", fill=(0, 0, 0))
    draw.text((50, 100), "Petitioner: Ramalingam, Gandhi Nagar, Perundurai", fill=(0, 0, 0))
    draw.text((50, 150), "Phone: 9842156789, Aadhaar: 1234 5678 9012", fill=(0, 0, 0))
    draw.text((50, 200), "Request: Patta Name Transfer Survey No: 142/2A", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_tamil_semantic_chunker():
    tamil_text = """
    தமிழ்நாடு அரசு மாவட்ட வருவாய் அலுவலர் அவர்களுக்கு வணக்கம்.
    எனது பெயர் கே. ராமலிங்கம். எனது பூர்வீக நிலத்திற்கு பட்டா மாறுதல் கோரி விண்ணப்பிக்கிறேன்.
    புல எண் 142/2A பெருந்துறை வட்டம் ஈரோடு மாவட்டத்தில் அமைந்துள்ளது.
    """
    chunks = tamil_chunker.split(tamil_text, page_number=1)
    assert len(chunks) > 0
    assert chunks[0]["page_number"] == 1
    assert "ராமலிங்கம்" in chunks[0]["text"]


def test_entity_extractor_regex_and_masking():
    sample_text = """
    விண்ணப்பதாரர்: கே. ராமலிங்கம்
    தொலைபேசி: +91 9842156789
    ஆதார் எண்: 4532 9876 1234
    புல எண்: 142/2A
    அஞ்சல் குறியீடு: 638052
    தொகை: ₹ 50,000 ரூபாய்
    """
    entities = entity_extractor._extract_regex(sample_text, page_number=1)
    extracted_map = {e["entity_type"]: e["entity_value"] for e in entities}

    # Verify Aadhaar masking: only last 4 digits visible
    assert "aadhaar" in extracted_map
    assert extracted_map["aadhaar"] == "XXXX-XXXX-1234"
    assert "4532" not in extracted_map["aadhaar"]

    # Verify Phone
    assert "phone" in extracted_map
    assert "9842156789" in extracted_map["phone"]

    # Verify Survey No
    assert "survey_no" in extracted_map
    assert extracted_map["survey_no"] == "142/2A"


def test_vector_store_embedding_shape():
    texts = ["பட்டா மாறுதல் கோரிக்கை மனு", "சாலை சீரமைப்பு மனு"]
    embeddings = vector_store.encode(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384


def test_ai_analyzer_claim_verification():
    chunks = [
        {"page_number": 1, "chunk_text": "மனுதாரர் ராமலிங்கம் நில பட்டா மாறுதல் கோரியுள்ளார்."}
    ]
    sample_analysis = {
        "description_summary_tamil": "ராமலிங்கம் பட்டா மாறுதல் கோரியுள்ளார்",
        "claims": [
            {"text": "ராமலிங்கம் நில பட்டா மாறுதல்", "source_page": 1, "confidence": 0.95},
            {"text": "விண்வெளி ஆராய்ச்சி கோரிக்கை", "source_page": 1, "confidence": 0.95}
        ]
    }
    verified = ai_analyzer._verify_claims(sample_analysis, chunks)
    assert verified["claims"][0]["verified"] is True
    assert verified["claims"][1]["verified"] is False
    assert verified["hallucination_score"] == 0.5
    assert verified["grounding_score"] == 0.5


def test_fastapi_root_endpoint():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "DRO Grievance AI Module"
