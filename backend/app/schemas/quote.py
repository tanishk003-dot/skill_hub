from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MotivationalQuoteBase(BaseModel):
    role: str
    text: str
    author: str
    is_active: bool = True

class MotivationalQuoteCreate(MotivationalQuoteBase):
    pass

class MotivationalQuoteUpdate(BaseModel):
    role: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    is_active: Optional[bool] = None

class MotivationalQuoteOut(MotivationalQuoteBase):
    id: int
    is_demo: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class DailyQuoteOut(BaseModel):
    id: int
    role: str
    text: str
    author: str
    date: str
    dismiss_timeout_ms: int = 5000
