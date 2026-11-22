from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    skill_category = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False, default="Self-paced") # Self-paced, Live class, Workshop
    resources = Column(JSON, nullable=False, default=list) # [{name, url, file_path, type}]
    duration_hours = Column(Float, nullable=False, default=1.0)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by])
    assignments = relationship("TrainingAssignment", back_populates="training", cascade="all, delete-orphan")

class TrainingAssignment(Base):
    __tablename__ = "training_assignments"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=False, default="NOT_STARTED") # NOT_STARTED, IN_PROGRESS, COMPLETED
    progress_percent = Column(Float, nullable=False, default=0.0)
    completed_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("training_id", "ase_id", name="uk_training_ase"),
    )

    training = relationship("Training", back_populates="assignments")
    ase = relationship("User", foreign_keys=[ase_id])
    cohort = relationship("Cohort", foreign_keys=[cohort_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
