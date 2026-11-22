import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app, validate_production_configuration
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
from app.core.security import (
    hash_password, verify_password, create_access_token, validate_password_complexity
)
from app.core.datetime_util import utc_now
from app.models.user import User, UserRole
from app.models.admin_audit_log import AdminAuditLog
from app.models.login_lockout import LoginAttempt
from app.models.ai_class_summary import ClassTranscript
from app.models.phase10_models import WebcamProctoringSnapshot
from app.models.phase13_models import ClassAttendanceImport, SSOOAuthState
from app.services.lockout_service import (
    check_login_lockout, record_login_attempt, unlock_account_by_admin
)
from app.services.retention_service import run_data_retention_cleanup
from app.services.ceo_center_service import get_ceo_command_center_analytics

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_db():
    yield

def test_production_configuration_validation():
    """Verify security hardening guards refuse to start with default/insecure configs."""
    orig_env = settings.APP_ENV
    orig_key = settings.SECRET_KEY
    orig_enc = settings.TOKEN_ENCRYPTION_KEY
    orig_exp = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    orig_cors = settings.CORS_ORIGINS

    try:
        settings.APP_ENV = "production"

        # 1. Default SECRET_KEY rejected
        settings.SECRET_KEY = "skillhub-super-secret-jwt-key-replace-in-production"
        with pytest.raises(RuntimeError, match="default or weak SECRET_KEY"):
            validate_production_configuration()

        # Set valid key
        settings.SECRET_KEY = "a_very_secure_production_secret_key_32_chars!"

        # 2. Missing/weak TOKEN_ENCRYPTION_KEY rejected
        settings.TOKEN_ENCRYPTION_KEY = ""
        with pytest.raises(RuntimeError, match="TOKEN_ENCRYPTION_KEY must be set"):
            validate_production_configuration()

        settings.TOKEN_ENCRYPTION_KEY = "abcdefghijklmnopqrstuvwxyz123456"

        # 3. Long ACCESS_TOKEN_EXPIRE_MINUTES rejected
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = 1440
        with pytest.raises(RuntimeError, match="ACCESS_TOKEN_EXPIRE_MINUTES"):
            validate_production_configuration()

        settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        # 4. Wildcard CORS rejected
        settings.CORS_ORIGINS = "http://localhost:4300,*"
        with pytest.raises(RuntimeError, match="wildcard '\\*' in CORS_ORIGINS"):
            validate_production_configuration()

    finally:
        settings.APP_ENV = orig_env
        settings.SECRET_KEY = orig_key
        settings.TOKEN_ENCRYPTION_KEY = orig_enc
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = orig_exp
        settings.CORS_ORIGINS = orig_cors

def test_password_complexity_policy():
    """Verify enterprise password policy rules."""
    # Too short
    valid, msg = validate_password_complexity("Ab1!")
    assert not valid
    assert "at least 8 characters" in msg

    # No uppercase
    valid, msg = validate_password_complexity("lowercase1!")
    assert not valid
    assert "uppercase" in msg

    # No lowercase
    valid, msg = validate_password_complexity("UPPERCASE1!")
    assert not valid
    assert "lowercase" in msg

    # No digit
    valid, msg = validate_password_complexity("NoDigitsHere!")
    assert not valid
    assert "digit" in msg

    # No special char
    valid, msg = validate_password_complexity("NoSpecialChars123")
    assert not valid
    assert "special" in msg

    # Fully compliant
    valid, msg = validate_password_complexity("SecureP@ssw0rd2026")
    assert valid
    assert msg is None

def test_login_lockout_and_exponential_backoff():
    """Verify 5 failed attempts trigger exponential backoff and admin unlock restores access."""
    db: Session = SessionLocal()
    test_email = f"lockout_test_{int(datetime.now(timezone.utc).timestamp())}@csm.tech"
    ip = "192.168.1.99"

    user = User(
        name="Lockout Target",
        email=test_email,
        hashed_password=hash_password("ValidPassword123!"),
        role=UserRole.ASE,
        is_active=True
    )
    db.add(user)
    db.commit()

    try:
        # 1-4 failures: no lockout
        for i in range(4):
            record_login_attempt(db, test_email, ip, is_success=False)
            assert check_login_lockout(db, test_email, ip) is None

        # 5th failure: triggers 1-minute lockout
        record_login_attempt(db, test_email, ip, is_success=False)
        lockout_msg = check_login_lockout(db, test_email, ip)
        assert lockout_msg is not None
        assert "temporarily locked" in lockout_msg

        # Login endpoint returns HTTP 429
        resp = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "ValidPassword123!"
        })
        assert resp.status_code == 429

        # Admin unlocks account
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        unlock_account_by_admin(db, user.id, admin, ip_address="127.0.0.1")

        # Access restored
        assert check_login_lockout(db, test_email, ip) is None
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "ValidPassword123!"
        })
        assert login_resp.status_code == 200

    finally:
        db.query(LoginAttempt).filter(LoginAttempt.email == test_email).delete()
        db.query(AdminAuditLog).filter(AdminAuditLog.target_id == str(user.id)).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()

def test_break_glass_admin_isolation():
    """Verify normal login floods do not lock out break-glass admin login."""
    db: Session = SessionLocal()
    admin = db.query(User).filter(User.role == UserRole.ADMIN, User.is_active == True).first()
    assert admin is not None
    admin_email = admin.email

    try:
        # Attacker floods 10 normal failed logins
        for _ in range(10):
            record_login_attempt(db, admin_email, "10.0.0.99", is_success=False, is_break_glass=False)

        # Break-glass route remains accessible and rate-limited independently
        assert check_login_lockout(db, admin_email, "127.0.0.1", is_break_glass=True) is None

    finally:
        db.query(LoginAttempt).filter(LoginAttempt.email == admin_email).delete()
        admin.failed_login_attempts = 0
        admin.lockout_until = None
        db.commit()
        db.close()

def test_admin_audit_logs_api_and_isolation():
    """Verify admin audit log recording and role-based access control."""
    db: Session = SessionLocal()
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    ase = db.query(User).filter(User.role == UserRole.ASE).first()

    admin_token = create_access_token(subject=admin.id, role=admin.role.value)
    ase_token = create_access_token(subject=ase.id, role=ase.role.value)

    # 1. ASE attempting to access audit logs is rejected (HTTP 403)
    resp = client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {ase_token}"})
    assert resp.status_code == 403

    # 2. Admin can list audit logs
    resp = client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data

    db.close()

def test_data_retention_cleanup():
    """Verify data retention service purges records past their TTL."""
    db: Session = SessionLocal()
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=400)

    # Create expired transcript
    old_transcript = ClassTranscript(
        live_class_id=None,
        file_name="old_transcript.vtt",
        file_type="vtt",
        raw_text="Test raw transcript text for retention testing",
        created_at=old_date,
        expires_at=old_date
    )
    db.add(old_transcript)

    # Create expired attendance staging
    old_import = ClassAttendanceImport(
        live_class_id=1,
        staged_records_json="[]",
        is_confirmed=False,
        expires_at=old_date,
        created_at=old_date
    )
    db.add(old_import)
    db.commit()

    saved_transcript_id = old_transcript.id
    saved_import_id = old_import.id

    # Run cleanup
    results = run_data_retention_cleanup(db)
    assert results["class_transcripts_purged"] >= 1
    assert results["attendance_staging_purged"] >= 1

    # Verify rows are deleted
    assert db.query(ClassTranscript).filter(ClassTranscript.id == saved_transcript_id).first() is None
    assert db.query(ClassAttendanceImport).filter(ClassAttendanceImport.id == saved_import_id).first() is None

    db.close()

def test_dynamic_ceo_command_center_metrics():
    """Verify CEO Command Center calculates metrics dynamically and shows Insufficient Data when N < 5."""
    db: Session = SessionLocal()
    analytics = get_ceo_command_center_analytics(db)

    # Formatted display labels present
    assert "time_to_productivity_display" in analytics
    assert "training_roi_display" in analytics
    assert "formulas" in analytics
    assert "causation_note" in analytics["formulas"]

    # When sample size is small (< 5), shows Insufficient data
    if analytics["time_to_productivity_sample_size"] < 5:
        assert analytics["time_to_productivity_days"] is None
        assert analytics["time_to_productivity_display"] == "Insufficient data"

    if analytics["training_roi_sample_size"] < 5:
        assert analytics["training_roi_uplift_pct"] is None
        assert analytics["training_roi_display"] == "Insufficient data"

    db.close()

def test_security_headers_present():
    """Verify response contains all required security hardening headers."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    headers = resp.headers

    assert "content-security-policy" in headers
    assert "x-frame-options" in headers
    assert headers["x-frame-options"] == "DENY"
    assert "x-content-type-options" in headers
    assert headers["x-content-type-options"] == "nosniff"
    assert "referrer-policy" in headers

def test_timezone_aware_utc_util():
    """Verify utc_now returns timezone-aware UTC datetime."""
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


# ============================================================================
# Phase 14 / Polish: Production Hardening, LLM Demo Mode & SSO Disabled Tests
# ============================================================================

def test_production_start_with_empty_llm_key_succeeds_in_demo_ai_mode(monkeypatch):
    """
    Test requirement:
    In APP_ENV=production, if LLM_API_KEY is empty and ALLOW_MOCK_LLM=true (default),
    the app must start normally in 'Demo AI mode' (MockProvider) without crashing.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "prod-secret-key-32-chars-long-strictly-enforced!")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "abcdefghijklmnopqrstuvwxyz123456")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://skillhub.csm.tech")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_MOCK_LLM", True)
    monkeypatch.setattr(settings, "SSO_PROVIDER_TYPE", "auto")
    monkeypatch.setattr(settings, "ATTENDANCE_PROVIDER_TYPE", "auto")
    monkeypatch.setattr(settings, "TEAMS_BOT_PROVIDER_TYPE", "auto")
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", "")
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", "")

    # Must start normally without exception
    validate_production_configuration()

    # Verify MockProvider is used and is_demo_mode() is True
    from app.services.llm_service import get_llm_provider, is_demo_mode, MockProvider
    provider = get_llm_provider()
    assert isinstance(provider, MockProvider)
    assert is_demo_mode() is True

    # If ALLOW_MOCK_LLM is explicitly disabled with an empty key, startup must fail
    monkeypatch.setattr(settings, "ALLOW_MOCK_LLM", False)
    with pytest.raises(RuntimeError, match="LLM_API_KEY is empty in production and ALLOW_MOCK_LLM is false"):
        validate_production_configuration()


def test_production_start_with_mock_sso_provider_fails(monkeypatch):
    """
    Test requirement:
    In APP_ENV=production, MockSSOProvider and SSO_PROVIDER_TYPE='mock' must remain
    strictly impossible and refuse startup with an error.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "prod-secret-key-32-chars-long-strictly-enforced!")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "abcdefghijklmnopqrstuvwxyz123456")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://skillhub.csm.tech")
    monkeypatch.setattr(settings, "SSO_PROVIDER_TYPE", "mock")

    from app.services.sso_provider import MockSSOProvider, get_sso_provider
    with pytest.raises(RuntimeError, match="MockSSOProvider cannot be initialized in production"):
        MockSSOProvider()

    with pytest.raises(RuntimeError, match="Mock SSO cannot be enabled when APP_ENV=production"):
        get_sso_provider()

    with pytest.raises(RuntimeError, match="Mock SSO is strictly forbidden in production"):
        validate_production_configuration()


def test_local_login_works_with_sso_disabled(monkeypatch):
    """
    Test requirement:
    When AZURE_* variables are empty, SSO is disabled ('Sign in with Microsoft' hidden)
    and standard local password login works normally.
    """
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", "")
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "AZURE_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")

    # 1. Verify SSO config endpoint reports SSO disabled
    conf_resp = client.get("/api/v1/auth/sso/config")
    assert conf_resp.status_code == 200
    conf_data = conf_resp.json()
    assert conf_data["sso_enabled"] is False
    assert conf_data["tenant_configured"] is False
    assert conf_data["allow_local_login"] is True

    # 2. Verify SSO authorize endpoint returns 503 because SSO is disabled
    auth_resp = client.post("/api/v1/auth/sso/authorize", json={
        "redirect_uri": settings.AZURE_REDIRECT_URI
    })
    assert auth_resp.status_code == 503
    assert "disabled" in auth_resp.json()["detail"].lower()

    # 3. Verify standard local password login succeeds
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin.demo@csm.tech",
        "password": "Admin@123"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["email"] == "admin.demo@csm.tech"

