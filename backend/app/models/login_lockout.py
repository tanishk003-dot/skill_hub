from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Index
from app.core.database import Base, DateTime6
from app.core.datetime_util import utc_now

class LoginAttempt(Base):
    """
    Tracks authentication attempts per account and per IP to enforce exponential backoff lockout.
    """
    __tablename__ = "login_attempts"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    is_success = Column(Boolean, nullable=False, default=False)
    is_break_glass = Column(Boolean, nullable=False, default=False)
    failure_reason = Column(String(100), nullable=True)
    attempted_at = Column(DateTime6(), default=utc_now, nullable=False, index=True)
