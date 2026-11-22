from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_admin, require_mentor_or_admin
from app.models.user import User, UserRole
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.phase10_models import CameraHeartbeat, WebcamProctoringSnapshot
from app.models.assignment import MentorAseAssignment
from app.services.webcam_proctoring_service import (
    record_webcam_consent,
    generate_camera_handshake,
    record_camera_heartbeat,
    record_camera_event,
    grant_camera_override,
    log_webcam_audit,
    purge_expired_snapshots
)
from app.services.accommodation_service import (
    create_accommodation_request,
    get_accommodations,
    decide_accommodation,
    get_active_accommodation
)

router = APIRouter(prefix="/proctoring", tags=["Phase 10: Webcam Proctoring & Accommodations"])

# --- Request / Response Schemas ---

class ConsentRequest(BaseModel):
    consented: bool

class CameraHeartbeatRequest(BaseModel):
    attempt_id: int
    status: str # ACTIVE, BLOCKED, REVOKED, NO_FACE, MULTIPLE_FACES, HEAD_TURNED
    details: Optional[str] = None

class CameraEventRequest(BaseModel):
    attempt_id: int
    event_type: str # NO_FACE, MULTIPLE_FACES, HEAD_TURNED, CAMERA_BLOCKED, CAMERA_REVOKED
    duration_seconds: float = 0.0
    snapshot_base64: Optional[str] = None
    is_warning: bool = True

class CameraOverrideRequest(BaseModel):
    assignment_id: int
    attempt_id: Optional[int] = None
    reason: str = Field(..., min_length=5, description="Mandatory documented reason for override")

class AccommodationCreateRequest(BaseModel):
    ase_id: int
    accommodation_type: str # EXTRA_TIME_PCT, CAMERA_EXEMPTION, REST_BREAKS, ALTERNATIVE_PROCTORING, OTHER
    extra_time_percent: float = 0.0
    reason_category: str
    medical_notes: Optional[str] = None

class AccommodationDecisionRequest(BaseModel):
    approved: bool
    admin_notes: Optional[str] = None

# --- Webcam Proctoring Endpoints ---

@router.post("/consent/{assignment_id}")
def submit_webcam_consent(
    assignment_id: int,
    payload: ConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    consent = record_webcam_consent(
        db=db,
        assignment_id=assignment_id,
        ase_id=current_user.id,
        consented=payload.consented,
        ip_address=client_ip,
        user_agent=user_agent
    )
    return {
        "success": True,
        "consented": consent.consented,
        "consented_at": consent.consented_at.isoformat()
    }


@router.post("/handshake/{assignment_id}")
def create_camera_handshake(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.ase_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return generate_camera_handshake(db, assignment_id, current_user.id)


@router.post("/camera-heartbeat")
def receive_camera_heartbeat(
    payload: CameraHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return record_camera_heartbeat(
        db=db,
        attempt_id=payload.attempt_id,
        ase_id=current_user.id,
        status_code=payload.status,
        details=payload.details
    )


@router.post("/camera-event")
def report_camera_event(
    payload: CameraEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return record_camera_event(
        db=db,
        attempt_id=payload.attempt_id,
        ase_id=current_user.id,
        event_type=payload.event_type,
        duration_seconds=payload.duration_seconds,
        snapshot_base64=payload.snapshot_base64,
        is_warning=payload.is_warning
    )


@router.post("/camera-override")
def grant_override(
    payload: CameraOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    return grant_camera_override(
        db=db,
        assignment_id=payload.assignment_id,
        granted_by_user=current_user,
        reason=payload.reason,
        attempt_id=payload.attempt_id
    )


@router.get("/events/{attempt_id}")
def get_camera_proctoring_log(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mentor_or_admin)
):
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    # Mentor isolation: mentors can only see events for their own assigned mentees
    if current_user.role == UserRole.MENTOR:
        mapping = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == attempt.ase_id
        ).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mentors may only view proctoring logs for their assigned mentees"
            )

    # Log audit entry: human review tracking
    log_webcam_audit(db, current_user.id, attempt.id, "VIEW_EVENT_LOG")

    heartbeats = db.query(CameraHeartbeat).filter(
        CameraHeartbeat.attempt_id == attempt.id
    ).order_by(CameraHeartbeat.id.desc()).limit(50).all()

    snapshots = db.query(WebcamProctoringSnapshot).filter(
        WebcamProctoringSnapshot.attempt_id == attempt.id
    ).order_by(WebcamProctoringSnapshot.id.desc()).all()

    return {
        "attempt_id": attempt.id,
        "ase_name": attempt.ase.name if attempt.ase else None,
        "camera_override_active": getattr(attempt, "camera_override_active", False),
        "camera_exempt": getattr(attempt, "camera_exempt", False),
        "last_camera_status": getattr(attempt, "camera_status", "UNKNOWN"),
        "recent_heartbeats": [
            {
                "status": hb.status,
                "timestamp": hb.timestamp.isoformat(),
                "details": hb.details
            }
            for hb in heartbeats
        ],
        "snapshot_count": len(snapshots),
        "human_review_notice": "Camera events are recorded for human review. No automatic disqualification is applied from camera events alone."
    }


# --- Reasonable Accommodations Endpoints ---

@router.post("/accommodations/request")
def request_accommodation(
    payload: AccommodationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    req = create_accommodation_request(
        db=db,
        current_user=current_user,
        ase_id=payload.ase_id,
        accommodation_type=payload.accommodation_type,
        extra_time_percent=payload.extra_time_percent,
        reason_category=payload.reason_category,
        medical_notes=payload.medical_notes
    )
    return {
        "success": True,
        "request_id": req.id,
        "status": req.status,
        "created_at": req.created_at.isoformat()
    }


@router.get("/accommodations/list")
def list_accommodations(
    ase_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_accommodations(db, current_user, ase_id)


@router.put("/accommodations/{request_id}/decision")
def review_accommodation(
    request_id: int,
    payload: AccommodationDecisionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return decide_accommodation(
        db=db,
        admin_user=admin,
        request_id=request_id,
        approved=payload.approved,
        admin_notes=payload.admin_notes
    )


@router.get("/accommodations/active/{ase_id}")
def check_active_accommodation(
    ase_id: int,
    accommodation_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only requester, mentor, or admin
    if current_user.role == UserRole.ASE and current_user.id != ase_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    elif current_user.role == UserRole.MENTOR:
        mapping = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == ase_id
        ).first()
        if not mapping:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    acc = get_active_accommodation(db, ase_id, accommodation_type)
    if not acc:
        return {"has_active": False}

    return {
        "has_active": True,
        "accommodation_type": acc.accommodation_type,
        "extra_time_percent": acc.extra_time_percent,
        "neutral_notice": "Standard Accommodations Active: Approved session adjustments applied."
    }
