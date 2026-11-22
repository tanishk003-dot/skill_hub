import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assessment import Assessment
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AssessmentResponse, AttemptStatus, ExamViolation
from app.schemas.question import QuestionExamOut, QuestionOption
from app.schemas.exam import (
    SectionExamOut, ExamStartResponse, ExamAutosaveRequest, ExamSubmitRequest,
    ExamResultResponse, ExamViolationCreate, ExamViolationOut, ExamViolationResponse
)
from app.api.deps import get_current_user
from app.core.scoring import calculate_assessment_results
from app.core.config import settings
from app.services.insights_service import mark_ai_insights_stale
from app.services.webcam_proctoring_service import (
    check_is_camera_exempt, check_is_camera_overridden, verify_and_consume_handshake
)
from app.services.accommodation_service import get_active_accommodation

router = APIRouter(prefix="/exam", tags=["Exam Engine"])

def _auto_submit_attempt(
    attempt: AssessmentAttempt,
    assessment: Assessment,
    db: Session,
    now_utc: datetime,
    status: AttemptStatus = AttemptStatus.AUTO_SUBMITTED,
    reason: Optional[str] = None
) -> None:
    resp_map = {r.question_id: r.selected_options for r in attempt.responses}
    res = calculate_assessment_results(
        passing_percentage=assessment.passing_percentage,
        sections=assessment.sections,
        responses_by_question=resp_map
    )
    attempt.status = status
    attempt.auto_submit_reason = reason
    attempt.submitted_at = now_utc
    attempt.total_score = res["total_score"]
    attempt.max_score = res["max_score"]
    attempt.percentage = res["percentage"]
    attempt.passed = res["passed"]
    attempt.section_scores = res["section_scores"]
    attempt.skill_percentages = res["skill_percentages"]
    attempt.strong_areas = res["strong_areas"]
    attempt.weak_areas = res["weak_areas"]
    
    # Update is_correct on response rows
    for resp in attempt.responses:
        # Match with detailed
        for d in res["detailed_responses"]:
            if d["question_id"] == resp.question_id:
                resp.is_correct = d["is_correct"]
                resp.marks_obtained = d["marks_obtained"]
                break
    db.commit()
    db.refresh(attempt)
    mark_ai_insights_stale(db, attempt.ase_id)


@router.post("/start/{assignment_id}", response_model=ExamStartResponse)
def start_or_resume_exam(
    assignment_id: int,
    handshake_token: Optional[str] = Query(None),
    x_camera_handshake: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment assignment not found")

    # Verify authorization
    if assignment.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to take this assessment")

    now_utc = datetime.now(timezone.utc)
    start_utc = assignment.start_date.replace(tzinfo=timezone.utc if assignment.start_date.tzinfo is None else None)
    end_utc = assignment.end_date.replace(tzinfo=timezone.utc if assignment.end_date.tzinfo is None else None)

    if now_utc < start_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This assessment has not started yet. Available from {assignment.start_date} UTC."
        )

    assessment = assignment.assessment
    attempt = assignment.attempt

    # Phase 10: Check Webcam Proctoring policy & Backend Enforcement
    webcam_mode = getattr(assessment, "webcam_mode", "OFF") or "OFF"
    is_exempt = check_is_camera_exempt(db, assignment.ase_id)
    is_overridden = check_is_camera_overridden(db, assignment.id, assignment.ase_id)

    if webcam_mode == "REQUIRED" and not is_exempt and not is_overridden:
        token = handshake_token or x_camera_handshake
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webcam consent and validated camera handshake required before starting exam"
            )
        valid = verify_and_consume_handshake(db, assignment.id, assignment.ase_id, token)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid, expired or already used camera handshake. Please recalibrate your camera."
            )

    # Phase 10: Reasonable Accommodations (Server-side Timer Extension)
    active_time_acc = get_active_accommodation(db, assignment.ase_id, "EXTRA_TIME_PCT")
    extra_time_pct = active_time_acc.extra_time_percent if active_time_acc else 0.0

    effective_duration_minutes = assessment.total_duration_minutes
    if attempt and attempt.extended_total_duration_minutes:
        effective_duration_minutes = attempt.extended_total_duration_minutes
    elif extra_time_pct > 0:
        effective_duration_minutes = int(round(assessment.total_duration_minutes * (1.0 + extra_time_pct / 100.0)))

    total_allowed_seconds = effective_duration_minutes * 60

    if attempt:
        if attempt.status in [AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION]:
            msg = "Assessment already completed. Only one attempt is permitted."
            if attempt.status == AttemptStatus.AUTO_SUBMITTED_VIOLATION:
                msg = "Assessment was terminated due to security violations. Only one attempt is permitted."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )

        # Attempt is IN_PROGRESS -> calculate remaining time from SERVER clock
        started_utc = attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)
        elapsed_seconds = (now_utc - started_utc).total_seconds()

        # Check if expired
        if elapsed_seconds >= total_allowed_seconds or now_utc > end_utc:
            _auto_submit_attempt(attempt, assessment, db, now_utc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time expired. This assessment has been automatically submitted."
            )

        remaining_seconds = max(0, int(total_allowed_seconds - elapsed_seconds))
    else:
        # Check if already past end date before starting
        if now_utc > end_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment window has already expired."
            )

        initial_camera_status = "INACTIVE"
        if is_exempt:
            initial_camera_status = "EXEMPT"
        elif is_overridden:
            initial_camera_status = "OVERRIDDEN"
        elif webcam_mode in ["REQUIRED", "ADVISORY"]:
            initial_camera_status = "ACTIVE"

        # Create new attempt with Phase 10 camera & accommodation state
        attempt = AssessmentAttempt(
            assessment_assignment_id=assignment.id,
            ase_id=assignment.ase_id,
            started_at=now_utc,
            status=AttemptStatus.IN_PROGRESS,
            camera_exempt=is_exempt,
            camera_override_active=is_overridden,
            camera_status=initial_camera_status,
            accommodation_applied=bool(is_exempt or extra_time_pct > 0),
            extended_total_duration_minutes=effective_duration_minutes if extra_time_pct > 0 else None
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        remaining_seconds = total_allowed_seconds

    # Build saved responses map
    saved_responses = {r.question_id: r.selected_options for r in attempt.responses}

    # Build sections & questions WITHOUT correct_answers
    sections_out = []
    for s in assessment.sections:
        # Collect questions
        section_questions = [sq.question for sq in s.section_questions]

        if assessment.randomize_questions:
            r = random.Random(attempt.id + s.id)
            section_questions = list(section_questions)
            r.shuffle(section_questions)

        questions_out = []
        for q in section_questions:
            opts = list(q.options)
            if assessment.randomize_options:
                r_opt = random.Random(attempt.id + q.id)
                opts = list(opts)
                r_opt.shuffle(opts)

            questions_out.append(QuestionExamOut(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                skill_category=q.skill_category,
                options=[QuestionOption(id=opt["id"], text=opt["text"]) for opt in opts],
                marks=q.marks
            ))

        sec_timer = s.timer_minutes
        if extra_time_pct > 0:
            sec_timer = int(round(s.timer_minutes * (1.0 + extra_time_pct / 100.0)))

        sections_out.append(SectionExamOut(
            id=s.id,
            title=s.title,
            timer_minutes=sec_timer,
            order_index=s.order_index,
            questions=questions_out
        ))

    accommodation_notice = None
    if is_exempt or extra_time_pct > 0 or getattr(attempt, "accommodation_applied", False):
        accommodation_notice = "Standard Accommodations Active: Approved session adjustments applied."

    return ExamStartResponse(
        attempt_id=attempt.id,
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        assessment_type=assessment.type.value,
        total_duration_minutes=effective_duration_minutes,
        started_at=attempt.started_at,
        server_time=now_utc,
        remaining_total_seconds=remaining_seconds,
        sections=sections_out,
        saved_responses=saved_responses,
        violation_count=attempt.violation_count or 0,
        proctoring_debug=settings.PROCTORING_DEBUG,
        webcam_mode=webcam_mode,
        webcam_policy=getattr(assessment, "webcam_policy", "WARNING_ONLY") or "WARNING_ONLY",
        camera_no_face_seconds=getattr(assessment, "camera_no_face_seconds", 10) or 10,
        camera_multiple_faces_seconds=getattr(assessment, "camera_multiple_faces_seconds", 5) or 5,
        camera_head_turn_seconds=getattr(assessment, "camera_head_turn_seconds", 12) or 12,
        camera_grace_period_seconds=getattr(assessment, "camera_grace_period_seconds", 30) or 30,
        camera_exempt=is_exempt or getattr(attempt, "camera_exempt", False),
        camera_override_active=is_overridden or getattr(attempt, "camera_override_active", False),
        camera_status=getattr(attempt, "camera_status", "ACTIVE") or "ACTIVE",
        accommodation_applied=bool(is_exempt or extra_time_pct > 0 or getattr(attempt, "accommodation_applied", False)),
        accommodation_notice=accommodation_notice
    )


@router.post("/autosave")
def autosave_answer(
    payload: ExamAutosaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == payload.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if attempt.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt is already closed")

    now_utc = datetime.now(timezone.utc)
    started_utc = attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)
    end_utc = attempt.assignment.end_date.replace(tzinfo=timezone.utc if attempt.assignment.end_date.tzinfo is None else None)
    total_allowed = attempt.assignment.assessment.total_duration_minutes * 60

    if (now_utc - started_utc).total_seconds() >= total_allowed or now_utc > end_utc:
        _auto_submit_attempt(attempt, attempt.assignment.assessment, db, now_utc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Time expired; attempt was auto-submitted")

    # Upsert response
    existing_resp = db.query(AssessmentResponse).filter(
        AssessmentResponse.attempt_id == attempt.id,
        AssessmentResponse.question_id == payload.question_id
    ).first()

    if existing_resp:
        existing_resp.selected_options = payload.selected_options
    else:
        new_resp = AssessmentResponse(
            attempt_id=attempt.id,
            question_id=payload.question_id,
            selected_options=payload.selected_options,
            is_correct=False,
            marks_obtained=0.0
        )
        db.add(new_resp)

    db.commit()
    return {"status": "saved", "question_id": payload.question_id}


@router.post("/violation/{attempt_id}", response_model=ExamViolationResponse)
def record_violation(
    attempt_id: int,
    payload: ExamViolationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if attempt.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Requirement 3: After auto-submit, any further answer/violation requests for that attempt must return 409
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attempt is already closed (status: {attempt.status.value})"
        )

    now_utc = datetime.now(timezone.utc)

    # Debounce check (Requirements 2 & 5)
    latest_violation = db.query(ExamViolation).filter(
        ExamViolation.attempt_id == attempt.id
    ).order_by(ExamViolation.occurred_at.desc(), ExamViolation.id.desc()).first()

    if latest_violation:
        lat_utc = latest_violation.occurred_at.replace(
            tzinfo=timezone.utc if latest_violation.occurred_at.tzinfo is None else None
        )
        time_diff = (now_utc - lat_utc).total_seconds()
        cooldown = 1.0 if latest_violation.occurred_at.microsecond > 0 else 0.5
        if time_diff < cooldown:
            # Debounced! Return existing count without incrementing or creating duplicate
            return ExamViolationResponse(
                violation_count=attempt.violation_count,
                auto_submitted=False,
                status=attempt.status.value,
                debounced=True,
                message="Violation debounced (cooldown period active)"
            )

    # Requirement 1: Backend is source of truth for violation_count.
    # Increment count; never reset or take from client.
    attempt.violation_count = (attempt.violation_count or 0) + 1

    # Record violation in exam_violations table
    violation_record = ExamViolation(
        attempt_id=attempt.id,
        type=payload.type,
        occurred_at=now_utc,
        details=payload.details
    )
    db.add(violation_record)

    # Requirement 3 & 4: At 2nd violation, backend auto-submits immediately
    if attempt.violation_count >= 2:
        auto_reason = "Exceeded maximum allowed security violations (2/2)"
        _auto_submit_attempt(
            attempt=attempt,
            assessment=attempt.assignment.assessment,
            db=db,
            now_utc=now_utc,
            status=AttemptStatus.AUTO_SUBMITTED_VIOLATION,
            reason=auto_reason
        )
        return ExamViolationResponse(
            violation_count=attempt.violation_count,
            auto_submitted=True,
            status=attempt.status.value,
            debounced=False,
            message="Maximum security violations exceeded. Assessment auto-submitted."
        )

    db.commit()
    db.refresh(attempt)
    mark_ai_insights_stale(db, attempt.ase_id)

    return ExamViolationResponse(
        violation_count=attempt.violation_count,
        auto_submitted=False,
        status=attempt.status.value,
        debounced=False,
        message="Security violation recorded (Warning 1 of 2)"
    )


@router.post("/submit", response_model=ExamResultResponse)
def submit_exam(
    payload: ExamSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == payload.attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if attempt.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    now_utc = datetime.now(timezone.utc)
    assessment = attempt.assignment.assessment

    if attempt.status == AttemptStatus.IN_PROGRESS:
        started_utc = attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)
        end_utc = attempt.assignment.end_date.replace(tzinfo=timezone.utc if attempt.assignment.end_date.tzinfo is None else None)
        total_allowed = assessment.total_duration_minutes * 60

        is_late = (now_utc - started_utc).total_seconds() > (total_allowed + 30) or now_utc > end_utc
        attempt.status = AttemptStatus.AUTO_SUBMITTED if is_late else AttemptStatus.SUBMITTED

        # Score all responses
        resp_map = {r.question_id: r.selected_options for r in attempt.responses}
        res = calculate_assessment_results(
            passing_percentage=assessment.passing_percentage,
            sections=assessment.sections,
            responses_by_question=resp_map
        )

        attempt.submitted_at = now_utc
        attempt.total_score = res["total_score"]
        attempt.max_score = res["max_score"]
        attempt.percentage = res["percentage"]
        attempt.passed = res["passed"]
        attempt.section_scores = res["section_scores"]
        attempt.skill_percentages = res["skill_percentages"]
        attempt.strong_areas = res["strong_areas"]
        attempt.weak_areas = res["weak_areas"]

        for resp in attempt.responses:
            for d in res["detailed_responses"]:
                if d["question_id"] == resp.question_id:
                    resp.is_correct = d["is_correct"]
                    resp.marks_obtained = d["marks_obtained"]
                    break

        db.commit()
        db.refresh(attempt)

        # Phase 11: Recompute item analysis cache when attempt is submitted and graded
        from app.services.item_analysis_service import compute_question_analytics
        for resp in attempt.responses:
            try:
                compute_question_analytics(db, resp.question_id, getattr(resp, "question_version", 1) or 1)
            except Exception as e:
                logger.error("Item analytics computation failed for question %s: %s", resp.question_id, e, exc_info=True)

    return get_exam_result(attempt.id, db, current_user)


@router.get("/result/{attempt_id}", response_model=ExamResultResponse)
def get_exam_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    # Authorization check: ASE owner, assigned Mentor, or Admin
    is_owner = attempt.ase_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN
    is_assigned_mentor = False

    if current_user.role == UserRole.MENTOR:
        # Check if current_user is the mentor of attempt.ase_id
        if attempt.ase and attempt.ase.mentor_assignment:
            is_assigned_mentor = (attempt.ase.mentor_assignment.mentor_id == current_user.id)

    if not (is_owner or is_admin or is_assigned_mentor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view these results")

    # Build question review WITH correct answers (only after submission)
    assessment = attempt.assignment.assessment
    resp_map = {r.question_id: r for r in attempt.responses}

    questions_review = []
    for s in assessment.sections:
        for sq in s.section_questions:
            q = sq.question
            r = resp_map.get(q.id)
            selected = r.selected_options if r else []
            is_corr = r.is_correct if r else False
            marks_ob = r.marks_obtained if r else 0.0

            questions_review.append({
                "question_id": q.id,
                "section_title": s.title,
                "question_text": q.question_text,
                "question_type": q.question_type.value,
                "skill_category": q.skill_category,
                "options": q.options,
                "selected_options": selected,
                "correct_answers": q.correct_answers,
                "is_correct": is_corr,
                "marks_obtained": marks_ob,
                "max_marks": q.marks
            })

    proctoring_violations = [
        ExamViolationOut(
            id=v.id,
            attempt_id=v.attempt_id,
            type=v.type,
            occurred_at=v.occurred_at,
            details=v.details
        )
        for v in (attempt.violations or [])
    ]

    return ExamResultResponse(
        attempt_id=attempt.id,
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        ase_id=attempt.ase.id,
        ase_name=attempt.ase.name,
        ase_email=attempt.ase.email,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        status=attempt.status.value,
        total_score=attempt.total_score,
        max_score=attempt.max_score,
        percentage=attempt.percentage,
        passing_percentage=assessment.passing_percentage,
        passed=attempt.passed,
        section_scores=attempt.section_scores or [],
        skill_percentages=attempt.skill_percentages or {},
        strong_areas=attempt.strong_areas or [],
        weak_areas=attempt.weak_areas or [],
        questions_review=questions_review,
        violation_count=attempt.violation_count or 0,
        auto_submit_reason=attempt.auto_submit_reason,
        proctoring_violations=proctoring_violations
    )
