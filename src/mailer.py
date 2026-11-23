"""
Mailer module: Handles SMTP transport, authentication, message construction,
and Virtual Dry-Run simulation for zero-risk student testing and portfolio proof.
"""
import smtplib
import uuid
import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Any

from src.logger import logger
from src.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SENDER_NAME,
    SENDER_EMAIL,
    DRY_RUN,
    PREVIEWS_DIR
)

class EmailSender:
    def __init__(self, dry_run: bool = DRY_RUN):
        self.dry_run = dry_run
        self.host = SMTP_HOST
        self.port = SMTP_PORT
        self.user = SMTP_USER
        self.password = SMTP_PASSWORD
        self.sender_name = SENDER_NAME
        self.sender_email = SENDER_EMAIL

    def build_message(self, to_email: str, subject: str, html_content: str) -> EmailMessage:
        """Constructs a MIME multi-part EmailMessage with HTML and plain-text fallback."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email
        msg["Date"] = datetime.datetime.now(datetime.timezone.utc)
        msg["Message-ID"] = f"<{uuid.uuid4()}@{self.host}>"

        # Plain-text preview fallback
        plain_fallback = (
            f"{subject}\n\n"
            "This is an automated notification. Please view this email in an HTML-compatible client."
        )
        msg.set_content(plain_fallback)
        msg.add_alternative(html_content, subtype="html")
        return msg

    def save_preview(self, reminder_id: str, to_email: str, subject: str, html_content: str) -> Path:
        """Saves rendered email to disk for visual inspection during dry-run."""
        safe_email = to_email.replace("@", "_at_").replace(".", "_")
        filename = f"{reminder_id}_{safe_email}.html"
        preview_path = PREVIEWS_DIR / filename
        
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return preview_path

    def send_email(self, to_email: str, subject: str, html_content: str, job_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Sends email either via real SMTP or in Virtual Simulation (Dry-Run) mode.
        Returns detailed dispatch result dictionary.
        """
        job_context = job_context or {}
        reminder_id = job_context.get("reminder_id", "N/A")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        msg = self.build_message(to_email, subject, html_content)

        # ----------------------------------------------------
        # Virtual Simulation Mode (DRY RUN)
        # ----------------------------------------------------
        if self.dry_run:
            preview_file = self.save_preview(reminder_id, to_email, subject, html_content)
            logger.info(
                f"[SIMULATION] Dry-run send for '{to_email}' (Reminder {reminder_id}) | "
                f"Subject: '{subject}' | Preview saved: {preview_file.name}"
            )
            return {
                "status": "SIMULATED_SUCCESS",
                "message_id": msg["Message-ID"],
                "timestamp": now_str,
                "error": None,
                "preview_path": str(preview_file)
            }

        # ----------------------------------------------------
        # Real SMTP Delivery Mode
        # ----------------------------------------------------
        if not self.password:
            error_msg = "SMTP_PASSWORD is missing in .env. Run with --dry-run or configure your credentials."
            logger.error(error_msg)
            return {
                "status": "FAILED",
                "message_id": None,
                "timestamp": now_str,
                "error": error_msg,
                "preview_path": None
            }

        try:
            logger.info(f"Connecting to SMTP server {self.host}:{self.port}...")
            if self.port == 465:
                # SSL connection
                with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                # STARTTLS connection (standard for port 587)
                with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.user, self.password)
                    server.send_message(msg)

            logger.info(f"Email successfully delivered to '{to_email}' (Msg-ID: {msg['Message-ID']})")
            return {
                "status": "SENT",
                "message_id": msg["Message-ID"],
                "timestamp": now_str,
                "error": None,
                "preview_path": None
            }

        except smtplib.SMTPAuthenticationError as e:
            err = f"SMTP Authentication failed: Check SMTP_USER and App Password. Details: {e}"
            logger.error(err)
            return {"status": "FAILED", "message_id": None, "timestamp": now_str, "error": err, "preview_path": None}
        except smtplib.SMTPConnectError as e:
            err = f"Could not connect to SMTP server {self.host}:{self.port}. Details: {e}"
            logger.error(err)
            return {"status": "FAILED", "message_id": None, "timestamp": now_str, "error": err, "preview_path": None}
        except Exception as e:
            err = f"Unexpected error while sending to {to_email}: {str(e)}"
            logger.error(err)
            return {"status": "FAILED", "message_id": None, "timestamp": now_str, "error": err, "preview_path": None}
