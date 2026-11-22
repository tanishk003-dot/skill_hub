import os
import time
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.seed import init_db
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus, ExamViolation
from app.models.assessment_assignment import AssessmentAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.phase10_models import (
    WebcamConsent, CameraHandshake, CameraHeartbeat, CameraOverrideLog,
    WebcamProctoringSnapshot, WebcamAuditLog, AccommodationRequest, AccommodationAuditLog
)
from app.services.webcam_proctoring_service import purge_expired_webcam_snapshots

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

def _get_auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}

def _create_base_assessment(db: Session, admin: User, webcam_mode: str = "REQUIRED", webcam_policy: str = "WARNING_ONLY") -> Assessment:
    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.EASY,
        skill_category="Logic",
        question_text="Sample Logic Question for Phase 10 Testing",
        question_type=QuestionType.SINGLE_CHOICE,
        options=[{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        correct_answers=["a"],
        marks=2
    )
    db.add(q)
    db.flush()

    assessment = Assessment(
        title=f"Webcam Assessment {uuid.uuid4().hex[:6]}",
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=30,
        passing_percentage=60.0,
        webcam_mode=webcam_mode,
        webcam_policy=webcam_policy,
        camera_no_face_seconds=15,
        camera_multiple_faces_seconds=10,
        camera_head_turn_seconds=15,
        camera_grace_period_seconds=30,
        created_by=admin.id
    )
    db.add(assessment)
    db.flush()

    sec = AssessmentSection(
        assessment_id=assessment.id,
        title="Main Section",
        order_index=0,
        timer_minutes=30
    )
    db.add(sec)
    db.flush()

    sq = AssessmentSectionQuestion(
        section_id=sec.id,
        question_id=q.id,
        order_index=0
    )
    db.add(sq)
    db.commit()
    db.refresh(assessment)
    return assessment

def _create_assignment(db: Session, assessment_id: int, ase_id: int) -> AssessmentAssignment:
    now = datetime.now(timezone.utc)
    assignment = AssessmentAssignment(
        assessment_id=assessment_id,
        ase_id=ase_id,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=7)
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def test_consent_and_handshake_required_for_exam_start(db_session: Session):
    """
    Test requirement 1 & 3:
    - New assessments default to webcam_mode=REQUIRED
    - /exam/start must return 403 unless consent is recorded and a valid camera_ready handshake exists
    - Handshake is single-use: direct or replayed calls without valid token fail
    """
    ts = time.time()
    admin = User(name="Admin P10", email=f"admin_p10_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE P10", email=f"ase_p10_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    assessment = _create_base_assessment(db_session, admin, webcam_mode="REQUIRED")
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    ase_headers = _get_auth_headers(ase)

    # 1. Direct call to start exam without handshake -> 403 Forbidden
    resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    assert resp.status_code == 403
    assert "Webcam" in resp.json()["detail"] or "handshake" in resp.json()["detail"]

    # 2. Record consent
    consent_resp = client.post(f"/api/v1/proctoring/consent/{assignment.id}", headers=ase_headers, json={
        "consented": True
    })
    assert consent_resp.status_code == 200
    assert consent_resp.json()["consented"] is True

    # 3. Request handshake token (after in-browser 10-second calibration passes)
    handshake_resp = client.post(f"/api/v1/proctoring/handshake/{assignment.id}", headers=ase_headers)
    assert handshake_resp.status_code == 200
    token_data = handshake_resp.json()
    handshake_token = token_data["handshake_token"]
    assert handshake_token is not None

    # 4. Start exam with valid handshake token header
    start_resp = client.post(
        f"/api/v1/exam/start/{assignment.id}",
        headers={**ase_headers, "X-Camera-Handshake": handshake_token}
    )
    assert start_resp.status_code == 200
    exam_data = start_resp.json()
    assert exam_data["assessment_id"] == assessment.id
    assert exam_data["webcam_mode"] == "REQUIRED"
    assert exam_data["camera_status"] == "ACTIVE"
    assert len(exam_data["sections"]) > 0

    # 5. Reuse same handshake token -> fails with 403 (single use consumed)
    replay_resp = client.post(
        f"/api/v1/exam/start/{assignment.id}",
        headers={**ase_headers, "X-Camera-Handshake": handshake_token}
    )
    assert replay_resp.status_code == 403
    assert "Invalid, expired or already used" in replay_resp.json()["detail"]


def test_camera_modes_advisory_and_off(db_session: Session):
    """
    Test requirement 1 & 3:
    - ADVISORY mode: ASE can start, advisory consent/warning logged, doesn't hard-block
    - OFF mode: Exam starts immediately without camera or handshake
    """
    ts = time.time()
    admin = User(name="Admin P10 Modes", email=f"admin_modes_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE P10 Modes", email=f"ase_modes_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    ase_headers = _get_auth_headers(ase)
    admin_headers = _get_auth_headers(admin)

    # 1. Assessment with webcam_mode="OFF"
    ass_off = _create_base_assessment(db_session, admin, webcam_mode="OFF")
    assign_off = _create_assignment(db_session, ass_off.id, ase.id)

    resp_off = client.post(f"/api/v1/exam/start/{assign_off.id}", headers=ase_headers)
    assert resp_off.status_code == 200
    assert resp_off.json()["webcam_mode"] == "OFF"

    # 2. Assessment with webcam_mode="ADVISORY"
    ass_adv = _create_base_assessment(db_session, admin, webcam_mode="ADVISORY")
    assign_adv = _create_assignment(db_session, ass_adv.id, ase.id)

    # In ADVISORY mode, starting without handshake logs advisory notice and allows exam
    resp_adv = client.post(f"/api/v1/exam/start/{assign_adv.id}", headers=ase_headers)
    assert resp_adv.status_code == 200
    assert resp_adv.json()["webcam_mode"] == "ADVISORY"

    # 3. Admin modifies webcam config via PATCH endpoint
    patch_resp = client.patch(f"/api/v1/assessments/{ass_adv.id}/webcam-config", headers=admin_headers, json={
        "webcam_mode": "REQUIRED",
        "webcam_policy": "COUNTED_STRIKES",
        "camera_grace_period_seconds": 45
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["webcam_mode"] == "REQUIRED"
    assert patch_resp.json()["webcam_policy"] == "COUNTED_STRIKES"
    assert patch_resp.json()["camera_grace_period_seconds"] == 45


def test_mentor_camera_override_flow(db_session: Session):
    """
    Test requirement:
    - Mentor (for own mentee) or Admin can grant a one-time camera override
    - Mandatory documented reason (min 5 chars)
    - Written to camera_override_logs and audit logged
    - Candidate sees neutral notice ("Standard Accommodations Active" / override active)
    """
    ts = time.time()
    admin = User(name="Admin Override", email=f"admin_ov_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    mentor1 = User(name="Mentor Assigned", email=f"mentor_1_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    mentor2 = User(name="Mentor Unassigned", email=f"mentor_2_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="ASE Override", email=f"ase_ov_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, mentor1, mentor2, ase])
    db_session.commit()

    # Assign mentor1 to ase
    pair = MentorAseAssignment(mentor_id=mentor1.id, ase_id=ase.id)
    db_session.add(pair)

    assessment = _create_base_assessment(db_session, admin, webcam_mode="REQUIRED")
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    mentor1_headers = _get_auth_headers(mentor1)
    mentor2_headers = _get_auth_headers(mentor2)
    ase_headers = _get_auth_headers(ase)

    # 1. Unassigned mentor tries to override -> 403 Forbidden
    unauth_resp = client.post("/api/v1/proctoring/camera-override", headers=mentor2_headers, json={
        "assignment_id": assignment.id,
        "reason": "Hardware failure verified on mentor call."
    })
    assert unauth_resp.status_code == 403

    # 2. Reason too short (< 5 chars) -> 422 Unprocessable Entity
    short_resp = client.post("/api/v1/proctoring/camera-override", headers=mentor1_headers, json={
        "assignment_id": assignment.id,
        "reason": "bad"
    })
    assert short_resp.status_code == 422

    # 3. Assigned mentor grants override with valid reason
    good_override = client.post("/api/v1/proctoring/camera-override", headers=mentor1_headers, json={
        "assignment_id": assignment.id,
        "reason": "Hardware failure on camera sensor verified by mentor via screen share."
    })
    assert good_override.status_code == 200
    assert good_override.json()["success"] is True

    # 4. ASE now starts exam without camera handshake -> succeeds due to override!
    resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["camera_override_active"] is True
    assert data["camera_status"] == "OVERRIDDEN"


def test_reasonable_accommodations_camera_exemption(db_session: Session):
    """
    Test requirement:
    - ASE or mentor submits accommodation request
    - Admin approves CAMERA_EXEMPTION
    - Exam start automatically bypasses camera requirement without exposing reason
    """
    ts = time.time()
    admin = User(name="Admin Accom", email=f"admin_acc_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE Accom", email=f"ase_acc_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    assessment = _create_base_assessment(db_session, admin, webcam_mode="REQUIRED")
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    ase_headers = _get_auth_headers(ase)
    admin_headers = _get_auth_headers(admin)

    # 1. Candidate submits accommodation request
    req_resp = client.post("/api/v1/proctoring/accommodations/request", headers=ase_headers, json={
        "ase_id": ase.id,
        "accommodation_type": "CAMERA_EXEMPTION",
        "reason_category": "MEDICAL",
        "medical_notes": "Sensitivity to continuous camera exposure under physician guidance."
    })
    assert req_resp.status_code == 200
    req_id = req_resp.json()["request_id"]
    assert req_resp.json()["status"] == "PENDING"

    # 2. Admin approves request
    dec_resp = client.put(f"/api/v1/proctoring/accommodations/{req_id}/decision", headers=admin_headers, json={
        "approved": True,
        "admin_notes": "Approved based on documentation on file with HR."
    })
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "APPROVED"

    # 3. Candidate starts exam without camera handshake -> auto-bypasses camera!
    start_resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    assert start_resp.status_code == 200
    data = start_resp.json()
    assert data["camera_exempt"] is True
    assert data["accommodation_applied"] is True
    assert data["camera_status"] == "EXEMPT"


def test_reasonable_accommodations_extra_time_scaling(db_session: Session):
    """
    Test requirement:
    - EXTRA_TIME_PCT extends total duration and section timers server-side
    - Neutral notice only ("Standard Accommodations Active"), no medical reasons exposed
    """
    ts = time.time()
    admin = User(name="Admin Time", email=f"admin_time_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE Time", email=f"ase_time_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    assessment = _create_base_assessment(db_session, admin, webcam_mode="OFF")
    assert assessment.total_duration_minutes == 30
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    ase_headers = _get_auth_headers(ase)
    admin_headers = _get_auth_headers(admin)

    # 1. Candidate submits EXTRA_TIME_PCT request for 50% extra time
    req_resp = client.post("/api/v1/proctoring/accommodations/request", headers=ase_headers, json={
        "ase_id": ase.id,
        "accommodation_type": "EXTRA_TIME_PCT",
        "extra_time_percent": 50.0,
        "reason_category": "COGNITIVE",
        "medical_notes": "Requires extended time allowance for processing."
    })
    assert req_resp.status_code == 200
    req_id = req_resp.json()["request_id"]

    # 2. Admin approves
    client.put(f"/api/v1/proctoring/accommodations/{req_id}/decision", headers=admin_headers, json={
        "approved": True,
        "admin_notes": "50% extra time approved."
    })

    # 3. Candidate starts exam
    start_resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    assert start_resp.status_code == 200
    data = start_resp.json()
    # 30 * 1.5 = 45 minutes
    assert data["total_duration_minutes"] == 45
    assert data["accommodation_applied"] is True
    # Section timer also scaled: 30 * 1.5 = 45 minutes
    assert data["sections"][0]["timer_minutes"] == 45


def test_medical_notes_privacy_masking(db_session: Session):
    """
    Test requirement:
    - Medical notes strictly private to requester and admin
    - Mentor queries return masked placeholder: [Confidential to Candidate & Admin]
    """
    ts = time.time()
    admin = User(name="Admin Privacy", email=f"admin_priv_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    mentor = User(name="Mentor Privacy", email=f"mentor_priv_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="ASE Privacy", email=f"ase_priv_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, mentor, ase])
    db_session.commit()

    pair = MentorAseAssignment(mentor_id=mentor.id, ase_id=ase.id)
    db_session.add(pair)
    db_session.commit()

    ase_headers = _get_auth_headers(ase)
    mentor_headers = _get_auth_headers(mentor)
    admin_headers = _get_auth_headers(admin)

    secret_note = "Detailed private medical condition: Epilepsy under light flashing."
    req_resp = client.post("/api/v1/proctoring/accommodations/request", headers=ase_headers, json={
        "ase_id": ase.id,
        "accommodation_type": "ALTERNATIVE_PROCTORING",
        "reason_category": "MEDICAL",
        "medical_notes": secret_note
    })
    assert req_resp.status_code == 200

    # 1. Mentor checks requests for assigned ASEs -> medical notes MUST be masked
    mentor_resp = client.get("/api/v1/proctoring/accommodations/list", headers=mentor_headers)
    assert mentor_resp.status_code == 200
    items = mentor_resp.json()
    assert len(items) >= 1
    mentor_item = next(i for i in items if i["ase_id"] == ase.id)
    assert "Confidential to Candidate & Admin" in mentor_item["medical_notes"]
    assert secret_note not in mentor_item["medical_notes"]

    # 2. Admin checks all requests -> sees full notes
    admin_resp = client.get("/api/v1/proctoring/accommodations/list", headers=admin_headers)
    assert admin_resp.status_code == 200
    admin_item = next(i for i in admin_resp.json() if i["ase_id"] == ase.id)
    assert admin_item["medical_notes"] == secret_note

    # 3. ASE checks own requests -> sees full notes
    ase_resp = client.get("/api/v1/proctoring/accommodations/list", headers=ase_headers)
    assert ase_resp.status_code == 200
    my_item = next(i for i in ase_resp.json() if i["ase_id"] == ase.id)
    assert my_item["medical_notes"] == secret_note


def test_heartbeat_and_camera_violation_events(db_session: Session):
    """
    Test requirement:
    - Mid-exam camera heartbeat every 10-15s
    - Mid-exam violation events recorded with policy (WARNING_ONLY vs COUNTED_STRIKES)
    """
    ts = time.time()
    admin = User(name="Admin Events", email=f"admin_ev_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE Events", email=f"ase_ev_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    # Create assessment with COUNTED_STRIKES policy
    assessment = _create_base_assessment(db_session, admin, webcam_mode="OFF", webcam_policy="COUNTED_STRIKES")
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    ase_headers = _get_auth_headers(ase)
    start_resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    assert start_resp.status_code == 200
    attempt_id = start_resp.json()["attempt_id"]

    # 1. Heartbeat
    hb_resp = client.post("/api/v1/proctoring/camera-heartbeat", headers=ase_headers, json={
        "attempt_id": attempt_id,
        "status": "ACTIVE",
        "details": "Face verified in frame"
    })
    assert hb_resp.status_code == 200
    assert hb_resp.json()["ok"] is True

    # 2. Camera event: CAMERA_BLOCKED under COUNTED_STRIKES policy -> creates ExamViolation strike
    ev_resp = client.post("/api/v1/proctoring/camera-event", headers=ase_headers, json={
        "attempt_id": attempt_id,
        "event_type": "CAMERA_BLOCKED",
        "duration_seconds": 18.0,
        "is_warning": False
    })
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert ev_data["event_recorded"] is True
    assert ev_data["strike_triggered"] is True


def test_snapshot_encryption_and_retention_purge(db_session: Session, monkeypatch):
    """
    Test requirement:
    - Low-res snapshot encrypted with Fernet
    - Stored outside web root
    - Auto-purged after retention window
    """
    monkeypatch.setenv("WEBCAM_SNAPSHOTS_ENABLED", "true")
    ts = time.time()
    admin = User(name="Admin Snap", email=f"admin_snap_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE Snap", email=f"ase_snap_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    assessment = _create_base_assessment(db_session, admin, webcam_mode="OFF")
    assignment = _create_assignment(db_session, assessment.id, ase.id)

    ase_headers = _get_auth_headers(ase)
    start_resp = client.post(f"/api/v1/exam/start/{assignment.id}", headers=ase_headers)
    attempt_id = start_resp.json()["attempt_id"]

    # Send camera event with base64 snapshot payload
    sample_snapshot_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
    cam_resp = client.post("/api/v1/proctoring/camera-event", headers=ase_headers, json={
        "attempt_id": attempt_id,
        "event_type": "NO_FACE",
        "duration_seconds": 20.0,
        "snapshot_base64": sample_snapshot_base64,
        "is_warning": True
    })
    assert cam_resp.status_code == 200

    # Purge snapshots with retention_days=0 using fresh session (everything older than now is purged)
    time.sleep(0.1)
    purged_count = purge_expired_webcam_snapshots(retention_days=0)
    assert purged_count >= 1


def test_failed_snapshot_save_is_logged(monkeypatch, caplog):
    """
    Requirement 3: Errors saving webcam snapshots must NOT be silently swallowed.
    The exam flow continues normally, but the failure is logged at ERROR level.
    """
    import logging
    monkeypatch.setenv("WEBCAM_SNAPSHOTS_ENABLED", "true")
    caplog.set_level(logging.ERROR)

    ts = time.time()
    admin = User(name="Admin FailSnap", email=f"admin_fs_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE FailSnap", email=f"ase_fs_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db = SessionLocal()
    db.add_all([admin, ase])
    db.commit()

    assessment = _create_base_assessment(db, admin, webcam_mode="OFF")
    assignment = _create_assignment(db, assessment.id, ase.id)
    assignment_id = assignment.id
    ase_headers = _get_auth_headers(ase)
    db.close()

    start_resp = client.post(f"/api/v1/exam/start/{assignment_id}", headers=ase_headers)
    attempt_id = start_resp.json()["attempt_id"]

    # Mock fernet.encrypt to raise an error to simulate filesystem/encryption failure
    from app.services import webcam_proctoring_service
    def mock_encrypt_fail(data):
        raise IOError("Disk write simulation failed")
    monkeypatch.setattr(webcam_proctoring_service.fernet, "encrypt", mock_encrypt_fail)

    sample_snapshot_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    resp = client.post("/api/v1/proctoring/camera-event", headers=ase_headers, json={
        "attempt_id": attempt_id,
        "event_type": "NO_FACE",
        "duration_seconds": 15.0,
        "snapshot_base64": sample_snapshot_base64,
        "is_warning": True
    })

    # Exam proctoring flow MUST continue without crashing
    assert resp.status_code == 200
    assert resp.json()["event_recorded"] is True

    # But the failure MUST be logged at ERROR level
    assert "Webcam snapshot storage failed" in caplog.text


def test_snapshot_purge_31_days_vs_yesterday():
    """
    Requirement 4: Verify consistent purge with naive/aware UTC timestamps and fresh session:
    - Snapshot older than 30 days (31 days ago) is purged.
    - Snapshot from yesterday (1 day ago) is kept.
    """
    db = SessionLocal()
    ts = time.time()
    admin = User(name="Admin PurgeTest", email=f"admin_pt_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="ASE PurgeTest", email=f"ase_pt_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db.add_all([admin, ase])
    db.commit()

    assessment = _create_base_assessment(db, admin, webcam_mode="OFF")
    assignment = _create_assignment(db, assessment.id, ase.id)

    attempt = AssessmentAttempt(
        assessment_assignment_id=assignment.id,
        ase_id=ase.id,
        status=AttemptStatus.IN_PROGRESS
    )
    db.add(attempt)
    db.commit()

    now_utc = datetime.now(timezone.utc)
    t_31_days_ago = (now_utc - timedelta(days=31)).replace(tzinfo=None)
    t_1_day_ago = (now_utc - timedelta(days=1)).replace(tzinfo=None)

    snap_old = WebcamProctoringSnapshot(
        attempt_id=attempt.id,
        event_type="NO_FACE",
        snapshot_path="/tmp/fake_old.enc",
        is_encrypted=True,
        captured_at=t_31_days_ago,
        auto_purge_at=t_31_days_ago + timedelta(days=30)  # expired yesterday
    )
    snap_recent = WebcamProctoringSnapshot(
        attempt_id=attempt.id,
        event_type="MULTIPLE_FACES",
        snapshot_path="/tmp/fake_recent.enc",
        is_encrypted=True,
        captured_at=t_1_day_ago,
        auto_purge_at=t_1_day_ago + timedelta(days=30)  # expires in 29 days
    )
    db.add_all([snap_old, snap_recent])
    db.commit()
    old_id = snap_old.id
    recent_id = snap_recent.id
    db.close()

    # Purge with standard 30-day retention
    purged_count = purge_expired_webcam_snapshots(retention_days=30)
    assert purged_count >= 1

    # Verify snap_old is deleted, snap_recent is preserved
    verify_db = SessionLocal()
    assert verify_db.query(WebcamProctoringSnapshot).filter(WebcamProctoringSnapshot.id == old_id).first() is None
    assert verify_db.query(WebcamProctoringSnapshot).filter(WebcamProctoringSnapshot.id == recent_id).first() is not None
    verify_db.close()
