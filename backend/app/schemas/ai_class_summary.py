from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TranscriptNotesCreate(BaseModel):
    live_class_id: Optional[int] = None
    training_id: Optional[int] = None
    notes: Optional[str] = None
    topics_covered: Optional[str] = None
    privacy_consent_acknowledged: bool = Field(..., description="Must explicitly acknowledge privacy consent")

class ClassTranscriptResponse(BaseModel):
    id: int
    live_class_id: Optional[int]
    training_id: Optional[int]
    uploaded_by: Optional[int]
    topics_covered: Optional[str]
    file_name: Optional[str]
    file_type: Optional[str]
    token_count: int
    used_token_count: int
    truncated_ratio: float
    raw_text_present: bool
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class ClassSummaryUpdate(BaseModel):
    key_topics: Optional[List[str]] = None
    key_concepts: Optional[List[Dict[str, str]]] = None
    practical_examples: Optional[List[str]] = None
    ase_recap: Optional[str] = None
    suggested_homework: Optional[List[str]] = None

class ClassSummaryResponse(BaseModel):
    id: int
    transcript_id: Optional[int]
    live_class_id: Optional[int]
    training_id: Optional[int]
    key_topics: List[str]
    key_concepts: List[Dict[str, str]]
    practical_examples: List[str]
    ase_recap: str
    suggested_homework: List[str]
    is_published: bool
    published_at: Optional[datetime]
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlanRecommendationRequest(BaseModel):
    summary_id: int

class PlanRecommendationResponse(BaseModel):
    recommended_total_questions: int
    difficulty_split: Dict[str, int]
    topic_split: Dict[str, int]

class AssessmentGenerateRequest(BaseModel):
    live_class_id: Optional[int] = None
    training_id: Optional[int] = None
    title: str = "Class Evaluation Assessment"
    generation_mode: str = "AUTO" # AUTO, BANK, MIXED
    recommended_total_questions: int = Field(20, ge=5, le=50)
    difficulty_split: Dict[str, int] = {"EASY": 35, "MEDIUM": 45, "HARD": 20}
    topic_split: Optional[Dict[str, int]] = None
    skill_category: Optional[str] = "Software Engineering"

class AIGeneratedQuestionResponse(BaseModel):
    id: int
    ai_assessment_id: int
    question_bank_id: Optional[int]
    question_type: str
    skill_category: str
    difficulty: str
    question_text: str
    options: List[str]
    correct_answers: List[str]
    explanation: str
    source: str
    review_status: str
    mentor_verify_required: bool
    quality_flags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AIGeneratedQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    skill_category: Optional[str] = None
    review_status: Optional[str] = None
    mentor_verify_required: Optional[bool] = None

class AIGeneratedAssessmentResponse(BaseModel):
    id: int
    live_class_id: Optional[int]
    training_id: Optional[int]
    title: str
    generation_mode: str
    status: str
    recommended_total_questions: int
    difficulty_split: Dict[str, int]
    topic_split: Dict[str, int]
    is_immutable: bool
    version: int
    assessment_id: Optional[int]
    questions: List[AIGeneratedQuestionResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionBankExportRequest(BaseModel):
    question_ids: List[int]

class ClassEffectivenessResponse(BaseModel):
    has_enough_data: bool
    total_attempts: int
    topic_scores: Dict[str, float]
    missed_concepts: List[Dict[str, Any]]
    suggested_revision_topics: List[str]
    follow_up_proposal: Dict[str, Any]
    message: Optional[str] = None
