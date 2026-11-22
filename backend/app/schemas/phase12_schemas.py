from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class VolunteerToggleRequest(BaseModel):
    is_volunteer: bool

class BuddyPairingCreate(BaseModel):
    buddy_id: int
    buddee_id: int

class BuddyChangeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)

class BuddyRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = Field(None, max_length=1000)

class BuddyMilestoneCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    xp_amount: int = Field(25, ge=5, le=100)

class ForumPostCreate(BaseModel):
    cohort_id: int
    title: str = Field(..., min_length=5, max_length=250)
    body: str = Field(..., min_length=10, max_length=10000)
    tags: Optional[str] = Field(None, max_length=255)
    tagged_assessment_id: Optional[int] = None
    is_anonymous: bool = False

class ForumAnswerCreate(BaseModel):
    body: str = Field(..., min_length=5, max_length=10000)
    is_anonymous: bool = False

class ForumReportCreate(BaseModel):
    reason: str
    notes: Optional[str] = Field(None, max_length=500)
    post_id: Optional[int] = None
    answer_id: Optional[int] = None

class ForumModerationAction(BaseModel):
    target_type: str  # "POST" or "ANSWER"
    target_id: int
    action: str       # "HIDE", "DELETE", "DISMISS", "APPROVE_HELD", "REJECT_HELD"
    reason: str = Field(..., min_length=5, max_length=500)
