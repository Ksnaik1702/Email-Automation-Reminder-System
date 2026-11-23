"""
APScheduler-Powered Background Worker Engine for Email Automation & Reminder System.
Continuously scans SQLite database for due campaigns and recurring reminders,
processes occurrences through the scheduling service, enforces idempotency,
and provides clean lifecycle management with graceful shutdown.
"""
import os
import sys
import time
import signal
import argparse
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore

from db.database import SessionLocal, init_db
from src.services import scheduling_service
from src.logger import logger

# Configuration defaults
DEFAULT_POLL_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "10"))
DEFAULT_SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() in ("true", "1", "yes")


class BackgroundWorker:
    """
    Coordinates database initialization, periodic APScheduler trigger jobs,
    crash-recovery startup sweeps, and graceful termination.
    """

    def __init__(
        self,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
        simulation_mode: bool = DEFAULT_SIMULATION_MODE,
        blocking: bool = True
    ):
        self.poll_interval = max(1, poll_interval)
        self.simulation_mode = simulation_mode
        self.blocking = blocking
        self.is_running = False

        # Configure APScheduler with single-instance execution lock
        jobstores = {
            "default": MemoryJobStore()
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=1)
        }
        job_defaults = {
            "coalesce": True,          # Coalesce missed runs into a single run
            "max_instances": 1,        # Prevent concurrent overlapping execution of same job
            "misfire_grace_time": 300  # 5 minutes grace time for delayed triggers
        }

        scheduler_cls = BlockingScheduler if blocking else BackgroundScheduler
        self.scheduler = scheduler_cls(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )

    def trigger_cycle(self) -> dict:
        """
        Executes a single processing cycle with dedicated database session management.
        Recovers and executes all due campaigns and reminders.
        """
        db = SessionLocal()
        try:
            summary = scheduling_service.run_pending_jobs(
                db=db,
                simulation_mode=self.simulation_mode
            )
            if summary["due_campaigns_count"] > 0 or summary["due_reminders_count"] > 0:
                logger.info(
                    f"[WORKER TICK] Processed: Campaigns={summary['campaigns_processed']}, "
                    f"Reminders={summary['reminders_processed']}, "
                    f"Simulated={summary['messages_simulated']}, "
                    f"Duplicates Prevented={summary['duplicates_prevented']}"
                )
            return summary
        except Exception as e:
            logger.error(f"[WORKER ERROR] Unhandled exception during cycle: {e}")
            return {"errors": [str(e)]}
        finally:
            db.close()

    def start(self):
        """Initializes database, runs startup sweep, and launches worker loop."""
        logger.info("=" * 65)
        logger.info("   EMAIL AUTOMATION & REMINDER SYSTEM: BACKGROUND WORKER")
        logger.info("=" * 65)
        logger.info(f"Mode          : {'🟢 SIMULATION (DRY-RUN)' if self.simulation_mode else '🚨 LIVE SMTP'}")
        logger.info(f"Poll Interval : Every {self.poll_interval} seconds")
        logger.info(f"Engine        : APScheduler (Single-Worker Coalesced)")
        logger.info("=" * 65)

        # 1. Initialize DB schema if needed
        init_db()

        # 2. Startup sweep: Catch up any overdue jobs from downtime / crash
        logger.info("Executing startup catch-up sweep for pending overdue jobs...")
        self.trigger_cycle()

        # 3. Register recurring APScheduler job
        self.scheduler.add_job(
            func=self.trigger_cycle,
            trigger="interval",
            seconds=self.poll_interval,
            id="worker_periodic_sweep",
            replace_existing=True
        )

        self.is_running = True

        # 4. Attach OS signal handlers for graceful shutdown
        def _handle_signal(sig, frame):
            logger.info(f"Received signal {sig}. Initiating graceful worker shutdown...")
            self.stop()
            sys.exit(0)

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except Exception:
            pass  # Some environments/threads restrict signal handling

        logger.info(f"Background worker is active and listening for due jobs...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Worker stopped by keyboard interrupt.")
            self.stop()

    def stop(self):
        """Stops the scheduler cleanly."""
        if self.is_running:
            self.is_running = False
            try:
                self.scheduler.shutdown(wait=False)
                logger.info("APScheduler shutdown complete.")
            except Exception as e:
                logger.warning(f"Error during scheduler shutdown: {e}")


def main():
    parser = argparse.ArgumentParser(description="Email Automation Background Worker")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle and exit immediately")
    parser.add_argument("--live", action="store_true", help="Disable simulation mode (Not recommended in Phase 5)")
    args = parser.parse_args()

    simulation = not args.live

    if args.once:
        init_db()
        logger.info(f"Running single evaluation sweep (simulation={simulation})...")
        worker = BackgroundWorker(poll_interval=args.interval, simulation_mode=simulation, blocking=False)
        result = worker.trigger_cycle()
        logger.info(f"Single sweep completed: {result}")
    else:
        worker = BackgroundWorker(poll_interval=args.interval, simulation_mode=simulation, blocking=True)
        worker.start()


if __name__ == "__main__":
    main()
