import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token

client = TestClient(app)


def test_login_wrong_domain_rejected():
    """Verify login with email not ending with @csm.tech returns HTTP 400."""
    # 1. External public domain
    res = client.post("/api/v1/auth/login", json={
        "email": "user@gmail.com",
        "password": "Password@123"
    })
    assert res.status_code == 400
    assert "Use your @csm.tech email" in res.json()["detail"]

    # 2. Legacy domain
    res2 = client.post("/api/v1/auth/login", json={
        "email": "admin@skillhub.com",
        "password": "Password@123"
    })
    assert res2.status_code == 400
    assert "Use your @csm.tech email" in res2.json()["detail"]


def test_login_non_revealing_401():
    """Verify non-existing user and wrong password return identical generic 401 error."""
    # 1. Non-existent user
    res1 = client.post("/api/v1/auth/login", json={
        "email": "completely.nonexistent.user@csm.tech",
        "password": "SomePassword@123"
    })
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Invalid email or password"

    # 2. Existing user with wrong password
    res2 = client.post("/api/v1/auth/login", json={
        "email": "admin.demo@csm.tech",
        "password": "WrongPassword@999"
    })
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Invalid email or password"


def test_login_case_insensitive_and_whitespace():
    """Verify login is case-insensitive and trims whitespace."""
    # Uppercase email with whitespace
    res = client.post("/api/v1/auth/login", json={
        "email": "  ADMIN.DEMO@CSM.TECH  ",
        "password": "Admin@123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["email"] == "admin.demo@csm.tech"


def test_admin_create_and_update_user_domain_enforcement():
    """Verify admin endpoints enforce @csm.tech email domain rule."""
    db = SessionLocal()
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    assert admin is not None
    admin_token = create_access_token(subject=admin.id, role=admin.role.value)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create with invalid domain -> 400
    res_create_fail = client.post("/api/v1/users", headers=headers, json={
        "name": "Invalid Domain User",
        "email": "invalid.user@othercompany.com",
        "password": "Password@123",
        "role": "ASE"
    })
    assert res_create_fail.status_code == 400
    assert "Use your @csm.tech email" in res_create_fail.json()["detail"]

    # 2. Create with valid domain -> 201
    res_create_ok = client.post("/api/v1/users", headers=headers, json={
        "name": "Valid Domain User",
        "email": "valid.newhire@csm.tech",
        "password": "Password@123",
        "role": "ASE"
    })
    assert res_create_ok.status_code == 201
    created_id = res_create_ok.json()["id"]

    try:
        # 3. Update email to invalid domain -> 400
        res_update_fail = client.put(f"/api/v1/users/{created_id}", headers=headers, json={
            "email": "hacked@external.com"
        })
        assert res_update_fail.status_code == 400
        assert "Use your @csm.tech email" in res_update_fail.json()["detail"]

        # 4. Update email to valid domain -> 200
        res_update_ok = client.put(f"/api/v1/users/{created_id}", headers=headers, json={
            "email": "updated.newhire@csm.tech"
        })
        assert res_update_ok.status_code == 200
        assert res_update_ok.json()["email"] == "updated.newhire@csm.tech"
    finally:
        db.query(User).filter(User.id == created_id).delete()
        db.commit()
        db.close()


def test_forced_password_change_in_production(monkeypatch):
    """In production, seeded accounts must return must_change_password=True."""
    monkeypatch.setattr(settings, "APP_ENV", "production")

    res = client.post("/api/v1/auth/login", json={
        "email": "admin.demo@csm.tech",
        "password": "Admin@123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["must_change_password"] is True


def test_change_password_flow():
    """Verify change-password endpoint validation, complexity, and success."""
    db = SessionLocal()
    try:
        # Create a dedicated user for password change testing
        test_email = "pwd_test_user@csm.tech"
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            db.delete(existing)
            db.commit()

        u = User(
            name="Password Test User",
            email=test_email,
            hashed_password=hash_password("Initial@123"),
            role=UserRole.ASE,
            is_active=True,
            must_change_password=True
        )
        db.add(u)
        db.commit()
        db.refresh(u)

        token = create_access_token(subject=u.id, role=u.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Wrong current password -> 400
        res1 = client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "WrongPassword@123",
            "new_password": "NewSecret@456",
            "confirm_password": "NewSecret@456"
        })
        assert res1.status_code == 400
        assert "Current password is incorrect" in res1.json()["detail"]

        # 2. Confirmation mismatch -> 400
        res2 = client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "Initial@123",
            "new_password": "NewSecret@456",
            "confirm_password": "DifferentSecret@789"
        })
        assert res2.status_code == 400
        assert "do not match" in res2.json()["detail"]

        # 3. Same as current password -> 400
        res3 = client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "Initial@123",
            "new_password": "Initial@123",
            "confirm_password": "Initial@123"
        })
        assert res3.status_code == 400
        assert "must be different" in res3.json()["detail"]

        # 4. Weak password (no uppercase or digits) -> 400 or 422
        res4 = client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "Initial@123",
            "new_password": "alllowercasepwd",
            "confirm_password": "alllowercasepwd"
        })
        assert res4.status_code in [400, 422]
        assert "Password must" in res4.json()["detail"]

        # 5. Successful password change
        res5 = client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "Initial@123",
            "new_password": "UpdatedValid@2026",
            "confirm_password": "UpdatedValid@2026"
        })
        assert res5.status_code == 200
        assert res5.json()["must_change_password"] is False

        # 6. Verify old password fails and new password succeeds on login
        fail_login = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "Initial@123"
        })
        assert fail_login.status_code == 401

        ok_login = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "UpdatedValid@2026"
        })
        assert ok_login.status_code == 200
        assert ok_login.json()["must_change_password"] is False

    finally:
        db.query(User).filter(User.email == "pwd_test_user@csm.tech").delete()
        db.commit()
        db.close()
