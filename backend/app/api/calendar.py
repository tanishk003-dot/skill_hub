from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.assessment_assignment import AssessmentAssignment
from app.models.training import TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.schemas.calendar import CalendarEvent, CalendarEventsResponse

router = APIRouter(prefix="/calendar", tags=["Calendar"])

def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    # Format as standard UTC ISO-8601 string: 2026-11-20T10:00:00Z
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

@router.get("/events", response_model=CalendarEventsResponse)
def get_calendar_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 3: All datetimes stored in UTC; calendar events must be returned in UTC ISO format.
    Aggregates:
    1. Live classes
    2. Assessments
    3. Training due dates
    """
    events: List[CalendarEvent] = []

    # 1. LIVE CLASSES
    class_query = db.query(LiveClass)
    if current_user.role == UserRole.ASE:
        invited_ids = db.query(LiveClassAttendee.live_class_id).filter(LiveClassAttendee.ase_id == current_user.id).all()
        class_ids = [c[0] for c in invited_ids]
        class_query = class_query.filter(LiveClass.id.in_(class_ids))
    elif current_user.role == UserRole.MENTOR:
        class_query = class_query.filter(LiveClass.created_by == current_user.id)

    classes = class_query.all()
    for lc in classes:
        end_time = lc.start_time + timedelta(minutes=lc.duration_minutes)
        events.append(CalendarEvent(
            id=f"class-{lc.id}",
            title=f"Live Class: {lc.title}",
            event_type="CLASS",
            start_time=to_utc_iso(lc.start_time) or "",
            end_time=to_utc_iso(end_time),
            status="SCHEDULED",
            meeting_link=lc.meeting_link,
            action_url=lc.meeting_link,
            details=f"Duration: {lc.duration_minutes} mins | Audience: {lc.audience_type}"
        ))

    # 2. ASSESSMENTS
    mentor_mentee_ids = []
    if current_user.role == UserRole.MENTOR:
        rows = db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()
        mentor_mentee_ids = [r[0] for r in rows]

    aa_query = db.query(AssessmentAssignment)
    if current_user.role == UserRole.ASE:
        aa_query = aa_query.filter(AssessmentAssignment.ase_id == current_user.id)
    elif current_user.role == UserRole.MENTOR:
        aa_query = aa_query.filter(AssessmentAssignment.ase_id.in_(mentor_mentee_ids))

    assessments = aa_query.all()
    for aa in assessments:
        title = aa.assessment.title if aa.assessment else "Assessment"
        events.append(CalendarEvent(
            id=f"assessment-{aa.id}",
            title=f"Assessment Deadline: {title}",
            event_type="ASSESSMENT",
            start_time=to_utc_iso(aa.end_date) or "",
            end_time=to_utc_iso(aa.end_date),
            status="DUE",
            meeting_link=None,
            action_url="/ase/my-assessments" if current_user.role == UserRole.ASE else "/mentor/assessments",
            details=f"Start: {to_utc_iso(aa.start_date)} | Due: {to_utc_iso(aa.end_date)}"
        ))

    # 3. TRAININGS
    ta_query = db.query(TrainingAssignment)
    if current_user.role == UserRole.ASE:
        ta_query = ta_query.filter(TrainingAssignment.ase_id == current_user.id)
    elif current_user.role == UserRole.MENTOR:
        ta_query = ta_query.filter(TrainingAssignment.ase_id.in_(mentor_mentee_ids))

    trainings = ta_query.all()
    for ta in trainings:
        training_title = ta.training.title if ta.training else "Training"
        events.append(CalendarEvent(
            id=f"training-{ta.id}",
            title=f"Training Due: {training_title}",
            event_type="TRAINING",
            start_time=to_utc_iso(ta.due_date) or "",
            end_time=to_utc_iso(ta.due_date),
            status=ta.status,
            meeting_link=None,
            action_url="/ase/learning" if current_user.role == UserRole.ASE else "/mentor/trainings",
            details=f"Skill: {ta.training.skill_category if ta.training else 'General'} | Status: {ta.status} ({ta.progress_percent:.0f}%)"
        ))

    return CalendarEventsResponse(events=events)
