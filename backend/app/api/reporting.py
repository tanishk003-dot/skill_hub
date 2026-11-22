from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.phase11_models import ReportingApiToken
from app.schemas.phase11_schemas import ReportingTokenCreate, ReportingTokenOut
from app.services.reporting_token_service import (
    create_reporting_token,
    revoke_reporting_token,
    validate_reporting_token,
    log_token_access,
    get_reporting_entity_flat_data
)

router = APIRouter(prefix="/reporting", tags=["Power BI & External Reporting API"])

# ================= TOKEN MANAGEMENT (ADMIN ONLY) =================
@router.post("/tokens")
def api_create_reporting_token(
    payload: ReportingTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates a new scoped reporting API token. Plaintext token returned ONCE."""
    return create_reporting_token(
        db=db,
        admin_user=current_user,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
        include_pii=payload.include_pii,
        allowed_ips=payload.allowed_ips
    )


@router.get("/tokens", response_model=List[ReportingTokenOut])
def api_list_reporting_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin lists active and revoked reporting tokens."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can manage reporting tokens.")
    return db.query(ReportingApiToken).order_by(ReportingApiToken.created_at.desc()).all()


@router.delete("/tokens/{token_id}")
def api_revoke_reporting_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin revokes a reporting token."""
    revoked = revoke_reporting_token(db, token_id, current_user)
    return {"message": "Token revoked successfully", "token_id": revoked.id, "is_revoked": revoked.is_revoked}


# ================= DATA ENDPOINTS (AUTHENTICATED VIA REPORTING TOKEN ONLY) =================
@router.get("/{entity}")
def api_get_reporting_entity_data(
    entity: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Flat JSON export for Power BI reporting.
    Requires 'Authorization: Bearer rpt_...' header (tokens in query parameters are strictly rejected).
    """
    # Strict reject if token sent in query param
    if "token" in request.query_params or "api_key" in request.query_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tokens must NOT be passed in the URL. Use the Authorization header: 'Bearer rpt_...'"
        )

    client_ip = request.client.host if request.client else None
    token = validate_reporting_token(
        db=db,
        auth_header=authorization,
        required_scope=entity,
        client_ip=client_ip
    )

    log_token_access(db, token.id, f"/api/v1/reporting/{entity}", client_ip)

    return get_reporting_entity_flat_data(db, token, entity)
