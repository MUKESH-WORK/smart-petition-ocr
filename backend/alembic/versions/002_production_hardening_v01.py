"""Production hardening V0.1: ocr_lines, stamp_parse, benchmark_runs, and entity review states

Revision ID: 002_production_hardening_v01
Revises: 001_initial_schema
Create Date: 2026-09-10 11:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_production_hardening_v01'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ocr_lines table for complete PP-OCRv5 per-line grounding (Fixes D1)
    op.execute("""
    CREATE TABLE IF NOT EXISTS ocr_lines (
        line_id BIGSERIAL PRIMARY KEY,
        source_id UUID NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
        page_number INT NOT NULL,
        line_index INT NOT NULL,
        polygon JSONB NOT NULL,
        text TEXT NOT NULL,
        score REAL,
        script VARCHAR(10) CHECK (script IN ('ta', 'en', 'mixed')),
        style VARCHAR(20) CHECK (style IN ('printed', 'handwritten')),
        struck BOOLEAN DEFAULT FALSE,
        region_type VARCHAR(20) DEFAULT 'body' CHECK (region_type IN ('body', 'stamp')),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ocr_lines_source_page ON ocr_lines(source_id, page_number)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ocr_lines_source_line ON ocr_lines(source_id, line_index)")

    # 2. stamp_parse table for GDP intake stamp extraction (Fixes D6)
    op.execute("""
    CREATE TABLE IF NOT EXISTS stamp_parse (
        source_id UUID PRIMARY KEY REFERENCES sources(source_id) ON DELETE CASCADE,
        stamp_found BOOLEAN NOT NULL,
        raw_cells JSONB NOT NULL,
        date_norm TEXT,
        department TEXT,
        subject TEXT,
        sub_subject TEXT,
        forwarding_officer TEXT,
        validation JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    # 3. Field-level review state on extracted_entities (Fixes D12, Officer Gate)
    op.execute("""
    ALTER TABLE extracted_entities 
    ADD COLUMN IF NOT EXISTS review_state VARCHAR(20) DEFAULT 'pending' 
        CHECK (review_state IN ('pending', 'confirmed', 'corrected', 'rejected'))
    """)
    op.execute("""
    ALTER TABLE extracted_entities 
    ADD COLUMN IF NOT EXISTS officer_note TEXT
    """)

    # 4. benchmark_runs table for empirical hardware and model comparisons (Section 5)
    op.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_runs (
        run_id BIGSERIAL PRIMARY KEY,
        run_type VARCHAR(50) NOT NULL,
        config JSONB NOT NULL,
        metrics JSONB NOT NULL,
        run_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS benchmark_runs CASCADE")
    op.execute("ALTER TABLE extracted_entities DROP COLUMN IF EXISTS review_state")
    op.execute("ALTER TABLE extracted_entities DROP COLUMN IF EXISTS officer_note")
    op.execute("DROP TABLE IF EXISTS stamp_parse CASCADE")
    op.execute("DROP TABLE IF EXISTS ocr_lines CASCADE")
