from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])

@router.get("/admin")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    total_mentors = db.query(User).filter(User.role == UserRole.MENTOR, User.is_active == True).count()
    total_ases = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True).count()
    total_assignments = db.query(MentorAseAssignment).join(
        User, MentorAseAssignment.ase_id == User.id
    ).filter(User.is_active == True).count()
    
    # ASEs without assignments
    assigned_ase_ids = [a.ase_id for a in db.query(MentorAseAssignment.ase_id).all()]
    unassigned_ases_count = db.query(User).filter(
        User.role == UserRole.ASE,
        User.is_active == True,
        ~User.id.in_(assigned_ase_ids) if assigned_ase_ids else True
    ).count()

    # Recent 5 users
    recent_users = db.query(User).filter(User.is_active == True).order_by(User.id.desc()).limit(5).all()

    return {
        "total_mentors": total_mentors,
        "total_ases": total_ases,
        "total_assignments": total_assignments,
        "unassigned_ases": unassigned_ases_count,
        "recent_users": [
            {"id": u.id, "name": u.name, "email": u.email, "role": u.role.value, "created_at": u.created_at}
            for u in recent_users
        ]
    }

@router.get("/mentor")
def get_mentor_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.MENTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentor dashboard is only accessible by Mentors or Admins"
        )
    
    assignments = db.query(MentorAseAssignment).filter(
        MentorAseAssignment.mentor_id == current_user.id
    ).all()

    mentees = []
    for a in assignments:
        if a.ase and a.ase.is_active:
            mentees.append({
                "id": a.ase.id,
                "name": a.ase.name,
                "email": a.ase.email,
                "role": a.ase.role.value,
                "assigned_at": a.assigned_at
            })

    return {
        "mentor_id": current_user.id,
        "mentor_name": current_user.name,
        "mentor_email": current_user.email,
        "total_mentees": len(mentees),
        "mentees": mentees
    }

@router.get("/ase")
def get_ase_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ASE and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ASE dashboard is only accessible by ASEs or Admins"
        )
    
    assignment = db.query(MentorAseAssignment).filter(
        MentorAseAssignment.ase_id == current_user.id
    ).first()

    mentor_info = None
    if assignment and assignment.mentor and assignment.mentor.is_active:
        mentor_info = {
            "id": assignment.mentor.id,
            "name": assignment.mentor.name,
            "email": assignment.mentor.email,
            "assigned_at": assignment.assigned_at
        }

    return {
        "ase_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "created_at": current_user.created_at,
        "has_mentor": mentor_info is not None,
        "mentor": mentor_info
    }
