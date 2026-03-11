from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from secrets import token_urlsafe
from core.config import settings

ph = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return ph.hash(password)

def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token() -> str:
    """
    Create a secure random refresh token (Phase 2.7).
    
    Returns a 32-byte URL-safe random token.
    The token will be hashed before storage.
    """
    return token_urlsafe(32)
