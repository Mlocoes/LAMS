-- Migration: Add notification_configs table
-- Date: 2026-03-10
-- Purpose: Support notification system for alerts (email, slack, discord)

-- Check if table already exists and create if not
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notification_configs') THEN
        CREATE TABLE notification_configs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider VARCHAR NOT NULL,  -- 'email', 'slack', 'discord'
            config JSONB NOT NULL,      -- Provider-specific configuration
            enabled BOOLEAN DEFAULT TRUE,
            severity_filter VARCHAR DEFAULT 'all',  -- 'all', 'warning', 'critical'
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX idx_notification_configs_user_id ON notification_configs(user_id);
        CREATE INDEX idx_notification_configs_enabled ON notification_configs(enabled);
        
        RAISE NOTICE 'Table notification_configs created successfully';
    ELSE
        RAISE NOTICE 'Table notification_configs already exists, skipping';
    END IF;
END $$;

-- Add update trigger for updated_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_notification_configs_updated_at'
    ) THEN
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $func$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql;

        CREATE TRIGGER update_notification_configs_updated_at
        BEFORE UPDATE ON notification_configs
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        
        RAISE NOTICE 'Trigger update_notification_configs_updated_at created successfully';
    ELSE
        RAISE NOTICE 'Trigger already exists, skipping';
    END IF;
END $$;
