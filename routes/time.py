from datetime import timezone
from zoneinfo import ZoneInfo  # Python 3.9+


MOUNTAIN_TZ = ZoneInfo("America/Denver")


def utc_to_mountain(dt):
    """
    Convert UTC datetime to Mountain Time (handles DST correctly).
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(MOUNTAIN_TZ)

def fmt_dt(dt):
    """
    Display datetime in Mountain Time as YYYY-MM-DD HH:MM:SS
    """
    if dt is None:
        return "—"

    local = utc_to_mountain(dt)
    return local.strftime("%Y-%m-%d %H:%M:%S")