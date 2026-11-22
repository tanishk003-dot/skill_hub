import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, validate_email_domain
from app.api.deps import get_current_user, require_admin
from app.models.user import User, UserRole
from app.models.phase13_models import (
    UserSSOAccount, SSOAuditLog, SSOConfiguration, SSOOAuthState
)
from app.schemas.auth import TokenResponse
from app.schemas.phase13_schemas import (
    SSOConfigOut, SSOAuthorizeRequest, SSOAuthorizeResponse,
    SSOCallbackRequest, SSOSettingsUpdate, SSOAuditLogOut
)
from app.services.sso_provider import get_sso_provider, SSOValidationError
from app.services.token_encryption_service import encrypt_token

router = APIRouter(prefix="/auth/sso", tags=["Single Sign-On (Microsoft)"])

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def _get_or_create_sso_config(db: Session) -> SSOConfiguration:
    conf = db.query(SSOConfiguration).first()
    if not conf:
        conf = SSOConfiguration(
            allow_local_login=settings.ALLOW_LOCAL_LOGIN,
            auto_provision_ase=settings.SSO_AUTO_PROVISION_ASE
        )
        db.add(conf)
        db.commit()
        db.refresh(conf)
    return conf

@router.get("/config", response_model=SSOConfigOut)
def get_sso_public_config(db: Session = Depends(get_db)):
    """Returns public SSO status for login UI without leaking secrets."""
    conf = _get_or_create_sso_config(db)
    is_configured = bool(settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID)
    sso_enabled = is_configured if settings.APP_ENV == "production" else (is_configured or settings.SSO_PROVIDER_TYPE in ("mock", "auto"))
    return SSOConfigOut(
        sso_enabled=sso_enabled,
        tenant_configured=is_configured,
        client_id=settings.AZURE_CLIENT_ID if is_configured else None,
        allow_local_login=conf.allow_local_login,
        auto_provision_ase=conf.auto_provision_ase,
        app_env=settings.APP_ENV
    )

@router.post("/authorize", response_model=SSOAuthorizeResponse)
def sso_authorize(payload: SSOAuthorizeRequest, db: Session = Depends(get_db)):
    """
    Initializes OIDC authorization with PKCE.
    Stores state, nonce, and code_verifier server-side with 10-minute TTL.
    """
    is_configured = bool(settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID)
    if settings.APP_ENV == "production" and not is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Single Sign-On is disabled. Please log in with email and password."
        )
    redirect_uri = payload.redirect_uri.strip()
    
    # Exact redirect URI validation
    allowed_uris = [settings.AZURE_REDIRECT_URI]
    if settings.APP_ENV != "production":
        allowed_uris.extend([
            "http://localhost:4300/auth/sso/callback",
            "http://127.0.0.1:4300/auth/sso/callback",
            "http://localhost:4200/auth/sso/callback"
        ])
    
    if redirect_uri not in allowed_uris:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unauthorized redirect URI. Exact match required."
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    # PKCE S256 code challenge
    challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").replace("=", "")

    oauth_state = SSOOAuthState(
        state=state,
        nonce=nonce,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        is_used=False
    )
    db.add(oauth_state)
    db.commit()

    provider = get_sso_provider()
    auth_url = provider.generate_authorization_url(
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri
    )

    return SSOAuthorizeResponse(authorization_url=auth_url, state=state)

@router.post("/callback", response_model=TokenResponse)
def sso_callback(
    payload: SSOCallbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handles SSO OAuth callback:
    - Single-use server-side state verification.
    - PKCE code verifier exchange.
    - Cryptographic ID token and claim verification.
    - Identity linking by (tid, oid) with fallback to verified email.
    - Strict role assignment: never auto-create ADMIN or MENTOR.
    - Full audit logging with generic client error messages.
    """
    ip_addr = _get_client_ip(request)
    ua = request.headers.get("user-agent", "Unknown")[:300]

    is_configured = bool(settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID)
    if settings.APP_ENV == "production" and not is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Single Sign-On is disabled. Please log in with email and password."
        )

    # Clean up expired states older than 1 hour
    db.query(SSOOAuthState).filter(SSOOAuthState.expires_at < datetime.now(timezone.utc) - timedelta(hours=1)).delete(synchronize_session=False)

    oauth_state = db.query(SSOOAuthState).filter(
        SSOOAuthState.state == payload.state,
        SSOOAuthState.is_used == False,
        SSOOAuthState.expires_at > datetime.now(timezone.utc)
    ).first()

    if not oauth_state:
        # State invalid, expired, or replayed
        audit = SSOAuditLog(
            event_type="LOGIN_FAILED",
            failure_reason="INVALID_OR_EXPIRED_STATE",
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired SSO state. Please initiate login again."
        )

    if payload.redirect_uri != oauth_state.redirect_uri:
        audit = SSOAuditLog(
            event_type="LOGIN_FAILED",
            failure_reason="REDIRECT_URI_MISMATCH",
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch."
        )

    # Invalidate state immediately (single use protection)
    oauth_state.is_used = True
    db.commit()

    provider = get_sso_provider()
    try:
        token_result = provider.exchange_and_validate(
            code=payload.code,
            code_verifier=oauth_state.code_verifier,
            redirect_uri=payload.redirect_uri,
            expected_nonce=oauth_state.nonce
        )
    except SSOValidationError as exc:
        audit = SSOAuditLog(
            event_type="LOGIN_FAILED",
            failure_reason=exc.internal_code,
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please contact your administrator."
        )

    tid = token_result.get("tid")
    oid = token_result.get("oid")
    raw_email = token_result.get("email", "").strip().lower()
    try:
        email = validate_email_domain(raw_email)
    except HTTPException:
        audit = SSOAuditLog(
            event_type="LOGIN_FAILED",
            upn=upn,
            tid=tid,
            oid=oid,
            failure_reason="INVALID_EMAIL_DOMAIN",
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use your @csm.tech email"
        )
    name = token_result.get("name")
    upn = token_result.get("upn", email)
    refresh_token = token_result.get("refresh_token")

    # Reject tokens from any other tenant if tenant is configured
    if settings.AZURE_TENANT_ID and tid and tid.lower() != settings.AZURE_TENANT_ID.lower():
        audit = SSOAuditLog(
            event_type="LOGIN_FAILED",
            upn=upn,
            tid=tid,
            oid=oid,
            failure_reason=f"TENANT_MISMATCH: {tid}",
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please contact your administrator."
        )

    # 1. Identify by existing (tid, oid)
    sso_account = db.query(UserSSOAccount).filter(
        UserSSOAccount.tid == tid,
        UserSSOAccount.oid == oid
    ).first()

    user: Optional[User] = None

    if sso_account:
        user = db.query(User).filter(User.id == sso_account.user_id).first()
        if not user or not user.is_active:
            audit = SSOAuditLog(
                user_id=user.id if user else None,
                event_type="LOGIN_FAILED",
                upn=upn,
                tid=tid,
                oid=oid,
                failure_reason="INACTIVE_OR_DELETED_USER",
                ip_address=ip_addr,
                user_agent=ua
            )
            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact an Administrator."
            )

        if refresh_token:
            sso_account.encrypted_refresh_token = encrypt_token(refresh_token)
        sso_account.last_login_at = datetime.now(timezone.utc)
        sso_account.upn = upn

        audit = SSOAuditLog(
            user_id=user.id,
            event_type="LOGIN_SUCCESS",
            upn=upn,
            tid=tid,
            oid=oid,
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()

    else:
        # 2. First login: match verified email/UPN to an existing user
        user = db.query(User).filter(func.lower(User.email) == email).first()

        if user:
            if not user.is_active:
                audit = SSOAuditLog(
                    user_id=user.id,
                    event_type="LOGIN_FAILED",
                    upn=upn,
                    tid=tid,
                    oid=oid,
                    failure_reason="INACTIVE_USER_ON_LINK",
                    ip_address=ip_addr,
                    user_agent=ua
                )
                db.add(audit)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account has been deactivated. Please contact an Administrator."
                )

            # Link identity
            sso_account = UserSSOAccount(
                user_id=user.id,
                tid=tid,
                oid=oid,
                upn=upn,
                encrypted_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
                last_login_at=datetime.now(timezone.utc)
            )
            db.add(sso_account)

            audit = SSOAuditLog(
                user_id=user.id,
                event_type="LINK",
                upn=upn,
                tid=tid,
                oid=oid,
                ip_address=ip_addr,
                user_agent=ua
            )
            db.add(audit)
            db.commit()

        else:
            # 3. User does not exist: check auto-provisioning
            conf = _get_or_create_sso_config(db)
            if conf.auto_provision_ase:
                # Strictly auto-create as ASE (NEVER ADMIN or MENTOR)
                dummy_pwd = secrets.token_urlsafe(32)
                user = User(
                    name=name or email.split("@")[0],
                    email=email,
                    hashed_password=hash_password(dummy_pwd),
                    role=UserRole.ASE,
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                sso_account = UserSSOAccount(
                    user_id=user.id,
                    tid=tid,
                    oid=oid,
                    upn=upn,
                    encrypted_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
                    last_login_at=datetime.now(timezone.utc)
                )
                db.add(sso_account)

                audit = SSOAuditLog(
                    user_id=user.id,
                    event_type="AUTO_PROVISION",
                    upn=upn,
                    tid=tid,
                    oid=oid,
                    ip_address=ip_addr,
                    user_agent=ua
                )
                db.add(audit)
                db.commit()
            else:
                audit = SSOAuditLog(
                    event_type="LOGIN_FAILED",
                    upn=upn,
                    tid=tid,
                    oid=oid,
                    failure_reason="UNMAPPED_USER_NOT_PROVISIONED",
                    ip_address=ip_addr,
                    user_agent=ua
                )
                db.add(audit)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account not registered. Please contact your administrator for access."
                )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role
    )

@router.get("/audit-logs", response_model=List[SSOAuditLogOut])
def get_sso_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only audit trail for SSO authentication activities."""
    logs = db.query(SSOAuditLog).order_by(SSOAuditLog.created_at.desc()).limit(limit).all()
    return logs

@router.put("/settings", response_model=SSOConfigOut)
def update_sso_settings(
    payload: SSOSettingsUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Admin configuration for SSO toggles.
    Local login safety guard:
    - allow_local_login can ONLY be disabled if at least one successful SSO admin login exists.
    - Requires explicit payload.confirm = True.
    """
    conf = _get_or_create_sso_config(db)

    if not payload.allow_local_login and conf.allow_local_login:
        if not payload.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Disabling local password login requires explicit confirmation."
            )

        # Check if at least one admin has successfully logged in via SSO
        admin_sso_login = db.query(SSOAuditLog).join(User, SSOAuditLog.user_id == User.id).filter(
            SSOAuditLog.event_type.in_(["LOGIN_SUCCESS", "LINK"]),
            User.role == UserRole.ADMIN
        ).first()

        if not admin_sso_login:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disable local login until at least one Administrator has successfully logged in via Microsoft SSO."
            )

    conf.allow_local_login = payload.allow_local_login
    conf.auto_provision_ase = payload.auto_provision_ase
    conf.updated_by = admin_user.id
    conf.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conf)

    is_configured = bool(settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID)
    sso_enabled = is_configured if settings.APP_ENV == "production" else (is_configured or settings.SSO_PROVIDER_TYPE in ("mock", "auto"))
    return SSOConfigOut(
        sso_enabled=sso_enabled,
        tenant_configured=is_configured,
        client_id=settings.AZURE_CLIENT_ID if is_configured else None,
        allow_local_login=conf.allow_local_login,
        auto_provision_ase=conf.auto_provision_ase,
        app_env=settings.APP_ENV
    )

@router.delete("/unlink")
def unlink_sso_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unlinks current user's SSO account and securely deletes stored refresh token."""
    sso_acc = db.query(UserSSOAccount).filter(UserSSOAccount.user_id == current_user.id).first()
    if sso_acc:
        db.delete(sso_acc)
        audit = SSOAuditLog(
            user_id=current_user.id,
            event_type="UNLINK",
            upn=current_user.email
        )
        db.add(audit)
        db.commit()
        return {"status": "unlinked", "message": "SSO account unlinked and stored tokens destroyed."}
    return {"status": "not_linked", "message": "No SSO link existed for this account."}
