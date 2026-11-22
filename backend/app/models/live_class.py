from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class LiveClass(Base):
    __tablename__ = "live_classes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, default=60)
    audience_type = Column(String(50), nullable=False, default="COHORT") # ALL, COHORT, SELECTED
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="SET NULL"), nullable=True, index=True)
    meeting_link = Column(String(500), nullable=False)
    provider = Column(String(50), nullable=False, default="MANUAL") # MANUAL, TEAMS_GRAPH
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by])
    cohort = relationship("Cohort", foreign_keys=[cohort_id])
    attendees = relationship("LiveClassAttendee", back_populates="live_class", cascade="all, delete-orphan")

class LiveClassAttendee(Base):
    __tablename__ = "live_class_attendees"

    id = Column(Integer, primary_key=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="INVITED") # INVITED, ATTENDED, ABSENT
    marked_at = Column(DateTime, nullable=True)
    marked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("live_class_id", "ase_id", name="uk_class_ase"),
    )

    live_class = relationship("LiveClass", back_populates="attendees")
    ase = relationship("User", foreign_keys=[ase_id])
    marker = relationship("User", foreign_keys=[marked_by])
