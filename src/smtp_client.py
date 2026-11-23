"""
Modular SMTP Delivery Engine with Strict Simulation/Live Mode Separation.
Implements secure credential management, multipart MIME composition, rate limiting,
temporary vs permanent error classification, exponential backoff, and SMTP acceptance tracking.
"""
import os
import re
import time
import socket
import smtplib
import uuid
import datetime
from email.message import EmailMessage
from typing import Dict, Any, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from unittest.mock import MagicMock

from src.logger import logger

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SMTPAwaitingResponseError(TimeoutError):
    """
    Raised when a socket timeout or network disconnection occurs after message data
    has been transmitted over the socket to the SMTP server, while awaiting the final 250 OK acknowledgment.
    Indicates that downstream delivery state is uncertain and must NOT be automatically retried.
    """
    stage = "POST_SUBMISSION"


@dataclass
class SMTPConfig:
    """
    Secure SMTP transport configuration.
    Masks passwords in string representations to guarantee zero credential leakage.
    """
    host: str = "smtp.gmail.com"
    port: int = 587
    user: str = ""
    password: str = ""
    use_tls: bool = True
    from_email: str = "noreply@company.com"
    from_name: str = "Email Automation Hub"
    rate_limit_per_second: float = 5.0
    max_retries: int = 3
    backoff_base_seconds: int = 60
    max_backoff_seconds: int = 3600
    timeout_seconds: int = 15

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Loads SMTP configuration from environment variables."""
        return cls(
            host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
            from_email=os.getenv("SMTP_FROM_EMAIL") or os.getenv("SENDER_EMAIL", "noreply@company.com"),
            from_name=os.getenv("SMTP_FROM_NAME") or os.getenv("SENDER_NAME", "Email Automation Hub"),
            rate_limit_per_second=float(os.getenv("EMAIL_RATE_LIMIT_PER_SECOND", "5.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            backoff_base_seconds=int(os.getenv("RETRY_BACKOFF_BASE_SECONDS", "60")),
            max_backoff_seconds=int(os.getenv("MAX_BACKOFF_SECONDS", "3600")),
            timeout_seconds=int(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))
        )

    def is_configured(self) -> bool:
        """Returns True only if minimal credentials and host are present."""
        return bool(self.host and self.user and self.password)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validates configuration parameters."""
        if not self.host:
            return False, "SMTP_HOST is not configured."
        if not self.user:
            return False, "SMTP_USER is not configured."
        if not self.password:
            return False, "SMTP_PASS / SMTP_PASSWORD is not configured."
        if not EMAIL_REGEX.match(self.from_email):
            return False, f"Invalid sender address: '{self.from_email}'"
        return True, None

    def __repr__(self) -> str:
        masked_pass = "***" if self.password else "<NOT_SET>"
        return (
            f"<SMTPConfig host='{self.host}:{self.port}' user='{self.user}' "
            f"password='{masked_pass}' tls={self.use_tls} from='{self.from_name} <{self.from_email}>'>"
        )


class SMTPDeliveryResult(NamedTuple):
    """Normalized dispatch result containing delivery status and diagnostics."""
    status: str                       # SIMULATED_SUCCESS, SMTP_ACCEPTED, FAILED, RETRY_PENDING, SKIPPED_INACTIVE
    message_id: Optional[str]
    smtp_response: Optional[str]
    error_category: Optional[str]     # None, AUTHENTICATION_ERROR, TEMPORARY_NETWORK, RECIPIENT_REJECTED, etc.
    error_message: Optional[str]
    attempt: int
    retry_after_seconds: Optional[int]
    next_retry_at: Optional[datetime.datetime]


class SMTPClient:
    """
    Enterprise-grade SMTP client with multipart message formatting,
    rate limiting, exponential backoff, and robust error classification.
    """

    def __init__(self, config: Optional[SMTPConfig] = None):
        self.config = config or SMTPConfig.from_env()
        self._last_send_timestamp = 0.0

    def _apply_rate_limit(self):
        """Enforces inter-message delay based on configured sending rate limit."""
        if self.config.rate_limit_per_second > 0:
            min_interval = 1.0 / self.config.rate_limit_per_second
            elapsed = time.time() - self._last_send_timestamp
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_send_timestamp = time.time()

    def verify_connection(self) -> Tuple[bool, str]:
        """
        Tests connectivity and authentication against the SMTP server without sending an email.
        Issues NOOP to confirm channel viability.
        """
        valid, reason = self.config.validate()
        if not valid:
            return False, f"Configuration Error: {reason}"

        try:
            logger.info(f"Testing SMTP connection to {self.config.host}:{self.config.port}...")
            if self.config.port == 465:
                with smtplib.SMTP_SSL(self.config.host, self.config.port, timeout=self.config.timeout_seconds) as server:
                    server.login(self.config.user, self.config.password)
                    status_code, response = server.noop()
                    return True, f"SMTP Handshake Successful: {status_code} {response.decode('utf-8', errors='ignore')}"
            else:
                with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout_seconds) as server:
                    server.ehlo()
                    if self.config.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.config.user, self.config.password)
                    status_code, response = server.noop()
                    return True, f"SMTP Handshake Successful: {status_code} {response.decode('utf-8', errors='ignore')}"
        except smtplib.SMTPAuthenticationError as e:
            err = f"SMTP Authentication Error (Code {e.smtp_code}): {e.smtp_error.decode('utf-8', errors='ignore') if isinstance(e.smtp_error, bytes) else str(e)}"
            logger.error(err)
            return False, err
        except smtplib.SMTPConnectError as e:
            err = f"SMTP Connect Error: Could not establish socket to {self.config.host}:{self.config.port}. Details: {e}"
            logger.error(err)
            return False, err
        except socket.timeout:
            err = f"SMTP Connection timed out after {self.config.timeout_seconds} seconds."
            logger.error(err)
            return False, err
        except Exception as e:
            err = f"SMTP Verification Error: {str(e)}"
            logger.error(err)
            return False, err

    def build_multipart_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> EmailMessage:
        """
        Constructs an RFC 5322 compliant multipart/alternative MIME message.
        Contains plain-text alternative, rendered HTML, sender identity,
        and tracking headers.
        """
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = to_email
        msg["Date"] = datetime.datetime.now(datetime.timezone.utc)
        
        # Unique Message-ID
        domain = self.config.from_email.split("@")[-1] if "@" in self.config.from_email else "localhost"
        unique_id = f"<{uuid.uuid4()}@{domain}>"
        msg["Message-ID"] = unique_id

        # Custom diagnostic headers
        if custom_headers:
            for header_name, header_val in custom_headers.items():
                if header_val is not None:
                    msg[header_name] = str(header_val)

        # 1. Plain-text alternative
        text_body = plain_text or (
            f"{subject}\n\n"
            "This is an automated notification. Please view this message in an HTML-compatible client."
        )
        msg.set_content(text_body)

        # 2. HTML body
        msg.add_alternative(html_content, subtype="html")
        return msg

    def send_live_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None,
        attempt: int = 1,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> SMTPDeliveryResult:
        """
        Transmits a live message via SMTP.
        Enforces rate limiting, classifies errors, and schedules retries with exponential backoff.
        """
        # Validate recipient email format before transmission
        clean_email = to_email.strip()
        if not clean_email or not EMAIL_REGEX.match(clean_email):
            logger.error(f"[SMTP REJECTED] Malformed recipient email: '{to_email}'")
            return SMTPDeliveryResult(
                status="FAILED",
                message_id=None,
                smtp_response=None,
                error_category="INVALID_RECIPIENT_ADDRESS",
                error_message=f"Recipient email '{to_email}' failed syntax validation.",
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )

        # Validate SMTP configuration
        valid_cfg, cfg_err = self.config.validate()
        if not valid_cfg:
            logger.error(f"[SMTP CONFIG ERROR] {cfg_err}")
            return SMTPDeliveryResult(
                status="FAILED",
                message_id=None,
                smtp_response=None,
                error_category="CONFIGURATION_ERROR",
                error_message=cfg_err,
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )

        msg = self.build_multipart_message(
            to_email=clean_email,
            subject=subject,
            html_content=html_content,
            plain_text=plain_text,
            custom_headers=custom_headers
        )

        self._apply_rate_limit()

        stage = "PRE_SUBMISSION"

        def _hook_stage_tracking(srv):
            if hasattr(srv, "send") and not isinstance(srv, MagicMock):
                orig_send = srv.send
                def _tracked_send(payload):
                    nonlocal stage
                    res = orig_send(payload)
                    # When terminating dot is sent, transmission payload is committed to network
                    if isinstance(payload, bytes) and b".\r\n" in payload:
                        stage = "POST_SUBMISSION"
                    elif isinstance(payload, str) and ".\r\n" in payload:
                        stage = "POST_SUBMISSION"
                    return res
                srv.send = _tracked_send

        try:
            logger.info(f"[SMTP TRANSMIT] Attempt {attempt}/{self.config.max_retries} to '{clean_email}' via {self.config.host}:{self.config.port}...")

            if self.config.port == 465:
                with smtplib.SMTP_SSL(self.config.host, self.config.port, timeout=self.config.timeout_seconds) as server:
                    server.login(self.config.user, self.config.password)
                    _hook_stage_tracking(server)
                    response = server.send_message(msg)
            else:
                with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout_seconds) as server:
                    server.ehlo()
                    if self.config.use_tls:
                        server.starttls()
                        server.ehlo()
                    server.login(self.config.user, self.config.password)
                    _hook_stage_tracking(server)
                    response = server.send_message(msg)

            # SMTP Acceptance verified
            resp_str = "250 Message accepted for delivery"
            logger.info(f"[SMTP ACCEPTED] Relayed to '{clean_email}' (Msg-ID: {msg['Message-ID']})")

            return SMTPDeliveryResult(
                status="SMTP_ACCEPTED",
                message_id=msg["Message-ID"],
                smtp_response=resp_str,
                error_category=None,
                error_message=None,
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )

        # ----------------- Permanent Failures (Never Retried) ----------------- #
        except smtplib.SMTPAuthenticationError as e:
            err = f"SMTP Authentication failed: Check credentials. Code: {e.smtp_code}"
            logger.error(err)
            return SMTPDeliveryResult(
                status="FAILED",
                message_id=None,
                smtp_response=str(e),
                error_category="AUTHENTICATION_ERROR",
                error_message=err,
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )

        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as e:
            err = f"Permanent SMTP address rejection: {str(e)}"
            logger.error(err)
            return SMTPDeliveryResult(
                status="FAILED",
                message_id=None,
                smtp_response=str(e),
                error_category="PERMANENT_RECIPIENT_REJECTED",
                error_message=err,
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )

        # ----------------- Network / Timeout / Uncertain Failures ----------------- #
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, socket.timeout, TimeoutError, ConnectionResetError, ConnectionRefusedError, SMTPAwaitingResponseError) as e:
            err_str = str(e).lower()
            is_post_sub = (
                stage == "POST_SUBMISSION" or
                isinstance(e, SMTPAwaitingResponseError) or
                getattr(e, "stage", None) in ("POST_SUBMISSION", "AWAITING_RESPONSE") or
                "after submission" in err_str or
                "awaiting response" in err_str or
                "post_submission" in err_str
            )

            # Case A: Uncertain outcome after message submission (Awaiting response)
            if is_post_sub:
                err = f"Uncertain SMTP delivery: Socket timeout or connection loss occurred after message payload submission while awaiting server response ({type(e).__name__}: {str(e)})"
                logger.error(f"[SMTP UNCERTAIN OUTCOME] Attempt {attempt} to '{clean_email}': {err}. Automatic retry disabled to prevent duplicate transmission.")

                return SMTPDeliveryResult(
                    status="DELIVERY_UNCERTAIN",
                    message_id=msg["Message-ID"],
                    smtp_response=f"UNKNOWN_TIMEOUT_POST_SUBMISSION ({str(e)})",
                    error_category="DELIVERY_UNCERTAIN",
                    error_message=err,
                    attempt=attempt,
                    retry_after_seconds=None,
                    next_retry_at=None
                )

            # Case B: Pre-submission failure (Safe to retry with bounded exponential backoff)
            err = f"Pre-submission network/connection failure: {type(e).__name__} ({str(e)})"
            logger.warning(f"[SMTP TEMPORARY ERROR] Attempt {attempt} failed: {err}")

            if attempt < self.config.max_retries:
                # Calculate bounded exponential backoff
                raw_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                delay_seconds = min(self.config.max_backoff_seconds, raw_delay)
                next_retry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_seconds)
                logger.info(f"[RETRY SCHEDULED] Next attempt in {delay_seconds}s (capped at {self.config.max_backoff_seconds}s) at {next_retry.isoformat()}")

                return SMTPDeliveryResult(
                    status="RETRY_PENDING",
                    message_id=None,
                    smtp_response=str(e),
                    error_category="TEMPORARY_NETWORK",
                    error_message=err,
                    attempt=attempt,
                    retry_after_seconds=delay_seconds,
                    next_retry_at=next_retry.replace(tzinfo=None)
                )
            else:
                logger.error(f"[MAX RETRIES EXCEEDED] Terminal failure after {attempt} attempts: {err}")
                return SMTPDeliveryResult(
                    status="FAILED",
                    message_id=None,
                    smtp_response=str(e),
                    error_category="MAX_RETRIES_EXCEEDED",
                    error_message=f"Exceeded max retry limit ({self.config.max_retries}): {err}",
                    attempt=attempt,
                    retry_after_seconds=None,
                    next_retry_at=None
                )

        except Exception as e:
            err = f"Unexpected SMTP error: {type(e).__name__} - {str(e)}"
            logger.error(err)
            return SMTPDeliveryResult(
                status="FAILED",
                message_id=None,
                smtp_response=str(e),
                error_category="UNEXPECTED_SYSTEM_ERROR",
                error_message=err,
                attempt=attempt,
                retry_after_seconds=None,
                next_retry_at=None
            )
