import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class GoalStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    ABANDONED = "ABANDONED"

class QuestionItemAnalytics(Base):
    __tablename__ = "question_item_analytics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    question_version = Column(Integer, nullable=False, default=1, index=True)
    
    attempts_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    difficulty_index = Column(Float, nullable=False, default=0.0)      # p = correct / attempts
    discrimination_index = Column(Float, nullable=False, default=0.0)  # D = (U_corr - L_corr) / (0.27 * N)
    is_indicative_discrimination = Column(Boolean, nullable=False, default=False) # True when 10 <= N < 30
    
    most_chosen_wrong_option = Column(String(100), nullable=True)
    avg_time_seconds = Column(Float, nullable=False, default=0.0)
    
    is_too_easy = Column(Boolean, nullable=False, default=False)       # p > 0.95 when N >= 10
    is_too_hard = Column(Boolean, nullable=False, default=False)       # p < 0.10 when N >= 10
    is_poor_discrimination = Column(Boolean, nullable=False, default=False) # D < 0.20 or D <= 0 when N >= 30
    needs_review = Column(Boolean, nullable=False, default=False)
    review_reason = Column(String(255), nullable=True)
    
    option_distribution = Column(JSON, nullable=True)                  # e.g. {"opt1": 20, "opt2": 4}
    formula_metadata = Column(JSON, nullable=True)                     # snapshot of formulas and N values
    
    calculated_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    is_demo = Column(Boolean, nullable=False, default=False)

    question = relationship("QuestionBank")


class OneOnOneMeeting(Base):
    __tablename__ = "one_on_one_meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mentee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    meeting_date = Column(DateTime, nullable=False)
    status = Column(Enum(MeetingStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=MeetingStatus.SCHEDULED)
    
    shared_notes = Column(Text, nullable=True)                         # Visible to mentor and mentee
    encrypted_private_notes = Column(Text, nullable=True)              # AES/Fernet at rest, strictly mentor only
    ai_summary_shared = Column(Text, nullable=True)
    ai_summary_private = Column(Text, nullable=True)                   # Visible to mentor only
    
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    mentor = relationship("User", foreign_keys=[mentor_id])
    mentee = relationship("User", foreign_keys=[mentee_id])
    goals = relationship("OneOnOneGoal", back_populates="meeting", cascade="all, delete-orphan")
    action_items = relationship("OneOnOneActionItem", back_populates="meeting", cascade="all, delete-orphan")
    comments = relationship("OneOnOneComment", back_populates="meeting", cascade="all, delete-orphan")


class OneOnOneGoal(Base):
    __tablename__ = "one_on_one_goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("one_on_one_meetings.id", ondelete="SET NULL"), nullable=True, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mentee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=False)
    status = Column(Enum(GoalStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=GoalStatus.NOT_STARTED)
    
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    meeting = relationship("OneOnOneMeeting", back_populates="goals")
    mentor = relationship("User", foreign_keys=[mentor_id])
    mentee = relationship("User", foreign_keys=[mentee_id])
    action_items = relationship("OneOnOneActionItem", back_populates="goal", cascade="all, delete-orphan")
    comments = relationship("OneOnOneComment", back_populates="goal", cascade="all, delete-orphan")


class OneOnOneActionItem(Base):
    __tablename__ = "one_on_one_action_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("one_on_one_meetings.id", ondelete="CASCADE"), nullable=True, index=True)
    goal_id = Column(Integer, ForeignKey("one_on_one_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    mentor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mentee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task = Column(Text, nullable=False)
    assigned_to = Column(String(30), nullable=False, default="ASE")     # "ASE" or "MENTOR"
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    meeting = relationship("OneOnOneMeeting", back_populates="action_items")
    goal = relationship("OneOnOneGoal", back_populates="action_items")
    mentor = relationship("User", foreign_keys=[mentor_id])
    mentee = relationship("User", foreign_keys=[mentee_id])
    comments = relationship("OneOnOneComment", back_populates="action_item", cascade="all, delete-orphan")


class OneOnOneComment(Base):
    __tablename__ = "one_on_one_comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(Integer, ForeignKey("one_on_one_meetings.id", ondelete="CASCADE"), nullable=True, index=True)
    goal_id = Column(Integer, ForeignKey("one_on_one_goals.id", ondelete="CASCADE"), nullable=True, index=True)
    action_item_id = Column(Integer, ForeignKey("one_on_one_action_items.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    comment_text = Column(Text, nullable=False)
    
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    meeting = relationship("OneOnOneMeeting", back_populates="comments")
    goal = relationship("OneOnOneGoal", back_populates="comments")
    action_item = relationship("OneOnOneActionItem", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])


class ReportingApiToken(Base):
    __tablename__ = "reporting_api_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256
    created_by_admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scopes = Column(JSON, nullable=False)                                      # ["assessments", "results", ...]
    include_pii = Column(Boolean, nullable=False, default=False)
    allowed_ips = Column(JSON, nullable=True)                                  # list of IP strings
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    last_used_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    creator = relationship("User", foreign_keys=[created_by_admin_id])
    audit_logs = relationship("ReportingTokenAuditLog", back_populates="token", cascade="all, delete-orphan")


class ReportingTokenAuditLog(Base):
    __tablename__ = "reporting_token_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token_id = Column(Integer, ForeignKey("reporting_api_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    endpoint = Column(String(255), nullable=False)
    accessed_at = Column(DateTime, default=get_utc_now, nullable=False)

    token = relationship("ReportingApiToken", back_populates="audit_logs")


class StaffingProject(Base):
    __tablename__ = "staffing_projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    headcount = Column(Integer, nullable=False, default=1)
    start_date = Column(DateTime, nullable=False)
    ready_now_threshold_pct = Column(Float, nullable=False, default=90.0)      # Configurable threshold (default 90%)
    status = Column(String(30), nullable=False, default="PLANNING")            # PLANNING, ACTIVE, COMPLETED, CANCELLED
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    creator = relationship("User", foreign_keys=[created_by_user_id])
    skills = relationship("StaffingProjectSkill", back_populates="project", cascade="all, delete-orphan")


class StaffingProjectSkill(Base):
    __tablename__ = "staffing_project_skills"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("staffing_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False)
    min_level_pct = Column(Float, nullable=False, default=70.0)
    weight = Column(Float, nullable=False, default=1.0)

    project = relationship("StaffingProject", back_populates="skills")
