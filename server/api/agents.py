"""
Agent API Key Management Endpoints (Phase 1.5)

These endpoints allow administrators to generate, manage, and revoke API keys for agents.
Each agent needs a unique API key to authenticate with the server.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, List
from pydantic import BaseModel
from secrets import token_urlsafe

from database.models import User, Host, AgentAPIKey
from auth.security import get_password_hash
from api.dependencies import get_db, get_current_active_admin
from core.config import settings

router = APIRouter()

class APIKeyGenerate(BaseModel):
    host_id: str
    expires_in_days: Optional[int] = None  # None means no expiration

class APIKeyResponse(BaseModel):
    id: int
    host_id: str
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool

class APIKeyGenerateResponse(BaseModel):
    api_key: str  # Plaintext key (only shown once!)
    key_info: APIKeyResponse

@router.post("/generate", response_model=APIKeyGenerateResponse)
async def generate_api_key(
    key_data: APIKeyGenerate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin)
) -> Any:
    """
    Generate a new API key for an agent.
    The plaintext key is only shown once - store it securely!
    
    Requires: Admin role
    """
    # Verify host exists
    stmt = select(Host).where(Host.id == key_data.host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host {key_data.host_id} not found"
        )
    
    # Check if API key already exists for this host
    stmt = select(AgentAPIKey).where(AgentAPIKey.host_id == key_data.host_id)
    result = await db.execute(stmt)
    existing_key = result.scalar_one_or_none()
    
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key already exists for host {key_data.host_id}. Revoke it first if you want to generate a new one."
        )
    
    # Generate secure random API key (44 characters, URL-safe)
    api_key = token_urlsafe(32)
    
    # Calculate expiration if specified
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_in_days)
    
    # Create API key record (store hashed version)
    new_key = AgentAPIKey(
        host_id=key_data.host_id,
        key_hash=get_password_hash(api_key),  # Hash the key
        created_by=current_admin.id,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    
    return {
        "api_key": api_key,  # ⚠️ Only shown once!
        "key_info": {
            "id": new_key.id,
            "host_id": new_key.host_id,
            "created_at": new_key.created_at,
            "last_used": new_key.last_used,
            "expires_at": new_key.expires_at,
            "is_active": new_key.is_active
        }
    }

@router.get("/keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
    include_revoked: bool = False
) -> Any:
    """
    List all agent API keys.
    
    Requires: Admin role
    """
    stmt = select(AgentAPIKey)
    
    if not include_revoked:
        stmt = stmt.where(AgentAPIKey.is_active == True)
    
    result = await db.execute(stmt)
    keys = result.scalars().all()
    
    return [
        {
            "id": key.id,
            "host_id": key.host_id,
            "created_at": key.created_at,
            "last_used": key.last_used,
            "expires_at": key.expires_at,
            "is_active": key.is_active
        }
        for key in keys
    ]

@router.post("/revoke/{host_id}")
async def revoke_api_key(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin)
) -> Any:
    """
    Revoke an agent's API key.
    The agent will no longer be able to send data to the server.
    
    Requires: Admin role
    """
    stmt = select(AgentAPIKey).where(AgentAPIKey.host_id == host_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for host {host_id}"
        )
    
    api_key.is_active = False
    await db.commit()
    
    return {"message": f"API key for host {host_id} has been revoked"}

@router.delete("/delete/{host_id}")
async def delete_api_key(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin)
) -> Any:
    """
    Permanently delete an agent's API key.
    Use with caution - this cannot be undone!
    
    Requires: Admin role
    """
    stmt = select(AgentAPIKey).where(AgentAPIKey.host_id == host_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for host {host_id}"
        )
    
    await db.delete(api_key)
    await db.commit()
    
    return {"message": f"API key for host {host_id} has been permanently deleted"}

@router.post("/rotate/{host_id}", response_model=APIKeyGenerateResponse)
async def rotate_api_key(
    host_id: str,
    expires_in_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin)
) -> Any:
    """
    Rotate (revoke old and generate new) an agent's API key.
    The old key will be revoked and a new one generated.
    
    Requires: Admin role
    """
    # Find existing key
    stmt = select(AgentAPIKey).where(AgentAPIKey.host_id == host_id)
    result = await db.execute(stmt)
    old_key = result.scalar_one_or_none()
    
    if not old_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for host {host_id}"
        )
    
    # Delete old key
    await db.delete(old_key)
    await db.commit()
    
    # Generate new key
    api_key = token_urlsafe(32)
    
    # Calculate expiration if specified
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    # Create new API key record
    new_key = AgentAPIKey(
        host_id=host_id,
        key_hash=get_password_hash(api_key),
        created_by=current_admin.id,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    
    return {
        "api_key": api_key,  # ⚠️ Only shown once!
        "key_info": {
            "id": new_key.id,
            "host_id": new_key.host_id,
            "created_at": new_key.created_at,
            "last_used": new_key.last_used,
            "expires_at": new_key.expires_at,
            "is_active": new_key.is_active
        }
    }
