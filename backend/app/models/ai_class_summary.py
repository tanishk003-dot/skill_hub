from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class ClassTranscript(Base):
    __tablename__ = "class_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_text = Column(Text, nullable=True) # None when auto-deleted or manually deleted
    topics_covered = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), nullable=True) # "txt", "vtt", "docx", "notes"
    privacy_consent_acknowledged = Column(Boolean, nullable=False, default=False)
    token_count = Column(Integer, nullable=False, default=0)
    used_token_count = Column(Integer, nullable=False, default=0)
    truncated_ratio = Column(Float, nullable=False, default=1.0) # 1.0 = 100% of transcript used
    expires_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    uploader = relationship("User", foreign_keys=[uploaded_by])
    live_class = relationship("LiveClass", foreign_keys=[live_class_id])
    training = relationship("Training", foreign_keys=[training_id])
    summaries = relationship("ClassSummary", back_populates="transcript", cascade="all, delete-orphan")


class ClassSummary(Base):
    __tablename__ = "class_summaries"

    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(Integer, ForeignKey("class_transcripts.id", ondelete="SET NULL"), nullable=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    key_topics = Column(JSON, nullable=False, default=list) # ["Topic 1", ...]
    key_concepts = Column(JSON, nullable=False, default=list) # [{"concept": "...", "explanation": "..."}]
    practical_examples = Column(JSON, nullable=False, default=list) # ["Example 1", ...]
    ase_recap = Column(Text, nullable=False, default="")
    suggested_homework = Column(JSON, nullable=False, default=list) # ["Task 1", ...]
    is_published = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    transcript = relationship("ClassTranscript", back_populates="summaries")
    creator = relationship("User", foreign_keys=[created_by])
    live_class = relationship("LiveClass", foreign_keys=[live_class_id])
    training = relationship("Training", foreign_keys=[training_id])


class AIGeneratedAssessment(Base):
    __tablename__ = "ai_generated_assessments"

    id = Column(Integer, primary_key=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    generation_mode = Column(String(50), nullable=False, default="AUTO") # AUTO, BANK, MIXED
    status = Column(String(50), nullable=False, default="DRAFT") # DRAFT, APPROVED, PUBLISHED
    recommended_total_questions = Column(Integer, nullable=False, default=20)
    difficulty_split = Column(JSON, nullable=False, default=dict) # {"EASY": 40, "MEDIUM": 40, "HARD": 20}
    topic_split = Column(JSON, nullable=False, default=dict) # {"Topic A": 5, "Topic B": 5}
    is_immutable = Column(Boolean, nullable=False, default=False) # True once assigned to any ASE
    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey("ai_generated_assessments.id", ondelete="SET NULL"), nullable=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by])
    live_class = relationship("LiveClass", foreign_keys=[live_class_id])
    training = relationship("Training", foreign_keys=[training_id])
    assessment = relationship("Assessment", foreign_keys=[assessment_id])
    questions = relationship("AIGeneratedQuestion", back_populates="ai_assessment", cascade="all, delete-orphan")


class AIGeneratedQuestion(Base):
    __tablename__ = "ai_generated_questions"

    id = Column(Integer, primary_key=True, index=True)
    ai_assessment_id = Column(Integer, ForeignKey("ai_generated_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_bank_id = Column(Integer, ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True)
    question_type = Column(String(50), nullable=False, default="SINGLE_CHOICE") # SINGLE_CHOICE, MULTI_CHOICE, CODING
    skill_category = Column(String(100), nullable=False, default="General")
    difficulty = Column(String(50), nullable=False, default="MEDIUM") # EASY, MEDIUM, HARD
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False, default=list) # ["Option A", "Option B", ...]
    correct_answers = Column(JSON, nullable=False, default=list) # ["Option A"]
    explanation = Column(Text, nullable=False, default="")
    source = Column(String(50), nullable=False, default="AI generated") # "AI generated" or "Question Bank"
    review_status = Column(String(50), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    mentor_verify_required = Column(Boolean, nullable=False, default=False)
    quality_flags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ai_assessment = relationship("AIGeneratedAssessment", back_populates="questions")
    question_bank_ref = relationship("QuestionBank", foreign_keys=[question_bank_id])


class ClassEffectivenessReport(Base):
    __tablename__ = "class_effectiveness_reports"

    id = Column(Integer, primary_key=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=True, index=True)
    generated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    total_attempts = Column(Integer, nullable=False, default=0)
    topic_scores = Column(JSON, nullable=False, default=dict) # {"Topic": avg_score_pct}
    missed_concepts = Column(JSON, nullable=False, default=list) # [{"concept": "...", "score": 45.0, "reason": "..."}]
    suggested_revision_topics = Column(JSON, nullable=False, default=list)
    follow_up_proposal = Column(JSON, nullable=False, default=dict) # {"title": "...", "duration_minutes": 15, "topics": [...]}
    has_enough_data = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    live_class = relationship("LiveClass", foreign_keys=[live_class_id])
    assessment = relationship("Assessment", foreign_keys=[assessment_id])
    generator = relationship("User", foreign_keys=[generated_by])


class AIGenerateRateLog(Base):
    __tablename__ = "ai_generate_rate_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False) # "SUMMARY", "ASSESSMENT_GENERATE"
    question_count = Column(Integer, nullable=False, default=0)
    tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", foreign_keys=[user_id])
