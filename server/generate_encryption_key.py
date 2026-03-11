#!/usr/bin/env python3
"""
Generate encryption key for field-level encryption (Phase 3.4)

This script generates a Fernet encryption key for use with the ENCRYPTION_KEY setting.

Usage:
    python generate_encryption_key.py

Output:
    Prints a base64-encoded 32-byte key suitable for ENCRYPTION_KEY in .env file
"""

from cryptography.fernet import Fernet

def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    key = Fernet.generate_key()
    return key.decode('ascii')

if __name__ == "__main__":
    key = generate_encryption_key()
    
    print("=" * 80)
    print("ENCRYPTION KEY GENERATED")
    print("=" * 80)
    print()
    print("Add this to your .env file:")
    print()
    print(f"ENCRYPTION_KEY={key}")
    print()
    print("=" * 80)
    print("IMPORTANT:")
    print("- Store this key securely (password manager, secrets vault)")
    print("- NEVER commit this key to version control")
    print("- If you lose this key, encrypted data CANNOT be recovered")
    print("- Use the same key across all server instances")
    print("- Rotate keys periodically (see Phase 3.5 for key rotation)")
    print("=" * 80)
