from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty
from app.schemas.question import QuestionBankCreate, QuestionBankOut
from app.api.deps import require_admin, require_mentor_or_admin

router = APIRouter(prefix="/questions", tags=["Question Bank"])

@router.get("", response_model=List[QuestionBankOut])
def list_questions(
    type: Optional[AssessmentType] = Query(None, description="Filter by assessment type"),
    difficulty: Optional[QuestionDifficulty] = Query(None, description="Filter by difficulty"),
    skill: Optional[str] = Query(None, description="Filter by skill category"),
    search: Optional[str] = Query(None, description="Search text in question"),
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    query = db.query(QuestionBank)
    if type:
        query = query.filter(QuestionBank.type == type)
    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)
    if skill:
        query = query.filter(QuestionBank.skill_category.ilike(f"%{skill.strip()}%"))
    if search:
        query = query.filter(QuestionBank.question_text.ilike(f"%{search.strip()}%"))

    questions = query.order_by(QuestionBank.id.desc()).all()
    # Format options correctly if needed
    return questions

@router.post("", response_model=QuestionBankOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionBankCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    options_data = [opt.model_dump() for opt in payload.options]
    question = QuestionBank(
        type=payload.type,
        difficulty=payload.difficulty,
        skill_category=payload.skill_category.strip(),
        question_text=payload.question_text.strip(),
        question_type=payload.question_type,
        options=options_data,
        correct_answers=payload.correct_answers,
        marks=payload.marks
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question

@router.get("/{question_id}", response_model=QuestionBankOut)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_mentor_or_admin)
):
    q = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return q

@router.delete("/{question_id}", status_code=status.HTTP_200_OK)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    q = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"message": "Question deleted successfully", "id": question_id}
