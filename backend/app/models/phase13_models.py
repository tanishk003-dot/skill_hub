from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base, DateTime6

class UserSSOAccount(Base):
    __tablename__ = "user_sso_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tid = Column(String(100), nullable=False, index=True) # Azure Tenant ID
    oid = Column(String(100), nullable=False, index=True) # Azure Object ID
    upn = Column(String(150), nullable=False, index=True) # User Principal Name
    encrypted_refresh_token = Column(Text, nullable=True) # Encrypted at rest via Fernet/AES
    token_expires_at = Column(DateTime6(), nullable=True)
    last_login_at = Column(DateTime6(), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tid", "oid", name="uk_sso_tid_oid"),
    )

    user = relationship("User", foreign_keys=[user_id])


class SSOAuditLog(Base):
    __tablename__ = "sso_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True) # LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, LINK, BREAK_GLASS_LOGIN, BREAK_GLASS_FAILED, AUTO_PROVISION
    upn = Column(String(150), nullable=True)
    tid = Column(String(100), nullable=True)
    oid = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(300), nullable=True)
    failure_reason = Column(String(255), nullable=True) # Detailed internal reason (not returned to client)
    created_at = Column(DateTime6(), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", foreign_keys=[user_id])


class SSOConfiguration(Base):
    __tablename__ = "sso_configurations"

    id = Column(Integer, primary_key=True, index=True)
    allow_local_login = Column(Boolean, nullable=False, default=True)
    auto_provision_ase = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    admin_user = relationship("User", foreign_keys=[updated_by])


class SSOOAuthState(Base):
    __tablename__ = "sso_oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(128), nullable=False, unique=True, index=True)
    nonce = Column(String(128), nullable=False, index=True)
    code_verifier = Column(String(128), nullable=False)
    redirect_uri = Column(String(500), nullable=False)
    is_used = Column(Boolean, nullable=False, default=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    preferred_channels = Column(String(100), nullable=False, default="IN_APP,EMAIL") # Comma-separated: IN_APP,EMAIL,TEAMS
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(10), nullable=False, default="22:00") # HH:MM format
    quiet_hours_end = Column(String(10), nullable=False, default="07:00")   # HH:MM format
    timezone = Column(String(50), nullable=False, default="UTC")
    teams_recipient_id = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])


class ClassAttendanceImport(Base):
    __tablename__ = "class_attendance_imports"

    id = Column(Integer, primary_key=True, index=True)
    live_class_id = Column(Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    imported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    raw_report_json = Column(Text, nullable=True) # Staged report (deleted after confirmation or expired)
    staged_records_json = Column(Text, nullable=False) # JSON array of mapped/unmapped candidates
    is_confirmed = Column(Boolean, nullable=False, default=False, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True) # Staging TTL: 30 days
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    live_class = relationship("LiveClass", foreign_keys=[live_class_id])
    importer = relationship("User", foreign_keys=[imported_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
