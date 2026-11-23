"""
Idempotency and Duplicate Execution Prevention Service.
Generates deterministic execution keys for scheduled occurrences using stable identifiers.
Guarantees at-most-once delivery semantics across restarts and multi-cycle scheduler runs.
"""
import hashlib
import datetime
from typing import Union, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


def normalize_recipient_email(email: str) -> str:
    """Normalizes email by stripping whitespace and lowercasing."""
    if not email:
        return ""
    return email.strip().lower()


def normalize_scheduled_time(scheduled_time: Union[datetime.datetime, str]) -> str:
    """
    Normalizes scheduled occurrence time to a canonical UTC ISO-8601 string:
    Format: YYYY-MM-DDTHH:MM:SSZ
    """
    if isinstance(scheduled_time, str):
        # Strip trailing Z or +00:00 for flexible parsing
        clean_str = scheduled_time.strip()
        try:
            # Handle ISO string
            dt_obj = datetime.datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                # Handle standard YYYY-MM-DD HH:MM:SS format
                dt_obj = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Fallback to date only
                dt_obj = datetime.datetime.strptime(clean_str, "%Y-%m-%d")
    else:
        dt_obj = scheduled_time

    # Normalize to UTC
    if dt_obj.tzinfo is None:
        # Assume UTC if naive
        dt_utc = dt_obj.replace(tzinfo=datetime.timezone.utc)
    else:
        dt_utc = dt_obj.astimezone(datetime.timezone.utc)

    # Format canonically
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_execution_key(
    reminder_id: Union[int, str],
    recipient: str,
    scheduled_at: Union[datetime.datetime, str]
) -> str:
    """
    Generates a deterministic SHA-256 idempotency key using stable occurrence coordinates:
    canonical = reminder_id|recipient_email|scheduled_timestamp_utc
    """
    clean_reminder_id = str(reminder_id).strip()
    clean_recipient = normalize_recipient_email(recipient)
    clean_timestamp = normalize_scheduled_time(scheduled_at)

    canonical = f"reminder:{clean_reminder_id}|recipient:{clean_recipient}|scheduled:{clean_timestamp}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]


def is_already_executed(session: Session, execution_key: str) -> bool:
    """
    Checks if a scheduled occurrence has already been executed in the MessageLog table.
    """
    from db.models import MessageLog
    existing = session.query(MessageLog).filter_by(execution_key=execution_key).first()
    return existing is not None and existing.execution_status in ("SENT", "SIMULATED_SUCCESS")


def record_execution(
    session: Session,
    execution_key: str,
    recipient_email: str,
    subject: str,
    status: str,
    campaign_id: Optional[int] = None,
    reminder_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    scheduled_at: Optional[datetime.datetime] = None,
    error_message: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Safely records an execution into MessageLog table.
    Returns (True, None) on success, or (False, error_reason) if a duplicate occurs.
    """
    from db.models import MessageLog

    log_entry = MessageLog(
        execution_key=execution_key,
        campaign_id=campaign_id,
        reminder_id=reminder_id,
        employee_id=employee_id,
        recipient_email=normalize_recipient_email(recipient_email),
        subject=subject,
        execution_status=status,
        scheduled_at=scheduled_at,
        executed_at=datetime.datetime.now(datetime.timezone.utc),
        error_message=error_message
    )

    try:
        session.add(log_entry)
        session.commit()
        return True, None
    except IntegrityError as e:
        session.rollback()
        return False, f"Duplicate occurrence blocked: {execution_key}"
    except Exception as e:
        session.rollback()
        return False, str(e)
