from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="User prompt text")

class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    sender_role: str
    content: str
    feedback: Optional[str] = None
    feedback_comment: Optional[str] = None
    created_at: datetime
    is_demo_mode: Optional[bool] = False

    class Config:
        from_attributes = True

class ChatSessionOut(BaseModel):
    id: int
    title: str
    is_active: bool
    created_at: datetime
    messages: List[ChatMessageOut] = []

    class Config:
        from_attributes = True

class ChatFeedbackUpdate(BaseModel):
    feedback: str = Field(..., pattern="^(UP|DOWN)$", description="Must be UP or DOWN")
    comment: Optional[str] = Field(None, max_length=255)

class StarterPromptsOut(BaseModel):
    role: str
    prompts: List[str]
    demo_mode: bool
    provider: str

class AdminLLMUsageItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    role: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True

class AdminLLMUsageSummary(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_requests: int
    demo_mode: bool
    provider: str
    model: str
    rate_limit_per_hour: int
    recent_logs: List[AdminLLMUsageItem] = []
