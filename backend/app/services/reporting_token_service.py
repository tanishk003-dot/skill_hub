import secrets
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.models.user import User, UserRole
from app.models.phase11_models import ReportingApiToken, ReportingTokenAuditLog
from app.models.phase9_models import AseReadinessHistory
from app.services.export_service import get_export_data, generate_pseudonymous_id

def get_utc_now():
    return datetime.now(timezone.utc)

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_reporting_token(
    db: Session,
    admin_user: User,
    name: str,
    scopes: List[str],
    expires_in_days: int = 90,
    include_pii: bool = False,
    allowed_ips: Optional[List[str]] = None,
    is_demo: bool = False
) -> Dict[str, Any]:
    """Generates a new scoped Power BI reporting token. Plaintext returned ONCE."""
    if admin_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can generate reporting API tokens.")

    raw_token = f"rpt_{secrets.token_hex(24)}"
    token_h = hash_token(raw_token)
    expires_at = get_utc_now() + timedelta(days=expires_in_days)

    db_token = ReportingApiToken(
        name=name,
        token_hash=token_h,
        created_by_admin_id=admin_user.id,
        scopes=scopes,
        include_pii=include_pii,
        allowed_ips=allowed_ips,
        expires_at=expires_at,
        is_revoked=False,
        is_demo=is_demo
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return {
        "id": db_token.id,
        "name": db_token.name,
        "token": raw_token,  # Shown only once!
        "scopes": db_token.scopes,
        "include_pii": db_token.include_pii,
        "allowed_ips": db_token.allowed_ips,
        "expires_at": db_token.expires_at.isoformat(),
        "created_at": db_token.created_at.isoformat()
    }


def revoke_reporting_token(db: Session, token_id: int, admin_user: User) -> ReportingApiToken:
    if admin_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can revoke reporting tokens.")

    token = db.query(ReportingApiToken).filter(ReportingApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reporting token not found.")

    token.is_revoked = True
    db.commit()
    db.refresh(token)
    return token


# In-memory rate limiting for reporting tokens: token_id -> list of timestamps
_REPORTING_RATE_LOG: Dict[int, List[datetime]] = {}

def validate_reporting_token(
    db: Session,
    auth_header: Optional[str],
    required_scope: str,
    client_ip: Optional[str] = None
) -> ReportingApiToken:
    """Validates the Authorization Bearer header, scope, expiration, IP, and rate limit."""
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer rpt_...'"
        )

    raw_token = auth_header.split(" ", 1)[1].strip()
    if not raw_token.startswith("rpt_"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format.")

    token_h = hash_token(raw_token)
    db_token = db.query(ReportingApiToken).filter(ReportingApiToken.token_hash == token_h).first()

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unrecognized reporting token.")

    if db_token.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reporting token has been revoked.")

    now = get_utc_now()
    # Check expiration (ensure tz-aware)
    exp = db_token.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reporting token has expired.")

    # Scope validation
    if required_scope not in (db_token.scopes or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token missing required scope '{required_scope}'."
        )

    # IP allowlist validation
    if db_token.allowed_ips and client_ip:
        if client_ip not in db_token.allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP address '{client_ip}' is not authorized for this token."
            )

    # Rate limiting: max 60 calls/minute
    one_min_ago = now - timedelta(minutes=1)
    timestamps = [t for t in _REPORTING_RATE_LOG.get(db_token.id, []) if t > one_min_ago]
    if len(timestamps) >= 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: 60 requests per minute."
        )
    timestamps.append(now)
    _REPORTING_RATE_LOG[db_token.id] = timestamps

    # Update last used
    db_token.last_used_at = now
    db.commit()

    return db_token


def log_token_access(db: Session, token_id: int, endpoint: str, client_ip: Optional[str] = None):
    audit = ReportingTokenAuditLog(
        token_id=token_id,
        endpoint=endpoint,
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()


def get_reporting_entity_flat_data(
    db: Session,
    token: ReportingApiToken,
    entity: str
) -> List[Dict[str, Any]]:
    """Generates Power BI-friendly flat JSON."""
    if entity == "readiness":
        scores = db.query(AseReadinessHistory).all()
        data = []
        for s in scores:
            cand_id = generate_pseudonymous_id(s.ase_id)
            row = {
                "readiness_id": s.id,
                "candidate_id": cand_id,
                "readiness_score": s.overall_score,
                "calculated_at": s.calculated_at.isoformat() if s.calculated_at else None
            }
            if token.include_pii and s.ase:
                row["candidate_name"] = s.ase.name
                row["candidate_email"] = s.ase.email
            data.append(row)
        return data

    # Use export service with synthetic admin user
    dummy_admin = User(id=token.created_by_admin_id, role=UserRole.ADMIN, name="Admin")
    raw_data = get_export_data(db, entity, dummy_admin, include_pii=token.include_pii)
    
    # Flatten field names for Power BI (lowercase, underscores)
    flat_data = []
    for item in raw_data:
        flat_item = {}
        for k, v in item.items():
            clean_key = k.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("%", "pct")
            flat_item[clean_key] = v
        flat_data.append(flat_item)
    return flat_data
