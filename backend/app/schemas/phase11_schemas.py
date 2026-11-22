from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# ================= ITEM ANALYSIS SCHEMAS =================
class QuestionItemAnalyticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    question_version: int
    attempts_count: int
    correct_count: int
    difficulty_index: float
    discrimination_index: float
    is_indicative_discrimination: bool
    most_chosen_wrong_option: Optional[str] = None
    avg_time_seconds: float
    is_too_easy: bool
    is_too_hard: bool
    is_poor_discrimination: bool
    needs_review: bool
    review_reason: Optional[str] = None
    option_distribution: Optional[Dict[str, int]] = None
    formula_metadata: Optional[Dict[str, Any]] = None
    calculated_at: datetime
    updated_at: datetime

class QuestionReviewRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# ================= 1-ON-1 MEETING & GOAL SCHEMAS =================
class OneOnOneMeetingCreate(BaseModel):
    mentee_id: int
    title: str = Field(..., min_length=3, max_length=200)
    meeting_date: datetime
    shared_notes: Optional[str] = None
    private_notes: Optional[str] = None

class OneOnOneMeetingUpdate(BaseModel):
    title: Optional[str] = None
    meeting_date: Optional[datetime] = None
    status: Optional[str] = None # SCHEDULED, COMPLETED, CANCELLED
    shared_notes: Optional[str] = None
    private_notes: Optional[str] = None

class OneOnOneMeetingOut(BaseModel):
    id: int
    mentor_id: int
    mentee_id: int
    title: str
    meeting_date: str
    status: str
    shared_notes: Optional[str] = None
    private_notes: Optional[str] = None # Masked/None for non-mentors!
    ai_summary_shared: Optional[str] = None
    ai_summary_private: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class OneOnOneGoalCreate(BaseModel):
    mentee_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    target_date: datetime
    meeting_id: Optional[int] = None

class OneOnOneGoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mentor_id: int
    mentee_id: int
    meeting_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    target_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime

class OneOnOneActionItemCreate(BaseModel):
    mentee_id: int
    task: str = Field(..., min_length=2)
    assigned_to: str = "ASE" # "ASE" or "MENTOR"
    meeting_id: Optional[int] = None
    goal_id: Optional[int] = None

class OneOnOneActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mentor_id: int
    mentee_id: int
    meeting_id: Optional[int] = None
    goal_id: Optional[int] = None
    task: str
    assigned_to: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

class OneOnOneCommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1)
    meeting_id: Optional[int] = None
    goal_id: Optional[int] = None
    action_item_id: Optional[int] = None

class OneOnOneCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    comment_text: str
    created_at: datetime

class AISummaryRequest(BaseModel):
    target: str = "shared" # "shared" or "private"


# ================= REPORTING TOKEN SCHEMAS =================
class ReportingTokenCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    scopes: List[str] # ["assessments", "results", "cohorts", "trainings", "attendance", "readiness"]
    include_pii: bool = False
    expires_in_days: int = 90
    allowed_ips: Optional[List[str]] = None

class ReportingTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    scopes: List[str]
    include_pii: bool
    allowed_ips: Optional[List[str]] = None
    expires_at: datetime
    is_revoked: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime


# ================= STAFFING PROJECT SCHEMAS =================
class StaffingProjectSkillCreate(BaseModel):
    skill_name: str
    min_level_pct: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(1.0, gt=0.0)

class StaffingProjectCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    headcount: int = Field(1, ge=1)
    start_date: datetime
    ready_now_threshold_pct: float = Field(90.0, ge=0.0, le=100.0)
    skills: List[StaffingProjectSkillCreate]

class StaffingProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    headcount: Optional[int] = None
    start_date: Optional[datetime] = None
    ready_now_threshold_pct: Optional[float] = None
    status: Optional[str] = None # PLANNING, ACTIVE, COMPLETED, CANCELLED
