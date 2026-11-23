"""
Reporting module: Audits and logs every email interaction to CSV reports
and generates executive summary metrics for operations teams.
"""
import csv
from pathlib import Path
from typing import List, Dict, Any
from src.logger import logger
from src.config import REPORT_FILE

FIELDNAMES = [
    "reminder_id",
    "contact_id",
    "recipient_name",
    "recipient_email",
    "company",
    "category",
    "priority",
    "subject",
    "status",
    "timestamp",
    "message_id",
    "error",
    "preview_file"
]

class DeliveryReporter:
    def __init__(self, report_path: Path = REPORT_FILE):
        self.report_path = report_path
        self._ensure_file_headers()

    def _ensure_file_headers(self):
        """Creates the CSV file with headers if it does not exist yet."""
        if not self.report_path.exists():
            with open(self.report_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()

    def record_result(self, job: Dict[str, Any], subject: str, result: Dict[str, Any]):
        """Appends a single send attempt record to the CSV delivery audit."""
        row = {
            "reminder_id": job.get("reminder_id", ""),
            "contact_id": job.get("contact_id", ""),
            "recipient_name": job.get("name", ""),
            "recipient_email": job.get("email", ""),
            "company": job.get("company", ""),
            "category": job.get("category", ""),
            "priority": job.get("priority", ""),
            "subject": subject,
            "status": result.get("status", "UNKNOWN"),
            "timestamp": result.get("timestamp", ""),
            "message_id": result.get("message_id") or "N/A",
            "error": result.get("error") or "None",
            "preview_file": Path(result.get("preview_path", "")).name if result.get("preview_path") else "N/A"
        }

        with open(self.report_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)

    def print_summary(self, results: List[Dict[str, Any]]):
        """Prints an executive summary table to terminal."""
        total = len(results)
        successful = sum(1 for r in results if r["status"] in ("SENT", "SIMULATED_SUCCESS"))
        failed = sum(1 for r in results if r["status"] == "FAILED")
        rate = (successful / total * 100) if total > 0 else 0

        summary_box = f"""
============================================================
              AUTOMATION EXECUTION SUMMARY
============================================================
  Total Reminders Processed : {total}
  Successful / Simulated    : {successful}
  Failed Dispatches         : {failed}
  Delivery Success Rate     : {rate:.1f}%
  Audit Report Saved To     : {self.report_path}
============================================================
"""
        print(summary_box)
        logger.info(f"Summary: Total={total}, Success={successful}, Failed={failed}, Rate={rate:.1f}%")
