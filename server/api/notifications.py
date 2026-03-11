"""
API endpoints for managing notification configurations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from database.models import NotificationConfig
from api.dependencies import get_db, get_current_user

router = APIRouter()


# Pydantic Schemas
class NotificationConfigCreate(BaseModel):
    provider: str  # "email", "slack", "discord"
    config: Dict[str, Any]  # Provider-specific configuration
    enabled: bool = True
    severity_filter: str = "all"  # "all", "warning", "critical"


class NotificationConfigUpdate(BaseModel):
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    severity_filter: Optional[str] = None


class NotificationConfigResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    config: Dict[str, Any]
    enabled: bool
    severity_filter: str
    
    class Config:
        from_attributes = True


# Endpoints
@router.get("/", response_model=List[NotificationConfigResponse])
async def list_notification_configs(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all notification configurations for the current user"""
    stmt = select(NotificationConfig).where(NotificationConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return configs


@router.get("/{config_id}", response_model=NotificationConfigResponse)
async def get_notification_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific notification configuration"""
    stmt = select(NotificationConfig).where(
        NotificationConfig.id == config_id,
        NotificationConfig.user_id == current_user.id
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    
    return config


@router.post("/", response_model=NotificationConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_config(
    config_in: NotificationConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new notification configuration"""
    # Validate provider type
    if config_in.provider not in ["email", "slack", "discord"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid provider. Must be 'email', 'slack', or 'discord'"
        )
    
    # Validate severity filter
    if config_in.severity_filter not in ["all", "warning", "critical"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid severity_filter. Must be 'all', 'warning', or 'critical'"
        )
    
    # Create new config
    new_config = NotificationConfig(
        user_id=current_user.id,
        provider=config_in.provider,
        config=config_in.config,
        enabled=config_in.enabled,
        severity_filter=config_in.severity_filter
    )
    
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    
    return new_config


@router.put("/{config_id}", response_model=NotificationConfigResponse)
async def update_notification_config(
    config_id: int,
    config_update: NotificationConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing notification configuration"""
    # Get existing config
    stmt = select(NotificationConfig).where(
        NotificationConfig.id == config_id,
        NotificationConfig.user_id == current_user.id
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    
    # Update fields if provided
    if config_update.config is not None:
        config.config = config_update.config
    
    if config_update.enabled is not None:
        config.enabled = config_update.enabled
    
    if config_update.severity_filter is not None:
        if config_update.severity_filter not in ["all", "warning", "critical"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid severity_filter. Must be 'all', 'warning', or 'critical'"
            )
        config.severity_filter = config_update.severity_filter
    
    await db.commit()
    await db.refresh(config)
    
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a notification configuration"""
    # Get existing config
    stmt = select(NotificationConfig).where(
        NotificationConfig.id == config_id,
        NotificationConfig.user_id == current_user.id
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    
    await db.delete(config)
    await db.commit()
    
    return None


@router.post("/{config_id}/test")
async def test_notification_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Send a test notification to verify configuration"""
    from notifications.email import EmailNotificationProvider
    from notifications.slack import SlackNotificationProvider
    from notifications.discord import DiscordNotificationProvider
    from datetime import datetime, timezone
    
    # Get config
    stmt = select(NotificationConfig).where(
        NotificationConfig.id == config_id,
        NotificationConfig.user_id == current_user.id
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found")
    
    # Create test alert object
    class TestAlert:
        def __init__(self):
            self.host_id = "test-host"
            self.metric = "test_metric"
            self.value = 99.9
            self.severity = "warning"
            self.message = "This is a test notification from LAMS"
            self.event_time = datetime.now(timezone.utc)
    
    test_alert = TestAlert()
    
    # Initialize provider
    if config.provider == "email":
        provider = EmailNotificationProvider(config.config)
    elif config.provider == "slack":
        provider = SlackNotificationProvider(config.config)
    elif config.provider == "discord":
        provider = DiscordNotificationProvider(config.config)
    else:
        raise HTTPException(status_code=400, detail="Invalid provider type")
    
    # Validate config
    if not provider.validate_config():
        raise HTTPException(status_code=400, detail="Invalid provider configuration - missing required fields")
    
    # Send test notification
    try:
        success = await provider.send(test_alert)
        return {"status": "success", "message": "Test notification sent successfully"}
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        # Extract meaningful error message
        error_detail = str(e)
        if "authentication" in error_detail.lower() or "credentials" in error_detail.lower():
            error_detail = "Authentication failed. Please check your SMTP username and password."
        elif "connection" in error_detail.lower() or "refused" in error_detail.lower():
            error_detail = "Connection failed. Please check your SMTP host and port."
        elif "timeout" in error_detail.lower():
            error_detail = "Connection timeout. Please check your SMTP server address."
        
        raise HTTPException(status_code=500, detail=error_detail)
