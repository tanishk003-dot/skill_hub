from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token, hash_password, validate_password_complexity, validate_email_domain
from app.models.user import User, UserRole
from app.models.phase13_models import SSOConfiguration, SSOAuditLog
from app.models.admin_audit_log import AdminAuditLog
from app.schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from app.schemas.user import UserOut
from app.api.deps import get_current_user
from app.services.lockout_service import check_login_lockout, record_login_attempt

router = APIRouter(prefix="/auth", tags=["Authentication"])

SEEDED_DEFAULT_EMAILS = {
    "admin.demo@csm.tech", "mentor.demo@csm.tech", "ase.demo@csm.tech",
    "demo.aarav.sharma@csm.tech", "demo.diya.patel@csm.tech", "demo.rohan.gupta@csm.tech",
    "demo.ananya.verma@csm.tech", "demo.kabir.mehta@csm.tech", "demo.ishita.roy@csm.tech",
    "demo.priya.patel@csm.tech", "demo.rohan.verma@csm.tech", "demo.sneha.rao@csm.tech",
    "demo.vikram.malhotra@csm.tech", "demo.ananya.deshmukh@csm.tech"
}

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip_addr = _get_client_ip(request)
    ua = request.headers.get("user-agent", "Unknown")[:300]
    email = validate_email_domain(payload.email)

    # Check lockout per-account and per-IP
    lockout_err = check_login_lockout(db, email, ip_addr, is_break_glass=False)
    if lockout_err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=lockout_err
        )

    user = db.query(User).filter(User.email == email).first()

    # Check local login toggle
    conf = db.query(SSOConfiguration).first()
    allow_local = conf.allow_local_login if conf else settings.ALLOW_LOCAL_LOGIN

    if not allow_local:
        # Local login disabled for general users. Check for Break-Glass Admin access.
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Local password login has been disabled by your administrator. Please use Sign in with Microsoft."
            )
        # Break-glass admin login path
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact an Administrator."
            )
        if not verify_password(payload.password, user.hashed_password):
            record_login_attempt(db, email, ip_addr, is_success=False, is_break_glass=True, failure_reason="INVALID_PASSWORD")
            audit = SSOAuditLog(
                user_id=user.id,
                event_type="BREAK_GLASS_FAILED",
                upn=user.email,
                failure_reason="INVALID_PASSWORD",
                ip_address=ip_addr,
                user_agent=ua
            )
            db.add(audit)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        record_login_attempt(db, email, ip_addr, is_success=True, is_break_glass=True)
        audit = SSOAuditLog(
            user_id=user.id,
            event_type="BREAK_GLASS_LOGIN",
            upn=user.email,
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        user.fresh_login = True
        db.commit()

        access_token = create_access_token(subject=user.id, role=user.role.value)
        must_change = getattr(user, "must_change_password", False)
        if settings.APP_ENV.lower() == "production" and (user.is_demo or user.email in SEEDED_DEFAULT_EMAILS):
            if must_change is not False:
                must_change = True
                user.must_change_password = True
                db.commit()

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            must_change_password=must_change
        )

    # Standard Local Login Flow
    if not user:
        record_login_attempt(db, email, ip_addr, is_success=False, failure_reason="USER_NOT_FOUND")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an Administrator.",
        )
    if not verify_password(payload.password, user.hashed_password):
        record_login_attempt(db, email, ip_addr, is_success=False, failure_reason="INVALID_PASSWORD")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    record_login_attempt(db, email, ip_addr, is_success=True)
    user.fresh_login = True
    db.commit()

    must_change = getattr(user, "must_change_password", False)
    if settings.APP_ENV.lower() == "production" and (user.is_demo or user.email in SEEDED_DEFAULT_EMAILS):
        if must_change is not False:
            must_change = True
            user.must_change_password = True
            db.commit()

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        must_change_password=must_change
    )

@router.post("/login/break-glass", response_model=TokenResponse)
def break_glass_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Dedicated Break-Glass Admin Emergency Login Route.
    Isolated rate limit: max 3 attempts per minute per IP/account.
    Cannot be disabled by SSO toggles or blocked by general login flood.
    """
    ip_addr = _get_client_ip(request)
    ua = request.headers.get("user-agent", "Unknown")[:300]
    email = validate_email_domain(payload.email)

    lockout_err = check_login_lockout(db, email, ip_addr, is_break_glass=True)
    if lockout_err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=lockout_err
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or user.role != UserRole.ADMIN:
        record_login_attempt(db, email, ip_addr, is_success=False, is_break_glass=True, failure_reason="NON_ADMIN_ACCESS")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Emergency break-glass login is restricted to System Administrators only."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is deactivated. Contact secondary admin."
        )

    if not verify_password(payload.password, user.hashed_password):
        record_login_attempt(db, email, ip_addr, is_success=False, is_break_glass=True, failure_reason="INVALID_PASSWORD")
        audit = SSOAuditLog(
            user_id=user.id,
            event_type="BREAK_GLASS_FAILED",
            upn=user.email,
            failure_reason="INVALID_PASSWORD",
            ip_address=ip_addr,
            user_agent=ua
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials"
        )

    record_login_attempt(db, email, ip_addr, is_success=True, is_break_glass=True)
    audit = SSOAuditLog(
        user_id=user.id,
        event_type="BREAK_GLASS_LOGIN",
        upn=user.email,
        ip_address=ip_addr,
        user_agent=ua
    )
    db.add(audit)
    user.fresh_login = True
    db.commit()

    access_token = create_access_token(subject=user.id, role=user.role.value)
    must_change = getattr(user, "must_change_password", False)
    if settings.APP_ENV.lower() == "production" and (user.is_demo or user.email in SEEDED_DEFAULT_EMAILS):
        if must_change is not False:
            must_change = True
            user.must_change_password = True
            db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        must_change_password=must_change
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    mentor_id = None
    mentor_name = None
    if current_user.mentor_assignment and current_user.mentor_assignment.mentor:
        mentor_id = current_user.mentor_assignment.mentor.id
        mentor_name = current_user.mentor_assignment.mentor.name

    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        must_change_password=getattr(current_user, "must_change_password", False),
        created_at=current_user.created_at,
        assigned_mentor_id=mentor_id,
        assigned_mentor_name=mentor_name
    )

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    is_valid, err_msg = validate_password_complexity(payload.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_msg
        )
    
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False
    db.commit()

    return {
        "message": "Password changed successfully",
        "must_change_password": False
    }
