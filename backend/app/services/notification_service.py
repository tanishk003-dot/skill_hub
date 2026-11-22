from typing import Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User
from app.services.email_provider import get_email_provider

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "GENERAL",
    link: Optional[str] = None,
    send_email: bool = True,
    is_demo: bool = False
) -> Notification:
    """
    Creates an in-app notification record and dispatches an email notification.
    """
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        link=link,
        is_read=False,
        is_demo=is_demo
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    if send_email:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            email_provider = get_email_provider()
            subject = f"[L&K Skill Hub] {title}"
            body_text = f"Hello {user.name},\n\n{message}\n\nLog in to L&K Skill Hub to review your dashboard.\n\nRegards,\nL&K Academy Team"
            email_provider.send_email(
                to_email=user.email,
                subject=subject,
                body_text=body_text,
                notification_type=notification_type
            )

    return notif
