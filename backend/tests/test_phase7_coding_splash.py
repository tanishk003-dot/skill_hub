import pytest
import os
from datetime import datetime, date, timedelta, timezone
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.assessment_assignment import AssessmentAssignment
from app.models.quote import MotivationalQuote
from app.models.coding import CodingSubmission, CodingRunLog, CodingPlagiarismFlag
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.services.code_runner import (
    Judge0Runner,
    MockRunner,
    get_code_runner,
    sanitize_error_output
)
from app.services.plagiarism_service import compute_similarity, scan_and_record_plagiarism

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

# ============================================================================
# 1. Judge0 503 Sandboxed Runner & MockRunner Restrictions
# ============================================================================
def test_mock_runner_only_allowed_when_app_env_is_test(monkeypatch):
    # Requirement 1: MockRunner is allowed only when APP_ENV=test
    monkeypatch.setattr(settings, "APP_ENV", "test")
    runner = get_code_runner()
    assert isinstance(runner, MockRunner)

    monkeypatch.setattr(settings, "APP_ENV", "production")
    runner = get_code_runner()
    assert isinstance(runner, Judge0Runner)

def test_judge0_runner_returns_503_when_unreachable_or_unhealthy(monkeypatch):
    # Requirement 1: If Judge0 is unreachable or unhealthy, return clear 503 "Code runner unavailable"
    # NEVER silently fallback to MockRunner or host execution
    monkeypatch.setattr(settings, "JUDGE0_URL", "http://127.0.0.1:59999")
    runner = Judge0Runner()
    with pytest.raises(HTTPException) as exc_info:
        runner.run_tests(
            language="python",
            source_code="print(1)",
            sample_cases=[{"id": 1, "input": "", "expected_output": "1"}],
            hidden_cases=[]
        )
    assert exc_info.value.status_code == 503
    assert "Code runner unavailable" in str(exc_info.value.detail)

# ============================================================================
# 2. Hidden Test Case Confidentiality & Zero Leakage
# ============================================================================
def test_hidden_test_cases_never_leak_in_sanitizer():
    # Requirement 5: Hidden inputs and expected outputs must NEVER appear in logs or errors
    hidden_cases = [
        {"id": 101, "input": "super_secret_input_999", "expected_output": "classified_output_888"},
        {"id": 102, "input": "abc123xyz", "expected_output": "result456"}
    ]

    dirty_compile_error = (
        "Traceback (most recent call last):\n"
        "  File 'solution.py', line 2, in <module>\n"
        "    ValueError: Error on input 'super_secret_input_999' expecting 'classified_output_888'\n"
    )

    clean_error = sanitize_error_output(dirty_compile_error, hidden_cases)
    assert "super_secret_input_999" not in clean_error
    assert "classified_output_888" not in clean_error
    assert "[HIDDEN_INPUT_REDACTED]" in clean_error
    assert "[HIDDEN_OUTPUT_REDACTED]" in clean_error

# ============================================================================
# 3. Canonical Coding Endpoints, Ownership & Deadlines
# ============================================================================
def test_coding_run_and_submit_ownership_and_deadline(db_session: Session, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")

    # Create ASE User and Assessment
    ase = User(name="Coding ASE", email=f"coding_ase_{datetime.now(timezone.utc).timestamp()}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    other_ase = User(name="Other ASE", email=f"other_ase_{datetime.now(timezone.utc).timestamp()}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([ase, other_ase])
    db_session.commit()

    assessment = Assessment(
        title="Coding Proficiency Assessment",
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=30,
        passing_percentage=60.0
    )
    db_session.add(assessment)
    db_session.commit()

    now_utc = datetime.now(timezone.utc)
    assignment = AssessmentAssignment(
        assessment_id=assessment.id,
        ase_id=ase.id,
        start_date=now_utc - timedelta(hours=1),
        end_date=now_utc + timedelta(days=1)
    )
    db_session.add(assignment)
    db_session.commit()

    # Coding Question with Hidden Cases
    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.EASY,
        skill_category="Algorithms",
        question_text="Sum two numbers",
        question_type=QuestionType.CODING,
        marks=10,
        options=[],
        correct_answers=[],
        sample_test_cases=[{"id": 1, "input": "2 3", "expected_output": "5"}],
        hidden_test_cases=[{"id": 2, "input": "100 200", "expected_output": "300", "marks": 5}]
    )
    db_session.add(q)
    db_session.commit()

    # Create In-Progress Attempt
    attempt = AssessmentAttempt(
        assessment_assignment_id=assignment.id,
        ase_id=ase.id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=now_utc
    )
    db_session.add(attempt)
    db_session.commit()

    ase_headers = _get_auth_headers(ase)
    other_headers = _get_auth_headers(other_ase)

    # 1. Canonical route run: /api/v1/coding/run
    run_payload = {
        "attempt_id": attempt.id,
        "question_id": q.id,
        "language": "python",
        "source_code": "print(5)"
    }
    resp = client.post("/api/v1/coding/run", json=run_payload, headers=ase_headers)
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["status"] == "ACCEPTED"
    assert len(run_data["results"]) == 1
    # Sample test case has input/output shown
    assert run_data["results"][0]["input"] == "2 3"

    # 2. Forbidden access: other user cannot run code on this attempt
    resp_other = client.post("/api/v1/coding/run", json=run_payload, headers=other_headers)
    assert resp_other.status_code == 403

    # 3. Canonical route submit: /api/v1/coding/submit
    submit_payload = {
        "attempt_id": attempt.id,
        "question_id": q.id,
        "language": "python",
        "source_code": "print(5)"
    }
    sub_resp = client.post("/api/v1/coding/submit", json=submit_payload, headers=ase_headers)
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["submission_id"] > 0
    # REQUIREMENT 5 CHECK: In submit response, hidden test case inputs/outputs MUST be None!
    for r in sub_data["results"]:
        if not r["is_sample"]:
            assert r["input"] is None
            assert r["expected_output"] is None
            assert r["actual_output"] is None

    # 4. Conflict 409 check: when attempt is closed/submitted
    attempt.status = AttemptStatus.SUBMITTED
    db_session.commit()

    conflict_resp = client.post("/api/v1/coding/run", json=run_payload, headers=ase_headers)
    assert conflict_resp.status_code == 409
    assert "closed" in conflict_resp.json()["detail"].lower()

# ============================================================================
# 4. DB-Backed Run Rate Limiting
# ============================================================================
def test_coding_run_db_rate_limiting(db_session: Session, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "CODING_RUN_RATE_LIMIT_PER_ATTEMPT", 3)

    ase = User(name="RateLimit ASE", email=f"rl_ase_{datetime.now(timezone.utc).timestamp()}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add(ase)
    db_session.commit()

    assessment = Assessment(title="RL Assessment", type=AssessmentType.LOGICAL_THINKING, total_duration_minutes=30)
    db_session.add(assessment)
    db_session.commit()

    now_utc = datetime.now(timezone.utc)
    assignment = AssessmentAssignment(
        assessment_id=assessment.id,
        ase_id=ase.id,
        start_date=now_utc - timedelta(hours=1),
        end_date=now_utc + timedelta(days=1)
    )
    db_session.add(assignment)
    db_session.commit()

    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.EASY,
        skill_category="Logic",
        question_text="QRL",
        question_type=QuestionType.CODING,
        options=[],
        correct_answers=[]
    )
    db_session.add(q)
    db_session.commit()

    attempt = AssessmentAttempt(assessment_assignment_id=assignment.id, ase_id=ase.id, status=AttemptStatus.IN_PROGRESS, started_at=datetime.now(timezone.utc))
    db_session.add(attempt)
    db_session.commit()

    headers = _get_auth_headers(ase)
    payload = {"attempt_id": attempt.id, "question_id": q.id, "language": "python", "source_code": "pass"}

    # Runs 1, 2, 3 should succeed
    for i in range(3):
        r = client.post("/api/v1/coding/run", json=payload, headers=headers)
        assert r.status_code == 200

    # Run 4 should hit DB rate limit and return 429
    r4 = client.post("/api/v1/coding/run", json=payload, headers=headers)
    assert r4.status_code == 429
    assert "limit reached" in r4.json()["detail"].lower()

    # Verify logs stored in DB
    db_log_count = db_session.query(CodingRunLog).filter(CodingRunLog.attempt_id == attempt.id).count()
    assert db_log_count == 3

# ============================================================================
# 5. Plagiarism Detection & Privacy Isolation
# ============================================================================
def test_plagiarism_detection_and_isolation(db_session: Session):
    ts = datetime.now(timezone.utc).timestamp()
    mentor_1 = User(name="Mentor 1", email=f"mentor1_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    mentor_2 = User(name="Mentor 2", email=f"mentor2_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    admin = User(name="Admin Plag", email=f"admin_plag_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase_1 = User(name="Plag ASE 1", email=f"plag_ase1_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    ase_2 = User(name="Plag ASE 2", email=f"plag_ase2_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    ase_3 = User(name="Plag ASE 3", email=f"plag_ase3_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)

    db_session.add_all([mentor_1, mentor_2, admin, ase_1, ase_2, ase_3])
    db_session.commit()

    # Assign ase_1 and ase_2 to mentor_1; ase_3 to mentor_2
    db_session.add_all([
        MentorAseAssignment(mentor_id=mentor_1.id, ase_id=ase_1.id),
        MentorAseAssignment(mentor_id=mentor_1.id, ase_id=ase_2.id),
        MentorAseAssignment(mentor_id=mentor_2.id, ase_id=ase_3.id)
    ])
    db_session.commit()

    # Create dummy question
    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.EASY,
        skill_category="Strings",
        question_text="Q Plag",
        question_type=QuestionType.CODING,
        options=[],
        correct_answers=[]
    )
    db_session.add(q)
    db_session.commit()

    # Flag between ase_1 and ase_2 (both belong to mentor_1)
    flag_1_2 = CodingPlagiarismFlag(
        question_id=q.id,
        ase1_id=ase_1.id,
        ase2_id=ase_2.id,
        attempt1_id=10,
        attempt2_id=11,
        similarity_score=92.5,
        status="FLAGGED_FOR_REVIEW"
    )
    # Flag between ase_1 and ase_3 (cross-mentor)
    flag_1_3 = CodingPlagiarismFlag(
        question_id=q.id,
        ase1_id=ase_1.id,
        ase2_id=ase_3.id,
        attempt1_id=10,
        attempt2_id=12,
        similarity_score=85.0,
        status="FLAGGED_FOR_REVIEW"
    )
    db_session.add_all([flag_1_2, flag_1_3])
    db_session.commit()

    # ASE gets 403 Forbidden
    ase_headers = _get_auth_headers(ase_1)
    resp_ase = client.get("/api/v1/coding/plagiarism", headers=ase_headers)
    assert resp_ase.status_code == 403

    # Mentor 1 sees ONLY flag_1_2 (where both are their mentees)
    m1_headers = _get_auth_headers(mentor_1)
    resp_m1 = client.get("/api/v1/coding/plagiarism", headers=m1_headers)
    assert resp_m1.status_code == 200
    m1_flags = resp_m1.json()
    flag_ids = [f["id"] for f in m1_flags]
    assert flag_1_2.id in flag_ids
    assert flag_1_3.id not in flag_ids
    # Similarity score returned, NO source code returned
    assert "source_code" not in m1_flags[0]
    assert m1_flags[0]["similarity_score"] == 92.5

    # Admin sees all flags
    admin_headers = _get_auth_headers(admin)
    resp_admin = client.get("/api/v1/coding/plagiarism", headers=admin_headers)
    assert resp_admin.status_code == 200
    admin_flag_ids = [f["id"] for f in resp_admin.json()]
    assert flag_1_2.id in admin_flag_ids
    assert flag_1_3.id in admin_flag_ids

# ============================================================================
# 6. Daily Quotes Deterministic Selection & Admin Management
# ============================================================================
def test_daily_quote_deterministic_selection_and_admin_crud(db_session: Session):
    ts = datetime.now(timezone.utc).timestamp()
    admin = User(name="Quote Admin", email=f"quote_admin_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    ase = User(name="Quote ASE", email=f"quote_ase_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([admin, ase])
    db_session.commit()

    admin_headers = _get_auth_headers(admin)
    ase_headers = _get_auth_headers(ase)

    # 1. Fetch daily quote twice for same user -> deterministic, identical quote
    r1 = client.get("/api/v1/quotes/daily", headers=ase_headers)
    assert r1.status_code == 200
    q1 = r1.json()["quote"]

    r2 = client.get("/api/v1/quotes/daily", headers=ase_headers)
    assert r2.status_code == 200
    q2 = r2.json()["quote"]

    assert q1["id"] == q2["id"]
    assert q1["text"] == q2["text"]
    assert q1["role"] == "ASE"

    # 2. Admin CRUD on Quotes
    new_quote_payload = {
        "role": "ADMIN",
        "text": f"True leaders build resilient systems {ts}.",
        "author": "L&K Team",
        "is_active": True
    }
    create_resp = client.post("/api/v1/quotes/admin", json=new_quote_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    created_quote = create_resp.json()
    assert created_quote["id"] > 0

    # Non-admin cannot create quote
    forbidden_resp = client.post("/api/v1/quotes/admin", json=new_quote_payload, headers=ase_headers)
    assert forbidden_resp.status_code == 403

    # Update quote
    update_resp = client.put(f"/api/v1/quotes/admin/{created_quote['id']}", json={"is_active": False}, headers=admin_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False

# ============================================================================
# 7. ASE Onboarding Progress Breakdown (Assessments 40%, Trainings 40%, Classes 20%)
# ============================================================================
def test_ase_onboarding_progress_calculation(db_session: Session):
    ts = datetime.now(timezone.utc).timestamp()
    ase = User(name="Progress ASE", email=f"prog_ase_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add(ase)
    db_session.commit()

    ase_headers = _get_auth_headers(ase)

    prog_resp = client.get(f"/api/v1/analytics/ase/{ase.id}/onboarding-progress", headers=ase_headers)
    assert prog_resp.status_code == 200
    pdata = prog_resp.json()
    assert "overall_percentage" in pdata
    assert pdata["assessments"]["weight"] == 40
    assert pdata["trainings"]["weight"] == 40
    assert pdata["live_classes"]["weight"] == 20
