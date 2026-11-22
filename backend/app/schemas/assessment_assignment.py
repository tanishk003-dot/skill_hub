from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.question import AssessmentType

class AssessmentAssignRequest(BaseModel):
    assessment_id: int
    target: str = "SELECTED"  # "ALL", "SELECTED", or "COHORT"
    ase_ids: Optional[List[int]] = None
    cohort_id: Optional[int] = None
    start_date: datetime
    end_date: datetime

class AssessmentAssignmentOut(BaseModel):
    id: int
    assessment_id: int
    assessment_title: str
    assessment_type: AssessmentType
    total_duration_minutes: int
    passing_percentage: float
    ase_id: int
    ase_name: str
    ase_email: str
    cohort_id: Optional[int] = None
    cohort_name: Optional[str] = None
    assigned_by_name: Optional[str] = None
    start_date: datetime
    end_date: datetime
    status: str  # UPCOMING, ACTIVE, COMPLETED, EXPIRED
    attempt_id: Optional[int] = None
    attempt_status: Optional[str] = None
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    violation_count: Optional[int] = 0

    class Config:
        from_attributes = True
