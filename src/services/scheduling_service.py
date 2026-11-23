"""
Scheduling Service Layer: Engine for identifying due campaigns and reminders,
claiming jobs safely, rendering personalized content via Jinja2 sandboxing,
enforcing SHA-256 idempotency, advancing calendar-aware recurrences, and recording
execution logs into SQLite as the single source of truth.
Supports both Virtual Simulation Mode and Live SMTP Delivery Mode with exponential backoff retries.
"""
import os
import re
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from db.models import (
    Campaign, CampaignRecipient, ReminderJob, MessageLog,
    EmailTemplate, Employee, utc_now
)
from src.timezone_utils import ensure_utc, to_local, calculate_next_run, DEFAULT_TIMEZONE
from src.idempotency import (
    generate_execution_key, generate_campaign_execution_key,
    is_already_executed, record_execution, normalize_recipient_email
)
from src.smtp_client import SMTPClient, SMTPConfig, SMTPDeliveryResult
from src.services import template_service
from src.logger import logger

PREVIEWS_DIR = Path("outputs/previews")


def sanitize_filename(name: str) -> str:
    """Sanitizes strings for safe cross-platform file paths."""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)


def save_simulation_preview(
    filename: str,
    subject: str,
    html_content: str,
    plain_text: str,
    metadata: Dict[str, Any]
) -> Path:
    """
    Saves rendered email preview to disk during Virtual Simulation Mode.
    Generates a realistic HTML preview with an inspection metadata header.
    """
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    clean_path = PREVIEWS_DIR / sanitize_filename(filename)

    meta_html = "".join([f"<div><strong>{k}:</strong> {v}</div>" for k, v in metadata.items()])

    full_document = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }}
    .sim-banner {{ background: #059669; color: #ffffff; padding: 10px 20px; font-size: 13px; font-weight: 600; display: flex; justify-content: space-between; }}
    .sim-meta {{ background: #f1f5f9; border-bottom: 2px solid #e2e8f0; padding: 14px 24px; font-size: 12px; line-height: 1.6; color: #334155; }}
    .sim-content {{ padding: 24px; max-width: 680px; margin: 24px auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  </style>
</head>
<body>
  <div class="sim-banner">
    <span>🟢 VIRTUAL SIMULATION MODE (DRY-RUN)</span>
    <span>No real SMTP transmission occurred</span>
  </div>
  <div class="sim-meta">
    {meta_html}
  </div>
  <div class="sim-content">
    <div style="font-size: 18px; font-weight: 700; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px;">
      {subject}
    </div>
    {html_content}
  </div>
</body>
</html>
"""
    with open(clean_path, "w", encoding="utf-8") as f:
        f.write(full_document)

    return clean_path


# ----------------- Due Job Identification ----------------- #

def get_due_campaigns(
    db: Session,
    as_of: Optional[datetime.datetime] = None
) -> List[Campaign]:
    """
    Identifies campaigns that are due for execution:
    - Status is 'READY' or 'SCHEDULED' or 'PROCESSING' (for crash recovery).
    - scheduled_at is NULL (immediate) or scheduled_at <= as_of_utc.
    """
    cutoff = ensure_utc(as_of) if as_of else utc_now()

    due = db.query(Campaign).filter(
        Campaign.status.in_(["READY", "SCHEDULED", "PROCESSING"]),
        or_(
            Campaign.scheduled_at == None,
            Campaign.scheduled_at <= cutoff
        )
    ).order_by(Campaign.scheduled_at.asc().nullsfirst()).all()

    return due


def get_due_reminders(
    db: Session,
    as_of: Optional[datetime.datetime] = None
) -> List[ReminderJob]:
    """
    Identifies personal/team reminder jobs that are due for execution:
    - Status is 'Active'
    - scheduled_at <= as_of_utc
    """
    cutoff = ensure_utc(as_of) if as_of else utc_now()

    due = db.query(ReminderJob).filter(
        ReminderJob.status == "Active",
        ReminderJob.scheduled_at <= cutoff
    ).order_by(ReminderJob.scheduled_at.asc()).all()

    return due


# ----------------- Job Processing Engines ----------------- #

def process_due_campaign(
    db: Session,
    campaign: Campaign,
    simulation_mode: bool = True,
    smtp_client: Optional[SMTPClient] = None
) -> Dict[str, Any]:
    """
    Executes a single due campaign:
    1. Claims the campaign by setting status='PROCESSING'.
    2. Loads template and validates existence.
    3. Iterates over targeted recipients.
    4. Enforces safety checks (skips inactive/unsubscribed employees).
    5. Evaluates SHA-256 idempotency key per recipient.
    6. Renders personalized email with Jinja2 sandboxing.
    7. In simulation mode: outputs HTML preview and records SIMULATED_SUCCESS.
    8. In live mode: sends via SMTP, records SMTP_ACCEPTED / RETRY_PENDING.
    9. Updates CampaignRecipient.status and Campaign.status='COMPLETED'.
    """
    stats = {
        "campaign_id": campaign.id,
        "campaign_name": campaign.campaign_name,
        "total_recipients": len(campaign.recipients),
        "dispatched": 0,
        "simulated": 0,
        "skipped_duplicate": 0,
        "skipped_inactive": 0,
        "retry_pending": 0,
        "delivery_uncertain": 0,
        "errors": []
    }

    mode_label = "SIMULATION" if simulation_mode else "LIVE_SMTP"
    logger.info(f"Processing Campaign ID={campaign.id} ('{campaign.campaign_name}') in [{mode_label}] mode with {len(campaign.recipients)} recipients...")

    # Validate live mode prerequisites
    if not simulation_mode:
        if not smtp_client:
            smtp_client = SMTPClient()
        valid_cfg, cfg_err = smtp_client.config.validate()
        if not valid_cfg:
            err = f"Live SMTP execution refused: {cfg_err}"
            logger.error(err)
            campaign.status = "FAILED"
            db.commit()
            stats["errors"].append(err)
            raise ValueError(err)

    # 1. Claim job state
    campaign.status = "PROCESSING"
    campaign.updated_at = utc_now()
    db.commit()

    template = campaign.template
    if not template:
        err = f"Campaign {campaign.id} has no valid associated EmailTemplate."
        logger.error(err)
        campaign.status = "FAILED"
        db.commit()
        stats["errors"].append(err)
        return stats

    scheduled_timestamp = campaign.scheduled_at or campaign.created_at

    # Build event context for template rendering
    event_ctx = {
        "event_name": campaign.campaign_name,
        "event_description": campaign.description or "Automated notification broadcast.",
        "event_date": campaign.scheduled_at.strftime("%B %d, %Y") if campaign.scheduled_at else "Today",
        "event_time": campaign.scheduled_at.strftime("%I:%M %p UTC") if campaign.scheduled_at else "Immediate"
    }

    for recipient in campaign.recipients:
        recip_email = normalize_recipient_email(recipient.recipient_email)
        exec_key = generate_campaign_execution_key(campaign.id, recip_email, scheduled_timestamp)

        # 2. Safety Check: Inactive / Unsubscribed Employees
        emp = recipient.employee
        if emp and emp.employment_status and emp.employment_status.strip().capitalize() not in ("Active", ""):
            logger.warning(f"[SAFETY CONTROL] Skipping inactive employee ID={emp.employee_id} ('{emp.full_name}', Status='{emp.employment_status}')")
            recipient.status = "Skipped_Inactive"
            stats["skipped_inactive"] += 1
            record_execution(
                session=db,
                execution_key=exec_key,
                recipient_email=recip_email,
                subject=template.subject,
                status="SKIPPED_INACTIVE",
                campaign_id=campaign.id,
                employee_id=recipient.employee_id,
                template_id=template.id,
                scheduled_at=scheduled_timestamp,
                execution_mode=mode_label,
                error_message=f"Employee status is '{emp.employment_status}'. Required: 'Active'."
            )
            continue

        # 3. Idempotency Check
        if is_already_executed(db, exec_key):
            logger.info(f"[IDEMPOTENCY] Skipping duplicate occurrence for campaign {campaign.id} to '{recip_email}' (key={exec_key[:12]}...)")
            recipient.status = "Skipped_Duplicate"
            stats["skipped_duplicate"] += 1
            continue

        # 4. Render Personalized Email
        try:
            preview = template_service.render_template_preview(
                db=db,
                subject_tmpl=template.subject,
                body_tmpl=template.body,
                employee_id=recipient.employee_id,
                event_context=event_ctx
            )
            if not preview.is_valid:
                err_msg = f"Validation failed for recipient {recip_email}: {preview.validation_error}"
                logger.error(err_msg)
                recipient.status = "Failed_Render"
                stats["errors"].append(err_msg)
                continue
        except Exception as e:
            err_msg = f"Failed to render email for recipient {recip_email}: {str(e)}"
            logger.error(err_msg)
            recipient.status = "Failed_Render"
            stats["errors"].append(err_msg)
            continue

        # 5. Dispatch or Simulate
        if simulation_mode:
            # Virtual Simulation Mode (Default)
            sim_filename = f"campaign_{campaign.id}_emp_{recipient.employee_id}_{recip_email}.html"
            preview_path = save_simulation_preview(
                filename=sim_filename,
                subject=preview.rendered_subject,
                html_content=preview.rendered_html,
                plain_text=preview.plain_text_fallback,
                metadata={
                    "Type": "Campaign Broadcast",
                    "Campaign ID": campaign.id,
                    "Campaign Name": campaign.campaign_name,
                    "Recipient": recip_email,
                    "Employee ID": recipient.employee_id,
                    "Execution Key": exec_key,
                    "Mode": "Virtual Simulation (Dry-Run)"
                }
            )

            # Record in DB MessageLog with SIMULATED_SUCCESS
            recorded, rec_err = record_execution(
                session=db,
                execution_key=exec_key,
                recipient_email=recip_email,
                subject=preview.rendered_subject,
                status="SIMULATED_SUCCESS",
                campaign_id=campaign.id,
                employee_id=recipient.employee_id,
                template_id=template.id,
                scheduled_at=scheduled_timestamp,
                execution_mode="SIMULATION",
                attempt_count=1
            )

            if recorded:
                recipient.status = "Simulated"
                stats["simulated"] += 1
                logger.info(f"[SIMULATION] Rendered campaign preview for '{recip_email}' -> {preview_path.name}")
            else:
                recipient.status = "Duplicate_Blocked"
                stats["skipped_duplicate"] += 1
                logger.warning(f"[IDEMPOTENCY] Database blocked duplicate insert: {rec_err}")

        else:
            # Live SMTP Delivery Mode
            custom_headers = {
                "X-Campaign-ID": str(campaign.id),
                "X-Employee-ID": str(recipient.employee_id),
                "X-Execution-Key": exec_key
            }

            delivery_res = smtp_client.send_live_email(
                to_email=recip_email,
                subject=preview.rendered_subject,
                html_content=preview.rendered_html,
                plain_text=preview.plain_text_fallback,
                attempt=1,
                custom_headers=custom_headers
            )

            record_execution(
                session=db,
                execution_key=exec_key,
                recipient_email=recip_email,
                subject=preview.rendered_subject,
                status=delivery_res.status,
                campaign_id=campaign.id,
                employee_id=recipient.employee_id,
                template_id=template.id,
                scheduled_at=scheduled_timestamp,
                execution_mode="LIVE_SMTP",
                attempt_count=delivery_res.attempt,
                smtp_response=delivery_res.smtp_response,
                provider_message_id=delivery_res.message_id,
                error_category=delivery_res.error_category,
                error_message=delivery_res.error_message,
                next_retry_at=delivery_res.next_retry_at
            )

            if delivery_res.status == "SMTP_ACCEPTED":
                recipient.status = "Accepted"
                stats["dispatched"] += 1
            elif delivery_res.status == "RETRY_PENDING":
                recipient.status = "Retry_Pending"
                stats["retry_pending"] += 1
            elif delivery_res.status == "DELIVERY_UNCERTAIN":
                recipient.status = "Delivery_Uncertain"
                stats["delivery_uncertain"] += 1
                stats["errors"].append(delivery_res.error_message or "Delivery uncertain (timeout awaiting response)")
            else:
                recipient.status = "Failed"
                stats["errors"].append(delivery_res.error_message or "SMTP delivery failed")

    # 6. Mark campaign complete
    campaign.status = "COMPLETED"
    campaign.updated_at = utc_now()
    db.commit()

    logger.info(
        f"Campaign ID={campaign.id} completed: Simulated={stats['simulated']}, "
        f"Dispatched={stats['dispatched']}, Inactive={stats['skipped_inactive']}, "
        f"Duplicates={stats['skipped_duplicate']}, Retries={stats['retry_pending']}, "
        f"Errors={len(stats['errors'])}"
    )
    return stats


def process_due_reminder(
    db: Session,
    reminder: ReminderJob,
    simulation_mode: bool = True,
    smtp_client: Optional[SMTPClient] = None
) -> Dict[str, Any]:
    """
    Executes a single due reminder occurrence:
    1. Validates employee existence and active status.
    2. Generates deterministic SHA-256 idempotency key for this exact occurrence.
    3. Checks MessageLog for duplicate prevention.
    4. Renders content.
    5. In simulation mode: outputs preview file and records SIMULATED_SUCCESS.
    6. In live mode: delivers via SMTP and records SMTP_ACCEPTED / RETRY_PENDING.
    7. Advances recurring schedules (Daily, Weekly, Monthly) to the next UTC occurrence,
       or marks one-time reminders as 'Completed'.
    """
    stats = {
        "reminder_id": reminder.id,
        "title": reminder.reminder_title,
        "status": "Pending",
        "error": None
    }

    mode_label = "SIMULATION" if simulation_mode else "LIVE_SMTP"

    emp = reminder.employee
    if not emp:
        err = f"Reminder {reminder.id} references missing Employee ID {reminder.employee_id}."
        logger.error(err)
        reminder.status = "Failed"
        db.commit()
        stats["error"] = err
        return stats

    recip_email = normalize_recipient_email(emp.email)
    scheduled_utc = reminder.scheduled_at
    exec_key = generate_execution_key(reminder.id, recip_email, scheduled_utc, job_type="reminder")

    # Safety check: Inactive / Unsubscribed employee
    if emp.employment_status and emp.employment_status.strip().capitalize() not in ("Active", ""):
        logger.warning(f"[SAFETY CONTROL] Skipping inactive reminder recipient ID={emp.employee_id} ({emp.full_name}, Status='{emp.employment_status}')")
        record_execution(
            session=db,
            execution_key=exec_key,
            recipient_email=recip_email,
            subject=f"Reminder: {reminder.reminder_title}",
            status="SKIPPED_INACTIVE",
            reminder_id=reminder.id,
            employee_id=emp.id,
            scheduled_at=scheduled_utc,
            execution_mode=mode_label,
            error_message=f"Employee status is '{emp.employment_status}'. Required: 'Active'."
        )
        stats["status"] = "SKIPPED_INACTIVE"
        reminder.status = "Paused"
        db.commit()
        return stats

    # 1. Check idempotency
    if is_already_executed(db, exec_key):
        logger.info(f"[IDEMPOTENCY] Reminder occurrence {reminder.id} already executed for '{recip_email}' at {scheduled_utc}.")
        stats["status"] = "Skipped_Duplicate"
    else:
        # 2. Render reminder content
        subject = f"🔔 Reminder: {reminder.reminder_title} - {emp.full_name}"
        html_body = f"""<div style="font-family: sans-serif; line-height: 1.5;">
  <h2 style="color: #2563eb; margin-top: 0;">Scheduled Reminder</h2>
  <p>Hello <strong>{emp.full_name}</strong>,</p>
  <p>This is an automated notification regarding:</p>
  <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
    <strong style="font-size: 15px; color: #1e40af;">{reminder.reminder_title}</strong>
  </div>
  <p style="font-size: 13px; color: #64748b;">
    Department: {emp.department} | Recurrence: {reminder.recurrence_type} | Timezone: {reminder.timezone}
  </p>
</div>"""
        plain_text = f"Reminder: {reminder.reminder_title}\n\nHello {emp.full_name},\nThis is a scheduled notification regarding: {reminder.reminder_title}\n\nDepartment: {emp.department}"

        # 3. Simulate or Dispatch
        if simulation_mode:
            sim_filename = f"reminder_{reminder.id}_{emp.id}_{recip_email}.html"
            preview_path = save_simulation_preview(
                filename=sim_filename,
                subject=subject,
                html_content=html_body,
                plain_text=plain_text,
                metadata={
                    "Type": "Personal/Team Reminder",
                    "Reminder ID": reminder.id,
                    "Title": reminder.reminder_title,
                    "Recipient": recip_email,
                    "Employee ID": emp.id,
                    "Recurrence": reminder.recurrence_type,
                    "Execution Key": exec_key,
                    "Mode": "Virtual Simulation (Dry-Run)"
                }
            )

            recorded, rec_err = record_execution(
                session=db,
                execution_key=exec_key,
                recipient_email=recip_email,
                subject=subject,
                status="SIMULATED_SUCCESS",
                reminder_id=reminder.id,
                employee_id=emp.id,
                scheduled_at=scheduled_utc,
                execution_mode="SIMULATION",
                attempt_count=1
            )

            if recorded:
                stats["status"] = "SIMULATED_SUCCESS"
                logger.info(f"[SIMULATION] Rendered reminder preview for '{recip_email}' -> {preview_path.name}")
            else:
                stats["status"] = "Skipped_Duplicate"
                logger.warning(f"[IDEMPOTENCY] Blocked duplicate insert: {rec_err}")
        else:
            # Live SMTP Delivery
            if not smtp_client:
                smtp_client = SMTPClient()
            valid_cfg, cfg_err = smtp_client.config.validate()
            if not valid_cfg:
                raise ValueError(f"Live SMTP mode requires valid configuration: {cfg_err}")

            custom_headers = {
                "X-Reminder-ID": str(reminder.id),
                "X-Employee-ID": str(emp.id),
                "X-Execution-Key": exec_key
            }

            delivery_res = smtp_client.send_live_email(
                to_email=recip_email,
                subject=subject,
                html_content=html_body,
                plain_text=plain_text,
                attempt=1,
                custom_headers=custom_headers
            )

            record_execution(
                session=db,
                execution_key=exec_key,
                recipient_email=recip_email,
                subject=subject,
                status=delivery_res.status,
                reminder_id=reminder.id,
                employee_id=emp.id,
                scheduled_at=scheduled_utc,
                execution_mode="LIVE_SMTP",
                attempt_count=delivery_res.attempt,
                smtp_response=delivery_res.smtp_response,
                provider_message_id=delivery_res.message_id,
                error_category=delivery_res.error_category,
                error_message=delivery_res.error_message,
                next_retry_at=delivery_res.next_retry_at
            )

            stats["status"] = delivery_res.status
            stats["error"] = delivery_res.error_message

    # 4. Advance recurrence or mark completed
    reminder.last_executed_at = utc_now()
    clean_rec = (reminder.recurrence_type or "None").strip().capitalize()

    if clean_rec in ("Daily", "Weekly", "Monthly"):
        next_run = calculate_next_run(reminder.scheduled_at, clean_rec, reminder.timezone)
        if next_run:
            logger.info(f"Recurring Reminder {reminder.id} advanced ({clean_rec}): {reminder.scheduled_at} -> {next_run} UTC")
            reminder.scheduled_at = next_run
            reminder.status = "Active"
        else:
            reminder.status = "Completed"
    else:
        # One-time reminder
        reminder.status = "Completed"

    db.commit()
    return stats


def process_pending_retries(
    db: Session,
    smtp_client: Optional[SMTPClient] = None,
    as_of: Optional[datetime.datetime] = None
) -> int:
    """
    Identifies MessageLog records with status='RETRY_PENDING' where
    next_retry_at <= now, and re-attempts delivery with exponential backoff.
    """
    cutoff = ensure_utc(as_of) if as_of else utc_now()
    pending = db.query(MessageLog).filter(
        MessageLog.execution_status == "RETRY_PENDING",
        MessageLog.next_retry_at <= cutoff
    ).all()

    if not pending:
        return 0

    if not smtp_client:
        smtp_client = SMTPClient()

    reprocessed = 0
    for log in pending:
        next_attempt = log.attempt_count + 1
        logger.info(f"[RETRY PROCESSOR] Re-attempting delivery for key={log.execution_key[:12]} (Attempt {next_attempt})...")

        # Re-fetch template or reconstruct body
        html_body = f"<p>Re-attempted notification for {log.recipient_email}</p>"
        if log.campaign and log.campaign.template:
            try:
                prev = template_service.render_template_preview(
                    db=db,
                    subject_tmpl=log.campaign.template.subject,
                    body_tmpl=log.campaign.template.body,
                    employee_id=log.employee_id
                )
                html_body = prev.rendered_html
            except Exception:
                pass

        delivery_res = smtp_client.send_live_email(
            to_email=log.recipient_email,
            subject=log.subject,
            html_content=html_body,
            attempt=next_attempt
        )

        record_execution(
            session=db,
            execution_key=log.execution_key,
            recipient_email=log.recipient_email,
            subject=log.subject,
            status=delivery_res.status,
            campaign_id=log.campaign_id,
            reminder_id=log.reminder_id,
            employee_id=log.employee_id,
            template_id=log.template_id,
            scheduled_at=log.scheduled_at,
            execution_mode="LIVE_SMTP",
            attempt_count=delivery_res.attempt,
            smtp_response=delivery_res.smtp_response,
            provider_message_id=delivery_res.message_id,
            error_category=delivery_res.error_category,
            error_message=delivery_res.error_message,
            next_retry_at=delivery_res.next_retry_at
        )
        reprocessed += 1

    return reprocessed


# ----------------- Unified Engine Cycle ----------------- #

def run_pending_jobs(
    db: Session,
    simulation_mode: bool = True,
    as_of: Optional[datetime.datetime] = None,
    smtp_client: Optional[SMTPClient] = None
) -> Dict[str, Any]:
    """
    Core polling loop execution unit:
    Identifies all due campaigns and reminders as of the specified timestamp,
    dispatches or simulates them, processes eligible retries, and returns metrics.
    """
    cutoff = ensure_utc(as_of) if as_of else utc_now()
    summary = {
        "timestamp_utc": cutoff.isoformat(),
        "simulation_mode": simulation_mode,
        "due_campaigns_count": 0,
        "due_reminders_count": 0,
        "campaigns_processed": 0,
        "reminders_processed": 0,
        "messages_simulated": 0,
        "messages_accepted": 0,
        "messages_uncertain": 0,
        "retries_scheduled": 0,
        "retries_processed": 0,
        "duplicates_prevented": 0,
        "inactive_skipped": 0,
        "errors": []
    }

    # Safety Guard: Live SMTP mode must fail closed if unconfirmed
    if not simulation_mode:
        env_confirmed = os.getenv("CONFIRM_LIVE_DELIVERY", "").lower() in ("true", "1", "yes") or \
                        os.getenv("LIVE_DELIVERY_CONFIRMED", "").lower() in ("true", "1", "yes")
        if not env_confirmed:
            refusal_err = "Safety refusal: Live SMTP delivery mode requires explicit confirmation (CONFIRM_LIVE_DELIVERY=true). Refusing execution."
            logger.error(f"🚨 [SAFETY REFUSAL] {refusal_err}")
            summary["errors"].append(refusal_err)
            return summary

    try:
        # A. Process due campaigns
        due_campaigns = get_due_campaigns(db, as_of=cutoff)
        summary["due_campaigns_count"] = len(due_campaigns)

        for camp in due_campaigns:
            try:
                res = process_due_campaign(db, camp, simulation_mode=simulation_mode, smtp_client=smtp_client)
                summary["campaigns_processed"] += 1
                summary["messages_simulated"] += res.get("simulated", 0)
                summary["messages_accepted"] += res.get("dispatched", 0)
                summary["messages_uncertain"] += res.get("delivery_uncertain", 0)
                summary["duplicates_prevented"] += res.get("skipped_duplicate", 0)
                summary["inactive_skipped"] += res.get("skipped_inactive", 0)
                summary["retries_scheduled"] += res.get("retry_pending", 0)
                if res.get("errors"):
                    summary["errors"].extend(res["errors"])
            except Exception as e:
                err_camp = f"Error executing Campaign ID={camp.id}: {str(e)}"
                logger.error(err_camp)
                summary["errors"].append(err_camp)

        # B. Process due reminders
        due_reminders = get_due_reminders(db, as_of=cutoff)
        summary["due_reminders_count"] = len(due_reminders)

        for rem in due_reminders:
            try:
                res = process_due_reminder(db, rem, simulation_mode=simulation_mode, smtp_client=smtp_client)
                summary["reminders_processed"] += 1
                if res.get("status") == "SIMULATED_SUCCESS":
                    summary["messages_simulated"] += 1
                elif res.get("status") == "SMTP_ACCEPTED":
                    summary["messages_accepted"] += 1
                elif res.get("status") == "DELIVERY_UNCERTAIN":
                    summary["messages_uncertain"] += 1
                elif res.get("status") == "Skipped_Duplicate":
                    summary["duplicates_prevented"] += 1
                elif res.get("status") == "SKIPPED_INACTIVE":
                    summary["inactive_skipped"] += 1
                elif res.get("status") == "RETRY_PENDING":
                    summary["retries_scheduled"] += 1

                if res.get("error"):
                    summary["errors"].append(res["error"])
            except Exception as e:
                err_rem = f"Error executing ReminderJob ID={rem.id}: {str(e)}"
                logger.error(err_rem)
                summary["errors"].append(err_rem)

        # C. Process pending retries (Live mode only)
        if not simulation_mode:
            try:
                retries_done = process_pending_retries(db, smtp_client=smtp_client, as_of=cutoff)
                summary["retries_processed"] = retries_done
            except Exception as e:
                logger.error(f"Error processing pending retries: {e}")
                summary["errors"].append(str(e))

    except Exception as e:
        logger.error(f"Critical error during run_pending_jobs cycle: {str(e)}")
        summary["errors"].append(str(e))

    return summary
