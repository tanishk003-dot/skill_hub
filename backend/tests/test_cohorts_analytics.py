import pytest
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.cohort import Cohort, CohortMember
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.services.insights_service import insights_service
from app.api.reports import sanitize_csv_cell

import time
from app.core.database import SessionLocal
from app.seed import init_db

client = TestClient(app)

def get_auth_headers(user_id: int, role: str):
    token = create_access_token(subject=str(user_id), role=role)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def setup_database():
    db = SessionLocal()
    ts = str(int(time.time() * 1000))

    # 1. Admin
    admin = User(name=f"Admin {ts}", email=f"admin_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ADMIN, is_active=True)
    db.add(admin)

    # 2. Mentor 1 & Mentor 2
    mentor1 = User(name=f"Mentor One {ts}", email=f"mentor1_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    mentor2 = User(name=f"Mentor Two {ts}", email=f"mentor2_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db.add(mentor1)
    db.add(mentor2)

    # 3. ASE 1 (assigned to mentor1), ASE 2 (assigned to mentor2), ASE 3 (no attempts)
    ase1 = User(name="ASE One", email=f"ase1_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    ase2 = User(name="ASE Two", email=f"ase2_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    ase3 = User(name="ASE Three", email=f"ase3_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db.add(ase1)
    db.add(ase2)
    db.add(ase3)
    db.commit()

    db.add(MentorAseAssignment(mentor_id=mentor1.id, ase_id=ase1.id))
    db.add(MentorAseAssignment(mentor_id=mentor2.id, ase_id=ase2.id))
    db.add(MentorAseAssignment(mentor_id=mentor1.id, ase_id=ase3.id))
    db.commit()

    # 4. Cohort
    cohort = Cohort(name="Batch 2026", start_date=date(2026, 1, 1), created_by=admin.id)
    db.add(cohort)
    db.commit()
    db.refresh(cohort)

    db.add(CohortMember(cohort_id=cohort.id, ase_id=ase1.id))
    db.add(CohortMember(cohort_id=cohort.id, ase_id=ase2.id))
    db.commit()

    # 5. Assessment & Attempts
    assessment = Assessment(title="Analytics Test Assessment", type=AssessmentType.LOGICAL_THINKING, total_duration_minutes=30, passing_percentage=60.0)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    now_utc = datetime.now(timezone.utc)
    # Assignment & attempt for ASE 1
    asg1 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase1.id, cohort_id=cohort.id, start_date=now_utc - timedelta(days=2), end_date=now_utc + timedelta(days=5))
    db.add(asg1)
    db.commit()
    db.refresh(asg1)

    att1 = AssessmentAttempt(
        assessment_assignment_id=asg1.id,
        ase_id=ase1.id,
        started_at=now_utc - timedelta(days=1),
        submitted_at=now_utc - timedelta(days=1, minutes=-20),
        status=AttemptStatus.SUBMITTED,
        total_score=16.0,
        max_score=20.0,
        percentage=80.0,
        passed=True,
        violation_count=0,
        skill_percentages={"Deductive Logic": 90.0, "Pattern Recognition": 40.0, "Quantitative Aptitude": 60.0},
        strong_areas=["Deductive Logic"],
        weak_areas=["Pattern Recognition", "Quantitative Aptitude"]
    )
    db.add(att1)

    # Assignment & attempt for ASE 2
    asg2 = AssessmentAssignment(assessment_id=assessment.id, ase_id=ase2.id, cohort_id=cohort.id, start_date=now_utc - timedelta(days=2), end_date=now_utc + timedelta(days=5))
    db.add(asg2)
    db.commit()
    db.refresh(asg2)

    att2 = AssessmentAttempt(
        assessment_assignment_id=asg2.id,
        ase_id=ase2.id,
        started_at=now_utc - timedelta(hours=10),
        submitted_at=now_utc - timedelta(hours=9),
        status=AttemptStatus.SUBMITTED,
        total_score=10.0,
        max_score=20.0,
        percentage=50.0,
        passed=False,
        violation_count=1,
        skill_percentages={"Deductive Logic": 45.0, "Pattern Recognition": 50.0, "Quantitative Aptitude": 55.0},
        strong_areas=[],
        weak_areas=["Deductive Logic", "Pattern Recognition", "Quantitative Aptitude"]
    )
    db.add(att2)
    db.commit()

    yield {
        "admin_id": admin.id,
        "mentor1_id": mentor1.id,
        "mentor2_id": mentor2.id,
        "ase1_id": ase1.id,
        "ase2_id": ase2.id,
        "ase3_id": ase3.id,
        "cohort_id": cohort.id,
        "att1_id": att1.id,
        "att2_id": att2.id
    }

    db.close()


# --- 1. Cohort CRUD & Cascade Safety Tests ---

def test_cohort_creation_and_membership(setup_database):
    data = setup_database
    admin_hdr = get_auth_headers(data["admin_id"], "ADMIN")

    # Create new cohort
    res = client.post("/api/v1/cohorts", json={
        "name": f"New Spring Cohort {time.time()}",
        "description": "Spring engineering batch",
        "start_date": "2026-03-01"
    }, headers=admin_hdr)
    assert res.status_code == 201
    cohort_id = res.json()["id"]

    # Add ASE3 to this cohort
    add_res = client.post(f"/api/v1/cohorts/{cohort_id}/members", json={"ase_ids": [data["ase3_id"]]}, headers=admin_hdr)
    assert add_res.status_code == 200
    assert add_res.json()["member_count"] == 1

    # Remove ASE3 from this cohort
    del_res = client.delete(f"/api/v1/cohorts/{cohort_id}/members/{data['ase3_id']}", headers=admin_hdr)
    assert del_res.status_code == 204


def test_delete_cohort_preserves_users_and_attempts(setup_database):
    """
    Requirement 1: Deleting a cohort must only remove cohort_members rows
    (and set cohort_id NULL on assignments). Never delete ASE users, attempts or results.
    """
    data = setup_database
    admin_hdr = get_auth_headers(data["admin_id"], "ADMIN")

    del_res = client.delete(f"/api/v1/cohorts/{data['cohort_id']}", headers=admin_hdr)
    assert del_res.status_code == 204

    # Verify ASE users still exist
    ase1_res = client.get(f"/api/v1/users/{data['ase1_id']}", headers=admin_hdr)
    assert ase1_res.status_code == 200
    assert ase1_res.json()["name"] == "ASE One"

    # Verify attempt still exists
    att1_res = client.get(f"/api/v1/exam/result/{data['att1_id']}", headers=admin_hdr)
    assert att1_res.status_code == 200
    assert att1_res.json()["total_score"] == 16.0


# --- 2. Permission Tests (403 Enforcement) ---

def test_report_permissions_403_enforcement(setup_database):
    """
    Requirement 3: An ASE can download only their own PDF, a mentor only their mentees' PDF/CSV,
    admin everything. Return 403 otherwise.
    """
    data = setup_database
    ase1_hdr = get_auth_headers(data["ase1_id"], "ASE")
    ase2_hdr = get_auth_headers(data["ase2_id"], "ASE")
    mentor1_hdr = get_auth_headers(data["mentor1_id"], "MENTOR")
    mentor2_hdr = get_auth_headers(data["mentor2_id"], "MENTOR")
    admin_hdr = get_auth_headers(data["admin_id"], "ADMIN")

    # 1. ASE 1 downloading own PDF -> 200 OK
    res = client.get(f"/api/v1/reports/ase/{data['att1_id']}/pdf", headers=ase1_hdr)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"

    # 2. ASE 1 downloading ASE 2's PDF -> 403 Forbidden
    res = client.get(f"/api/v1/reports/ase/{data['att2_id']}/pdf", headers=ase1_hdr)
    assert res.status_code == 403

    # 3. ASE attempting cohort CSV -> 403 Forbidden
    res = client.get(f"/api/v1/reports/cohort/{data['cohort_id']}/csv", headers=ase1_hdr)
    assert res.status_code == 403

    # 4. Mentor 1 downloading Mentee 1's PDF -> 200 OK
    res = client.get(f"/api/v1/reports/ase/{data['att1_id']}/pdf", headers=mentor1_hdr)
    assert res.status_code == 200

    # 5. Mentor 1 downloading Mentee 2's PDF (belongs to mentor2) -> 403 Forbidden
    res = client.get(f"/api/v1/reports/ase/{data['att2_id']}/pdf", headers=mentor1_hdr)
    assert res.status_code == 403

    # 6. Admin can download any -> 200 OK
    res = client.get(f"/api/v1/reports/ase/{data['att2_id']}/pdf", headers=admin_hdr)
    assert res.status_code == 200


# --- 3. CSV Injection Sanitization Test ---

def test_csv_injection_mitigation():
    """
    Requirement 4: Escape cells starting with = + - @ (prefix with single quote)
    """
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-5+2") == "'-5+2"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("Normal Student Name") == "Normal Student Name"
    assert sanitize_csv_cell(None) == ""


# --- 4. Insights Service Unit Tests ---

def test_insights_service_rules():
    """
    Requirement 7: Insights logic: <50% = HIGH priority, 50-70% = MEDIUM priority, >=70% = strength.
    """
    skills = {
        "Deductive Logic": 40.0,
        "Pattern Recognition": 65.0,
        "Quantitative Aptitude": 85.0
    }
    result = insights_service.generate_candidate_improvements(skills)
    assert "Quantitative Aptitude" in result["strong_areas"]
    assert "Deductive Logic" in result["weak_areas"]
    assert "Pattern Recognition" in result["weak_areas"]

    # Improvements priority
    improvements = result["improvements"]
    assert len(improvements) == 2
    # First must be HIGH priority (Deductive Logic at 40%)
    assert improvements[0]["skill"] == "Deductive Logic"
    assert improvements[0]["priority"] == "HIGH"
    # Second must be MEDIUM priority (Pattern Recognition at 65%)
    assert improvements[1]["skill"] == "Pattern Recognition"
    assert improvements[1]["priority"] == "MEDIUM"


# --- 5. Zero-Attempt & Mentor Isolation Dashboard Tests ---

def test_mentor_dashboard_isolation_and_zero_attempts(setup_database):
    """
    Requirement 2 & 6: Mentors see only their own mentees.
    Zero-attempt ASEs (ASE 3) must be handled gracefully without division by zero.
    """
    data = setup_database
    mentor1_hdr = get_auth_headers(data["mentor1_id"], "MENTOR")

    res = client.get("/api/v1/analytics/mentor/dashboard", headers=mentor1_hdr)
    assert res.status_code == 200
    dash = res.json()

    # Ranking table must only contain mentor1's mentees (ASE 1 and ASE 3)
    ranking_names = [row["ase_name"] for row in dash["ranking_table"]]
    assert "ASE One" in ranking_names
    assert "ASE Three" in ranking_names
    assert "ASE Two" not in ranking_names  # ASE Two belongs to mentor 2!

    # ASE Three has no attempts -> must display has_attempt: false without crashing
    ase3_row = next(r for r in dash["ranking_table"] if r["ase_name"] == "ASE Three")
    assert ase3_row["has_attempt"] is False
    assert ase3_row["attempts_count"] == 0


# --- 6. ASE Search & Pagination Test ---

def test_ase_search_pagination(setup_database):
    """
    Requirement 7: Paginate ASE search endpoint (page, page_size).
    """
    data = setup_database
    admin_hdr = get_auth_headers(data["admin_id"], "ADMIN")

    res = client.get("/api/v1/cohorts/search/ases?page=1&page_size=2", headers=admin_hdr)
    assert res.status_code == 200
    p = res.json()
    assert p["page"] == 1
    assert p["page_size"] == 2
    assert len(p["items"]) == 2
    assert p["total"] >= 3
    assert p["total_pages"] >= 2
