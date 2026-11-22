from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.question import AssessmentType
from app.schemas.question import QuestionBankOut

class SectionCreate(BaseModel):
    title: str
    timer_minutes: int
    question_ids: List[int]

class AssessmentCreate(BaseModel):
    title: str
    type: AssessmentType
    total_duration_minutes: int
    passing_percentage: float = 60.0
    randomize_questions: bool = False
    randomize_options: bool = False
    webcam_mode: str = "REQUIRED"
    webcam_policy: str = "WARNING_ONLY"
    camera_no_face_seconds: int = 10
    camera_multiple_faces_seconds: int = 5
    camera_head_turn_seconds: int = 12
    camera_grace_period_seconds: int = 30
    sections: List[SectionCreate]

class AssessmentWebcamUpdate(BaseModel):
    webcam_mode: Optional[str] = None
    webcam_policy: Optional[str] = None
    camera_no_face_seconds: Optional[int] = None
    camera_multiple_faces_seconds: Optional[int] = None
    camera_head_turn_seconds: Optional[int] = None
    camera_grace_period_seconds: Optional[int] = None

class SectionOut(BaseModel):
    id: int
    title: str
    order_index: int
    timer_minutes: int
    question_count: int
    questions: Optional[List[QuestionBankOut]] = None

    class Config:
        from_attributes = True

class AssessmentOut(BaseModel):
    id: int
    title: str
    type: AssessmentType
    total_duration_minutes: int
    passing_percentage: float
    randomize_questions: bool
    randomize_options: bool
    created_at: datetime
    webcam_mode: str = "OFF"
    webcam_policy: str = "WARNING_ONLY"
    camera_no_face_seconds: int = 10
    camera_multiple_faces_seconds: int = 5
    camera_head_turn_seconds: int = 12
    camera_grace_period_seconds: int = 30
    total_sections: int = 0
    total_questions: int = 0
    total_marks: int = 0
    sections: Optional[List[SectionOut]] = None

    class Config:
        from_attributes = True
