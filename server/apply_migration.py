#!/usr/bin/env python3
"""
Apply database migration to add tags column to hosts table.
This script can be run manually or will be applied automatically on server startup.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import from server modules
sys.path.insert(0, str(Path(__file__).parent))

from database.database import engine
from sqlalchemy import text

async def apply_migration():
    """Apply the tags column migration"""
    migration_file = Path(__file__).parent / "migrations" / "add_tags_column.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        async with engine.begin() as conn:
            print("📦 Reading migration file...")
            migration_sql = migration_file.read_text()
            
            print("🔄 Applying migration: add tags column to hosts table...")
            await conn.execute(text(migration_sql))
            
            print("✅ Migration applied successfully!")
            
            # Verify the column was added
            result = await conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'hosts' AND column_name = 'tags'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✓ Column 'tags' confirmed: {row[1]} with default {row[2]}")
            else:
                print("⚠️  Could not verify column creation")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

async def main():
    print("=" * 60)
    print("LAMS Database Migration - Add Tags Column")
    print("=" * 60)
    
    success = await apply_migration()
    
    await engine.dispose()
    
    if success:
        print("\n✅ Migration completed successfully")
        return 0
    else:
        print("\n❌ Migration failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
