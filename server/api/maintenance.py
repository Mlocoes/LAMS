"""
Maintenance API endpoints

Provides administrative endpoints for database maintenance tasks.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict

from api.dependencies import get_current_user
from database.models import User
from maintenance.cleanup import run_maintenance_job, cleanup_old_metrics, aggregate_metrics

router = APIRouter()


@router.post("/run", response_model=Dict[str, Any])
async def run_maintenance_manually(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Manually trigger the complete maintenance job.
    
    This runs both aggregation and cleanup tasks immediately.
    Requires admin authentication.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await run_maintenance_job()
    return result


@router.post("/cleanup", response_model=Dict[str, Any])
async def run_cleanup_manually(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Manually trigger cleanup of old metrics.
    
    Deletes metrics older than METRICS_RETENTION_DAYS.
    Requires admin authentication.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await cleanup_old_metrics()
    return result


@router.post("/aggregate", response_model=Dict[str, Any])
async def run_aggregation_manually(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Manually trigger aggregation of old metrics.
    
    Aggregates metrics older than METRICS_AGGREGATION_DAYS into hourly summaries.
    Requires admin authentication.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await aggregate_metrics()
    return result
