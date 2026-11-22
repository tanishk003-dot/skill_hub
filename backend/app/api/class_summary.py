from datetime import datetime, timedelta, timezone
from typing import List, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.training import Training, TrainingAssignment
from app.models.notification import Notification
from app.models.question import QuestionBank, AssessmentType, QuestionDifficulty, QuestionType
from app.models.assessment import Assessment, AssessmentSection, AssessmentSectionQuestion
from app.models.assessment_assignment import AssessmentAssignment
from app.models.ai_class_summary import (
    ClassTranscript, ClassSummary, AIGeneratedAssessment,
    AIGeneratedQuestion, ClassEffectivenessReport, AIGenerateRateLog
)
from app.schemas.ai_class_summary import (
    TranscriptNotesCreate, ClassTranscriptResponse,
    ClassSummaryUpdate, ClassSummaryResponse,
    PlanRecommendationRequest, PlanRecommendationResponse,
    AssessmentGenerateRequest, AIGeneratedAssessmentResponse,
    AIGeneratedQuestionResponse, AIGeneratedQuestionUpdate,
    QuestionBankExportRequest, ClassEffectivenessResponse
)
from app.services.transcript_parser import (
    process_transcript_file, process_raw_notes, estimate_tokens
)
from app.services.ai_assessment_generator import (
    check_ai_rate_limits, record_ai_rate_log,
    generate_class_summary_ai, recommend_assessment_plan,
    generate_questions_for_plan, balance_options_and_randomize
)
from app.services.effectiveness_service import get_class_effectiveness_analytics

router = APIRouter(prefix="/class-summaries", tags=["AI Class Summaries & Assessment Generator"])

def verify_class_ownership(db: Session, current_user: User, live_class_id: Optional[int], training_id: Optional[int]):
    if live_class_id:
        lc = db.query(LiveClass).filter(LiveClass.id == live_class_id).first()
        if not lc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")
        if current_user.role == UserRole.MENTOR and lc.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this live class.")
        return lc, None
    elif training_id:
        tr = db.query(Training).filter(Training.id == training_id).first()
        if not tr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found.")
        if current_user.role == UserRole.MENTOR and tr.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You do not own this training.")
        return None, tr
    return None, None

# ============================================================================
# 1. Transcript Endpoints
# ============================================================================

@router.post("/transcripts/upload", response_model=ClassTranscriptResponse)
async def upload_transcript(
    file: UploadFile = File(...),
    live_class_id: Optional[int] = Form(None),
    training_id: Optional[int] = Form(None),
    topics_covered: Optional[str] = Form(None),
    privacy_consent_acknowledged: bool = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can upload transcripts.")

    verify_class_ownership(db, current_user, live_class_id, training_id)

    content_bytes = await file.read()
    parsed = process_transcript_file(content_bytes, file.filename, privacy_consent_acknowledged)

    # Set retention expiry
    expires = datetime.now(timezone.utc) + timedelta(days=settings.TRANSCRIPT_RETENTION_DAYS)

    transcript = ClassTranscript(
        live_class_id=live_class_id,
        training_id=training_id,
        uploaded_by=current_user.id,
        raw_text=parsed["raw_text"],
        topics_covered=topics_covered,
        file_name=file.filename,
        file_type=parsed["file_type"],
        privacy_consent_acknowledged=True,
        token_count=parsed["token_count"],
        used_token_count=parsed["used_token_count"],
        truncated_ratio=parsed["truncated_ratio"],
        expires_at=expires
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    return ClassTranscriptResponse(
        id=transcript.id,
        live_class_id=transcript.live_class_id,
        training_id=transcript.training_id,
        uploaded_by=transcript.uploaded_by,
        topics_covered=transcript.topics_covered,
        file_name=transcript.file_name,
        file_type=transcript.file_type,
        token_count=transcript.token_count,
        used_token_count=transcript.used_token_count,
        truncated_ratio=transcript.truncated_ratio,
        raw_text_present=bool(transcript.raw_text),
        expires_at=transcript.expires_at,
        created_at=transcript.created_at
    )

@router.post("/transcripts/notes", response_model=ClassTranscriptResponse)
def submit_notes_transcript(
    payload: TranscriptNotesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can submit notes.")

    verify_class_ownership(db, current_user, payload.live_class_id, payload.training_id)

    parsed = process_raw_notes(payload.notes or "", payload.topics_covered or "", payload.privacy_consent_acknowledged)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.TRANSCRIPT_RETENTION_DAYS)

    transcript = ClassTranscript(
        live_class_id=payload.live_class_id,
        training_id=payload.training_id,
        uploaded_by=current_user.id,
        raw_text=parsed["raw_text"],
        topics_covered=payload.topics_covered,
        file_name="pasted_notes.txt",
        file_type="notes",
        privacy_consent_acknowledged=True,
        token_count=parsed["token_count"],
        used_token_count=parsed["used_token_count"],
        truncated_ratio=parsed["truncated_ratio"],
        expires_at=expires
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)

    return ClassTranscriptResponse(
        id=transcript.id,
        live_class_id=transcript.live_class_id,
        training_id=transcript.training_id,
        uploaded_by=transcript.uploaded_by,
        topics_covered=transcript.topics_covered,
        file_name=transcript.file_name,
        file_type=transcript.file_type,
        token_count=transcript.token_count,
        used_token_count=transcript.used_token_count,
        truncated_ratio=transcript.truncated_ratio,
        raw_text_present=bool(transcript.raw_text),
        expires_at=transcript.expires_at,
        created_at=transcript.created_at
    )

@router.delete("/transcripts/{transcript_id}/raw")
def delete_raw_transcript_text(
    transcript_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transcript = db.query(ClassTranscript).filter(ClassTranscript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found.")

    verify_class_ownership(db, current_user, transcript.live_class_id, transcript.training_id)

    transcript.raw_text = None
    db.commit()
    return {"message": "Raw transcript text deleted successfully. Summaries preserved."}

# ============================================================================
# 2. Class Summary Endpoints
# ============================================================================

@router.post("/generate", response_model=ClassSummaryResponse)
def generate_summary(
    transcript_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can generate summaries.")

    transcript = db.query(ClassTranscript).filter(ClassTranscript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found.")

    verify_class_ownership(db, current_user, transcript.live_class_id, transcript.training_id)

    # Check daily rate limit
    check_ai_rate_limits(db, current_user.id, "SUMMARY")

    text_to_use = transcript.raw_text or transcript.topics_covered or "Core session concepts"
    summary_data = generate_class_summary_ai(text_to_use, transcript.topics_covered)

    summary = ClassSummary(
        transcript_id=transcript.id,
        live_class_id=transcript.live_class_id,
        training_id=transcript.training_id,
        created_by=current_user.id,
        key_topics=summary_data["key_topics"],
        key_concepts=summary_data["key_concepts"],
        practical_examples=summary_data["practical_examples"],
        ase_recap=summary_data["ase_recap"],
        suggested_homework=summary_data["suggested_homework"],
        is_published=False,
        version=1
    )
    db.add(summary)
    record_ai_rate_log(db, current_user.id, "SUMMARY", tokens_used=transcript.used_token_count)
    db.commit()
    db.refresh(summary)

    return summary

@router.get("/by-class/{live_class_id}", response_model=Optional[ClassSummaryResponse])
def get_summary_by_class(
    live_class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lc = db.query(LiveClass).filter(LiveClass.id == live_class_id).first()
    if not lc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class not found.")

    summary = db.query(ClassSummary).filter(ClassSummary.live_class_id == live_class_id).order_by(ClassSummary.id.desc()).first()
    if not summary:
        return None

    if current_user.role == UserRole.ASE:
        # ASEs can never see draft summaries!
        if not summary.is_published:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No published class summary available.")
        # Ensure ASE was invited to this class
        attendee = db.query(LiveClassAttendee).filter(
            LiveClassAttendee.live_class_id == live_class_id,
            LiveClassAttendee.ase_id == current_user.id
        ).first()
        if not attendee and lc.audience_type != "ALL":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this summary.")

    elif current_user.role == UserRole.MENTOR:
        if lc.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this live class.")

    return summary

@router.put("/{summary_id}", response_model=ClassSummaryResponse)
def update_summary(
    summary_id: int,
    payload: ClassSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can update summaries.")

    summary = db.query(ClassSummary).filter(ClassSummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found.")

    verify_class_ownership(db, current_user, summary.live_class_id, summary.training_id)

    if payload.key_topics is not None:
        summary.key_topics = payload.key_topics
    if payload.key_concepts is not None:
        summary.key_concepts = payload.key_concepts
    if payload.practical_examples is not None:
        summary.practical_examples = payload.practical_examples
    if payload.ase_recap is not None:
        summary.ase_recap = payload.ase_recap
    if payload.suggested_homework is not None:
        summary.suggested_homework = payload.suggested_homework

    summary.version += 1
    summary.updated_at = datetime.now(timezone.utc)

    # If already published, send notification about update
    if summary.is_published and summary.live_class_id:
        attendees = db.query(LiveClassAttendee).filter(LiveClassAttendee.live_class_id == summary.live_class_id).all()
        for att in attendees:
            notif = Notification(
                user_id=att.ase_id,
                title="Class Summary Updated",
                message=f"The mentor updated the summary for class #{summary.live_class_id} (version {summary.version}).",
                type="TRAINING",
                link="/ase/learning"
            )
            db.add(notif)

    db.commit()
    db.refresh(summary)
    return summary

@router.post("/{summary_id}/publish", response_model=ClassSummaryResponse)
def publish_summary(
    summary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can publish summaries.")

    summary = db.query(ClassSummary).filter(ClassSummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found.")

    verify_class_ownership(db, current_user, summary.live_class_id, summary.training_id)

    summary.is_published = True
    summary.published_at = datetime.now(timezone.utc)

    # Send notifications to ASEs
    if summary.live_class_id:
        attendees = db.query(LiveClassAttendee).filter(LiveClassAttendee.live_class_id == summary.live_class_id).all()
        for att in attendees:
            notif = Notification(
                user_id=att.ase_id,
                title="New Class Summary Published",
                message=f"A structured class recap is now available for your review in My Learning.",
                type="TRAINING",
                link="/ase/learning"
            )
            db.add(notif)

    db.commit()
    db.refresh(summary)
    return summary

@router.post("/{summary_id}/unpublish", response_model=ClassSummaryResponse)
def unpublish_summary(
    summary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can unpublish summaries.")

    summary = db.query(ClassSummary).filter(ClassSummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found.")

    verify_class_ownership(db, current_user, summary.live_class_id, summary.training_id)

    summary.is_published = False
    db.commit()
    db.refresh(summary)
    return summary

# ============================================================================
# 3. AI Assessment Generation & Review Endpoints
# ============================================================================

@router.post("/recommend-plan", response_model=PlanRecommendationResponse)
def recommend_plan(
    payload: PlanRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can request assessment plans.")

    summary = db.query(ClassSummary).filter(ClassSummary.id == payload.summary_id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found.")

    verify_class_ownership(db, current_user, summary.live_class_id, summary.training_id)

    plan = recommend_assessment_plan(
        summary={"key_topics": summary.key_topics},
        transcript_text=summary.ase_recap
    )
    return PlanRecommendationResponse(**plan)

@router.post("/assessments/generate", response_model=AIGeneratedAssessmentResponse)
def generate_assessment(
    payload: AssessmentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can generate assessments.")

    verify_class_ownership(db, current_user, payload.live_class_id, payload.training_id)

    # Check rate limit and max questions per call
    check_ai_rate_limits(db, current_user.id, "ASSESSMENT_GENERATE", requested_questions=payload.recommended_total_questions)

    # Fetch latest summary if available
    summary_obj = None
    if payload.live_class_id:
        summary_obj = db.query(ClassSummary).filter(ClassSummary.live_class_id == payload.live_class_id).order_by(ClassSummary.id.desc()).first()

    summary_dict = {
        "key_topics": summary_obj.key_topics if summary_obj else ["System Architecture", "Reliability", "Testing"]
    }

    # Generate questions
    raw_questions = generate_questions_for_plan(
        db=db,
        mentor_id=current_user.id,
        plan={
            "recommended_total_questions": payload.recommended_total_questions,
            "topic_split": payload.topic_split or {},
            "difficulty_split": payload.difficulty_split
        },
        summary=summary_dict,
        generation_mode=payload.generation_mode,
        skill_category=payload.skill_category or "Software Engineering"
    )

    ai_assessment = AIGeneratedAssessment(
        live_class_id=payload.live_class_id,
        training_id=payload.training_id,
        created_by=current_user.id,
        title=payload.title,
        generation_mode=payload.generation_mode,
        status="DRAFT",
        recommended_total_questions=payload.recommended_total_questions,
        difficulty_split=payload.difficulty_split,
        topic_split=payload.topic_split or {},
        is_immutable=False,
        version=1
    )
    db.add(ai_assessment)
    db.flush()

    for q in raw_questions:
        q_record = AIGeneratedQuestion(
            ai_assessment_id=ai_assessment.id,
            question_bank_id=q.get("question_bank_id"),
            question_type=q.get("question_type", "SINGLE_CHOICE"),
            skill_category=q.get("skill_category", "Software Engineering"),
            difficulty=q.get("difficulty", "MEDIUM"),
            question_text=q.get("question_text"),
            options=q.get("options", []),
            correct_answers=q.get("correct_answers", []),
            explanation=q.get("explanation", ""),
            source=q.get("source", "AI generated"),
            review_status=q.get("review_status", "PENDING"),
            mentor_verify_required=q.get("mentor_verify_required", False),
            quality_flags=q.get("quality_flags", [])
        )
        db.add(q_record)

    record_ai_rate_log(db, current_user.id, "ASSESSMENT_GENERATE", question_count=len(raw_questions))
    db.commit()
    db.refresh(ai_assessment)
    return ai_assessment

@router.get("/assessments/{assessment_id}", response_model=AIGeneratedAssessmentResponse)
def get_ai_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can view AI assessments.")

    ass = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Assessment not found.")

    verify_class_ownership(db, current_user, ass.live_class_id, ass.training_id)
    return ass

@router.put("/questions/{question_id}", response_model=AIGeneratedQuestionResponse)
def update_question(
    question_id: int,
    payload: AIGeneratedQuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(AIGeneratedQuestion).filter(AIGeneratedQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    parent = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == q.ai_assessment_id).first()
    if parent and parent.is_immutable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment is immutable once assigned. Create a new version to modify.")

    verify_class_ownership(db, current_user, parent.live_class_id, parent.training_id)

    if payload.question_text is not None:
        q.question_text = payload.question_text
    if payload.options is not None:
        q.options = payload.options
    if payload.correct_answers is not None:
        q.correct_answers = payload.correct_answers
    if payload.explanation is not None:
        q.explanation = payload.explanation
    if payload.difficulty is not None:
        q.difficulty = payload.difficulty
    if payload.skill_category is not None:
        q.skill_category = payload.skill_category
    if payload.review_status is not None:
        q.review_status = payload.review_status
    if payload.mentor_verify_required is not None:
        q.mentor_verify_required = payload.mentor_verify_required

    db.commit()
    db.refresh(q)
    return q

@router.post("/questions/{question_id}/approve", response_model=AIGeneratedQuestionResponse)
def approve_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(AIGeneratedQuestion).filter(AIGeneratedQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    parent = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == q.ai_assessment_id).first()
    if parent and parent.is_immutable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment is immutable once assigned.")

    verify_class_ownership(db, current_user, parent.live_class_id, parent.training_id)

    q.review_status = "APPROVED"
    q.mentor_verify_required = False
    db.commit()
    db.refresh(q)
    return q

@router.post("/questions/{question_id}/reject", response_model=AIGeneratedQuestionResponse)
def reject_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(AIGeneratedQuestion).filter(AIGeneratedQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    parent = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == q.ai_assessment_id).first()
    if parent and parent.is_immutable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment is immutable once assigned.")

    verify_class_ownership(db, current_user, parent.live_class_id, parent.training_id)

    q.review_status = "REJECTED"
    db.commit()
    db.refresh(q)
    return q

@router.post("/questions/{question_id}/regenerate", response_model=AIGeneratedQuestionResponse)
def regenerate_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(AIGeneratedQuestion).filter(AIGeneratedQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    parent = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == q.ai_assessment_id).first()
    if parent and parent.is_immutable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment is immutable once assigned.")

    verify_class_ownership(db, current_user, parent.live_class_id, parent.training_id)

    # Synthesize refreshed variation
    q.question_text = f"Updated Analysis: In high-scale architectures, how should {q.skill_category} components handle backpressure?"
    new_opt1 = "Apply token-bucket rate limiting and drop-head queue eviction."
    new_opt2 = "Increase in-memory buffer capacity indefinitely."
    new_opt3 = "Switch protocol to unacknowledged broadcast UDP."
    new_opt4 = "Block worker threads until upstream producers recover."

    q.options = [new_opt1, new_opt2, new_opt3, new_opt4]
    q.correct_answers = [new_opt1]
    q.explanation = "Applying token-bucket rate limiting prevents memory saturation during severe backpressure events."
    q.review_status = "PENDING"
    q.mentor_verify_required = False
    q.quality_flags = []

    db.commit()
    db.refresh(q)
    return q

@router.post("/assessments/{assessment_id}/approve-all", response_model=AIGeneratedAssessmentResponse)
def approve_all_questions(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ass = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    verify_class_ownership(db, current_user, ass.live_class_id, ass.training_id)

    # Check requirement: "Approve all must fail if any question is pending or flagged"
    pending_or_flagged = [
        q for q in ass.questions
        if q.review_status == "PENDING" or q.mentor_verify_required
    ]

    if pending_or_flagged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve all: {len(pending_or_flagged)} question(s) are pending review or require manual mentor verification."
        )

    ass.status = "APPROVED"
    db.commit()
    db.refresh(ass)
    return ass

@router.post("/assessments/{assessment_id}/export-to-bank")
def export_questions_to_bank(
    assessment_id: int,
    payload: QuestionBankExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can export questions.")

    ass = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    verify_class_ownership(db, current_user, ass.live_class_id, ass.training_id)

    exported_count = 0
    for q_id in payload.question_ids:
        q = db.query(AIGeneratedQuestion).filter(
            AIGeneratedQuestion.id == q_id,
            AIGeneratedQuestion.ai_assessment_id == assessment_id
        ).first()

        if not q:
            continue

        # Requirement: "Only APPROVED questions may be copied into the main question bank"
        if q.review_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question #{q.id} is in status '{q.review_status}'. Only APPROVED questions can be exported to the question bank."
            )

        # Map to QuestionBank
        diff_str = q.difficulty.upper() if q.difficulty else "MEDIUM"
        if diff_str == "EASY":
            diff_enum = QuestionDifficulty.EASY
        elif diff_str == "HARD":
            diff_enum = QuestionDifficulty.HARD
        else:
            diff_enum = QuestionDifficulty.MEDIUM

        qb = QuestionBank(
            type=AssessmentType.LOGICAL_THINKING,
            question_type=QuestionType.SINGLE_CHOICE,
            difficulty=diff_enum,
            skill_category=q.skill_category,
            question_text=q.question_text,
            options=q.options,
            correct_answers=q.correct_answers,
            marks=1
        )
        db.add(qb)
        exported_count += 1

    db.commit()
    return {"message": f"Successfully exported {exported_count} approved question(s) to the Question Bank."}

@router.post("/assessments/{assessment_id}/finalize-assign")
def finalize_and_assign_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates core Assessment & Section, marks AI assessment immutable once assigned."""
    ass = db.query(AIGeneratedAssessment).filter(AIGeneratedAssessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    verify_class_ownership(db, current_user, ass.live_class_id, ass.training_id)

    # Filter only approved questions
    approved_questions = [q for q in ass.questions if q.review_status == "APPROVED"]
    if not approved_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment contains no approved questions. Please review and approve questions first."
        )

    # Create Core Assessment
    core_assessment = Assessment(
        title=ass.title,
        type=AssessmentType.LOGICAL_THINKING,
        total_duration_minutes=45,
        passing_percentage=70.0,
        randomize_questions=True,
        randomize_options=True,
        created_by=current_user.id
    )
    db.add(core_assessment)
    db.flush()

    # Create Section
    section = AssessmentSection(
        assessment_id=core_assessment.id,
        title="Class Mastery Section",
        order_index=1,
        timer_minutes=45
    )
    db.add(section)
    db.flush()

    # Add questions
    for idx, aq in enumerate(approved_questions):
        qb_id = aq.question_bank_id
        if not qb_id:
            diff_str = aq.difficulty.upper() if aq.difficulty else "MEDIUM"
            if diff_str == "EASY":
                diff_enum = QuestionDifficulty.EASY
            elif diff_str == "HARD":
                diff_enum = QuestionDifficulty.HARD
            else:
                diff_enum = QuestionDifficulty.MEDIUM

            qb = QuestionBank(
                type=AssessmentType.LOGICAL_THINKING,
                question_type=QuestionType.SINGLE_CHOICE,
                difficulty=diff_enum,
                skill_category=aq.skill_category,
                question_text=aq.question_text,
                options=aq.options,
                correct_answers=aq.correct_answers,
                marks=1
            )
            db.add(qb)
            db.flush()
            qb_id = qb.id
            aq.question_bank_id = qb_id

        sec_q = AssessmentSectionQuestion(
            section_id=section.id,
            question_id=qb_id,
            order_index=idx + 1
        )
        db.add(sec_q)

    # Link and mark IMMUTABLE once assigned
    ass.assessment_id = core_assessment.id
    ass.is_immutable = True
    ass.status = "PUBLISHED"

    db.commit()
    db.refresh(ass)
    return {
        "message": "Assessment finalized and published to core curriculum successfully.",
        "assessment_id": core_assessment.id,
        "is_immutable": ass.is_immutable
    }

# ============================================================================
# 4. Class Effectiveness Report Endpoint
# ============================================================================

@router.get("/effectiveness/live-class/{live_class_id}", response_model=ClassEffectivenessResponse)
def get_class_effectiveness(
    live_class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (UserRole.MENTOR, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mentors and admins can view effectiveness reports.")

    analytics = get_class_effectiveness_analytics(
        db=db,
        current_user=current_user,
        live_class_id=live_class_id
    )
    return ClassEffectivenessResponse(**analytics)
