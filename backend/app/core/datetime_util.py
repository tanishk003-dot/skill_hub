from datetime import datetime, timezone
from typing import Optional

def utc_now() -> datetime:
    """Returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def utc_now_naive() -> datetime:
    """Returns UTC datetime as naive object for storage/comparison where naive is expected."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware in UTC. If naive, assumes UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
