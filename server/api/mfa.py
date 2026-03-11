"""
API endpoints for Multi-Factor Authentication (Phase 3.2)

Endpoints:
- POST /mfa/setup - Initialize MFA setup (generate secret + QR code)
- POST /mfa/enable - Enable MFA after verifying TOTP code
- POST /mfa/verify - Verify TOTP code during login
- GET /mfa/status - Get MFA status for current user
- DELETE /mfa - Disable MFA
- POST /mfa/backup-codes - Regenerate backup codes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List

from database.models import User
from api.dependencies import get_db, get_current_user
from services.mfa_service import MFAService

router = APIRouter()


# Request/Response models
class MFASetupResponse(BaseModel):
    """Response for MFA setup with QR code and backup codes"""
    secret: str = Field(description="Base32 encoded TOTP secret for manual entry")
    qr_code: str = Field(description="Data URI with base64 encoded QR code image")
    backup_codes: List[str] = Field(description="10 backup codes (SAVE THESE!)")
    message: str = Field(default="Scan QR code with authenticator app, then verify with /mfa/enable")


class MFAEnableRequest(BaseModel):
    """Request to enable MFA with TOTP code verification"""
    totp_code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$', 
                           description="6-digit TOTP code from authenticator app")


class MFAVerifyRequest(BaseModel):
    """Request to verify TOTP or backup code"""
    code: str = Field(description="6-digit TOTP code or 8-character backup code")


class MFAStatusResponse(BaseModel):
    """MFA status information"""
    mfa_enabled: bool
    setup_completed: bool
    enabled_at: str | None
    last_used_at: str | None
    backup_codes_remaining: int


class BackupCodesResponse(BaseModel):
    """Response with new backup codes"""
    backup_codes: List[str]
    message: str = Field(default="Save these backup codes securely. Each code can only be used once.")


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize MFA setup for current user.
    
    Generates:
    - TOTP secret
    - QR code for authenticator apps (Google Authenticator, Authy, etc.)
    - 10 backup codes for account recovery
    
    IMPORTANT: Save backup codes securely! They are shown only once.
    
    Next step: Call POST /mfa/enable with a TOTP code to enable MFA.
    """
    try:
        setup_data = await MFAService.setup_mfa(db, current_user.id)
        return MFASetupResponse(**setup_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/mfa/enable", status_code=status.HTTP_200_OK)
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable MFA after setup.
    
    User must provide a valid TOTP code from their authenticator app
    to prove they can generate codes successfully.
    
    After enabling, TOTP codes will be required for login.
    """
    try:
        await MFAService.enable_mfa(db, current_user.id, request.totp_code)
        return {
            "message": "MFA enabled successfully",
            "mfa_enabled": True
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify TOTP code or backup code.
    
    Used during login to verify second factor.
    Accepts either:
    - 6-digit TOTP code from authenticator app
    - 8-character backup code (one-time use)
    
    Note: This endpoint is typically called by the frontend during login flow,
    not by end users directly.
    """
    code = request.code.strip()
    
    # Try TOTP code (6 digits)
    if len(code) == 6 and code.isdigit():
        is_valid = await MFAService.verify_totp(db, current_user.id, code)
        if is_valid:
            return {"message": "MFA verification successful", "verified": True}
    
    # Try backup code (8 chars)
    elif len(code) == 8:
        is_valid = await MFAService.verify_backup_code(db, current_user.id, code.upper())
        if is_valid:
            return {
                "message": "Backup code accepted (one-time use)",
                "verified": True,
                "backup_code_used": True
            }
    
    # Invalid format or wrong code
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired code"
    )


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get MFA status for current user.
    
    Returns:
    - Whether MFA is enabled
    - Setup completion status
    - Last usage timestamp
    - Remaining backup codes count
    """
    status_data = await MFAService.get_mfa_status(db, current_user.id)
    return MFAStatusResponse(**status_data)


@router.delete("/mfa", status_code=status.HTTP_200_OK)
async def disable_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable MFA for current user.
    
    Security recommendation: Require password re-entry in frontend
    before allowing MFA disable.
    """
    success = await MFAService.disable_mfa(db, current_user.id)
    
    if success:
        return {"message": "MFA disabled successfully", "mfa_enabled": False}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MFA not configured"
        )


@router.post("/mfa/backup-codes", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate new backup codes for current user.
    
    WARNING: This replaces ALL existing backup codes.
    Old backup codes will no longer work.
    
    Use cases:
    - Running out of backup codes
    - Backup codes compromised
    - Lost backup codes
    
    IMPORTANT: Save new backup codes securely!
    """
    try:
        backup_codes = await MFAService.regenerate_backup_codes(db, current_user.id)
        return BackupCodesResponse(backup_codes=backup_codes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
