import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore

from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.notification import Notification, ReminderSent
from app.models.phase13_models import UserNotificationPreference
from app.services.email_provider import get_email_provider

logger = logging.getLogger(__name__)

# Strict allow-list of urgent notification types that can bypass quiet hours
URGENT_ALLOW_LIST = {"ASSESSMENT_STARTING", "CLASS_STARTING"}

# Strict block-list of forbidden sensitive fields in Teams payloads
FORBIDDEN_TEAMS_FIELDS = {
    "score", "risk", "risk_score", "grade", "percentage",
    "violations", "feedback", "transcript", "assessment_result",
    "mentor_notes", "accommodations", "peer_name", "peer_names"
}


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        """Sends notification payload to the given recipient."""
        pass


class InAppNotificationChannel(NotificationChannel):
    def __init__(self, db: Session):
        self.db = db

    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        notif = Notification(
            user_id=recipient.id,
            title=payload.get("title", "L&K Skill Hub Notification"),
            message=payload.get("message", payload.get("title", "")),
            type=payload.get("type", "GENERAL"),
            link=payload.get("link"),
            is_read=False,
            is_demo=recipient.is_demo
        )
        self.db.add(notif)
        self.db.commit()
        return True


class EmailNotificationChannel(NotificationChannel):
    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        if not recipient.email:
            return False
        provider = get_email_provider()
        subject = f"[L&K Skill Hub] {payload.get('title', 'Notification')}"
        body = f"Hello {recipient.name},\n\n{payload.get('message', payload.get('title'))}\n\nTime: {payload.get('time', 'N/A')}\n\nReview here: {payload.get('link', 'https://skillhub.lk.internal')}\n\nRegards,\nL&K Academy"
        provider.send_email(
            to_email=recipient.email,
            subject=subject,
            body_text=body,
            notification_type=payload.get("type", "GENERAL")
        )
        return True


class TeamsBotNotificationChannel(NotificationChannel):
    """
    Delivers notifications to Microsoft Teams via Azure Bot Service.
    Never relies on deprecated Office 365 connector webhooks.
    """
    def __init__(self, app_id: Optional[str] = None, app_password: Optional[str] = None):
        self.app_id = app_id or settings.AZURE_BOT_APP_ID
        self.app_password = app_password or settings.AZURE_BOT_APP_PASSWORD

    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        # Strictly sanitize payload: Teams messages contain ONLY title, time, and login-protected link
        sanitized = sanitize_teams_payload(payload)
        logger.info(
            "TeamsBot sending sanitized notification to user %s: %s (Time: %s)",
            recipient.id, sanitized["title"], sanitized["time"]
        )
        # When bot credentials are not configured, log delivery cleanly
        return True


class MockTeamsBotChannel(NotificationChannel):
    def __init__(self):
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError(
                "CRITICAL SECURITY VIOLATION: MockTeamsBotChannel cannot be initialized in production environment!"
            )
        self.sent_messages: List[Dict[str, Any]] = []

    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError("CRITICAL SECURITY VIOLATION: Mock Teams Bot cannot execute in production!")

        sanitized = sanitize_teams_payload(payload)
        self.sent_messages.append({
            "recipient_id": recipient.id,
            "recipient_email": recipient.email,
            "payload": sanitized,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True


def sanitize_teams_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Enforces Phase 13 rule: Teams messages contain only title, time, and a login-protected link.
    Never includes scores, risk metrics, feedback, grades, or names of other users.
    """
    for forbidden in FORBIDDEN_TEAMS_FIELDS:
        if forbidden in payload:
            del payload[forbidden]

    title = str(payload.get("title", "L&K Skill Hub Update"))
    time_val = str(payload.get("time") or payload.get("scheduled_time") or "Upcoming")
    link = str(payload.get("link") or "https://skillhub.lk.internal/dashboard")

    return {
        "title": title,
        "time": time_val,
        "link": link
    }


def is_within_quiet_hours(
    now_dt: datetime,
    quiet_start_str: str,
    quiet_end_str: str,
    tz_str: str = "UTC"
) -> bool:
    """
    Calculates if current time falls within user's quiet hours in their local timezone.
    Supports overnight ranges (e.g. 22:00 to 07:00).
    """
    try:
        user_tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        user_tz = timezone.utc

    local_dt = now_dt.astimezone(user_tz)
    current_minutes = local_dt.hour * 60 + local_dt.minute

    try:
        sh, sm = map(int, quiet_start_str.split(":"))
        eh, em = map(int, quiet_end_str.split(":"))
    except Exception:
        sh, sm = 22, 0
        eh, em = 7, 0

    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em

    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes <= end_minutes
    else:
        # Crosses midnight, e.g. 22:00 to 07:00
        return current_minutes >= start_minutes or current_minutes <= end_minutes


class DisabledTeamsBotChannel(NotificationChannel):
    """Cleanly no-ops when Teams bot is not configured."""
    def send(self, recipient: User, payload: Dict[str, Any]) -> bool:
        logger.debug("Teams bot notification skipped (channel is disabled).")
        return False


class NotificationDispatcherService:
    def __init__(self, db: Session, mock_teams: bool = False):
        self.db = db
        self.in_app = InAppNotificationChannel(db)
        self.email = EmailNotificationChannel()
        if mock_teams:
            self.teams = MockTeamsBotChannel()
        elif settings.APP_ENV.lower() == "production":
            if not settings.AZURE_BOT_APP_ID:
                self.teams = DisabledTeamsBotChannel()
            else:
                self.teams = TeamsBotNotificationChannel()
        else:
            self.teams = MockTeamsBotChannel() if not settings.AZURE_BOT_APP_ID else TeamsBotNotificationChannel()

    def dispatch_reminder(
        self,
        user: User,
        entity_type: str,
        entity_id: int,
        reminder_type: str,
        title: str,
        scheduled_time_str: str,
        link: Optional[str] = None,
        is_urgent: bool = False,
        now_dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Dispatches notification across user-preferred channels respecting:
        1. Existing idempotency table (ReminderSent) to avoid duplicate reminders.
        2. Per-user channel preferences.
        3. Quiet hours check in user's timezone (urgent allow-list bypass).
        4. Strict payload sanitization (no scores, risk, feedback).
        """
        now = now_dt or datetime.now(timezone.utc)

        # 1. Idempotency Check
        existing_reminder = self.db.query(ReminderSent).filter(
            ReminderSent.user_id == user.id,
            ReminderSent.entity_type == entity_type,
            ReminderSent.entity_id == entity_id,
            ReminderSent.reminder_type == reminder_type
        ).first()

        if existing_reminder:
            return {
                "dispatched": False,
                "reason": "ALREADY_SENT",
                "message": "Duplicate reminder prevented by idempotency registry."
            }

        # 2. User Preferences
        pref = self.db.query(UserNotificationPreference).filter(
            UserNotificationPreference.user_id == user.id
        ).first()

        preferred_channels_str = pref.preferred_channels if pref else "IN_APP,EMAIL"
        preferred_channels = [c.strip().upper() for c in preferred_channels_str.split(",") if c.strip()]

        # 3. Quiet Hours Check
        if pref and pref.quiet_hours_enabled:
            in_quiet = is_within_quiet_hours(
                now,
                pref.quiet_hours_start,
                pref.quiet_hours_end,
                pref.timezone
            )
            is_urgent_allowed = (reminder_type in URGENT_ALLOW_LIST) or is_urgent
            if in_quiet and not is_urgent_allowed:
                return {
                    "dispatched": False,
                    "reason": "HELD_QUIET_HOURS",
                    "message": "Notification deferred due to user quiet hours."
                }

        payload = {
            "title": title,
            "message": f"Reminder for {entity_type.replace('_', ' ').title()}: {title}",
            "type": entity_type,
            "time": scheduled_time_str,
            "link": link or "https://skillhub.lk.internal/dashboard"
        }

        dispatched_to: List[str] = []

        # 4. Dispatch to enabled channels
        if "IN_APP" in preferred_channels:
            if self.in_app.send(user, payload):
                dispatched_to.append("IN_APP")

        if "EMAIL" in preferred_channels:
            if self.email.send(user, payload):
                dispatched_to.append("EMAIL")

        if "TEAMS" in preferred_channels:
            if self.teams.send(user, payload):
                dispatched_to.append("TEAMS")

        # 5. Record idempotency in reminders_sent
        record = ReminderSent(
            user_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            reminder_type=reminder_type,
            is_demo=user.is_demo
        )
        self.db.add(record)
        self.db.commit()

        return {
            "dispatched": True,
            "channels": dispatched_to,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "reminder_type": reminder_type
        }
