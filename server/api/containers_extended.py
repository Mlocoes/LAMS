"""
Extended container operations for Portainer-like features:
- Logs (streaming and static)
- Inspect (detailed configuration)
- Remove (with options)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone
import asyncio

from database.models import DockerContainer, Host, User, RemoteCommand
from api.dependencies import get_db, get_current_user

router = APIRouter()

# ============================================================================
# LOGS ENDPOINTS
# ============================================================================

class ContainerLogsResponse(BaseModel):
    logs: List[str]
    command_id: int
    
@router.get("/{host_id}/containers/{container_id}/logs")
async def get_container_logs(
    host_id: str,
    container_id: str,
    tail: int = Query(default=100, ge=1, le=10000),
    since: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContainerLogsResponse:
    """
    Get logs from a container.
    
    Args:
        tail: Number of lines from end (default 100, max 10000)
        since: Unix timestamp to show logs since (optional)
    
    Returns:
        Logs array and command_id for tracking
    """
    # Verify host exists
    stmt_host = select(Host).where(Host.id == host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Verify container exists
    stmt_container = select(DockerContainer).where(
        DockerContainer.id == container_id,
        DockerContainer.host_id == host_id
    )
    result_container = await db.execute(stmt_container)
    container = result_container.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Create command for agent to fetch logs
    command = RemoteCommand(
        host_id=host_id,
        command_type="container.logs",
        target_id=container_id,
        parameters={
            "container_id": container_id,
            "tail": tail,
            "since": since,
            "follow": False
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # Wait for agent to process command (with timeout)
    timeout_seconds = 30
    for _ in range(timeout_seconds * 2):  # Check every 0.5s
        await asyncio.sleep(0.5)
        await db.refresh(command)
        
        if command.status == "completed":
            logs = command.result.get("logs", []) if command.result else []
            return ContainerLogsResponse(logs=logs, command_id=command.id)
        elif command.status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch logs: {command.error_message}"
            )
    
    # Timeout
    raise HTTPException(
        status_code=504,
        detail="Timeout waiting for logs from agent"
    )

# ============================================================================
# INSPECT ENDPOINT
# ============================================================================

class ContainerInspectResponse(BaseModel):
    inspect_data: dict
    command_id: int

@router.get("/{host_id}/containers/{container_id}/inspect")
async def inspect_container(
    host_id: str,
    container_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContainerInspectResponse:
    """
    Get detailed inspection data for a container.
    
    Returns full Docker inspect JSON with all configuration details.
    """
    # Verify host exists
    stmt_host = select(Host).where(Host.id == host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Verify container exists
    stmt_container = select(DockerContainer).where(
        DockerContainer.id == container_id,
        DockerContainer.host_id == host_id
    )
    result_container = await db.execute(stmt_container)
    container = result_container.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Create command for agent to inspect container
    command = RemoteCommand(
        host_id=host_id,
        command_type="container.inspect",
        target_id=container_id,
        parameters={
            "container_id": container_id
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # Wait for agent to process command
    timeout_seconds = 10
    for _ in range(timeout_seconds * 2):
        await asyncio.sleep(0.5)
        await db.refresh(command)
        
        if command.status == "completed":
            inspect_data = command.result.get("inspect", {}) if command.result else {}
            return ContainerInspectResponse(
                inspect_data=inspect_data,
                command_id=command.id
            )
        elif command.status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to inspect container: {command.error_message}"
            )
    
    raise HTTPException(
        status_code=504,
        detail="Timeout waiting for inspect data from agent"
    )

# ============================================================================
# DELETE ENDPOINT
# ============================================================================

class ContainerRemoveRequest(BaseModel):
    force: bool = False
    volumes: bool = False

class ContainerRemoveResponse(BaseModel):
    command_id: int
    status: str
    message: str

@router.delete("/{host_id}/containers/{container_id}")
async def remove_container(
    host_id: str,
    container_id: str,
    force: bool = Query(default=False),
    volumes: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContainerRemoveResponse:
    """
    Remove a container.
    
    Args:
        force: Force removal even if container is running
        volumes: Also remove associated volumes
    
    Returns:
        Command ID for tracking the removal operation
    """
    # Verify host exists
    stmt_host = select(Host).where(Host.id == host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Verify container exists
    stmt_container = select(DockerContainer).where(
        DockerContainer.id == container_id,
        DockerContainer.host_id == host_id
    )
    result_container = await db.execute(stmt_container)
    container = result_container.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Check if container is running and force is not set
    if container.state.lower() == "running" and not force:
        raise HTTPException(
            status_code=400,
            detail="Container is running. Use force=true to remove anyway."
        )
    
    # Create removal command
    command = RemoteCommand(
        host_id=host_id,
        command_type="container.remove",
        target_id=container_id,
        parameters={
            "container_id": container_id,
            "force": force,
            "volumes": volumes
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # TODO: Add audit log entry here
    
    return ContainerRemoveResponse(
        command_id=command.id,
        status="queued",
        message=f"Container removal queued (force={force}, volumes={volumes})"
    )

# ============================================================================
# EXEC ENDPOINT (Interactive console)
# ============================================================================

class ContainerExecRequest(BaseModel):
    cmd: List[str]
    tty: bool = True
    stdin: bool = True

class ContainerExecResponse(BaseModel):
    exec_id: str
    command_id: int

@router.post("/{host_id}/containers/{container_id}/exec")
async def create_exec(
    host_id: str,
    container_id: str,
    request: ContainerExecRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ContainerExecResponse:
    """
    Create an exec instance in a container.
    
    This creates the exec - to attach and interact, use WebSocket endpoint.
    
    Args:
        cmd: Command to execute (e.g., ["/bin/bash"])
        tty: Allocate a pseudo-TTY
        stdin: Keep STDIN open
    
    Returns:
        Exec ID and command ID for WebSocket connection
    """
    # Verify host and container
    stmt_host = select(Host).where(Host.id == host_id)
    result_host = await db.execute(stmt_host)
    host = result_host.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    stmt_container = select(DockerContainer).where(
        DockerContainer.id == container_id,
        DockerContainer.host_id == host_id
    )
    result_container = await db.execute(stmt_container)
    container = result_container.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Verify container is running
    if container.state.lower() != "running":
        raise HTTPException(
            status_code=400,
            detail="Container must be running to execute commands"
        )
    
    # Create exec command
    command = RemoteCommand(
        host_id=host_id,
        command_type="container.exec.create",
        target_id=container_id,
        parameters={
            "container_id": container_id,
            "cmd": request.cmd,
            "tty": request.tty,
            "stdin": request.stdin
        },
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(command)
    await db.commit()
    await db.refresh(command)
    
    # Wait for exec creation
    timeout_seconds = 10
    for _ in range(timeout_seconds * 2):
        await asyncio.sleep(0.5)
        await db.refresh(command)
        
        if command.status == "completed":
            exec_id = command.result.get("exec_id", "") if command.result else ""
            return ContainerExecResponse(
                exec_id=exec_id,
                command_id=command.id
            )
        elif command.status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create exec: {command.error_message}"
            )
    
    raise HTTPException(
        status_code=504,
        detail="Timeout waiting for exec creation"
    )
