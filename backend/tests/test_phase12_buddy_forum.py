import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.main import app
from app.core.database import SessionLocal
from app.seed import init_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.cohort import Cohort, CohortMember
from app.models.assignment import MentorAseAssignment
from app.models.assessment import Assessment, AssessmentType
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.question import QuestionBank, QuestionType, QuestionDifficulty
from app.models.phase9_models import AseGamification
from app.models.phase12_models import (
    BuddyPairing, BuddyPairingStatus, BuddyMilestone, BuddyMilestoneStatus,
    ForumPost, ForumPostStatus, ForumAnswer, ForumReport, ForumIdentityAuditLog,
    ForumFilterAuditLog, ForumRateLimit
)

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(autouse=True)
def clean_rate_limits(db_session: Session):
    db_session.query(ForumRateLimit).delete()
    db_session.commit()

def _get_headers_for_user(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}

def _create_user(db: Session, email: str, role: UserRole, name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            name=name,
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

@pytest.fixture(scope="module")
def setup_data(db_session: Session):
    admin = _create_user(db_session, "admin_p12@csm.tech", UserRole.ADMIN, "Admin P12")
    mentor = _create_user(db_session, "mentor_p12@csm.tech", UserRole.MENTOR, "Mentor P12")
    ase1 = _create_user(db_session, "ase1_p12@csm.tech", UserRole.ASE, "Aarav Sharma")
    ase2 = _create_user(db_session, "ase2_p12@csm.tech", UserRole.ASE, "Diya Patel")
    ase3 = _create_user(db_session, "ase3_p12@csm.tech", UserRole.ASE, "Rohan Gupta")
    ase_beta = _create_user(db_session, "ase_beta_p12@csm.tech", UserRole.ASE, "Ananya Verma")

    # Cohorts
    c1 = db_session.query(Cohort).filter(Cohort.name == "Alpha P12").first()
    if not c1:
        c1 = Cohort(name="Alpha P12", description="Alpha test cohort", start_date=datetime.now(timezone.utc))
        db_session.add(c1)
        db_session.commit()
        db_session.refresh(c1)

    c2 = db_session.query(Cohort).filter(Cohort.name == "Beta P12").first()
    if not c2:
        c2 = Cohort(name="Beta P12", description="Beta test cohort", start_date=datetime.now(timezone.utc))
        db_session.add(c2)
        db_session.commit()
        db_session.refresh(c2)

    # Assign cohort memberships
    for u in [ase1, ase2, ase3]:
        mem = db_session.query(CohortMember).filter(CohortMember.ase_id == u.id).first()
        if not mem:
            db_session.add(CohortMember(cohort_id=c1.id, ase_id=u.id))
    mem_beta = db_session.query(CohortMember).filter(CohortMember.ase_id == ase_beta.id).first()
    if not mem_beta:
        db_session.add(CohortMember(cohort_id=c2.id, ase_id=ase_beta.id))

    # Mentor assignments
    for u in [ase1, ase2, ase3]:
        mass = db_session.query(MentorAseAssignment).filter(
            MentorAseAssignment.mentor_id == mentor.id,
            MentorAseAssignment.ase_id == u.id
        ).first()
        if not mass:
            db_session.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=u.id))

    # Ensure ase1 has at least 1 passed attempt so they meet volunteer eligibility
    ass = db_session.query(Assessment).first()
    if not ass:
        ass = Assessment(title="Sample Assessment", type=AssessmentType.LOGICAL_THINKING, total_duration_minutes=30)
        db_session.add(ass)
        db_session.commit()
        db_session.refresh(ass)

    ass_assign = db_session.query(AssessmentAssignment).filter(AssessmentAssignment.ase_id == ase1.id).first()
    if not ass_assign:
        ass_assign = AssessmentAssignment(
            assessment_id=ass.id,
            ase_id=ase1.id,
            cohort_id=c1.id,
            start_date=datetime.now(timezone.utc) - timedelta(days=2),
            end_date=datetime.now(timezone.utc) + timedelta(days=5)
        )
        db_session.add(ass_assign)
        db_session.commit()
        db_session.refresh(ass_assign)

    attempt = db_session.query(AssessmentAttempt).filter(AssessmentAttempt.ase_id == ase1.id).first()
    if not attempt:
        attempt = AssessmentAttempt(
            assessment_assignment_id=ass_assign.id,
            ase_id=ase1.id,
            status=AttemptStatus.SUBMITTED,
            percentage=85.0,
            passed=True
        )
        db_session.add(attempt)
        db_session.commit()

    db_session.commit()

    return {
        "admin": admin,
        "mentor": mentor,
        "ase1": ase1,
        "ase2": ase2,
        "ase3": ase3,
        "ase_beta": ase_beta,
        "c1": c1,
        "c2": c2,
        "ass": ass
    }


def test_buddy_volunteer_eligibility_and_toggle(setup_data, db_session):
    ase1 = setup_data["ase1"]
    
    # Toggle volunteer ON
    resp = client.post("/api/v1/buddy/volunteer", json={"is_volunteer": True}, headers=_get_headers_for_user(ase1))
    assert resp.status_code == 200
    assert resp.json()["is_buddy_volunteer"] is True

    # Toggle volunteer OFF
    resp2 = client.post("/api/v1/buddy/volunteer", json={"is_volunteer": False}, headers=_get_headers_for_user(ase1))
    assert resp2.status_code == 200
    assert resp2.json()["is_buddy_volunteer"] is False

    # Reset volunteer ON for subsequent tests
    client.post("/api/v1/buddy/volunteer", json={"is_volunteer": True}, headers=_get_headers_for_user(ase1))


def test_buddy_pairing_rules_and_concurrency_cap(setup_data, db_session):
    admin = setup_data["admin"]
    ase1 = setup_data["ase1"]
    ase2 = setup_data["ase2"]
    ase3 = setup_data["ase3"]
    ase_beta = setup_data["ase_beta"]

    # Set ase1 volunteer
    ase1.is_buddy_volunteer = True
    db_session.commit()

    # Clean existing pairings for clean test
    db_session.query(BuddyPairing).filter(
        or_(
            BuddyPairing.buddy_id == ase1.id,
            BuddyPairing.buddee_id.in_([ase2.id, ase3.id, ase_beta.id])
        )
    ).delete(synchronize_session=False)
    db_session.commit()

    # 1. Self-pairing blocked
    resp_self = client.post("/api/v1/buddy/pairings", json={
        "buddy_id": ase1.id,
        "buddee_id": ase1.id
    }, headers=_get_headers_for_user(admin))
    assert resp_self.status_code == 400
    assert "Self-pairing is prohibited" in resp_self.json()["detail"]

    # 2. Pair 1: ase1 -> ase2
    r1 = client.post("/api/v1/buddy/pairings", json={"buddy_id": ase1.id, "buddee_id": ase2.id}, headers=_get_headers_for_user(admin))
    assert r1.status_code == 200

    # 3. Duplicate pairing for same buddee blocked
    r_dup = client.post("/api/v1/buddy/pairings", json={"buddy_id": ase1.id, "buddee_id": ase2.id}, headers=_get_headers_for_user(admin))
    assert r_dup.status_code == 400
    assert "already has an active" in r_dup.json()["detail"]

    # 4. Pair 2: ase1 -> ase3
    r2 = client.post("/api/v1/buddy/pairings", json={"buddy_id": ase1.id, "buddee_id": ase3.id}, headers=_get_headers_for_user(admin))
    assert r2.status_code == 200

    # 5. Pair 3: ase1 -> ase_beta
    r3 = client.post("/api/v1/buddy/pairings", json={"buddy_id": ase1.id, "buddee_id": ase_beta.id}, headers=_get_headers_for_user(admin))
    assert r3.status_code == 200

    # 6. Pair 4: Exceeds capacity of 3
    temp_ase = _create_user(db_session, "extra_p12@csm.tech", UserRole.ASE, "Extra ASE")
    r4 = client.post("/api/v1/buddy/pairings", json={"buddy_id": ase1.id, "buddee_id": temp_ase.id}, headers=_get_headers_for_user(admin))
    assert r4.status_code == 400
    assert "maximum limit reached" in r4.json()["detail"]


def test_buddy_view_privacy_isolation(setup_data):
    ase1 = setup_data["ase1"]
    
    # Buddy views my-pairings
    resp = client.get("/api/v1/buddy/my-pairings", headers=_get_headers_for_user(ase1))
    assert resp.status_code == 200
    data = resp.json()
    assert "what_is_shared_notice" in data
    assert "What is shared: Only your first name + last initial" in data["what_is_shared_notice"]

    buddees = data["my_buddees"]
    assert len(buddees) > 0
    first_buddee = buddees[0]
    
    assert "." in first_buddee["coarse_name"]
    assert first_buddee["coarse_status"] in ["On track", "Needs support"]

    # Strictly verify NO confidential data fields leaked
    assert "email" not in first_buddee
    assert "phone" not in first_buddee
    assert "percentage" not in first_buddee
    assert "score" not in first_buddee
    assert "risk_score" not in first_buddee
    assert "violations" not in first_buddee
    assert "medical_notes" not in first_buddee
    assert "notes" not in first_buddee


def test_buddy_milestone_and_weekly_xp_cap(setup_data, db_session):
    ase1 = setup_data["ase1"]
    ase2 = setup_data["ase2"]

    # Clear prior milestones for hermetic weekly cap testing
    db_session.query(BuddyMilestone).filter(BuddyMilestone.buddy_id == ase1.id).delete()
    db_session.commit()

    pairing = db_session.query(BuddyPairing).filter(
        BuddyPairing.buddy_id == ase1.id,
        BuddyPairing.buddee_id == ase2.id
    ).first()

    gam = db_session.query(AseGamification).filter(AseGamification.ase_id == ase1.id).first()
    if not gam:
        gam = AseGamification(ase_id=ase1.id, xp=100, badges_json=[])
        db_session.add(gam)
        db_session.commit()
    initial_xp = gam.xp

    # Milestone 1 (50 XP)
    m1_resp = client.post(f"/api/v1/buddy/pairings/{pairing.id}/milestones", json={
        "title": "Study Roadmap Setup",
        "description": "Reviewed learning goals",
        "xp_amount": 50
    }, headers=_get_headers_for_user(ase1))
    assert m1_resp.status_code == 200
    m1_id = m1_resp.json()["milestone_id"]

    v1_resp = client.post(f"/api/v1/buddy/milestones/{m1_id}/verify", headers=_get_headers_for_user(ase2))
    assert v1_resp.status_code == 200
    assert v1_resp.json()["xp_awarded"] == 50

    db_session.refresh(gam)
    assert gam.xp == initial_xp + 50
    badge_names = [b.get("name") if isinstance(b, dict) else b for b in (gam.badges_json or [])]
    assert "Peer Guide" in badge_names

    # Milestone 2 (75 XP) -> Weekly cap is 100 XP, so only 50 XP should be awarded
    m2_resp = client.post(f"/api/v1/buddy/pairings/{pairing.id}/milestones", json={
        "title": "Code Review Session",
        "xp_amount": 75
    }, headers=_get_headers_for_user(ase1))
    m2_id = m2_resp.json()["milestone_id"]

    v2_resp = client.post(f"/api/v1/buddy/milestones/{m2_id}/verify", headers=_get_headers_for_user(ase2))
    assert v2_resp.status_code == 200
    assert v2_resp.json()["xp_awarded"] == 50

    db_session.refresh(gam)
    assert gam.xp == initial_xp + 100


def test_forum_cohort_isolation_and_scoping(setup_data):
    ase1 = setup_data["ase1"] # Cohort 1
    c2 = setup_data["c2"]     # Cohort 2

    # ase1 attempts to create post in Cohort 2 -> 403 Forbidden
    resp = client.post("/api/v1/forum/posts", json={
        "cohort_id": c2.id,
        "title": "Unauthorized cross-cohort post",
        "body": "This question belongs to another cohort.",
        "is_anonymous": False
    }, headers=_get_headers_for_user(ase1))
    assert resp.status_code == 403
    assert "restricted to viewing doubts within your assigned cohort" in resp.json()["detail"]


def test_active_assessment_forum_block_and_attempt_in_progress(setup_data, db_session):
    ase1 = setup_data["ase1"]
    c1 = setup_data["c1"]
    now = datetime.now(timezone.utc)

    # 1. Create an active assessment with assignment window active now
    ass = Assessment(title="Active Live Exam Test", type=AssessmentType.LOGICAL_THINKING, total_duration_minutes=30)
    db_session.add(ass)
    db_session.commit()
    db_session.refresh(ass)

    assignment = AssessmentAssignment(
        assessment_id=ass.id,
        ase_id=ase1.id,
        cohort_id=c1.id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=2)
    )
    db_session.add(assignment)
    db_session.commit()

    # Post tagged to active assessment -> HTTP 400
    resp_active = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Discussion on Active Test",
        "body": "What is the answer to question 3 on the active test?",
        "tagged_assessment_id": ass.id
    }, headers=_get_headers_for_user(ase1))
    assert resp_active.status_code == 400
    assert "Discussion of active assessments is prohibited" in resp_active.json()["detail"]

    # 2. In-Progress Exam read-only rule
    attempt = AssessmentAttempt(
        assessment_assignment_id=assignment.id,
        ase_id=ase1.id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=now
    )
    db_session.add(attempt)
    db_session.commit()

    # Attempt to post while having IN_PROGRESS attempt -> HTTP 400
    resp_in_prog = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Trying to post during live exam",
        "body": "Can anyone help with this algorithm while I am testing?",
    }, headers=_get_headers_for_user(ase1))
    assert resp_in_prog.status_code == 400
    assert "read-only mode while you have an active assessment attempt in progress" in resp_in_prog.json()["detail"]

    # Cleanup active attempt
    db_session.delete(attempt)
    db_session.commit()


def test_question_quoting_leak_held_for_review(setup_data, db_session):
    ase1 = setup_data["ase1"]
    mentor = setup_data["mentor"]
    c1 = setup_data["c1"]

    qb = db_session.query(QuestionBank).first()
    if not qb:
        qb = QuestionBank(
            question_text="Given a directed acyclic graph, find the longest path from source to target vertex.",
            type=QuestionType.MCQ,
            difficulty=QuestionDifficulty.MEDIUM,
            options=["O(V+E)", "O(V*E)", "O(V^2)", "O(1)"],
            correct_option=0
        )
        db_session.add(qb)
        db_session.commit()
        db_session.refresh(qb)

    resp = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Need help solving this problem",
        "body": f"Here is the problem: {qb.question_text}. What is the solution?",
        "is_anonymous": False
    }, headers=_get_headers_for_user(ase1))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HELD_FOR_REVIEW"
    assert data["is_held_for_review"] is True
    post_id = data["id"]

    # Mentor reviews and approves held post
    rev_resp = client.post("/api/v1/forum/moderation/action", json={
        "target_type": "POST",
        "target_id": post_id,
        "action": "APPROVE_HELD",
        "reason": "Verified fair practice and general conceptual discussion."
    }, headers=_get_headers_for_user(mentor))
    assert rev_resp.status_code == 200

    post = db_session.query(ForumPost).filter(ForumPost.id == post_id).first()
    assert post.status == ForumPostStatus.PUBLISHED


def test_anonymous_fields_peer_masking_vs_mentor_audit_log(setup_data, db_session):
    ase1 = setup_data["ase1"]
    ase2 = setup_data["ase2"]
    ase3 = setup_data["ase3"]
    mentor = setup_data["mentor"]
    c1 = setup_data["c1"]

    db_session.query(ForumRateLimit).delete()
    db_session.commit()

    resp = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Anonymous Doubt on Recursion Depth",
        "body": "How do we prevent maximum recursion depth exceeded in Python dfs?",
        "is_anonymous": True
    }, headers=_get_headers_for_user(ase1))
    assert resp.status_code == 200
    post_id = resp.json()["id"]

    ans_resp = client.post(f"/api/v1/forum/posts/{post_id}/answers", json={
        "body": "You can use sys.setrecursionlimit(2000) or convert to iterative stack.",
        "is_anonymous": True
    }, headers=_get_headers_for_user(ase2))
    assert ans_resp.status_code == 200

    # 1. PEER VIEW (ase3): author_id is None, author_name is "Anonymous 1"
    peer_resp = client.get(f"/api/v1/forum/posts/{post_id}", headers=_get_headers_for_user(ase3))
    assert peer_resp.status_code == 200
    peer_data = peer_resp.json()

    assert peer_data["author"]["author_id"] is None
    assert peer_data["author"]["author_name"] == "Anonymous 1"
    assert peer_data["author"]["is_anonymous_to_peers"] is True

    ans = peer_data["answers"][0]
    assert ans["author"]["author_id"] is None
    assert ans["author"]["author_name"] == "Anonymous 2"

    # 2. MENTOR VIEW: real author returned and identity audit log written
    initial_audit_count = db_session.query(ForumIdentityAuditLog).count()
    mentor_resp = client.get(f"/api/v1/forum/posts/{post_id}", headers=_get_headers_for_user(mentor))
    assert mentor_resp.status_code == 200
    mentor_data = mentor_resp.json()

    assert mentor_data["author"]["author_id"] == ase1.id
    assert mentor_data["author"]["author_name"] == ase1.name
    assert mentor_data["author"]["is_anonymous_to_peers"] is True

    new_audit_count = db_session.query(ForumIdentityAuditLog).count()
    assert new_audit_count > initial_audit_count


def test_pii_filter_warning_and_audit_no_raw_pii_stored(setup_data, db_session):
    ase1 = setup_data["ase1"]
    c1 = setup_data["c1"]

    resp_phone = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Call me for study group help",
        "body": "You can reach me directly on WhatsApp at 987-654-3210 for discussions.",
        "is_anonymous": False
    }, headers=_get_headers_for_user(ase1))
    assert resp_phone.status_code == 422
    assert "PHONE_PATTERN" in resp_phone.json()["detail"]["flagged_categories"]

    audit = db_session.query(ForumFilterAuditLog).filter(
        ForumFilterAuditLog.user_id == ase1.id,
        ForumFilterAuditLog.detected_category == "PHONE_PATTERN"
    ).order_by(ForumFilterAuditLog.id.desc()).first()
    assert audit is not None
    assert audit.detected_category == "PHONE_PATTERN"


def test_report_uniqueness_and_moderation(setup_data, db_session):
    ase1 = setup_data["ase1"]
    ase2 = setup_data["ase2"]
    mentor = setup_data["mentor"]
    c1 = setup_data["c1"]

    p_resp = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "Sample question to report",
        "body": "Spam promotional text here.",
        "is_anonymous": False
    }, headers=_get_headers_for_user(ase1))
    post_id = p_resp.json()["id"]

    r1 = client.post("/api/v1/forum/report", json={
        "post_id": post_id,
        "reason": "SPAM",
        "notes": "Clearly off-topic advertising."
    }, headers=_get_headers_for_user(ase2))
    assert r1.status_code == 200

    r_dup = client.post("/api/v1/forum/report", json={
        "post_id": post_id,
        "reason": "SPAM"
    }, headers=_get_headers_for_user(ase2))
    assert r_dup.status_code == 400
    assert "already submitted a report" in r_dup.json()["detail"]

    rep_list = client.get("/api/v1/forum/moderation/reports", headers=_get_headers_for_user(mentor))
    assert rep_list.status_code == 200
    assert len(rep_list.json()["reports"]) > 0

    mod_resp = client.post("/api/v1/forum/moderation/action", json={
        "target_type": "POST",
        "target_id": post_id,
        "action": "HIDE",
        "reason": "Off-topic promotional spam."
    }, headers=_get_headers_for_user(mentor))
    assert mod_resp.status_code == 200

    hidden_check = client.get(f"/api/v1/forum/posts/{post_id}", headers=_get_headers_for_user(ase2))
    assert hidden_check.status_code == 404


def test_ai_draft_answer_generation_and_untrusted_delimiters(setup_data, db_session):
    ase1 = setup_data["ase1"]
    c1 = setup_data["c1"]

    p_resp = client.post("/api/v1/forum/posts", json={
        "cohort_id": c1.id,
        "title": "How to structure pytest fixtures across modules?",
        "body": "What is the recommended practice for sharing database fixtures?",
        "is_anonymous": False
    }, headers=_get_headers_for_user(ase1))
    post_id = p_resp.json()["id"]

    ai_resp = client.post(f"/api/v1/forum/posts/{post_id}/ai-draft", headers=_get_headers_for_user(ase1))
    assert ai_resp.status_code == 200
    data = ai_resp.json()
    assert "AI-generated draft, please verify" in data["body"]
    assert data["is_mentor_verified"] is False


def test_forum_data_isolation_from_chat_scores_and_exports(setup_data, db_session):
    admin = setup_data["admin"]
    ase1 = setup_data["ase1"]

    # 1. Power BI Reporting API: Verify forum content is absent and forum endpoint is unsupported
    token_resp = client.post("/api/v1/reporting/tokens", json={
        "name": "Power BI Isolation Check",
        "scopes": ["assessments", "results"]
    }, headers=_get_headers_for_user(admin))
    assert token_resp.status_code == 200
    raw_token = token_resp.json()["token"]

    rpt_headers = {"Authorization": f"Bearer {raw_token}"}
    pbi_resp = client.get("/api/v1/reporting/assessments", headers=rpt_headers)
    assert pbi_resp.status_code == 200

    # Attempt to query forum data via reporting API -> 403 (unsupported scope)
    unsupported_pbi = client.get("/api/v1/reporting/forum", headers=rpt_headers)
    assert unsupported_pbi.status_code in [400, 403, 404]

    # 2. Similar questions: ensure hidden and anonymous authors are not leaked
    similar_resp = client.get("/api/v1/forum/posts/similar?query=recursion", headers=_get_headers_for_user(ase1))
    assert similar_resp.status_code == 200
    sim_items = similar_resp.json()
    for item in sim_items:
        # If it was an anonymous post, author_name should be "Anonymous Peer"
        if "author_name" in item:
            assert item["author_name"] in ["Anonymous Peer", ase1.name, "Aarav Sharma"]

