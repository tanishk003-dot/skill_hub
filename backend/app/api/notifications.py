from datetime import timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.phase13_models import UserNotificationPreference
from app.schemas.notification import NotificationOut, NotificationListResponse
from app.schemas.phase13_schemas import NotificationPreferenceOut, NotificationPreferenceUpdate

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=NotificationListResponse)
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 5: A user can only read their own notifications.
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    return NotificationListResponse(
        unread_count=unread_count,
        items=[NotificationOut.model_validate(n) for n in notifications]
    )

@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 5: A user can only mark their own notification as read (403/404 otherwise).
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    if notif.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify another user's notifications."
        )

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return NotificationOut.model_validate(notif)

@router.put("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 5: Marks all notifications of the current user as read.
    """
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .update({"is_read": True})
    )
    db.commit()
    return {"message": "All notifications marked as read.", "count": updated}

@router.get("/preferences", response_model=NotificationPreferenceOut)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves current user's notification channel preferences and quiet hours."""
    pref = db.query(UserNotificationPreference).filter(
        UserNotificationPreference.user_id == current_user.id
    ).first()

    if not pref:
        return NotificationPreferenceOut(
            preferred_channels=["IN_APP", "EMAIL"],
            quiet_hours_enabled=False,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            timezone="UTC",
            teams_recipient_id=None
        )

    channels = [c.strip().upper() for c in pref.preferred_channels.split(",") if c.strip()]
    return NotificationPreferenceOut(
        preferred_channels=channels,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        timezone=pref.timezone,
        teams_recipient_id=pref.teams_recipient_id
    )

@router.put("/preferences", response_model=NotificationPreferenceOut)
def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates current user's notification channel preferences and quiet hours."""
    pref = db.query(UserNotificationPreference).filter(
        UserNotificationPreference.user_id == current_user.id
    ).first()

    # Normalize channels
    valid_channels = {"IN_APP", "EMAIL", "TEAMS"}
    selected_channels = [c.upper() for c in payload.preferred_channels if c.upper() in valid_channels]
    if not selected_channels:
        selected_channels = ["IN_APP"]

    channels_str = ",".join(selected_channels)

    if not pref:
        pref = UserNotificationPreference(
            user_id=current_user.id,
            preferred_channels=channels_str,
            quiet_hours_enabled=payload.quiet_hours_enabled,
            quiet_hours_start=payload.quiet_hours_start,
            quiet_hours_end=payload.quiet_hours_end,
            timezone=payload.timezone,
            teams_recipient_id=payload.teams_recipient_id
        )
        db.add(pref)
    else:
        pref.preferred_channels = channels_str
        pref.quiet_hours_enabled = payload.quiet_hours_enabled
        pref.quiet_hours_start = payload.quiet_hours_start
        pref.quiet_hours_end = payload.quiet_hours_end
        pref.timezone = payload.timezone
        if payload.teams_recipient_id is not None:
            pref.teams_recipient_id = payload.teams_recipient_id

    db.commit()
    db.refresh(pref)

    return NotificationPreferenceOut(
        preferred_channels=selected_channels,
        quiet_hours_enabled=pref.quiet_hours_enabled,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        timezone=pref.timezone,
        teams_recipient_id=pref.teams_recipient_id
    )
