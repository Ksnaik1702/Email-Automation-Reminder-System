"""
Timezone and Recurrence Utilities for Email Automation & Reminder System.
Ensures all database timestamps are canonical UTC while supporting localized inputs
and calendar-aware recurring schedules (Daily, Weekly, Monthly) based on IANA timezones.
Default timezone: Asia/Kolkata (IST, UTC+05:30).
"""
import datetime
import zoneinfo
from typing import Optional, Union
from dateutil.relativedelta import relativedelta

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_timezone(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """Safely retrieves a ZoneInfo instance, falling back to DEFAULT_TIMEZONE."""
    if not tz_name or not str(tz_name).strip():
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return zoneinfo.ZoneInfo(str(tz_name).strip())
    except Exception:
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)


def ensure_utc(
    dt_val: Union[datetime.datetime, str],
    source_tz: Optional[str] = None
) -> datetime.datetime:
    """
    Normalizes any datetime (naive, aware, or ISO string) to a naive UTC datetime
    object suitable for direct storage in SQLite/SQLAlchemy DateTime columns.
    
    If dt_val is naive, it is assumed to be in source_tz (default: Asia/Kolkata).
    """
    if isinstance(dt_val, str):
        clean_str = dt_val.strip()
        # Handle trailing Z
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        try:
            parsed = datetime.datetime.fromisoformat(clean_str)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.datetime.strptime(clean_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unable to parse datetime string: '{dt_val}'")
    elif isinstance(dt_val, datetime.datetime):
        parsed = dt_val
    else:
        raise TypeError(f"Expected datetime or str, got {type(dt_val)}")

    if parsed.tzinfo is None:
        # Naive datetime: localize to source_tz, then convert to UTC
        local_tz = get_timezone(source_tz)
        localized = parsed.replace(tzinfo=local_tz)
        utc_dt = localized.astimezone(datetime.timezone.utc)
    else:
        # Already timezone-aware: convert directly to UTC
        utc_dt = parsed.astimezone(datetime.timezone.utc)

    # Return naive UTC datetime for SQLite standard compliance
    return utc_dt.replace(tzinfo=None)


def to_local(
    dt_utc: datetime.datetime,
    target_tz: Optional[str] = None
) -> datetime.datetime:
    """
    Converts a naive or aware UTC datetime to an aware datetime in target_tz.
    """
    tz = get_timezone(target_tz)
    if dt_utc.tzinfo is None:
        aware_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
    else:
        aware_utc = dt_utc.astimezone(datetime.timezone.utc)
    return aware_utc.astimezone(tz)


def format_localized(
    dt_utc: Optional[datetime.datetime],
    target_tz: Optional[str] = None,
    fmt: str = "%Y-%m-%d %I:%M %p %Z"
) -> str:
    """Formats a UTC datetime in the given target timezone."""
    if not dt_utc:
        return "N/A"
    localized = to_local(dt_utc, target_tz)
    return localized.strftime(fmt)


def calculate_next_run(
    current_scheduled_at: datetime.datetime,
    recurrence_type: Optional[str],
    tz_name: Optional[str] = None
) -> Optional[datetime.datetime]:
    """
    Calculates the next scheduled occurrence in UTC for recurring schedules.
    Supported recurrence types (case-insensitive):
    - None / 'Once' / '' -> None
    - 'Daily' -> +1 day at the same local wall-clock time
    - 'Weekly' -> +7 days at the same local wall-clock time
    - 'Monthly' -> +1 calendar month at the same local wall-clock time (clamps end of month)
    
    Calculation is performed in the target timezone to maintain accurate local wall-clock
    recurrence across day boundaries and daylight saving transitions, then converted back to UTC.
    """
    if not recurrence_type:
        return None

    clean_rec = recurrence_type.strip().capitalize()
    if clean_rec in ("None", "Once", ""):
        return None

    tz = get_timezone(tz_name)
    # Convert current UTC schedule to target local time
    local_dt = to_local(current_scheduled_at, tz_name)

    if clean_rec == "Daily":
        next_local = local_dt + datetime.timedelta(days=1)
    elif clean_rec == "Weekly":
        next_local = local_dt + datetime.timedelta(weeks=1)
    elif clean_rec == "Monthly":
        # Uses relativedelta to correctly handle calendar months and varying month lengths
        next_local = local_dt + relativedelta(months=1)
    else:
        # Unknown recurrence rule
        return None

    # Convert next occurrence back to naive UTC for storage
    return ensure_utc(next_local)
