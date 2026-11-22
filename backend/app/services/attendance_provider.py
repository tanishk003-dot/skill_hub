import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.live_class import LiveClass, LiveClassAttendee
from app.models.phase13_models import ClassAttendanceImport

logger = logging.getLogger(__name__)

class AttendanceReportError(Exception):
    pass

class AttendanceReportProvider(ABC):
    @abstractmethod
    def fetch_attendance_report(self, meeting_id_or_url: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches raw attendance records from Teams or Mock.
        Returns list of dicts with: email, display_name, join_time, leave_time, duration_seconds.
        Strictly excludes IP addresses, machine identifiers, or extraneous PII.
        """
        pass

class TeamsAttendanceProvider(AttendanceReportProvider):
    """
    Microsoft Graph Attendance Report Provider.
    Graph Permissions Required: OnlineMeetingAttendanceReport.Read.All (Application/Delegated).
    """
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.tenant_id = tenant_id or settings.AZURE_TENANT_ID
        self.client_id = client_id or settings.AZURE_CLIENT_ID
        self.client_secret = client_secret or settings.AZURE_CLIENT_SECRET

    def _get_token(self) -> Optional[str]:
        if not (self.tenant_id and self.client_id and self.client_secret):
            return None
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(token_url, data=data)
                if res.status_code == 200:
                    return res.json().get("access_token")
        except Exception:
            pass
        return None

    def fetch_attendance_report(self, meeting_id_or_url: str, **kwargs) -> List[Dict[str, Any]]:
        token = self._get_token()
        if not token:
            raise AttendanceReportError(
                "Microsoft Graph credentials not configured. Please check AZURE_TENANT_ID and secrets."
            )

        organizer_id = kwargs.get("organizer_azure_id") or kwargs.get("organizer_email")
        meeting_id = kwargs.get("meeting_id") or meeting_id_or_url

        # Microsoft Graph Attendance Report Endpoint
        if organizer_id:
            url = f"https://graph.microsoft.com/v1.0/users/{organizer_id}/onlineMeetings/{meeting_id}/attendanceReports"
        else:
            url = f"https://graph.microsoft.com/v1.0/communications/onlineMeetings/{meeting_id}/attendanceReports"

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 404:
                    return []
                if res.status_code != 200:
                    raise AttendanceReportError(f"Microsoft Graph returned HTTP {res.status_code}: {res.text}")
                
                reports = res.json().get("value", [])
                if not reports:
                    return []
                latest_report_id = reports[0].get("id")
                # Fetch detailed attendance records
                rec_url = f"{url}/{latest_report_id}/attendanceRecords"
                rec_res = client.get(rec_url, headers=headers)
                if rec_res.status_code != 200:
                    raise AttendanceReportError(f"Failed to fetch records: HTTP {rec_res.status_code}")

                raw_records = rec_res.json().get("value", [])
                results: List[Dict[str, Any]] = []
                for r in raw_records:
                    intervals = r.get("attendanceIntervals", [])
                    join_t = intervals[0].get("joinDateTime") if intervals else None
                    leave_t = intervals[-1].get("leaveDateTime") if intervals else None
                    results.append({
                        "email": (r.get("emailAddress") or "").strip().lower(),
                        "display_name": (r.get("identity") or {}).get("displayName", "Teams Attendee"),
                        "join_time": join_t,
                        "leave_time": leave_t,
                        "duration_seconds": r.get("totalAttendanceInSeconds", 0)
                    })
                return results
        except httpx.RequestError as exc:
            raise AttendanceReportError(f"Network error querying Microsoft Graph: {str(exc)}")


class MockAttendanceProvider(AttendanceReportProvider):
    def __init__(self):
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError(
                "CRITICAL SECURITY VIOLATION: MockAttendanceProvider cannot be initialized in production environment!"
            )

    def fetch_attendance_report(self, meeting_id_or_url: str, **kwargs) -> List[Dict[str, Any]]:
        if settings.APP_ENV.lower() == "production":
            raise RuntimeError("CRITICAL SECURITY VIOLATION: MockAttendanceProvider cannot execute in production!")

        # Allow passing mock records via kwargs for deterministic testing
        custom_records = kwargs.get("mock_records")
        if custom_records is not None:
            return custom_records

        # Default synthetic attendance records for demo/test
        now = datetime.now(timezone.utc)
        return [
            {
                "email": "demo.aarav.sharma@csm.tech",
                "display_name": "Aakash Sharma",
                "join_time": (now - timedelta(minutes=55)).isoformat(),
                "leave_time": now.isoformat(),
                "duration_seconds": 3300
            },
            {
                "email": "guest.external@partner.com",
                "display_name": "External Guest",
                "join_time": (now - timedelta(minutes=40)).isoformat(),
                "leave_time": (now - timedelta(minutes=10)).isoformat(),
                "duration_seconds": 1800
            }
        ]


class DisabledAttendanceProvider(AttendanceReportProvider):
    def fetch_attendance_report(self, meeting_id_or_url: str, **kwargs) -> List[Dict[str, Any]]:
        raise AttendanceReportError(
            "Attendance import is disabled: Microsoft Azure credentials are not configured."
        )


def get_attendance_provider(override_type: Optional[str] = None) -> AttendanceReportProvider:
    prov_type = (override_type or settings.ATTENDANCE_PROVIDER_TYPE).lower()

    if settings.APP_ENV.lower() == "production":
        if prov_type == "mock":
            raise RuntimeError("CRITICAL SECURITY VIOLATION: Mock Attendance cannot be enabled when APP_ENV=production!")
        if not (settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET):
            return DisabledAttendanceProvider()
        return TeamsAttendanceProvider()

    if prov_type == "mock":
        return MockAttendanceProvider()
    elif prov_type == "teams":
        return TeamsAttendanceProvider()

    if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET:
        return TeamsAttendanceProvider()
    return MockAttendanceProvider()


def generate_attendance_preview(
    db: Session,
    live_class: LiveClass,
    raw_records: List[Dict[str, Any]],
    imported_by_user_id: int
) -> Dict[str, Any]:
    """
    Matches raw attendance records against invited class attendees by case-insensitive email.
    Generates preview suggestions and creates an unconfirmed staging record with 30-day TTL.
    """
    # Clean up expired staging records older than 30 days
    db.query(ClassAttendanceImport).filter(
        ClassAttendanceImport.expires_at < datetime.now(timezone.utc)
    ).delete(synchronize_session=False)

    # Load invited attendees
    invited_attendees = db.query(LiveClassAttendee).filter(
        LiveClassAttendee.live_class_id == live_class.id
    ).all()

    invited_map = {}
    for a in invited_attendees:
        if a.ase and a.ase.email:
            invited_map[a.ase.email.strip().lower()] = a

    staged_records = []
    matched_count = 0
    unmatched_count = 0

    for rec in raw_records:
        rec_email = (rec.get("email") or "").strip().lower()
        dur = rec.get("duration_seconds", 0)
        jt = rec.get("join_time")
        lt = rec.get("leave_time")
        disp_name = rec.get("display_name", "")

        matched_att = invited_map.get(rec_email)
        if matched_att:
            matched_count += 1
            staged_records.append({
                "email": rec_email,
                "display_name": disp_name,
                "join_time": jt,
                "leave_time": lt,
                "duration_seconds": dur,
                "matched_ase_id": matched_att.ase_id,
                "matched_ase_name": matched_att.ase.name if matched_att.ase else f"ASE #{matched_att.ase_id}",
                "match_status": "EXACT_MATCH",
                "suggested_status": "ATTENDED" if dur >= 300 else "ABSENT" # Minimum 5 mins attendance threshold
            })
        else:
            unmatched_count += 1
            staged_records.append({
                "email": rec_email,
                "display_name": disp_name,
                "join_time": jt,
                "leave_time": lt,
                "duration_seconds": dur,
                "matched_ase_id": None,
                "matched_ase_name": None,
                "match_status": "UNMATCHED",
                "suggested_status": "UNMATCHED"
            })

    # Save to staging
    staging = ClassAttendanceImport(
        live_class_id=live_class.id,
        imported_by=imported_by_user_id,
        raw_report_json=json.dumps(raw_records),
        staged_records_json=json.dumps(staged_records),
        is_confirmed=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(staging)
    db.commit()
    db.refresh(staging)

    return {
        "import_id": staging.id,
        "live_class_id": live_class.id,
        "class_title": live_class.title,
        "total_attendees_in_report": len(raw_records),
        "total_invited": len(invited_attendees),
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "notice": "Teams attendance reports are generated by Microsoft after the meeting concludes and can take up to several hours to become available.",
        "records": staged_records
    }


def confirm_attendance_import(
    db: Session,
    import_id: int,
    confirmed_by_user_id: int,
    mappings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Confirms mapped attendance records, updates LiveClassAttendee status, and clears raw staging data.
    """
    staging = db.query(ClassAttendanceImport).filter(
        ClassAttendanceImport.id == import_id
    ).first()
    if not staging:
        raise AttendanceReportError("Attendance import staging record not found.")

    if staging.is_confirmed:
        raise AttendanceReportError("This attendance import has already been confirmed.")

    updated_count = 0
    now = datetime.now(timezone.utc)

    for m in mappings:
        ase_id = m.get("ase_id")
        status_val = m.get("status", "ATTENDED").upper()
        if not ase_id or status_val not in ("ATTENDED", "ABSENT", "INVITED"):
            continue

        att = db.query(LiveClassAttendee).filter(
            LiveClassAttendee.live_class_id == staging.live_class_id,
            LiveClassAttendee.ase_id == ase_id
        ).first()

        if att:
            att.status = status_val
            att.marked_at = now
            att.marked_by = confirmed_by_user_id
            updated_count += 1

    staging.is_confirmed = True
    staging.confirmed_at = now
    staging.confirmed_by = confirmed_by_user_id
    staging.raw_report_json = None # Auto-delete raw staging report to preserve privacy
    db.commit()

    return {
        "import_id": staging.id,
        "live_class_id": staging.live_class_id,
        "updated_attendees_count": updated_count,
        "is_confirmed": True
    }
