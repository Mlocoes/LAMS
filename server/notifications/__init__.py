"""
LAMS Notification System
Provides notification delivery through multiple channels (Email, Slack, Discord)
"""
from notifications.base import NotificationProvider
from notifications.email import EmailNotificationProvider
from notifications.slack import SlackNotificationProvider
from notifications.discord import DiscordNotificationProvider

__all__ = [
    "NotificationProvider",
    "EmailNotificationProvider",
    "SlackNotificationProvider",
    "DiscordNotificationProvider",
]
