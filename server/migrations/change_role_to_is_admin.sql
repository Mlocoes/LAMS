-- Migration: Change User.role (string) to User.is_admin (boolean)
-- Date: 2026-03-10

-- Step 1: Add new is_admin column as boolean (default False)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Step 2: Migrate existing data (convert "Admin" role to is_admin=true)
UPDATE users SET is_admin = TRUE WHERE role = 'Admin';
UPDATE users SET is_admin = FALSE WHERE role != 'Admin' OR role IS NULL;

-- Step 3: Drop old role column
ALTER TABLE users DROP COLUMN IF EXISTS role;

-- Verification:
-- SELECT id, email, is_admin FROM users;
