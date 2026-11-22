from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.phase11_models import StaffingProject, StaffingProjectSkill
from app.schemas.phase11_schemas import StaffingProjectCreate, StaffingProjectUpdate
from app.services.matching_service import calculate_project_matches, MATCHING_DISCLAIMER

router = APIRouter(prefix="/staffing", tags=["Skill-to-Project Matching"])

@router.post("/projects")
def api_create_project(
    payload: StaffingProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates a new staffing project with required skills and competency thresholds."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators or delivery heads can create staffing projects."
        )

    project = StaffingProject(
        name=payload.name,
        description=payload.description,
        headcount=payload.headcount,
        start_date=payload.start_date,
        ready_now_threshold_pct=payload.ready_now_threshold_pct,
        status="PLANNING",
        created_by_user_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    for skill_data in payload.skills:
        skill = StaffingProjectSkill(
            project_id=project.id,
            skill_name=skill_data.skill_name,
            min_level_pct=skill_data.min_level_pct,
            weight=skill_data.weight
        )
        db.add(skill)

    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "headcount": project.headcount,
        "start_date": project.start_date.isoformat(),
        "ready_now_threshold_pct": project.ready_now_threshold_pct,
        "status": project.status,
        "skills": [
            {
                "id": s.id,
                "skill_name": s.skill_name,
                "min_level_pct": s.min_level_pct,
                "weight": s.weight
            }
            for s in project.skills
        ],
        "disclaimer": MATCHING_DISCLAIMER
    }


@router.get("/projects")
def api_list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists staffing projects.
    Admins and Mentors can view projects. ASEs cannot view projects (403 Forbidden).
    """
    if current_user.role == UserRole.ASE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ASEs are not authorized to view staffing projects."
        )

    projects = db.query(StaffingProject).order_by(StaffingProject.created_at.desc()).all()
    results = []
    for p in projects:
        results.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "headcount": p.headcount,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "ready_now_threshold_pct": p.ready_now_threshold_pct,
            "status": p.status,
            "skill_count": len(p.skills),
            "disclaimer": MATCHING_DISCLAIMER
        })
    return results


@router.get("/projects/{project_id}")
def api_get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns project details and required skills."""
    if current_user.role == UserRole.ASE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ASEs are not authorized to view staffing projects."
        )

    project = db.query(StaffingProject).filter(StaffingProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "headcount": project.headcount,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "ready_now_threshold_pct": project.ready_now_threshold_pct,
        "status": project.status,
        "skills": [
            {
                "id": s.id,
                "skill_name": s.skill_name,
                "min_level_pct": s.min_level_pct,
                "weight": s.weight
            }
            for s in project.skills
        ],
        "disclaimer": MATCHING_DISCLAIMER
    }


@router.get("/projects/{project_id}/matches")
def api_get_project_matches(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns candidate rankings for a project with skill gaps, recommended trainings,
    and 'Ready now / Ready in X weeks' classification.
    Role-scoped: Admins see all; Mentors see only their assigned mentees; ASEs get 403 Forbidden.
    """
    return calculate_project_matches(db, project_id, current_user)
