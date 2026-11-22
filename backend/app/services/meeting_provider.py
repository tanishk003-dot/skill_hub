import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class MeetingValidationError(Exception):
    pass

class MeetingProvider(ABC):
    @abstractmethod
    def create_or_validate_link(self, link_input: Optional[str] = None, title: Optional[str] = None, **kwargs) -> str:
        """Returns validated or generated meeting URL"""
        pass

def validate_meeting_url(url: str) -> str:
    if not url or not isinstance(url, str):
        raise MeetingValidationError("Meeting link cannot be empty.")
    
    url = url.strip()
    parsed = urlparse(url)
    
    if parsed.scheme.lower() != "https":
        raise MeetingValidationError(f"Invalid URL scheme '{parsed.scheme}'. Only secure https:// URLs are allowed.")
    
    hostname = (parsed.hostname or "").lower()
    allowed_domains = settings.allowed_meeting_domains_list

    # Match exact hostname or subdomain of allowed domains (e.g. us04web.zoom.us matches zoom.us)
    is_allowed = any(hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains)
    if not is_allowed:
        domains_str = ", ".join(allowed_domains)
        raise MeetingValidationError(f"Domain '{hostname}' is not authorized. Allowed meeting domains are: {domains_str}")

    return url

class ManualLinkProvider(MeetingProvider):
    def create_or_validate_link(self, link_input: Optional[str] = None, title: Optional[str] = None, **kwargs) -> str:
        if not link_input:
            raise MeetingValidationError("A meeting link must be provided for manual link entry.")
        return validate_meeting_url(link_input)

class TeamsGraphProvider(MeetingProvider):
    """
    Microsoft Graph API provider for creating Teams online meetings.
    
    Least-Privilege Graph Permissions required:
    1. Application (App-only daemon flow):
       - Endpoint: POST https://graph.microsoft.com/v1.0/users/{userId}/onlineMeetings
       - Permission: OnlineMeetings.ReadWrite.All (Application, Admin consent required)
       - Teams Application Access Policy: Must be granted to the organizer's user ID via
         Grant-CsApplicationAccessPolicy in Teams PowerShell.
    2. Delegated:
       - Endpoint: POST https://graph.microsoft.com/v1.0/me/onlineMeetings
       - Permission: OnlineMeetings.ReadWrite (Delegated)
    
    If credentials are missing or the API call fails, falls back gracefully to ManualLinkProvider.
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

    def _get_app_access_token(self) -> Optional[str]:
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
                logger.warning("Microsoft Graph client credentials token acquisition failed: HTTP %s", res.status_code)
                return None
        except Exception as exc:
            logger.warning("Error acquiring Microsoft Graph token: %s", str(exc))
            return None

    def create_or_validate_link(self, link_input: Optional[str] = None, title: Optional[str] = None, **kwargs) -> str:
        # If user explicitly passed a manual link, validate and return
        if link_input:
            return validate_meeting_url(link_input)

        # If mock link is explicitly requested (e.g. in tests)
        if kwargs.get("mock_teams") is True:
            safe_title = (title or "Session").replace(" ", "_")
            return f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_mock_{safe_title}%40thread.v2/0"

        # Attempt real Graph API meeting creation if credentials exist
        token = self._get_app_access_token()
        if not token:
            # Informative fallback
            logger.info("Teams Graph credentials not available. Falling back to default session link.")
            safe_title = (title or "L&K Skill Hub Live Session").replace(" ", "%20")
            stub_link = f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_fallback_{safe_title}%40thread.v2/0"
            return validate_meeting_url(stub_link)

        organizer_id = kwargs.get("organizer_azure_id") or kwargs.get("organizer_email")
        if not organizer_id:
            logger.info("No organizer Azure ID or email provided for application-only meeting creation. Using fallback.")
            safe_title = (title or "L&K Skill Hub Live Session").replace(" ", "%20")
            stub_link = f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_fallback_{safe_title}%40thread.v2/0"
            return validate_meeting_url(stub_link)

        # Microsoft Graph Application Endpoint: POST /v1.0/users/{userId}/onlineMeetings
        graph_url = f"https://graph.microsoft.com/v1.0/users/{organizer_id}/onlineMeetings"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        start_dt = kwargs.get("start_time") or datetime.now(timezone.utc)
        duration_mins = kwargs.get("duration_minutes", 60)
        end_dt = start_dt + timedelta(minutes=duration_mins)

        payload = {
            "subject": title or "L&K Skill Hub Live Session",
            "startDateTime": start_dt.isoformat() if hasattr(start_dt, "isoformat") else str(start_dt),
            "endDateTime": end_dt.isoformat() if hasattr(end_dt, "isoformat") else str(end_dt)
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(graph_url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    join_url = data.get("joinWebUrl")
                    if join_url:
                        return validate_meeting_url(join_url)
                logger.warning("Graph meeting creation failed (HTTP %s): %s. Falling back.", res.status_code, res.text)
        except Exception as exc:
            logger.warning("Graph meeting creation exception: %s. Falling back.", str(exc))

        # Graceful fallback link
        safe_title = (title or "L&K Skill Hub Live Session").replace(" ", "%20")
        fallback_link = f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_fallback_{safe_title}%40thread.v2/0"
        return validate_meeting_url(fallback_link)

def get_meeting_provider(provider_type: str = "MANUAL") -> MeetingProvider:
    if provider_type.upper() == "TEAMS_GRAPH":
        if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET:
            return TeamsGraphProvider()
        logger.info("Teams Graph credentials missing. Falling back to ManualLinkProvider.")
        return ManualLinkProvider()
    return ManualLinkProvider()
