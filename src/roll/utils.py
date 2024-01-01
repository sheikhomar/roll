from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current time in UTC."""
    return datetime.now(tz=timezone.utc)
