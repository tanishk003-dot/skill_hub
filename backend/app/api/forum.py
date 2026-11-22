from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.phase12_schemas import (
    ForumPostCreate, ForumAnswerCreate, ForumReportCreate, ForumModerationAction
)
from app.services.forum_service import (
    create_forum_post, list_forum_posts, get_thread_detail,
    create_forum_answer, vote_answer, mark_accepted_answer,
    verify_answer, report_item, list_reports_for_moderators,
    moderate_content, generate_ai_draft_answer, find_similar_questions
)

router = APIRouter(prefix="/forum", tags=["Phase 12 Doubt Forum"])

@router.get("/posts")
def get_posts(
    cohort_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    unanswered_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists forum questions scoped to user's cohort with pagination and filtering.
    """
    return list_forum_posts(
        db=db,
        user=current_user,
        cohort_id=cohort_id,
        tag=tag,
        unanswered_only=unanswered_only,
        page=page,
        page_size=page_size
    )

@router.post("/posts")
def create_post(
    req: ForumPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Publishes a new question or holds for review if potential assessment leak detected.
    """
    return create_forum_post(
        db=db,
        user=current_user,
        cohort_id=req.cohort_id,
        title=req.title,
        body=req.body,
        tags=req.tags,
        tagged_assessment_id=req.tagged_assessment_id,
        is_anonymous=req.is_anonymous
    )

@router.get("/posts/similar")
def search_similar_questions(
    query: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Suggests similar resolved/published questions within user's cohort.
    """
    return find_similar_questions(db, query, current_user)

@router.get("/posts/{post_id}")
def get_post_thread(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches full thread with answers. Masks anonymous authors for peers;
    reveals author with audit log for mentors/admins.
    """
    return get_thread_detail(db, post_id, current_user)

@router.post("/posts/{post_id}/answers")
def post_answer(
    post_id: int,
    req: ForumAnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an answer to a question.
    """
    return create_forum_answer(
        db=db,
        user=current_user,
        post_id=post_id,
        body=req.body,
        is_anonymous=req.is_anonymous
    )

@router.post("/answers/{answer_id}/vote")
def toggle_upvote(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upvotes or removes upvote on an answer.
    """
    return vote_answer(db, answer_id, current_user)

@router.post("/posts/{post_id}/accept/{answer_id}")
def accept_answer(
    post_id: int,
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Question author accepts an answer.
    """
    return mark_accepted_answer(db, post_id, answer_id, current_user)

@router.post("/answers/{answer_id}/verify")
def verify_mentor_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mentor/Admin verifies an answer.
    """
    return verify_answer(db, answer_id, current_user)

@router.post("/posts/{post_id}/ai-draft")
def request_ai_draft(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates an AI draft answer with untrusted delimiters and MockProvider fallback.
    """
    return generate_ai_draft_answer(db, post_id, current_user)

@router.post("/report")
def report_post_or_answer(
    req: ForumReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reports content for moderation. One report per user per item.
    """
    return report_item(
        db=db,
        user=current_user,
        reason=req.reason,
        notes=req.notes,
        post_id=req.post_id,
        answer_id=req.answer_id
    )

@router.get("/moderation/reports")
def view_moderation_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mentors/Admins view reported content along with reporter abuse statistics.
    """
    return list_reports_for_moderators(db, current_user)

@router.post("/moderation/action")
def execute_moderation_action(
    req: ForumModerationAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mentors/Admins hide, delete, dismiss, or approve held questions.
    """
    return moderate_content(
        db=db,
        user=current_user,
        target_type=req.target_type,
        target_id=req.target_id,
        action=req.action,
        reason=req.reason
    )
