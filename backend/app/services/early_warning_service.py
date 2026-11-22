from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from app.core.datetime_util import ensure_utc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.assignment import MentorAseAssignment
from app.models.training import TrainingAssignment
from app.models.assessment_attempt import AssessmentAttempt, AttemptStatus
from app.models.phase9_models import AseRiskSignal, MentorNudgeLog
from app.models.notification import Notification

SUPPORTIVE_NUDGE_TEMPLATE = (
    "Hi {first_name}! Just checking in to see how your onboarding journey is going. "
    "Remember that your mentor and technical leads are here to support you anytime you run into questions or blockers. "
    "Keep up the momentum on your training pathway!"
)

def evaluate_ase_risk(db: Session, ase_id: int, mentor_id: Optional[int] = None) -> AseRiskSignal:
    ase = db.query(User).filter(User.id == ase_id).first()
    if not ase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ASE not found.")

    risk_points = 0.0
    factors = []

    # 1. Overdue / incomplete trainings
    now = datetime.now(timezone.utc)
    trainings = db.query(TrainingAssignment).filter(TrainingAssignment.ase_id == ase_id).all()
    overdue_count = 0
    for t in trainings:
        if t.due_date and ensure_utc(t.due_date) < now and t.status != "COMPLETED":
            overdue_count += 1

    if overdue_count > 0:
        pts = min(40.0, overdue_count * 25.0)
        risk_points += pts
        factors.append(f"{overdue_count} overdue training module(s) requiring completion.")

    # 2. Failing assessment scores (< 60%)
    attempts = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.ase_id == ase_id,
        AssessmentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED, AttemptStatus.AUTO_SUBMITTED_VIOLATION])
    ).all()
    failing_attempts = [a for a in attempts if a.percentage < 60.0]
    if failing_attempts:
        risk_points += 30.0
        factors.append(f"{len(failing_attempts)} assessment attempt(s) scored below passing benchmark (60%).")

    # 3. Proctoring violations / auto-submits
    violated = [a for a in attempts if a.violation_count > 0 or a.status == AttemptStatus.AUTO_SUBMITTED_VIOLATION]
    if violated:
        risk_points += 25.0
        factors.append("Proctoring integrity flags or auto-submits recorded during assessments.")

    # 4. Inactivity check
    if not attempts and not trainings:
        risk_points += 15.0
        factors.append("No active learning progress or evaluations logged yet.")

    final_score = round(min(100.0, max(0.0, risk_points)), 1)
    if final_score >= 60.0:
        level = "HIGH"
    elif final_score >= 30.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    # AI-synthesized explanation for the mentor
    if not factors:
        explanation = f"{ase.name} is on track with healthy progress, steady attendance, and compliant assessment evaluations."
    else:
        explanation = (
            f"Risk Signal Alert for {ase.name}: Primary drivers include "
            f"{'; '.join(factors)}. "
            "Recommended Intervention: Reach out with a supportive check-in to clear learning blockers or offer a 1-on-1 coaching sync."
        )

    # Upsert risk signal
    sig = db.query(AseRiskSignal).filter(AseRiskSignal.ase_id == ase_id).first()
    if not sig:
        sig = AseRiskSignal(
            ase_id=ase_id,
            mentor_id=mentor_id,
            risk_score=final_score,
            risk_level=level,
            factors_json=factors,
            ai_explanation=explanation
        )
        db.add(sig)
    else:
        sig.mentor_id = mentor_id or sig.mentor_id
        sig.risk_score = final_score
        sig.risk_level = level
        sig.factors_json = factors
        sig.ai_explanation = explanation
        sig.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(sig)
    return sig

def get_mentor_risk_matrix(db: Session, mentor_id: int) -> List[Dict[str, Any]]:
    mentee_assignments = db.query(MentorAseAssignment).filter(
        MentorAseAssignment.mentor_id == mentor_id
    ).all()
    mentee_ids = [m.ase_id for m in mentee_assignments]

    matrix = []
    for m_id in mentee_ids:
        sig = evaluate_ase_risk(db, m_id, mentor_id=mentor_id)
        ase_user = db.query(User).filter(User.id == m_id).first()
        if ase_user:
            matrix.append({
                "ase_id": ase_user.id,
                "name": ase_user.name,
                "email": ase_user.email,
                "risk_score": sig.risk_score,
                "risk_level": sig.risk_level,
                "factors": sig.factors_json,
                "ai_explanation": sig.ai_explanation,
                "last_nudged_at": sig.last_nudged_at
            })

    matrix.sort(key=lambda x: x["risk_score"], reverse=True)
    return matrix

def send_supportive_nudge(db: Session, mentor_id: int, ase_id: int) -> Dict[str, Any]:
    # Check 48-hour rate limit
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    recent_nudge = db.query(MentorNudgeLog).filter(
        MentorNudgeLog.ase_id == ase_id,
        MentorNudgeLog.sent_at >= cutoff
    ).first()

    if recent_nudge:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A supportive nudge was already sent to this ASE in the last 48 hours. Please allow time for the learner to respond."
        )

    ase_user = db.query(User).filter(User.id == ase_id).first()
    if not ase_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ASE not found.")

    first_name = ase_user.name.split()[0] if ase_user.name else "Engineer"
    message_text = SUPPORTIVE_NUDGE_TEMPLATE.format(first_name=first_name)

    # Dispatch in-app notification
    notif = Notification(
        user_id=ase_id,
        title="Check-in from your Mentor",
        message=message_text,
        type="GENERAL",
        link="/ase/dashboard"
    )
    db.add(notif)

    # Log nudge
    log = MentorNudgeLog(
        mentor_id=mentor_id,
        ase_id=ase_id,
        message=message_text,
        sent_at=datetime.now(timezone.utc)
    )
    db.add(log)

    # Update risk signal record
    sig = db.query(AseRiskSignal).filter(AseRiskSignal.ase_id == ase_id).first()
    if sig:
        sig.last_nudged_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "message": "Supportive nudge dispatched successfully.",
        "ase_id": ase_id,
        "sent_at": log.sent_at
    }
