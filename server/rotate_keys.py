#!/usr/bin/env python3
"""
Rotate Encryption Keys (Phase 3.5)

This script rotates encryption keys and re-encrypts existing data.

IMPORTANT:
1. BACKUP YOUR DATABASE before running!
2. Set MASTER_ENCRYPTION_KEY in .env before running
3. This operation can take time with large datasets
4. Server should ideally be in maintenance mode during rotation

Usage:
    python rotate_keys.py [--force] [--skip-reencrypt]

Options:
    --force            Force rotation even if threshold not reached
    --skip-reencrypt   Rotate key but don't re-encrypt data (faster, but leaves old data)
"""

import asyncio
import argparse
import sys

# Add parent directory to path
sys.path.insert(0, '/home/mloco/Escritorio/LAMS/server')

from database.db import AsyncSessionLocal
from services.key_rotation_service import get_key_rotation_service


async def rotate_keys(force: bool = False, skip_reencrypt: bool = False):
    """
    Main key rotation routine.
    
    Args:
        force: Force rotation even if not needed
        skip_reencrypt: Skip re-encryption of existing data
    """
    print("=" * 80)
    print("ENCRYPTION KEY ROTATION TOOL (Phase 3.5)")
    print("=" * 80)
    print()
    
    service = get_key_rotation_service()
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if rotation is needed
            stats = await service.get_key_stats(db)
            
            print("Current Key Status:")
            print(f"  Total keys: {stats['total_keys']}")
            
            if stats['active_key']:
                active = stats['active_key']
                print(f"  Active key version: {active['version']}")
                print(f"  Key age: {active['age_days']} days")
                print(f"  Algorithm: {active['algorithm']}")
                print(f"  Rotation threshold: {stats['rotation_threshold_days']} days")
            else:
                print("  No active key found!")
            
            print()
            
            # Check if rotation needed
            if not force and not stats['rotation_needed']:
                print(f"✓ Key rotation not needed yet (age: {stats['active_key']['age_days']} days)")
                print(f"  Threshold: {stats['rotation_threshold_days']} days")
                print()
                print("Use --force to rotate anyway.")
                return
            
            if stats['rotation_needed']:
                print(f"⚠️  Key rotation RECOMMENDED (age: {stats['active_key']['age_days']} days)")
            else:
                print("⚠️  Forcing key rotation (--force flag)")
            
            print()
            print("⚠️  WARNING: This will:")
            print("  1. Generate a new encryption key")
            print("  2. Mark the old key as rotated")
            print("  3. Re-encrypt all data with the new key (if not skipped)")
            print()
            
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            
            print()
            print("🔄 Rotating encryption key...")
            
            # Get old version before rotation
            old_version = await service.get_active_key_version(db)
            
            # Rotate key
            new_key = await service.rotate_key(
                db,
                created_by="admin_script",
                notes="Manual key rotation via rotate_keys.py"
            )
            
            print(f"✅ New key created: version {new_key.version}")
            print()
            
            if skip_reencrypt:
                print("⏭️  Skipping data re-encryption (--skip-reencrypt flag)")
                print()
                print("⚠️  WARNING: Old data is still encrypted with old key!")
                print("   You must run re-encryption later:")
                print(f"   python rotate_keys.py --reencrypt-from {old_version} --reencrypt-to {new_key.version}")
            else:
                print("🔄 Re-encrypting existing data...")
                count = await service.reencrypt_data(db, old_version, new_key.version)
                print(f"✅ Re-encrypted {count} records")
            
            print()
            print("=" * 80)
            print("KEY ROTATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("Next steps:")
            print("1. Update ENCRYPTION_KEY in .env to use new key (optional, for consistency)")
            print("2. Monitor logs for decryption errors")
            print("3. Schedule next rotation in", stats['rotation_threshold_days'], "days")
            print()
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise


async def initialize_keys():
    """Create initial encryption key if none exists."""
    print("=" * 80)
    print("INITIALIZE ENCRYPTION KEYS (Phase 3.5)")
    print("=" * 80)
    print()
    
    service = get_key_rotation_service()
    
    async with AsyncSessionLocal() as db:
        try:
            stats = await service.get_key_stats(db)
            
            if stats['total_keys'] > 0:
                print(f"✓ Encryption keys already initialized ({stats['total_keys']} keys exist)")
                print(f"  Active version: {stats['active_key']['version']}")
                return
            
            print("No encryption keys found. Creating initial key...")
            print()
            print("This will:")
            print("1. Use current ENCRYPTION_KEY from .env")
            print("2. Encrypt it with MASTER_ENCRYPTION_KEY")
            print("3. Store as version 1")
            print()
            
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            
            key = await service.create_initial_key(db, created_by="admin_script")
            
            print()
            print(f"✅ Initial encryption key created (version {key.version})")
            print()
            print("Key rotation is now enabled!")
            print(f"Next rotation recommended in {service.KEY_ROTATION_DAYS} days")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Rotate encryption keys")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rotation even if threshold not reached"
    )
    parser.add_argument(
        "--skip-reencrypt",
        action="store_true",
        help="Skip re-encryption of existing data"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize encryption keys (first-time setup)"
    )
    
    args = parser.parse_args()
    
    if args.init:
        asyncio.run(initialize_keys())
    else:
        asyncio.run(rotate_keys(force=args.force, skip_reencrypt=args.skip_reencrypt))


if __name__ == "__main__":
    main()
