"""
Discord Notification Provider using Webhooks
Sends formatted embeds to Discord channels
"""
import aiohttp
from typing import Dict, Any
from notifications.base import NotificationProvider


class DiscordNotificationProvider(NotificationProvider):
    """Send notifications to Discord via Webhooks"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Discord provider
        
        Config should contain:
            - webhook_url: Discord Webhook URL
            - username: Bot username (optional, default: "LAMS Monitor")
            - avatar_url: Bot avatar URL (optional)
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.username = config.get("username", "LAMS Monitor")
        self.avatar_url = config.get("avatar_url")
        
    def validate_config(self) -> bool:
        """Validate Discord configuration"""
        if not self.webhook_url:
            self.logger.error("Discord webhook_url is required")
            return False
        
        if not self.webhook_url.startswith("https://discord.com/api/webhooks/"):
            self.logger.error("Invalid Discord webhook URL format")
            return False
        
        return True
    
    async def send(self, alert: Any) -> bool:
        """
        Send Discord notification
        
        Args:
            alert: Alert object
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.validate_config():
            self.logger.error("Invalid Discord configuration, skipping notification")
            return False
        
        try:
            # Build Discord embed payload
            payload = self._build_discord_payload(alert)
            
            # Send to Discord webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 204]:
                        self.logger.info("Discord notification sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Discord webhook returned {response.status}: {error_text}")
                        return False
                        
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error sending Discord notification: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Discord notification: {e}")
            return False
    
    def _build_discord_payload(self, alert: Any) -> Dict[str, Any]:
        """Build Discord embed formatted payload"""
        # Determine color based on severity (Discord uses decimal color codes)
        # Critical: Red (#dc3545 = 14431557), Warning: Orange (#ffc107 = 16761095)
        color = 14431557 if alert.severity == "critical" else 16761095
        icon = "🚨" if alert.severity == "critical" else "⚠️"
        
        payload = {
            "username": self.username,
            "embeds": [
                {
                    "title": f"{icon} LAMS Alert - {alert.severity.upper()}",
                    "color": color,
                    "fields": [
                        {
                            "name": "🖥️ Host",
                            "value": alert.host_id,
                            "inline": True
                        },
                        {
                            "name": "📊 Metric",
                            "value": alert.metric,
                            "inline": True
                        },
                        {
                            "name": "📈 Value",
                            "value": f"{alert.value:.2f}",
                            "inline": True
                        },
                        {
                            "name": "⚡ Severity",
                            "value": alert.severity.upper(),
                            "inline": True
                        },
                        {
                            "name": "💬 Message",
                            "value": alert.message,
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"LAMS Monitoring System"
                    },
                    "timestamp": alert.event_time.isoformat()
                }
            ]
        }
        
        # Add avatar URL if specified
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        
        return payload
