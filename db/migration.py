"""
Safe Data Migration & Ingestion Service.
Migrates existing CSV records (contacts.csv, reminders.csv, delivery_report.csv)
and HTML template files into the normalized SQLAlchemy models idempotently.
"""
import csv
import hashlib
import sys
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog
from src.config import DATA_DIR, TEMPLATES_DIR, OUTPUTS_DIR, CONTACTS_FILE, REMINDERS_FILE, REPORT_FILE
from src.logger import logger


def generate_execution_key(reminder_code: str, recipient_email: str, timestamp_str: str) -> str:
    """Generates a deterministic idempotency hash for an execution instance."""
    raw = f"{reminder_code.strip()}:{recipient_email.strip().lower()}:{timestamp_str.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def migrate_employees(session) -> int:
    """Migrates data/contacts.csv into Employee records."""
    if not CONTACTS_FILE.exists():
        logger.warning(f"Contacts file not found: {CONTACTS_FILE}")
        return 0

    imported_count = 0
    with open(CONTACTS_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("contact_id", "").strip()
            email = row.get("email", "").strip().lower()
            if not cid or not email:
                continue

            existing = session.query(Employee).filter(
                (Employee.employee_id == cid) | (Employee.email == email)
            ).first()

            if not existing:
                emp = Employee(
                    employee_id=cid,
                    full_name=row.get("name", "").strip(),
                    email=email,
                    company=row.get("company", "").strip(),
                    department=row.get("department", "").strip(),
                    designation=row.get("role", "").strip(),
                    timezone=row.get("timezone", "Asia/Kolkata").strip(),
                    employment_status="Active"
                )
                session.add(emp)
                imported_count += 1

    session.commit()
    logger.info(f"Employee migration completed: {imported_count} new employees inserted.")
    return imported_count


def migrate_templates(session) -> int:
    """Imports HTML templates from templates/ directory into EmailTemplate table."""
    if not TEMPLATES_DIR.exists():
        return 0

    imported_count = 0
    default_templates = [
        ("meeting_reminder.html", "Meeting", "📅 Scheduled Meeting Alert - {{ title }}"),
        ("payment_due_reminder.html", "Finance", "🚨 [URGENT] Outstanding Invoice Due: {{ title }}"),
        ("class_webinar_reminder.html", "Training", "🎓 Masterclass Alert: {{ title }}")
    ]

    for filename, category, default_subject in default_templates:
        filepath = TEMPLATES_DIR / filename
        if not filepath.exists():
            continue

        existing = session.query(EmailTemplate).filter_by(template_name=filename).first()
        if not existing:
            with open(filepath, "r", encoding="utf-8") as f:
                body_content = f.read()

            tmpl = EmailTemplate(
                template_name=filename,
                category=category,
                subject=default_subject,
                body=body_content
            )
            session.add(tmpl)
            imported_count += 1

    session.commit()
    logger.info(f"Template migration completed: {imported_count} templates registered.")
    return imported_count


def migrate_campaigns_and_reminders(session) -> int:
    """Migrates data/reminders.csv into Campaign, CampaignRecipient, and ReminderJob records."""
    if not REMINDERS_FILE.exists():
        return 0

    imported_jobs = 0
    with open(REMINDERS_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row.get("reminder_id", "").strip()
            cid = row.get("contact_id", "").strip()
            title = row.get("title", "").strip()
            template_name = row.get("template_name", "meeting_reminder.html").strip()
            category = row.get("category", "General").strip()
            due_date_str = row.get("due_date", "").strip()

            # Find employee
            emp = session.query(Employee).filter_by(employee_id=cid).first()
            if not emp:
                continue

            # Find or fallback template
            tmpl = session.query(EmailTemplate).filter_by(template_name=template_name).first()
            if not tmpl:
                tmpl = session.query(EmailTemplate).first()
                if not tmpl:
                    continue

            # Find or create a parent campaign for this category
            camp_name = f"{category} Notification Pipeline"
            camp = session.query(Campaign).filter_by(campaign_name=camp_name).first()
            if not camp:
                camp = Campaign(
                    campaign_name=camp_name,
                    description=f"Automated pipeline for {category} reminders",
                    category=category,
                    template_id=tmpl.id,
                    status="Scheduled"
                )
                session.add(camp)
                session.flush()

            # Ensure CampaignRecipient relationship exists
            existing_recipient = session.query(CampaignRecipient).filter_by(
                campaign_id=camp.id, employee_id=emp.id
            ).first()
            if not existing_recipient:
                rec = CampaignRecipient(
                    campaign_id=camp.id,
                    employee_id=emp.id,
                    recipient_email=emp.email,
                    status="Pending"
                )
                session.add(rec)

            # Check if ReminderJob already exists
            existing_job = session.query(ReminderJob).filter_by(
                employee_id=emp.id, reminder_title=title
            ).first()

            if not existing_job:
                # Parse scheduled date
                try:
                    sched_dt = datetime.datetime.strptime(due_date_str, "%Y-%m-%d")
                except Exception:
                    sched_dt = datetime.datetime.utcnow() + datetime.timedelta(days=1)

                r_job = ReminderJob(
                    campaign_id=camp.id,
                    employee_id=emp.id,
                    reminder_title=title,
                    scheduled_at=sched_dt,
                    timezone=emp.timezone,
                    recurrence_type="None",
                    status="Active"
                )
                session.add(r_job)
                imported_jobs += 1

    session.commit()
    logger.info(f"Reminders migration completed: {imported_jobs} jobs created.")
    return imported_jobs


def migrate_delivery_reports(session) -> int:
    """
    Migrates historical outputs/delivery_report.csv records into MessageLog.
    Uses execution_key hashing to eliminate duplicates automatically!
    """
    if not REPORT_FILE.exists():
        return 0

    migrated_count = 0
    duplicate_count = 0

    with open(REPORT_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rem_code = row.get("reminder_id", "R_MIG").strip()
            email = row.get("recipient_email", "").strip()
            ts = row.get("timestamp", "").strip()
            status = row.get("status", "UNKNOWN").strip()
            subj = row.get("subject", "Automated Reminder").strip()
            err = row.get("error") if row.get("error") != "None" else None

            if not email or not ts:
                continue

            exec_key = generate_execution_key(rem_code, email, ts)

            # Check if this exact execution was already logged (Deduplication)
            existing_log = session.query(MessageLog).filter_by(execution_key=exec_key).first()
            if existing_log:
                duplicate_count += 1
                continue

            # Resolve employee if possible
            emp = session.query(Employee).filter_by(email=email).first()

            # Parse execution timestamp
            try:
                exec_dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                exec_dt = datetime.datetime.utcnow()

            log_entry = MessageLog(
                employee_id=emp.id if emp else None,
                recipient_email=email,
                subject=subj,
                execution_status=status,
                executed_at=exec_dt,
                error_message=err,
                execution_key=exec_key
            )
            session.add(log_entry)
            migrated_count += 1

    session.commit()
    logger.info(
        f"Delivery report migration completed: {migrated_count} unique execution records preserved. "
        f"{duplicate_count} duplicate rows filtered out."
    )
    return migrated_count


def run_full_migration():
    """Executes full idempotent migration suite."""
    init_db()
    session = SessionLocal()
    try:
        e_count = migrate_employees(session)
        t_count = migrate_templates(session)
        r_count = migrate_campaigns_and_reminders(session)
        l_count = migrate_delivery_reports(session)
        print(f"Migration finished: Employees={e_count}, Templates={t_count}, Reminders={r_count}, Logs={l_count}")
    finally:
        session.close()


if __name__ == "__main__":
    run_full_migration()
