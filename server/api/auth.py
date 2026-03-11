from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta, datetime, timezone
from typing import Any
from pydantic import BaseModel, EmailStr, field_validator, Field
from password_strength import PasswordPolicy
from slowapi import Limiter
from slowapi.util import get_remote_address

from database.models import User, RefreshToken
from auth.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from api.dependencies import get_db, get_current_user, get_current_user_no_password_check
from core.config import settings
from middleware.csrf import generate_csrf_token, set_csrf_cookie
from services.session_service import SessionService  # Phase 3.1: Session management
from services.mfa_service import MFAService  # Phase 3.2: MFA/2FA

router = APIRouter()

# Phase 2.1: Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Phase 2.2: Password policy (12+ chars, uppercase, numbers, special chars)
password_policy = PasswordPolicy.from_names(
    length=12,  # min length: 12
    uppercase=1,  # need min. 1 uppercase letter
    numbers=1,  # need min. 1 digit
    special=1,  # need min. 1 special character
)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = False
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength (Phase 2.2)"""
        errors = password_policy.test(v)
        if errors:
            error_messages = []
            for error in errors:
                error_name = error.__class__.__name__
                if error_name == "Length":
                    error_messages.append("at least 12 characters")
                elif error_name == "Uppercase":
                    error_messages.append("at least 1 uppercase letter")
                elif error_name == "Numbers":
                    error_messages.append("at least 1 number")
                elif error_name == "Special":
                    error_messages.append("at least 1 special character")
            
            raise ValueError(
                f"Password must contain: {', '.join(error_messages)}"
            )
        return v

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength (Phase 2.2)"""
        errors = password_policy.test(v)
        if errors:
            error_messages = []
            for error in errors:
                error_name = error.__class__.__name__
                if error_name == "Length":
                    error_messages.append("at least 12 characters")
                elif error_name == "Uppercase":
                    error_messages.append("at least 1 uppercase letter")
                elif error_name == "Numbers":
                    error_messages.append("at least 1 number")
                elif error_name == "Special":
                    error_messages.append("at least 1 special character")
            
            raise ValueError(
                f"Password must contain: {', '.join(error_messages)}"
            )
        return v

class LoginRequest(BaseModel):
    """Schema for login request with JSON"""
    email: EmailStr
    password: str

class MFAVerifyLogin(BaseModel):
    """Request model for MFA verification during login (Phase 3.2)"""
    temp_token: str
    mfa_code: str = Field(description="6-digit TOTP code or 8-character backup code")

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")  # Phase 2.1: Rate limit registration to 5 per hour
async def register_user(
    request: Request,
    response: Response,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        is_admin=user_in.is_admin,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Phase 2.5: Generate and set CSRF token for new user
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, secure=settings.ENVIRONMENT == "production")
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "is_admin": new_user.is_admin,
        "csrf_token": csrf_token  # Return CSRF token for client to include in headers
    }

@router.post("/login")
@limiter.limit("5/15minutes")  # Phase 2.1: Rate limit login to 5 attempts per 15 minutes
async def login_access_token(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login endpoint.
    Sets HttpOnly cookie with JWT token (Phase 1.4 - secure against XSS).
    Also returns token in response for backward compatibility with agents.
    """
    # Find user by email
    stmt = select(User).where(User.email == login_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Phase 3.2: Check if MFA is enabled for this user
    mfa_enabled = await MFAService.is_mfa_enabled(db, user.id)
    
    if mfa_enabled:
        # MFA required - return temporary token for MFA verification
        # Create a short-lived temp token (5 minutes) for MFA verification
        temp_token = create_access_token(
            user.id, 
            expires_delta=timedelta(minutes=5),
            extra_claims={"mfa_pending": True}
        )
        
        return {
            "mfa_required": True,
            "temp_token": temp_token,
            "message": "MFA verification required. Use POST /auth/verify-mfa with TOTP code."
        }

    # No MFA - proceed with normal login
    # Create access token (Phase 2.7: Now expires in 1 hour)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Phase 2.7: Create refresh token
    refresh_token = create_refresh_token()
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store refresh token in database
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=get_password_hash(refresh_token),
        expires_at=refresh_token_expires,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(refresh_token_obj)
    await db.commit()
    await db.refresh(refresh_token_obj)  # Get the ID after commit
    
    # Phase 3.1: Create session with device tracking
    session = await SessionService.create_session(
        db=db,
        user_id=user.id,
        request=request,
        refresh_token_id=refresh_token_obj.id
    )
    
    # Set HttpOnly cookie for access token (Phase 1.4 - secure against XSS)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # JavaScript cannot access this cookie
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="strict",  # CSRF protection
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
        path="/",
    )
    
    # Phase 2.7: Set refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert days to seconds
        path="/api/v1/auth",  # Only sent to auth endpoints
    )
    
    # Phase 3.1: Set session token in HttpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS * 24 * 60 * 60,  # Days to seconds
        path="/",
    )
    
    # Phase 2.5: Generate and set CSRF token
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, secure=settings.ENVIRONMENT == "production")
    
    return {
        "access_token": access_token,  # For backward compatibility with agents
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Seconds
        "must_change_password": user.must_change_password,  # Phase 1.2: Inform frontend
        "csrf_token": csrf_token,  # Phase 2.5: Return CSRF token for client
        "user": {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }

@router.post("/verify-mfa")
@limiter.limit("10/15minutes")  # Phase 3.2: Rate limit MFA verification
async def verify_mfa_and_login(
    request: Request,
    response: Response,
    mfa_data: MFAVerifyLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Verify MFA code and complete login (Phase 3.2).
    
    After successful password authentication, users with MFA enabled must
    provide a TOTP code or backup code to complete login.
    
    Flow:
    1. POST /auth/login → returns {mfa_required: true, temp_token: "..."}
    2. POST /auth/verify-mfa → verifies code and returns full auth tokens
    """
    # Decode temp token to get user_id
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(
            mfa_data.temp_token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = int(payload.get("sub"))
        mfa_pending = payload.get("mfa_pending", False)
        
        if not mfa_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token - not a temporary MFA token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired temporary token"
        )
    
    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify MFA code
    code = mfa_data.mfa_code.strip()
    is_valid = False
    used_backup_code = False
    
    # Try TOTP code (6 digits)
    if len(code) == 6 and code.isdigit():
        is_valid = await MFAService.verify_totp(db, user_id, code)
    # Try backup code (8 chars)
    elif len(code) == 8:
        is_valid = await MFAService.verify_backup_code(db, user_id, code.upper())
        used_backup_code = is_valid
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA code"
        )
    
    # MFA verified - proceed with full login (same as normal login)
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Create refresh token
    refresh_token = create_refresh_token()
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store refresh token in database
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=get_password_hash(refresh_token),
        expires_at=refresh_token_expires,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(refresh_token_obj)
    await db.commit()
    await db.refresh(refresh_token_obj)
    
    # Create session with device tracking
    session = await SessionService.create_session(
        db=db,
        user_id=user.id,
        request=request,
        refresh_token_id=refresh_token_obj.id
    )
    
    # Set HttpOnly cookies
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS * 24 * 60 * 60,
        path="/",
    )
    
    # Generate and set CSRF token
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, secure=settings.ENVIRONMENT == "production")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "must_change_password": user.must_change_password,
        "csrf_token": csrf_token,
        "mfa_verified": True,
        "backup_code_used": used_backup_code,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }

@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token (Phase 2.7).
    
    The refresh token must be in the 'refresh_token' HttpOnly cookie.
    Returns a new access token with extended validity.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Find refresh token in database
    stmt = select(RefreshToken).where(
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    )
    result = await db.execute(stmt)
    all_tokens = result.scalars().all()
    
    # Verify refresh token
    matching_token = None
    for token in all_tokens:
        if verify_password(refresh_token, token.token_hash):
            matching_token = token
            break
    
    if not matching_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Update last_used
    matching_token.last_used = datetime.now(timezone.utc)
    await db.commit()
    
    # Get user
    stmt = select(User).where(User.id == matching_token.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if password change is required
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
            headers={"X-Password-Change-Required": "true"}
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    # Set new access token in cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    
    # Phase 2.5: Regenerate CSRF token on refresh (rotate tokens)
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token, secure=settings.ENVIRONMENT == "production")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "csrf_token": csrf_token  # Phase 2.5: Return new CSRF token
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "must_change_password": current_user.must_change_password,
        "password_changed_at": current_user.password_changed_at
    }

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_no_password_check)  # Allow access even if password change is required
) -> Any:
    """
    Change user password.
    This endpoint is accessible even when must_change_password flag is set.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check that new password is different
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.must_change_password = False
    current_user.password_changed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "message": "Password changed successfully",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "is_admin": current_user.is_admin
        }
    }

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_no_password_check)  # Verify user but allow logout even if password change required
) -> Any:
    """
    Logout endpoint (Phase 1.4 + 2.7).
    Clears both cookies and revokes refresh token.
    """
    # Phase 2.7: Revoke refresh token if present
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        # Find and revoke refresh token
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        all_tokens = result.scalars().all()
        
        for token in all_tokens:
            if verify_password(refresh_token, token.token_hash):
                token.revoked = True
                token.revoked_at = datetime.now(timezone.utc)
                break
        
        await db.commit()
    
    # Phase 3.1: Terminate session if present
    session_token = request.cookies.get("session_token")
    if session_token:
        session = await SessionService.get_session_by_token(db, session_token)
        if session:
            await SessionService.terminate_session(db, session.id)
    
    # Clear the access token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict"
    )
    
    # Phase 2.7: Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict"
    )
    
    # Phase 3.1: Clear the session token cookie
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict"
    )
    
    return {"message": "Logged out successfully"}
