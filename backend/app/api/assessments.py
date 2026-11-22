from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.question import AssessmentType, QuestionBank
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.schemas.assessment import AssessmentCreate, AssessmentOut, SectionOut, AssessmentWebcamUpdate
from app.api.deps import require_admin, require_mentor_or_admin

router = APIRouter(prefix="/assessments", tags=["Assessments"])

def _build_assessment_out(a: Assessment, include_details: bool = False) -> AssessmentOut:
    total_sections = len(a.sections) if a.sections else 0
    total_questions = 0
    total_marks = 0

    section_outs = []
    if a.sections:
        for s in a.sections:
            q_count = len(s.section_questions) if s.section_questions else 0
            total_questions += q_count
            
            questions_out = []
            if include_details and s.section_questions:
                for sq in s.section_questions:
                    total_marks += sq.question.marks
                    questions_out.append(sq.question)
            elif s.section_questions:
                for sq in s.section_questions:
                    total_marks += sq.question.marks

            section_outs.append(SectionOut(
                id=s.id,
                title=s.title,
                order_index=s.order_index,
                timer_minutes=s.timer_minutes,
                question_count=q_count,
                questions=questions_out if include_details else None
            ))

    return AssessmentOut(
        id=a.id,
        title=a.title,
        type=a.type,
        total_duration_minutes=a.total_duration_minutes,
        passing_percentage=a.passing_percentage,
        randomize_questions=a.randomize_questions,
        randomize_options=a.randomize_options,
        created_at=a.created_at,
        webcam_mode=getattr(a, "webcam_mode", "OFF") or "OFF",
        webcam_policy=getattr(a, "webcam_policy", "WARNING_ONLY") or "WARNING_ONLY",
        camera_no_face_seconds=getattr(a, "camera_no_face_seconds", 10) or 10,
        camera_multiple_faces_seconds=getattr(a, "camera_multiple_faces_seconds", 5) or 5,
        camera_head_turn_seconds=getattr(a, "camera_head_turn_seconds", 12) or 12,
        camera_grace_period_seconds=getattr(a, "camera_grace_period_seconds", 30) or 30,
        total_sections=total_sections,
        total_questions=total_questions,
        total_marks=total_marks,
        sections=section_outs
    )

@router.get("", response_model=List[AssessmentOut])
def list_assessments(
    type: Optional[AssessmentType] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    query = db.query(Assessment)
    if type:
        query = query.filter(Assessment.type == type)
    assessments = query.order_by(Assessment.id.desc()).all()
    return [_build_assessment_out(a, include_details=False) for a in assessments]

@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if not payload.sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one section is required to create an assessment"
        )

    # 1. Create Assessment header
    assessment = Assessment(
        title=payload.title.strip(),
        type=payload.type,
        total_duration_minutes=payload.total_duration_minutes,
        passing_percentage=payload.passing_percentage,
        randomize_questions=payload.randomize_questions,
        randomize_options=payload.randomize_options,
        webcam_mode=payload.webcam_mode,
        webcam_policy=payload.webcam_policy,
        camera_no_face_seconds=payload.camera_no_face_seconds,
        camera_multiple_faces_seconds=payload.camera_multiple_faces_seconds,
        camera_head_turn_seconds=payload.camera_head_turn_seconds,
        camera_grace_period_seconds=payload.camera_grace_period_seconds,
        created_by=admin.id
    )
    db.add(assessment)
    db.flush()

    # 2. Add sections and question mappings
    for idx, sec_data in enumerate(payload.sections):
        section = AssessmentSection(
            assessment_id=assessment.id,
            title=sec_data.title.strip(),
            order_index=idx,
            timer_minutes=sec_data.timer_minutes
        )
        db.add(section)
        db.flush()

        for q_idx, q_id in enumerate(sec_data.question_ids):
            # Verify question exists
            q = db.query(QuestionBank).filter(QuestionBank.id == q_id).first()
            if not q:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Question with ID {q_id} does not exist in Question Bank"
                )
            sq = AssessmentSectionQuestion(
                section_id=section.id,
                question_id=q_id,
                order_index=q_idx
            )
            db.add(sq)

    db.commit()
    db.refresh(assessment)
    return _build_assessment_out(assessment, include_details=True)

@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return _build_assessment_out(assessment, include_details=True)

@router.patch("/{assessment_id}/webcam-config", response_model=AssessmentOut)
def update_assessment_webcam_config(
    assessment_id: int,
    payload: AssessmentWebcamUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if payload.webcam_mode is not None:
        if payload.webcam_mode not in ["OFF", "ADVISORY", "REQUIRED"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid webcam_mode")
        assessment.webcam_mode = payload.webcam_mode

    if payload.webcam_policy is not None:
        if payload.webcam_policy not in ["WARNING_ONLY", "COUNTED_STRIKES"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid webcam_policy")
        assessment.webcam_policy = payload.webcam_policy

    if payload.camera_no_face_seconds is not None:
        assessment.camera_no_face_seconds = payload.camera_no_face_seconds
    if payload.camera_multiple_faces_seconds is not None:
        assessment.camera_multiple_faces_seconds = payload.camera_multiple_faces_seconds
    if payload.camera_head_turn_seconds is not None:
        assessment.camera_head_turn_seconds = payload.camera_head_turn_seconds
    if payload.camera_grace_period_seconds is not None:
        assessment.camera_grace_period_seconds = payload.camera_grace_period_seconds

    db.commit()
    db.refresh(assessment)
    return _build_assessment_out(assessment, include_details=True)


@router.delete("/{assessment_id}", status_code=status.HTTP_200_OK)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    db.delete(assessment)
    db.commit()
    return {"message": "Assessment deleted successfully", "id": assessment_id}
