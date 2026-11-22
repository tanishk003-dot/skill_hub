import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("skillhub.email")

class BaseEmailProvider(ABC):
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body_text: str, notification_type: str = "GENERAL", body_html: Optional[str] = None) -> bool:
        """Sends an email notification."""
        pass

class ConsoleEmailProvider(BaseEmailProvider):
    def send_email(self, to_email: str, subject: str, body_text: str, notification_type: str = "GENERAL", body_html: Optional[str] = None) -> bool:
        # Strict adherence to security requirement:
        # Never log SMTP credentials or full email bodies containing personal data.
        # ConsoleEmailProvider logs ONLY recipient, subject and notification type.
        logger.info(
            f"[EMAIL DISPATCH] Recipient: {to_email} | Subject: '{subject}' | Type: {notification_type}"
        )
        return True

class SMTPEmailProvider(BaseEmailProvider):
    def send_email(self, to_email: str, subject: str, body_text: str, notification_type: str = "GENERAL", body_html: Optional[str] = None) -> bool:
        if not settings.SMTP_HOST:
            logger.warning("[EMAIL] SMTP_HOST not configured. Falling back to console dispatch.")
            return ConsoleEmailProvider().send_email(to_email, subject, body_text, notification_type)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_PORT == 587:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())

            logger.info(f"[EMAIL DISPATCH VIA SMTP] Recipient: {to_email} | Subject: '{subject}' | Type: {notification_type}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Failed to send email to {to_email}: {str(e)}")
            return False

def get_email_provider() -> BaseEmailProvider:
    if settings.SMTP_HOST:
        return SMTPEmailProvider()
    return ConsoleEmailProvider()
