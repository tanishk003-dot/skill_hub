from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(30), nullable=False)
    source_code = Column(Text, nullable=False)
    passed_sample_cases = Column(Integer, default=0, nullable=False)
    total_sample_cases = Column(Integer, default=0, nullable=False)
    passed_hidden_cases = Column(Integer, default=0, nullable=False)
    total_hidden_cases = Column(Integer, default=0, nullable=False)
    total_passed = Column(Integer, default=0, nullable=False)
    total_cases = Column(Integer, default=0, nullable=False)
    execution_time_ms = Column(Float, default=0.0, nullable=False)
    memory_used_kb = Column(Float, default=0.0, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    status = Column(String(40), default="ACCEPTED", nullable=False)
    ai_review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    attempt = relationship("AssessmentAttempt", backref="coding_submissions")
    question = relationship("QuestionBank")
    ase = relationship("User")

class CodingRunLog(Base):
    __tablename__ = "coding_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

class CodingPlagiarismFlag(Base):
    __tablename__ = "coding_plagiarism_flags"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    ase1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ase2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt1_id = Column(Integer, nullable=False)
    attempt2_id = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    status = Column(String(30), default="FLAGGED_FOR_REVIEW", nullable=False)
    flagged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)

    question = relationship("QuestionBank")
    ase1 = relationship("User", foreign_keys=[ase1_id])
    ase2 = relationship("User", foreign_keys=[ase2_id])
