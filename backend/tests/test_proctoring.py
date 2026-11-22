import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus, ExamViolation

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    db = SessionLocal()
    ts = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    
    # Create test ASE user
    ase_user = User(
        name=f"Test ASE User {ts}",
        email=f"test_ase_{ts}@csm.tech",
        hashed_password=hash_password("password123"),
        role=UserRole.ASE,
        is_active=True
    )
    db.add(ase_user)
    db.commit()
    db.refresh(ase_user)

    # Create Question & Assessment
    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.EASY,
        skill_category="Logic",
        question_text=f"Sample Logic Q {ts}",
        question_type=QuestionType.SINGLE_CHOICE,
        options=[{"id": "opt1", "text": "Choice 1"}, {"id": "opt2", "text": "Choice 2"}],
        correct_answers=["opt1"],
        marks=2
    )
    db.add(q)
    db.commit()
    db.refresh(q)

    assessment = Assessment(
        title=f"Proctored Test Assessment {ts}",
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=30,
        passing_percentage=60.0,
        webcam_mode="OFF"
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    section = AssessmentSection(
        assessment_id=assessment.id,
        title="Section 1",
        order_index=0,
        timer_minutes=15
    )
    db.add(section)
    db.commit()
    db.refresh(section)

    sq = AssessmentSectionQuestion(
        section_id=section.id,
        question_id=q.id,
        order_index=0
    )
    db.add(sq)
    db.commit()

    now_utc = datetime.now(timezone.utc)
    assignment = AssessmentAssignment(
        assessment_id=assessment.id,
        ase_id=ase_user.id,
        start_date=now_utc - timedelta(hours=1),
        end_date=now_utc + timedelta(hours=2)
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    yield {
        "ase_id": ase_user.id,
        "ase_email": ase_user.email,
        "assignment_id": assignment.id,
        "question_id": q.id
    }

    try:
        db.query(ExamViolation).filter(ExamViolation.attempt_id.in_(
            db.query(AssessmentAttempt.id).filter(AssessmentAttempt.assessment_assignment_id == assignment.id)
        )).delete(synchronize_session=False)
        db.query(AssessmentAttempt).filter(AssessmentAttempt.assessment_assignment_id == assignment.id).delete(synchronize_session=False)
        db.query(AssessmentAssignment).filter(AssessmentAssignment.id == assignment.id).delete(synchronize_session=False)
        db.query(AssessmentSectionQuestion).filter(AssessmentSectionQuestion.section_id == section.id).delete(synchronize_session=False)
        db.query(AssessmentSection).filter(AssessmentSection.id == section.id).delete(synchronize_session=False)
        db.query(Assessment).filter(Assessment.id == assessment.id).delete(synchronize_session=False)
        db.query(QuestionBank).filter(QuestionBank.id == q.id).delete(synchronize_session=False)
        db.query(User).filter(User.id == ase_user.id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def get_auth_headers(user_id: int, role: str = "ASE"):
    token = create_access_token(subject=str(user_id), role=role)
    return {"Authorization": f"Bearer {token}"}


def test_first_violation_flow(setup_database):
    data = setup_database
    headers = get_auth_headers(data["ase_id"])

    # Start exam
    start_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    assert start_res.status_code == 200
    attempt_id = start_res.json()["attempt_id"]
    assert start_res.json()["violation_count"] == 0

    # 1st Violation (Fullscreen exit)
    v1_res = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "FULLSCREEN_EXIT", "details": {"reason": "User pressed ESC"}},
        headers=headers
    )
    assert v1_res.status_code == 200
    v1_data = v1_res.json()
    assert v1_data["violation_count"] == 1
    assert v1_data["auto_submitted"] is False
    assert v1_data["debounced"] is False
    assert v1_data["status"] == "IN_PROGRESS"


def test_violation_debouncing(setup_database):
    data = setup_database
    headers = get_auth_headers(data["ase_id"])

    # Start exam
    start_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    attempt_id = start_res.json()["attempt_id"]

    # 1st Violation
    v1_res = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "FULLSCREEN_EXIT"},
        headers=headers
    )
    assert v1_res.status_code == 200
    assert v1_res.json()["violation_count"] == 1

    # Immediate 2nd event (e.g. window blur triggered immediately by fullscreen exit)
    v2_res = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "WINDOW_BLUR"},
        headers=headers
    )
    assert v2_res.status_code == 200
    v2_data = v2_res.json()
    assert v2_data["debounced"] is True
    # Count must remain 1 because it was debounced!
    assert v2_data["violation_count"] == 1
    assert v2_data["auto_submitted"] is False


def test_second_violation_auto_submits(setup_database):
    data = setup_database
    headers = get_auth_headers(data["ase_id"])

    start_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    attempt_id = start_res.json()["attempt_id"]

    # Answer a question first
    save_res = client.post(
        "/api/v1/exam/autosave",
        json={"attempt_id": attempt_id, "question_id": data["question_id"], "selected_options": ["opt1"]},
        headers=headers
    )
    assert save_res.status_code == 200

    # 1st Violation
    v1_res = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "FULLSCREEN_EXIT"},
        headers=headers
    )
    assert v1_res.status_code == 200
    assert v1_res.json()["violation_count"] == 1

    # Wait for debounce window (1.6s)
    time.sleep(1.6)

    # 2nd Violation (Tab switch)
    v2_res = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "TAB_SWITCH"},
        headers=headers
    )
    assert v2_res.status_code == 200
    v2_data = v2_res.json()
    assert v2_data["violation_count"] == 2
    assert v2_data["auto_submitted"] is True
    assert v2_data["status"] == "AUTO_SUBMITTED_VIOLATION"


def test_after_auto_submit_returns_409(setup_database):
    data = setup_database
    headers = get_auth_headers(data["ase_id"])

    start_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    attempt_id = start_res.json()["attempt_id"]

    # 1st violation
    client.post(f"/api/v1/exam/violation/{attempt_id}", json={"type": "FULLSCREEN_EXIT"}, headers=headers)
    time.sleep(1.6)
    # 2nd violation (auto-submits)
    client.post(f"/api/v1/exam/violation/{attempt_id}", json={"type": "TAB_SWITCH"}, headers=headers)

    # 3. Subsequent autosave MUST return 409 Conflict
    save_after_close = client.post(
        "/api/v1/exam/autosave",
        json={"attempt_id": attempt_id, "question_id": data["question_id"], "selected_options": ["opt2"]},
        headers=headers
    )
    assert save_after_close.status_code == 409
    assert "already closed" in save_after_close.json()["detail"].lower()

    # 4. Subsequent violation request MUST return 409 Conflict
    viol_after_close = client.post(
        f"/api/v1/exam/violation/{attempt_id}",
        json={"type": "WINDOW_BLUR"},
        headers=headers
    )
    assert viol_after_close.status_code == 409
    assert "already closed" in viol_after_close.json()["detail"].lower()


def test_backend_source_of_truth_cannot_reset(setup_database):
    data = setup_database
    headers = get_auth_headers(data["ase_id"])

    start_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    attempt_id = start_res.json()["attempt_id"]

    # 1st violation
    client.post(f"/api/v1/exam/violation/{attempt_id}", json={"type": "FULLSCREEN_EXIT"}, headers=headers)

    # Resume exam (refresh) -> check violation_count is retained from backend (1)
    resume_res = client.post(f"/api/v1/exam/start/{data['assignment_id']}", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["violation_count"] == 1
