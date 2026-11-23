"""
Main Entrypoint for the Email Automation & Reminder System.

Usage:
  python main.py                  # Runs 1 dispatch cycle in safe DRY-RUN simulation
  python main.py --dry-run        # Explicit safe dry-run (no emails sent, HTML previews saved)
  python main.py --send-real      # LIVE SMTP mode (sends real emails using .env credentials)
  python main.py --schedule       # Runs continuous scheduler loop
  python main.py --report         # Displays delivery statistics from output CSV
"""
import argparse
import sys
from pathlib import Path

from src.logger import logger
from src.config import DRY_RUN, REPORT_FILE
from src.scheduler import dispatch_batch, run_scheduler_loop

BANNER = r"""
========================================================================
     ___ _  _   _   ___ _       _   _   _ _____ ___  __  __   _ _____ ___ ___  _  _ 
    | __|  \/  |   /_\ |_| |   /_\ | | | |_   _/ _ \|  \/  | /_\_   _|_ _/ _ \| \| |
    | _|| |\/| |  / _ \| | |__/ _ \| |_| | | || (_) | |\/| |/ _ \| |  | | (_) | .` |
    |___|_|  |_| /_/ \_\_|____/_/ \_\\___/  |_| \___/|_|  |_/_/ \_\_| |___\___/|_|\_|
                                & REMINDER SYSTEM
========================================================================
"""

def show_report():
    """Reads and displays summary of previous delivery report."""
    if not REPORT_FILE.exists():
        print("\nNo delivery report found yet. Run an automation cycle first!\n")
        return
    
    import csv
    print(f"\nAudit Log from: {REPORT_FILE}\n")
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print("Report file is empty.")
            return

        print(f"{'Reminder':<10} {'Recipient':<22} {'Priority':<10} {'Status':<18} {'Timestamp':<20}")
        print("-" * 80)
        for r in rows:
            print(f"{r.get('reminder_id',''):<10} {r.get('recipient_email',''):<22} {r.get('priority',''):<10} {r.get('status',''):<18} {r.get('timestamp',''):<20}")
        print("-" * 80)
        print(f"Total Logged Actions: {len(rows)}\n")

def main():
    print(BANNER)
    parser = argparse.ArgumentParser(
        description="Automated Email and Scheduled Reminder Dispatch System."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate email dispatch without connecting to SMTP (HTML previews saved locally)."
    )
    group.add_argument(
        "--send-real",
        action="store_true",
        help="Live dispatch: Connect to SMTP server and send real emails."
    )
    
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Start recurring scheduler loop."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Scheduler loop interval in seconds (default: 30s)."
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show previously logged email delivery report."
    )

    args = parser.parse_args()

    if args.report:
        show_report()
        sys.exit(0)

    # Determine dry-run mode:
    # If --send-real is given -> check confirmation or exit closed
    # If --dry-run is given -> dry_run = True
    # Otherwise fallback to safe simulation mode
    if args.send_real:
        env_confirmed = os.getenv("CONFIRM_LIVE_DELIVERY", "").lower() in ("true", "1", "yes") or \
                        os.getenv("LIVE_DELIVERY_CONFIRMED", "").lower() in ("true", "1", "yes")
        if not env_confirmed:
            logger.error(
                "🚨 [SAFETY REFUSAL] Live SMTP dispatch requested with --send-real, but confirmation "
                "CONFIRM_LIVE_DELIVERY=true is not set in environment. "
                "Execution refused: Live email transmission requires explicit safety confirmation. "
                "Exiting immediately without processing any jobs."
            )
            sys.exit(1)
        dry_run = False
        mode_label = "🔴 LIVE SMTP DISPATCH MODE"
    else:
        dry_run = True
        mode_label = "🟢 VIRTUAL SIMULATION (DRY-RUN) MODE"

    print(f"Active Mode : {mode_label}")
    print(f"Safety Note : {'No real emails will be sent. HTML previews will be generated in outputs/previews/.' if dry_run else 'Live credentials will be used to send real emails.'}\n")

    if args.schedule:
        run_scheduler_loop(interval_seconds=args.interval, dry_run=dry_run)
    else:
        dispatch_batch(dry_run=dry_run)

if __name__ == "__main__":
    main()
