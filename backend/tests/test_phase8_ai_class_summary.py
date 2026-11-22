import io
import time
import zipfile
import docx
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.training import Training, TrainingAssignment
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.assignment import MentorAseAssignment
from app.models.ai_class_summary import (
    ClassTranscript, ClassSummary, AIGeneratedAssessment,
    AIGeneratedQuestion, AIGenerateRateLog
)
from app.services.scheduler import cleanup_expired_transcripts

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

def create_sample_docx_bytes(text: str) -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_file_upload_safety_and_privacy_consent(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db_session.add(mentor)
    db_session.commit()
    headers = _get_auth_headers(mentor)

    lc = LiveClass(
        title="Distributed Caching Masterclass",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=60,
        audience_type="ALL",
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor.id
    )
    db_session.add(lc)
    db_session.commit()

    # Reject without privacy consent
    file_content = b"Lecture transcript discussing Redis clustering and cache invalidation."
    files = {"file": ("transcript.txt", file_content, "text/plain")}
    data = {"live_class_id": lc.id, "privacy_consent_acknowledged": "false"}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 400
    assert "privacy" in resp.json()["detail"].lower()

    # Reject executable / binary in .txt
    binary_content = b"MZ\x90\x00\x03\x00\x00\x00Binary Payload"
    files = {"file": ("malicious.txt", binary_content, "text/plain")}
    data = {"live_class_id": lc.id, "privacy_consent_acknowledged": "true"}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 400
    assert "binary" in resp.json()["detail"].lower()

    # Accept valid .txt
    files = {"file": ("clean_transcript.txt", file_content, "text/plain")}
    data = {"live_class_id": lc.id, "privacy_consent_acknowledged": "true"}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 200
    trans_data = resp.json()
    assert trans_data["file_type"] == "txt"
    assert trans_data["raw_text_present"] is True

    # Accept valid .vtt (cleans timestamps & cues)
    vtt_content = (
        b"WEBVTT\n\n"
        b"1\n00:00:01.000 --> 00:00:04.000\n<v Instructor>Today we cover cache invalidation.</v>\n\n"
        b"2\n00:00:05.000 --> 00:00:09.000\nWrite-through versus write-back strategies.\n"
    )
    files = {"file": ("subtitles.vtt", vtt_content, "text/vtt")}
    data = {"live_class_id": lc.id, "privacy_consent_acknowledged": "true"}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 200
    assert resp.json()["file_type"] == "vtt"

    # Accept valid .docx
    docx_bytes = create_sample_docx_bytes("In depth review of database sharding and partitioning strategies.")
    files = {"file": ("notes.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"live_class_id": lc.id, "privacy_consent_acknowledged": "true"}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 200
    assert resp.json()["file_type"] == "docx"

    # Reject unsupported format
    files = {"file": ("script.py", b"print('hello')", "text/x-python")}
    resp = client.post("/api/v1/class-summaries/transcripts/upload", headers=headers, files=files, data=data)
    assert resp.status_code == 400

def test_transcript_retention_and_manual_deletion(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db_session.add(mentor)
    db_session.commit()
    headers = _get_auth_headers(mentor)

    lc = LiveClass(
        title="Security & Auth Architecture",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor.id
    )
    db_session.add(lc)
    db_session.commit()

    # Create notes transcript
    payload = {
        "live_class_id": lc.id,
        "notes": "Discussion on OAuth2, JWT token signing, and refresh token rotation.",
        "topics_covered": "OAuth2, JWT, PKCE",
        "privacy_consent_acknowledged": True
    }
    resp = client.post("/api/v1/class-summaries/transcripts/notes", headers=headers, json=payload)
    assert resp.status_code == 200
    t_id = resp.json()["id"]

    # Generate summary first
    sum_resp = client.post(f"/api/v1/class-summaries/generate?transcript_id={t_id}", headers=headers)
    assert sum_resp.status_code == 200
    s_id = sum_resp.json()["id"]

    # Manual deletion of raw transcript text
    del_resp = client.delete(f"/api/v1/class-summaries/transcripts/{t_id}/raw", headers=headers)
    assert del_resp.status_code == 200

    # Verify raw text is None in DB but summary stays intact
    t_db = db_session.query(ClassTranscript).filter(ClassTranscript.id == t_id).first()
    assert t_db.raw_text is None

    s_db = db_session.query(ClassSummary).filter(ClassSummary.id == s_id).first()
    assert s_db is not None
    assert len(s_db.key_topics) > 0

    # Test auto retention scheduler cleanup
    t_expired = ClassTranscript(
        live_class_id=lc.id,
        uploaded_by=mentor.id,
        raw_text="This raw text should be expired.",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(t_expired)
    db_session.commit()

    cleaned = cleanup_expired_transcripts(db_session)
    assert cleaned >= 1
    db_session.refresh(t_expired)
    assert t_expired.raw_text is None

def test_mentor_isolation_and_ase_draft_protection(db_session: Session):
    ts = time.time()
    mentor_a = User(name="Mentor A", email=f"mentor_a_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    mentor_b = User(name="Mentor B", email=f"mentor_b_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="ASE One", email=f"ase_one_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([mentor_a, mentor_b, ase])
    db_session.commit()

    headers_a = _get_auth_headers(mentor_a)
    headers_b = _get_auth_headers(mentor_b)
    headers_ase = _get_auth_headers(ase)

    # Class owned by Mentor B
    lc_b = LiveClass(
        title="Mentor B Private Architecture",
        start_time=datetime.now(timezone.utc) + timedelta(days=3),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor_b.id
    )
    db_session.add(lc_b)
    db_session.commit()

    # Mentor A attempts to upload notes for Mentor B's class -> 403 Forbidden
    payload = {
        "live_class_id": lc_b.id,
        "notes": "Attempting unauthorized note upload",
        "privacy_consent_acknowledged": True
    }
    resp = client.post("/api/v1/class-summaries/transcripts/notes", headers=headers_a, json=payload)
    assert resp.status_code == 403

    # Non-existent class ID -> 404 Not Found
    payload["live_class_id"] = 999999
    resp = client.post("/api/v1/class-summaries/transcripts/notes", headers=headers_a, json=payload)
    assert resp.status_code == 404

    # Mentor B generates draft summary
    payload["live_class_id"] = lc_b.id
    t_resp = client.post("/api/v1/class-summaries/transcripts/notes", headers=headers_b, json=payload)
    t_id = t_resp.json()["id"]

    sum_resp = client.post(f"/api/v1/class-summaries/generate?transcript_id={t_id}", headers=headers_b)
    assert sum_resp.status_code == 200
    assert sum_resp.json()["is_published"] is False

    # ASE attempts to get draft summary -> 404 Not Found (ASEs can NEVER see drafts)
    ase_get_resp = client.get(f"/api/v1/class-summaries/by-class/{lc_b.id}", headers=headers_ase)
    assert ase_get_resp.status_code == 404

def test_summary_publish_edit_and_notifications(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    ase = User(name="ASE Attendee", email=f"ase_att_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.ASE, is_active=True)
    db_session.add_all([mentor, ase])
    db_session.commit()

    headers = _get_auth_headers(mentor)
    headers_ase = _get_auth_headers(ase)

    lc = LiveClass(
        title="Microservices & Event Mesh",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=60,
        audience_type="SELECTED",
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor.id
    )
    db_session.add(lc)
    db_session.commit()

    attendee = LiveClassAttendee(
        live_class_id=lc.id,
        ase_id=ase.id,
        status="INVITED"
    )
    db_session.add(attendee)
    db_session.commit()

    # Upload transcript & generate summary
    t_resp = client.post("/api/v1/class-summaries/transcripts/notes", headers=headers, json={
        "live_class_id": lc.id,
        "notes": "Kafka partitions, consumer groups, and idempotency guarantees.",
        "topics_covered": "Kafka, Event Sourcing",
        "privacy_consent_acknowledged": True
    })
    t_id = t_resp.json()["id"]
    sum_resp = client.post(f"/api/v1/class-summaries/generate?transcript_id={t_id}", headers=headers)
    summary_id = sum_resp.json()["id"]

    # Publish summary
    pub_resp = client.post(f"/api/v1/class-summaries/{summary_id}/publish", headers=headers)
    assert pub_resp.status_code == 200
    assert pub_resp.json()["is_published"] is True

    # ASE can now view published summary
    ase_resp = client.get(f"/api/v1/class-summaries/by-class/{lc.id}", headers=headers_ase)
    assert ase_resp.status_code == 200
    assert "Kafka" in str(ase_resp.json()["key_topics"])

    # Mentor edits published summary -> version increments & sends update notification
    edit_resp = client.put(f"/api/v1/class-summaries/{summary_id}", headers=headers, json={
        "ase_recap": "Updated recap: Remember to configure max.poll.interval.ms properly."
    })
    assert edit_resp.status_code == 200
    assert edit_resp.json()["version"] == 2

    # Unpublish summary
    unpub_resp = client.post(f"/api/v1/class-summaries/{summary_id}/unpublish", headers=headers)
    assert unpub_resp.status_code == 200
    assert unpub_resp.json()["is_published"] is False

    # Now ASE cannot see it again (404)
    ase_after_unpub = client.get(f"/api/v1/class-summaries/by-class/{lc.id}", headers=headers_ase)
    assert ase_after_unpub.status_code == 404

def test_assessment_generation_review_workflow_and_immutability(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db_session.add(mentor)
    db_session.commit()
    headers = _get_auth_headers(mentor)

    lc = LiveClass(
        title="High Performance Python Services",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor.id
    )
    db_session.add(lc)
    db_session.commit()

    # Generate assessment
    gen_payload = {
        "live_class_id": lc.id,
        "title": "Async Python Evaluation",
        "generation_mode": "AUTO",
        "recommended_total_questions": 20,
        "difficulty_split": {"EASY": 40, "MEDIUM": 40, "HARD": 20},
        "skill_category": "Software Engineering"
    }
    resp = client.post("/api/v1/class-summaries/assessments/generate", headers=headers, json=gen_payload)
    assert resp.status_code == 200
    ass_data = resp.json()
    ass_id = ass_data["id"]
    questions = ass_data["questions"]
    assert len(questions) == 20

    # Check question quality: Single choice has exactly 1 correct answer, options non-empty
    for q in questions:
        assert len(q["options"]) >= 2
        assert len(q["correct_answers"]) == 1
        assert q["correct_answers"][0] in q["options"]
        assert q["explanation"]
        assert q["difficulty"] in ("EASY", "MEDIUM", "HARD")

    # Approve all should FAIL if any question is PENDING or flagged
    app_all_resp = client.post(f"/api/v1/class-summaries/assessments/{ass_id}/approve-all", headers=headers)
    assert app_all_resp.status_code == 400
    assert "pending" in app_all_resp.json()["detail"].lower() or "verification" in app_all_resp.json()["detail"].lower()

    # Approve each question individually
    for q in questions:
        q_id = q["id"]
        app_resp = client.post(f"/api/v1/class-summaries/questions/{q_id}/approve", headers=headers)
        assert app_resp.status_code == 200
        assert app_resp.json()["review_status"] == "APPROVED"
        assert app_resp.json()["mentor_verify_required"] is False

    # Now approve-all succeeds
    app_all_resp2 = client.post(f"/api/v1/class-summaries/assessments/{ass_id}/approve-all", headers=headers)
    assert app_all_resp2.status_code == 200
    assert app_all_resp2.json()["status"] == "APPROVED"

    # Export approved questions to Question Bank
    export_resp = client.post(
        f"/api/v1/class-summaries/assessments/{ass_id}/export-to-bank",
        headers=headers,
        json={"question_ids": [questions[0]["id"], questions[1]["id"]]}
    )
    assert export_resp.status_code == 200
    assert "Successfully exported 2" in export_resp.json()["message"]

    # Finalize and assign -> sets is_immutable = True
    finalize_resp = client.post(f"/api/v1/class-summaries/assessments/{ass_id}/finalize-assign", headers=headers)
    assert finalize_resp.status_code == 200
    assert finalize_resp.json()["is_immutable"] is True

    # Any further edit to questions on this assessment must be rejected (immutable)
    q1_id = questions[0]["id"]
    edit_q_resp = client.put(f"/api/v1/class-summaries/questions/{q1_id}", headers=headers, json={"question_text": "Modified question text"})
    assert edit_q_resp.status_code == 400
    assert "immutable" in edit_q_resp.json()["detail"].lower()

def test_class_effectiveness_privacy_and_analytics(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db_session.add(mentor)
    db_session.commit()
    headers = _get_auth_headers(mentor)

    lc = LiveClass(
        title="Scalable Microservices Deep Dive",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/test",
        created_by=mentor.id
    )
    db_session.add(lc)
    db_session.commit()

    # With fewer than 3 attempts, must return privacy protected "Not enough data"
    eff_resp = client.get(f"/api/v1/class-summaries/effectiveness/live-class/{lc.id}", headers=headers)
    assert eff_resp.status_code == 200
    data = eff_resp.json()
    assert data["has_enough_data"] is False
    assert "Fewer than 3 ASEs" in data["message"]

def test_ai_rate_limits(db_session: Session):
    ts = time.time()
    mentor = User(name="Mentor Alice", email=f"mentor_alice_{ts}@csm.tech", hashed_password=hash_password("pw"), role=UserRole.MENTOR, is_active=True)
    db_session.add(mentor)
    db_session.commit()
    headers = _get_auth_headers(mentor)

    # Reject more than 50 questions in one call
    payload = {
        "title": "Too Many Questions",
        "recommended_total_questions": 51,
        "difficulty_split": {"EASY": 40, "MEDIUM": 40, "HARD": 20}
    }
    resp = client.post("/api/v1/class-summaries/assessments/generate", headers=headers, json=payload)
    assert resp.status_code in (400, 422)

    # Exhaust daily rate limit with rate logs
    for _ in range(20):
        log = AIGenerateRateLog(user_id=mentor.id, action_type="SUMMARY", created_at=datetime.now(timezone.utc))
        db_session.add(log)
    db_session.commit()

    # Next call should return 429
    resp_429 = client.post("/api/v1/class-summaries/assessments/generate", headers=headers, json={
        "title": "Rate Limit Exceeded Test",
        "recommended_total_questions": 20,
        "difficulty_split": {"EASY": 40, "MEDIUM": 40, "HARD": 20}
    })
    assert resp_429.status_code == 429
    assert "Daily AI generation rate limit exceeded" in resp_429.json()["detail"]
