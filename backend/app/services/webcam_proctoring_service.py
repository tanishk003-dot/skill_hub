import os
import uuid
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

from app.models.phase10_models import (
    WebcamConsent, CameraHandshake, CameraHeartbeat, CameraOverrideLog,
    WebcamProctoringSnapshot, WebcamAuditLog, AccommodationRequest
)
from app.models.assessment import Assessment
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus, ExamViolation
from app.models.assignment import MentorAseAssignment
from app.models.user import User, UserRole
from app.core.config import settings
from app.core.database import SessionLocal

def get_utc_now():
    return datetime.now(timezone.utc)

# Encryption key for snapshots (generates stable fallback if not set)
ENCRYPTION_KEY = os.getenv("WEBCAM_ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

SNAPSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "proctoring_snapshots"))
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

def record_webcam_consent(
    db: Session,
    assignment_id: int,
    ase_id: int,
    consented: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> WebcamConsent:
    if not consented:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webcam proctoring consent must be accepted to proceed with required proctoring"
        )
    
    consent = db.query(WebcamConsent).filter(
        WebcamConsent.assignment_id == assignment_id,
        WebcamConsent.ase_id == ase_id
    ).first()

    if not consent:
        consent = WebcamConsent(
            assignment_id=assignment_id,
            ase_id=ase_id,
            consented=True,
            consented_at=get_utc_now(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(consent)
    else:
        consent.consented = True
        consent.consented_at = get_utc_now()
        consent.ip_address = ip_address
        consent.user_agent = user_agent

    db.commit()
    db.refresh(consent)
    return consent


def check_is_camera_exempt(db: Session, ase_id: int) -> bool:
    """Checks if candidate has an approved CAMERA_EXEMPTION accommodation."""
    acc = db.query(AccommodationRequest).filter(
        AccommodationRequest.ase_id == ase_id,
        AccommodationRequest.accommodation_type == "CAMERA_EXEMPTION",
        AccommodationRequest.status == "APPROVED"
    ).first()
    return acc is not None


def check_is_camera_overridden(db: Session, assignment_id: int, ase_id: int) -> bool:
    """Checks if a mentor/admin granted an active camera override for this assignment."""
    ovr = db.query(CameraOverrideLog).filter(
        CameraOverrideLog.assignment_id == assignment_id,
        CameraOverrideLog.ase_id == ase_id
    ).first()
    return ovr is not None


def generate_camera_handshake(db: Session, assignment_id: int, ase_id: int) -> Dict[str, Any]:
    """Generates a short-lived, single-use handshake token once calibration is verified."""
    assignment = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    is_exempt = check_is_camera_exempt(db, ase_id)
    is_overridden = check_is_camera_overridden(db, assignment_id, ase_id)

    # Unless exempt or overridden, consent must be on file
    if not is_exempt and not is_overridden:
        consent = db.query(WebcamConsent).filter(
            WebcamConsent.assignment_id == assignment_id,
            WebcamConsent.ase_id == ase_id,
            WebcamConsent.consented == True
        ).first()
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webcam consent not recorded for this assessment assignment"
            )

    token = uuid.uuid4().hex
    now = get_utc_now()
    expires_at = now + timedelta(minutes=5)

    handshake = CameraHandshake(
        handshake_token=token,
        assignment_id=assignment_id,
        ase_id=ase_id,
        created_at=now,
        expires_at=expires_at,
        is_used=False
    )
    db.add(handshake)
    db.commit()

    return {
        "handshake_token": token,
        "expires_at": expires_at.isoformat(),
        "is_exempt": is_exempt,
        "is_overridden": is_overridden
    }


def verify_and_consume_handshake(
    db: Session,
    assignment_id: int,
    ase_id: int,
    token: Optional[str]
) -> bool:
    """Consumes the single-use handshake token, returning True if valid."""
    if not token:
        return False

    handshake = db.query(CameraHandshake).filter(
        CameraHandshake.handshake_token == token,
        CameraHandshake.assignment_id == assignment_id,
        CameraHandshake.ase_id == ase_id,
        CameraHandshake.is_used == False
    ).first()

    if not handshake:
        return False

    now = get_utc_now()
    exp = handshake.expires_at.replace(tzinfo=timezone.utc if handshake.expires_at.tzinfo is None else None)
    if now > exp:
        return False

    handshake.is_used = True
    handshake.used_at = now
    db.commit()
    return True


def record_camera_heartbeat(
    db: Session,
    attempt_id: int,
    ase_id: int,
    status_code: str,
    details: Optional[str] = None
) -> Dict[str, Any]:
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.ase_id == ase_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")

    now = get_utc_now()
    attempt.last_camera_heartbeat_at = now
    attempt.camera_status = status_code

    hb = CameraHeartbeat(
        attempt_id=attempt.id,
        ase_id=ase_id,
        status=status_code,
        details=details,
        timestamp=now
    )
    db.add(hb)
    db.commit()

    # Calculate remaining seconds from server clock
    assignment = attempt.assignment
    assessment = assignment.assessment
    started_utc = attempt.started_at.replace(tzinfo=timezone.utc if attempt.started_at.tzinfo is None else None)
    total_minutes = attempt.extended_total_duration_minutes or assessment.total_duration_minutes
    total_seconds = total_minutes * 60
    elapsed = (now - started_utc).total_seconds()
    remaining = max(0, int(total_seconds - elapsed))

    return {
        "ok": True,
        "server_time": now.isoformat(),
        "remaining_seconds": remaining,
        "camera_status": status_code,
        "webcam_policy": getattr(assessment, "webcam_policy", "WARNING_ONLY"),
        "grace_period_seconds": getattr(assessment, "camera_grace_period_seconds", 30)
    }


def record_camera_event(
    db: Session,
    attempt_id: int,
    ase_id: int,
    event_type: str,
    duration_seconds: float,
    snapshot_base64: Optional[str] = None,
    is_warning: bool = True
) -> Dict[str, Any]:
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.ase_id == ase_id
    ).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    assessment = attempt.assignment.assessment
    now = get_utc_now()

    # Optional encrypted snapshot storage
    saved_snapshot_path = None
    snapshots_enabled = os.getenv("WEBCAM_SNAPSHOTS_ENABLED", "false").lower() == "true"
    if snapshots_enabled and snapshot_base64:
        try:
            # Low-res compressed bytes
            raw_bytes = base64.b64decode(snapshot_base64.split(",")[-1])
            encrypted_data = fernet.encrypt(raw_bytes)
            filename = f"snap_{attempt_id}_{int(now.timestamp())}_{uuid.uuid4().hex[:6]}.enc"
            filepath = os.path.join(SNAPSHOTS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(encrypted_data)
            saved_snapshot_path = filepath

            retention_days = int(os.getenv("WEBCAM_RETENTION_DAYS", "30"))
            auto_purge = now + timedelta(days=retention_days)

            snap_rec = WebcamProctoringSnapshot(
                attempt_id=attempt_id,
                event_type=event_type,
                snapshot_path=filepath,
                is_encrypted=True,
                captured_at=now,
                auto_purge_at=auto_purge
            )
            db.add(snap_rec)
        except Exception as e:
            # Snapshot failure should not interrupt proctoring logging
            logger.error("Webcam snapshot storage failed: %s", e, exc_info=True)

    # Check assessment policy: WARNING_ONLY vs COUNTED_STRIKES
    policy = getattr(assessment, "webcam_policy", "WARNING_ONLY")
    strike_triggered = False

    if policy == "COUNTED_STRIKES" and not is_warning:
        # Increment violation pipeline
        attempt.violation_count += 1
        viol = ExamViolation(
            attempt_id=attempt.id,
            type=f"CAMERA_{event_type}",
            occurred_at=now,
            details={"duration_seconds": duration_seconds}
        )
        db.add(viol)
        strike_triggered = True

        if attempt.violation_count >= 2:
            attempt.status = AttemptStatus.AUTO_SUBMITTED_VIOLATION
            attempt.auto_submit_reason = f"Webcam proctoring policy violation: {event_type} exceeded grace period."
            attempt.submitted_at = now

    db.commit()

    return {
        "event_recorded": True,
        "event_type": event_type,
        "policy": policy,
        "strike_triggered": strike_triggered,
        "violation_count": attempt.violation_count,
        "attempt_status": attempt.status.value
    }


def grant_camera_override(
    db: Session,
    assignment_id: int,
    granted_by_user: User,
    reason: str,
    attempt_id: Optional[int] = None
) -> Dict[str, Any]:
    """Mentor or Admin grants a one-time camera override with mandatory reason."""
    if len(reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A substantive mandatory reason (min 5 characters) must be documented for camera override"
        )

    assignment = db.query(AssessmentAssignment).filter(
        AssessmentAssignment.id == assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    # Mentor isolation: mentors can only override their own assigned mentees
    if granted_by_user.role == UserRole.MENTOR:
        mapping = db.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == granted_by_user.id,
            MentorAseAssignment.ase_id == assignment.ase_id
        ).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mentors may only grant camera overrides for their own assigned mentees"
            )

    now = get_utc_now()
    override_log = CameraOverrideLog(
        attempt_id=attempt_id,
        assignment_id=assignment_id,
        ase_id=assignment.ase_id,
        granted_by=granted_by_user.id,
        reason=reason.strip(),
        granted_at=now
    )
    db.add(override_log)

    if assignment.attempt:
        assignment.attempt.camera_override_active = True

    # Generate immediate handshake token for the candidate
    token = uuid.uuid4().hex
    handshake = CameraHandshake(
        handshake_token=token,
        assignment_id=assignment_id,
        ase_id=assignment.ase_id,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        is_used=False
    )
    db.add(handshake)
    db.commit()

    return {
        "success": True,
        "message": "One-time camera override granted and logged",
        "override_token": token,
        "granted_at": now.isoformat()
    }


def purge_expired_snapshots(db: Optional[Session] = None, retention_days: Optional[int] = None) -> int:
    """Purges snapshots older than WEBCAM_RETENTION_DAYS or explicit retention_days.
    Uses its own fresh session if none is provided, and compares timestamps in UTC consistently.
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        now_utc = datetime.now(timezone.utc)
        # Consistent naive UTC for MySQL DATETIME columns
        now_naive = now_utc.replace(tzinfo=None)

        if retention_days is not None:
            cutoff = (now_utc - timedelta(days=retention_days)).replace(tzinfo=None)
            expired = db.query(WebcamProctoringSnapshot).filter(
                (WebcamProctoringSnapshot.auto_purge_at <= now_naive) |
                (WebcamProctoringSnapshot.captured_at <= cutoff)
            ).all()
        else:
            expired = db.query(WebcamProctoringSnapshot).filter(
                WebcamProctoringSnapshot.auto_purge_at <= now_naive
            ).all()

        count = 0
        for snap in expired:
            if snap.snapshot_path and os.path.exists(snap.snapshot_path):
                try:
                    os.remove(snap.snapshot_path)
                except OSError as e:
                    logger.warning("Failed to remove snapshot file from disk (%s): %s", snap.snapshot_path, e)
            db.delete(snap)
            count += 1

        db.commit()
        return count
    finally:
        if close_session:
            db.close()


# Backward-compatible alias
purge_expired_webcam_snapshots = purge_expired_snapshots

purge_expired_webcam_snapshots = purge_expired_snapshots


def log_webcam_audit(db: Session, viewer_id: int, attempt_id: int, action: str):
    audit = WebcamAuditLog(
        viewer_id=viewer_id,
        attempt_id=attempt_id,
        action=action,
        viewed_at=get_utc_now()
    )
    db.add(audit)
    db.commit()
