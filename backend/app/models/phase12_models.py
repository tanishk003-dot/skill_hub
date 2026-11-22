from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base, DateTime6

def get_utc_now():
    return datetime.now(timezone.utc)

# ==================== BUDDY SYSTEM ENUMS & MODELS ====================

class BuddyPairingStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CHANGE_REQUESTED = "CHANGE_REQUESTED"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"

class BuddyMilestoneStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED_BY_BUDDEE = "CONFIRMED_BY_BUDDEE"
    VERIFIED_BY_MENTOR = "VERIFIED_BY_MENTOR"

class BuddyPairing(Base):
    __tablename__ = "buddy_pairings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    buddy_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    buddee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(BuddyPairingStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=BuddyPairingStatus.ACTIVE, index=True)
    paired_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paired_at = Column(DateTime, default=get_utc_now, nullable=False)
    change_reason = Column(String(500), nullable=True)
    change_requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_requested_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("buddy_id != buddee_id", name="chk_buddy_no_self_pair"),
    )

    buddy = relationship("User", foreign_keys=[buddy_id])
    buddee = relationship("User", foreign_keys=[buddee_id])
    milestones = relationship("BuddyMilestone", back_populates="pairing", cascade="all, delete-orphan")
    ratings = relationship("BuddyRating", back_populates="pairing", cascade="all, delete-orphan")

class BuddyRating(Base):
    __tablename__ = "buddy_ratings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pairing_id = Column(Integer, ForeignKey("buddy_pairings.id", ondelete="CASCADE"), nullable=False, index=True)
    rated_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    feedback = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    pairing = relationship("BuddyPairing", back_populates="ratings")
    rater = relationship("User", foreign_keys=[rated_by_id])

class BuddyMilestone(Base):
    __tablename__ = "buddy_milestones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pairing_id = Column(Integer, ForeignKey("buddy_pairings.id", ondelete="CASCADE"), nullable=False, index=True)
    buddy_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    buddee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(Enum(BuddyMilestoneStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=BuddyMilestoneStatus.PENDING, index=True)
    xp_amount = Column(Integer, nullable=False, default=25)
    xp_awarded = Column(Boolean, nullable=False, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    pairing = relationship("BuddyPairing", back_populates="milestones")
    buddy = relationship("User", foreign_keys=[buddy_id])
    buddee = relationship("User", foreign_keys=[buddee_id])


# ==================== FORUM ENUMS & MODELS ====================

class ForumPostStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    HELD_FOR_REVIEW = "HELD_FOR_REVIEW"
    HIDDEN = "HIDDEN"
    REJECTED = "REJECTED"

class ForumReportReason(str, enum.Enum):
    OFF_TOPIC = "OFF_TOPIC"
    EXAM_LEAK = "EXAM_LEAK"
    HARASSMENT = "HARASSMENT"
    SPAM = "SPAM"
    PII_VIOLATION = "PII_VIOLATION"
    OTHER = "OTHER"

class ForumReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISMISSED = "DISMISSED"
    ACTIONED = "ACTIONED"

class ForumPost(Base):
    __tablename__ = "forum_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(250), nullable=False)
    body = Column(Text, nullable=False)
    tags = Column(String(255), nullable=True)  # comma-separated skill or class tags
    tagged_assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    is_anonymous = Column(Boolean, nullable=False, default=False, index=True)
    status = Column(Enum(ForumPostStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=ForumPostStatus.PUBLISHED, index=True)
    held_reason = Column(String(500), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(String(500), nullable=True)
    
    is_resolved = Column(Boolean, nullable=False, default=False, index=True)
    accepted_answer_id = Column(Integer, nullable=True)  # references forum_answers.id
    view_count = Column(Integer, nullable=False, default=0)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    cohort = relationship("Cohort", foreign_keys=[cohort_id])
    author = relationship("User", foreign_keys=[author_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    tagged_assessment = relationship("Assessment", foreign_keys=[tagged_assessment_id])
    answers = relationship("ForumAnswer", back_populates="post", cascade="all, delete-orphan", order_by="ForumAnswer.created_at")
    reports = relationship("ForumReport", back_populates="post", cascade="all, delete-orphan")

class ForumAnswer(Base):
    __tablename__ = "forum_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, nullable=False, default=False, index=True)
    
    is_accepted = Column(Boolean, nullable=False, default=False, index=True)
    is_mentor_verified = Column(Boolean, nullable=False, default=False, index=True)
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    is_ai_generated = Column(Boolean, nullable=False, default=False, index=True)
    ai_model = Column(String(50), nullable=True)
    
    is_hidden = Column(Boolean, nullable=False, default=False, index=True)
    hidden_reason = Column(String(500), nullable=True)
    upvote_count = Column(Integer, nullable=False, default=0)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    post = relationship("ForumPost", back_populates="answers")
    author = relationship("User", foreign_keys=[author_id])
    verifier = relationship("User", foreign_keys=[verified_by])
    votes = relationship("ForumVote", back_populates="answer", cascade="all, delete-orphan")
    reports = relationship("ForumReport", back_populates="answer", cascade="all, delete-orphan")

class ForumVote(Base):
    __tablename__ = "forum_votes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id = Column(Integer, ForeignKey("forum_answers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vote_type = Column(Integer, nullable=False, default=1)  # +1 upvote
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("answer_id", "user_id", name="uk_forum_vote_answer_user"),
    )

    answer = relationship("ForumAnswer", back_populates="votes")
    user = relationship("User", foreign_keys=[user_id])

class ForumReport(Base):
    __tablename__ = "forum_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=True, index=True)
    answer_id = Column(Integer, ForeignKey("forum_answers.id", ondelete="CASCADE"), nullable=True, index=True)
    reason = Column(Enum(ForumReportReason, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    notes = Column(String(500), nullable=True)
    status = Column(Enum(ForumReportStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=ForumReportStatus.PENDING, index=True)
    action_taken = Column(String(200), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        # Note: Handled by service logic to allow unique (reporter, post) or (reporter, answer)
    )

    reporter = relationship("User", foreign_keys=[reporter_id])
    post = relationship("ForumPost", back_populates="reports")
    answer = relationship("ForumAnswer", back_populates="reports")
    resolver = relationship("User", foreign_keys=[resolved_by])

class ForumIdentityAuditLog(Base):
    __tablename__ = "forum_identity_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    viewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_role = Column(String(50), nullable=False)
    target_type = Column(String(20), nullable=False)  # "POST" or "ANSWER"
    target_id = Column(Integer, nullable=False, index=True)
    revealed_author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime6(), default=get_utc_now, nullable=False)

    viewer = relationship("User", foreign_keys=[viewer_id])
    revealed_author = relationship("User", foreign_keys=[revealed_author_id])

class ForumFilterAuditLog(Base):
    __tablename__ = "forum_filter_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False)  # "POST" or "ANSWER"
    detected_category = Column(String(50), nullable=False)  # "PHONE_PATTERN", "EMAIL_PATTERN", "PROFANITY", "CREDENTIAL_PATTERN"
    action = Column(String(50), nullable=False, default="BLOCKED_PRE_SUBMISSION")
    created_at = Column(DateTime6(), default=get_utc_now, nullable=False)

    user = relationship("User", foreign_keys=[user_id])

class ForumRateLimit(Base):
    __tablename__ = "forum_rate_limits"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(30), nullable=False, index=True)  # "QUESTION", "ANSWER", "AI_DRAFT"
    created_at = Column(DateTime6(), default=get_utc_now, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
