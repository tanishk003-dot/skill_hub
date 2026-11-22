from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.datetime_util import utc_now
from app.models.user import User
from app.models.login_lockout import LoginAttempt
from app.models.admin_audit_log import AdminAuditLog

def check_login_lockout(
    db: Session,
    email: str,
    ip_address: str,
    is_break_glass: bool = False
) -> Optional[str]:
    """
    Checks per-account and per-IP lockout constraints.
    Returns error message if locked out, None if permitted.
    """
    now = datetime.now(timezone.utc)

    # 1. Break-Glass Isolated Rate Limiting
    if is_break_glass:
        one_min_ago = now - timedelta(minutes=1)
        recent_bg_fails = db.query(LoginAttempt).filter(
            LoginAttempt.is_break_glass == True,
            LoginAttempt.is_success == False,
            LoginAttempt.attempted_at >= one_min_ago,
            (LoginAttempt.ip_address == ip_address) | (LoginAttempt.email == email)
        ).count()
        if recent_bg_fails >= settings.BREAK_GLASS_RATE_LIMIT_PER_MINUTE:
            return "Break-glass rate limit exceeded. Please wait 60 seconds before retrying."
        return None

    # 2. Per-IP Lockout (prevents brute force across accounts)
    fifteen_min_ago = now - timedelta(minutes=15)
    ip_fails = db.query(LoginAttempt).filter(
        LoginAttempt.ip_address == ip_address,
        LoginAttempt.is_success == False,
        LoginAttempt.attempted_at >= fifteen_min_ago
    ).count()

    if ip_fails >= 15:
        return "Too many failed login attempts from this network address. Please wait 15 minutes before retrying."

    # 3. Per-Account Lockout with Exponential Backoff
    user = db.query(User).filter(User.email == email).first()
    if user:
        if user.is_locked:
            return "This account has been administratively locked. Please contact your system administrator."
        
        if user.lockout_until:
            lockout_expiry = user.lockout_until
            # Ensure timezone awareness for comparison
            if lockout_expiry.tzinfo is None:
                lockout_expiry = lockout_expiry.replace(tzinfo=timezone.utc)

            if now < lockout_expiry:
                remaining_secs = max(1, int((lockout_expiry - now).total_seconds()))
                return (
                    f"Account temporarily locked due to consecutive failed attempts. "
                    f"Please retry in {remaining_secs} seconds or contact an administrator to unlock your account."
                )
            else:
                # Lockout period elapsed: clear lockout
                user.lockout_until = None
                db.commit()

    return None

def record_login_attempt(
    db: Session,
    email: str,
    ip_address: str,
    is_success: bool,
    is_break_glass: bool = False,
    failure_reason: Optional[str] = None
) -> None:
    """
    Records login attempt and updates user lockout state with exponential backoff on failure.
    """
    now = datetime.now(timezone.utc)
    attempt = LoginAttempt(
        email=email,
        ip_address=ip_address,
        is_success=is_success,
        is_break_glass=is_break_glass,
        failure_reason=failure_reason,
        attempted_at=now
    )
    db.add(attempt)

    user = db.query(User).filter(User.email == email).first()
    if user:
        if is_success:
            user.failed_login_attempts = 0
            user.lockout_until = None
            user.is_locked = False
        else:
            if not is_break_glass:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                    # Exponential backoff calculation:
                    # 5 fails: 60s * 2^0 = 60s (1 min)
                    # 6 fails: 60s * 2^1 = 120s (2 min)
                    # 7 fails: 60s * 2^2 = 240s (4 min)
                    # 8 fails: 60s * 2^3 = 480s (8 min)
                    # capped at LOGIN_LOCKOUT_MAX_SECONDS (1800s = 30 min)
                    exponent = user.failed_login_attempts - settings.LOGIN_MAX_FAILED_ATTEMPTS
                    delay_seconds = min(
                        settings.LOGIN_LOCKOUT_BASE_SECONDS * (2 ** min(exponent, 6)),
                        settings.LOGIN_LOCKOUT_MAX_SECONDS
                    )
                    user.lockout_until = now + timedelta(seconds=delay_seconds)

    db.commit()

def unlock_account_by_admin(
    db: Session,
    user_id: int,
    admin_user: User,
    ip_address: str = "127.0.0.1",
    user_agent: str = "Unknown"
) -> User:
    """
    Allows an administrator to immediately unlock a locked user account.
    Records the event to append-only admin_audit_logs.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise ValueError("User not found")

    target.failed_login_attempts = 0
    target.lockout_until = None
    target.is_locked = False

    audit = AdminAuditLog(
        actor_id=admin_user.id,
        actor_email=admin_user.email,
        action="USER_UNLOCK",
        target_type="USER",
        target_id=str(target.id),
        details=f"Administrator unlocked account for user {target.email}",
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit)
    db.commit()
    db.refresh(target)
    return target
