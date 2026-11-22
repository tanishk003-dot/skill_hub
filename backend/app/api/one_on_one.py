from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.phase11_models import (
    OneOnOneMeeting, OneOnOneGoal, OneOnOneActionItem, OneOnOneComment
)
from app.schemas.phase11_schemas import (
    OneOnOneMeetingCreate, OneOnOneMeetingUpdate, OneOnOneMeetingOut,
    OneOnOneGoalCreate, OneOnOneGoalOut,
    OneOnOneActionItemCreate, OneOnOneActionItemOut,
    OneOnOneCommentCreate, OneOnOneCommentOut,
    AISummaryRequest
)
from app.services.one_on_one_service import (
    create_meeting, get_meeting, update_meeting,
    create_goal, update_goal_status,
    create_action_item, toggle_action_item,
    add_comment, generate_ai_meeting_summary
)

router = APIRouter(prefix="/one-on-one", tags=["Mentor 1-on-1 Notes & Goals"])

# ================= MEETINGS =================
@router.post("/meetings", response_model=OneOnOneMeetingOut)
def api_create_meeting(
    payload: OneOnOneMeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor creates a 1-on-1 meeting record with shared and optional encrypted private notes."""
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors can create 1-on-1 meetings.")

    meeting = create_meeting(
        db=db,
        mentor_id=current_user.id,
        mentee_id=payload.mentee_id,
        title=payload.title,
        meeting_date=payload.meeting_date,
        shared_notes=payload.shared_notes,
        private_notes=payload.private_notes
    )
    return get_meeting(db, meeting.id, current_user)


@router.get("/meetings", response_model=List[OneOnOneMeetingOut])
def api_list_meetings(
    mentee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists meetings.
    - Mentor sees meetings for their mentees.
    - ASE sees only their own meetings (private notes omitted).
    - Admin sees meetings (private notes omitted).
    """
    query = db.query(OneOnOneMeeting)
    if current_user.role == UserRole.ASE:
        query = query.filter(OneOnOneMeeting.mentee_id == current_user.id)
    elif current_user.role == UserRole.MENTOR:
        query = query.filter(OneOnOneMeeting.mentor_id == current_user.id)
        if mentee_id:
            query = query.filter(OneOnOneMeeting.mentee_id == mentee_id)
    elif current_user.role == UserRole.ADMIN:
        if mentee_id:
            query = query.filter(OneOnOneMeeting.mentee_id == mentee_id)

    meetings = query.order_by(OneOnOneMeeting.meeting_date.desc()).all()
    return [get_meeting(db, m.id, current_user) for m in meetings]


@router.get("/meetings/{meeting_id}", response_model=OneOnOneMeetingOut)
def api_get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns meeting details. Private notes are returned ONLY to the assigned mentor."""
    return get_meeting(db, meeting_id, current_user)


@router.put("/meetings/{meeting_id}", response_model=OneOnOneMeetingOut)
def api_update_meeting(
    meeting_id: int,
    payload: OneOnOneMeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor updates meeting notes or status."""
    return update_meeting(
        db=db,
        meeting_id=meeting_id,
        requesting_user=current_user,
        title=payload.title,
        meeting_date=payload.meeting_date,
        status_val=payload.status,
        shared_notes=payload.shared_notes,
        private_notes=payload.private_notes
    )


@router.post("/meetings/{meeting_id}/summarize")
async def api_summarize_meeting(
    meeting_id: int,
    payload: AISummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an AI summary for shared notes or private notes."""
    summary = await generate_ai_meeting_summary(
        db=db,
        meeting_id=meeting_id,
        mentor_user=current_user,
        target=payload.target
    )
    return {"meeting_id": meeting_id, "target": payload.target, "summary": summary}


# ================= GOALS =================
@router.post("/goals", response_model=OneOnOneGoalOut)
def api_create_goal(
    payload: OneOnOneGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor creates a performance goal for a mentee."""
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors can create goals.")

    return create_goal(
        db=db,
        mentor_id=current_user.id,
        mentee_id=payload.mentee_id,
        title=payload.title,
        target_date=payload.target_date,
        description=payload.description,
        meeting_id=payload.meeting_id
    )


@router.get("/goals", response_model=List[OneOnOneGoalOut])
def api_list_goals(
    mentee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists goals for the user's scope."""
    query = db.query(OneOnOneGoal)
    if current_user.role == UserRole.ASE:
        query = query.filter(OneOnOneGoal.mentee_id == current_user.id)
    elif current_user.role == UserRole.MENTOR:
        query = query.filter(OneOnOneGoal.mentor_id == current_user.id)
        if mentee_id:
            query = query.filter(OneOnOneGoal.mentee_id == mentee_id)
    elif current_user.role == UserRole.ADMIN and mentee_id:
        query = query.filter(OneOnOneGoal.mentee_id == mentee_id)

    return query.order_by(OneOnOneGoal.target_date.asc()).all()


@router.patch("/goals/{goal_id}/status", response_model=OneOnOneGoalOut)
def api_update_goal_status(
    goal_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates goal status (NOT_STARTED, IN_PROGRESS, ACHIEVED, ABANDONED)."""
    return update_goal_status(db, goal_id, status, current_user)


# ================= ACTION ITEMS =================
@router.post("/actions", response_model=OneOnOneActionItemOut)
def api_create_action_item(
    payload: OneOnOneActionItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor creates an action item."""
    if current_user.role != UserRole.MENTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors can create action items.")

    return create_action_item(
        db=db,
        mentor_id=current_user.id,
        mentee_id=payload.mentee_id,
        task=payload.task,
        assigned_to=payload.assigned_to,
        meeting_id=payload.meeting_id,
        goal_id=payload.goal_id
    )


@router.get("/actions", response_model=List[OneOnOneActionItemOut])
def api_list_action_items(
    meeting_id: Optional[int] = None,
    goal_id: Optional[int] = None,
    mentee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists action items."""
    query = db.query(OneOnOneActionItem)
    if current_user.role == UserRole.ASE:
        query = query.filter(OneOnOneActionItem.mentee_id == current_user.id)
    elif current_user.role == UserRole.MENTOR:
        query = query.filter(OneOnOneActionItem.mentor_id == current_user.id)
        if mentee_id:
            query = query.filter(OneOnOneActionItem.mentee_id == mentee_id)

    if meeting_id:
        query = query.filter(OneOnOneActionItem.meeting_id == meeting_id)
    if goal_id:
        query = query.filter(OneOnOneActionItem.goal_id == goal_id)

    return query.order_by(OneOnOneActionItem.created_at.desc()).all()


@router.patch("/actions/{action_id}/toggle", response_model=OneOnOneActionItemOut)
def api_toggle_action_item(
    action_id: int,
    is_completed: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ASE or Mentor ticks/unticks action items."""
    return toggle_action_item(db, action_id, is_completed, current_user)


# ================= COMMENTS =================
@router.post("/comments", response_model=OneOnOneCommentOut)
def api_add_comment(
    payload: OneOnOneCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mentor or ASE adds a comment on meeting, goal, or action item."""
    return add_comment(
        db=db,
        user_id=current_user.id,
        comment_text=payload.comment_text,
        meeting_id=payload.meeting_id,
        goal_id=payload.goal_id,
        action_item_id=payload.action_item_id
    )
