from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.chat import LLMUsageLog
from app.schemas.chat import AdminLLMUsageSummary, AdminLLMUsageItem
from app.services.llm_service import get_llm_provider, is_demo_mode

router = APIRouter(prefix="/admin/llm", tags=["Admin LLM Usage"])

@router.get("/usage", response_model=AdminLLMUsageSummary)
def get_admin_llm_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns organizational LLM token usage metrics and audit logs.
    Restricted strictly to Administrators.
    PRIVACY GUARANTEE: Does NOT disclose chat messages, prompts, or sensitive user transcripts.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required."
        )

    provider = get_llm_provider()
    demo_mode = is_demo_mode()

    # Aggregates
    totals = db.query(
        func.coalesce(func.sum(LLMUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(LLMUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
        func.count(LLMUsageLog.id).label("request_count")
    ).first()

    # Recent usage logs (last 50 requests)
    logs = db.query(LLMUsageLog).order_by(LLMUsageLog.created_at.desc()).limit(50).all()

    recent_items = []
    for log in logs:
        recent_items.append(
            AdminLLMUsageItem(
                id=log.id,
                user_id=log.user_id,
                user_name=log.user.name if log.user else "User",
                role=log.role,
                provider=log.provider,
                model=log.model,
                prompt_tokens=log.prompt_tokens,
                completion_tokens=log.completion_tokens,
                total_tokens=log.total_tokens,
                created_at=log.created_at
            )
        )

    return AdminLLMUsageSummary(
        total_prompt_tokens=totals.prompt_tokens,
        total_completion_tokens=totals.completion_tokens,
        total_tokens=totals.total_tokens,
        total_requests=totals.request_count,
        demo_mode=demo_mode,
        provider=provider.provider_name,
        model=provider.model_name,
        rate_limit_per_hour=settings.CHAT_RATE_LIMIT_PER_HOUR,
        recent_logs=recent_items
    )
