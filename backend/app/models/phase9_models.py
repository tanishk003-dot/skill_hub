from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReadinessConfig(Base):
    __tablename__ = "readiness_configs"

    id = Column(Integer, primary_key=True, index=True)
    assessment_weight = Column(Float, nullable=False, default=0.30)
    coding_weight = Column(Float, nullable=False, default=0.25)
    training_weight = Column(Float, nullable=False, default=0.20)
    attendance_weight = Column(Float, nullable=False, default=0.15)
    consistency_weight = Column(Float, nullable=False, default=0.10)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    updater = relationship("User", foreign_keys=[updated_by])


class ReadinessAuditLog(Base):
    __tablename__ = "readiness_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_weights = Column(JSON, nullable=False)
    new_weights = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[changed_by])


class AseReadinessHistory(Base):
    __tablename__ = "ase_readiness_history"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, default=0.0)
    breakdown_json = Column(JSON, nullable=False, default=dict)
    skill_dna_json = Column(JSON, nullable=False, default=dict)
    formula_snapshot = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_demo = Column(Boolean, nullable=False, default=False)

    ase = relationship("User", foreign_keys=[ase_id])


class AseGamification(Base):
    __tablename__ = "ase_gamification"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    xp = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1)
    streak_days = Column(Integer, nullable=False, default=0)
    last_active_date = Column(String(20), nullable=True) # YYYY-MM-DD
    badges_json = Column(JSON, nullable=False, default=list) # [{id, name, icon, awarded_at, desc}]
    leaderboard_opt_in = Column(Boolean, nullable=False, default=False) # STRICT DEFAULT OFF
    show_full_name_publicly = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ase = relationship("User", foreign_keys=[ase_id])


class OnboardingMilestone(Base):
    __tablename__ = "onboarding_milestones"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_phase = Column(Integer, nullable=False) # 30, 60, 90
    milestone_type = Column(String(50), nullable=False) # ASSESSMENT, TRAINING, LIVE_CLASS, REASSESSMENT
    entity_id = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)

    ase = relationship("User", foreign_keys=[ase_id])


class AILearningRoadmap(Base):
    __tablename__ = "ai_learning_roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False, default=1)
    generated_from_weak_skills = Column(JSON, nullable=False, default=list)
    roadmap_items_json = Column(JSON, nullable=False, default=list) # [{id, title, skill, training_id, completed, due_date}]
    version = Column(Integer, nullable=False, default=1)
    is_stale = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_demo = Column(Boolean, nullable=False, default=False)

    ase = relationship("User", foreign_keys=[ase_id])


class AseRiskSignal(Base):
    __tablename__ = "ase_risk_signals"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    risk_score = Column(Float, nullable=False, default=0.0) # 0 to 100
    risk_level = Column(String(20), nullable=False, default="LOW") # LOW, MEDIUM, HIGH
    factors_json = Column(JSON, nullable=False, default=list)
    ai_explanation = Column(Text, nullable=False, default="")
    last_nudged_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ase = relationship("User", foreign_keys=[ase_id])
    mentor = relationship("User", foreign_keys=[mentor_id])


class MentorNudgeLog(Base):
    __tablename__ = "mentor_nudge_logs"

    id = Column(Integer, primary_key=True, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    mentor = relationship("User", foreign_keys=[mentor_id])
    ase = relationship("User", foreign_keys=[ase_id])


class ReassessmentSchedule(Base):
    __tablename__ = "reassessment_schedules"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="SET NULL"), nullable=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    phase_label = Column(String(50), nullable=False) # e.g. 30_DAY, 60_DAY, 90_DAY
    original_assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    reassessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=False, default="SCHEDULED") # SCHEDULED, COMPLETED, CANCELLED
    is_demo = Column(Boolean, nullable=False, default=False)

    cohort = relationship("Cohort", foreign_keys=[cohort_id])
    ase = relationship("User", foreign_keys=[ase_id])
    original_assessment = relationship("Assessment", foreign_keys=[original_assessment_id])
    reassessment = relationship("Assessment", foreign_keys=[reassessment_id])


class IssuedCertificate(Base):
    __tablename__ = "issued_certificates"

    id = Column(Integer, primary_key=True, index=True)
    cert_uuid = Column(String(64), nullable=False, unique=True, index=True) # UUID4
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False) # TRAINING, ASSESSMENT
    entity_id = Column(Integer, nullable=False)
    issue_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    pdf_file_path = Column(String(255), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, nullable=False, default=False)

    ase = relationship("User", foreign_keys=[ase_id])


class MockInterviewSession(Base):
    __tablename__ = "mock_interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = Column(String(100), nullable=False, default="Associate Software Engineer")
    skill_focus = Column(String(100), nullable=False, default="Backend Architecture")
    question_history_json = Column(JSON, nullable=False, default=list) # [{q, a, feedback}]
    feedback_json = Column(JSON, nullable=False, default=dict) # {strengths, improvements, rating}
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    ase = relationship("User", foreign_keys=[ase_id])


class MockInterviewRateLog(Base):
    __tablename__ = "mock_interview_rate_logs"

    id = Column(Integer, primary_key=True, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class PublicVerifyRateLog(Base):
    __tablename__ = "public_verify_rate_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
