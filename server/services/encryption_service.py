"""
Encryption Service for Field-Level Encryption (Phase 3.4)

Uses Fernet (symmetric encryption) from cryptography library.
Fernet guarantees that messages encrypted cannot be manipulated or read without the key.

Features:
- Encrypt/decrypt strings
- Encrypt/decrypt sensitive database fields
- Key rotation support (future enhancement)
"""

from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import base64
import logging

from core.config import settings

logger = logging.getLogger("security")


class EncryptionService:
    """Service for field-level encryption using Fernet"""
    
    def __init__(self):
        """Initialize Fernet cipher with encryption key from settings"""
        try:
            self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise ValueError("Invalid ENCRYPTION_KEY configuration")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            plaintext: Plain text string to encrypt
            
        Returns:
            Base64 encoded encrypted value
            
        Example:
            >>> service = EncryptionService()
            >>> encrypted = service.encrypt("my-api-key-12345")
            >>> print(encrypted)  # "gAAAAABf..."
        """
        if not plaintext:
            return ""
        
        try:
            # Encrypt and return base64 string
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('ascii')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt value: {e}")
    
    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted string value.
        
        Args:
            encrypted_value: Base64 encoded encrypted value
            
        Returns:
            Decrypted plain text string
            
        Raises:
            ValueError: If decryption fails (wrong key, corrupted data, etc.)
            
        Example:
            >>> service = EncryptionService()
            >>> decrypted = service.decrypt("gAAAAABf...")
            >>> print(decrypted)  # "my-api-key-12345"
        """
        if not encrypted_value:
            return ""
        
        try:
            # Decrypt base64 string
            decrypted_bytes = self._fernet.decrypt(encrypted_value.encode('ascii'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed - invalid token (wrong key or corrupted data)")
            raise ValueError("Failed to decrypt value - invalid encryption key or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt value: {e}")
    
    def encrypt_optional(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt a string value that may be None.
        
        Args:
            plaintext: Plain text string or None
            
        Returns:
            Encrypted string or None
        """
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
    
    def decrypt_optional(self, encrypted_value: Optional[str]) -> Optional[str]:
        """
        Decrypt an encrypted string that may be None.
        
        Args:
            encrypted_value: Encrypted string or None
            
        Returns:
            Decrypted string or None
        """
        if encrypted_value is None:
            return None
        return self.decrypt(encrypted_value)
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64 encoded 32-byte key suitable for ENCRYPTION_KEY setting
            
        Example:
            >>> key = EncryptionService.generate_key()
            >>> print(key)  # "1234567890abcdef...=="
        """
        return Fernet.generate_key().decode('ascii')


# Global singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create global EncryptionService instance.
    
    Returns:
        EncryptionService singleton
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
