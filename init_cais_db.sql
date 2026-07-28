-- Habilitar vector
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear esquema
CREATE SCHEMA IF NOT EXISTS cais;
GRANT ALL ON SCHEMA cais TO cais_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA cais GRANT ALL ON TABLES TO cais_user;

-- WORM LEDGER
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

-- CONSTRUCTION CODES
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
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- VIOLATIONS
CREATE TABLE IF NOT EXISTS cais.violations (
    id BIGSERIAL PRIMARY KEY,
    violation_id VARCHAR(100) NOT NULL UNIQUE,
    audit_id VARCHAR(100),
    code_id VARCHAR(50) REFERENCES cais.construction_codes(code_id),
    document_page INTEGER,
    coordinates JSONB,
    screenshot_path TEXT,
    severity VARCHAR(20),
    fact_hash VARCHAR(64),
    jurisdiction VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WORM trigger
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

-- Genesis block
INSERT INTO cais.worm_ledger (
    sequence, event_type, payload, actor, previous_hash, node_id
) VALUES (
    0,
    'SYSTEM_INITIALIZATION',
    jsonb_build_object('timestamp', NOW(), 'version', '1.0.0'),
    'cais_system',
    '0' || REPEAT('0', 63),
    'local'
);
