import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.notification import Notification, ReminderSent
from app.services.scheduler import process_due_reminders

def _clean_phase5_data(db):
    is_mysql = "mysql" in str(db.bind.url)
    try:
        if is_mysql:
            db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        phase5_emails = [
            "admin@csm.tech", "mentor@csm.tech", "other_mentor@csm.tech",
            "ase1@csm.tech", "ase2@csm.tech", "unassigned@csm.tech"
        ]
        test_user_ids = [u[0] for u in db.query(User.id).filter(User.email.in_(phase5_emails)).all()]
        if test_user_ids:
            db.query(ReminderSent).filter(ReminderSent.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(Notification).filter(Notification.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(LiveClassAttendee).filter((LiveClassAttendee.ase_id.in_(test_user_ids)) | (LiveClassAttendee.marked_by.in_(test_user_ids))).delete(synchronize_session=False)
            db.query(LiveClass).filter(LiveClass.created_by.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(TrainingAssignment).filter((TrainingAssignment.ase_id.in_(test_user_ids)) | (TrainingAssignment.assigned_by.in_(test_user_ids))).delete(synchronize_session=False)
            db.query(CohortMember).filter(CohortMember.ase_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(Cohort).filter(Cohort.created_by.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(MentorAseAssignment).filter((MentorAseAssignment.mentor_id.in_(test_user_ids)) | (MentorAseAssignment.ase_id.in_(test_user_ids))).delete(synchronize_session=False)
            db.query(Training).filter(Training.created_by.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
        db.query(Cohort).filter(Cohort.name == "Alpha Cohort").delete(synchronize_session=False)
        db.query(Training).filter(Training.title.like("%Testing%")).delete(synchronize_session=False)
        db.query(Training).filter(Training.title.like("%System Architecture%")).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error in _clean_phase5_data: {e}")
    finally:
        if is_mysql:
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.commit()

@pytest.fixture(scope="function")
def test_db():
    db = SessionLocal()
    _clean_phase5_data(db)

    # Seed core test users
    admin = User(name="Test Admin", email="admin@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.ADMIN, is_active=True)
    mentor = User(name="Test Mentor", email="mentor@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.MENTOR, is_active=True)
    other_mentor = User(name="Other Mentor", email="other_mentor@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.MENTOR, is_active=True)
    ase1 = User(name="ASE One", email="ase1@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.ASE, is_active=True)
    ase2 = User(name="ASE Two", email="ase2@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.ASE, is_active=True)
    unassigned_ase = User(name="Unassigned ASE", email="unassigned@csm.tech", hashed_password=hash_password("Pass123"), role=UserRole.ASE, is_active=True)

    db.add_all([admin, mentor, other_mentor, ase1, ase2, unassigned_ase])
    db.commit()

    # Mappings: mentor maps to ase1, ase2. unassigned_ase is NOT mapped to mentor.
    db.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=ase1.id))
    db.add(MentorAseAssignment(mentor_id=mentor.id, ase_id=ase2.id))

    # Cohort
    cohort = Cohort(name="Alpha Cohort", start_date=datetime.now(timezone.utc).date(), created_by=admin.id)
    db.add(cohort)
    db.commit()
    db.add(CohortMember(cohort_id=cohort.id, ase_id=ase1.id))
    db.commit()

    try:
        yield db
    finally:
        _clean_phase5_data(db)
        db.close()

@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)

def auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}

# ==============================================================================
# 1. Training Creation and Mentor Assignment Isolation (403 Tests)
# ==============================================================================

def test_training_creation_and_listing(client, test_db):
    admin = test_db.query(User).filter_by(email="admin@csm.tech").first()
    res = client.post(
        "/api/v1/trainings/",
        json={
            "title": "System Architecture Patterns",
            "description": "Comprehensive guide to microservices",
            "skill_category": "System Architecture",
            "type": "Self-paced",
            "resources": [{"name": "Doc Link", "url": "https://example.com/doc", "type": "link"}],
            "duration_hours": 3.0
        },
        headers=auth_headers(admin)
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "System Architecture Patterns"

    list_res = client.get("/api/v1/trainings/", headers=auth_headers(admin))
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_mentor_cannot_assign_unassigned_ase_returns_403(client, test_db):
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()
    unassigned_ase = test_db.query(User).filter_by(email="unassigned@csm.tech").first()

    training = Training(title="T1", skill_category="Logic", type="Workshop", resources=[], duration_hours=1.0, created_by=mentor.id)
    test_db.add(training)
    test_db.commit()

    # Mentor attempts to assign training to an unassigned ASE
    due = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    res = client.post(
        f"/api/v1/trainings/{training.id}/assign",
        json={
            "target": "SELECTED",
            "ase_ids": [unassigned_ase.id],
            "due_date": due
        },
        headers=auth_headers(mentor)
    )
    assert res.status_code == 403
    assert "Mentors can assign trainings only to their own assigned mentees" in res.json()["detail"]

def test_ase_progress_update_and_isolation_403(client, test_db):
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()
    ase2 = test_db.query(User).filter_by(email="ase2@csm.tech").first()

    training = Training(title="T2", skill_category="Logic", type="Self-paced", resources=[], duration_hours=2.0)
    test_db.add(training)
    test_db.commit()

    ta = TrainingAssignment(
        training_id=training.id,
        ase_id=ase1.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=5),
        status="NOT_STARTED",
        progress_percent=0.0
    )
    test_db.add(ta)
    test_db.commit()

    # ase1 updates their own progress to 50%
    res = client.put(
        f"/api/v1/trainings/assignments/{ta.id}/progress",
        json={"progress_percent": 50.0},
        headers=auth_headers(ase1)
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"
    assert res.json()["progress_percent"] == 50.0

    # ase2 attempts to update ase1's assignment -> 403 Forbidden
    res_forbidden = client.put(
        f"/api/v1/trainings/assignments/{ta.id}/progress",
        json={"progress_percent": 100.0},
        headers=auth_headers(ase2)
    )
    assert res_forbidden.status_code == 403

# ==============================================================================
# 2. Meeting Link Domain Validation and Rejection
# ==============================================================================

def test_meeting_link_validation(client, test_db):
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()

    # 1. Valid Teams link succeeds
    res_valid = client.post(
        "/api/v1/classes/",
        json={
            "title": "Architecture Live",
            "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
            "audience_type": "SELECTED",
            "ase_ids": [ase1.id],
            "meeting_link": "https://teams.microsoft.com/l/meetup-join/19%3ameeting123%40thread.v2/0",
            "provider": "MANUAL"
        },
        headers=auth_headers(mentor)
    )
    assert res_valid.status_code == 201

    # 2. Insecure http:// link is rejected
    res_http = client.post(
        "/api/v1/classes/",
        json={
            "title": "Insecure Class",
            "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
            "audience_type": "SELECTED",
            "ase_ids": [ase1.id],
            "meeting_link": "http://teams.microsoft.com/l/meetup-join",
            "provider": "MANUAL"
        },
        headers=auth_headers(mentor)
    )
    assert res_http.status_code == 400
    assert "https://" in res_http.json()["detail"]

    # 3. Unallowed domain or unsafe javascript scheme is rejected
    res_malicious = client.post(
        "/api/v1/classes/",
        json={
            "title": "Malicious Class",
            "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
            "audience_type": "SELECTED",
            "ase_ids": [ase1.id],
            "meeting_link": "https://attacker.example.com/steal-creds",
            "provider": "MANUAL"
        },
        headers=auth_headers(mentor)
    )
    assert res_malicious.status_code == 400
    assert "not authorized" in res_malicious.json()["detail"]

# ==============================================================================
# 3. Live Class Attendance Authorization & Rescheduling Notifications
# ==============================================================================

def test_attendance_marking_authorization(client, test_db):
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()
    other_mentor = test_db.query(User).filter_by(email="other_mentor@csm.tech").first()
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()
    unassigned_ase = test_db.query(User).filter_by(email="unassigned@csm.tech").first()

    lc = LiveClass(
        title="Class A",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=45,
        audience_type="SELECTED",
        meeting_link="https://meet.google.com/abc-defg-hij",
        provider="MANUAL",
        created_by=mentor.id
    )
    test_db.add(lc)
    test_db.commit()

    db_attendee = LiveClassAttendee(live_class_id=lc.id, ase_id=ase1.id, status="INVITED")
    test_db.add(db_attendee)
    test_db.commit()

    # Creator mentor marks attendance for invited ASE -> 200 OK
    res = client.put(
        f"/api/v1/classes/{lc.id}/attendance",
        json={"attendances": [{"ase_id": ase1.id, "status": "ATTENDED"}]},
        headers=auth_headers(mentor)
    )
    assert res.status_code == 200

    # Non-creator other_mentor attempts to mark attendance -> 403 Forbidden
    res_403 = client.put(
        f"/api/v1/classes/{lc.id}/attendance",
        json={"attendances": [{"ase_id": ase1.id, "status": "ABSENT"}]},
        headers=auth_headers(other_mentor)
    )
    assert res_403.status_code == 403

    # Attempting to mark attendance for an ASE who was NOT invited -> 400 Bad Request
    res_not_invited = client.put(
        f"/api/v1/classes/{lc.id}/attendance",
        json={"attendances": [{"ase_id": unassigned_ase.id, "status": "ATTENDED"}]},
        headers=auth_headers(mentor)
    )
    assert res_not_invited.status_code == 400

def test_reschedule_class_triggers_notification(client, test_db):
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()

    lc = LiveClass(
        title="Original Time Class",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=60,
        meeting_link="https://zoom.us/j/123456789",
        provider="MANUAL",
        created_by=mentor.id
    )
    test_db.add(lc)
    test_db.commit()
    test_db.add(LiveClassAttendee(live_class_id=lc.id, ase_id=ase1.id, status="INVITED"))
    test_db.commit()

    # Update start_time (reschedule)
    new_start = datetime.now(timezone.utc) + timedelta(days=3)
    res = client.put(
        f"/api/v1/classes/{lc.id}",
        json={"start_time": new_start.isoformat()},
        headers=auth_headers(mentor)
    )
    assert res.status_code == 200

    # Verify notification created for invited ase1
    notif = test_db.query(Notification).filter(
        Notification.user_id == ase1.id,
        Notification.title.ilike("%Rescheduled%")
    ).first()
    assert notif is not None

# ==============================================================================
# 4. Idempotent Deadline Reminders
# ==============================================================================

def test_idempotent_scheduler_reminders(test_db):
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()
    training = Training(title="Urgent Training", skill_category="Logic", type="Self-paced", resources=[])
    test_db.add(training)
    test_db.commit()

    # Due in 12 hours (within 24h window)
    ta = TrainingAssignment(
        training_id=training.id,
        ase_id=ase1.id,
        due_date=datetime.now(timezone.utc) + timedelta(hours=12),
        status="NOT_STARTED"
    )
    test_db.add(ta)
    test_db.commit()

    # First run: should dispatch 1 reminder and create ReminderSent record
    count1 = process_due_reminders(test_db)
    assert count1 >= 1

    reminders = test_db.query(ReminderSent).filter_by(
        user_id=ase1.id,
        entity_type="TRAINING",
        entity_id=ta.id
    ).all()
    assert len(reminders) == 1

    # Second run (simulating scheduler tick or server restart): must NOT duplicate
    count2 = process_due_reminders(test_db)
    assert count2 == 0

    reminders_after = test_db.query(ReminderSent).filter_by(
        user_id=ase1.id,
        entity_type="TRAINING",
        entity_id=ta.id
    ).all()
    assert len(reminders_after) == 1

# ==============================================================================
# 5. Notification Access Isolation (403 Tests)
# ==============================================================================

def test_notification_user_isolation_403(client, test_db):
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()
    ase2 = test_db.query(User).filter_by(email="ase2@csm.tech").first()

    notif = Notification(user_id=ase1.id, title="Secret Notif", message="Only for ase1", type="GENERAL", is_read=False)
    test_db.add(notif)
    test_db.commit()

    # ase2 attempts to mark ase1's notification as read -> 403 Forbidden
    res = client.put(
        f"/api/v1/notifications/{notif.id}/read",
        headers=auth_headers(ase2)
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"]

    # ase1 marks their own notification as read -> 200 OK
    res_ok = client.put(
        f"/api/v1/notifications/{notif.id}/read",
        headers=auth_headers(ase1)
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["is_read"] is True

# ==============================================================================
# 6. Calendar Events Formatting (UTC ISO Format)
# ==============================================================================

def test_calendar_events_utc_iso_format(client, test_db):
    ase1 = test_db.query(User).filter_by(email="ase1@csm.tech").first()
    mentor = test_db.query(User).filter_by(email="mentor@csm.tech").first()

    lc = LiveClass(
        title="Class for Calendar",
        start_time=datetime(2026, 11, 20, 10, 0, 0),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/123",
        created_by=mentor.id
    )
    test_db.add(lc)
    test_db.commit()
    test_db.add(LiveClassAttendee(live_class_id=lc.id, ase_id=ase1.id, status="INVITED"))
    test_db.commit()

    res = client.get("/api/v1/calendar/events", headers=auth_headers(ase1))
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) >= 1

    class_event = next(e for e in events if e["id"] == f"class-{lc.id}")
    assert class_event["start_time"] == "2026-11-20T10:00:00Z"
    assert class_event["end_time"] == "2026-11-20T11:00:00Z"
    assert class_event["event_type"] == "CLASS"
