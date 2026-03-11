from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Any, Optional

from database.models import AlertRule, User
from api.dependencies import get_db, get_current_user, get_current_active_admin

router = APIRouter()

class AlertRuleCreate(BaseModel):
    metric_name: str           # e.g. "cpu_usage", "memory_used"
    operator: str              # ">", "<", "=="
    threshold: float
    severity: str              # "warning" | "critical"
    duration_minutes: int = 1
    host_id: Optional[str] = None  # None = apply to all hosts

class AlertRuleResponse(AlertRuleCreate):
    id: int
    model_config = {"from_attributes": True}

@router.get("/", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    result = await db.execute(select(AlertRule))
    return result.scalars().all()

@router.post("/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_in: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    rule = AlertRule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_in: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> Any:
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    for field, value in rule_in.model_dump().items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> None:
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    await db.delete(rule)
    await db.commit()
