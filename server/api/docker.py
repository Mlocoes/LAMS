from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Any
from datetime import datetime

from database.models import DockerContainer, Host, User, RemoteCommand
from api.dependencies import get_db, get_current_user

router = APIRouter()

class DockerContainerData(BaseModel):
    id: str
    name: str
    image: str
    state: str
    cpu_percent: float = 0.0
    memory_usage: float = 0.0
    created_at: datetime
    
class DockerSyncPayload(BaseModel):
    host_id: str
    containers: List[DockerContainerData]

@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_containers(
    payload: DockerSyncPayload,
    db: AsyncSession = Depends(get_db)
    # Auth omitted for agent in this example
) -> Any:
    # Very host existence
    stmt = select(Host).where(Host.id == payload.host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    # Simple sync strategy: remove all for host, insert new
    # Better strategy in production is merge by ID. Doing merge here.
    
    for c in payload.containers:
        stmt_c = select(DockerContainer).where(DockerContainer.id == c.id)
        res_c = await db.execute(stmt_c)
        existing = res_c.scalar_one_or_none()
        
        if existing:
            existing.state = c.state
            existing.cpu_percent = c.cpu_percent
            existing.memory_usage = c.memory_usage
        else:
            new_c = DockerContainer(
                id=c.id,
                host_id=payload.host_id,
                name=c.name,
                image=c.image,
                state=c.state,
                cpu_percent=c.cpu_percent,
                memory_usage=c.memory_usage,
                created_at=c.created_at
            )
            db.add(new_c)
            
    # Optionally: detect and remove containers not in payload (they were deleted)
    # Not implementing aggressive deletion in this MVP for safety.
    
    await db.commit()
    return {"status": "synced", "count": len(payload.containers)}

@router.get("/{host_id}", response_model=List[DockerContainerData])
async def get_containers(
    host_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    stmt = select(DockerContainer).where(DockerContainer.host_id == host_id)
    result = await db.execute(stmt)
    return result.scalars().all()

class DockerActionRequest(BaseModel):
    action: str # start, stop, restart

@router.post("/{host_id}/containers/{container_id}/action")
async def execute_docker_action(
    host_id: str,
    container_id: str,
    req: DockerActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a remote command for the agent to execute.
    Agent polls /api/v1/commands/{host_id}/pending and executes commands.
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
    
    # Validate action
    valid_actions = ["start", "stop", "restart"]
    if req.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )
    
    # Map action to command_type
    command_type = f"docker_{req.action}"
    
    # Create remote command
    new_command = RemoteCommand(
        host_id=host_id,
        command_type=command_type,
        target_id=container_id,
        status="pending"
    )
    
    db.add(new_command)
    await db.commit()
    await db.refresh(new_command)
    
    return {
        "status": "success",
        "message": f"Command '{req.action}' queued for container {container.name}",
        "command_id": new_command.id
    }
