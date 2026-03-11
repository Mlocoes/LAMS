from typing import Generator, AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError
from datetime import datetime, timezone
from core.config import settings
from database.database import async_session_maker
from database.models import User, AgentAPIKey
from auth.security import verify_password

# Custom OAuth2 scheme that reads from cookie or Authorization header
class OAuth2PasswordBearerCookie(OAuth2PasswordBearer):
    """
    OAuth2 password bearer that reads token from:
    1. HttpOnly cookie (preferred, secure)
    2. Authorization header (fallback for agents and API clients)
    """
    async def __call__(self, request: Request) -> Optional[str]:
        # Try to get token from HttpOnly cookie first (Phase 1.4)
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            # Cookie format: "Bearer <token>"
            scheme, token = get_authorization_scheme_param(cookie_token)
            if scheme.lower() == "bearer":
                return token
        
        # Fallback to Authorization header (for agents and API clients)
        authorization = request.headers.get("Authorization")
        if authorization:
            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() == "bearer":
                return token
        
        # No token found
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user with password change verification"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Check if password change is required (Phase 1.2)
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required. Please change your password to continue.",
            headers={"X-Password-Change-Required": "true"},
        )
    
    return user

async def get_current_user_no_password_check(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user without password change verification (for password change endpoint only)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user

async def verify_agent_api_key(
    x_api_key: str = Header(..., alias="X-Agent-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Verify agent API key and return host_id (Phase 1.5).
    
    The API key must be sent in the X-Agent-API-Key header.
    Returns the host_id if the key is valid and active.
    
    Raises HTTPException if:
    - API key is missing
    - API key is invalid
    - API key is revoked (is_active=False)
    - API key has expired
    """
    # Find API key in database
    stmt = select(AgentAPIKey).where(AgentAPIKey.is_active == True)
    result = await db.execute(stmt)
    all_keys = result.scalars().all()
    
    # Check each active key to find a match
    matching_key = None
    for key in all_keys:
        if verify_password(x_api_key, key.key_hash):
            matching_key = key
            break
    
    if not matching_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked agent API key"
        )
    
    # Check expiration
    if matching_key.expires_at and matching_key.expires_at < datetime.now(timezone.utc):
        # Mark as inactive if expired
        matching_key.is_active = False
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent API key has expired"
        )
    
    # Update last_used timestamp
    matching_key.last_used = datetime.now(timezone.utc)
    await db.commit()
    
    return matching_key.host_id
