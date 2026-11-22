from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ReadinessWeightsUpdate(BaseModel):
    assessment_weight: float = Field(..., ge=0.0, le=1.0)
    coding_weight: float = Field(..., ge=0.0, le=1.0)
    training_weight: float = Field(..., ge=0.0, le=1.0)
    attendance_weight: float = Field(..., ge=0.0, le=1.0)
    consistency_weight: float = Field(..., ge=0.0, le=1.0)

class ReadinessBreakdownItem(BaseModel):
    score: float
    weight: float
    weighted_value: float
    count: Optional[int] = None
    streak_days: Optional[int] = None

class ReadinessResponse(BaseModel):
    ase_id: int
    overall_score: float
    breakdown: Dict[str, ReadinessBreakdownItem]
    skill_dna: Dict[str, float]
    formula: str
    disclaimer: str
    weights: Dict[str, float]

class LeaderboardOptInUpdate(BaseModel):
    opt_in: bool
    show_full_name: Optional[bool] = None

class LeaderboardItem(BaseModel):
    rank: int
    display_name: str
    level: int
    xp: int
    streak_days: int
    badges_count: int
    is_me: bool

class RoadmapItem(BaseModel):
    id: str
    title: str
    skill: str
    training_id: Optional[int]
    training_title: Optional[str]
    action: str
    completed: bool
    due_date: str

class RoadmapResponse(BaseModel):
    id: int
    ase_id: int
    week_number: int
    generated_from_weak_skills: List[str]
    roadmap_items: List[RoadmapItem]
    version: int
    created_at: datetime

class RoadmapItemToggle(BaseModel):
    completed: bool

class RiskSignalResponse(BaseModel):
    ase_id: int
    name: str
    email: str
    risk_score: float
    risk_level: str
    factors: List[str]
    ai_explanation: str
    last_nudged_at: Optional[datetime]

class NudgeResponse(BaseModel):
    message: str
    ase_id: int
    sent_at: datetime

class ReassessmentScheduleCreate(BaseModel):
    original_assessment_id: int
    phase_label: str = "30_DAY"
    cohort_id: Optional[int] = None
    ase_id: Optional[int] = None
    scheduled_days_from_now: int = 14

class ReassessmentScheduleResponse(BaseModel):
    id: int
    cohort_id: Optional[int]
    ase_id: Optional[int]
    phase_label: str
    original_assessment_id: int
    reassessment_id: int
    scheduled_date: datetime
    status: str

    class Config:
        from_attributes = True

class ReassessmentGrowthResponse(BaseModel):
    ase_id: int
    has_data: bool
    message: Optional[str] = None
    baseline_percentage: Optional[float] = None
    latest_percentage: Optional[float] = None
    overall_growth_delta_pct: Optional[float] = None
    phases: List[Dict[str, Any]] = []

class CertificateIssueRequest(BaseModel):
    ase_id: int
    title: str
    entity_type: str = "TRAINING" # TRAINING, ASSESSMENT
    entity_id: int

class CertificatePublicVerifyResponse(BaseModel):
    status: str
    recipient_name: str
    course_title: str
    issue_date: str
    certificate_id: str

class MockInterviewStartRequest(BaseModel):
    target_role: Optional[str] = "Associate Software Engineer"
    skill_focus: Optional[str] = "Backend Distributed Systems"

class MockInterviewResponseRequest(BaseModel):
    session_id: int
    candidate_answer: str

class MilestoneToggleRequest(BaseModel):
    is_completed: bool
