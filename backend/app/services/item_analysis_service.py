import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.question import QuestionBank
from app.models.assessment_attempt import AssessmentAttempt, AssessmentResponse, AttemptStatus
from app.models.phase11_models import QuestionItemAnalytics

def get_utc_now():
    return datetime.now(timezone.utc)

def compute_question_analytics(
    db: Session,
    question_id: int,
    version: Optional[int] = None
) -> QuestionItemAnalytics:
    """Computes or refreshes the item analysis for a given question and version."""
    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise ValueError(f"Question with id {question_id} not found")

    target_version = version if version is not None else (question.version or 1)

    # Fetch all responses for this question and version from completed attempts
    responses_query = (
        db.query(AssessmentResponse, AssessmentAttempt)
        .join(AssessmentAttempt, AssessmentResponse.attempt_id == AssessmentAttempt.id)
        .filter(
            AssessmentResponse.question_id == question_id,
            AssessmentResponse.question_version == target_version,
            AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
        )
    )
    records = responses_query.all()
    n_attempts = len(records)

    # Check existing analytics cache row
    analytics_row = (
        db.query(QuestionItemAnalytics)
        .filter(
            QuestionItemAnalytics.question_id == question_id,
            QuestionItemAnalytics.question_version == target_version
        )
        .first()
    )
    if not analytics_row:
        analytics_row = QuestionItemAnalytics(
            question_id=question_id,
            question_version=target_version
        )
        db.add(analytics_row)

    if n_attempts == 0:
        analytics_row.attempts_count = 0
        analytics_row.correct_count = 0
        analytics_row.difficulty_index = 0.0
        analytics_row.discrimination_index = 0.0
        analytics_row.is_indicative_discrimination = False
        analytics_row.most_chosen_wrong_option = None
        analytics_row.avg_time_seconds = 0.0
        analytics_row.is_too_easy = False
        analytics_row.is_too_hard = False
        analytics_row.is_poor_discrimination = False
        analytics_row.needs_review = False
        analytics_row.review_reason = None
        analytics_row.option_distribution = {}
        analytics_row.formula_metadata = {
            "sample_size": 0,
            "min_sample_for_difficulty": 10,
            "min_sample_for_discrimination": 30,
            "status": "INSUFFICIENT_DATA"
        }
        db.commit()
        db.refresh(analytics_row)
        return analytics_row

    # 1. Difficulty Index (p = correct / total)
    correct_count = sum(1 for resp, _ in records if resp.is_correct)
    difficulty_index = round(correct_count / n_attempts, 4)

    # 2. Distractor & Option Distribution
    option_counts: Dict[str, int] = {}
    wrong_option_counts: Dict[str, int] = {}
    total_time = 0.0

    for resp, _ in records:
        total_time += getattr(resp, "time_spent_seconds", 0.0) or 0.0
        sel = resp.selected_options or []
        if isinstance(sel, list):
            for opt in sel:
                opt_str = str(opt)
                option_counts[opt_str] = option_counts.get(opt_str, 0) + 1
                if not resp.is_correct:
                    wrong_option_counts[opt_str] = wrong_option_counts.get(opt_str, 0) + 1
        elif isinstance(sel, str):
            option_counts[sel] = option_counts.get(sel, 0) + 1
            if not resp.is_correct:
                wrong_option_counts[sel] = wrong_option_counts.get(sel, 0) + 1

    most_chosen_wrong = None
    if wrong_option_counts:
        most_chosen_wrong = max(wrong_option_counts, key=wrong_option_counts.get)

    avg_time = round(total_time / n_attempts, 2)

    # 3. Discrimination Index (D = (U_corr - L_corr) / (0.27 * N))
    # Sort attempts by overall percentage or score
    sorted_records = sorted(records, key=lambda pair: pair[1].percentage or 0.0, reverse=True)
    group_size = max(1, int(round(0.27 * n_attempts)))

    upper_group = sorted_records[:group_size]
    lower_group = sorted_records[-group_size:]

    u_correct = sum(1 for resp, _ in upper_group if resp.is_correct)
    l_correct = sum(1 for resp, _ in lower_group if resp.is_correct)

    discrimination_index = round((u_correct - l_correct) / group_size, 4)

    # 4. Flags and Threshold Rules
    is_indicative = (10 <= n_attempts < 30)
    is_too_easy = (n_attempts >= 10 and difficulty_index > 0.95)
    is_too_hard = (n_attempts >= 10 and difficulty_index < 0.10)
    
    # Discrimination index is only strictly flagged at N >= 30
    is_poor_discrimination = False
    if n_attempts >= 30:
        is_poor_discrimination = (discrimination_index < 0.20 or discrimination_index <= 0.0)

    needs_review = is_too_easy or is_too_hard or is_poor_discrimination
    reasons = []
    if is_too_easy:
        reasons.append("Difficulty index > 0.95 (Too Easy)")
    if is_too_hard:
        reasons.append("Difficulty index < 0.10 (Too Hard)")
    if is_poor_discrimination:
        reasons.append("Discrimination index < 0.20 (Poor / Negative Discrimination)")

    analytics_row.attempts_count = n_attempts
    analytics_row.correct_count = correct_count
    analytics_row.difficulty_index = difficulty_index
    analytics_row.discrimination_index = discrimination_index
    analytics_row.is_indicative_discrimination = is_indicative
    analytics_row.most_chosen_wrong_option = most_chosen_wrong
    analytics_row.avg_time_seconds = avg_time
    analytics_row.is_too_easy = is_too_easy
    analytics_row.is_too_hard = is_too_hard
    analytics_row.is_poor_discrimination = is_poor_discrimination
    analytics_row.needs_review = needs_review
    analytics_row.review_reason = "; ".join(reasons) if reasons else None
    analytics_row.option_distribution = option_counts
    analytics_row.formula_metadata = {
        "sample_size": n_attempts,
        "upper_group_size": group_size,
        "upper_correct": u_correct,
        "lower_correct": l_correct,
        "discrimination_formula": "D = (U_correct - L_correct) / (0.27 * N)",
        "difficulty_formula": "p = Correct_Attempts / Total_Attempts",
        "sample_status": "SUFFICIENT" if n_attempts >= 30 else ("INDICATIVE_ONLY" if n_attempts >= 10 else "INSUFFICIENT")
    }
    analytics_row.updated_at = get_utc_now()

    db.commit()
    db.refresh(analytics_row)
    return analytics_row


def get_or_compute_analytics(db: Session, question_id: int, version: Optional[int] = None) -> QuestionItemAnalytics:
    """Returns cached analytics or computes if not found."""
    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise ValueError("Question not found")
    
    target_version = version if version is not None else (question.version or 1)
    cached = (
        db.query(QuestionItemAnalytics)
        .filter(
            QuestionItemAnalytics.question_id == question_id,
            QuestionItemAnalytics.question_version == target_version
        )
        .first()
    )
    if cached:
        return cached
    return compute_question_analytics(db, question_id, target_version)


def create_new_question_version(db: Session, question_id: int, new_data: Dict[str, Any]) -> QuestionBank:
    """
    If a question already has attempts/responses, edits create an incremented version.
    Past attempts stay tied to the previous version.
    """
    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise ValueError("Question not found")

    has_responses = (
        db.query(AssessmentResponse)
        .filter(AssessmentResponse.question_id == question_id)
        .count() > 0
    )

    if has_responses:
        # Increment version
        new_version = (question.version or 1) + 1
        question.version = new_version
    
    # Update attributes
    for key, val in new_data.items():
        if hasattr(question, key) and key not in ["id", "created_at"]:
            setattr(question, key, val)

    # Reset AI review status if modified
    if question.is_ai_generated:
        question.ai_review_status = "PENDING_REVIEW"

    db.commit()
    db.refresh(question)

    # Invalidate old cached analytics row for new version
    compute_question_analytics(db, question.id, question.version)
    return question


def send_question_back_to_review(db: Session, question_id: int, reason: str, user_id: int) -> QuestionItemAnalytics:
    """Marks question as needing review."""
    question = db.query(QuestionBank).filter(QuestionBank.id == question_id).first()
    if not question:
        raise ValueError("Question not found")

    question.ai_review_status = "NEEDS_REVIEW"
    analytics = get_or_compute_analytics(db, question_id, question.version)
    analytics.needs_review = True
    analytics.review_reason = reason
    db.commit()
    db.refresh(analytics)
    return analytics
