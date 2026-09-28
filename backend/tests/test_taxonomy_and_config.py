import pytest
from app.config import settings
from services.taxonomy_matcher import (
    CANONICAL_PREDEFINED_TAXONOMY,
    taxonomy_matcher,
    CMHelplineTaxonomyValidator,
)


def test_settings_loaded():
    """Verify backend settings load with sensible defaults."""
    assert settings.PROJECT_NAME is not None
    assert settings.API_V1_STR == "/api/v1"
    assert settings.JWT_ALGORITHM == "HS256"


def test_taxonomy_predefined_list():
    """Verify canonical taxonomy contains valid department and officer structures."""
    assert len(CANONICAL_PREDEFINED_TAXONOMY) > 0

    first_item = CANONICAL_PREDEFINED_TAXONOMY[0]
    assert "department" in first_item
    assert "grievance_type" in first_item
    assert "responsible_officer" in first_item


def test_taxonomy_matcher_match():
    """Verify taxonomy matching returns structured department and officer for standard inputs."""
    result = taxonomy_matcher.match(
        petition_text="முதியோர் உதவித்தொகை வேண்டும்",
        detected_dept="Revenue and Disaster Management (REV)",
    )
    assert result is not None
    assert "department" in result
    assert "grievance_type" in result
    assert "responsible_officer" in result
