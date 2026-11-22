from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base, DateTime6

def get_utc_now():
    return datetime.now(timezone.utc)

class WebcamConsent(Base):
    __tablename__ = "webcam_consents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assessment_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consented = Column(Boolean, nullable=False, default=True)
    consented_at = Column(DateTime6(), default=get_utc_now, nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    assignment = relationship("AssessmentAssignment")
    ase = relationship("User")


class CameraHandshake(Base):
    __tablename__ = "camera_handshakes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    handshake_token = Column(String(64), unique=True, nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("assessment_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime6(), default=get_utc_now, nullable=False)
    expires_at = Column(DateTime6(), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime6(), nullable=True)

    assignment = relationship("AssessmentAssignment")
    ase = relationship("User")


class CameraHeartbeat(Base):
    __tablename__ = "camera_heartbeats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False) # ACTIVE, BLOCKED, REVOKED, NO_FACE, MULTIPLE_FACES, HEAD_TURNED
    details = Column(String(255), nullable=True)
    timestamp = Column(DateTime6(), default=get_utc_now, nullable=False)

    attempt = relationship("AssessmentAttempt")
    ase = relationship("User")


class CameraOverrideLog(Base):
    __tablename__ = "camera_override_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assessment_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    granted_at = Column(DateTime6(), default=get_utc_now, nullable=False)

    assignment = relationship("AssessmentAssignment")
    ase = relationship("User", foreign_keys=[ase_id])
    granter = relationship("User", foreign_keys=[granted_by])


class WebcamProctoringSnapshot(Base):
    __tablename__ = "webcam_proctoring_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    snapshot_path = Column(String(255), nullable=False)
    is_encrypted = Column(Boolean, default=True, nullable=False)
    captured_at = Column(DateTime6(), default=get_utc_now, nullable=False)
    auto_purge_at = Column(DateTime6(), nullable=False)

    attempt = relationship("AssessmentAttempt")


class WebcamAuditLog(Base):
    __tablename__ = "webcam_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    viewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False) # VIEW_EVENT_LOG, VIEW_SNAPSHOT
    viewed_at = Column(DateTime6(), default=get_utc_now, nullable=False)

    viewer = relationship("User")
    attempt = relationship("AssessmentAttempt")


class AccommodationRequest(Base):
    __tablename__ = "accommodation_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ase_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    accommodation_type = Column(String(50), nullable=False) # EXTRA_TIME_PCT, CAMERA_EXEMPTION, REST_BREAKS, ALTERNATIVE_PROCTORING, OTHER
    extra_time_percent = Column(Float, default=0.0, nullable=False)
    reason_category = Column(String(100), nullable=False)
    medical_notes = Column(Text, nullable=True) # Confidential: only visible to requester and admin
    status = Column(String(20), default="PENDING", nullable=False) # PENDING, APPROVED, REJECTED
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    ase = relationship("User", foreign_keys=[ase_id])
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class AccommodationAuditLog(Base):
    __tablename__ = "accommodation_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("accommodation_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False) # REQUEST_CREATED, REQUEST_APPROVED, REQUEST_REJECTED, APPLIED_TO_EXAM
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    note = Column(Text, nullable=True)
    timestamp = Column(DateTime6(), default=get_utc_now, nullable=False)

    request = relationship("AccommodationRequest")
    actor = relationship("User")
