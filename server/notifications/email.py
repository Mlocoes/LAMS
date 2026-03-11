"""
Email Notification Provider using SMTP
Supports standard SMTP servers (Gmail, SendGrid, etc.)
"""
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from notifications.base import NotificationProvider


class EmailNotificationProvider(NotificationProvider):
    """Send notifications via Email using SMTP"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email provider
        
        Config should contain:
            - smtp_host: SMTP server hostname
            - smtp_port: SMTP server port (usually 587 for TLS, 465 for SSL)
            - smtp_user: SMTP username
            - smtp_password: SMTP password
            - from_email: Sender email address
            - to_email: Recipient email address (or comma-separated list)
            - use_tls: Whether to use TLS (default: True)
        """
        super().__init__(config)
        self.smtp_host = config.get("smtp_host")
        # Ensure port is integer
        smtp_port = config.get("smtp_port", 587)
        self.smtp_port = int(smtp_port) if isinstance(smtp_port, str) else smtp_port
        self.smtp_user = config.get("smtp_user")
        self.smtp_password = config.get("smtp_password")
        self.from_email = config.get("from_email")
        self.to_email = config.get("to_email")
        self.use_tls = config.get("use_tls", True)
        
    def validate_config(self) -> bool:
        """Validate email configuration"""
        required_fields = [
            "smtp_host", "smtp_port", "smtp_user", 
            "smtp_password", "from_email", "to_email"
        ]
        
        for field in required_fields:
            if not getattr(self, field, None):
                self.logger.error(f"Email config missing required field: {field}")
                return False
        
        return True
    
    async def send(self, alert: Any) -> bool:
        """
        Send email notification
        
        Args:
            alert: Alert object
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.validate_config():
            self.logger.error("Invalid email configuration, skipping notification")
            return False
        
        # Run SMTP operations in a thread to avoid blocking event loop
        try:
            await asyncio.to_thread(self._send_sync, alert)
            self.logger.info(f"Email notification sent successfully to {self.to_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed - check credentials: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _send_sync(self, alert: Any) -> None:
        """
        Synchronous send method to be run in a thread
        
        Args:
            alert: Alert object
        """
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"🚨 LAMS Alert - {alert.severity.upper()} - {alert.host_id}"
        message["From"] = self.from_email
        message["To"] = self.to_email
        
        # Plain text version
        text_body = self.format_message(alert)
        
        # HTML version
        html_body = self._format_html_message(alert)
        
        # Attach both versions
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        if self.use_tls:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
    
    def _format_html_message(self, alert: Any) -> str:
        """Format alert as HTML email"""
        severity_color = "#ff6b6b" if alert.severity == "critical" else "#ffa500"
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px;">
                        <h2 style="margin: 0;">🚨 LAMS Alert - {alert.severity.upper()}</h2>
                    </div>
                    <div style="background-color: #f5f5f5; padding: 20px; margin-top: 10px; border-radius: 5px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Host:</td>
                                <td style="padding: 8px;">{alert.host_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Metric:</td>
                                <td style="padding: 8px;">{alert.metric}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Value:</td>
                                <td style="padding: 8px;">{alert.value:.2f}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Time:</td>
                                <td style="padding: 8px;">{alert.event_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Message:</td>
                                <td style="padding: 8px;">{alert.message}</td>
                            </tr>
                        </table>
                    </div>
                    <div style="margin-top: 20px; padding: 10px; background-color: #e3f2fd; border-left: 4px solid #2196f3;">
                        <p style="margin: 0; font-size: 12px; color: #666;">
                            This is an automated alert from your LAMS monitoring system.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
