from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.chat import ChatSession, ChatMessage, LLMUsageLog
from app.schemas.chat import (
    ChatMessageCreate, ChatMessageOut, ChatSessionOut,
    ChatFeedbackUpdate, StarterPromptsOut
)
from app.services.llm_service import get_llm_provider, is_demo_mode
from app.services.prompt_builder import build_system_prompt

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

def _get_or_create_active_session(db: Session, user_id: int) -> ChatSession:
    session = db.query(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatSession.is_active == True
    ).order_by(ChatSession.created_at.desc()).first()

    if not session:
        session = ChatSession(
            user_id=user_id,
            title="Active Chat",
            is_active=True
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    return session

@router.get("/starter-prompts", response_model=StarterPromptsOut)
def get_starter_prompts(
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    provider = get_llm_provider()
    demo_mode = is_demo_mode()

    if role == UserRole.ASE.value:
        prompts = [
            "What are my weakest skills based on my latest assessment?",
            "Can you suggest a personalized 2-week study plan?",
            "What trainings do I have due next and how should I prioritize them?",
            "How can I improve my logical thinking and section pacing?"
        ]
    elif role == UserRole.MENTOR.value:
        prompts = [
            "Which of my mentees need immediate attention or intervention?",
            "Summarize the overall performance and skill gaps of my cohort.",
            "Who has overdue training modules or proctoring flags?",
            "Suggest remedial practice topics for my upcoming mentoring session."
        ]
    else:  # ADMIN
        prompts = [
            "Summarize organization-wide skill gaps and competencies.",
            "How is assessment workflow completion tracking across cohorts?",
            "What is the overall training completion and live class attendance rate?",
            "Give me an executive summary of current engineering cohort performance."
        ]

    return StarterPromptsOut(
        role=role,
        prompts=prompts,
        demo_mode=demo_mode,
        provider=provider.provider_name
    )

@router.get("/history", response_model=ChatSessionOut)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns active chat session history for current user only.
    Strictly isolated: users can never read others' sessions.
    """
    session = _get_or_create_active_session(db, current_user.id)
    return session

@router.delete("/history")
def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clears current active chat session and initializes a fresh conversation.
    """
    active_sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id,
        ChatSession.is_active == True
    ).all()
    for s in active_sessions:
        s.is_active = False
    
    # Create new fresh session
    new_session = ChatSession(
        user_id=current_user.id,
        title="Active Chat",
        is_active=True
    )
    db.add(new_session)
    db.commit()
    return {"message": "Chat history cleared successfully."}

@router.post("/message", response_model=ChatMessageOut)
def send_chat_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends a message to the AI Chatbot.
    Enforces DB-backed rate limiting, max message length, context isolation, and prompt injection protections.
    """
    # 1. Message length validation
    if len(payload.content) > settings.CHAT_MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message exceeds maximum allowed length of {settings.CHAT_MAX_MESSAGE_CHARS} characters."
        )

    # 2. Database-backed rate limiting per user (last 1 hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    message_count = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user.id,
        ChatMessage.sender_role == "USER",
        ChatMessage.created_at >= one_hour_ago
    ).count()

    if message_count >= settings.CHAT_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your limit of {settings.CHAT_RATE_LIMIT_PER_HOUR} messages per hour. Please try again later."
        )

    session = _get_or_create_active_session(db, current_user.id)

    # 3. Store user message in DB
    user_msg = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        sender_role="USER",
        content=payload.content
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 4. Construct role-isolated system prompt
    system_prompt = build_system_prompt(user=current_user, db=db, user_query=payload.content)

    # 5. Build recent message history (last 6 messages for context)
    recent_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at.desc()).limit(7).all()
    recent_messages.reverse()

    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in recent_messages:
        role_label = "assistant" if m.sender_role == "ASSISTANT" else "user"
        llm_messages.append({"role": role_label, "content": m.content})

    # 6. Execute LLM completion
    provider = get_llm_provider()
    demo_mode = is_demo_mode()

    try:
        reply_text, p_tokens, c_tokens = provider.generate_completion(
            messages=llm_messages,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    except Exception as e:
        reply_text = (
            "I encountered a temporary service issue connecting to the AI model. "
            "Please try again shortly, or reach out to your mentor for immediate guidance."
        )
        p_tokens, c_tokens = 0, 0

    # 7. Store assistant message in DB
    asst_msg = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        sender_role="ASSISTANT",
        content=reply_text
    )
    db.add(asst_msg)

    # 8. Log token usage (NO prompt, NO response content logged per Requirement 6)
    usage_log = LLMUsageLog(
        user_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_tokens=p_tokens + c_tokens
    )
    db.add(usage_log)
    db.commit()
    db.refresh(asst_msg)

    return ChatMessageOut(
        id=asst_msg.id,
        session_id=asst_msg.session_id,
        sender_role=asst_msg.sender_role,
        content=asst_msg.content,
        feedback=asst_msg.feedback,
        feedback_comment=asst_msg.feedback_comment,
        created_at=asst_msg.created_at,
        is_demo_mode=demo_mode
    )

@router.post("/feedback/{message_id}")
def submit_chat_feedback(
    message_id: int,
    payload: ChatFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits thumbs up/down feedback for an assistant message.
    Strictly restricted to the message owner (403 Forbidden for others).
    """
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat message not found.")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to submit feedback on this message.")

    message.feedback = payload.feedback
    if payload.comment:
        message.feedback_comment = payload.comment
    db.commit()
    return {"message": "Feedback recorded successfully.", "feedback": message.feedback}
