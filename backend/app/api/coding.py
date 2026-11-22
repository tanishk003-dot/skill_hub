import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, QuestionType
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.assessment import Assessment
from app.models.coding import CodingSubmission, CodingRunLog, CodingPlagiarismFlag
from app.schemas.coding import (
    CodingRunRequest,
    CodingRunResponse,
    CodingSubmitRequest,
    CodingSubmitResponse,
    CodingSubmissionOut,
    PlagiarismFlagOut,
    CodeReviewOut,
    TestCaseResultOut
)
from app.services.code_runner import get_code_runner, sanitize_error_output
from app.services.plagiarism_service import scan_and_record_plagiarism
from app.services.code_review_service import generate_ai_code_review

router = APIRouter(prefix="/coding", tags=["coding"])

def _validate_attempt_access(attempt_id: int, current_user: User, db: Session) -> AssessmentAttempt:
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")
    
    # Requirement 4: Run/submit only allowed on the caller's own attempt
    if attempt.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden: you do not own this attempt")
    
    # Requirement 4: Return 409 for closed/auto-submitted attempts
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment attempt is already closed")
    
    # Server-side deadline check
    if attempt.started_at and attempt.assignment and attempt.assignment.assessment:
        duration_minutes = attempt.assignment.assessment.total_duration_minutes
        started_utc = attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)
        deadline = started_utc + timedelta(minutes=duration_minutes)
        now_utc = datetime.now(timezone.utc)
        if now_utc > deadline:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment attempt deadline has expired")
            
    return attempt

@router.post("/run", response_model=CodingRunResponse)
def run_code(
    payload: CodingRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes code against sample test cases only.
    Enforces server-side deadline, ownership, and DB-backed rate limiting.
    """
    attempt = _validate_attempt_access(payload.attempt_id, current_user, db)

    # Check question
    question = db.query(QuestionBank).filter(QuestionBank.id == payload.question_id).first()
    if not question or question.question_type != QuestionType.CODING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coding question not found")

    # DB Rate limit check
    rate_limit = getattr(settings, "CODING_RUN_RATE_LIMIT_PER_ATTEMPT", 30)
    run_count = db.query(CodingRunLog).filter(
        CodingRunLog.attempt_id == payload.attempt_id,
        CodingRunLog.ase_id == current_user.id
    ).count()

    if run_count >= rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Run rate limit reached ({rate_limit} runs per attempt). Please submit your code."
        )

    # Record run in DB
    run_log = CodingRunLog(
        attempt_id=payload.attempt_id,
        question_id=payload.question_id,
        ase_id=current_user.id
    )
    db.add(run_log)
    db.commit()

    sample_cases = question.sample_test_cases or []
    hidden_cases = question.hidden_test_cases or []

    # If custom_input is provided, synthesize a sample test case
    if payload.custom_input is not None and len(payload.custom_input.strip()) > 0:
        sample_cases = [{"id": 0, "input": payload.custom_input, "expected_output": ""}]

    runner = get_code_runner()
    summary = runner.run_tests(
        language=payload.language,
        source_code=payload.source_code,
        sample_cases=sample_cases,
        hidden_cases=hidden_cases,
        is_sample_only=True
    )

    results_out = [
        TestCaseResultOut(
            test_case_id=r.id,
            status=r.status_description,
            is_sample=True,
            input=r.input,
            expected_output=r.expected_output,
            actual_output=r.actual_output,
            execution_time_ms=r.execution_time_ms,
            memory_kb=r.memory_used_kb,
            error_message=sanitize_error_output(r.compile_error, hidden_cases)
        )
        for r in summary.test_results
    ]

    runs_remaining = max(0, rate_limit - (run_count + 1))
    return CodingRunResponse(
        status=summary.overall_status,
        passed=(summary.overall_status == "ACCEPTED"),
        results=results_out,
        runs_remaining=runs_remaining
    )

@router.post("/submit", response_model=CodingSubmitResponse)
def submit_code(
    payload: CodingSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates code against both sample and hidden test cases, calculates score,
    records submission, scans for plagiarism, and returns safe results (hidden inputs/outputs scrubbed).
    """
    attempt = _validate_attempt_access(payload.attempt_id, current_user, db)

    question = db.query(QuestionBank).filter(QuestionBank.id == payload.question_id).first()
    if not question or question.question_type != QuestionType.CODING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coding question not found")

    sample_cases = question.sample_test_cases or []
    hidden_cases = question.hidden_test_cases or []

    runner = get_code_runner()
    summary = runner.run_tests(
        language=payload.language,
        source_code=payload.source_code,
        sample_cases=sample_cases,
        hidden_cases=hidden_cases,
        is_sample_only=False
    )

    total_cases = summary.total_cases
    total_passed = summary.total_passed
    calculated_score = 0.0
    if total_cases > 0:
        calculated_score = round((total_passed / float(total_cases)) * float(question.marks), 2)

    # Upsert CodingSubmission
    submission = db.query(CodingSubmission).filter(
        CodingSubmission.attempt_id == payload.attempt_id,
        CodingSubmission.question_id == payload.question_id
    ).first()

    if not submission:
        submission = CodingSubmission(
            attempt_id=payload.attempt_id,
            question_id=payload.question_id,
            ase_id=current_user.id,
            language=payload.language,
            source_code=payload.source_code,
            passed_sample_cases=summary.passed_sample,
            total_sample_cases=summary.total_sample,
            passed_hidden_cases=summary.passed_hidden,
            total_hidden_cases=summary.total_hidden,
            total_passed=total_passed,
            total_cases=total_cases,
            execution_time_ms=summary.max_time_ms,
            memory_used_kb=summary.max_memory_kb,
            score=calculated_score,
            status=summary.overall_status
        )
        db.add(submission)
    else:
        submission.language = payload.language
        submission.source_code = payload.source_code
        submission.passed_sample_cases = summary.passed_sample
        submission.total_sample_cases = summary.total_sample
        submission.passed_hidden_cases = summary.passed_hidden
        submission.total_hidden_cases = summary.total_hidden
        submission.total_passed = total_passed
        submission.total_cases = total_cases
        submission.execution_time_ms = summary.max_time_ms
        submission.memory_used_kb = summary.max_memory_kb
        submission.score = calculated_score
        submission.status = summary.overall_status

    db.commit()
    db.refresh(submission)

    # Scan for plagiarism
    try:
        scan_and_record_plagiarism(db, submission)
    except Exception as e:
        logger.error("Plagiarism scan failed for submission %s: %s", submission.id, e, exc_info=True)

    # Requirement 5: Hidden test cases MUST NOT leak input, expected_output, or actual_output
    safe_results: List[TestCaseResultOut] = []
    for r in summary.test_results:
        safe_results.append(
            TestCaseResultOut(
                test_case_id=r.id,
                status=r.status_description,
                is_sample=r.is_sample,
                input=r.input if r.is_sample else None,
                expected_output=r.expected_output if r.is_sample else None,
                actual_output=r.actual_output if r.is_sample else None,
                execution_time_ms=r.execution_time_ms,
                memory_kb=r.memory_used_kb,
                error_message=sanitize_error_output(r.compile_error, hidden_cases)
            )
        )

    return CodingSubmitResponse(
        submission_id=submission.id,
        status=submission.status,
        passed_sample_cases=summary.passed_sample,
        total_sample_cases=summary.total_sample,
        passed_hidden_cases=summary.passed_hidden,
        total_hidden_cases=summary.total_hidden,
        total_passed=total_passed,
        total_cases=total_cases,
        score=calculated_score,
        results=safe_results
    )

@router.post("/review/{submission_id}", response_model=CodeReviewOut)
def get_or_generate_review(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(CodingSubmission).filter(CodingSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coding submission not found")

    # Auth check
    if current_user.role == UserRole.ASE and submission.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        if submission.ase_id not in mentee_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: ASE is not your mentee")

    if submission.ai_review and len(submission.ai_review.strip()) > 0:
        return CodeReviewOut(submission_id=submission.id, review=submission.ai_review)

    question_title = submission.question.question_text[:50] if submission.question else "Problem"
    review_text = generate_ai_code_review(submission.language, submission.source_code, question_title)
    submission.ai_review = review_text
    db.commit()

    return CodeReviewOut(submission_id=submission.id, review=review_text)

@router.get("/attempt/{attempt_id}/submissions", response_model=List[CodingSubmissionOut])
def get_attempt_submissions(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        
    if current_user.role == UserRole.ASE and attempt.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        if attempt.ase_id not in mentee_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: ASE is not your mentee")
            
    return db.query(CodingSubmission).filter(CodingSubmission.attempt_id == attempt_id).all()

@router.get("/submission/{submission_id}", response_model=CodingSubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(CodingSubmission).filter(CodingSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if current_user.role == UserRole.ASE and submission.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        if submission.ase_id not in mentee_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return submission

@router.get("/plagiarism", response_model=List[PlagiarismFlagOut])
def get_plagiarism_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 6:
    - ASEs get 403.
    - Mentors see only pairs where BOTH ASEs are their own mentees.
    - Admin sees all.
    - Response returns similarity score only, not other ASE's code.
    """
    if current_user.role == UserRole.ASE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Plagiarism reports are restricted to Mentors and Administrators")

    query = db.query(CodingPlagiarismFlag)

    if current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        # Both ase1 and ase2 must be in mentee_ids
        query = query.filter(
            CodingPlagiarismFlag.ase1_id.in_(mentee_ids),
            CodingPlagiarismFlag.ase2_id.in_(mentee_ids)
        )

    flags = query.order_by(CodingPlagiarismFlag.flagged_at.desc()).all()

    results = []
    for f in flags:
        results.append(
            PlagiarismFlagOut(
                id=f.id,
                question_id=f.question_id,
                attempt1_id=f.attempt1_id,
                attempt2_id=f.attempt2_id,
                ase1_id=f.ase1_id,
                ase1_name=f.ase1.name if f.ase1 else f"ASE #{f.ase1_id}",
                ase2_id=f.ase2_id,
                ase2_name=f.ase2.name if f.ase2 else f"ASE #{f.ase2_id}",
                similarity_score=f.similarity_score,
                status=f.status,
                flagged_at=f.flagged_at
            )
        )
    return results
