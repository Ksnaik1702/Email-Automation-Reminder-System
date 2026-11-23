"""
Scheduler module: Coordinates time-based triggers, batch dispatches,
and recurring automated polling using Python's schedule library.
"""
import time
import datetime
from typing import List, Dict, Any
from src.logger import logger
from src.data_loader import get_merged_reminder_jobs
from src.templating import render_email_content
from src.mailer import EmailSender
from src.reporter import DeliveryReporter

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

def dispatch_batch(dry_run: bool = True) -> List[Dict[str, Any]]:
    """
    Executes a complete cycle of reading contacts/reminders,
    personalizing templates, sending (or simulating) emails,
    and recording delivery metrics.
    """
    logger.info(f"=== Starting Reminder Dispatch Cycle (dry_run={dry_run}) ===")
    jobs = get_merged_reminder_jobs()
    sender = EmailSender(dry_run=dry_run)
    reporter = DeliveryReporter()
    results = []

    for job in jobs:
        to_email = job.get("email")
        template_name = job.get("template_name", "meeting_reminder.html")
        reminder_id = job.get("reminder_id")

        try:
            subject, html_body = render_email_content(template_name, job)
            send_result = sender.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_body,
                job_context=job
            )
            reporter.record_result(job, subject, send_result)
            results.append(send_result)

        except Exception as e:
            err_msg = f"Failed to process reminder {reminder_id}: {str(e)}"
            logger.error(err_msg)
            fail_result = {
                "status": "FAILED",
                "message_id": None,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e),
                "preview_path": None
            }
            reporter.record_result(job, f"Reminder Error ({reminder_id})", fail_result)
            results.append(fail_result)

    reporter.print_summary(results)
    return results

def run_scheduler_loop(interval_seconds: int = 30, dry_run: bool = True, max_cycles: int = None):
    """
    Continuous worker loop that triggers dispatch every interval_seconds.
    Can be stopped cleanly with Ctrl+C or after max_cycles (useful for testing).
    """
    logger.info(f"Starting continuous scheduler loop (interval: {interval_seconds}s, dry_run: {dry_run})...")
    cycles = 0

    if SCHEDULE_AVAILABLE:
        schedule.every(interval_seconds).seconds.do(dispatch_batch, dry_run=dry_run)
        logger.info("Using 'schedule' library for job orchestration.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    logger.info(f"Reached max test cycles ({max_cycles}). Exiting scheduler loop.")
                    break
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user (Ctrl+C). Stopped gracefully.")
    else:
        logger.info("'schedule' package not installed, running built-in timing loop.")
        try:
            while True:
                dispatch_batch(dry_run=dry_run)
                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    logger.info(f"Reached max test cycles ({max_cycles}). Exiting scheduler loop.")
                    break
                logger.info(f"Sleeping for {interval_seconds} seconds until next check...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user. Stopped gracefully.")
