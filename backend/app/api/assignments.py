from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.schemas.assignment import AssignRequest, AssignmentOut
from app.api.deps import require_admin

router = APIRouter(prefix="/assignments", tags=["Assignments"])

def _to_assignment_out(a: MentorAseAssignment) -> AssignmentOut:
    return AssignmentOut(
        id=a.id,
        mentor_id=a.mentor_id,
        mentor_name=a.mentor.name if a.mentor else "Unknown",
        mentor_email=a.mentor.email if a.mentor else "",
        ase_id=a.ase_id,
        ase_name=a.ase.name if a.ase else "Unknown",
        ase_email=a.ase.email if a.ase else "",
        assigned_at=a.assigned_at
    )

@router.get("", response_model=List[AssignmentOut])
def list_assignments(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    assignments = db.query(MentorAseAssignment).join(MentorAseAssignment.mentor).join(MentorAseAssignment.ase).all()
    return [_to_assignment_out(a) for a in assignments]

@router.post("", response_model=AssignmentOut)
def assign_ase_to_mentor(
    payload: AssignRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Verify Mentor
    mentor = db.query(User).filter(User.id == payload.mentor_id, User.is_active == True).first()
    if not mentor or mentor.role != UserRole.MENTOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid active Mentor required"
        )
    
    # Verify ASE
    ase = db.query(User).filter(User.id == payload.ase_id, User.is_active == True).first()
    if not ase or ase.role != UserRole.ASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid active ASE required"
        )
    
    # Check if ASE is already assigned
    existing = db.query(MentorAseAssignment).filter(MentorAseAssignment.ase_id == payload.ase_id).first()
    if existing:
        # Reassign to new mentor
        existing.mentor_id = payload.mentor_id
        db.commit()
        db.refresh(existing)
        return _to_assignment_out(existing)
    
    # Create new assignment
    new_assignment = MentorAseAssignment(
        mentor_id=payload.mentor_id,
        ase_id=payload.ase_id
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return _to_assignment_out(new_assignment)

@router.delete("/{assignment_id}", status_code=status.HTTP_200_OK)
def remove_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    assignment = db.query(MentorAseAssignment).filter(MentorAseAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    db.delete(assignment)
    db.commit()
    return {"message": "Assignment unassigned successfully", "id": assignment_id}
