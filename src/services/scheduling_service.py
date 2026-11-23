"""
Scheduling Service Layer: Engine for identifying due campaigns and reminders,
claiming jobs safely, rendering personalized content via Jinja2 sandboxing,
enforcing SHA-256 idempotency, advancing calendar-aware recurrences, and recording
execution logs into SQLite as the single source of truth.
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
    simulation_mode: bool = True
) -> Dict[str, Any]:
    """
    Executes a single due campaign:
    1. Claims the campaign by setting status='PROCESSING'.
    2. Loads template and validates existence.
    3. Iterates over targeted recipients.
    4. Evaluates SHA-256 idempotency key per recipient.
    5. Renders personalized email with Jinja2 sandboxing.
    6. In simulation mode: outputs HTML preview and records SIMULATED_SUCCESS.
    7. Updates CampaignRecipient.status and Campaign.status='COMPLETED'.
    """
    stats = {
        "campaign_id": campaign.id,
        "campaign_name": campaign.campaign_name,
        "total_recipients": len(campaign.recipients),
        "dispatched": 0,
        "simulated": 0,
        "skipped_duplicate": 0,
        "errors": []
    }

    logger.info(f"Processing Campaign ID={campaign.id} ('{campaign.campaign_name}') with {len(campaign.recipients)} recipients...")

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

        # 2. Idempotency Check
        if is_already_executed(db, exec_key):
            logger.info(f"[IDEMPOTENCY] Skipping duplicate occurrence for campaign {campaign.id} to '{recip_email}' (key={exec_key[:12]}...)")
            recipient.status = "Skipped_Duplicate"
            stats["skipped_duplicate"] += 1
            continue

        # 3. Render Personalized Email
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

        # 4. Dispatch or Simulate
        if simulation_mode:
            # Virtual Simulation Mode
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
                scheduled_at=scheduled_timestamp
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
            # Live delivery reserved for Phase 6
            # In Phase 5, safety default blocks live execution
            raise NotImplementedError("Live SMTP delivery is not enabled in Phase 5. Use simulation_mode=True.")

    # 5. Mark campaign complete
    campaign.status = "COMPLETED"
    campaign.updated_at = utc_now()
    db.commit()

    logger.info(f"Campaign ID={campaign.id} completed: Simulated={stats['simulated']}, Skipped={stats['skipped_duplicate']}, Errors={len(stats['errors'])}")
    return stats


def process_due_reminder(
    db: Session,
    reminder: ReminderJob,
    simulation_mode: bool = True
) -> Dict[str, Any]:
    """
    Executes a single due reminder occurrence:
    1. Validates employee existence.
    2. Generates deterministic SHA-256 idempotency key for this exact scheduled occurrence.
    3. Checks MessageLog for duplicate prevention.
    4. Renders content.
    5. In simulation mode: outputs preview file and records SIMULATED_SUCCESS.
    6. Advances recurring schedules (Daily, Weekly, Monthly) to the next UTC occurrence,
       or marks one-time reminders as 'Completed'.
    """
    stats = {
        "reminder_id": reminder.id,
        "title": reminder.reminder_title,
        "status": "Pending",
        "error": None
    }

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
  <p>This is an automated reminder regarding:</p>
  <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
    <strong style="font-size: 15px; color: #1e40af;">{reminder.reminder_title}</strong>
  </div>
  <p style="font-size: 13px; color: #64748b;">
    Department: {emp.department} | Recurrence: {reminder.recurrence_type} | Timezone: {reminder.timezone}
  </p>
</div>"""
        plain_text = f"Reminder: {reminder.reminder_title}\n\nHello {emp.full_name},\nThis is a scheduled reminder regarding: {reminder.reminder_title}\n\nDepartment: {emp.department}"

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
                scheduled_at=scheduled_utc
            )

            if recorded:
                stats["status"] = "SIMULATED_SUCCESS"
                logger.info(f"[SIMULATION] Rendered reminder preview for '{recip_email}' -> {preview_path.name}")
            else:
                stats["status"] = "Skipped_Duplicate"
                logger.warning(f"[IDEMPOTENCY] Blocked duplicate insert: {rec_err}")
        else:
            raise NotImplementedError("Live delivery reserved for Phase 6.")

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


# ----------------- Unified Engine Cycle ----------------- #

def run_pending_jobs(
    db: Session,
    simulation_mode: bool = True,
    as_of: Optional[datetime.datetime] = None
) -> Dict[str, Any]:
    """
    Core polling loop execution unit:
    Identifies all due campaigns and reminders as of the specified timestamp,
    dispatches or simulates them, handles crashes and recovery, and returns
    aggregate performance metrics.
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
        "messages_sent": 0,
        "duplicates_prevented": 0,
        "errors": []
    }

    try:
        # A. Process due campaigns
        due_campaigns = get_due_campaigns(db, as_of=cutoff)
        summary["due_campaigns_count"] = len(due_campaigns)

        for camp in due_campaigns:
            try:
                res = process_due_campaign(db, camp, simulation_mode=simulation_mode)
                summary["campaigns_processed"] += 1
                summary["messages_simulated"] += res.get("simulated", 0)
                summary["messages_sent"] += res.get("dispatched", 0)
                summary["duplicates_prevented"] += res.get("skipped_duplicate", 0)
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
                res = process_due_reminder(db, rem, simulation_mode=simulation_mode)
                summary["reminders_processed"] += 1
                if res.get("status") == "SIMULATED_SUCCESS":
                    summary["messages_simulated"] += 1
                elif res.get("status") == "SENT":
                    summary["messages_sent"] += 1
                elif res.get("status") == "Skipped_Duplicate":
                    summary["duplicates_prevented"] += 1
                if res.get("error"):
                    summary["errors"].append(res["error"])
            except Exception as e:
                err_rem = f"Error executing ReminderJob ID={rem.id}: {str(e)}"
                logger.error(err_rem)
                summary["errors"].append(err_rem)

    except Exception as e:
        logger.error(f"Critical error during run_pending_jobs cycle: {str(e)}")
        summary["errors"].append(str(e))

    return summary
