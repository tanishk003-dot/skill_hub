import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, Enum, JSON, String
from sqlalchemy.orm import relationship
from app.core.database import Base, DateTime6

class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"
    AUTO_SUBMITTED_VIOLATION = "AUTO_SUBMITTED_VIOLATION"

def get_utc_now():
    return datetime.now(timezone.utc)

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_assignment_id = Column(Integer, ForeignKey("assessment_assignments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=get_utc_now, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(Enum(AttemptStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=AttemptStatus.IN_PROGRESS, index=True)
    
    total_score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Float, nullable=False, default=0.0)
    percentage = Column(Float, nullable=False, default=0.0)
    passed = Column(Boolean, nullable=False, default=False)
    
    section_scores = Column(JSON, nullable=True)     # [{"section_id": 1, "title": "...", "score": 4, "max": 5, "percentage": 80.0}]
    skill_percentages = Column(JSON, nullable=True)  # {"Numerical": 85.0, "Deduction": 60.0}
    strong_areas = Column(JSON, nullable=True)       # ["Numerical"]
    weak_areas = Column(JSON, nullable=True)         # ["Deduction"]

    # Phase 3 Proctoring fields
    violation_count = Column(Integer, nullable=False, default=0)
    auto_submit_reason = Column(String(255), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)

    # Phase 10 Webcam Proctoring & Accommodations fields
    camera_override_active = Column(Boolean, nullable=False, default=False)
    camera_exempt = Column(Boolean, nullable=False, default=False)
    accommodation_applied = Column(Boolean, nullable=False, default=False)
    extended_total_duration_minutes = Column(Integer, nullable=True)
    last_camera_heartbeat_at = Column(DateTime6(), nullable=True)
    camera_status = Column(String(30), nullable=False, default="INITIALIZING")

    # Relationships
    assignment = relationship("AssessmentAssignment", back_populates="attempt")
    ase = relationship("User", foreign_keys=[ase_id])
    responses = relationship("AssessmentResponse", back_populates="attempt", cascade="all, delete-orphan")
    violations = relationship("ExamViolation", back_populates="attempt", cascade="all, delete-orphan", order_by="ExamViolation.occurred_at")


class ExamViolation(Base):
    __tablename__ = "exam_violations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    occurred_at = Column(DateTime6(), default=get_utc_now, nullable=False, index=True)
    details = Column(JSON, nullable=True)

    attempt = relationship("AssessmentAttempt", back_populates="violations")


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_options = Column(JSON, nullable=False)  # list of strings e.g. ["opt1"]
    is_correct = Column(Boolean, nullable=False, default=False)
    marks_obtained = Column(Float, nullable=False, default=0.0)
    time_spent_seconds = Column(Float, nullable=False, default=0.0)
    question_version = Column(Integer, nullable=False, default=1)

    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="responses")
    question = relationship("QuestionBank")
