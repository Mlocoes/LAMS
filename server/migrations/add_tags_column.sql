-- Migration: Add tags column to hosts table
-- Date: 2025-03-10
-- Description: Add JSON column for tags to enable host categorization

-- Add tags column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='hosts' AND column_name='tags'
    ) THEN
        ALTER TABLE hosts ADD COLUMN tags JSON DEFAULT '[]'::json;
        COMMENT ON COLUMN hosts.tags IS 'Tags for host categorization and filtering';
    END IF;
END $$;
