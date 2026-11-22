from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.cohort import Cohort, CohortMember
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.training import TrainingAssignment
from app.models.phase9_models import AseGamification
from app.models.phase12_models import (
    BuddyPairing, BuddyPairingStatus, BuddyMilestone, BuddyMilestoneStatus, BuddyRating
)

MAX_BUDDEES_CAP = 3
BUDDY_WEEKLY_XP_CAP = 100

def get_utc_now():
    return datetime.now(timezone.utc)

def get_coarse_name(full_name: str) -> str:
    """Returns 'FirstName L.' format"""
    if not full_name:
        return "Peer"
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

def calculate_coarse_status(db: Session, ase_id: int) -> str:
    """
    Computes a coarse status ('On track' or 'Needs support') without exposing exact scores.
    'Needs support' if any attempt failed or training progress is lagging.
    """
    attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == ase_id,
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED])
    ).all()
    
    if attempts:
        has_failed = any(not a.passed for a in attempts)
        if has_failed:
            return "Needs support"

    trainings = db.query(TrainingAssignment).filter(TrainingAssignment.ase_id == ase_id).all()
    if trainings:
        now = get_utc_now()
        overdue = any(t.status != "COMPLETED" and t.due_date and t.due_date.replace(tzinfo=timezone.utc) < now for t in trainings)
        if overdue:
            return "Needs support"

    return "On track"

WHAT_IS_SHARED_NOTICE = (
    "What is shared: Only your first name + last initial, cohort name, and high-level progress "
    "status ('On track' / 'Needs support') are visible to your buddy. Exact scores, risk scores, "
    "proctoring logs, 1-on-1 notes, and accommodations are strictly confidential."
)

def toggle_volunteer_status(db: Session, user: User, is_volunteer: bool) -> User:
    """
    Allows an ASE to toggle their buddy volunteer status.
    Must meet eligibility requirement: at least one passed assessment.
    """
    if user.role != UserRole.ASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Associate Engineers (ASE) can volunteer as a peer buddy."
        )

    if is_volunteer:
        # Check eligibility: at least one passed assessment
        passed_count = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == user.id,
            AssessmentAttempt.passed == True
        ).count()
        if passed_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ineligible to volunteer: You must have passed at least one assessment to be a peer buddy."
            )

    user.is_buddy_volunteer = is_volunteer
    db.commit()
    db.refresh(user)
    return user


def create_buddy_pairing(db: Session, buddy_id: int, buddee_id: int, current_user: User) -> BuddyPairing:
    """
    Pairs an experienced volunteer buddy with a new buddee.
    Enforces:
    - No self-pairing
    - One active buddy per buddee
    - Buddy must be a volunteer and meet eligibility
    - Cap of 3 buddees per buddy enforced atomically
    """
    if buddy_id == buddee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-pairing is prohibited. An ASE cannot be their own buddy."
        )

    buddy = db.query(User).filter(User.id == buddy_id, User.role == UserRole.ASE).first()
    buddee = db.query(User).filter(User.id == buddee_id, User.role == UserRole.ASE).first()
    if not buddy or not buddee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buddy or buddee user not found.")

    if not buddy.is_buddy_volunteer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{buddy.name} is not registered as an active buddy volunteer."
        )

    # 1 active buddy per buddee rule
    existing_active = db.query(BuddyPairing).filter(
        BuddyPairing.buddee_id == buddee_id,
        BuddyPairing.status == BuddyPairingStatus.ACTIVE
    ).first()
    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buddee already has an active peer buddy pairing."
        )

    # Check capacity with DB query
    active_buddee_count = db.query(BuddyPairing).filter(
        BuddyPairing.buddy_id == buddy_id,
        BuddyPairing.status == BuddyPairingStatus.ACTIVE
    ).count()

    if active_buddee_count >= MAX_BUDDEES_CAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Buddy capacity exceeded: {buddy.name} already has {MAX_BUDDEES_CAP} active buddees (maximum limit reached)."
        )

    pairing = BuddyPairing(
        buddy_id=buddy_id,
        buddee_id=buddee_id,
        status=BuddyPairingStatus.ACTIVE,
        paired_by=current_user.id,
        paired_at=get_utc_now()
    )
    db.add(pairing)
    db.commit()
    db.refresh(pairing)
    return pairing


def get_buddy_view_for_user(db: Session, user: User) -> Dict[str, Any]:
    """
    Returns the buddy pairing details for the logged-in user.
    If the user is a BUDDY: returns their active buddees with coarse details ONLY.
    If the user is a BUDDEE: returns their paired buddy with coarse details.
    """
    # 1. As Buddy: fetch my buddees
    as_buddy_pairings = db.query(BuddyPairing).filter(
        BuddyPairing.buddy_id == user.id,
        BuddyPairing.status.in_([BuddyPairingStatus.ACTIVE, BuddyPairingStatus.CHANGE_REQUESTED])
    ).all()

    buddees_list = []
    for p in as_buddy_pairings:
        b_user = p.buddee
        cohort_mem = db.query(CohortMember).filter(CohortMember.ase_id == b_user.id).first()
        cohort_name = cohort_mem.cohort.name if cohort_mem and cohort_mem.cohort else "Assigned Cohort"
        coarse_status = calculate_coarse_status(db, b_user.id)
        
        buddees_list.append({
            "pairing_id": p.id,
            "buddee_id": b_user.id,
            "coarse_name": get_coarse_name(b_user.name),
            "cohort_name": cohort_name,
            "coarse_status": coarse_status,
            "paired_at": p.paired_at.isoformat() if p.paired_at else None,
            "status": p.status.value
        })

    # 2. As Buddee: fetch my assigned buddy
    as_buddee_pairing = db.query(BuddyPairing).filter(
        BuddyPairing.buddee_id == user.id,
        BuddyPairing.status.in_([BuddyPairingStatus.ACTIVE, BuddyPairingStatus.CHANGE_REQUESTED])
    ).first()

    my_buddy_info = None
    if as_buddee_pairing:
        buddy_user = as_buddee_pairing.buddy
        cohort_mem = db.query(CohortMember).filter(CohortMember.ase_id == buddy_user.id).first()
        cohort_name = cohort_mem.cohort.name if cohort_mem and cohort_mem.cohort else "Senior Cohort"
        my_buddy_info = {
            "pairing_id": as_buddee_pairing.id,
            "buddy_id": buddy_user.id,
            "coarse_name": get_coarse_name(buddy_user.name),
            "cohort_name": cohort_name,
            "paired_at": as_buddee_pairing.paired_at.isoformat() if as_buddee_pairing.paired_at else None,
            "status": as_buddee_pairing.status.value
        }

    return {
        "is_volunteer": bool(user.is_buddy_volunteer),
        "what_is_shared_notice": WHAT_IS_SHARED_NOTICE,
        "max_buddees_cap": MAX_BUDDEES_CAP,
        "my_buddees": buddees_list,
        "my_buddy": my_buddy_info
    }


def request_pairing_change(db: Session, pairing_id: int, user: User, reason: str) -> BuddyPairing:
    """
    Allows either the buddy or buddee to request a change.
    """
    pairing = db.query(BuddyPairing).filter(BuddyPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found.")

    if user.id not in [pairing.buddy_id, pairing.buddee_id] and user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this pairing.")

    pairing.status = BuddyPairingStatus.CHANGE_REQUESTED
    pairing.change_reason = reason
    pairing.change_requested_by = user.id
    pairing.change_requested_at = get_utc_now()
    db.commit()
    db.refresh(pairing)
    return pairing


def rate_buddy(db: Session, pairing_id: int, user: User, rating_val: int, feedback: Optional[str]) -> BuddyRating:
    """
    Buddee rates their buddy.
    """
    pairing = db.query(BuddyPairing).filter(BuddyPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found.")

    if pairing.buddee_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned buddee can rate this buddy.")

    if rating_val < 1 or rating_val > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5.")

    rating = BuddyRating(
        pairing_id=pairing.id,
        rated_by_id=user.id,
        rating=rating_val,
        feedback=feedback
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


def create_milestone(db: Session, pairing_id: int, title: str, description: Optional[str], xp_amount: int = 25) -> BuddyMilestone:
    """
    Creates a peer learning milestone for a pairing.
    """
    pairing = db.query(BuddyPairing).filter(BuddyPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found.")

    milestone = BuddyMilestone(
        pairing_id=pairing.id,
        buddy_id=pairing.buddy_id,
        buddee_id=pairing.buddee_id,
        title=title,
        description=description,
        xp_amount=xp_amount,
        status=BuddyMilestoneStatus.PENDING
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def verify_and_award_milestone_xp(db: Session, milestone_id: int, current_user: User) -> Dict[str, Any]:
    """
    Confirms/verifies milestone and awards XP to the buddy, subject to the weekly cap of 100 XP.
    Can be confirmed by the buddee or verified by a mentor/admin.
    """
    milestone = db.query(BuddyMilestone).filter(BuddyMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")

    if milestone.xp_awarded:
        return {"message": "Milestone XP already awarded.", "xp_awarded": 0}

    # Verify authorization: must be the buddee, or mentor/admin
    is_buddee = (milestone.buddee_id == current_user.id)
    is_mentor_admin = (current_user.role in [UserRole.MENTOR, UserRole.ADMIN])
    if not is_buddee and not is_mentor_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the buddee or mentor can verify milestones.")

    # Calculate buddy's weekly XP earned so far
    one_week_ago = get_utc_now() - timedelta(days=7)
    recent_milestones = db.query(BuddyMilestone).filter(
        BuddyMilestone.buddy_id == milestone.buddy_id,
        BuddyMilestone.xp_awarded == True,
        BuddyMilestone.confirmed_at >= one_week_ago
    ).all()
    weekly_xp_used = sum(m.xp_amount for m in recent_milestones)

    remaining_cap = max(0, BUDDY_WEEKLY_XP_CAP - weekly_xp_used)
    award_amount = min(milestone.xp_amount, remaining_cap)

    milestone.status = BuddyMilestoneStatus.CONFIRMED_BY_BUDDEE if is_buddee else BuddyMilestoneStatus.VERIFIED_BY_MENTOR
    milestone.confirmed_at = get_utc_now()
    milestone.xp_awarded = True
    milestone.xp_amount = award_amount

    # Award to Gamification Profile if exists
    if award_amount > 0:
        gamification = db.query(AseGamification).filter(AseGamification.ase_id == milestone.buddy_id).first()
        if gamification:
            gamification.xp += award_amount
            # Award "Peer Guide" badge if not present
            badges = gamification.badges_json or []
            badge_names = [b.get("name") if isinstance(b, dict) else b for b in badges]
            if "Peer Guide" not in badge_names:
                badges.append({
                    "id": "peer-guide",
                    "name": "Peer Guide",
                    "icon": "handshake",
                    "desc": "Helped peers through 1-on-1 buddy mentorship"
                })
                gamification.badges_json = list(badges)

    db.commit()
    db.refresh(milestone)
    return {
        "message": f"Milestone verified successfully. {award_amount} XP awarded to buddy (Weekly Cap: {BUDDY_WEEKLY_XP_CAP} XP).",
        "xp_awarded": award_amount,
        "weekly_xp_used": weekly_xp_used + award_amount,
        "weekly_cap": BUDDY_WEEKLY_XP_CAP
    }
