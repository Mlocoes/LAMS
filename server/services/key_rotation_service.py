"""
Key Rotation Service for Encryption Key Management (Phase 3.5)

Implements secure key rotation with versioning:
- Generate new encryption keys
- Rotate keys periodically (default: 90 days)
- Re-encrypt data with new keys
- Maintain multiple key versions for graceful transitions
- Encrypt keys at rest with master key

Key rotation reduces risk from:
- Long-term key exposure
- Cryptanalysis attacks
- Compliance requirements (PCI-DSS, HIPAA)
"""

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, desc
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional, Dict

from database.models import EncryptionKey, UserMFA
from core.config import settings

logger = logging.getLogger("security")


class KeyRotationService:
    """Service for managing encryption key rotation"""
    
    def __init__(self):
        """Initialize with master key for encrypting keys at rest"""
        if not settings.MASTER_ENCRYPTION_KEY:
            raise ValueError("MASTER_ENCRYPTION_KEY must be set for key rotation")
        
        # Master Fernet instance (encrypts the encryption keys themselves)
        self._master_fernet = Fernet(settings.MASTER_ENCRYPTION_KEY.encode())
        
        # Cache of decrypted keys by version
        self._key_cache: Dict[int, Fernet] = {}
    
    async def get_active_key_version(self, db: AsyncSession) -> int:
        """
        Get the version of the currently active encryption key.
        
        Returns:
            int: Active key version
            
        Raises:
            ValueError: If no active key exists
        """
        stmt = select(EncryptionKey).where(EncryptionKey.is_active == True)
        result = await db.execute(stmt)
        active_key = result.scalar_one_or_none()
        
        if not active_key:
            raise ValueError("No active encryption key found")
        
        return active_key.version
    
    async def get_key_by_version(self, db: AsyncSession, version: int) -> Fernet:
        """
        Get Fernet instance for a specific key version.
        
        Caches decrypted keys for performance.
        
        Args:
            db: Database session
            version: Key version to retrieve
            
        Returns:
            Fernet: Cipher instance for that key version
            
        Raises:
            ValueError: If key version doesn't exist
        """
        # Check cache first
        if version in self._key_cache:
            return self._key_cache[version]
        
        # Load from database
        stmt = select(EncryptionKey).where(EncryptionKey.version == version)
        result = await db.execute(stmt)
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            raise ValueError(f"Encryption key version {version} not found")
        
        # Decrypt the key using master key
        decrypted_key = self._master_fernet.decrypt(key_record.key_encrypted.encode())
        
        # Create Fernet instance
        fernet = Fernet(decrypted_key)
        
        # Cache it
        self._key_cache[version] = fernet
        
        return fernet
    
    async def create_initial_key(self, db: AsyncSession, created_by: str = "system") -> EncryptionKey:
        """
        Create the initial encryption key (version 1).
        
        Should only be called during initial setup.
        
        Args:
            db: Database session
            created_by: Who created the key
            
        Returns:
            EncryptionKey: Created key record
            
        Raises:
            ValueError: If a key already exists
        """
        # Check if any key exists
        stmt = select(EncryptionKey).limit(1)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("Encryption keys already exist. Use rotate_key() instead.")
        
        # Use current ENCRYPTION_KEY from settings
        current_key = settings.ENCRYPTION_KEY
        
        # Encrypt it with master key
        encrypted_key = self._master_fernet.encrypt(current_key.encode())
        
        # Create record
        key_record = EncryptionKey(
            version=1,
            key_encrypted=encrypted_key.decode('ascii'),
            algorithm="fernet",
            is_active=True,
            created_by=created_by,
            notes="Initial encryption key"
        )
        
        db.add(key_record)
        await db.commit()
        await db.refresh(key_record)
        
        logger.info(
            "Initial encryption key created",
            extra={
                "version": 1,
                "created_by": created_by
            }
        )
        
        return key_record
    
    async def rotate_key(self, db: AsyncSession, created_by: str = "system", notes: Optional[str] = None) -> EncryptionKey:
        """
        Rotate to a new encryption key.
        
        Process:
        1. Get current active key
        2. Generate new key
        3. Mark old key as rotated
        4. Save new key as active
        5. Re-encrypt all data with new key
        
        Args:
            db: Database session
            created_by: Who initiated the rotation
            notes: Optional notes about the rotation
            
        Returns:
            EncryptionKey: New active key record
        """
        # Get current active key
        stmt = select(EncryptionKey).where(EncryptionKey.is_active == True)
        result = await db.execute(stmt)
        current_key = result.scalar_one_or_none()
        
        if not current_key:
            raise ValueError("No active key to rotate. Create initial key first.")
        
        old_version = current_key.version
        new_version = old_version + 1
        
        # Generate new Fernet key
        new_key_bytes = Fernet.generate_key()
        
        # Encrypt new key with master key
        encrypted_new_key = self._master_fernet.encrypt(new_key_bytes)
        
        # Mark old key as rotated
        current_key.is_active = False
        current_key.rotated_at = datetime.now(timezone.utc)
        
        # Create new key record
        new_key_record = EncryptionKey(
            version=new_version,
            key_encrypted=encrypted_new_key.decode('ascii'),
            algorithm="fernet",
            is_active=True,
            created_by=created_by,
            notes=notes or f"Key rotation from version {old_version}"
        )
        
        db.add(new_key_record)
        await db.commit()
        await db.refresh(new_key_record)
        
        # Clear cache (force reload)
        self._key_cache.clear()
        
        logger.info(
            "Encryption key rotated",
            extra={
                "old_version": old_version,
                "new_version": new_version,
                "created_by": created_by
            }
        )
        
        return new_key_record
    
    async def reencrypt_data(self, db: AsyncSession, old_version: int, new_version: int) -> int:
        """
        Re-encrypt data from old key version to new key version.
        
        Currently supports:
        - user_mfa.mfa_secret
        
        Args:
            db: Database session
            old_version: Old key version
            new_version: New key version
            
        Returns:
            int: Number of records re-encrypted
        """
        old_fernet = await self.get_key_by_version(db, old_version)
        new_fernet = await self.get_key_by_version(db, new_version)
        
        count = 0
        
        # Re-encrypt MFA secrets
        stmt = select(UserMFA).where(
            UserMFA.key_version == old_version,
            UserMFA.mfa_secret.isnot(None),
            UserMFA.mfa_secret != ''
        )
        result = await db.execute(stmt)
        mfa_records = result.scalars().all()
        
        for mfa in mfa_records:
            try:
                # Decrypt with old key
                decrypted = old_fernet.decrypt(mfa.mfa_secret.encode())
                
                # Re-encrypt with new key
                reencrypted = new_fernet.encrypt(decrypted)
                
                # Update record
                mfa.mfa_secret = reencrypted.decode('ascii')
                mfa.key_version = new_version
                
                count += 1
            except Exception as e:
                logger.error(
                    f"Failed to re-encrypt MFA secret for user {mfa.user_id}: {e}",
                    extra={"user_id": mfa.user_id, "error": str(e)}
                )
        
        await db.commit()
        
        logger.info(
            "Data re-encrypted",
            extra={
                "old_version": old_version,
                "new_version": new_version,
                "records_updated": count
            }
        )
        
        return count
    
    async def check_rotation_needed(self, db: AsyncSession) -> bool:
        """
        Check if key rotation is needed based on age.
        
        Args:
            db: Database session
            
        Returns:
            bool: True if rotation needed
        """
        stmt = select(EncryptionKey).where(EncryptionKey.is_active == True)
        result = await db.execute(stmt)
        active_key = result.scalar_one_or_none()
        
        if not active_key:
            return True  # No key exists
        
        # Check age
        age = datetime.now(timezone.utc) - active_key.created_at
        rotation_threshold = timedelta(days=settings.KEY_ROTATION_DAYS)
        
        return age >= rotation_threshold
    
    async def get_key_stats(self, db: AsyncSession) -> dict:
        """
        Get statistics about encryption keys.
        
        Returns:
            dict: Key statistics
        """
        # Get all keys
        stmt = select(EncryptionKey).order_by(desc(EncryptionKey.version))
        result = await db.execute(stmt)
        keys = result.scalars().all()
        
        if not keys:
            return {
                "total_keys": 0,
                "active_key": None,
                "rotation_needed": True
            }
        
        active_key = [k for k in keys if k.is_active][0] if any(k.is_active for k in keys) else None
        
        if active_key:
            age_days = (datetime.now(timezone.utc) - active_key.created_at).days
            rotation_needed = age_days >= settings.KEY_ROTATION_DAYS
        else:
            age_days = None
            rotation_needed = True
        
        return {
            "total_keys": len(keys),
            "active_key": {
                "version": active_key.version,
                "created_at": active_key.created_at.isoformat(),
                "age_days": age_days,
                "algorithm": active_key.algorithm
            } if active_key else None,
            "rotation_needed": rotation_needed,
            "rotation_threshold_days": settings.KEY_ROTATION_DAYS,
            "oldest_key_version": min(k.version for k in keys),
            "newest_key_version": max(k.version for k in keys)
        }


# Global singleton instance
_key_rotation_service: Optional[KeyRotationService] = None


def get_key_rotation_service() -> KeyRotationService:
    """
    Get or create global KeyRotationService instance.
    
    Returns:
        KeyRotationService singleton
    """
    global _key_rotation_service
    if _key_rotation_service is None:
        _key_rotation_service = KeyRotationService()
    return _key_rotation_service
