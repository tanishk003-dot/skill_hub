from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel

class CohortBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date

class CohortCreate(CohortBase):
    pass

class CohortUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None

class CohortMemberOut(BaseModel):
    id: int
    ase_id: int
    ase_name: str
    ase_email: str
    mentor_id: Optional[int] = None
    mentor_name: Optional[str] = None
    added_at: datetime

    class Config:
        from_attributes = True

class CohortOut(CohortBase):
    id: int
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    created_at: datetime
    member_count: int = 0
    members: Optional[List[CohortMemberOut]] = None

    class Config:
        from_attributes = True

class CohortAddMembersRequest(BaseModel):
    ase_ids: List[int]

class ASESearchItem(BaseModel):
    id: int
    name: str
    email: str
    cohort_id: Optional[int] = None
    cohort_name: Optional[str] = None
    mentor_id: Optional[int] = None
    mentor_name: Optional[str] = None
    total_assessments: int = 0
    latest_score: Optional[float] = None
    latest_passed: Optional[bool] = None
    latest_status: Optional[str] = None
    violation_count: int = 0
    suggested_focus: Optional[str] = None

class ASESearchResponse(BaseModel):
    items: List[ASESearchItem]
    total: int
    page: int
    page_size: int
    total_pages: int
