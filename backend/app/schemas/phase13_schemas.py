from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class SSOConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sso_enabled: bool
    tenant_configured: bool
    client_id: Optional[str] = None
    allow_local_login: bool
    auto_provision_ase: bool
    app_env: str = "development"

class SSOAuthorizeRequest(BaseModel):
    redirect_uri: str = Field(..., description="Exact registered callback URL")

class SSOAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str

class SSOCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str

class SSOSettingsUpdate(BaseModel):
    allow_local_login: bool
    auto_provision_ase: bool
    confirm: bool = False

class SSOAuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    event_type: str
    upn: Optional[str] = None
    tid: Optional[str] = None
    oid: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime

class AttendanceRecordOut(BaseModel):
    email: str
    display_name: str
    join_time: Optional[str] = None
    leave_time: Optional[str] = None
    duration_seconds: int
    matched_ase_id: Optional[int] = None
    matched_ase_name: Optional[str] = None
    match_status: str
    suggested_status: str

class AttendancePreviewOut(BaseModel):
    import_id: int
    live_class_id: int
    class_title: str
    total_attendees_in_report: int
    total_invited: int
    matched_count: int
    unmatched_count: int
    notice: str
    records: List[AttendanceRecordOut]

class AttendanceConfirmItem(BaseModel):
    ase_id: int
    status: str = Field(..., pattern="^(ATTENDED|ABSENT|INVITED)$")

class AttendanceConfirmRequest(BaseModel):
    import_id: int
    mappings: List[AttendanceConfirmItem]

class AttendanceConfirmOut(BaseModel):
    import_id: int
    live_class_id: int
    updated_attendees_count: int
    is_confirmed: bool

class NotificationPreferenceOut(BaseModel):
    preferred_channels: List[str]
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    timezone: str
    teams_recipient_id: Optional[str] = None

class NotificationPreferenceUpdate(BaseModel):
    preferred_channels: List[str]
    quiet_hours_enabled: bool
    quiet_hours_start: str = Field("22:00", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: str = Field("07:00", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = "UTC"
    teams_recipient_id: Optional[str] = None
