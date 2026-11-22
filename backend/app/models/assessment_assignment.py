import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class AssessmentAssignment(Base):
    __tablename__ = "assessment_assignments"
    __table_args__ = (
        UniqueConstraint("assessment_id", "ase_id", name="uk_assessment_ase"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    assessment = relationship("Assessment", back_populates="assignments")
    cohort = relationship("Cohort", back_populates="assignments")
    ase = relationship("User", foreign_keys=[ase_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    attempt = relationship("AssessmentAttempt", back_populates="assignment", uselist=False, cascade="all, delete-orphan")
