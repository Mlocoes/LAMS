import logging
from typing import List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NotificationConfig, User
from notifications.email import EmailNotificationProvider
from notifications.slack import SlackNotificationProvider
from notifications.discord import DiscordNotificationProvider

logger = logging.getLogger("lams.notifications")


async def get_notification_providers(session: AsyncSession) -> List:
    """
    Get all enabled notification providers from database
    
    Args:
        session: Database session
        
    Returns:
        List of initialized notification provider instances
    """
    providers = []
    
    try:
        # Get all enabled notification configs
        stmt = select(NotificationConfig).where(NotificationConfig.enabled == True)
        result = await session.execute(stmt)
        configs = result.scalars().all()
        
        for config in configs:
            try:
                # Initialize provider based on type
                if config.provider == "email":
                    provider = EmailNotificationProvider(config.config)
                elif config.provider == "slack":
                    provider = SlackNotificationProvider(config.config)
                elif config.provider == "discord":
                    provider = DiscordNotificationProvider(config.config)
                else:
                    logger.warning(f"Unknown provider type: {config.provider}")
                    continue
                
                # Validate configuration
                if provider.validate_config():
                    # Store severity filter for later use
                    provider.severity_filter = config.severity_filter
                    providers.append(provider)
                else:
                    logger.warning(f"Invalid configuration for {config.provider} provider (ID: {config.id})")
                    
            except Exception as e:
                logger.error(f"Error initializing provider {config.provider}: {e}")
                continue
        
        logger.info(f"Loaded {len(providers)} notification providers")
        
    except Exception as e:
        logger.error(f"Error loading notification providers: {e}")
    
    return providers


async def send_alert_notification(alert, session: AsyncSession):
    """
    Send notifications for an alert through all enabled providers
    
    Args:
        alert: Alert object to notify about
        session: Database session for loading notification configs
    """
    try:
        providers = await get_notification_providers(session)
        
        if not providers:
            logger.info("No notification providers configured, skipping notifications")
            return
        
        # Send through each provider
        sent_count = 0
        for provider in providers:
            try:
                # Check if alert matches severity filter
                if provider.should_send(alert, provider.severity_filter):
                    success = await provider.send(alert)
                    if success:
                        sent_count += 1
                else:
                    logger.debug(f"Alert severity '{alert.severity}' filtered out by {provider.__class__.__name__}")
                    
            except Exception as e:
                logger.error(f"Failed to send notification via {provider.__class__.__name__}: {e}")
        
        if sent_count > 0:
            logger.info(f"Alert notifications sent successfully via {sent_count} provider(s)")
        else:
            logger.warning("Failed to send notifications through any provider")
            
    except Exception as e:
        logger.error(f"Error in notification dispatch: {e}")
