"""Initial database schema with pgvector, JSONB, tsvector, and partitions

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-02 11:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    op.execute('CREATE EXTENSION IF NOT EXISTS unaccent;')
    
    # Check if vector extension is available in PostgreSQL installation
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"))
    has_vector = res.scalar() is not None

    if has_vector:
        op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # 2. Master Locations
    op.execute("""
    CREATE TABLE IF NOT EXISTS master_locations (
        id SERIAL PRIMARY KEY,
        district_code VARCHAR(10) NOT NULL,
        district_name_tamil VARCHAR(100),
        taluk_code VARCHAR(10) NOT NULL,
        taluk_name_tamil VARCHAR(100),
        block_code VARCHAR(10),
        block_name_tamil VARCHAR(100),
        firka_code VARCHAR(10),
        firka_name_tamil VARCHAR(100),
        village_code VARCHAR(10),
        village_name_tamil VARCHAR(100),
        UNIQUE(district_code, taluk_code, block_code, firka_code, village_code)
    );
    """)

    # 3. Officers
    op.execute("""
    CREATE TABLE IF NOT EXISTS officers (
        officer_id VARCHAR(50) PRIMARY KEY,
        name_tamil VARCHAR(100),
        designation VARCHAR(100),
        department VARCHAR(50),
        taluk_access VARCHAR(10)[],
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # 4. Sources
    op.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        officer_id VARCHAR(50) REFERENCES officers(officer_id),
        file_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(20) CHECK (file_type IN ('pdf', 'png', 'jpg', 'jpeg', 'tiff', 'docx')),
        file_size_bytes INTEGER,
        file_hash VARCHAR(64) UNIQUE,
        page_count INTEGER DEFAULT 0,
        status VARCHAR(30) DEFAULT 'uploaded' 
            CHECK (status IN ('uploaded', 'ocr_processing', 'ocr_complete', 'entity_extracting', 'ai_analyzing', 'draft_ready', 'officer_approved', 'pushed_to_dro', 'rejected')),
        content_fingerprint JSONB,
        file_data BYTEA,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # 5. OCR Results
    op.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        id SERIAL PRIMARY KEY,
        source_id UUID REFERENCES sources(source_id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        full_text TEXT,
        blocks JSONB,
        tables JSONB,
        avg_confidence REAL CHECK (avg_confidence BETWEEN 0 AND 1),
        ocr_engine VARCHAR(50),
        processing_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(source_id, page_number)
    );
    """)

    # 6. Document Chunks
    if has_vector:
        op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_id UUID REFERENCES sources(source_id) ON DELETE CASCADE,
            page_number INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT NOT NULL,
            embedding VECTOR(384),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);")
    else:
        op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_id UUID REFERENCES sources(source_id) ON DELETE CASCADE,
            page_number INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT NOT NULL,
            embedding FLOAT8[],
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_fts ON document_chunks USING GIN (to_tsvector('simple', chunk_text));")
    op.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_source_id ON document_chunks(source_id);")

    # 7. Extracted Entities
    op.execute("""
    CREATE TABLE IF NOT EXISTS extracted_entities (
        id SERIAL PRIMARY KEY,
        source_id UUID REFERENCES sources(source_id) ON DELETE CASCADE,
        entity_type VARCHAR(50) NOT NULL,
        entity_value TEXT NOT NULL,
        confidence REAL,
        validation_status VARCHAR(20) DEFAULT 'pending' 
            CHECK (validation_status IN ('pending', 'verified', 'suspect', 'missing')),
        source_page INTEGER,
        source_chunk_id UUID REFERENCES document_chunks(id),
        extracted_by VARCHAR(20) DEFAULT 'regex' CHECK (extracted_by IN ('regex', 'ai_ner', 'master_db_lookup', 'officer_edit')),
        officer_corrected BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_extracted_entities_source_id ON extracted_entities(source_id);")

    # 8. AI Analysis
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_analysis (
        id SERIAL PRIMARY KEY,
        source_id UUID REFERENCES sources(source_id) ON DELETE CASCADE,
        grievance_type_suggested VARCHAR(100),
        grievance_subtype_suggested VARCHAR(100),
        department_suggested VARCHAR(100),
        priority_suggested VARCHAR(20) CHECK (priority_suggested IN ('HIGH', 'MEDIUM', 'LOW')),
        description_summary_tamil TEXT,
        description_summary_english TEXT,
        action_items JSONB,
        claims JSONB,
        hallucination_score REAL,
        grounding_score REAL,
        raw_ai_response JSONB,
        generated_at TIMESTAMP DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_source_id ON ai_analysis(source_id);")

    # 9. Grievance Drafts
    op.execute("""
    CREATE TABLE IF NOT EXISTS grievance_drafts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        source_id UUID REFERENCES sources(source_id),
        officer_id VARCHAR(50) REFERENCES officers(officer_id),
        petitioner_name VARCHAR(200),
        father_husband_name VARCHAR(200),
        address TEXT,
        phone VARCHAR(20),
        email VARCHAR(100),
        district VARCHAR(50),
        taluk VARCHAR(50),
        block VARCHAR(50),
        firka VARCHAR(50),
        village VARCHAR(50),
        department VARCHAR(100),
        grievance_type VARCHAR(100),
        grievance_subtype VARCHAR(100),
        description TEXT,
        priority VARCHAR(20),
        dro_grievance_id VARCHAR(100),
        dro_status VARCHAR(50) DEFAULT 'draft',
        officer_approved BOOLEAN DEFAULT FALSE,
        officer_notes TEXT,
        approved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_grievance_drafts_source_id ON grievance_drafts(source_id);")

    # 10. Job Queue
    op.execute("""
    CREATE TABLE IF NOT EXISTS job_queue (
        id SERIAL PRIMARY KEY,
        job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('ocr', 'entity_extraction', 'ai_analysis', 'vector_indexing')),
        source_id UUID REFERENCES sources(source_id),
        payload JSONB,
        status VARCHAR(20) DEFAULT 'pending' 
            CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
        worker_id VARCHAR(50),
        error_message TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP,
        completed_at TIMESTAMP
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_queue_pending ON job_queue (status, job_type, created_at) WHERE status = 'pending';")

    # 11. Audit Log (Partitioned)
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id BIGSERIAL,
        timestamp TIMESTAMP DEFAULT NOW(),
        source_id UUID,
        officer_id VARCHAR(50),
        action VARCHAR(100) NOT NULL,
        details JSONB,
        ip_address INET,
        PRIMARY KEY (id, timestamp)
    ) PARTITION BY RANGE (timestamp);
    """)

    partitions = [
        ("audit_log_y2026m01", "2026-01-01", "2026-02-01"),
        ("audit_log_y2026m02", "2026-02-01", "2026-03-01"),
        ("audit_log_y2026m03", "2026-03-01", "2026-04-01"),
        ("audit_log_y2026m04", "2026-04-01", "2026-05-01"),
        ("audit_log_y2026m05", "2026-05-01", "2026-06-01"),
        ("audit_log_y2026m06", "2026-06-01", "2026-07-01"),
        ("audit_log_y2026m07", "2026-07-01", "2026-08-01"),
        ("audit_log_y2026m08", "2026-08-01", "2026-09-01"),
        ("audit_log_y2026m09", "2026-09-01", "2026-10-01"),
        ("audit_log_y2026m10", "2026-10-01", "2026-11-01"),
        ("audit_log_y2026m11", "2026-11-01", "2026-12-01"),
        ("audit_log_y2026m12", "2026-12-01", "2027-01-01"),
    ]
    for part_name, start_d, end_d in partitions:
        op.execute(f"CREATE TABLE IF NOT EXISTS {part_name} PARTITION OF audit_log FOR VALUES FROM ('{start_d}') TO ('{end_d}');")
    op.execute("CREATE TABLE IF NOT EXISTS audit_log_default PARTITION OF audit_log DEFAULT;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS job_queue CASCADE;")
    op.execute("DROP TABLE IF EXISTS grievance_drafts CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_analysis CASCADE;")
    op.execute("DROP TABLE IF EXISTS extracted_entities CASCADE;")
    op.execute("DROP TABLE IF EXISTS document_chunks CASCADE;")
    op.execute("DROP TABLE IF EXISTS ocr_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS sources CASCADE;")
    op.execute("DROP TABLE IF EXISTS officers CASCADE;")
    op.execute("DROP TABLE IF EXISTS master_locations CASCADE;")
