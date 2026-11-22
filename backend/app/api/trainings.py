import os
import uuid
from datetime import datetime, timezone
from app.core.datetime_util import ensure_utc
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.cohort import Cohort, CohortMember
from app.models.training import Training, TrainingAssignment
from app.models.assessment_attempt import AssessmentAttempt
from app.schemas.training import (
    TrainingCreate, TrainingUpdate, TrainingOut, TrainingAssignPayload,
    TrainingProgressUpdate, TrainingAssignmentOut, SuggestedAseItem, ResourceItem
)
from app.services.notification_service import create_notification
from app.services.insights_service import mark_ai_insights_stale

router = APIRouter(prefix="/trainings", tags=["Trainings"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg", ".mp4"}
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB

def get_mentor_mentee_ids(db: Session, mentor_id: int) -> List[int]:
    rows = db.query(MentorAseAssignment.ase_id).filter(MentorAseAssignment.mentor_id == mentor_id).all()
    return [r[0] for r in rows]

@router.get("/", response_model=List[TrainingOut])
def list_trainings(
    skill_category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Training)
    if skill_category:
        query = query.filter(Training.skill_category.ilike(f"%{skill_category}%"))
    return query.order_by(Training.created_at.desc()).all()

@router.post("/", response_model=TrainingOut, status_code=status.HTTP_201_CREATED)
def create_training(
    payload: TrainingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins and Mentors can create trainings.")
    
    training = Training(
        title=payload.title,
        description=payload.description,
        skill_category=payload.skill_category,
        type=payload.type,
        resources=[r.model_dump() for r in payload.resources],
        duration_hours=payload.duration_hours,
        created_by=current_user.id
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training

@router.get("/{training_id}", response_model=TrainingOut)
def get_training(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training program not found.")
    return training

@router.put("/{training_id}", response_model=TrainingOut)
def update_training(
    training_id: int,
    payload: TrainingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to edit trainings.")
    
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training program not found.")
    
    if current_user.role == UserRole.MENTOR and training.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only edit their own trainings.")

    if payload.title is not None:
        training.title = payload.title
    if payload.description is not None:
        training.description = payload.description
    if payload.skill_category is not None:
        training.skill_category = payload.skill_category
    if payload.type is not None:
        training.type = payload.type
    if payload.resources is not None:
        training.resources = [r.model_dump() for r in payload.resources]
    if payload.duration_hours is not None:
        training.duration_hours = payload.duration_hours

    db.commit()
    db.refresh(training)
    return training

@router.delete("/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to delete trainings.")
    
    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training program not found.")
    
    if current_user.role == UserRole.MENTOR and training.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mentors can only delete their own trainings.")

    # Requirement 9: Deleting a training must not delete ASE users or assessment results
    db.delete(training)
    db.commit()
    return None

@router.post("/{training_id}/assign")
def assign_training(
    training_id: int,
    payload: TrainingAssignPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to assign trainings.")

    training = db.query(Training).filter(Training.id == training_id).first()
    if not training:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training program not found.")

    mentor_mentee_ids = get_mentor_mentee_ids(db, current_user.id) if current_user.role == UserRole.MENTOR else []

    target_ase_ids: List[int] = []

    if payload.target == "ALL":
        if current_user.role == UserRole.MENTOR:
            target_ase_ids = mentor_mentee_ids
        else:
            ases = db.query(User.id).filter(User.role == UserRole.ASE, User.is_active == True).all()
            target_ase_ids = [a[0] for a in ases]
    elif payload.target == "COHORT":
        if not payload.cohort_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cohort_id is required for COHORT target.")
        members = db.query(CohortMember.ase_id).filter(CohortMember.cohort_id == payload.cohort_id).all()
        cohort_ases = [m[0] for m in members]
        if current_user.role == UserRole.MENTOR:
            # Mentors can only assign to their own mentees within that cohort
            target_ase_ids = [aid for aid in cohort_ases if aid in mentor_mentee_ids]
        else:
            target_ase_ids = cohort_ases
    elif payload.target == "SELECTED":
        if not payload.ase_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ase_ids list cannot be empty.")
        if current_user.role == UserRole.MENTOR:
            unauthorized = [aid for aid in payload.ase_ids if aid not in mentor_mentee_ids]
            if unauthorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Mentors can assign trainings only to their own assigned mentees."
                )
        target_ase_ids = payload.ase_ids
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target type.")

    assigned_count = 0
    for ase_id in set(target_ase_ids):
        existing = db.query(TrainingAssignment).filter(
            TrainingAssignment.training_id == training_id,
            TrainingAssignment.ase_id == ase_id
        ).first()

        if existing:
            existing.due_date = payload.due_date
            if payload.cohort_id:
                existing.cohort_id = payload.cohort_id
            db.commit()
        else:
            new_assign = TrainingAssignment(
                training_id=training_id,
                ase_id=ase_id,
                cohort_id=payload.cohort_id,
                assigned_by=current_user.id,
                due_date=payload.due_date,
                status="NOT_STARTED",
                progress_percent=0.0
            )
            db.add(new_assign)
            db.commit()

            # Send Notification
            create_notification(
                db=db,
                user_id=ase_id,
                title=f"New Training Assigned: {training.title}",
                message=f"You have been assigned the training '{training.title}' ({training.skill_category}) due by {payload.due_date.strftime('%Y-%m-%d %H:%M UTC')}.",
                notification_type="TRAINING",
                link="/ase/learning"
            )
            mark_ai_insights_stale(db, ase_id)
        assigned_count += 1

    return {"message": f"Successfully assigned training to {assigned_count} engineer(s).", "count": assigned_count}

@router.get("/suggest-ases/{skill_category}", response_model=List[SuggestedAseItem])
def suggest_ases_for_training(
    skill_category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 2: Add a 'Suggest ASEs' button that pre-selects ASEs weak in the training's skill category (< 70%).
    Mentors see only their own mentees; Admin sees all.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to query suggestions.")

    mentor_mentee_ids = get_mentor_mentee_ids(db, current_user.id) if current_user.role == UserRole.MENTOR else None

    # Get all active ASEs
    ase_query = db.query(User).filter(User.role == UserRole.ASE, User.is_active == True)
    if mentor_mentee_ids is not None:
        ase_query = ase_query.filter(User.id.in_(mentor_mentee_ids))
    ases = ase_query.all()

    suggestions: List[SuggestedAseItem] = []

    for ase in ases:
        # Get their assessment attempts to compute skill score
        attempts = db.query(AssessmentAttempt).filter(
            AssessmentAttempt.ase_id == ase.id,
            AssessmentAttempt.status.in_(["SUBMITTED", "AUTO_SUBMITTED", "AUTO_SUBMITTED_VIOLATION"])
        ).all()

        skill_scores = []
        for att in attempts:
            if att.skill_scores and isinstance(att.skill_scores, dict):
                for k, v in att.skill_scores.items():
                    if skill_category.lower() in k.lower():
                        skill_scores.append(float(v))

        # Cohort info
        cohort_member = db.query(CohortMember).filter(CohortMember.ase_id == ase.id).first()
        cohort_id = cohort_member.cohort_id if cohort_member else None
        cohort_name = cohort_member.cohort.name if cohort_member and cohort_member.cohort else None

        if skill_scores:
            avg_score = sum(skill_scores) / len(skill_scores)
            if avg_score < 70.0:
                suggestions.append(SuggestedAseItem(
                    ase_id=ase.id,
                    ase_name=ase.name,
                    ase_email=ase.email,
                    cohort_id=cohort_id,
                    cohort_name=cohort_name,
                    skill_category=skill_category,
                    score_percentage=round(avg_score, 1),
                    reason=f"Scored {round(avg_score, 1)}% in assessments for {skill_category} (< 70% threshold)"
                ))
        else:
            # If no assessment attempts yet, candidate can also benefit from foundational training
            pass

    return suggestions

@router.get("/my-learning", response_model=List[TrainingAssignmentOut])
def get_my_learning(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 3: ASE 'My Learning' page: assigned trainings with progress, mark progress/complete, due dates, overdue badge.
    """
    now = datetime.now(timezone.utc)
    query = db.query(TrainingAssignment).filter(TrainingAssignment.ase_id == current_user.id)
    assignments = query.order_by(TrainingAssignment.due_date.asc()).all()

    results: List[TrainingAssignmentOut] = []
    for a in assignments:
        is_overdue = bool(a.due_date and ensure_utc(a.due_date) < now and a.status != "COMPLETED")
        results.append(TrainingAssignmentOut(
            id=a.id,
            training_id=a.training_id,
            training_title=a.training.title if a.training else "Training",
            training_description=a.training.description if a.training else None,
            skill_category=a.training.skill_category if a.training else "General",
            training_type=a.training.type if a.training else "Self-paced",
            duration_hours=a.training.duration_hours if a.training else 1.0,
            resources=[ResourceItem(**r) for r in (a.training.resources or [])] if a.training else [],
            ase_id=a.ase_id,
            ase_name=current_user.name,
            ase_email=current_user.email,
            cohort_id=a.cohort_id,
            cohort_name=a.cohort.name if a.cohort else None,
            due_date=a.due_date,
            status=a.status,
            progress_percent=a.progress_percent,
            completed_at=a.completed_at,
            is_overdue=is_overdue
        ))

    return results

@router.put("/assignments/{assignment_id}/progress")
def update_training_progress(
    assignment_id: int,
    payload: TrainingProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 5: Users can only update their own assignments (403 otherwise).
    """
    assignment = db.query(TrainingAssignment).filter(TrainingAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training assignment not found.")

    if current_user.role == UserRole.ASE and assignment.ase_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own training progress.")

    clamped_progress = max(0.0, min(100.0, payload.progress_percent))
    assignment.progress_percent = clamped_progress

    if clamped_progress >= 100.0 or payload.status == "COMPLETED":
        assignment.status = "COMPLETED"
        assignment.progress_percent = 100.0
        if not assignment.completed_at:
            assignment.completed_at = datetime.now(timezone.utc)
    elif clamped_progress > 0.0:
        assignment.status = "IN_PROGRESS"
    else:
        assignment.status = "NOT_STARTED"

    db.commit()
    db.refresh(assignment)

    return {
        "message": "Progress updated successfully.",
        "progress_percent": assignment.progress_percent,
        "status": assignment.status
    }

@router.post("/upload-resource")
async def upload_training_resource(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 7: Training file uploads: allow only pdf, docx, pptx, xlsx, png, jpg, mp4 up to 10 MB,
    store outside web root with randomized filenames, serve only to authorized users.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.MENTOR]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Admins and Mentors can upload resources.")

    original_filename = file.filename or "resource"
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed types: pdf, docx, pptx, xlsx, png, jpg, mp4"
        )

    # Read content to verify size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum permitted limit of 10 MB."
        )

    upload_folder = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_folder, exist_ok=True)

    random_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(upload_folder, random_name)

    with open(saved_path, "wb") as f:
        f.write(contents)

    return {
        "name": original_filename,
        "file_path": random_name,
        "url": f"/api/v1/trainings/resources/{random_name}",
        "type": "file"
    }

@router.get("/resources/{filename}")
def serve_training_resource(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Requirement 7: Serve only to authorized users.
    """
    # Prevent path traversal attacks
    clean_filename = os.path.basename(filename)
    upload_folder = os.path.abspath(settings.UPLOAD_DIR)
    target_file = os.path.join(upload_folder, clean_filename)

    if not os.path.isfile(target_file):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource file not found.")

    return FileResponse(target_file, filename=clean_filename)
