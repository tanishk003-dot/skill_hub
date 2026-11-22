from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, Index
from app.core.database import Base, DateTime6
from app.core.datetime_util import utc_now

class AdminAuditLog(Base):
    """
    Append-only audit trail for administrative actions.
    Records actor, action, target, IP, user-agent, and sanitized metadata.
    Never stores passwords, tokens, medical notes, private 1-on-1 notes, or raw messages.
    """
    __tablename__ = "admin_audit_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True) # USER_CREATE, USER_DELETE, ROLE_CHANGE, USER_UNLOCK, etc.
    target_type = Column(String(100), nullable=False, index=True) # USER, ASSESSMENT, CONFIG, RETENTION, etc.
    target_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True) # Sanitized JSON / descriptive summary
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(300), nullable=True)
    created_at = Column(DateTime6(), default=utc_now, nullable=False, index=True)
