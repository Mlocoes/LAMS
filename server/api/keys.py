"""
Encryption Key Management API (Phase 3.5)

Endpoints for managing encryption key rotation and monitoring.

Only accessible by administrators.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from api.dependencies import get_db, get_current_user, get_current_active_admin
from database.models import User
from services.key_rotation_service import get_key_rotation_service
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.logging_config import get_security_logger

security_logger = get_security_logger()
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# Request/Response Models

class KeyRotationRequest(BaseModel):
    """Request to rotate encryption key."""
    force: bool = False
    skip_reencrypt: bool = False
    notes: Optional[str] = None


class KeyRotationResponse(BaseModel):
    """Response from key rotation."""
    success: bool
    old_version: int
    new_version: int
    reencrypted_count: int
    message: str


class KeyStatusResponse(BaseModel):
    """Current active key status."""
    version: int
    algorithm: str
    created_at: datetime
    age_days: int
    rotation_needed: bool


class KeyStatsResponse(BaseModel):
    """Statistics about encryption keys."""
    total_keys: int
    oldest_version: Optional[int]
    newest_version: Optional[int]
    active_key: Optional[dict]
    rotation_needed: bool
    rotation_threshold_days: int


class ReencryptRequest(BaseModel):
    """Request to re-encrypt data with current key."""
    old_version: int
    new_version: Optional[int] = None  # None = use active key


class ReencryptResponse(BaseModel):
    """Response from re-encryption."""
    success: bool
    old_version: int
    new_version: int
    reencrypted_count: int


# Endpoints

@router.post("/rotate", response_model=KeyRotationResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")  # Limit key rotations to prevent abuse
async def rotate_encryption_key(
    request: KeyRotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    Rotate encryption key (Admin only).
    
    This will:
    1. Generate a new encryption key
    2. Mark the old key as rotated
    3. Re-encrypt existing data (unless skip_reencrypt=True)
    
    **Requires Admin role.**
    
    Args:
        force: Force rotation even if not needed
        skip_reencrypt: Skip re-encryption of existing data (faster, but leaves old data)
        notes: Optional notes about this rotation
    
    Returns:
        Rotation results with new version and re-encryption count
    """
    try:
        service = get_key_rotation_service()
        
        # Check if rotation is needed
        stats = await service.get_key_stats(db)
        
        if not request.force and not stats['rotation_needed']:
            security_logger.warning(
                "Key rotation attempted but not needed",
                extra={
                    'user_id': current_user.id,
                    'age_days': stats['active_key']['age_days'],
                    'threshold': stats['rotation_threshold_days']
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Key rotation not needed yet (age: {stats['active_key']['age_days']} days, threshold: {stats['rotation_threshold_days']} days). Use force=true to rotate anyway."
            )
        
        # Get old version before rotation
        old_version = await service.get_active_key_version(db)
        
        # Rotate key
        notes = request.notes or f"Key rotation by {current_user.email}"
        new_key = await service.rotate_key(
            db,
            created_by=current_user.email,
            notes=notes
        )
        
        # Re-encrypt data (unless skipped)
        reencrypted_count = 0
        if not request.skip_reencrypt:
            reencrypted_count = await service.reencrypt_data(db, old_version, new_key.version)
        
        security_logger.info(
            "Encryption key rotated",
            extra={
                'user_id': current_user.id,
                'old_version': old_version,
                'new_version': new_key.version,
                'reencrypted_count': reencrypted_count,
                'skip_reencrypt': request.skip_reencrypt
            }
        )
        
        return KeyRotationResponse(
            success=True,
            old_version=old_version,
            new_version=new_key.version,
            reencrypted_count=reencrypted_count,
            message=f"Key rotated from version {old_version} to {new_key.version}. Re-encrypted {reencrypted_count} records."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        security_logger.error(
            f"Key rotation failed: {e}",
            extra={'user_id': current_user.id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key rotation failed: {str(e)}"
        )


@router.get("/status", response_model=KeyStatusResponse)
async def get_key_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    Get current active encryption key status (Admin only).
    
    Returns information about the currently active encryption key,
    including version, age, and whether rotation is recommended.
    
    **Requires Admin role.**
    """
    try:
        service = get_key_rotation_service()
        stats = await service.get_key_stats(db)
        
        if not stats['active_key']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active encryption key found"
            )
        
        active = stats['active_key']
        
        return KeyStatusResponse(
            version=active['version'],
            algorithm=active['algorithm'],
            created_at=active['created_at'],
            age_days=active['age_days'],
            rotation_needed=stats['rotation_needed']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key status: {str(e)}"
        )


@router.get("/stats", response_model=KeyStatsResponse)
async def get_key_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    Get statistics about encryption keys (Admin only).
    
    Returns comprehensive statistics including:
    - Total number of keys
    - Active key information
    - Version range (oldest/newest)
    - Rotation recommendation
    
    **Requires Admin role.**
    """
    try:
        service = get_key_rotation_service()
        stats = await service.get_key_stats(db)
        
        return KeyStatsResponse(
            total_keys=stats['total_keys'],
            oldest_version=stats.get('oldest_version'),
            newest_version=stats.get('newest_version'),
            active_key=stats.get('active_key'),
            rotation_needed=stats['rotation_needed'],
            rotation_threshold_days=stats['rotation_threshold_days']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key statistics: {str(e)}"
        )


@router.post("/reencrypt", response_model=ReencryptResponse)
@limiter.limit("3/hour")  # Limit re-encryption operations
async def reencrypt_data(
    request: ReencryptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    Re-encrypt data from old key to new key (Admin only).
    
    This is useful when:
    - Key was rotated with skip_reencrypt=True
    - Data was imported with an old key version
    - Migration to current key is needed
    
    **Requires Admin role.**
    
    Args:
        old_version: Source key version
        new_version: Target key version (defaults to active key)
    
    Returns:
        Re-encryption results with count of updated records
    """
    try:
        service = get_key_rotation_service()
        
        # Default to active key if new_version not specified
        new_version = request.new_version
        if new_version is None:
            new_version = await service.get_active_key_version(db)
        
        # Re-encrypt data
        count = await service.reencrypt_data(db, request.old_version, new_version)
        
        security_logger.info(
            "Data re-encrypted",
            extra={
                'user_id': current_user.id,
                'old_version': request.old_version,
                'new_version': new_version,
                'count': count
            }
        )
        
        return ReencryptResponse(
            success=True,
            old_version=request.old_version,
            new_version=new_version,
            reencrypted_count=count
        )
        
    except Exception as e:
        security_logger.error(
            f"Re-encryption failed: {e}",
            extra={
                'user_id': current_user.id,
                'old_version': request.old_version,
                'new_version': request.new_version
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-encryption failed: {str(e)}"
        )
