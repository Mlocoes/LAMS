-- Migration: Add UserSession table for Phase 3.1
-- Description: Implements session management with device tracking
-- Date: 2026-03-09
-- Phase: 3.1 - Session Management and Limits

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    refresh_token_id INTEGER REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    
    -- Device information
    device_name VARCHAR(255),
    device_type VARCHAR(50),  -- 'desktop', 'mobile', 'tablet', 'other'
    browser VARCHAR(100),
    os VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Create indexes for performance
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active);
CREATE INDEX idx_user_sessions_last_activity ON user_sessions(last_activity);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Add comments
COMMENT ON TABLE user_sessions IS 'Tracks user sessions with device information (Phase 3.1)';
COMMENT ON COLUMN user_sessions.session_token IS 'Unique session identifier (32-byte URL-safe token)';
COMMENT ON COLUMN user_sessions.refresh_token_id IS 'Associated refresh token (nullable for compatibility)';
COMMENT ON COLUMN user_sessions.device_type IS 'Device category: desktop, mobile, tablet, other';
COMMENT ON COLUMN user_sessions.last_activity IS 'Last activity timestamp (updated on API calls)';
COMMENT ON COLUMN user_sessions.expires_at IS 'Absolute session expiration (7 days from creation)';
COMMENT ON COLUMN user_sessions.is_active IS 'Whether session is still valid';

-- Cleanup job: Delete expired and inactive sessions older than 30 days
-- This should be run periodically (e.g., daily cron job)
-- DELETE FROM user_sessions 
-- WHERE (expires_at < NOW() OR is_active = FALSE)
--   AND created_at < NOW() - INTERVAL '30 days';
