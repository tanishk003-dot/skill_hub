from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class AttendeeOut(BaseModel):
    ase_id: int
    ase_name: str
    ase_email: str
    status: str # INVITED, ATTENDED, ABSENT
    marked_at: Optional[datetime] = None
    marked_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LiveClassBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    duration_minutes: int = 60
    audience_type: str = "COHORT" # ALL, COHORT, SELECTED
    cohort_id: Optional[int] = None
    meeting_link: str
    provider: str = "MANUAL"

class LiveClassCreate(LiveClassBase):
    ase_ids: Optional[List[int]] = None # For audience_type == 'SELECTED'

class LiveClassUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    audience_type: Optional[str] = None
    cohort_id: Optional[int] = None
    ase_ids: Optional[List[int]] = None
    meeting_link: Optional[str] = None
    provider: Optional[str] = None

class LiveClassOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    duration_minutes: int
    audience_type: str
    cohort_id: Optional[int] = None
    cohort_name: Optional[str] = None
    meeting_link: str
    provider: str
    created_by: Optional[int] = None
    creator_name: Optional[str] = None
    total_invited: int = 0
    total_attended: int = 0
    attendees: List[AttendeeOut] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AttendanceItem(BaseModel):
    ase_id: int
    status: str # ATTENDED, ABSENT, INVITED

class AttendanceBatchUpdate(BaseModel):
    attendances: List[AttendanceItem]
