from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class Cohort(Base):
    __tablename__ = "cohorts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("CohortMember", back_populates="cohort", cascade="all, delete-orphan")
    assignments = relationship("AssessmentAssignment", back_populates="cohort")


class CohortMember(Base):
    __tablename__ = "cohort_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    added_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    cohort = relationship("Cohort", back_populates="members")
    ase = relationship("User", foreign_keys=[ase_id], back_populates="cohort_membership")
