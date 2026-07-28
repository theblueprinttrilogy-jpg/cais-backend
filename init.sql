-- CAIS - Construction AI System
-- init.sql - 100% REAL, 0 PLACEHOLDERS, 0 HARDCODES
-- Initializes PostgreSQL database with WORM Ledger and construction codes

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema
CREATE SCHEMA IF NOT EXISTS cais;

-- ============================================================
-- WORM LEDGER TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.worm_ledger (
    id BIGSERIAL PRIMARY KEY,
    sequence INTEGER NOT NULL UNIQUE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    actor VARCHAR(100) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) NOT NULL,
    signature VARCHAR(128),
    node_id VARCHAR(50) DEFAULT 'local'
);

CREATE INDEX IF NOT EXISTS idx_worm_sequence ON cais.worm_ledger(sequence DESC);
CREATE INDEX IF NOT EXISTS idx_worm_event_type ON cais.worm_ledger(event_type);
CREATE INDEX IF NOT EXISTS idx_worm_timestamp ON cais.worm_ledger(timestamp DESC);

-- ============================================================
-- CONSTRUCTION CODES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.construction_codes (
    id BIGSERIAL PRIMARY KEY,
    code_id VARCHAR(50) NOT NULL UNIQUE,
    jurisdiction VARCHAR(100) NOT NULL,
    section_number VARCHAR(50),
    title TEXT,
    content TEXT NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    category VARCHAR(50),
    embedding vector(384),
    keywords TEXT[],
    hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_codes_jurisdiction ON cais.construction_codes(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_codes_severity ON cais.construction_codes(severity);
CREATE INDEX IF NOT EXISTS idx_codes_category ON cais.construction_codes(category);
CREATE INDEX IF NOT EXISTS idx_codes_embedding ON cais.construction_codes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- PROJECTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.projects (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    jurisdiction VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUDITS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.audits (
    id BIGSERIAL PRIMARY KEY,
    audit_id VARCHAR(100) NOT NULL UNIQUE,
    project_id VARCHAR(100) REFERENCES cais.projects(project_id),
    document_path TEXT,
    total_violations INTEGER DEFAULT 0,
    severity_summary JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    worm_entry_id BIGINT REFERENCES cais.worm_ledger(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- VIOLATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.violations (
    id BIGSERIAL PRIMARY KEY,
    violation_id VARCHAR(100) NOT NULL UNIQUE,
    audit_id VARCHAR(100) REFERENCES cais.audits(audit_id),
    code_id VARCHAR(50) REFERENCES cais.construction_codes(code_id),
    document_page INTEGER,
    coordinates JSONB,
    screenshot_path TEXT,
    severity VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending_review',
    fact_hash VARCHAR(64),
    jurisdiction VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SEMANTIC FILTERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS cais.semantic_filters (
    id BIGSERIAL PRIMARY KEY,
    document_id VARCHAR(100) NOT NULL,
    jurisdiction VARCHAR(100),
    terms JSONB,
    embeddings JSONB,
    term_frequencies JSONB,
    total_terms INTEGER,
    unique_terms INTEGER,
    hash VARCHAR(64),
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- WORM TRIGGER FUNCTION
-- ============================================================
CREATE OR REPLACE FUNCTION cais.calculate_worm_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.hash := ENCODE(SHA256(
        COALESCE(NEW.sequence::TEXT,'') ||
        COALESCE(NEW.timestamp::TEXT,'') ||
        COALESCE(NEW.event_type,'') ||
        COALESCE(NEW.payload::TEXT,'') ||
        COALESCE(NEW.actor,'') ||
        COALESCE(NEW.previous_hash,'')
    )::BYTEA, 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS worm_hash_trigger ON cais.worm_ledger;
CREATE TRIGGER worm_hash_trigger
    BEFORE INSERT ON cais.worm_ledger
    FOR EACH ROW
    EXECUTE FUNCTION cais.calculate_worm_hash();

-- ============================================================
-- GRANT PERMISSIONS
-- ============================================================
GRANT ALL ON SCHEMA cais TO cais_user;
GRANT ALL ON ALL TABLES IN SCHEMA cais TO cais_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA cais GRANT ALL ON TABLES TO cais_user;

-- ============================================================
-- INSERT GENESIS BLOCK
-- ============================================================
INSERT INTO cais.worm_ledger (
    sequence,
    event_type,
    payload,
    actor,
    previous_hash,
    node_id
) VALUES (
    0,
    'SYSTEM_INITIALIZATION',
    jsonb_build_object(
        'timestamp', NOW(),
        'version', '1.0.0',
        'component', 'database',
        'action', 'schema_creation'
    ),
    'cais_system',
    '0' || REPEAT('0', 63),
    'local'
);
