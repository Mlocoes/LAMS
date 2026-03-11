"""
Base Abstract Class for Notification Providers
All notification providers must inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger("lams.notifications")


class NotificationProvider(ABC):
    """Abstract base class for notification providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize notification provider with configuration
        
        Args:
            config: Dictionary with provider-specific configuration
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.logger = logger
        
    @abstractmethod
    async def send(self, alert: Any) -> bool:
        """
        Send notification for an alert
        
        Args:
            alert: Alert object containing notification data
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate provider configuration
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass
    
    def format_message(self, alert: Any) -> str:
        """
        Format alert message for notification
        
        Args:
            alert: Alert object
            
        Returns:
            str: Formatted message string
        """
        return (
            f"🚨 LAMS Alert - {alert.severity.upper()}\n\n"
            f"Host: {alert.host_id}\n"
            f"Metric: {alert.metric}\n"
            f"Value: {alert.value:.2f}\n"
            f"Time: {alert.event_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Message: {alert.message}\n"
        )
    
    def should_send(self, alert: Any, severity_filter: str = "all") -> bool:
        """
        Determine if notification should be sent based on severity filter
        
        Args:
            alert: Alert object
            severity_filter: Filter level ("all", "warning", "critical")
            
        Returns:
            bool: True if notification should be sent
        """
        if not self.enabled:
            return False
            
        if severity_filter == "all":
            return True
        elif severity_filter == "warning":
            return alert.severity in ["warning", "critical"]
        elif severity_filter == "critical":
            return alert.severity == "critical"
        
        return True
