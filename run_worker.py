"""
Worker Daemon: Continuous scheduling and dispatch worker.
Processes RRULE recurrence rules and dispatches due messages.
"""
import time
import os
import uuid
import datetime as dt
from src.logger import logger
from src.config import DRY_RUN
from src.renderer import render_email
from src.mailer import EmailSender
from db.database import get_connection, init_db

try:
    from dateutil.rrule import rrulestr
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

def plan_next_fires(conn, now_iso: str):
    """
    Expands active reminders into scheduled messages table if due.
    Supports single runs and RFC 5545 RRULE recurring schedules.
    """
    cursor = conn.cursor()
    reminders = cursor.execute(
        "SELECT id, contact_id, campaign_id, start_at_utc, rrule, last_fired_at_utc "
        "FROM reminders WHERE active = 1;"
    ).fetchall()

    now_dt = dt.datetime.fromisoformat(now_iso)

    for r in reminders:
        rid = r["id"]
        start_str = r["start_at_utc"].replace("Z", "+00:00")
        try:
            start_dt = dt.datetime.fromisoformat(start_str)
        except Exception:
            continue

        rrule_str = r["rrule"]
        last_str = r["last_fired_at_utc"]
        last_dt = dt.datetime.fromisoformat(last_str) if last_str else None

        next_fire = None
        if rrule_str and DATEUTIL_AVAILABLE:
            try:
                rule = rrulestr(rrule_str, dtstart=start_dt)
                seed = last_dt or (start_dt - dt.timedelta(seconds=1))
                next_fire = rule.after(seed, inc=True)
            except Exception as e:
                logger.warning(f"Error parsing RRULE for reminder {rid}: {e}")
        else:
            # One-off reminder
            if not last_dt and start_dt <= now_dt:
                next_fire = start_dt

        # If a fire is due within the next minute, enqueue into messages
        if next_fire and next_fire <= now_dt + dt.timedelta(minutes=1):
            mid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO messages(id, campaign_id, contact_id, scheduled_at_utc, status) "
                "VALUES (?, ?, ?, ?, 'scheduled');",
                (mid, r["campaign_id"], r["contact_id"], next_fire.isoformat())
            )
            conn.execute(
                "UPDATE reminders SET last_fired_at_utc = ? WHERE id = ?;",
                (now_dt.isoformat(), rid)
            )
            logger.info(f"[PLANNER] Enqueued scheduled message {mid} for reminder {rid}")

    conn.commit()

def dispatch_due(conn, mailer: EmailSender, now_iso: str):
    """
    Selects all scheduled messages due for dispatch,
    renders their subject and markdown content, and sends/simulates them.
    """
    cursor = conn.cursor()
    query = """
    SELECT m.id, m.campaign_id, m.contact_id, t.subject, t.body_md,
           c.name as cname, c.email as cemail, c.unsubscribed,
           camp.sender_name, camp.sender_email
    FROM messages m
    JOIN campaigns camp ON camp.id = m.campaign_id
    JOIN templates t ON t.id = camp.template_id
    JOIN contacts c ON c.id = m.contact_id
    WHERE m.status = 'scheduled' AND m.scheduled_at_utc <= ?;
    """
    due_rows = cursor.execute(query, (now_iso,)).fetchall()

    for row in due_rows:
        mid = row["id"]
        # Safety check: honor unsubscribe
        if row["unsubscribed"]:
            logger.warning(f"Contact {row['cemail']} has unsubscribed. Cancelling message {mid}.")
            conn.execute("UPDATE messages SET status = 'cancelled', error = 'User unsubscribed' WHERE id = ?;", (mid,))
            continue

        context = {
            "name": row["cname"],
            "email": row["cemail"],
            "message_id": mid
        }
        subj, html = render_email(row["subject"], row["body_md"], context)

        # Dispatch via mailer
        result = mailer.send_email(
            to_email=row["cemail"],
            subject=subj,
            html_content=html,
            job_context={"reminder_id": mid}
        )

        if result["status"] in ("SENT", "SIMULATED_SUCCESS"):
            conn.execute(
                "UPDATE messages SET status = 'sent', sent_at_utc = ?, body_rendered_html = ?, provider_msg_id = ? WHERE id = ?;",
                (now_iso, html, result.get("message_id"), mid)
            )
            logger.info(f"[DISPATCHER] Message {mid} successfully processed ({result['status']})")
        else:
            conn.execute(
                "UPDATE messages SET status = 'failed', error = ? WHERE id = ?;",
                (result.get("error", "Unknown error"), mid)
            )
            logger.error(f"[DISPATCHER] Message {mid} failed: {result.get('error')}")

    conn.commit()

def run_worker_loop(interval: int = 15, run_once: bool = False):
    """Main worker daemon polling loop."""
    init_db()
    mailer = EmailSender(dry_run=DRY_RUN)
    logger.info(f"Worker process started (interval={interval}s, dry_run={DRY_RUN})")

    try:
        while True:
            now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
            conn = get_connection()
            try:
                plan_next_fires(conn, now_iso)
                dispatch_due(conn, mailer, now_iso)
            finally:
                conn.close()

            if run_once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the Email Automation background worker.")
    parser.add_argument("--once", action="store_true", help="Run a single planning & dispatch cycle and exit.")
    parser.add_argument("--interval", type=int, default=15, help="Tick interval in seconds.")
    args = parser.parse_args()

    run_worker_loop(interval=args.interval, run_once=args.once)
