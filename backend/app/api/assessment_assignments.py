from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.assessment import Assessment
from app.models.cohort import Cohort, CohortMember
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.schemas.assessment_assignment import AssessmentAssignRequest, AssessmentAssignmentOut
from app.api.deps import get_current_user, require_mentor_or_admin
from app.core.scoring import calculate_assessment_results

router = APIRouter(prefix="/assessment-assignments", tags=["Assessment Assignments"])

def _to_assignment_out(a: AssessmentAssignment, db: Session) -> AssessmentAssignmentOut:
    now_utc = datetime.now(timezone.utc)
    
    # Check attempt and auto-close if expired while IN_PROGRESS
    attempt = a.attempt
    if attempt and attempt.status == AttemptStatus.IN_PROGRESS:
        # Check if duration passed or end_date passed
        elapsed = (now_utc - attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)).total_seconds()
        total_allowed = a.assessment.total_duration_minutes * 60
        end_utc = a.end_date.replace(tzinfo=timezone.utc if a.end_date.tzinfo is None else None)
        
        if elapsed >= total_allowed or now_utc > end_utc:
            # Auto-submit!
            resp_map = {r.question_id: r.selected_options for r in attempt.responses}
            res = calculate_assessment_results(
                passing_percentage=a.assessment.passing_percentage,
                sections=a.assessment.sections,
                responses_by_question=resp_map
            )
            attempt.status = AttemptStatus.AUTO_SUBMITTED
            attempt.submitted_at = now_utc
            attempt.total_score = res["total_score"]
            attempt.max_score = res["max_score"]
            attempt.percentage = res["percentage"]
            attempt.passed = res["passed"]
            attempt.section_scores = res["section_scores"]
            attempt.skill_percentages = res["skill_percentages"]
            attempt.strong_areas = res["strong_areas"]
            attempt.weak_areas = res["weak_areas"]
            db.commit()
            db.refresh(attempt)

    # Determine status
    computed_status = "ACTIVE"
    start_utc = a.start_date.replace(tzinfo=timezone.utc if a.start_date.tzinfo is None else None)
    end_utc = a.end_date.replace(tzinfo=timezone.utc if a.end_date.tzinfo is None else None)

    if attempt and attempt.status in [AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION]:
        computed_status = "COMPLETED"
    elif now_utc < start_utc:
        computed_status = "UPCOMING"
    elif now_utc > end_utc:
        computed_status = "EXPIRED"
    else:
        computed_status = "ACTIVE"

    return AssessmentAssignmentOut(
        id=a.id,
        assessment_id=a.assessment_id,
        assessment_title=a.assessment.title,
        assessment_type=a.assessment.type,
        total_duration_minutes=a.assessment.total_duration_minutes,
        passing_percentage=a.assessment.passing_percentage,
        ase_id=a.ase_id,
        ase_name=a.ase.name if a.ase else "Unknown",
        ase_email=a.ase.email if a.ase else "",
        cohort_id=a.cohort_id,
        cohort_name=a.cohort.name if a.cohort else None,
        assigned_by_name=a.assigner.name if a.assigner else "System",
        start_date=a.start_date,
        end_date=a.end_date,
        status=computed_status,
        attempt_id=attempt.id if attempt else None,
        attempt_status=attempt.status.value if attempt else None,
        total_score=attempt.total_score if attempt and attempt.status != AttemptStatus.IN_PROGRESS else None,
        max_score=attempt.max_score if attempt and attempt.status != AttemptStatus.IN_PROGRESS else None,
        percentage=attempt.percentage if attempt and attempt.status != AttemptStatus.IN_PROGRESS else None,
        passed=attempt.passed if attempt and attempt.status != AttemptStatus.IN_PROGRESS else None,
        violation_count=attempt.violation_count if attempt else 0
    )

@router.post("", response_model=List[AssessmentAssignmentOut])
def assign_assessment(
    payload: AssessmentAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    assessment = db.query(Assessment).filter(Assessment.id == payload.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if payload.end_date <= payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    # Determine target ASEs
    target_upper = payload.target.upper()
    assigned_cohort_id = None

    if target_upper == "ALL":
        target_ases = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True).all()
    elif target_upper == "COHORT":
        if not payload.cohort_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cohort ID is required when target is COHORT")
        cohort = db.query(Cohort).filter(Cohort.id == payload.cohort_id).first()
        if not cohort:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
        assigned_cohort_id = cohort.id

        if user.role == UserRole.MENTOR:
            # Mentors see only their own mentees' data even in a shared cohort
            mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == user.id).all()]
            target_ases = db.query(User).join(CohortMember, CohortMember.ase_id == User.id).filter(
                CohortMember.cohort_id == cohort.id,
                User.id.in_(mentee_ids),
                User.is_active == True
            ).all()
        else:
            target_ases = db.query(User).join(CohortMember, CohortMember.ase_id == User.id).filter(
                CohortMember.cohort_id == cohort.id,
                User.is_active == True
            ).all()

        if not target_ases:
            detail_msg = "No eligible ASEs found in this cohort." if user.role == UserRole.ADMIN else "No assigned mentees found in this cohort."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail_msg)
    else:
        if not payload.ase_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one ASE must be selected"
            )
        target_ases = db.query(User).filter(
            User.id.in_(payload.ase_ids),
            User.role == UserRole.ASE,
            User.is_active == True
        ).all()

    created_assignments = []
    for ase in target_ases:
        # Check if already assigned
        existing = db.query(AssessmentAssignment).filter(
            AssessmentAssignment.assessment_id == assessment.id,
            AssessmentAssignment.ase_id == ase.id
        ).first()

        if existing:
            # Update dates and cohort
            existing.start_date = payload.start_date
            existing.end_date = payload.end_date
            existing.assigned_by = user.id
            if assigned_cohort_id:
                existing.cohort_id = assigned_cohort_id
            db.commit()
            db.refresh(existing)
            created_assignments.append(_to_assignment_out(existing, db))
        else:
            new_assign = AssessmentAssignment(
                assessment_id=assessment.id,
                ase_id=ase.id,
                assigned_by=user.id,
                cohort_id=assigned_cohort_id,
                start_date=payload.start_date,
                end_date=payload.end_date
            )
            db.add(new_assign)
            db.commit()
            db.refresh(new_assign)
            created_assignments.append(_to_assignment_out(new_assign, db))

    return created_assignments

@router.get("/my", response_model=List[AssessmentAssignmentOut])
def get_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ASE and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ASE accounts can view 'My Assessments'"
        )

    assignments = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.ase_id == current_user.id
    ).order_by(AssessmentAssignment.id.desc()).all()

    return [_to_assignment_out(a, db) for a in assignments]

@router.get("/ase/{ase_id}", response_model=List[AssessmentAssignmentOut])
def get_ase_assignments(
    ase_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    assignments = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.ase_id == ase_id
    ).order_by(AssessmentAssignment.id.desc()).all()

    return [_to_assignment_out(a, db) for a in assignments]

@router.get("/all", response_model=List[AssessmentAssignmentOut])
def list_all_assignments(
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    assignments = db.query(AssessmentAssignment).order_by(AssessmentAssignment.id.desc()).all()
    return [_to_assignment_out(a, db) for a in assignments]
