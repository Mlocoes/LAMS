-- Phase 3.5: Key Rotation (Encryption Key Versioning)
-- Migration to add encryption_keys table for key rotation support

CREATE TABLE IF NOT EXISTS encryption_keys (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    key_encrypted TEXT NOT NULL,  -- Encrypted with master key (environment variable)
    algorithm VARCHAR(50) NOT NULL DEFAULT 'fernet',  -- 'fernet' for now, extensible
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rotated_at TIMESTAMP,  -- When this key was rotated (replaced)
    is_active BOOLEAN NOT NULL DEFAULT TRUE,  -- Only one active key at a time
    created_by VARCHAR(255),  -- Admin who created the key
    notes TEXT  -- Optional notes about the key rotation
);

-- Index for lookups
CREATE INDEX idx_encryption_keys_version ON encryption_keys(version);
CREATE INDEX idx_encryption_keys_active ON encryption_keys(is_active);
CREATE INDEX idx_encryption_keys_created_at ON encryption_keys(created_at);

-- Constraint: Only one active key allowed
CREATE UNIQUE INDEX idx_encryption_keys_single_active 
    ON encryption_keys(is_active) 
    WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE encryption_keys IS 'Phase 3.5: Stores versioned encryption keys for key rotation. Supports graceful key transitions.';
COMMENT ON COLUMN encryption_keys.key_encrypted IS 'Fernet key encrypted with master key from MASTER_ENCRYPTION_KEY env var';
COMMENT ON COLUMN encryption_keys.version IS 'Incrementing version number. Higher = newer.';
COMMENT ON COLUMN encryption_keys.is_active IS 'Current active key for new encryptions. Only one can be active.';

-- Add key_version column to tables that store encrypted data
-- This allows decrypting with the correct key version

-- For user_mfa table
ALTER TABLE user_mfa 
ADD COLUMN IF NOT EXISTS key_version INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_user_mfa_key_version ON user_mfa(key_version);

COMMENT ON COLUMN user_mfa.key_version IS 'Version of encryption key used for mfa_secret';
