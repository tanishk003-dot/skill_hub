from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.question import QuestionExamOut

class SectionExamOut(BaseModel):
    id: int
    title: str
    timer_minutes: int
    order_index: int
    questions: List[QuestionExamOut]

class ExamStartResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    assessment_type: str
    total_duration_minutes: int
    started_at: datetime
    server_time: datetime
    remaining_total_seconds: int
    sections: List[SectionExamOut]
    saved_responses: Dict[int, List[str]]
    violation_count: int = 0
    proctoring_debug: bool = False
    webcam_mode: str = "OFF"
    webcam_policy: str = "WARNING_ONLY"
    camera_no_face_seconds: int = 10
    camera_multiple_faces_seconds: int = 5
    camera_head_turn_seconds: int = 12
    camera_grace_period_seconds: int = 30
    camera_exempt: bool = False
    camera_override_active: bool = False
    camera_status: str = "INACTIVE"
    accommodation_applied: bool = False
    accommodation_notice: Optional[str] = None

class ExamAutosaveRequest(BaseModel):
    attempt_id: int
    question_id: int
    selected_options: List[str]

class ExamSubmitRequest(BaseModel):
    attempt_id: int

class ExamViolationCreate(BaseModel):
    type: str
    details: Optional[Dict[str, Any]] = None

class ExamViolationOut(BaseModel):
    id: int
    attempt_id: int
    type: str
    occurred_at: datetime
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ExamViolationResponse(BaseModel):
    violation_count: int
    auto_submitted: bool
    status: str
    debounced: bool
    message: Optional[str] = None

class ExamResultResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    assessment_title: str
    ase_id: int
    ase_name: str
    ase_email: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    status: str
    total_score: float
    max_score: float
    percentage: float
    passing_percentage: float
    passed: bool
    section_scores: List[Dict[str, Any]]
    skill_percentages: Dict[str, float]
    strong_areas: List[str]
    weak_areas: List[str]
    questions_review: Optional[List[Dict[str, Any]]] = None
    violation_count: int = 0
    auto_submit_reason: Optional[str] = None
    proctoring_violations: List[ExamViolationOut] = []

    class Config:
        from_attributes = True
