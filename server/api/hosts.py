from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from pydantic import BaseModel, field_validator
from typing import List, Any, Optional
from datetime import datetime, timezone

from database.models import Host, User, AlertRule
from api.dependencies import get_db, get_current_user, verify_agent_api_key
from utils.sanitization import sanitize_string, sanitize_tags, sanitize_hostname, validate_host_id

router = APIRouter()

class HostRegister(BaseModel):
    id: str # HWID or unique agent identifier
    hostname: str
    ip: str
    os: str
    kernel_version: str
    cpu_cores: int
    total_memory: float
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate and sanitize host ID (Phase 2.4)"""
        return validate_host_id(v)
    
    @field_validator('hostname')
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        """Validate and sanitize hostname (Phase 2.4)"""
        return sanitize_hostname(v)
    
    @field_validator('ip', 'os', 'kernel_version')
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        """Sanitize text fields (Phase 2.4)"""
        return sanitize_string(v, max_length=255)

class HostResponse(HostRegister):
    status: str
    last_seen: datetime
    tags: Optional[List[str]] = []

    model_config = {"from_attributes": True}

class HostTagsUpdate(BaseModel):
    tags: List[str]
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and sanitize tags (Phase 2.4)"""
        return sanitize_tags(v)

@router.post("/register", response_model=HostResponse)
async def register_host(
    host_data: HostRegister, 
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Register or update a host.
    
    This endpoint does NOT require authentication for initial registration.
    After registration, admins can generate an API key for the host.
    
    If a host with the same ID already exists, it will be updated.
    """
    stmt = select(Host).where(Host.id == host_data.id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()

    if host:
        # Update existing
        host.hostname = host_data.hostname
        host.ip = host_data.ip
        host.os = host_data.os
        host.kernel_version = host_data.kernel_version
        host.cpu_cores = host_data.cpu_cores
        host.total_memory = host_data.total_memory
        host.last_seen = datetime.now(timezone.utc)
        host.status = "online"
    else:
        # Create new
        host = Host(**host_data.model_dump())
        db.add(host)
    
    await db.commit()
    await db.refresh(host)
    return host

@router.get("/", response_model=List[HostResponse])
async def get_hosts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    stmt = select(Host)
    result = await db.execute(stmt)
    hosts = result.scalars().all()
    return hosts

@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    stmt = select(Host).where(Host.id == host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host

@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a host and all its associated data.
    This includes metrics, alerts, docker containers, commands, and alert rules.
    Requires authentication.
    """
    stmt = select(Host).where(Host.id == host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Delete alert rules associated with this host
    # (AlertRule doesn't have CASCADE configured in the ForeignKey)
    delete_stmt = delete(AlertRule).where(AlertRule.host_id == host_id)
    await db.execute(delete_stmt)
    
    # Delete the host (metrics, alerts, docker_containers, and remote_commands 
    # will be deleted automatically via CASCADE)
    await db.delete(host)
    await db.commit()
    return None

@router.patch("/{host_id}/tags", response_model=HostResponse)
async def update_host_tags(
    host_id: str,
    tags_data: HostTagsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update tags for a specific host.
    Tags are used for categorizing and filtering hosts.
    """
    stmt = select(Host).where(Host.id == host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Update tags
    host.tags = tags_data.tags
    await db.commit()
    await db.refresh(host)
    return host
