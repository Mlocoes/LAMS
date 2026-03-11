"""
API endpoints for remote command management
Allows agents to poll for pending commands and report execution results
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel
from datetime import datetime, timezone

from database.models import RemoteCommand, Host
from api.dependencies import get_db, get_current_user

router = APIRouter()


# Pydantic Schemas
class CommandResponse(BaseModel):
    id: int
    host_id: str
    command_type: str
    target_id: str
    status: str
    created_at: datetime
    executed_at: datetime | None
    result: str | None
    
    class Config:
        from_attributes = True


class CommandResultUpdate(BaseModel):
    status: str  # "completed" or "failed"
    result: str  # Success message or error details


class CommandCreate(BaseModel):
    host_id: str
    command_type: str
    target_id: str


# Endpoints for Agent
@router.get("/{host_id}/pending", response_model=List[CommandResponse])
async def get_pending_commands(
    host_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending commands for a specific host (for agent polling)
    No authentication required - agents use this endpoint
    """
    # Verify host exists
    stmt_host = select(Host).where(Host.id == host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Get pending commands
    stmt = select(RemoteCommand).where(
        RemoteCommand.host_id == host_id,
        RemoteCommand.status == "pending"
    ).order_by(RemoteCommand.created_at)
    
    result = await db.execute(stmt)
    commands = result.scalars().all()
    
    # Mark as executing
    for cmd in commands:
        cmd.status = "executing"
    
    await db.commit()
    
    return commands


@router.post("/{command_id}/result", status_code=status.HTTP_200_OK)
async def update_command_result(
    command_id: int,
    result_data: CommandResultUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update command execution result (called by agent after execution)
    No authentication required - agents use this endpoint
    """
    # Get command
    stmt = select(RemoteCommand).where(RemoteCommand.id == command_id)
    result = await db.execute(stmt)
    command = result.scalar_one_or_none()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    # Update command status
    command.status = result_data.status
    command.result = result_data.result
    command.executed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"status": "success", "message": "Command result updated"}


# Endpoints for Web UI
@router.get("/{command_id}", response_model=CommandResponse)
async def get_command_status(
    command_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get command status (for web UI polling)
    Requires authentication
    """
    stmt = select(RemoteCommand).where(RemoteCommand.id == command_id)
    result = await db.execute(stmt)
    command = result.scalar_one_or_none()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    return command


@router.get("/host/{host_id}", response_model=List[CommandResponse])
async def get_host_commands(
    host_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get recent commands for a specific host (for web UI history)
    Requires authentication
    """
    stmt = select(RemoteCommand).where(
        RemoteCommand.host_id == host_id
    ).order_by(RemoteCommand.created_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    commands = result.scalars().all()
    
    return commands


@router.post("/", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def create_command(
    command_data: CommandCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new remote command (for web UI)
    Requires authentication
    """
    # Verify host exists
    stmt_host = select(Host).where(Host.id == command_data.host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Validate command type
    valid_commands = ["docker_start", "docker_stop", "docker_restart"]
    if command_data.command_type not in valid_commands:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command type. Must be one of: {', '.join(valid_commands)}"
        )
    
    # Create command
    new_command = RemoteCommand(
        host_id=command_data.host_id,
        command_type=command_data.command_type,
        target_id=command_data.target_id,
        status="pending"
    )
    
    db.add(new_command)
    await db.commit()
    await db.refresh(new_command)
    
    return new_command
