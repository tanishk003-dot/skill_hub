from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base

class MotivationalQuote(Base):
    __tablename__ = "motivational_quotes"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False, index=True)  # "ADMIN", "MENTOR", "ASE"
    text = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
