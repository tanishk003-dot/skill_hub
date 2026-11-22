from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.question import AssessmentType

def get_utc_now():
    return datetime.now(timezone.utc)

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    type = Column(Enum(AssessmentType, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    total_duration_minutes = Column(Integer, nullable=False)
    passing_percentage = Column(Float, nullable=False, default=60.0)
    randomize_questions = Column(Boolean, nullable=False, default=False)
    randomize_options = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Phase 10 Webcam Proctoring settings
    webcam_mode = Column(String(20), nullable=False, default="OFF")
    webcam_policy = Column(String(20), nullable=False, default="WARNING_ONLY")
    camera_no_face_seconds = Column(Integer, nullable=False, default=10)
    camera_multiple_faces_seconds = Column(Integer, nullable=False, default=5)
    camera_head_turn_seconds = Column(Integer, nullable=False, default=12)
    camera_grace_period_seconds = Column(Integer, nullable=False, default=30)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    sections = relationship("AssessmentSection", back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentSection.order_index")
    assignments = relationship("AssessmentAssignment", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentSection(Base):
    __tablename__ = "assessment_sections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    timer_minutes = Column(Integer, nullable=False, default=15)

    # Relationships
    assessment = relationship("Assessment", back_populates="sections")
    section_questions = relationship("AssessmentSectionQuestion", back_populates="section", cascade="all, delete-orphan", order_by="AssessmentSectionQuestion.order_index")


class AssessmentSectionQuestion(Base):
    __tablename__ = "assessment_section_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("assessment_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0)

    # Relationships
    section = relationship("AssessmentSection", back_populates="section_questions")
    question = relationship("QuestionBank")
