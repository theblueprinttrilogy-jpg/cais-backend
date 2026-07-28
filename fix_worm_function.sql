-- Habilitar pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Reemplazar la función con digest()
CREATE OR REPLACE FUNCTION cais.calculate_worm_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.hash := ENCODE(
        digest(
            COALESCE(NEW.sequence::TEXT,'') ||
            COALESCE(NEW.timestamp::TEXT,'') ||
            COALESCE(NEW.event_type,'') ||
            COALESCE(NEW.payload::TEXT,'') ||
            COALESCE(NEW.actor,'') ||
            COALESCE(NEW.previous_hash,''),
            'sha256'
        ),
        'hex'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recrear el trigger
DROP TRIGGER IF EXISTS worm_hash_trigger ON cais.worm_ledger;
CREATE TRIGGER worm_hash_trigger
    BEFORE INSERT ON cais.worm_ledger
    FOR EACH ROW
    EXECUTE FUNCTION cais.calculate_worm_hash();

-- Insertar el bloque génesis
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
