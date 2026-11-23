"""
Idempotency and Duplicate Execution Prevention Service.
Generates deterministic execution keys for scheduled occurrences using stable identifiers.
Enforces execution key uniqueness across restarts and multi-cycle scheduler runs,
preventing automated duplicate submission.
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
    scheduled_at: Union[datetime.datetime, str],
    job_type: str = "reminder"
) -> str:
    """
    Generates a deterministic SHA-256 idempotency key using stable occurrence coordinates:
    canonical = {job_type}:{job_id}|recipient:{recipient_email}|scheduled:{scheduled_timestamp_utc}
    Default job_type is 'reminder' for full backward compatibility.
    """
    clean_job_id = str(reminder_id).strip()
    clean_recipient = normalize_recipient_email(recipient)
    clean_timestamp = normalize_scheduled_time(scheduled_at)

    canonical = f"{job_type}:{clean_job_id}|recipient:{clean_recipient}|scheduled:{clean_timestamp}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:40]


def generate_campaign_execution_key(
    campaign_id: Union[int, str],
    recipient: str,
    scheduled_at: Union[datetime.datetime, str]
) -> str:
    """
    Helper to generate a deterministic idempotency key for campaign message dispatches.
    """
    return generate_execution_key(campaign_id, recipient, scheduled_at, job_type="campaign")


def is_already_executed(session: Session, execution_key: str) -> bool:
    """
    Checks if a scheduled occurrence has already been executed in the MessageLog table.
    Considers SIMULATED_SUCCESS, SMTP_ACCEPTED, SENT, DELIVERY_CONFIRMED, and DELIVERY_UNCERTAIN as executed.
    DELIVERY_UNCERTAIN is treated as executed to prevent unsafe automatic resending.
    """
    from db.models import MessageLog
    existing = session.query(MessageLog).filter_by(execution_key=execution_key).first()
    return existing is not None and existing.execution_status in (
        "SENT", "SIMULATED_SUCCESS", "SMTP_ACCEPTED", "DELIVERY_CONFIRMED", "DELIVERY_UNCERTAIN"
    )


def record_execution(
    session: Session,
    execution_key: str,
    recipient_email: str,
    subject: str,
    status: str,
    campaign_id: Optional[int] = None,
    reminder_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    template_id: Optional[int] = None,
    scheduled_at: Optional[datetime.datetime] = None,
    execution_mode: str = "SIMULATION",
    attempt_count: int = 1,
    smtp_response: Optional[str] = None,
    message_id: Optional[str] = None,
    smtp_queue_id: Optional[str] = None,
    provider_message_id: Optional[str] = None,
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    next_retry_at: Optional[datetime.datetime] = None
) -> Tuple[bool, Optional[str]]:
    """
    Safely records or updates an execution into the MessageLog table.
    Enforces atomic uniqueness on execution_key while preserving attempt counts
    and provider diagnostics.
    """
    from db.models import MessageLog

    # Check if a record already exists for this execution key
    existing = session.query(MessageLog).filter_by(execution_key=execution_key).first()

    if existing:
        # If already terminal, successful, or uncertain, block duplicate execution attempt
        if existing.execution_status in ("SENT", "SIMULATED_SUCCESS", "SMTP_ACCEPTED", "DELIVERY_CONFIRMED", "DELIVERY_UNCERTAIN"):
            return False, f"Duplicate execution blocked: Key {execution_key} has already been recorded with status '{existing.execution_status}'."

        # Otherwise, this is updating a pending/retry attempt
        existing.execution_status = status
        existing.execution_mode = execution_mode
        existing.attempt_count = attempt_count
        existing.smtp_response = smtp_response
        if message_id is not None or existing.message_id is None:
            existing.message_id = message_id
        if smtp_queue_id is not None or existing.smtp_queue_id is None:
            existing.smtp_queue_id = smtp_queue_id
        if provider_message_id is not None or existing.provider_message_id is None:
            existing.provider_message_id = provider_message_id
        existing.error_category = error_category
        existing.error_message = error_message
        existing.next_retry_at = next_retry_at
        existing.executed_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            session.commit()
            return True, None
        except Exception as e:
            session.rollback()
            return False, str(e)

    log_entry = MessageLog(
        execution_key=execution_key,
        campaign_id=campaign_id,
        reminder_id=reminder_id,
        employee_id=employee_id,
        template_id=template_id,
        recipient_email=normalize_recipient_email(recipient_email),
        subject=subject,
        execution_status=status,
        execution_mode=execution_mode,
        attempt_count=attempt_count,
        smtp_response=smtp_response,
        message_id=message_id,
        smtp_queue_id=smtp_queue_id,
        provider_message_id=provider_message_id,
        error_category=error_category,
        error_message=error_message,
        next_retry_at=next_retry_at,
        scheduled_at=scheduled_at,
        executed_at=datetime.datetime.now(datetime.timezone.utc)
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
