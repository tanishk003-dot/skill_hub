import base64
import json
import time
from datetime import datetime, timezone, timedelta
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app, validate_production_configuration
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.seed import init_db
from app.models.user import User, UserRole
from app.models.notification import Notification, ReminderSent
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.phase13_models import (
    UserSSOAccount, SSOAuditLog, SSOConfiguration, SSOOAuthState,
    UserNotificationPreference, ClassAttendanceImport
)
from app.services.sso_provider import (
    AzureOIDCProvider, MockSSOProvider, SSOValidationError
)
from app.services.attendance_provider import (
    MockAttendanceProvider, generate_attendance_preview, confirm_attendance_import
)
from app.services.notification_dispatcher import (
    NotificationDispatcherService, MockTeamsBotChannel, sanitize_teams_payload,
    is_within_quiet_hours
)
from app.services.meeting_provider import TeamsGraphProvider
from app.services.token_encryption_service import (
    encrypt_token, decrypt_token, rotate_token_cipher
)

client = TestClient(app)

# Helper: Generate RSA 2048-bit key pair and JWK dictionary for testing
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

def _int_to_b64url(val: int) -> str:
    b = val.to_bytes((val.bit_length() + 7) // 8, byteorder="big")
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

_public_numbers = _public_key.public_numbers()
TEST_KID = "test-ms-rsa-kid-01"
TEST_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": TEST_KID,
            "n": _int_to_b64url(_public_numbers.n),
            "e": _int_to_b64url(_public_numbers.e)
        }
    ]
}

TEST_TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
TEST_CLIENT_ID = "11111111-2222-3333-4444-555555555555"

def make_test_jwt(
    tid: str = TEST_TENANT_ID,
    aud: str = TEST_CLIENT_ID,
    iss: str = None,
    nonce: str = "valid-nonce",
    exp_offset: int = 3600,
    nbf_offset: int = 0,
    email: str = "ase_sso_test@csm.tech",
    oid: str = "test-oid-12345",
    kid: str = TEST_KID,
    alg: str = "RS256",
    sign_key: bytes = _private_pem
) -> str:
    now = int(time.time())
    if iss is None:
        iss = f"https://login.microsoftonline.com/{tid}/v2.0"

    headers = {"kid": kid, "alg": alg}
    payload = {
        "iss": iss,
        "aud": aud,
        "tid": tid,
        "oid": oid,
        "preferred_username": email,
        "name": "Test SSO User",
        "nonce": nonce,
        "iat": now,
        "exp": now + exp_offset,
        "nbf": now + nbf_offset
    }

    if alg.upper() == "NONE":
        # Unsigned token
        header_b64 = base64.urlsafe_b64encode(json.dumps(headers).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{header_b64}.{payload_b64}."

    return jwt.encode(payload, sign_key, algorithm=alg, headers=headers)


@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()


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
            is_active=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


# ============================================================================
# 1. Production Safety Guards Test
# ============================================================================
def test_mock_providers_refuse_startup_in_production(monkeypatch):
    """
    Requirement 1: MockSSOProvider, MockAttendanceProvider and the Teams bot mock
    must be impossible to enable when APP_ENV=production: the app must refuse to start.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "prod-secret-key-32-chars-long-strictly-enforced!")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "abcdefghijklmnopqrstuvwxyz123456")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://skillhub.csm.tech")

    with pytest.raises(RuntimeError, match="cannot be initialized in production"):
        MockSSOProvider()

    with pytest.raises(RuntimeError, match="cannot be initialized in production"):
        MockAttendanceProvider()

    with pytest.raises(RuntimeError, match="cannot be initialized in production"):
        MockTeamsBotChannel()

    # validate_production_configuration refuses startup if mock SSO configured
    monkeypatch.setattr(settings, "SSO_PROVIDER_TYPE", "mock")
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        validate_production_configuration()


# ============================================================================
# 2. SSO Valid Token Handshake & Linking Test
# ============================================================================
def test_sso_valid_token_handshake(db_session: Session, monkeypatch):
    """
    Requirement 2 & 4: Valid RS256 token signed with RSA key validates against JWKS,
    matches verified email to user, creates (tid, oid) link, logs audit trail, and returns JWT.
    """
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setattr(settings, "AZURE_REDIRECT_URI", "http://localhost:4300/auth/sso/callback")

    test_user = _create_user(db_session, "ase_sso_valid@csm.tech", UserRole.ASE, "Valid SSO User")

    # Initiate authorize
    auth_res = client.post("/api/v1/auth/sso/authorize", json={
        "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert auth_res.status_code == 200
    state = auth_res.json()["state"]

    # Retrieve nonce stored for this state
    state_row = db_session.query(SSOOAuthState).filter(SSOOAuthState.state == state).first()
    assert state_row is not None
    nonce = state_row.nonce

    valid_token = make_test_jwt(nonce=nonce, email=test_user.email, oid="oid-valid-user-999")

    # Patch Azure provider to use test JWKS
    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    monkeypatch.setattr("app.api.sso.get_sso_provider", lambda: test_provider)

    # Mock exchange_and_validate to decode our token
    original_exchange = test_provider.exchange_and_validate
    monkeypatch.setattr(
        test_provider,
        "exchange_and_validate",
        lambda code, code_verifier, redirect_uri, expected_nonce, **kwargs: original_exchange(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            expected_nonce=expected_nonce,
            id_token=valid_token,
            refresh_token="test-refresh-token-xyz"
        )
    )

    cb_res = client.post("/api/v1/auth/sso/callback", json={
        "code": "test-auth-code",
        "state": state,
        "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert cb_res.status_code == 200
    data = cb_res.json()
    assert "access_token" in data
    assert data["email"] == test_user.email

    # Verify SSO account linking in DB
    sso_link = db_session.query(UserSSOAccount).filter(UserSSOAccount.user_id == test_user.id).first()
    assert sso_link is not None
    assert sso_link.tid == TEST_TENANT_ID
    assert sso_link.oid == "oid-valid-user-999"

    # Verify audit log recorded
    audit = db_session.query(SSOAuditLog).filter(
        SSOAuditLog.user_id == test_user.id,
        SSOAuditLog.event_type == "LINK"
    ).first()
    assert audit is not None


# ============================================================================
# 3. Cryptographic Rejections: Wrong Tenant, Aud, Expired, Immature, Tampered, Alg None, Unknown KID
# ============================================================================
def test_sso_wrong_tenant_rejected(db_session: Session, monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    # Token with issuer matching TEST_TENANT_ID but tid claim has wrong tenant GUID
    bad_tenant_jwt = make_test_jwt(
        tid="00000000-0000-0000-0000-000000000000",
        iss=f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0"
    )

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(bad_tenant_jwt)
    assert "TENANT_MISMATCH" in exc.value.internal_code


def test_sso_wrong_audience_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    bad_aud_jwt = make_test_jwt(aud="unauthorized-client-app")

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(bad_aud_jwt)
    assert "AUDIENCE_MISMATCH" in exc.value.internal_code


def test_sso_expired_token_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    expired_jwt = make_test_jwt(exp_offset=-3600)

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(expired_jwt)
    assert "TOKEN_EXPIRED" in exc.value.internal_code


def test_sso_not_yet_valid_token_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    future_jwt = make_test_jwt(nbf_offset=3600)

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(future_jwt)
    assert "TOKEN_NOT_YET_VALID" in exc.value.internal_code


def test_sso_tampered_signature_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    good_jwt = make_test_jwt()
    # Flip characters in signature
    parts = good_jwt.split(".")
    tampered_sig = parts[2][:-4] + "AAAA"
    tampered_jwt = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(tampered_jwt)
    assert "SIGNATURE_VERIFICATION_FAILED" in exc.value.internal_code


def test_sso_alg_none_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    none_jwt = make_test_jwt(alg="none")

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(none_jwt)
    assert "INSECURE_ALGORITHM" in exc.value.internal_code


def test_sso_unknown_kid_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    unknown_kid_jwt = make_test_jwt(kid="nonexistent-key-id")

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(unknown_kid_jwt)
    assert "UNKNOWN_KID" in exc.value.internal_code


# ============================================================================
# 4. State & Nonce Replay Protections
# ============================================================================
def test_sso_nonce_replay_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    mismatched_nonce_jwt = make_test_jwt(nonce="attacker-nonce-999")

    with pytest.raises(SSOValidationError) as exc:
        test_provider.validate_id_token(mismatched_nonce_jwt, expected_nonce="expected-nonce-000")
    assert "NONCE_REPLAY" in exc.value.internal_code


def test_sso_state_replay_rejected(db_session: Session):
    """
    Requirement 4: State must be single-use. Replaying the state fails with 400.
    """
    auth_res = client.post("/api/v1/auth/sso/authorize", json={
        "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    state = auth_res.json()["state"]

    # Manually mark as used to simulate replay
    st = db_session.query(SSOOAuthState).filter(SSOOAuthState.state == state).first()
    st.is_used = True
    db_session.commit()

    cb_res = client.post("/api/v1/auth/sso/callback", json={
        "code": "any-code",
        "state": state,
        "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert cb_res.status_code == 400
    assert "Invalid or expired SSO state" in cb_res.json()["detail"]


# ============================================================================
# 5. User Provisioning & Inactive User Handling
# ============================================================================
def test_sso_unmapped_user_and_auto_provision_toggle(db_session: Session, monkeypatch):
    """
    Requirement 1 & 2: Auto-provision as ASE only if admin enables it,
    otherwise 'ask admin for access' (403). Never auto-create ADMIN or MENTOR.
    """
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setattr(settings, "AZURE_REDIRECT_URI", "http://localhost:4300/auth/sso/callback")

    conf = db_session.query(SSOConfiguration).first()
    if not conf:
        conf = SSOConfiguration(allow_local_login=True, auto_provision_ase=False)
        db_session.add(conf)
    else:
        conf.auto_provision_ase = False
    db_session.commit()

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    monkeypatch.setattr("app.api.sso.get_sso_provider", lambda: test_provider)

    unmapped_email = "new_engineer_unmapped@csm.tech"
    # Ensure database cleanup of test email from prior runs
    db_session.query(UserSSOAccount).filter(UserSSOAccount.upn == unmapped_email).delete()
    db_session.query(User).filter(User.email == unmapped_email).delete()
    db_session.commit()
    token = make_test_jwt(email=unmapped_email, oid="unmapped-oid-111")

    # 1. When auto_provision_ase is False -> 403 Forbidden
    auth_res = client.post("/api/v1/auth/sso/authorize", json={"redirect_uri": "http://localhost:4300/auth/sso/callback"})
    state = auth_res.json()["state"]
    st_row = db_session.query(SSOOAuthState).filter(SSOOAuthState.state == state).first()
    token1 = make_test_jwt(nonce=st_row.nonce, email=unmapped_email, oid="unmapped-oid-111")

    def _exchange_1(code, code_verifier, redirect_uri, expected_nonce, **kwargs):
        kwargs["id_token"] = token1
        kwargs["refresh_token"] = None
        return AzureOIDCProvider.exchange_and_validate(test_provider, code, code_verifier, redirect_uri, expected_nonce, **kwargs)

    monkeypatch.setattr(test_provider, "exchange_and_validate", _exchange_1)

    res1 = client.post("/api/v1/auth/sso/callback", json={
        "code": "code-1", "state": state, "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert res1.status_code == 403
    assert "Account not registered. Please contact your administrator" in res1.json()["detail"]

    # 2. When auto_provision_ase is True -> Auto creates ASE
    conf.auto_provision_ase = True
    db_session.commit()

    auth_res2 = client.post("/api/v1/auth/sso/authorize", json={"redirect_uri": "http://localhost:4300/auth/sso/callback"})
    state2 = auth_res2.json()["state"]
    st_row2 = db_session.query(SSOOAuthState).filter(SSOOAuthState.state == state2).first()
    token2 = make_test_jwt(nonce=st_row2.nonce, email=unmapped_email, oid="unmapped-oid-111")

    def _exchange_2(code, code_verifier, redirect_uri, expected_nonce, **kwargs):
        kwargs["id_token"] = token2
        kwargs["refresh_token"] = None
        return AzureOIDCProvider.exchange_and_validate(test_provider, code, code_verifier, redirect_uri, expected_nonce, **kwargs)

    monkeypatch.setattr(test_provider, "exchange_and_validate", _exchange_2)

    res2 = client.post("/api/v1/auth/sso/callback", json={
        "code": "code-2", "state": state2, "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert res2.status_code == 200
    assert res2.json()["role"] == "ASE"  # Strictly ASE!

    created_u = db_session.query(User).filter(User.email == unmapped_email).first()
    assert created_u is not None
    assert created_u.role == UserRole.ASE


def test_sso_inactive_user_rejected(db_session: Session, monkeypatch):
    """
    Requirement 2: Deactivated users cannot log in via SSO (403).
    """
    monkeypatch.setattr(settings, "AZURE_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setattr(settings, "AZURE_CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setattr(settings, "AZURE_REDIRECT_URI", "http://localhost:4300/auth/sso/callback")

    inactive_user = _create_user(db_session, "inactive_ase_sso@csm.tech", UserRole.ASE, "Inactive ASE")
    inactive_user.is_active = False
    db_session.commit()

    test_provider = AzureOIDCProvider(jwks_override=TEST_JWKS)
    monkeypatch.setattr("app.api.sso.get_sso_provider", lambda: test_provider)

    auth_res = client.post("/api/v1/auth/sso/authorize", json={"redirect_uri": "http://localhost:4300/auth/sso/callback"})
    state = auth_res.json()["state"]
    st_row = db_session.query(SSOOAuthState).filter(SSOOAuthState.state == state).first()
    token_inactive = make_test_jwt(nonce=st_row.nonce, email=inactive_user.email, oid="oid-inactive-999")

    def _exchange_inactive(code, code_verifier, redirect_uri, expected_nonce, **kwargs):
        kwargs["id_token"] = token_inactive
        kwargs["refresh_token"] = None
        return AzureOIDCProvider.exchange_and_validate(test_provider, code, code_verifier, redirect_uri, expected_nonce, **kwargs)

    monkeypatch.setattr(test_provider, "exchange_and_validate", _exchange_inactive)

    cb_res = client.post("/api/v1/auth/sso/callback", json={
        "code": "code", "state": state, "redirect_uri": "http://localhost:4300/auth/sso/callback"
    })
    assert cb_res.status_code == 403
    assert "deactivated" in cb_res.json()["detail"].lower()


# ============================================================================
# 6. Local Login Safety & Break-Glass Login
# ============================================================================
def test_break_glass_admin_login_when_local_login_disabled(db_session: Session):
    """
    Requirement 3: When ALLOW_LOCAL_LOGIN=False, general users receive 403,
    but Break-Glass Administrator login succeeds and records audit log.
    """
    admin_u = _create_user(db_session, "admin_bg_test@csm.tech", UserRole.ADMIN, "BG Admin")
    ase_u = _create_user(db_session, "ase_bg_test@csm.tech", UserRole.ASE, "BG ASE")

    conf = db_session.query(SSOConfiguration).first()
    conf.allow_local_login = False
    db_session.commit()

    # 1. Normal ASE fails
    res_ase = client.post("/api/v1/auth/login", json={"email": ase_u.email, "password": "Password@123"})
    assert res_ase.status_code == 403
    assert "Local password login has been disabled" in res_ase.json()["detail"]

    # 2. Break-glass admin succeeds
    res_admin = client.post("/api/v1/auth/login", json={"email": admin_u.email, "password": "Password@123"})
    assert res_admin.status_code == 200
    assert "access_token" in res_admin.json()

    # Verify audit log
    audit = db_session.query(SSOAuditLog).filter(
        SSOAuditLog.user_id == admin_u.id,
        SSOAuditLog.event_type == "BREAK_GLASS_LOGIN"
    ).first()
    assert audit is not None

    # Reset
    conf.allow_local_login = True
    db_session.commit()


def test_local_login_toggle_guard(db_session: Session):
    """
    Requirement 3: Disabling local login requires confirmation and at least one
    prior successful SSO Admin login.
    """
    admin_u = _create_user(db_session, "admin_guard_test@csm.tech", UserRole.ADMIN, "Guard Admin")
    headers = _get_headers_for_user(admin_u)

    # Clear prior admin SSO login logs
    db_session.query(SSOAuditLog).filter(
        SSOAuditLog.user_id == admin_u.id,
        SSOAuditLog.event_type.in_(["LOGIN_SUCCESS", "LINK"])
    ).delete(synchronize_session=False)
    db_session.commit()

    # 1. Attempt disable without confirm -> 400
    res1 = client.put("/api/v1/auth/sso/settings", headers=headers, json={
        "allow_local_login": False,
        "auto_provision_ase": False,
        "confirm": False
    })
    assert res1.status_code == 400
    assert "explicit confirmation" in res1.json()["detail"]

    # 2. Attempt disable without prior SSO admin login -> 400
    res2 = client.put("/api/v1/auth/sso/settings", headers=headers, json={
        "allow_local_login": False,
        "auto_provision_ase": False,
        "confirm": True
    })
    assert res2.status_code == 400
    assert "at least one Administrator has successfully logged in via Microsoft SSO" in res2.json()["detail"]


# ============================================================================
# 7. Teams Meeting Generation & Fallback
# ============================================================================
def test_teams_meeting_creation_and_fallback():
    """
    Requirement 2 & 5: TeamsGraphProvider creates online meetings or falls back gracefully.
    """
    provider = TeamsGraphProvider()
    # Explicit link returns validated link
    valid_link = provider.create_or_validate_link("https://teams.microsoft.com/l/meetup-join/19%3axyz/0")
    assert "teams.microsoft.com" in valid_link

    # Missing credentials falls back gracefully to manual meeting link
    fallback_link = provider.create_or_validate_link(title="Sprint Architecture Review")
    assert "teams.microsoft.com" in fallback_link
    assert "fallback" in fallback_link


# ============================================================================
# 8. Attendance Preview & Confirm Permissions
# ============================================================================
def test_attendance_preview_and_confirm_permissions(db_session: Session):
    """
    Requirement 3 & 6: Only the class owner mentor or admin can preview and confirm attendance.
    """
    mentor_u = _create_user(db_session, "mentor_att_owner@csm.tech", UserRole.MENTOR, "Owner Mentor")
    other_mentor = _create_user(db_session, "mentor_att_other@csm.tech", UserRole.MENTOR, "Other Mentor")
    ase_u = _create_user(db_session, "ase_att_test@csm.tech", UserRole.ASE, "Att ASE")

    # Create live class
    lc = LiveClass(
        title="Async Microservices Deep Dive",
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        duration_minutes=60,
        meeting_link="https://teams.microsoft.com/l/meetup-join/19%3atest/0",
        provider="TEAMS_GRAPH",
        created_by=mentor_u.id
    )
    db_session.add(lc)
    db_session.commit()
    db_session.refresh(lc)

    # Add invited attendee
    att_rec = LiveClassAttendee(
        live_class_id=lc.id,
        ase_id=ase_u.id,
        status="INVITED"
    )
    db_session.add(att_rec)
    db_session.commit()

    # 1. ASE cannot preview -> 403
    res_ase = client.get(f"/api/v1/classes/{lc.id}/attendance/import-preview", headers=_get_headers_for_user(ase_u))
    assert res_ase.status_code == 403

    # 2. Non-owner mentor cannot preview -> 403
    res_other = client.get(f"/api/v1/classes/{lc.id}/attendance/import-preview", headers=_get_headers_for_user(other_mentor))
    assert res_other.status_code == 403

    # 3. Owner mentor previews -> 200
    res_owner = client.get(f"/api/v1/classes/{lc.id}/attendance/import-preview", headers=_get_headers_for_user(mentor_u))
    assert res_owner.status_code == 200
    preview_data = res_owner.json()
    assert preview_data["live_class_id"] == lc.id
    import_id = preview_data["import_id"]

    # 4. Confirm attendance
    res_conf = client.post(
        f"/api/v1/classes/{lc.id}/attendance/import-confirm",
        headers=_get_headers_for_user(mentor_u),
        json={
            "import_id": import_id,
            "mappings": [{"ase_id": ase_u.id, "status": "ATTENDED"}]
        }
    )
    assert res_conf.status_code == 200
    assert res_conf.json()["is_confirmed"] is True

    # Verify status updated
    db_session.refresh(att_rec)
    assert att_rec.status == "ATTENDED"


# ============================================================================
# 9. Teams Notification Bot: Quiet Hours & Payload Privacy
# ============================================================================
def test_teams_notification_quiet_hours_and_urgent_allowlist(db_session: Session):
    """
    Requirement 4 & 7: Quiet hours suppress non-urgent notifications;
    Urgent notifications (assessment/class starting) bypass quiet hours.
    """
    ase_u = _create_user(db_session, "ase_notif_quiet@csm.tech", UserRole.ASE, "Quiet ASE")

    # Clean existing reminder logs for test isolation
    db_session.query(ReminderSent).filter(ReminderSent.user_id == ase_u.id).delete()
    db_session.commit()

    # Set quiet hours 22:00 to 07:00 UTC
    pref = db_session.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == ase_u.id).first()
    if not pref:
        pref = UserNotificationPreference(
            user_id=ase_u.id,
            preferred_channels="IN_APP,EMAIL,TEAMS",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            timezone="UTC"
        )
        db_session.add(pref)
    else:
        pref.preferred_channels = "IN_APP,EMAIL,TEAMS"
        pref.quiet_hours_enabled = True
        pref.quiet_hours_start = "22:00"
        pref.quiet_hours_end = "07:00"
        pref.timezone = "UTC"
    db_session.commit()

    dispatcher = NotificationDispatcherService(db_session, mock_teams=True)

    # 23:30 UTC is inside quiet hours
    quiet_dt = datetime(2026, 11, 20, 23, 30, tzinfo=timezone.utc)

    # 1. Routine reminder -> Deferred (HELD_QUIET_HOURS)
    res_routine = dispatcher.dispatch_reminder(
        user=ase_u,
        entity_type="TRAINING",
        entity_id=101,
        reminder_type="24H_BEFORE",
        title="Python Async Fundamentals",
        scheduled_time_str="Tomorrow at 10:00 AM",
        now_dt=quiet_dt
    )
    assert res_routine["dispatched"] is False
    assert res_routine["reason"] == "HELD_QUIET_HOURS"

    # 2. Urgent reminder -> Bypasses quiet hours
    res_urgent = dispatcher.dispatch_reminder(
        user=ase_u,
        entity_type="ASSESSMENT",
        entity_id=202,
        reminder_type="ASSESSMENT_STARTING",
        title="Algorithms Benchmark Exam",
        scheduled_time_str="Starting in 10 minutes",
        is_urgent=True,
        now_dt=quiet_dt
    )
    assert res_urgent["dispatched"] is True, f"Expected urgent reminder to dispatch, got: {res_urgent}"
    assert "TEAMS" in res_urgent["channels"]


def test_teams_notification_payload_no_scores():
    """
    Requirement 7: Teams messages contain ONLY title, time, and login link.
    Never scores, risk, feedback, or grades.
    """
    dirty_payload = {
        "title": "Assessment Notification",
        "time": "Tomorrow at 9:00 AM",
        "link": "https://skillhub.lk.internal/exam/1",
        "score": 95.0,
        "risk": "HIGH",
        "grade": "A+",
        "feedback": "Needs improvement on pointers",
        "violations": 2
    }

    clean = sanitize_teams_payload(dirty_payload)
    assert "score" not in clean
    assert "risk" not in clean
    assert "grade" not in clean
    assert "feedback" not in clean
    assert "violations" not in clean
    assert clean["title"] == "Assessment Notification"
    assert clean["time"] == "Tomorrow at 9:00 AM"


# ============================================================================
# 10. Token Encryption & Rotation
# ============================================================================
def test_token_encryption_and_rotation(monkeypatch):
    """
    Requirement 8: Token encryption at rest with MultiFernet rotation support.
    """
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "primary-test-key-seed-12345")
    raw_token = "secret-ms-refresh-token-value-abc-123"

    cipher = encrypt_token(raw_token)
    assert cipher != raw_token

    decrypted = decrypt_token(cipher)
    assert decrypted == raw_token

    # Rotate keys: old key added to TOKEN_ROTATION_KEYS, new key set as primary
    monkeypatch.setattr(settings, "TOKEN_ROTATION_KEYS", "primary-test-key-seed-12345")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "new-primary-key-seed-67890")

    # Still successfully decrypts with rotated history keys
    decrypted_after_rot = decrypt_token(cipher)
    assert decrypted_after_rot == raw_token
