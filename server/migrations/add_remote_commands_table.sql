-- Migration: Add remote_commands table
-- Date: 2026-03-10
-- Purpose: Support remote Docker container management (start/stop/restart)

-- Check if table already exists and create if not
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'remote_commands') THEN
        CREATE TABLE remote_commands (
            id SERIAL PRIMARY KEY,
            host_id VARCHAR NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
            command_type VARCHAR NOT NULL,  -- 'docker_start', 'docker_stop', 'docker_restart'
            target_id VARCHAR NOT NULL,      -- container_id
            status VARCHAR DEFAULT 'pending' NOT NULL,  -- 'pending', 'executing', 'completed', 'failed'
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            executed_at TIMESTAMP WITH TIME ZONE,
            result TEXT  -- Success message or error details
        );
        
        CREATE INDEX idx_remote_commands_host_id ON remote_commands(host_id);
        CREATE INDEX idx_remote_commands_status ON remote_commands(status);
        CREATE INDEX idx_remote_commands_created_at ON remote_commands(created_at);
        
        RAISE NOTICE 'Table remote_commands created successfully';
    ELSE
        RAISE NOTICE 'Table remote_commands already exists, skipping';
    END IF;
END $$;
