from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    unread_count: int
    items: List[NotificationOut]
