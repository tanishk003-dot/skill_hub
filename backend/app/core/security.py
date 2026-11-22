from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import jwt
import bcrypt
from fastapi import HTTPException, status
from app.core.config import settings

def validate_email_domain(email: str) -> str:
    """
    Normalizes email (trim, lowercase) and enforces ALLOWED_EMAIL_DOMAINS.
    Raises HTTP 400 Bad Request with 'Use your @<domain> email' if domain is not allowed.
    """
    if not email or "@" not in email:
        allowed = [d.strip().lower() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
        primary = allowed[0] if allowed else "csm.tech"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Use your @{primary} email"
        )
    normalized = email.strip().lower()
    allowed = [d.strip().lower() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
    if not allowed:
        return normalized
    domain = normalized.split("@")[-1]
    if domain not in allowed:
        primary = allowed[0]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Use your @{primary} email"
        )
    return normalized

def hash_password(password: str) -> str:
    # bcrypt max length is 72 bytes
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(subject: Union[str, Any], role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def validate_password_complexity(password: str) -> tuple[bool, Optional[str]]:
    """
    Validates password complexity against enterprise security standards:
    - Min 8 chars
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 numeric digit
    - At least 1 special character
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long."
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/`~" for c in password):
        return False, "Password must contain at least one special symbol."
    return True, None
