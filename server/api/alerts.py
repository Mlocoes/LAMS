from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Any
from datetime import datetime

from database.models import Alert, User
from api.dependencies import get_db, get_current_user

router = APIRouter()

class AlertResponse(BaseModel):
    id: int
    host_id: str
    event_time: datetime
    metric: str
    value: float
    severity: str
    message: str
    resolved: bool

    model_config = {"from_attributes": True}

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    resolved: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    stmt = select(Alert).where(Alert.resolved == resolved).order_by(Alert.event_time.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.resolved = True
    await db.commit()
    return {"status": "resolved"}
