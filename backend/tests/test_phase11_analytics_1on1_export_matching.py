import io
import csv
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from app.main import app
from app.core.database import SessionLocal
from app.seed import init_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AssessmentResponse, AttemptStatus
from app.models.training import Training
from app.models.phase11_models import (
    OneOnOneMeeting, OneOnOneGoal, OneOnOneActionItem,
    ReportingApiToken, StaffingProject, StaffingProjectSkill
)
from app.services.note_encryption_service import decrypt_note, encrypt_note
from app.services.item_analysis_service import compute_question_analytics, get_or_compute_analytics
from app.services.matching_service import calculate_project_matches

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()


def _get_headers_for_user(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db: Session, email: str, role: UserRole) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            name=f"Test {role.value}",
            email=email,
            hashed_password=hash_password("Password@123"),
            role=role,
            is_active=True,
            is_demo=False
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


# ================= PART B TESTS: QUESTION ITEM ANALYSIS =================
def test_item_analysis_math_and_thresholds(db_session: Session):
    admin = _create_user(db_session, "admin_item_test@csm.tech", UserRole.ADMIN)
    headers = _get_headers_for_user(admin)

    # 1. Create Question
    q = QuestionBank(
        type=AssessmentType.LOGICAL_THINKING,
        difficulty=QuestionDifficulty.MEDIUM,
        skill_category="Deductive Logic",
        question_text="What is the time complexity of binary search?",
        question_type=QuestionType.SINGLE_CHOICE,
        options=[{"id": "opt1", "text": "O(log n)"}, {"id": "opt2", "text": "O(n)"}, {"id": "opt3", "text": "O(1)"}],
        correct_answers=["opt1"],
        marks=2,
        version=1,
        author_id=admin.id
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    # 2. When N < 10, no quality flags should be raised
    analytics_empty = get_or_compute_analytics(db_session, q.id, 1)
    assert analytics_empty.attempts_count == 0
    assert analytics_empty.is_too_easy is False
    assert analytics_empty.is_too_hard is False
    assert analytics_empty.is_poor_discrimination is False

    # 3. Simulate 35 attempts to test Discrimination Index and Difficulty Index
    # Create an assessment to link attempts
    ass = Assessment(
        title="Item Analysis Assessment",
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=30,
        passing_percentage=60.0,
        created_by=admin.id
    )
    db_session.add(ass)
    db_session.commit()
    db_session.refresh(ass)

    sec = AssessmentSection(assessment_id=ass.id, title="Section 1", order_index=1, timer_minutes=30)
    db_session.add(sec)
    db_session.commit()
    db_session.refresh(sec)

    db_session.add(AssessmentSectionQuestion(section_id=sec.id, question_id=q.id, order_index=1))
    db_session.commit()

    # Generate 35 attempts: Top 10 score 100% and got q correct; bottom 10 score 20% and got q wrong (opt2 chosen)
    now_utc = datetime.now(timezone.utc)
    for i in range(35):
        cand = _create_user(db_session, f"ase_item_{i}@csm.tech", UserRole.ASE)
        asg = AssessmentAssignment(
            assessment_id=ass.id,
            ase_id=cand.id,
            start_date=now_utc - timedelta(days=2),
            end_date=now_utc + timedelta(days=5)
        )
        db_session.add(asg)
        db_session.commit()
        db_session.refresh(asg)

        pct = 95.0 if i < 15 else 30.0
        is_corr = True if i < 20 else False
        sel_opt = ["opt1"] if is_corr else ["opt2"]

        att = AssessmentAttempt(
            assessment_assignment_id=asg.id,
            ase_id=cand.id,
            status=AttemptStatus.SUBMITTED,
            total_score=20.0 if is_corr else 5.0,
            max_score=20.0,
            percentage=pct,
            passed=is_corr
        )
        db_session.add(att)
        db_session.commit()
        db_session.refresh(att)

        resp = AssessmentResponse(
            attempt_id=att.id,
            question_id=q.id,
            selected_options=sel_opt,
            is_correct=is_corr,
            marks_obtained=2.0 if is_corr else 0.0,
            time_spent_seconds=25.0,
            question_version=1
        )
        db_session.add(resp)
    db_session.commit()

    # Recompute analytics
    analytics_computed = compute_question_analytics(db_session, q.id, 1)
    assert analytics_computed.attempts_count == 35
    assert analytics_computed.correct_count == 20
    assert analytics_computed.difficulty_index == round(20 / 35, 4)
    # Upper 27% (9 candidates) all got it correct, Lower 27% (9 candidates) all got it wrong -> D should be high positive (~1.0)
    assert analytics_computed.discrimination_index > 0.5
    assert analytics_computed.is_indicative_discrimination is False  # N >= 30, so confirmed!
    assert analytics_computed.most_chosen_wrong_option == "opt2"

    # 4. API endpoint verification
    res = client.get(f"/api/v1/analytics/questions/{q.id}", headers=headers)
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["attempts_count"] == 35
    assert json_data["most_chosen_wrong_option"] == "opt2"

    # 5. One-click send back to review
    rev_res = client.post(
        f"/api/v1/analytics/questions/{q.id}/review",
        json={"reason": "Rephrase distractor option 2."},
        headers=headers
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["needs_review"] is True
    assert rev_res.json()["review_reason"] == "Rephrase distractor option 2."


# ================= PART C TESTS: 1-ON-1 NOTES & PRIVACY =================
def test_one_on_one_mentor_notes_and_privacy_isolation(db_session: Session):
    mentor = _create_user(db_session, "mentor_1on1@csm.tech", UserRole.MENTOR)
    mentee = _create_user(db_session, "ase_1on1@csm.tech", UserRole.ASE)
    admin = _create_user(db_session, "admin_1on1@csm.tech", UserRole.ADMIN)
    other_mentor = _create_user(db_session, "other_mentor_1on1@csm.tech", UserRole.MENTOR)

    # Assign mentor to mentee
    asg = db_session.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == mentee.id).first()
    if not asg:
        db_session.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=mentee.id))
        db_session.commit()

    mentor_headers = _get_headers_for_user(mentor)
    mentee_headers = _get_headers_for_user(mentee)
    admin_headers = _get_headers_for_user(admin)
    other_mentor_headers = _get_headers_for_user(other_mentor)

    # 1. Mentor creates meeting with shared and private notes
    meet_payload = {
        "mentee_id": mentee.id,
        "title": "Quarterly Career Mentoring",
        "meeting_date": datetime.now(timezone.utc).isoformat(),
        "shared_notes": "Great progress on async python. Focus on test cases.",
        "private_notes": "Candidate seems fatigued by sprint deadlines; watch for burnout."
    }
    create_res = client.post("/api/v1/one-on-one/meetings", json=meet_payload, headers=mentor_headers)
    assert create_res.status_code == 200
    meeting_data = create_res.json()
    meeting_id = meeting_data["id"]

    # Verify that in database, private note is encrypted
    db_meeting = db_session.query(OneOnOneMeeting).filter(OneOnOneMeeting.id == meeting_id).first()
    assert db_meeting.encrypted_private_notes != meet_payload["private_notes"]
    assert decrypt_note(db_meeting.encrypted_private_notes) == meet_payload["private_notes"]

    # 2. Mentor views meeting: gets decrypted private notes
    m_res = client.get(f"/api/v1/one-on-one/meetings/{meeting_id}", headers=mentor_headers)
    assert m_res.status_code == 200
    assert m_res.json()["private_notes"] == meet_payload["private_notes"]
    assert m_res.json()["shared_notes"] == meet_payload["shared_notes"]

    # 3. Mentee (ASE) views meeting: shared notes visible, private notes are NULL / masked!
    ase_res = client.get(f"/api/v1/one-on-one/meetings/{meeting_id}", headers=mentee_headers)
    assert ase_res.status_code == 200
    assert ase_res.json()["shared_notes"] == meet_payload["shared_notes"]
    assert ase_res.json()["private_notes"] is None

    # 4. Admin views meeting: private notes are NULL / masked!
    adm_res = client.get(f"/api/v1/one-on-one/meetings/{meeting_id}", headers=admin_headers)
    assert adm_res.status_code == 200
    assert adm_res.json()["private_notes"] is None

    # 5. Unauthorized mentor gets 403 Forbidden
    unauth_res = client.get(f"/api/v1/one-on-one/meetings/{meeting_id}", headers=other_mentor_headers)
    assert unauth_res.status_code == 403

    # 6. Action item checklist workflow
    act_res = client.post("/api/v1/one-on-one/actions", json={
        "mentee_id": mentee.id,
        "task": "Review gRPC error handling specs",
        "assigned_to": "ASE",
        "meeting_id": meeting_id
    }, headers=mentor_headers)
    assert act_res.status_code == 200
    action_id = act_res.json()["id"]

    # Mentee ticks the action item
    toggle_res = client.patch(f"/api/v1/one-on-one/actions/{action_id}/toggle?is_completed=true", headers=mentee_headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_completed"] is True
    assert toggle_res.json()["completed_at"] is not None

    # 7. AI summary of meeting
    sum_res = client.post(
        f"/api/v1/one-on-one/meetings/{meeting_id}/summarize",
        json={"target": "shared"},
        headers=mentor_headers
    )
    assert sum_res.status_code == 200
    assert "[AI-Generated Summary, Please Verify]" in sum_res.json()["summary"]


# ================= PART D TESTS: EXPORT & FORMULA INJECTION =================
def test_export_formula_injection_and_role_scoping(db_session: Session):
    admin = _create_user(db_session, "admin_exp@csm.tech", UserRole.ADMIN)
    mentor = _create_user(db_session, "mentor_exp@csm.tech", UserRole.MENTOR)
    mentee = _create_user(db_session, "ase_exp@csm.tech", UserRole.ASE)

    # Assign mentor to mentee
    if not db_session.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == mentee.id).first():
        db_session.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=mentee.id))
        db_session.commit()

    # Create assessment with potential dangerous formula title: "=SUM(1,2)*cmd|' /C calc'!A0"
    ass_malicious = Assessment(
        title="=SUM(1,2)*cmd|' /C calc'!A0",
        type=AssessmentType.APTITUDE,
        total_duration_minutes=25,
        passing_percentage=50.0,
        created_by=admin.id
    )
    db_session.add(ass_malicious)
    db_session.commit()

    admin_headers = _get_headers_for_user(admin)
    mentor_headers = _get_headers_for_user(mentor)
    ase_headers = _get_headers_for_user(mentee)

    # 1. ASE cannot export data (403 Forbidden)
    ase_exp = client.get("/api/v1/export/assessments?format=csv", headers=ase_headers)
    assert ase_exp.status_code == 403

    # 2. Admin CSV export escapes dangerous formula prefix with single quote
    csv_res = client.get("/api/v1/export/assessments?format=csv", headers=admin_headers)
    assert csv_res.status_code == 200
    csv_text = csv_res.text
    # Check that dangerous '=' is escaped as "'="
    assert "'=SUM(1,2)" in csv_text

    # 3. Excel export test (.xlsx)
    xlsx_res = client.get("/api/v1/export/assessments?format=xlsx", headers=admin_headers)
    assert xlsx_res.status_code == 200
    assert xlsx_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    wb = load_workbook(io.BytesIO(xlsx_res.content))
    sheet = wb.active
    # Find cell containing formula
    found_escaped = False
    for row in sheet.iter_rows(values_only=True):
        for cell_val in row:
            if isinstance(cell_val, str) and cell_val.startswith("'=SUM"):
                found_escaped = True
                break
    assert found_escaped is True

    # 4. Pseudonymous IDs by default vs include_pii=True
    res_default = client.get("/api/v1/export/results?format=csv&include_pii=false", headers=admin_headers)
    assert res_default.status_code == 200
    assert "Candidate ID" in res_default.text
    assert "Candidate Email" not in res_default.text  # PII stripped!

    res_pii = client.get("/api/v1/export/results?format=csv&include_pii=true", headers=admin_headers)
    assert res_pii.status_code == 200
    assert "Candidate Email" in res_pii.text  # PII included upon explicit opt-in


# ================= PART D TESTS: REPORTING API TOKEN FOR POWER BI =================
def test_reporting_api_token_power_bi_integration(db_session: Session):
    admin = _create_user(db_session, "admin_rpt@csm.tech", UserRole.ADMIN)
    admin_headers = _get_headers_for_user(admin)

    # 1. Admin generates reporting token
    tok_payload = {
        "name": "Power BI Executive Dashboard",
        "scopes": ["assessments", "results"],
        "include_pii": False,
        "expires_in_days": 90
    }
    tok_res = client.post("/api/v1/reporting/tokens", json=tok_payload, headers=admin_headers)
    assert tok_res.status_code == 200
    tok_data = tok_res.json()
    raw_token = tok_data["token"]
    assert raw_token.startswith("rpt_")

    # 2. Token must be sent in Authorization header ONLY (URL query param must fail)
    query_param_res = client.get(f"/api/v1/reporting/assessments?token={raw_token}")
    assert query_param_res.status_code == 400

    # 3. Successful fetch using Bearer header
    rpt_headers = {"Authorization": f"Bearer {raw_token}"}
    data_res = client.get("/api/v1/reporting/assessments", headers=rpt_headers)
    assert data_res.status_code == 200
    data_list = data_res.json()
    assert isinstance(data_list, list)

    # 4. Scope rejection: token has 'assessments' and 'results', not 'attendance'
    unscoped_res = client.get("/api/v1/reporting/attendance", headers=rpt_headers)
    assert unscoped_res.status_code == 403

    # 5. Token revocation
    del_res = client.delete(f"/api/v1/reporting/tokens/{tok_data['id']}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["is_revoked"] is True

    # After revocation, token returns 401 Unauthorized
    revoked_res = client.get("/api/v1/reporting/assessments", headers=rpt_headers)
    assert revoked_res.status_code == 401


# ================= PART E TESTS: SKILL-TO-PROJECT MATCHING =================
def test_skill_to_project_matching_and_scoping(db_session: Session):
    admin = _create_user(db_session, "admin_match@csm.tech", UserRole.ADMIN)
    mentor = _create_user(db_session, "mentor_match@csm.tech", UserRole.MENTOR)
    mentee = _create_user(db_session, "ase_match@csm.tech", UserRole.ASE)
    unassigned_ase = _create_user(db_session, "ase_unassigned@csm.tech", UserRole.ASE)

    # Assign mentor to mentee
    if not db_session.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == mentee.id).first():
        db_session.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=mentee.id))
        db_session.commit()

    # Create dummy training module in database for gap matching
    tr = db_session.query(Training).filter(Training.title == "Advanced Async Python").first()
    if not tr:
        tr = Training(
            title="Advanced Async Python",
            description="Deep dive into Python coroutines and async architectures.",
            skill_category="Deductive Logic",
            created_by=admin.id
        )
        db_session.add(tr)
        db_session.commit()

    # Give mentee a completed attempt with known skill percentage
    ass = Assessment(title="Skill Assessment", type=AssessmentType.LOGICAL_THINKING, total_duration_minutes=20, passing_percentage=60.0, created_by=admin.id)
    db_session.add(ass)
    db_session.commit()

    asg = AssessmentAssignment(assessment_id=ass.id, ase_id=mentee.id, start_date=datetime.now(timezone.utc) - timedelta(days=5), end_date=datetime.now(timezone.utc) + timedelta(days=5))
    db_session.add(asg)
    db_session.commit()

    att = AssessmentAttempt(
        assessment_assignment_id=asg.id,
        ase_id=mentee.id,
        status=AttemptStatus.SUBMITTED,
        percentage=80.0,
        skill_percentages={"deductive logic": 80.0, "system architecture": 60.0}
    )
    db_session.add(att)
    db_session.commit()

    admin_headers = _get_headers_for_user(admin)
    mentor_headers = _get_headers_for_user(mentor)
    ase_headers = _get_headers_for_user(mentee)

    # 1. Admin creates staffing project
    proj_payload = {
        "name": "Cloud Native Modernization",
        "headcount": 2,
        "start_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "ready_now_threshold_pct": 90.0,
        "skills": [
            {"skill_name": "Deductive Logic", "min_level_pct": 80.0, "weight": 1.0},
            {"skill_name": "System Architecture", "min_level_pct": 80.0, "weight": 1.0}
        ]
    }
    proj_res = client.post("/api/v1/staffing/projects", json=proj_payload, headers=admin_headers)
    assert proj_res.status_code == 200
    project_id = proj_res.json()["id"]

    # 2. ASE cannot access project matching (403 Forbidden)
    ase_res = client.get(f"/api/v1/staffing/projects/{project_id}/matches", headers=ase_headers)
    assert ase_res.status_code == 403

    # 3. Mentor accesses project matching: sees ONLY assigned mentee!
    m_res = client.get(f"/api/v1/staffing/projects/{project_id}/matches", headers=mentor_headers)
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert m_data["disclaimer"] == "Decision support only. Not a basis for staffing, promotion or termination decisions."
    
    cand_ids = [c["candidate_id"] for c in m_data["candidates"]]
    assert mentee.id in cand_ids
    assert unassigned_ase.id not in cand_ids  # Mentor isolation verified!

    # 4. Match percentage verification:
    # Required: Deductive Logic (min 80, wt 1.0), System Architecture (min 80, wt 1.0) -> Denom = 160
    # Candidate: Deductive Logic 80 (min(80, 80) = 80), System Architecture 60 (min(60, 80) = 60) -> Numer = 140
    # Expected match % = (140 / 160) * 100 = 87.5%
    # Since 87.5% < 90.0% (ready now threshold), candidate is labeled "Ready in 1 week"
    mentee_match = next(c for c in m_data["candidates"] if c["candidate_id"] == mentee.id)
    assert mentee_match["match_percentage"] == 87.5
    assert mentee_match["is_ready_now"] is False
    assert "Ready in" in mentee_match["readiness_label"]
    assert mentee_match["formula_breakdown"]["weighted_numerator"] == 140.0
    assert mentee_match["formula_breakdown"]["weighted_denominator"] == 160.0
