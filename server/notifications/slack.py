"""
Slack Notification Provider using Incoming Webhooks
Sends formatted messages to Slack channels
"""
import aiohttp
from typing import Dict, Any
from notifications.base import NotificationProvider


class SlackNotificationProvider(NotificationProvider):
    """Send notifications to Slack via Incoming Webhooks"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Slack provider
        
        Config should contain:
            - webhook_url: Slack Incoming Webhook URL
            - username: Bot username (optional, default: "LAMS Monitor")
            - icon_emoji: Bot icon emoji (optional, default: ":bell:")
            - channel: Channel override (optional)
        """
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.username = config.get("username", "LAMS Monitor")
        self.icon_emoji = config.get("icon_emoji", ":bell:")
        self.channel = config.get("channel")  # Optional channel override
        
    def validate_config(self) -> bool:
        """Validate Slack configuration"""
        if not self.webhook_url:
            self.logger.error("Slack webhook_url is required")
            return False
        
        if not self.webhook_url.startswith("https://hooks.slack.com/"):
            self.logger.error("Invalid Slack webhook URL format")
            return False
        
        return True
    
    async def send(self, alert: Any) -> bool:
        """
        Send Slack notification
        
        Args:
            alert: Alert object
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.validate_config():
            self.logger.error("Invalid Slack configuration, skipping notification")
            return False
        
        try:
            # Build Slack message payload
            payload = self._build_slack_payload(alert)
            
            # Send to Slack webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info("Slack notification sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Slack webhook returned {response.status}: {error_text}")
                        return False
                        
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP error sending Slack notification: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Slack notification: {e}")
            return False
    
    def _build_slack_payload(self, alert: Any) -> Dict[str, Any]:
        """Build Slack Block Kit formatted payload"""
        # Determine color based on severity
        color = "#dc3545" if alert.severity == "critical" else "#ffc107"
        icon = "🚨" if alert.severity == "critical" else "⚠️"
        
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{icon} LAMS Alert - {alert.severity.upper()}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Host:*\n{alert.host_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Metric:*\n{alert.metric}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Value:*\n{alert.value:.2f}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:*\n{alert.severity}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Message:*\n{alert.message}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"🕐 {alert.event_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Add channel override if specified
        if self.channel:
            payload["channel"] = self.channel
        
        return payload
