#!/usr/bin/env python3
"""
Encrypt existing sensitive data in database (Phase 3.4)

This script encrypts sensitive fields that are currently stored in plaintext.

IMPORTANT:
1. BACKUP YOUR DATABASE before running this script!
2. Set ENCRYPTION_KEY in .env before running
3. This script is idempotent - safe to run multiple times
4. Fields already encrypted will be skipped

Usage:
    python encrypt_existing_data.py [--dry-run]

Options:
    --dry-run    Show what would be encrypted without making changes
"""

import asyncio
import argparse
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Add parent directory to path
sys.path.insert(0, '/home/mloco/Escritorio/LAMS/server')

from database.db import AsyncSessionLocal
from database.models import UserMFA, NotificationConfig
from services.encryption_service import get_encryption_service
import json


async def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be already encrypted.
    Fernet encrypted values start with 'gAAAAA' (base64 of version byte)
    """
    if not value:
        return False
    return value.startswith('gAAAAA')


async def encrypt_mfa_secrets(db: AsyncSession, dry_run: bool = False):
    """
    Encrypt MFA secrets that are currently in plaintext.
    
    Args:
        db: Database session
        dry_run: If True, don't make changes
    """
    encryption_service = get_encryption_service()
    
    print("\n🔐 Encrypting MFA secrets...")
    
    # Get all MFA records with secrets
    stmt = select(UserMFA).where(
        UserMFA.mfa_secret.isnot(None),
        UserMFA.mfa_secret != ''
    )
    result = await db.execute(stmt)
    mfa_records = result.scalars().all()
    
    encrypted_count = 0
    skipped_count = 0
    
    for mfa in mfa_records:
        # Check if already encrypted
        if await is_encrypted(mfa.mfa_secret):
            print(f"  ⏭️  User {mfa.user_id}: Already encrypted, skipping")
            skipped_count += 1
            continue
        
        if dry_run:
            print(f"  🔄 User {mfa.user_id}: Would encrypt MFA secret")
            encrypted_count += 1
        else:
            # Encrypt the secret
            encrypted_secret = encryption_service.encrypt(mfa.mfa_secret)
            mfa.mfa_secret = encrypted_secret
            print(f"  ✅ User {mfa.user_id}: MFA secret encrypted")
            encrypted_count += 1
    
    if not dry_run and encrypted_count > 0:
        await db.commit()
    
    print(f"\n  Total: {encrypted_count} encrypted, {skipped_count} skipped")
    return encrypted_count


async def encrypt_notification_configs(db: AsyncSession, dry_run: bool = False):
    """
    Encrypt notification config JSON that may contain sensitive webhooks/credentials.
    
    Args:
        db: Database session
        dry_run: If True, don't make changes
    """
    encryption_service = get_encryption_service()
    
    print("\n🔐 Encrypting notification configs...")
    
    # Get all notification configs
    stmt = select(NotificationConfig).where(
        NotificationConfig.config.isnot(None)
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()
    
    encrypted_count = 0
    skipped_count = 0
    
    for config in configs:
        # Convert JSON to string for encryption check
        config_str = json.dumps(config.config)
        
        # Check if already encrypted (if config_str starts with gAAAAA, it's encrypted)
        # Note: This is a heuristic - encrypted JSON won't be valid JSON
        if await is_encrypted(config_str):
            print(f"  ⏭️  Config {config.id} ({config.provider}): Already encrypted, skipping")
            skipped_count += 1
            continue
        
        if dry_run:
            print(f"  🔄 Config {config.id} ({config.provider}): Would encrypt")
            encrypted_count += 1
        else:
            # Encrypt the config JSON
            config_str = json.dumps(config.config)
            encrypted_config = encryption_service.encrypt(config_str)
            # Store encrypted string in JSON field (wrap in object for JSON compatibility)
            config.config = {"_encrypted": encrypted_config}
            print(f"  ✅ Config {config.id} ({config.provider}): Config encrypted")
            encrypted_count += 1
    
    if not dry_run and encrypted_count > 0:
        await db.commit()
    
    print(f"\n  Total: {encrypted_count} encrypted, {skipped_count} skipped")
    return encrypted_count


async def main(dry_run: bool = False):
    """
    Main encryption routine.
    
    Args:
        dry_run: If True, show what would be encrypted without making changes
    """
    print("=" * 80)
    print("DATABASE ENCRYPTION TOOL (Phase 3.4)")
    print("=" * 80)
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    else:
        print("\n⚠️  LIVE MODE - Database will be modified!")
        print("⚠️  Make sure you have a backup!\n")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
    
    async with AsyncSessionLocal() as db:
        try:
            # Encrypt MFA secrets
            mfa_count = await encrypt_mfa_secrets(db, dry_run)
            
            # Encrypt notification configs
            # config_count = await encrypt_notification_configs(db, dry_run)
            # Note: Commenting out for now as it requires schema changes
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"MFA secrets encrypted: {mfa_count}")
            # print(f"Notification configs encrypted: {config_count}")
            
            if dry_run:
                print("\nℹ️  This was a dry run. Run without --dry-run to apply changes.")
            else:
                print("\n✅ Encryption completed successfully!")
                print("\n⚠️  IMPORTANT:")
                print("- Keep your ENCRYPTION_KEY secure")
                print("- Update your application to decrypt these fields when reading")
                print("- Test decryption with: python test_encryption.py")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if not dry_run:
                await db.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encrypt sensitive database fields")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be encrypted without making changes"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run))
