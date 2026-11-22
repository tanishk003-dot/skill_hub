import io
import time
import uuid
import pytest
from datetime import datetime, timedelta, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.cohort import Cohort, CohortMember
from app.models.assignment import MentorAseAssignment
from app.models.training import Training, TrainingAssignment
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.phase9_models import (
    ReadinessConfig, ReadinessAuditLog, AseReadinessHistory,
    AseGamification, OnboardingMilestone, AILearningRoadmap,
    AseRiskSignal, MentorNudgeLog, ReassessmentSchedule,
    IssuedCertificate, MockInterviewSession, PublicVerifyRateLog
)
from app.services.readiness_service import LEGAL_DISCLAIMER

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

def _get_auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}

def test_readiness_calculation_and_legal_disclaimer(db_session: Session):
    ts = time.time()
    admin = User(name="Admin User", email=f"admin_r_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="Ase Learner", email=f"ase_r_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    admin_headers = _get_auth_headers(admin)
    ase_headers = _get_auth_headers(ase)

    # 1. ASE accesses own readiness (no data yet -> handles without crashing)
    resp = client.get("/api/v1/readiness/me", headers=ase_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 0.0
    assert "formula" in data
    # Legal disclaimer requirement
    assert data["disclaimer"] == LEGAL_DISCLAIMER
    assert "not a basis for hiring, promotion or termination" in data["disclaimer"]

    # 2. Non-admin attempting to update weights -> 403 Forbidden
    bad_update = client.put("/api/v1/readiness/config", headers=ase_headers, json={
        "assessment_weight": 0.2, "coding_weight": 0.2, "training_weight": 0.2, "attendance_weight": 0.2, "consistency_weight": 0.2
    })
    assert bad_update.status_code == 403

    # 3. Weights summing != 1.0 -> 422 Unprocessable Entity
    invalid_sum = client.put("/api/v1/readiness/config", headers=admin_headers, json={
        "assessment_weight": 0.5, "coding_weight": 0.5, "training_weight": 0.5, "attendance_weight": 0.1, "consistency_weight": 0.1
    })
    assert invalid_sum.status_code == 422
    assert "equal 1.0" in invalid_sum.json()["detail"].lower()

    # 4. Valid admin update -> 200 OK & written to audit log
    valid_update = client.put("/api/v1/readiness/config", headers=admin_headers, json={
        "assessment_weight": 0.25, "coding_weight": 0.25, "training_weight": 0.20, "attendance_weight": 0.15, "consistency_weight": 0.15
    })
    assert valid_update.status_code == 200
    assert valid_update.json()["weights"]["assessment_weight"] == 0.25

    audit = db_session.query(ReadinessAuditLog).order_by(ReadinessAuditLog.id.desc()).first()
    assert audit is not None
    assert audit.changed_by == admin.id
    assert audit.new_weights["assessment_weight"] == 0.25

def test_mentor_isolation_and_ase_risk_data_protection(db_session: Session):
    ts = time.time()
    mentor_a = User(name="Mentor A", email=f"mentor_a_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    mentor_b = User(name="Mentor B", email=f"mentor_b_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase_a = User(name="ASE A", email=f"ase_a_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([mentor_a, mentor_b, ase_a])
    db_session.commit()

    # Assign ASE A to Mentor A only
    assignment = MentorAseAssignment(mentor_id=mentor_a.id, ase_id=ase_a.id)
    db_session.add(assignment)
    db_session.commit()

    headers_a = _get_auth_headers(mentor_a)
    headers_b = _get_auth_headers(mentor_b)
    headers_ase = _get_auth_headers(ase_a)

    # 1. ASE must NEVER receive risk data -> 403 Forbidden
    ase_risk_resp = client.get("/api/v1/early-warning/mentee-risks", headers=headers_ase)
    assert ase_risk_resp.status_code == 403

    # 2. Mentor A sees risk signals for own mentee
    mentor_a_resp = client.get("/api/v1/early-warning/mentee-risks", headers=headers_a)
    assert mentor_a_resp.status_code == 200
    risks = mentor_a_resp.json()
    assert len(risks) == 1
    assert risks[0]["ase_id"] == ase_a.id

    # 3. Mentor B cannot nudge ASE A -> 403 Forbidden
    bad_nudge = client.post(f"/api/v1/early-warning/nudge/{ase_a.id}", headers=headers_b)
    assert bad_nudge.status_code == 403

    # 4. Mentor A nudges ASE A -> 200 OK (supportive template)
    nudge1 = client.post(f"/api/v1/early-warning/nudge/{ase_a.id}", headers=headers_a)
    assert nudge1.status_code == 200
    assert "dispatched" in nudge1.json()["message"].lower()

    # 5. Rate limit: 2nd nudge within 48h -> 429 Too Many Requests
    nudge2 = client.post(f"/api/v1/early-warning/nudge/{ase_a.id}", headers=headers_a)
    assert nudge2.status_code == 429
    assert "48 hours" in nudge2.json()["detail"].lower()

def test_leaderboard_opt_in_default_off_and_privacy(db_session: Session):
    ts = time.time()
    ase = User(name="Priya Sharma", email=f"priya_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add(ase)
    db_session.commit()
    headers = _get_auth_headers(ase)

    # 1. Default journey path: leaderboard_opt_in must be FALSE
    path_resp = client.get("/api/v1/journey/my-path", headers=headers)
    assert path_resp.status_code == 200
    assert path_resp.json()["leaderboard_opt_in"] is False

    # 2. Leaderboard: not opted in -> not visible on leaderboard
    lb1 = client.get("/api/v1/journey/leaderboard", headers=headers)
    assert lb1.status_code == 200
    assert not any(item["is_me"] for item in lb1.json())

    # 3. Opt-in with default last initial privacy
    opt_in_resp = client.put("/api/v1/journey/leaderboard-opt-in", headers=headers, json={"opt_in": True, "show_full_name": False})
    assert opt_in_resp.status_code == 200
    assert opt_in_resp.json()["leaderboard_opt_in"] is True

    # 4. Leaderboard: now appears with "Priya S." and ONLY non-sensitive gamification attributes
    lb2 = client.get("/api/v1/journey/leaderboard", headers=headers)
    assert lb2.status_code == 200
    my_entry = next((item for item in lb2.json() if item["is_me"]), None)
    assert my_entry is not None
    assert my_entry["display_name"] == "Priya S."
    assert "xp" in my_entry
    assert "level" in my_entry
    # Ensure zero leak of scores or risk
    assert "score" not in my_entry
    assert "risk" not in my_entry
    assert "weak_skills" not in my_entry

    # 5. Opt-out immediately removes user
    client.put("/api/v1/journey/leaderboard-opt-in", headers=headers, json={"opt_in": False})
    lb3 = client.get("/api/v1/journey/leaderboard", headers=headers)
    assert not any(item["is_me"] for item in lb3.json())

def test_verified_certificate_uuid_and_minimal_public_disclosure(db_session: Session):
    ts = time.time()
    admin = User(name="System Admin", email=f"admin_c_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase1 = User(name="Vikram Patel", email=f"vikram_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    ase2 = User(name="Other ASE", email=f"other_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase1, ase2])
    db_session.commit()

    admin_headers = _get_auth_headers(admin)
    ase1_headers = _get_auth_headers(ase1)
    ase2_headers = _get_auth_headers(ase2)

    # 1. Admin issues certificate
    issue_resp = client.post("/api/v1/certificates/issue", headers=admin_headers, json={
        "ase_id": ase1.id,
        "title": "Advanced Distributed Systems Masterclass",
        "entity_type": "TRAINING",
        "entity_id": 1
    })
    assert issue_resp.status_code == 200
    cert_uuid = issue_resp.json()["cert_uuid"]
    # Verify UUID4 format
    assert len(cert_uuid) == 36
    uuid_obj = uuid.UUID(cert_uuid, version=4)
    assert str(uuid_obj) == cert_uuid

    # 2. Public verify endpoint: NO authentication required
    public_resp = client.get(f"/api/v1/certificates/verify/{cert_uuid}")
    assert public_resp.status_code == 200
    v_data = public_resp.json()
    assert v_data["status"] == "Valid"
    # Minimal disclosure check: "Vikram P." (no full name unless opted in)
    assert v_data["recipient_name"] == "Vikram P."
    assert v_data["course_title"] == "Advanced Distributed Systems Masterclass"
    # Strictly NO email, user IDs, or marks
    assert "email" not in v_data
    assert "ase_id" not in v_data
    assert "score" not in v_data

    # 3. Authorized PDF download
    # Recipient can download
    down_resp = client.get(f"/api/v1/certificates/download/{cert_uuid}", headers=ase1_headers)
    assert down_resp.status_code == 200
    assert down_resp.headers["content-type"] == "application/pdf"

    # Other ASE cannot download another user's cert -> 403 Forbidden
    bad_down = client.get(f"/api/v1/certificates/download/{cert_uuid}", headers=ase2_headers)
    assert bad_down.status_code == 403

def test_mock_interviewer_ase_only_and_safety(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor M", email=f"mentor_m_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="Candidate ASE", email=f"cand_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([mentor, ase])
    db_session.commit()

    mentor_headers = _get_auth_headers(mentor)
    ase_headers = _get_auth_headers(ase)

    # 1. Mentor denied -> 403 Forbidden (ASE only)
    bad_start = client.post("/api/v1/mock-interview/start", headers=mentor_headers, json={})
    assert bad_start.status_code == 403

    # 2. ASE starts interview session
    start_resp = client.post("/api/v1/mock-interview/start", headers=ase_headers, json={
        "target_role": "Backend Engineer",
        "skill_focus": "Distributed Systems"
    })
    assert start_resp.status_code == 200
    s_data = start_resp.json()
    sess_id = s_data["session_id"]
    assert "question" in s_data
    assert "AI-generated, please verify" in s_data["disclaimer"]

    # 3. Candidate responds
    resp_call = client.post("/api/v1/mock-interview/respond", headers=ase_headers, json={
        "session_id": sess_id,
        "candidate_answer": "I implement idempotent unique keys using Redis setnx with a 24-hour TTL."
    })
    assert resp_call.status_code == 200
    ans_data = resp_call.json()
    assert "previous_feedback" in ans_data
    assert ans_data["is_demo_mode"] is True

def test_ceo_command_center_privacy_masking_and_pdf(db_session: Session):
    ts = time.time()
    admin = User(name="CEO Admin", email=f"ceo_admin_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    mentor = User(name="Mentor M", email=f"mentor_c_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    
    # Create small cohort with only 1 ASE (< 3 members) to test privacy masking
    c_small = Cohort(name=f"Secret Pilot Cohort {ts}", start_date=date.today())
    db_session.add_all([admin, mentor, c_small])
    db_session.commit()

    ase1 = User(name="Solo ASE", email=f"solo_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add(ase1)
    db_session.commit()

    cm = CohortMember(cohort_id=c_small.id, ase_id=ase1.id)
    db_session.add(cm)
    db_session.commit()

    admin_headers = _get_auth_headers(admin)
    mentor_headers = _get_auth_headers(mentor)

    # 1. Non-admin accessing CEO Command Center -> 403 Forbidden
    bad_access = client.get("/api/v1/ceo-center/overview", headers=mentor_headers)
    assert bad_access.status_code == 403

    # 2. Admin access overview
    overview_resp = client.get("/api/v1/ceo-center/overview", headers=admin_headers)
    assert overview_resp.status_code == 200
    ov = overview_resp.json()
    assert "org_readiness_avg" in ov
    assert "time_to_productivity_days" in ov
    assert "formulas" in ov
    assert "causation_note" in ov["formulas"]

    # Verify small cohort (< 3) is privacy masked
    pilot_cohort = next((c for c in ov["cohort_benchmarks"] if c["cohort_id"] == c_small.id), None)
    assert pilot_cohort is not None
    assert pilot_cohort["is_masked"] is True
    assert pilot_cohort["member_count"] == "< 3 (Masked)"
    assert pilot_cohort["average_readiness"] == "Masked for Privacy"

    # 3. Export Executive PDF
    pdf_resp = client.get("/api/v1/ceo-center/executive-pdf", headers=admin_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"

def test_reassessment_randomization_and_growth_analytics(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_r_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="Candidate Bob", email=f"bob_r_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([mentor, ase])
    db_session.commit()

    # Assign
    db_session.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=ase.id))

    # Create original assessment & question
    qb1 = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.MEDIUM,
        skill_category="Architecture",
        question_text="Baseline Question 1",
        question_type=QuestionType.SINGLE_CHOICE,
        options=["A", "B", "C", "D"],
        correct_answers=["A"],
        marks=1
    )
    qb2 = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.MEDIUM,
        skill_category="Architecture",
        question_text="Variant Question 2 (Different for Reassessment)",
        question_type=QuestionType.SINGLE_CHOICE,
        options=["A", "B", "C", "D"],
        correct_answers=["B"],
        marks=1
    )
    db_session.add_all([qb1, qb2])
    db_session.commit()

    orig_ass = Assessment(
        title="Architecture Baseline",
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=45,
        passing_percentage=60.0
    )
    db_session.add(orig_ass)
    db_session.commit()

    sec = AssessmentSection(assessment_id=orig_ass.id, title="Main Section", order_index=1, timer_minutes=45)
    db_session.add(sec)
    db_session.commit()
    db_session.add(AssessmentSectionQuestion(section_id=sec.id, question_id=qb1.id, order_index=1))
    db_session.commit()

    headers = _get_auth_headers(mentor)

    # Schedule re-assessment -> generates variant assessment with different question set to prevent memorization
    sched_resp = client.post("/api/v1/reassessments/schedule", headers=headers, json={
        "original_assessment_id": orig_ass.id,
        "phase_label": "30_DAY",
        "ase_id": ase.id,
        "scheduled_days_from_now": 30
    })
    assert sched_resp.status_code == 200
    sched_data = sched_resp.json()
    assert sched_data["reassessment_id"] != orig_ass.id

    # Growth analytics endpoint returns percentage progression
    growth_resp = client.get(f"/api/v1/reassessments/growth/{ase.id}", headers=headers)
    assert growth_resp.status_code == 200
    assert "phases" in growth_resp.json()
