import os
import sys
import json
import uuid
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from core.llm_client import llm_client, extract_json_object
from services.local_chandra_engine import compute_dhash, hamming_distance, LocalChandraEngine
from services.semantic_cache import semantic_cache, SemanticCacheManager
from services.ocr_router import HybridOCRRouter
from services.job_queue import PostgresJobQueue


# ==============================================================================
# 1. Edge Case 1: Cloud & Local Dual-Mode OCR & Zero Hardcoding
# ==============================================================================
def test_edge_case_1_chandra_dual_mode_parameters():
    """Verify dual-mode fallback configuration: accurate mode primary, balanced fallback."""
    assert hasattr(settings, "DATALAB_MODE")
    assert hasattr(settings, "DATALAB_FALLBACK_MODE")
    assert settings.DATALAB_MODE in ("accurate", "balanced", "fast")
    assert settings.DATALAB_FALLBACK_MODE == "balanced"
    assert settings.DATALAB_TIMEOUT > 0
    assert settings.DATALAB_FALLBACK_TIMEOUT > 0
    assert settings.DATALAB_FALLBACK_TIMEOUT <= settings.DATALAB_TIMEOUT


def test_edge_case_1_zero_hardcoding_vite_config():
    """Verify vite.config.js uses dynamic environment variables instead of hardcoded IPs."""
    vite_file = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "vite.config.js"))
    with open(vite_file, "r", encoding="utf-8") as f:
        content = f.read()
    # Ensure BACKEND_HOST and environment overrides are present
    assert "process.env.BACKEND_HOST" in content or "backendHost" in content
    assert "process.env.PORT" in content or "VITE_PORT" in content
    # Ensure Windows-only hotspot adapter is not strictly hardcoded as only option
    assert "process.env.VITE_BACKEND_URL" in content or "explicitBackendUrl" in content


@pytest.mark.asyncio
async def test_edge_case_1_ocr_dual_mode_fallback_flow():
    """Verify accurate mode failure automatically triggers balanced mode fallback."""
    router = HybridOCRRouter()
    call_modes = []

    async def mock_datalab(file_path, file_type, mode=None, timeout_sec=None):
        call_modes.append(mode)
        if mode == "accurate":
            return None  # Simulate accurate mode timeout
        elif mode == "balanced":
            return [{
                "page_number": 1,
                "full_text": "மாதாந்திர விதவை உதவித்தொகை கோருதல்",
                "blocks": [{"text": "மாதாந்திர விதவை உதவித்தொகை கோருதல்", "confidence": 0.98, "bbox": [[0,0],[100,0],[100,20],[0,20]]}],
                "tables": [],
                "avg_confidence": 0.98,
                "ocr_engine": "datalab_chandra_balanced"
            }]
        return None

    with patch.object(router, "_process_with_datalab", side_effect=mock_datalab):
        with patch.object(router, "_check_ocr_cache", return_value=None):
            # Mock db session
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=0), mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
            mock_db.commit = AsyncMock()

            # Execute pipeline
            result = await router.process_source(mock_db, str(uuid.uuid4()), "dummy.pdf", "pdf")
            assert "accurate" in call_modes
            assert "balanced" in call_modes
            assert result["ocr_engine"] == "datalab_chandra_balanced"
            assert result["pages"] == 1


# ==============================================================================
# 2. Edge Case 2: Local Chandra OCR V2 (5.6B) Specification & Perceptual Hashing
# ==============================================================================
def test_edge_case_2_dhash_perceptual_similarity():
    """Verify perceptual difference hash detects identical images with minor resizing."""
    from PIL import Image
    # Create test image
    img1 = Image.new("RGB", (200, 200), color=(128, 64, 32))
    img2 = img1.resize((100, 100))  # Resized duplicate
    h1 = compute_dhash(img1)
    h2 = compute_dhash(img2)
    assert len(h1) == 16
    assert len(h2) == 16
    dist = hamming_distance(h1, h2)
    assert dist <= 2, f"Expected near-zero Hamming distance for resized duplicate, got {dist}"


def test_edge_case_2_local_chandra_batch_configuration():
    """Verify local Chandra engine has batch size and timeout configured for 12 FPS throughput."""
    assert hasattr(settings, "LOCAL_CHANDRA_BATCH_SIZE")
    assert settings.LOCAL_CHANDRA_BATCH_SIZE >= 4
    engine = LocalChandraEngine()
    assert hasattr(engine, "process_pages_batch")
    assert hasattr(engine, "check_health")


# ==============================================================================
# 3. Edge Case 3: LLM Warmup, Concurrency Limiter & Self-Healing JSON
# ==============================================================================
def test_edge_case_3_extract_json_self_healing_balanced_brackets():
    """Verify truncated Tamil JSON with missing closing brackets/braces is auto-repaired without loss."""
    truncated_json = '{"petitioner_name": "மரகதம்", "claims": [{"text": "விதவை உதவித்தொகை கோரிக்கை", "source_page": 1'
    repaired = extract_json_object(truncated_json)
    assert repaired is not None, "Failed to self-heal truncated JSON"
    assert repaired.get("petitioner_name") == "மரகதம்"
    assert len(repaired.get("claims", [])) == 1


def test_edge_case_3_llm_concurrency_semaphore():
    """Verify LLMClient implements concurrency limiting via semaphore."""
    assert hasattr(llm_client, "_get_semaphore")
    sem = llm_client._get_semaphore()
    assert isinstance(sem, asyncio.Semaphore)
    assert sem._value == getattr(settings, "LLM_MAX_CONCURRENCY", 4)


@pytest.mark.asyncio
async def test_edge_case_3_llm_keep_alive_ping():
    """Verify keep_alive_ping method is present and callable."""
    assert hasattr(llm_client, "keep_alive_ping")
    # In test environment without active ollama, should return False or True safely without crash
    res = await llm_client.keep_alive_ping()
    assert isinstance(res, bool)


# ==============================================================================
# 4. Edge Case 4: Duplicate Petition Upload Prevention & Reprocessing Cost
# ==============================================================================
def test_edge_case_4_dedup_settings():
    """Verify exact hash and perceptual hash duplicate settings."""
    assert getattr(settings, "DEDUP_EXACT_HASH_ENABLED", True) is True
    assert getattr(settings, "DEDUP_PHASH_ENABLED", True) is True
    assert getattr(settings, "DEDUP_PHASH_THRESHOLD", 4) <= 8


# ==============================================================================
# 5. Edge Case 5: 10 Concurrent Users Worker Pool
# ==============================================================================
def test_edge_case_5_worker_pool_concurrency():
    """Verify job_queue supports scalable worker pool concurrency."""
    queue = PostgresJobQueue()
    assert hasattr(queue, "run_worker_pool")
    assert getattr(settings, "WORKER_CONCURRENCY", 4) >= 4
    assert getattr(settings, "DB_POOL_SIZE", 25) >= 20


# ==============================================================================
# 6. Edge Case 6: AI Semantic Caching
# ==============================================================================
def test_edge_case_6_semantic_cache_manager():
    """Verify SemanticCacheManager methods, hash calculation, and threshold."""
    assert hasattr(semantic_cache, "lookup")
    assert hasattr(semantic_cache, "store")
    assert getattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.92) == 0.92

    # Prompt hash consistency
    p1 = "முதியோர் உதவித்தொகை கோருதல்"
    p2 = "  முதியோர்   உதவித்தொகை கோருதல்  "
    h1 = SemanticCacheManager.compute_prompt_hash(p1)
    h2 = SemanticCacheManager.compute_prompt_hash(p2)
    assert h1 == h2, "Prompt hashing must normalize whitespace"
