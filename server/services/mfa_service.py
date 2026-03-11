"""
MFA Service for TOTP-based Two-Factor Authentication (Phase 3.2)

Implements RFC 6238 TOTP (Time-based One-Time Password) authentication:
- Generate TOTP secrets
- Generate QR codes for authenticator apps
- Verify TOTP codes
- Generate and verify backup codes
- Enable/disable MFA

Integrated with EncryptionService (Phase 3.4) and KeyRotationService (Phase 3.5)
for encrypted storage of MFA secrets.
"""

import pyotp
import qrcode
import io
import base64
import secrets
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import UserMFA, User
from auth.security import get_password_hash, verify_password
from core.config import settings
from services.encryption_service import get_encryption_service  # Phase 3.4
from services.key_rotation_service import get_key_rotation_service  # Phase 3.5

logger = logging.getLogger("security")


class MFAService:
    """Service for managing Multi-Factor Authentication"""
    
    @staticmethod
    async def setup_mfa(db: AsyncSession, user_id: int) -> dict:
        """
        Initialize MFA setup for a user.
        
        Generates a new TOTP secret and QR code.
        Does NOT enable MFA yet - user must verify first.
        
        Args:
            db: Database session
            user_id: User ID to setup MFA for
            
        Returns:
            dict with:
                - secret: Base32 encoded secret (for manual entry)
                - qr_code: Base64 encoded PNG image
                - backup_codes: List of plain backup codes (show once!)
        """
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        # Generate TOTP secret (16 bytes = 128 bits)
        secret = pyotp.random_base32()
        
        # Generate provisioning URI for QR code
        # Format: otpauth://totp/LAMS:user@email.com?secret=SECRET&issuer=LAMS
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="LAMS"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for JSON response
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_code_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Generate 10 backup codes (8 chars each)
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # Hash backup codes for storage
        hashed_backup_codes = [get_password_hash(code) for code in backup_codes]
        backup_codes_json = json.dumps(hashed_backup_codes)
        
        # Encrypt secret for storage (Phase 3.4)
        encryption_service = get_encryption_service()
        encrypted_secret = encryption_service.encrypt(secret)
        
        # Get current key version (Phase 3.5)
        key_rotation_service = get_key_rotation_service()
        key_version = await key_rotation_service.get_active_key_version(db)
        
        # Create or update MFA record (not enabled yet)
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if mfa:
            # Update existing
            mfa.mfa_secret = encrypted_secret
            mfa.backup_codes = backup_codes_json
            mfa.key_version = key_version
            mfa.mfa_enabled = False  # Reset to disabled until verified
        else:
            # Create new
            mfa = UserMFA(
                user_id=user_id,
                mfa_secret=encrypted_secret,
                backup_codes=backup_codes_json,
                key_version=key_version,
                mfa_enabled=False
            )
            db.add(mfa)
        
        await db.commit()
        
        logger.info(
            "MFA setup initiated",
            extra={
                "user_id": user_id,
                "email": user.email
            }
        )
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "backup_codes": backup_codes  # Plain codes - show once!
        }
    
    @staticmethod
    async def enable_mfa(db: AsyncSession, user_id: int, totp_code: str) -> bool:
        """
        Enable MFA after verifying TOTP code.
        
        User must provide a valid TOTP code to prove they can generate codes.
        
        Args:
            db: Database session
            user_id: User ID
            totp_code: 6-digit TOTP code from authenticator app
            
        Returns:
            bool: True if enabled successfully
            
        Raises:
            ValueError: If verification fails
        """
        # Get MFA record
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa or not mfa.mfa_secret:
            raise ValueError("MFA not set up. Call setup_mfa first.")
        
        if mfa.mfa_enabled:
            raise ValueError("MFA already enabled")
        
        # Decrypt secret (Phase 3.4/3.5)
        encryption_service = get_encryption_service()
        key_rotation_service = get_key_rotation_service()
        
        # Get the Fernet instance for this key version
        fernet = await key_rotation_service.get_key_by_version(db, mfa.key_version)
        secret = fernet.decrypt(mfa.mfa_secret.encode()).decode()
        
        # Verify TOTP code
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=1):
            logger.warning(
                "MFA enable failed - invalid code",
                extra={"user_id": user_id}
            )
            raise ValueError("Invalid TOTP code")
        
        # Enable MFA
        mfa.mfa_enabled = True
        mfa.enabled_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(
            "MFA enabled",
            extra={"user_id": user_id}
        )
        
        return True
    
    @staticmethod
    async def verify_totp(db: AsyncSession, user_id: int, totp_code: str) -> bool:
        """
        Verify a TOTP code during login.
        
        Args:
            db: Database session
            user_id: User ID
            totp_code: 6-digit TOTP code
            
        Returns:
            bool: True if valid
        """
        stmt = select(UserMFA).where(
            UserMFA.user_id == user_id,
            UserMFA.mfa_enabled == True
        )
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa:
            return False
        
        # Decrypt secret (Phase 3.4/3.5)
        key_rotation_service = get_key_rotation_service()
        fernet = await key_rotation_service.get_key_by_version(db, mfa.key_version)
        secret = fernet.decrypt(mfa.mfa_secret.encode()).decode()
        
        # Verify TOTP (allow 1 step before/after for clock skew)
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(totp_code, valid_window=1)
        
        if is_valid:
            # Update last used timestamp
            mfa.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(
                "MFA verification successful",
                extra={"user_id": user_id}
            )
        else:
            logger.warning(
                "MFA verification failed",
                extra={"user_id": user_id}
            )
        
        return is_valid
    
    @staticmethod
    async def verify_backup_code(db: AsyncSession, user_id: int, backup_code: str) -> bool:
        """
        Verify and consume a backup code.
        
        Backup codes are one-time use only.
        
        Args:
            db: Database session
            user_id: User ID
            backup_code: 8-character backup code
            
        Returns:
            bool: True if valid
        """
        stmt = select(UserMFA).where(
            UserMFA.user_id == user_id,
            UserMFA.mfa_enabled == True
        )
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa or not mfa.backup_codes:
            return False
        
        # Load backup codes
        hashed_codes = json.loads(mfa.backup_codes)
        
        # Check if backup code matches any stored hash
        for i, hashed_code in enumerate(hashed_codes):
            if verify_password(backup_code, hashed_code):
                # Valid backup code - remove it (one-time use)
                hashed_codes.pop(i)
                mfa.backup_codes = json.dumps(hashed_codes)
                mfa.last_used_at = datetime.now(timezone.utc)
                await db.commit()
                
                logger.info(
                    "Backup code used",
                    extra={
                        "user_id": user_id,
                        "remaining_codes": len(hashed_codes)
                    }
                )
                
                return True
        
        logger.warning(
            "Invalid backup code attempted",
            extra={"user_id": user_id}
        )
        
        return False
    
    @staticmethod
    async def disable_mfa(db: AsyncSession, user_id: int) -> bool:
        """
        Disable MFA for a user.
        
        Keeps the record but sets mfa_enabled=False.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            bool: True if disabled
        """
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa:
            return False
        
        mfa.mfa_enabled = False
        await db.commit()
        
        logger.info(
            "MFA disabled",
            extra={"user_id": user_id}
        )
        
        return True
    
    @staticmethod
    async def is_mfa_enabled(db: AsyncSession, user_id: int) -> bool:
        """
        Check if MFA is enabled for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            bool: True if MFA is enabled
        """
        stmt = select(UserMFA).where(
            UserMFA.user_id == user_id,
            UserMFA.mfa_enabled == True
        )
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        return mfa is not None
    
    @staticmethod
    async def get_mfa_status(db: AsyncSession, user_id: int) -> dict:
        """
        Get MFA status and stats for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            dict with MFA status info
        """
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa:
            return {
                "mfa_enabled": False,
                "setup_completed": False
            }
        
        # Count remaining backup codes
        backup_codes_count = 0
        if mfa.backup_codes:
            hashed_codes = json.loads(mfa.backup_codes)
            backup_codes_count = len(hashed_codes)
        
        return {
            "mfa_enabled": mfa.mfa_enabled,
            "setup_completed": mfa.mfa_secret is not None,
            "enabled_at": mfa.enabled_at.isoformat() if mfa.enabled_at else None,
            "last_used_at": mfa.last_used_at.isoformat() if mfa.last_used_at else None,
            "backup_codes_remaining": backup_codes_count
        }
    
    @staticmethod
    async def regenerate_backup_codes(db: AsyncSession, user_id: int) -> list[str]:
        """
        Generate new backup codes for a user.
        
        Replaces all existing backup codes.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            list[str]: New plain backup codes (show once!)
        """
        stmt = select(UserMFA).where(UserMFA.user_id == user_id)
        result = await db.execute(stmt)
        mfa = result.scalar_one_or_none()
        
        if not mfa or not mfa.mfa_enabled:
            raise ValueError("MFA not enabled")
        
        # Generate new backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        hashed_backup_codes = [get_password_hash(code) for code in backup_codes]
        backup_codes_json = json.dumps(hashed_backup_codes)
        
        mfa.backup_codes = backup_codes_json
        await db.commit()
        
        logger.info(
            "Backup codes regenerated",
            extra={"user_id": user_id}
        )
        
        return backup_codes
