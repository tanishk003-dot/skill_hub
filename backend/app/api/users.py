from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, validate_password_complexity, validate_email_domain
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.admin_audit_log import AdminAuditLog
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.api.deps import require_admin

router = APIRouter(prefix="/users", tags=["User Management"])

def _build_user_out(user: User) -> UserOut:
    mentor_id = None
    mentor_name = None
    if user.mentor_assignment and user.mentor_assignment.mentor:
        mentor_id = user.mentor_assignment.mentor.id
        mentor_name = user.mentor_assignment.mentor.name

    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        must_change_password=getattr(user, "must_change_password", False),
        created_at=user.created_at,
        assigned_mentor_id=mentor_id,
        assigned_mentor_name=mentor_name
    )

@router.get("", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    include_inactive: bool = Query(False, description="Include soft-deleted/inactive users"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active == True)
    if role:
        query = query.filter(User.role == role)
    
    users = query.order_by(User.id.desc()).all()
    return [_build_user_out(u) for u in users]

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    email = validate_email_domain(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email}' already exists"
        )
    
    is_valid, err_msg = validate_password_complexity(payload.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_msg
        )

    hashed = hash_password(payload.password)
    new_user = User(
        name=payload.name.strip(),
        email=email,
        hashed_password=hashed,
        role=payload.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit = AdminAuditLog(
        actor_id=admin.id,
        actor_email=admin.email,
        action="USER_CREATE",
        target_type="USER",
        target_id=str(new_user.id),
        details=f"Created user {new_user.email} with role {new_user.role}"
    )
    db.add(audit)
    db.commit()

    return _build_user_out(new_user)

@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return _build_user_out(user)

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if payload.email is not None:
        new_email = validate_email_domain(payload.email)
        if new_email != user.email:
            existing = db.query(User).filter(User.email == new_email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{new_email}' is already in use by another account"
                )
            user.email = new_email

    if payload.name is not None:
        user.name = payload.name.strip()
    
    if payload.password is not None and payload.password.strip():
        is_valid, err_msg = validate_password_complexity(payload.password.strip())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err_msg
            )
        user.hashed_password = hash_password(payload.password.strip())
        
    if payload.role is not None:
        # If changing role away from ASE or MENTOR, clean up invalid assignments
        if payload.role != user.role:
            if user.role == UserRole.ASE and payload.role != UserRole.ASE:
                db.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == user.id).delete()
            elif user.role == UserRole.MENTOR and payload.role != UserRole.MENTOR:
                db.query(MentorAseAssignment).filter(MentorAseAssignment.mentor_id == user.id).delete()
        user.role = payload.role
        
    if payload.is_active is not None:
        user.is_active = payload.is_active

    audit = AdminAuditLog(
        actor_id=admin.id,
        actor_email=admin.email,
        action="USER_UPDATE",
        target_type="USER",
        target_id=str(user.id),
        details=f"Updated user {user.email} (role: {user.role}, active: {user.is_active})"
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return _build_user_out(user)

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own active account"
        )
    
    # Soft delete: set is_active = False
    user.is_active = False
    
    # Remove existing assignment mapping if present to free up ASE/Mentor
    db.query(MentorAseAssignment).filter(
        (MentorAseAssignment.mentor_id == user.id) | (MentorAseAssignment.ase_id == user.id)
    ).delete()

    audit = AdminAuditLog(
        actor_id=admin.id,
        actor_email=admin.email,
        action="USER_DELETE",
        target_type="USER",
        target_id=str(user.id),
        details=f"Soft-deleted user {user.email}"
    )
    db.add(audit)
    db.commit()
    return {"message": f"User '{user.name}' soft-deleted successfully", "id": user.id, "is_active": False}
