#!/usr/bin/env python3
"""
Check Encryption Key Rotation Status (Phase 3.5)

This script checks the status of encryption keys and whether rotation is needed.

Usage:
    python check_rotation_status.py [--verbose]
"""

import asyncio
import argparse
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/home/mloco/Escritorio/LAMS/server')

from database.db import AsyncSessionLocal
from services.key_rotation_service import get_key_rotation_service
from database.models import EncryptionKey
from sqlalchemy import select, func


async def check_status(verbose: bool = False):
    """Check encryption key rotation status."""
    print("=" * 80)
    print("ENCRYPTION KEY ROTATION STATUS")
    print("=" * 80)
    print()
    
    service = get_key_rotation_service()
    
    async with AsyncSessionLocal() as db:
        try:
            # Get overall stats
            stats = await service.get_key_stats(db)
            
            print("📊 Overview:")
            print(f"  Total keys: {stats['total_keys']}")
            print(f"  Oldest version: {stats.get('oldest_version', 'N/A')}")
            print(f"  Newest version: {stats.get('newest_version', 'N/A')}")
            print()
            
            if not stats['active_key']:
                print("❌ No active key found!")
                print("   Run: python rotate_keys.py --init")
                return
            
            active = stats['active_key']
            print("🔑 Active Key:")
            print(f"  Version: {active['version']}")
            print(f"  Created: {active['created_at']}")
            print(f"  Age: {active['age_days']} days")
            print(f"  Algorithm: {active['algorithm']}")
            print()
            
            # Rotation recommendation
            threshold = stats['rotation_threshold_days']
            age = active['age_days']
            
            print("♻️  Rotation Status:")
            print(f"  Threshold: {threshold} days")
            
            if stats['rotation_needed']:
                days_overdue = age - threshold
                print(f"  ⚠️  ROTATION RECOMMENDED (overdue by {days_overdue} days)")
                print()
                print("  Action required:")
                print("    python rotate_keys.py")
            else:
                days_remaining = threshold - age
                print(f"  ✅ Rotation not needed ({days_remaining} days remaining)")
                print()
                print(f"  Next rotation recommended after: {threshold - age} days")
            
            print()
            
            # Data encryption status
            if verbose:
                print("=" * 80)
                print("DETAILED KEY INFORMATION")
                print("=" * 80)
                print()
                
                # Get all keys
                result = await db.execute(
                    select(EncryptionKey)
                    .order_by(EncryptionKey.version.desc())
                )
                keys = result.scalars().all()
                
                print(f"Total Keys: {len(keys)}")
                print()
                
                for key in keys:
                    status = "🟢 ACTIVE" if key.is_active else "⚪ ROTATED"
                    print(f"{status} Version {key.version}:")
                    print(f"  Algorithm: {key.algorithm}")
                    print(f"  Created: {key.created_at}")
                    if key.rotated_at:
                        print(f"  Rotated: {key.rotated_at}")
                    if key.created_by:
                        print(f"  Created by: {key.created_by}")
                    if key.notes:
                        print(f"  Notes: {key.notes}")
                    print()
                
                # Check data encryption by version
                from database.models import UserMFA
                
                result = await db.execute(
                    select(
                        UserMFA.key_version,
                        func.count(UserMFA.id).label('count')
                    )
                    .where(UserMFA.mfa_enabled == True)
                    .group_by(UserMFA.key_version)
                    .order_by(UserMFA.key_version)
                )
                
                version_counts = result.all()
                
                if version_counts:
                    print("=" * 80)
                    print("DATA ENCRYPTION STATUS (MFA Secrets)")
                    print("=" * 80)
                    print()
                    
                    total_records = sum(row.count for row in version_counts)
                    
                    for row in version_counts:
                        version = row.key_version
                        count = row.count
                        percentage = (count / total_records * 100) if total_records > 0 else 0
                        
                        status = "🟢 CURRENT" if version == active['version'] else "⚪ OLD"
                        print(f"{status} Version {version}: {count} records ({percentage:.1f}%)")
                    
                    print()
                    print(f"Total encrypted records: {total_records}")
                    
                    # Check if re-encryption needed
                    old_versions = [row for row in version_counts if row.key_version != active['version']]
                    if old_versions:
                        old_count = sum(row.count for row in old_versions)
                        print()
                        print(f"⚠️  {old_count} records encrypted with old key versions")
                        print("   Consider re-encrypting:")
                        print("     python rotate_keys.py --reencrypt")
                    else:
                        print()
                        print("✅ All records encrypted with current key version")
                
                print()
            
            print("=" * 80)
            print("TIP: Use --verbose for detailed key information")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise


async def check_health():
    """Quick health check for encryption keys."""
    service = get_key_rotation_service()
    
    async with AsyncSessionLocal() as db:
        try:
            stats = await service.get_key_stats(db)
            
            if stats['total_keys'] == 0:
                print("❌ UNHEALTHY: No encryption keys found")
                sys.exit(1)
            
            if not stats['active_key']:
                print("❌ UNHEALTHY: No active key")
                sys.exit(1)
            
            if stats['rotation_needed']:
                print(f"⚠️  WARNING: Key rotation overdue ({stats['active_key']['age_days']} days)")
                sys.exit(2)
            
            print("✅ HEALTHY: Encryption keys OK")
            sys.exit(0)
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check encryption key rotation status")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed key information"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Health check mode (exit codes: 0=OK, 1=ERROR, 2=ROTATION_NEEDED)"
    )
    
    args = parser.parse_args()
    
    if args.health:
        asyncio.run(check_health())
    else:
        asyncio.run(check_status(verbose=args.verbose))


if __name__ == "__main__":
    main()
