from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt
from app.schemas.cohort import (
    CohortCreate, CohortUpdate, CohortOut, CohortMemberOut,
    CohortAddMembersRequest, ASESearchResponse, ASESearchItem
)
from app.api.deps import get_current_user, require_mentor_or_admin

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])

def _to_cohort_out(c: Cohort, current_user: User, db: Session, include_members: bool = False) -> CohortOut:
    # Filter members according to role:
    # Admin sees all members. Mentor sees only their assigned mentees in this cohort.
    if current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        members_query = db.query(CohortMember).filter(CohortMember.cohort_id == c.id, CohortMember.ase_id.in_(mentee_ids))
    else:
        members_query = db.query(CohortMember).filter(CohortMember.cohort_id == c.id)

    members_list = members_query.all()
    member_count = len(members_list)

    members_out = []
    if include_members:
        for m in members_list:
            mentor_assignment = db.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == m.ase_id).first()
            members_out.append(CohortMemberOut(
                id=m.id,
                ase_id=m.ase_id,
                ase_name=m.ase.name if m.ase else "Unknown",
                ase_email=m.ase.email if m.ase else "",
                mentor_id=mentor_assignment.mentor_id if mentor_assignment else None,
                mentor_name=mentor_assignment.mentor.name if mentor_assignment and mentor_assignment.mentor else None,
                added_at=m.added_at
            ))

    return CohortOut(
        id=c.id,
        name=c.name,
        description=c.description,
        start_date=c.start_date,
        created_by=c.created_by,
        creator_name=c.creator.name if c.creator else "System",
        created_at=c.created_at,
        member_count=member_count,
        members=members_out if include_members else None
    )


@router.get("", response_model=List[CohortOut])
def list_cohorts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    if current_user.role == UserRole.ADMIN:
        cohorts = db.query(Cohort).order_by(Cohort.created_at.desc()).all()
    else:
        # Mentor sees cohorts they created or cohorts containing at least one of their mentees
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        cohorts = db.query(Cohort).outerjoin(CohortMember, CohortMember.cohort_id == Cohort.id).filter(
            or_(
                Cohort.created_by == current_user.id,
                CohortMember.ase_id.in_(mentee_ids)
            )
        ).distinct().order_by(Cohort.created_at.desc()).all()

    return [_to_cohort_out(c, current_user, db, include_members=False) for c in cohorts]


@router.post("", response_model=CohortOut, status_code=status.HTTP_201_CREATED)
def create_cohort(
    payload: CohortCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    existing = db.query(Cohort).filter(Cohort.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A cohort with this name already exists")

    new_cohort = Cohort(
        name=payload.name.strip(),
        description=payload.description,
        start_date=payload.start_date,
        created_by=current_user.id
    )
    db.add(new_cohort)
    db.commit()
    db.refresh(new_cohort)
    return _to_cohort_out(new_cohort, current_user, db, include_members=True)


@router.get("/{cohort_id}", response_model=CohortOut)
def get_cohort(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        is_creator = (cohort.created_by == current_user.id)
        has_mentee = db.query(CohortMember).filter(CohortMember.cohort_id == cohort.id, CohortMember.ase_id.in_(mentee_ids)).first() is not None
        if not (is_creator or has_mentee):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this cohort")

    return _to_cohort_out(cohort, current_user, db, include_members=True)


@router.put("/{cohort_id}", response_model=CohortOut)
def update_cohort(
    cohort_id: int,
    payload: CohortUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if current_user.role == UserRole.MENTOR and cohort.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only edit cohorts they created")

    if payload.name:
        existing = db.query(Cohort).filter(Cohort.name == payload.name.strip(), Cohort.id != cohort.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A cohort with this name already exists")
        cohort.name = payload.name.strip()

    if payload.description is not None:
        cohort.description = payload.description
    if payload.start_date is not None:
        cohort.start_date = payload.start_date

    db.commit()
    db.refresh(cohort)
    return _to_cohort_out(cohort, current_user, db, include_members=True)


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cohort(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if current_user.role == UserRole.MENTOR and cohort.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only delete cohorts they created")

    # Requirement 1: Deleting a cohort must only remove cohort_members rows
    # (and set cohort_id NULL on assignments). Never delete ASE users, attempts or results.
    db.query(AssessmentAssignment).filter(AssessmentAssignment.cohort_id == cohort_id).update({"cohort_id": None})
    db.query(CohortMember).filter(CohortMember.cohort_id == cohort_id).delete(synchronize_session=False)
    db.delete(cohort)
    db.commit()
    return None


@router.post("/{cohort_id}/members", response_model=CohortOut)
def add_cohort_members(
    cohort_id: int,
    payload: CohortAddMembersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if current_user.role == UserRole.MENTOR:
        mentee_ids = set(r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all())
        unauthorized_ids = [aid for aid in payload.ase_ids if aid not in mentee_ids]
        if unauthorized_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only add their assigned mentees to cohorts")

    for ase_id in payload.ase_ids:
        ase = db.query(User).filter(User.id == ase_id, User.role == UserRole.ASE, User.is_active == True).first()
        if not ase:
            continue

        # Check if already member of ANY cohort (enforces: one cohort per ASE)
        existing_any = db.query(CohortMember).filter(CohortMember.ase_id == ase_id).first()
        if existing_any:
            if existing_any.cohort_id == cohort_id:
                continue
            # Reassign to this cohort
            existing_any.cohort_id = cohort_id
            existing_any.added_at = datetime.now(timezone.utc)
        else:
            new_mem = CohortMember(
                cohort_id=cohort_id,
                ase_id=ase_id,
                added_at=datetime.now(timezone.utc)
            )
            db.add(new_mem)

    db.commit()
    db.refresh(cohort)
    return _to_cohort_out(cohort, current_user, db, include_members=True)


@router.delete("/{cohort_id}/members/{ase_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cohort_member(
    cohort_id: int,
    ase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if current_user.role == UserRole.MENTOR:
        is_mentee = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == ase_id
        ).first() is not None
        if not is_mentee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only manage their assigned mentees")

    member = db.query(CohortMember).filter(CohortMember.cohort_id == cohort_id, CohortMember.ase_id == ase_id).first()
    if member:
        db.delete(member)
        db.commit()
    return None


@router.get("/search/ases", response_model=ASESearchResponse)
def search_filter_ases(
    query: Optional[str] = Query(None, description="Search by name or email"),
    cohort_id: Optional[int] = Query(None, description="Filter by cohort"),
    mentor_id: Optional[int] = Query(None, description="Filter by mentor"),
    score_min: Optional[float] = Query(None, description="Min score percentage"),
    score_max: Optional[float] = Query(None, description="Max score percentage"),
    pass_status: Optional[str] = Query(None, description="PASSED, FAILED, or ALL"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    """
    Search & Filter ASEs with pagination, mentor isolation, score filtering, and pass/fail status.
    """
    base_query = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True)

    # Mentor isolation: Mentors see only their assigned mentees
    if current_user.role == UserRole.MENTOR:
        mentee_ids = [r[0] for r in db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == current_user.id).all()]
        base_query = base_query.filter(User.id.in_(mentee_ids))

    if query and query.strip():
        q_clean = f"%{query.strip().lower()}%"
        base_query = base_query.filter(or_(
            func.lower(User.name).like(q_clean),
            func.lower(User.email).like(q_clean)
        ))

    if cohort_id:
        base_query = base_query.join(CohortMember, CohortMember.ase_id == User.id).filter(CohortMember.cohort_id == cohort_id)

    if mentor_id and current_user.role == UserRole.ADMIN:
        base_query = base_query.join(MentorAseAssignment, MentorAseAssignment.ase_id == User.id).filter(MentorAseAssignment.mentor_id == mentor_id)

    all_matched_ases = base_query.order_by(User.name.asc()).all()

    # Collect attempt statistics & filter by score range / pass status
    filtered_items: List[ASESearchItem] = []
    for ase in all_matched_ases:
        cohort_mem = ase.cohort_membership
        mentor_assign = ase.mentor_assignment

        # Latest attempt
        latest_attempt = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ase.id
        ).order_by(AssessmentAttempt.started_at.desc()).first()

        total_attempts = db.query(AssessmentAttempt).filter(AssessmentAttempt.ase_id == ase.id).count()

        latest_pct = latest_attempt.percentage if (latest_attempt and latest_attempt.status.value != "IN_PROGRESS") else None
        latest_pass = latest_attempt.passed if (latest_attempt and latest_attempt.status.value != "IN_PROGRESS") else None
        latest_stat = latest_attempt.status.value if latest_attempt else "NOT_ATTEMPTED"
        v_count = latest_attempt.violation_count if latest_attempt else 0

        # Apply score filter
        if score_min is not None and (latest_pct is None or latest_pct < score_min):
            continue
        if score_max is not None and (latest_pct is None or latest_pct > score_max):
            continue

        # Apply pass filter
        if pass_status:
            p_upper = pass_status.upper()
            if p_upper == "PASSED" and latest_pass is not True:
                continue
            elif p_upper == "FAILED" and (latest_pass is not False or latest_stat == "NOT_ATTEMPTED"):
                continue

        suggested_focus = None
        if latest_attempt and latest_attempt.weak_areas:
            suggested_focus = f"Focus on {latest_attempt.weak_areas[0]}"

        filtered_items.append(ASESearchItem(
            id=ase.id,
            name=ase.name,
            email=ase.email,
            cohort_id=cohort_mem.cohort_id if cohort_mem else None,
            cohort_name=cohort_mem.cohort.name if cohort_mem and cohort_mem.cohort else None,
            mentor_id=mentor_assign.mentor_id if mentor_assign else None,
            mentor_name=mentor_assign.mentor.name if mentor_assign and mentor_assign.mentor else None,
            total_assessments=total_attempts,
            latest_score=latest_pct,
            latest_passed=latest_pass,
            latest_status=latest_stat,
            violation_count=v_count,
            suggested_focus=suggested_focus
        ))

    total = len(filtered_items)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = filtered_items[start_idx:end_idx]
    total_pages = max(1, (total + page_size - 1) // page_size)

    return ASESearchResponse(
        items=paginated,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
