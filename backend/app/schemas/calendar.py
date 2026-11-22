from typing import List, Optional
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    id: str # e.g. "class-1", "assessment-2", "training-3"
    title: str
    event_type: str # CLASS, ASSESSMENT, TRAINING
    start_time: str # UTC ISO 8601 string, e.g. "2026-11-20T10:00:00Z"
    end_time: Optional[str] = None
    status: Optional[str] = None
    meeting_link: Optional[str] = None
    action_url: Optional[str] = None
    details: Optional[str] = None

class CalendarEventsResponse(BaseModel):
    events: List[CalendarEvent]
