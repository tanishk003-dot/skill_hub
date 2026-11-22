from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.services.export_service import (
    get_export_data,
    generate_csv_string,
    generate_excel_bytes
)

router = APIRouter(prefix="/export", tags=["Exports (Excel & CSV)"])

@router.get("/{entity}")
def export_entity_data(
    entity: str,
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    include_pii: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports system data to Excel (.xlsx) or CSV with formula injection protection.
    Role-scoped: Mentors can only export data for their assigned mentees.
    PII (names/emails) is stripped by default unless admin opts in.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.MENTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only mentors and administrators can export data."
        )

    # Only admin can request PII export; mentors can see their own mentees' names
    if include_pii and current_user.role != UserRole.ADMIN:
        include_pii = False

    data = get_export_data(
        db=db,
        entity=entity,
        requesting_user=current_user,
        include_pii=include_pii
    )

    filename_base = f"skillhub_{entity}_{current_user.role.value.lower()}"

    if format == "csv":
        csv_content = generate_csv_string(data)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename_base}.csv",
                "Cache-Control": "no-cache"
            }
        )
    else:
        excel_bytes = generate_excel_bytes(data, sheet_title=entity.capitalize())
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename_base}.xlsx",
                "Cache-Control": "no-cache"
            }
        )
