"""Allow preprocess in job_queue job_type check constraint

Revision ID: 003_allow_preprocess_job_type
Revises: 002_production_hardening_v01
Create Date: 2026-09-10 15:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_allow_preprocess_job_type'
down_revision: Union[str, None] = '002_production_hardening_v01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;")
    op.execute("""
    ALTER TABLE job_queue ADD CONSTRAINT job_queue_job_type_check 
        CHECK (job_type IN ('preprocess', 'ocr', 'entity_extraction', 'ai_analysis', 'vector_indexing'));
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;")
    op.execute("""
    ALTER TABLE job_queue ADD CONSTRAINT job_queue_job_type_check 
        CHECK (job_type IN ('ocr', 'entity_extraction', 'ai_analysis', 'vector_indexing'));
    """)
