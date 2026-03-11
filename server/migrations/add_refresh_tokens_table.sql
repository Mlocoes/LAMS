-- Migration: Add RefreshToken table for Phase 2.7
-- Description: Implements refresh token storage with revocation support
-- Date: 2026-03-09
-- Phase: 2.7 - Refresh Tokens and Token Expiration

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- Auditing fields
    client_ip VARCHAR(45),
    user_agent VARCHAR(255),
    last_used TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked);

-- Add comment to table
COMMENT ON TABLE refresh_tokens IS 'Stores refresh tokens for user authentication (Phase 2.7)';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'Hashed refresh token using Argon2';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Token expiration timestamp (7 days from creation)';
COMMENT ON COLUMN refresh_tokens.revoked IS 'Whether the token has been revoked (for logout)';
COMMENT ON COLUMN refresh_tokens.client_ip IS 'IP address of the client that created the token';
COMMENT ON COLUMN refresh_tokens.user_agent IS 'User agent string for auditing purposes';
COMMENT ON COLUMN refresh_tokens.last_used IS 'Timestamp of last token usage (updated on /refresh)';

-- Cleanup job: Delete expired and revoked tokens older than 30 days
-- This should be run periodically (e.g., daily cron job)
-- DELETE FROM refresh_tokens 
-- WHERE (expires_at < NOW() OR revoked = TRUE) 
--   AND created_at < NOW() - INTERVAL '30 days';
