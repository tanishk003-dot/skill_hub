from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.phase10_models import AccommodationRequest, AccommodationAuditLog
from app.models.assignment import MentorAseAssignment
from app.models.user import User, UserRole

def get_utc_now():
    return datetime.now(timezone.utc)

ALLOWED_ACCOMMODATION_TYPES = [
    "EXTRA_TIME_PCT",
    "CAMERA_EXEMPTION",
    "REST_BREAKS",
    "ALTERNATIVE_PROCTORING",
    "OTHER"
]

def create_accommodation_request(
    db: Session,
    current_user: User,
    ase_id: int,
    accommodation_type: str,
    extra_time_percent: float,
    reason_category: str,
    medical_notes: Optional[str] = None
) -> AccommodationRequest:
    if accommodation_type not in ALLOWED_ACCOMMODATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid accommodation type. Allowed: {', '.join(ALLOWED_ACCOMMODATION_TYPES)}"
        )

    # Authorization checks
    if current_user.role == UserRole.ASE:
        if current_user.id != ase_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ASEs may only submit accommodation requests for themselves"
            )
    elif current_user.role == UserRole.MENTOR:
        mapping = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == current_user.id,
            MentorAseAssignment.ase_id == ase_id
        ).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mentors may only submit accommodation requests for their assigned mentees"
            )

    now = get_utc_now()
    req = AccommodationRequest(
        ase_id=ase_id,
        requested_by=current_user.id,
        accommodation_type=accommodation_type,
        extra_time_percent=extra_time_percent if accommodation_type == "EXTRA_TIME_PCT" else 0.0,
        reason_category=reason_category.strip(),
        medical_notes=medical_notes.strip() if medical_notes else None,
        status="PENDING",
        created_at=now
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    audit = AccommodationAuditLog(
        request_id=req.id,
        action="REQUEST_CREATED",
        actor_id=current_user.id,
        note=f"Accommodation request created by {current_user.name} ({current_user.role.value})",
        timestamp=now
    )
    db.add(audit)
    db.commit()

    return req


def get_accommodations(
    db: Session,
    current_user: User,
    ase_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    query = db.query(AccommodationRequest)

    if current_user.role == UserRole.ADMIN:
        if ase_id:
            query = query.filter(AccommodationRequest.ase_id == ase_id)
        requests = query.order_by(AccommodationRequest.id.desc()).all()
        # Admin sees all fields including medical notes
        return [
            {
                "id": r.id,
                "ase_id": r.ase_id,
                "ase_name": r.ase.name if r.ase else None,
                "requested_by": r.requested_by,
                "requested_by_name": r.requester.name if r.requester else None,
                "accommodation_type": r.accommodation_type,
                "extra_time_percent": r.extra_time_percent,
                "reason_category": r.reason_category,
                "medical_notes": r.medical_notes,
                "status": r.status,
                "admin_notes": r.admin_notes,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "created_at": r.created_at.isoformat()
            }
            for r in requests
        ]

    elif current_user.role == UserRole.MENTOR:
        # Mentor isolation: only assigned mentees, medical notes strictly masked
        assigned_ase_ids = [
            m.ase_id for m in db.query(MentorAseAssignment).filter(
                MentorAseAssignment.mentor_id == current_user.id
            ).all()
        ]
        query = query.filter(AccommodationRequest.ase_id.in_(assigned_ase_ids))
        if ase_id:
            if ase_id not in assigned_ase_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this candidate")
            query = query.filter(AccommodationRequest.ase_id == ase_id)
        
        requests = query.order_by(AccommodationRequest.id.desc()).all()
        return [
            {
                "id": r.id,
                "ase_id": r.ase_id,
                "ase_name": r.ase.name if r.ase else None,
                "requested_by": r.requested_by,
                "requested_by_name": r.requester.name if r.requester else None,
                "accommodation_type": r.accommodation_type,
                "extra_time_percent": r.extra_time_percent,
                "reason_category": r.reason_category,
                "medical_notes": "[Confidential to Candidate & Admin]", # Masked for mentor
                "status": r.status,
                "admin_notes": r.admin_notes,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "created_at": r.created_at.isoformat()
            }
            for r in requests
        ]

    else:
        # ASE sees only own requests, with own medical notes
        query = query.filter(AccommodationRequest.ase_id == current_user.id)
        requests = query.order_by(AccommodationRequest.id.desc()).all()
        return [
            {
                "id": r.id,
                "ase_id": r.ase_id,
                "ase_name": r.ase.name if r.ase else None,
                "requested_by": r.requested_by,
                "requested_by_name": r.requester.name if r.requester else None,
                "accommodation_type": r.accommodation_type,
                "extra_time_percent": r.extra_time_percent,
                "reason_category": r.reason_category,
                "medical_notes": r.medical_notes,
                "status": r.status,
                "admin_notes": r.admin_notes,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "created_at": r.created_at.isoformat()
            }
            for r in requests
        ]


def decide_accommodation(
    db: Session,
    admin_user: User,
    request_id: int,
    approved: bool,
    admin_notes: Optional[str] = None
) -> Dict[str, Any]:
    if admin_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may approve or reject accommodation requests"
        )

    req = db.query(AccommodationRequest).filter(
        AccommodationRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accommodation request not found")

    now = get_utc_now()
    req.status = "APPROVED" if approved else "REJECTED"
    req.admin_notes = admin_notes.strip() if admin_notes else None
    req.reviewed_by = admin_user.id
    req.reviewed_at = now
    db.commit()

    audit = AccommodationAuditLog(
        request_id=req.id,
        action="REQUEST_APPROVED" if approved else "REQUEST_REJECTED",
        actor_id=admin_user.id,
        note=admin_notes,
        timestamp=now
    )
    db.add(audit)
    db.commit()

    return {
        "id": req.id,
        "status": req.status,
        "reviewed_at": req.reviewed_at.isoformat(),
        "admin_notes": req.admin_notes
    }


def get_active_accommodation(
    db: Session,
    ase_id: int,
    accommodation_type: Optional[str] = None
) -> Optional[AccommodationRequest]:
    query = db.query(AccommodationRequest).filter(
        AccommodationRequest.ase_id == ase_id,
        AccommodationRequest.status == "APPROVED"
    )
    if accommodation_type:
        query = query.filter(AccommodationRequest.accommodation_type == accommodation_type)
    return query.order_by(AccommodationRequest.id.desc()).first()
