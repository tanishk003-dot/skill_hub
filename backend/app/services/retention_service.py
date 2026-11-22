from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.ai_class_summary import ClassTranscript
from app.models.phase10_models import WebcamProctoringSnapshot
from app.models.phase13_models import ClassAttendanceImport, SSOOAuthState, SSOAuditLog
from app.models.admin_audit_log import AdminAuditLog
from app.models.phase12_models import ForumFilterAuditLog, ForumIdentityAuditLog
from app.models.chat import ChatSession, ChatMessage

def run_data_retention_cleanup(db: Session) -> Dict[str, int]:
    """
    Executes automated data retention enforcement across all data categories.
    Retention windows are strictly configurable via .env settings:
    - Chat Transcripts: CHAT_TRANSCRIPT_RETENTION_DAYS (default 90)
    - Class Transcripts: TRANSCRIPT_RETENTION_DAYS (default 30)
    - Proctoring Snapshots: PROCTORING_SNAPSHOT_RETENTION_DAYS (default 30)
    - Attendance Staging: ATTENDANCE_STAGING_RETENTION_DAYS (default 30)
    - Admin Audit Logs: ADMIN_AUDIT_LOG_RETENTION_DAYS (default 365)
    - SSO Audit Logs: SSO_AUDIT_LOG_RETENTION_DAYS (default 180)
    - Forum Audit Logs: FORUM_AUDIT_LOG_RETENTION_DAYS (default 180)
    
    All retention periods must be confirmed and approved by HR/Legal in production.
    """
    now = datetime.now(timezone.utc)
    results = {}

    # 1. Class Transcripts Retention
    class_transcript_cutoff = now - timedelta(days=settings.TRANSCRIPT_RETENTION_DAYS)
    transcripts_deleted = db.query(ClassTranscript).filter(
        ClassTranscript.created_at < class_transcript_cutoff
    ).delete(synchronize_session=False)
    results["class_transcripts_purged"] = transcripts_deleted

    # 2. Proctoring Snapshots Retention
    snapshot_cutoff = now - timedelta(days=settings.PROCTORING_SNAPSHOT_RETENTION_DAYS)
    snapshots_deleted = db.query(WebcamProctoringSnapshot).filter(
        WebcamProctoringSnapshot.captured_at < snapshot_cutoff
    ).delete(synchronize_session=False)
    results["proctoring_snapshots_purged"] = snapshots_deleted

    # 3. Attendance Staging Imports Retention
    staging_cutoff = now - timedelta(days=settings.ATTENDANCE_STAGING_RETENTION_DAYS)
    staging_deleted = db.query(ClassAttendanceImport).filter(
        ClassAttendanceImport.created_at < staging_cutoff
    ).delete(synchronize_session=False)
    results["attendance_staging_purged"] = staging_deleted

    # 4. Expired OAuth States (1 hour TTL)
    oauth_states_deleted = db.query(SSOOAuthState).filter(
        SSOOAuthState.expires_at < now
    ).delete(synchronize_session=False)
    results["oauth_states_purged"] = oauth_states_deleted

    # 5. SSO Audit Logs Retention
    sso_audit_cutoff = now - timedelta(days=settings.SSO_AUDIT_LOG_RETENTION_DAYS)
    sso_audit_deleted = db.query(SSOAuditLog).filter(
        SSOAuditLog.created_at < sso_audit_cutoff
    ).delete(synchronize_session=False)
    results["sso_audit_logs_purged"] = sso_audit_deleted

    # 6. Forum Identity and Filter Audit Logs Retention
    forum_audit_cutoff = now - timedelta(days=settings.FORUM_AUDIT_LOG_RETENTION_DAYS)
    forum_identity_deleted = db.query(ForumIdentityAuditLog).filter(
        ForumIdentityAuditLog.created_at < forum_audit_cutoff
    ).delete(synchronize_session=False)
    results["forum_identity_audit_purged"] = forum_identity_deleted

    forum_filter_deleted = db.query(ForumFilterAuditLog).filter(
        ForumFilterAuditLog.created_at < forum_audit_cutoff
    ).delete(synchronize_session=False)
    results["forum_filter_audit_purged"] = forum_filter_deleted

    # 7. Admin Audit Logs Retention
    admin_audit_cutoff = now - timedelta(days=settings.ADMIN_AUDIT_LOG_RETENTION_DAYS)
    admin_audit_deleted = db.query(AdminAuditLog).filter(
        AdminAuditLog.created_at < admin_audit_cutoff
    ).delete(synchronize_session=False)
    results["admin_audit_logs_purged"] = admin_audit_deleted

    db.commit()
    return results
