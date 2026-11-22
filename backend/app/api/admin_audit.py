from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.admin_audit_log import AdminAuditLog
from app.api.deps import require_admin
from app.services.lockout_service import unlock_account_by_admin

router = APIRouter(prefix="/admin", tags=["Admin Audit & Governance"])

class AdminAuditLogOut(BaseModel):
    id: int
    actor_id: Optional[int]
    actor_email: str
    action: str
    target_type: str
    target_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminAuditLogOut]

@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_admin_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    actor_email: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Append-only view of all administrator governance and audit events.
    Restricted strictly to authenticated System Administrators.
    """
    query = db.query(AdminAuditLog)

    if action:
        query = query.filter(AdminAuditLog.action == action.strip().upper())
    if target_type:
        query = query.filter(AdminAuditLog.target_type == target_type.strip().upper())
    if actor_email:
        query = query.filter(AdminAuditLog.actor_email.ilike(f"%{actor_email.strip()}%"))
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (AdminAuditLog.action.ilike(s)) |
            (AdminAuditLog.details.ilike(s)) |
            (AdminAuditLog.actor_email.ilike(s)) |
            (AdminAuditLog.target_id.ilike(s))
        )

    total = query.count()
    items = query.order_by(desc(AdminAuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )

@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Allows an administrator to unlock a user account locked by failed login attempts.
    Append-only: creates an immutable entry in admin_audit_logs.
    """
    ip_addr = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "127.0.0.1")
    ua = request.headers.get("user-agent", "Unknown")[:300]
    try:
        user = unlock_account_by_admin(db, user_id, admin_user, ip_addr, ua)
        return {
            "message": f"User account {user.email} successfully unlocked.",
            "user_id": user.id,
            "status": "UNLOCKED"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
