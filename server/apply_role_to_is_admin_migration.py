#!/usr/bin/env python3
"""
Apply database migration to change User.role (string) to User.is_admin (boolean).
This script migrates existing data before applying the schema change.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import from server modules
sys.path.insert(0, str(Path(__file__).parent))

from database.database import engine
from sqlalchemy import text

async def apply_migration():
    """Apply the role to is_admin migration"""
    migration_file = Path(__file__).parent / "migrations" / "change_role_to_is_admin.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        async with engine.begin() as conn:
            print("📦 Reading migration file...")
            migration_sql = migration_file.read_text()
            
            # Check current state
            print("🔍 Checking current database schema...")
            result = await conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name IN ('role', 'is_admin')
            """))
            existing_columns = {row[0]: row[1] for row in result.fetchall()}
            
            if 'is_admin' in existing_columns and 'role' not in existing_columns:
                print("✅ Migration already applied (is_admin exists, role does not)")
                return True
            
            if 'is_admin' in existing_columns:
                print("⚠️  Column 'is_admin' already exists. Skipping column creation...")
                # Only run the UPDATE and DROP statements
                await conn.execute(text("UPDATE users SET is_admin = TRUE WHERE role = 'Admin'"))
                await conn.execute(text("UPDATE users SET is_admin = FALSE WHERE role != 'Admin' OR role IS NULL"))
                await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS role"))
            else:
                print("🔄 Applying migration: role (string) → is_admin (boolean)...")
                
                # Split and execute statements one by one
                statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
                
                for i, stmt in enumerate(statements, 1):
                    if stmt:
                        print(f"  Step {i}/{len(statements)}: Executing...")
                        await conn.execute(text(stmt))
            
            print("✅ Migration applied successfully!")
            
            # Verify the new column
            result = await conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'is_admin'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✓ Column 'is_admin' confirmed: {row[1]} with default {row[2]}")
                
                # Show migrated users
                result = await conn.execute(text("SELECT id, email, is_admin FROM users"))
                users = result.fetchall()
                print(f"\n📊 Migrated users ({len(users)}):")
                for user in users:
                    admin_label = "🛡️  ADMIN" if user[2] else "👤 USER"
                    print(f"  - {user[1]}: {admin_label}")
            else:
                print("⚠️  Could not verify column creation")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)
