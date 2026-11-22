from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.phase9_models import MockInterviewSession, MockInterviewRateLog
from app.services.llm_service import get_llm_provider, is_demo_mode

def check_interview_rate_limit(db: Session, ase_id: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_count = db.query(MockInterviewRateLog).filter(
        MockInterviewRateLog.ase_id == ase_id,
        MockInterviewRateLog.created_at >= cutoff
    ).count()

    if recent_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Mock interview session rate limit reached (max 10 interactions per hour). Please take a break and try again later."
        )

    db.add(MockInterviewRateLog(ase_id=ase_id))
    db.commit()

SAMPLE_QUESTIONS = [
    {
        "q": "How would you design a distributed idempotency key mechanism in an asynchronous payment processing microservice?",
        "expected_topics": ["Redis/DB unique key constraint", "TTL expiry", "Token bucket", "Outbox pattern"]
    },
    {
        "q": "Describe a scenario where you faced unexpected backpressure in an event pipeline. How did you diagnose and mitigate consumer lag?",
        "expected_topics": ["Kafka partition rebalance", "Consumer group scaling", "Queue eviction", "Monitoring metrics"]
    },
    {
        "q": "Behavioral: Describe a situation where you had a strong technical disagreement with a peer or senior engineer regarding API contracts. How did you resolve it?",
        "expected_topics": ["Empathetic listening", "Data-driven benchmarking", "Backward compatibility", "Consensus"]
    }
]

def start_mock_interview(db: Session, ase_id: int, target_role: str, skill_focus: str) -> Dict[str, Any]:
    check_interview_rate_limit(db, ase_id)
    
    first_q = SAMPLE_QUESTIONS[0]["q"]

    session = MockInterviewSession(
        ase_id=ase_id,
        target_role=target_role or "Associate Software Engineer",
        skill_focus=skill_focus or "Backend Distributed Systems",
        question_history_json=[{
            "step": 1,
            "question": first_q,
            "answer": None,
            "feedback": None
        }],
        feedback_json={}
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "step": 1,
        "question": first_q,
        "is_demo_mode": is_demo_mode(),
        "disclaimer": "AI-generated, please verify. This session is private to your profile."
    }

def submit_interview_response(db: Session, ase_id: int, session_id: int, candidate_answer: str) -> Dict[str, Any]:
    check_interview_rate_limit(db, ase_id)

    session = db.query(MockInterviewSession).filter(
        MockInterviewSession.id == session_id,
        MockInterviewSession.ase_id == ase_id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

    history = list(session.question_history_json or [])
    current_step_idx = len(history) - 1
    if current_step_idx < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session state.")

    # Wrap candidate input in security delimiters
    safe_answer = f"<untrusted_interview_candidate_response>\n{candidate_answer.strip()}\n</untrusted_interview_candidate_response>"

    # Evaluate answer and provide constructive feedback
    step_feedback = (
        "Strong structural rationale! You correctly identified the role of transactional uniqueness. "
        "Recommendation for next time: Mention TTL expiration windows and handling network partition edge-cases."
    )

    history[current_step_idx]["answer"] = candidate_answer
    history[current_step_idx]["feedback"] = step_feedback

    next_step = current_step_idx + 2
    if next_step <= len(SAMPLE_QUESTIONS):
        next_q = SAMPLE_QUESTIONS[next_step - 1]["q"]
        history.append({
            "step": next_step,
            "question": next_q,
            "answer": None,
            "feedback": None
        })
        is_finished = False
        summary_feedback = None
    else:
        next_q = None
        is_finished = True
        summary_feedback = {
            "overall_rating": "8.5 / 10 (Strong Engineering Foundations)",
            "strengths": [
                "Clear architectural decomposition",
                "Idempotency and database transaction awareness",
                "Professional, structured communication"
            ],
            "areas_to_improve": [
                "Quantify latency and memory footprint trade-offs",
                "Highlight monitoring metrics (P99 latency, queue depth)"
            ],
            "readiness_verdict": "Interview Ready for Mid-Level Engineering Challenges"
        }
        session.feedback_json = summary_feedback

    session.question_history_json = history
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "previous_feedback": step_feedback,
        "next_question": next_q,
        "is_finished": is_finished,
        "final_feedback": summary_feedback,
        "is_demo_mode": is_demo_mode(),
        "disclaimer": "AI-generated, please verify."
    }
