-- Phase 3.2: Multi-Factor Authentication (MFA/TOTP)
-- Migration to add user_mfa table for 2FA functionality

CREATE TABLE IF NOT EXISTS user_mfa (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(32),  -- Base32 encoded TOTP secret (16 bytes = 26 chars base32)
    backup_codes TEXT,  -- JSON array of hashed backup codes
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enabled_at TIMESTAMP,  -- When MFA was enabled
    last_used_at TIMESTAMP,  -- Last successful MFA verification
    UNIQUE(user_id)  -- One MFA config per user
);

-- Index for lookups
CREATE INDEX idx_user_mfa_user_id ON user_mfa(user_id);
CREATE INDEX idx_user_mfa_enabled ON user_mfa(mfa_enabled);

-- Comment
COMMENT ON TABLE user_mfa IS 'Phase 3.2: Stores MFA/TOTP configuration for users. One record per user.';
COMMENT ON COLUMN user_mfa.mfa_secret IS 'Base32 encoded TOTP secret key (RFC 6238)';
COMMENT ON COLUMN user_mfa.backup_codes IS 'JSON array of argon2 hashed backup codes for account recovery';
