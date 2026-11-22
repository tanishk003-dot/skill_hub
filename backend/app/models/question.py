import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Enum, Float, Boolean
from app.core.database import Base

class AssessmentType(str, enum.Enum):
    PSYCHOMETRIC = "Psychometric"
    BEHAVIOURAL = "Behavioural"
    LOGICAL_THINKING = "Logical Thinking"
    REASONING = "Reasoning"
    PATTERN_RECOGNITION = "Pattern Recognition"
    APTITUDE = "Aptitude"

class QuestionDifficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTI_CHOICE = "MULTI_CHOICE"
    CODING = "CODING"

def get_utc_now():
    return datetime.now(timezone.utc)

class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(Enum(AssessmentType, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    difficulty = Column(Enum(QuestionDifficulty, values_callable=lambda obj: [e.value for e in obj]), nullable=False, index=True)
    skill_category = Column(String(100), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=QuestionType.SINGLE_CHOICE)
    options = Column(JSON, nullable=True)  # list of {"id": "opt1", "text": "..."}
    correct_answers = Column(JSON, nullable=True)  # list of ["opt1"]
    marks = Column(Integer, nullable=False, default=1)
    
    # Phase 7: Coding Assessment Attributes
    problem_statement = Column(Text, nullable=True)
    allowed_languages = Column(JSON, nullable=True)  # ["python", "java", "javascript", "sql"]
    starter_code = Column(JSON, nullable=True)       # {"python": "...", "javascript": "...", ...}
    sample_test_cases = Column(JSON, nullable=True)  # [{"id": 1, "input": "...", "expected_output": "..."}]
    hidden_test_cases = Column(JSON, nullable=True)  # [{"id": 2, "input": "...", "expected_output": "...", "marks": 2}]
    time_limit_sec = Column(Float, default=2.0, nullable=True)
    memory_limit_mb = Column(Integer, default=256, nullable=True)

    # Phase 11: Versioning and AI Question Quality Review
    version = Column(Integer, nullable=False, default=1)
    author_id = Column(Integer, nullable=True)  # user id of author (mentor/admin)
    is_ai_generated = Column(Boolean, nullable=False, default=False)
    ai_review_status = Column(String(30), nullable=False, default="APPROVED") # APPROVED, NEEDS_REVIEW, IN_REVIEW

    created_at = Column(DateTime, default=get_utc_now, nullable=False)
