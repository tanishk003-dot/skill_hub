import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base, DateTime6

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MENTOR = "MENTOR"
    ASE = "ASE"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=UserRole.ASE, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    last_splash_date = Column(String(20), nullable=True)
    fresh_login = Column(Boolean, nullable=False, default=False)
    is_buddy_volunteer = Column(Boolean, nullable=False, default=False)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    lockout_until = Column(DateTime6(), nullable=True)
    is_locked = Column(Boolean, nullable=False, default=False)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Mentor's assigned mentees (assignments where user is mentor)
    mentee_assignments = relationship(
        "MentorAseAssignment",
        foreign_keys="MentorAseAssignment.mentor_id",
        back_populates="mentor",
        cascade="all, delete-orphan"
    )
    # ASE's mentor assignment (assignment where user is ASE - unique 1-to-1)
    mentor_assignment = relationship(
        "MentorAseAssignment",
        foreign_keys="MentorAseAssignment.ase_id",
        back_populates="ase",
        uselist=False,
        cascade="all, delete-orphan"
    )
    cohort_membership = relationship(
        "CohortMember",
        foreign_keys="CohortMember.ase_id",
        back_populates="ase",
        uselist=False,
        cascade="all, delete-orphan"
    )
