from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default="GENERAL") # ASSESSMENT, TRAINING, LIVE_CLASS, REMINDER, RESULT
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", foreign_keys=[user_id])

class ReminderSent(Base):
    __tablename__ = "reminders_sent"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False) # ASSESSMENT, TRAINING, LIVE_CLASS
    entity_id = Column(Integer, nullable=False)
    reminder_type = Column(String(50), nullable=False, default="24H_BEFORE") # 24H_BEFORE
    sent_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_demo = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", "reminder_type", name="uk_reminder_idempotent"),
    )

    user = relationship("User", foreign_keys=[user_id])
