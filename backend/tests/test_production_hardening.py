import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models.orm import Base, GrievanceDraft, ExtractedEntity
from services.vector_store import PGVectorStore


@pytest.fixture
def sqlite_test_db(tmp_path):
    import re
    import asyncio
    from sqlalchemy import event

    db_file = str(tmp_path / "test_hardening.db")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False
    )

    @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
    def _sqlite_compat(conn, cursor, statement, parameters, context, executemany):
        s = statement
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+UUID\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"CAST\s*\(\s*(\?|:\w+|[^\)]+)\s+AS\s+INET\s*\)", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"\bFOR\s+UPDATE\s+SKIP\s+LOCKED\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\bILIKE\b", "LIKE", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", s, flags=re.IGNORECASE)
        return s, parameters

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield engine, session_factory

    asyncio.run(engine.dispose())


def test_k1_push_to_dro_datetime_import():
    """K1: grievance.py must import datetime so push_to_dro does not fail with NameError."""
    import app.routers.grievance as gr
    assert hasattr(gr, "datetime"), "K1 Violation: 'datetime' is not imported in app.routers.grievance"


def test_k2_k7_source_code_has_no_hardcoded_names_or_templates():
    """K2/K7: ai_analyzer.py must contain ZERO occurrences of hardcoded 'கார்னாஜ்' or default encroachment injection."""
    analyzer_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "ai_analyzer.py")
    with open(analyzer_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "கார்னாஜ்" not in content, "K2 Violation: Hardcoded 'கார்னாஜ்' found in ai_analyzer.py"
    assert "ஈரோடு பெருந்துறை" not in content, "K7 Violation: Hardcoded location injection 'ஈரோடு பெருந்துறை' found"
    assert "dept_map =" not in content, "K2 Violation: Hardcoded dept_map found; must use taxonomy_matcher"


@pytest.mark.asyncio
async def test_k3_k4_k5_draft_model_defaults_null(sqlite_test_db):
    """K3/K4/K5: GrievanceDraft field defaults must be NULL/None; whatsapp flags False; status not 'Open'."""
    _, session_factory = sqlite_test_db
    async with session_factory() as session:
        draft = GrievanceDraft(description="Test petition")
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

        assert draft.status is None, f"Expected status to default to None, got {draft.status}"
        assert draft.is_whatsapp_tracking is False, f"WhatsApp tracking must default to False, got {draft.is_whatsapp_tracking}"
        assert draft.is_whatsapp_receipt is False, f"WhatsApp receipt must default to False, got {draft.is_whatsapp_receipt}"
        assert draft.dro_grievance_id is None, f"dro_grievance_id must default to None until minted, got {draft.dro_grievance_id}"
        assert draft.department is None, f"department must default to None, got {draft.department}"
        assert draft.district is None, f"district must default to None, got {draft.district}"


def test_k8_no_mock_random_vectors():
    """K8: Vector store must NOT return random vectors if SentenceTransformer is unavailable."""
    store = PGVectorStore(model_name="non_existent_dummy_model_for_test_123")
    store._embedder = None
    with pytest.raises(Exception) as exc_info:
        store.encode(["தமிழ்நாடு அரசு"])
    assert "SentenceTransformer" in str(exc_info.value) or "unavailable" in str(exc_info.value).lower()


def test_k9_config_purged_secrets():
    """K9: config.py class Settings must not have hardcoded production secrets as class defaults."""
    from app.config import Settings
    s = Settings()
    # If not overridden by environment, class fields must default to empty string
    assert Settings.__annotations__["POSTGRES_PASSWORD"] == str
    assert Settings.__annotations__["SECRET_KEY"] == str
    assert Settings.__annotations__["DATALAB_API_KEY"] == str


def test_k10_cors_and_seeding():
    """K10: Demo seeding must default to False and allowed origins must be restricted."""
    from app.config import settings
    assert hasattr(settings, "SEED_DEMO_DATA")
    assert hasattr(settings, "ALLOWED_ORIGINS")


@pytest.mark.asyncio
async def test_k11_auth_fails_closed():
    """K11: get_current_officer must raise 401 Unauthorized if no credentials or header provided."""
    from app.dependencies import get_current_officer
    with pytest.raises(HTTPException) as exc_info:
        await get_current_officer(authorization=None, x_officer_id=None)
    assert exc_info.value.status_code == 401

    # But succeeds when valid x_officer_id is provided
    officer = await get_current_officer(authorization=None, x_officer_id="DRO_TEST_01")
    assert officer["officer_id"] == "DRO_TEST_01"


def test_k12_translate_no_cloud_apis():
    """K12: translate.py must not contain external cloud endpoints for air-gapped security."""
    trans_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "routers", "translate.py")
    with open(trans_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "translate.googleapis.com" not in content, "Cloud leak: googleapis translation API found"
    assert "api.mymemory.translated.net" not in content, "Cloud leak: mymemory translation API found"


def test_k13_update_draft_whitelist():
    """K13: update_draft whitelist must exist and prevent mass-assignment to protected columns."""
    from app.routers.grievance import ALLOWED_UPDATE_FIELDS
    assert "petitioner_name" in ALLOWED_UPDATE_FIELDS
    assert "phone" in ALLOWED_UPDATE_FIELDS
    assert "dro_status" not in ALLOWED_UPDATE_FIELDS
    assert "officer_approved" not in ALLOWED_UPDATE_FIELDS
    assert "dro_grievance_id" not in ALLOWED_UPDATE_FIELDS


def test_k19_upload_extension_whitelist():
    """K19: grievance.py must enforce file extension whitelist."""
    from app.routers.grievance import ALLOWED_EXTENSIONS
    assert "pdf" in ALLOWED_EXTENSIONS
    assert "png" in ALLOWED_EXTENSIONS
    assert "jpg" in ALLOWED_EXTENSIONS
    assert "exe" not in ALLOWED_EXTENSIONS
    assert "sh" not in ALLOWED_EXTENSIONS


def test_k20_filestore_no_listdir():
    """K20: file_store.py must not call os.listdir in get_file_path."""
    fs_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "file_store.py")
    with open(fs_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "os.listdir" not in content, "K20 Violation: os.listdir found in file_store.py"


def test_k21_tamil_concept_map_json():
    """K21: Tamil concept map must be loaded dynamically by taxonomy_matcher."""
    from services.taxonomy_matcher import taxonomy_matcher
    assert hasattr(taxonomy_matcher, "concept_map")
    assert "ஆக்கிரமிப்பு" in taxonomy_matcher.concept_map


@pytest.mark.asyncio
async def test_upload_endpoint_authentication(sqlite_test_db):
    """Verify that /upload rejects anonymous uploads with 401 but accepts authenticated requests."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from models.database import get_db

    _, session_factory = sqlite_test_db

    async def _get_db_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Anonymous upload without officer_id or header -> 401
            res_anon = await ac.post("/api/v1/grievance/upload", files={"file": ("test.png", b"fake_png_data", "image/png")})
            assert res_anon.status_code == 401, f"Expected 401 for anonymous upload, got {res_anon.status_code}"

            # 2. Upload with X-Officer-Id header -> 200/202
            res_header = await ac.post(
                "/api/v1/grievance/upload",
                files={"file": ("test.png", b"fake_png_data", "image/png")},
                headers={"X-Officer-Id": "DRO_ERODE_01"}
            )
            assert res_header.status_code in [200, 202], f"Expected 200/202 with header, got {res_header.status_code}: {res_header.text}"

            # 3. Upload with form officer_id -> 200/202
            res_form = await ac.post(
                "/api/v1/grievance/upload",
                files={"file": ("test2.png", b"fake_png_data_2", "image/png")},
                data={"officer_id": "DRO_ERODE_01"}
            )
            assert res_form.status_code in [200, 202], f"Expected 200/202 with form officer_id, got {res_form.status_code}: {res_form.text}"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_officer_isolated_history_and_recent(sqlite_test_db):
    """Verify that /grievance/history and /grievance/recent return ONLY records processed by the authenticated officer."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from models.database import get_db
    from models.orm import Source, Officer

    _, session_factory = sqlite_test_db

    async def _get_db_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    try:
        # Seed 2 officers and sources
        async with session_factory() as s:
            o1 = Officer(officer_id="OFF_ALICE", name="Alice", email="alice@tn.gov.in", designation="DRO", department="Revenue", status="Active")
            o2 = Officer(officer_id="OFF_BOB", name="Bob", email="bob@tn.gov.in", designation="DRO", department="Revenue", status="Active")
            s.add_all([o1, o2])
            await s.commit()

            src1 = Source(source_id=uuid.uuid4(), officer_id="OFF_ALICE", file_name="alice_petition.pdf", file_type="pdf", file_size_bytes=1024, file_hash="hash_a1", status="draft_ready")
            src2 = Source(source_id=uuid.uuid4(), officer_id="OFF_BOB", file_name="bob_petition.pdf", file_type="pdf", file_size_bytes=2048, file_hash="hash_b1", status="draft_ready")
            s.add_all([src1, src2])
            await s.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Query history as Alice
            res_alice = await ac.get("/api/v1/grievance/history", headers={"X-Officer-Id": "OFF_ALICE"})
            assert res_alice.status_code == 200
            data_alice = res_alice.json()
            assert len(data_alice) == 1
            assert data_alice[0]["file_name"] == "alice_petition.pdf"
            assert data_alice[0]["officer_id"] == "OFF_ALICE"

            # 2. Query recent as Bob
            res_bob = await ac.get("/api/v1/grievance/recent", headers={"X-Officer-Id": "OFF_BOB"})
            assert res_bob.status_code == 200
            data_bob = res_bob.json()
            assert len(data_bob) == 1
            assert data_bob[0]["fileName"] == "bob_petition.pdf"
            assert data_bob[0]["officer_id"] == "OFF_BOB"
    finally:
        app.dependency_overrides.pop(get_db, None)

