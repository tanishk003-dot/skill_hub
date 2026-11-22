from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from app.models.question import AssessmentType, QuestionDifficulty, QuestionType

class QuestionOption(BaseModel):
    id: str
    text: str

class QuestionBankBase(BaseModel):
    type: AssessmentType
    difficulty: QuestionDifficulty
    skill_category: str
    question_text: str
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    options: Optional[List[QuestionOption]] = None
    marks: int = 1
    
    # Phase 7 coding fields
    problem_statement: Optional[str] = None
    allowed_languages: Optional[List[str]] = None
    starter_code: Optional[Dict[str, str]] = None
    sample_test_cases: Optional[List[Dict[str, Any]]] = None
    time_limit_sec: Optional[float] = 2.0
    memory_limit_mb: Optional[int] = 256

class QuestionBankCreate(QuestionBankBase):
    correct_answers: Optional[List[str]] = None
    hidden_test_cases: Optional[List[Dict[str, Any]]] = None

class QuestionBankOut(QuestionBankBase):
    id: int
    correct_answers: Optional[List[str]] = None
    hidden_test_cases: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Safe question schema for student taking exam: NO correct_answers, NO hidden_test_cases
class QuestionExamOut(BaseModel):
    id: int
    question_text: str
    question_type: QuestionType
    skill_category: str
    options: Optional[List[QuestionOption]] = None
    marks: int
    problem_statement: Optional[str] = None
    allowed_languages: Optional[List[str]] = None
    starter_code: Optional[Dict[str, str]] = None
    sample_test_cases: Optional[List[Dict[str, Any]]] = None
    time_limit_sec: Optional[float] = 2.0
    memory_limit_mb: Optional[int] = 256

    class Config:
        from_attributes = True
