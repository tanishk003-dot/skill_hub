from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.phase12_schemas import (
    VolunteerToggleRequest, BuddyPairingCreate, BuddyChangeRequest,
    BuddyRatingRequest, BuddyMilestoneCreate
)
from app.services.buddy_service import (
    toggle_volunteer_status, create_buddy_pairing, get_buddy_view_for_user,
    request_pairing_change, rate_buddy, create_milestone, verify_and_award_milestone_xp
)

router = APIRouter(prefix="/buddy", tags=["Phase 12 Buddy System"])

@router.get("/my-pairings")
def get_my_buddy_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns coarse buddy/buddee pairing view for logged-in user with strict privacy isolation.
    """
    return get_buddy_view_for_user(db, current_user)

@router.post("/volunteer")
def toggle_volunteer(
    req: VolunteerToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ASE toggles their buddy volunteer registration. Requires at least 1 passed assessment.
    """
    updated_user = toggle_volunteer_status(db, current_user, req.is_volunteer)
    return {
        "is_buddy_volunteer": updated_user.is_buddy_volunteer,
        "message": "Volunteer status updated successfully."
    }

@router.post("/pairings")
def pair_buddy(
    req: BuddyPairingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pairs an experienced volunteer buddy with a new buddee. Enforces cap of 3.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=403, detail="Only mentors and admins can create peer buddy pairings.")
    pairing = create_buddy_pairing(db, req.buddy_id, req.buddee_id, current_user)
    return {
        "pairing_id": pairing.id,
        "buddy_id": pairing.buddy_id,
        "buddee_id": pairing.buddee_id,
        "status": pairing.status.value,
        "message": "Peer pairing established successfully."
    }

@router.post("/pairings/{pairing_id}/change-request")
def change_buddy(
    pairing_id: int,
    req: BuddyChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requests a change of buddy with documented reason.
    """
    pairing = request_pairing_change(db, pairing_id, current_user, req.reason)
    return {
        "pairing_id": pairing.id,
        "status": pairing.status.value,
        "message": "Change request logged. Mentor will review for re-assignment."
    }

@router.post("/pairings/{pairing_id}/rate")
def submit_rating(
    pairing_id: int,
    req: BuddyRatingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buddee rates their buddy (1-5 stars).
    """
    rating = rate_buddy(db, pairing_id, current_user, req.rating, req.feedback)
    return {"rating_id": rating.id, "rating": rating.rating, "message": "Rating submitted. Thank you!"}

@router.post("/pairings/{pairing_id}/milestones")
def add_milestone(
    pairing_id: int,
    req: BuddyMilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a learning check-in milestone for a pairing.
    """
    milestone = create_milestone(db, pairing_id, req.title, req.description, req.xp_amount)
    return {"milestone_id": milestone.id, "title": milestone.title, "xp_amount": milestone.xp_amount}

@router.post("/milestones/{milestone_id}/verify")
def verify_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buddee confirms or mentor verifies milestone; awards XP to buddy subject to weekly cap.
    """
    return verify_and_award_milestone_xp(db, milestone_id, current_user)
