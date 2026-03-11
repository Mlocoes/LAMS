from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Any, Optional
from datetime import datetime, timezone

from database.models import Metric, Host, User
from api.dependencies import get_db, get_current_user, verify_agent_api_key

router = APIRouter()

class MetricPayload(BaseModel):
    host_id: str
    timestamp: datetime
    cpu_usage: float
    load_average: str
    memory_used: float
    memory_free: float
    swap_used: float
    disk_total: float
    disk_used: float
    disk_usage_percent: float
    temp_cpu: Optional[float] = None
    net_rx: float
    net_tx: float

@router.post("/", status_code=status.HTTP_201_CREATED)
async def ingest_metrics(
    payload: MetricPayload, 
    db: AsyncSession = Depends(get_db),
    authenticated_host_id: str = Depends(verify_agent_api_key)  # Phase 1.5: Verify agent API key
) -> Any:
    """
    Ingest metrics from an agent.
    Requires valid agent API key in X-Agent-API-Key header.
    """
    # Verify that the host_id in the payload matches the authenticated host
    if payload.host_id != authenticated_host_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent is authenticated for host {authenticated_host_id} but tried to send metrics for {payload.host_id}"
        )
    
    # Check if host exists
    stmt = select(Host).where(Host.id == payload.host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found. Please register first.")
    
    # Update host last_seen
    host.last_seen = payload.timestamp
    host.status = "online"

    # Insert Metric
    metric = Metric(**payload.model_dump())
    db.add(metric)
    await db.commit()
    return {"status": "ok"}

@router.get("/{host_id}", response_model=List[MetricPayload])
async def get_metrics(
    host_id: str,
    limit: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get metrics for a specific host.
    
    Args:
        host_id: Host identifier
        limit: Maximum number of metrics to return (default: 100)
        start_time: Optional start timestamp for filtering
        end_time: Optional end timestamp for filtering
    
    Returns ordered metrics (oldest to newest for charting)
    """
    stmt = select(Metric).where(Metric.host_id == host_id)
    
    # Apply time filters if provided
    if start_time:
        stmt = stmt.where(Metric.timestamp >= start_time)
    if end_time:
        stmt = stmt.where(Metric.timestamp <= end_time)
    
    stmt = stmt.order_by(Metric.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    metrics = result.scalars().all()
    
    # Return reversed to have chronological order for charts (oldest to newest)
    return metrics[::-1]
