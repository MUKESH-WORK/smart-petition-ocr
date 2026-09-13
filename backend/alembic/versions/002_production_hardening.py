"""Production hardening pass: indexes, queue performance, and constraint idempotency

Revision ID: 002_production_hardening
Revises: 001_initial_schema
Create Date: 2026-09-12 16:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_production_hardening'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. High-throughput job queue composite index for SKIP LOCKED / atomic polling
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_job_queue_poll 
    ON job_queue (status, job_type, created_at ASC);
    """)

    # 2. Source deduplication and fast SHA256 lookup index
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_sources_file_hash 
    ON sources (file_hash);
    """)

    # 3. Entity verification status index
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_extracted_entities_status 
    ON extracted_entities (source_id, validation_status);
    """)

    # 4. Draft lookup by source_id and DRO official tracking ID
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_grievance_drafts_source 
    ON grievance_drafts (source_id);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_grievance_drafts_dro_id 
    ON grievance_drafts (dro_grievance_id);
    """)

    # 5. Audit log source lookup index
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_audit_log_source 
    ON audit_log (source_id, timestamp DESC);
    """)

    # 6. Update sources status check constraint to include intermediate pipeline states
    op.execute("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_status_check;")
    op.execute("""
    ALTER TABLE sources ADD CONSTRAINT sources_status_check 
    CHECK (status IN (
        'uploaded',
        'pending',
        'processing',
        'ocr_processing',
        'ocr_complete',
        'ocr_review',
        'vector_indexing',
        'vector_indexed',
        'entity_extracting',
        'entity_extracted',
        'ai_analyzing',
        'draft_ready',
        'officer_approved',
        'pushed_to_dro',
        'rejected',
        'completed',
        'failed'
    ));
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_status_check;")
    op.execute("DROP INDEX IF EXISTS idx_job_queue_poll;")
    op.execute("DROP INDEX IF EXISTS idx_sources_file_hash;")
    op.execute("DROP INDEX IF EXISTS idx_extracted_entities_status;")
    op.execute("DROP INDEX IF EXISTS idx_grievance_drafts_source;")
    op.execute("DROP INDEX IF EXISTS idx_grievance_drafts_dro_id;")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_source;")
