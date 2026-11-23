"""
Phase 6 Automated Test Suite: SMTP Integration, Reliable Delivery & Audit Tracking.
Tests zero-risk simulation isolation, live delivery via mocked SMTP, error classification,
exponential backoff, employee safety filtering, and comprehensive 18-column audit logging.
"""
import os
import socket
import smtplib
import datetime
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from db.database import SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog
from src.smtp_client import SMTPClient, SMTPConfig, SMTPDeliveryResult, SMTPAwaitingResponseError
from src.services import scheduling_service
from src.services.scheduling_service import process_pending_retries
from src.idempotency import generate_campaign_execution_key, is_already_executed, record_execution
from src.worker import BackgroundWorker
from api.routes.scheduler import verify_smtp_connection, trigger_scheduler_cycle


class TestPhase6DeliveryEngine(unittest.TestCase):
    """Integration and Unit Tests for Phase 6 Email Delivery and Audit Engine."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.orig_env = {
            "SMTP_HOST": os.environ.get("SMTP_HOST"),
            "SMTP_PORT": os.environ.get("SMTP_PORT"),
            "SMTP_USER": os.environ.get("SMTP_USER"),
            "SMTP_PASS": os.environ.get("SMTP_PASS"),
            "SMTP_FROM_EMAIL": os.environ.get("SMTP_FROM_EMAIL"),
            "SMTP_FROM_NAME": os.environ.get("SMTP_FROM_NAME"),
            "CONFIRM_LIVE_DELIVERY": os.environ.get("CONFIRM_LIVE_DELIVERY")
        }
        os.environ["SMTP_HOST"] = "smtp.testserver.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USER"] = "testuser@testcorp.com"
        os.environ["SMTP_PASS"] = "mock_pass_123"
        os.environ["SMTP_FROM_EMAIL"] = "noreply@testcorp.com"
        os.environ["SMTP_FROM_NAME"] = "Test Mailer"
        os.environ["CONFIRM_LIVE_DELIVERY"] = "true"

    @classmethod
    def tearDownClass(cls):
        for k, v in cls.orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        self.session = SessionLocal()
        self._cleanup()

        # Seed active test employee
        self.active_emp = Employee(
            employee_id="TEST_EMP_P6_ACT",
            full_name="Kiran Patel",
            email="kiran.patel@testcorp.com",
            company="Tech Corp",
            department="Engineering",
            designation="DevOps Lead",
            timezone="Asia/Kolkata",
            employment_status="Active"
        )
        # Seed inactive test employee
        self.inactive_emp = Employee(
            employee_id="TEST_EMP_P6_INACT",
            full_name="Vikram Seth",
            email="vikram.seth@testcorp.com",
            company="Tech Corp",
            department="Operations",
            designation="Former Associate",
            timezone="Asia/Kolkata",
            employment_status="Terminated"
        )
        self.session.add(self.active_emp)
        self.session.add(self.inactive_emp)
        self.session.commit()

        # Seed test email template
        self.template = EmailTemplate(
            template_name="Test Phase 6 Dispatch Template",
            category="Technical Training",
            subject="Notice: {{ event_name | default('System Update') }}",
            body="<p>Hello {{ full_name }},</p><p>Scheduled update for {{ department }}.</p>"
        )
        self.session.add(self.template)
        self.session.commit()

    def tearDown(self):
        self._cleanup()
        self.session.close()

    def _cleanup(self):
        try:
            self.session.rollback()
        except Exception:
            pass

        # 1. Clean test campaigns matching pattern
        camps = self.session.query(Campaign).filter(Campaign.campaign_name.like("Test P6%")).all()
        for c in camps:
            self.session.query(CampaignRecipient).filter_by(campaign_id=c.id).delete()
            self.session.query(MessageLog).filter_by(campaign_id=c.id).delete()
            self.session.delete(c)

        # 2. Clean test reminders
        reminders = self.session.query(ReminderJob).filter(ReminderJob.reminder_title.like("Test P6%")).all()
        for r in reminders:
            self.session.query(MessageLog).filter_by(reminder_id=r.id).delete()
            self.session.delete(r)

        # 3. Clean test email templates and any dependent campaigns
        tmpl = self.session.query(EmailTemplate).filter_by(template_name="Test Phase 6 Dispatch Template").first()
        if tmpl:
            dep_camps = self.session.query(Campaign).filter_by(template_id=tmpl.id).all()
            for dc in dep_camps:
                self.session.query(CampaignRecipient).filter_by(campaign_id=dc.id).delete()
                self.session.query(MessageLog).filter_by(campaign_id=dc.id).delete()
                self.session.delete(dc)
            self.session.query(MessageLog).filter_by(template_id=tmpl.id).delete()
            self.session.delete(tmpl)

        # 4. Clean test employees and their references
        for emp_code in ["TEST_EMP_P6_ACT", "TEST_EMP_P6_INACT"]:
            emp = self.session.query(Employee).filter_by(employee_id=emp_code).first()
            if emp:
                self.session.query(CampaignRecipient).filter_by(employee_id=emp.id).delete()
                self.session.query(ReminderJob).filter_by(employee_id=emp.id).delete()
                self.session.query(MessageLog).filter_by(employee_id=emp.id).delete()
                self.session.delete(emp)

        # 5. Clean logs with test emails
        self.session.query(MessageLog).filter(
            MessageLog.recipient_email.in_([
                "kiran.patel@testcorp.com",
                "vikram.seth@testcorp.com",
                "invalid-format-recipient",
                "temp.failure@testcorp.com"
            ])
        ).delete()

        self.session.commit()

    # --------------------------------------------------------------------------
    # TEST 1: Simulation Mode Isolation
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    @patch("src.smtp_client.smtplib.SMTP_SSL")
    def test_01_simulation_mode_never_connects_smtp(self, mock_ssl, mock_smtp):
        """Simulation mode must NEVER open an outbound SMTP socket or dispatch real emails."""
        campaign = Campaign(
            campaign_name="Test P6 Sim Only",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        # Process in simulation mode
        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=True
        )

        # Zero SMTP interaction
        mock_smtp.assert_not_called()
        mock_ssl.assert_not_called()

        self.assertEqual(summary["simulated"], 1)
        self.assertEqual(summary["dispatched"], 0)

        # Verify audit log recorded execution_mode=SIMULATION and status=SIMULATED_SUCCESS
        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_mode, "SIMULATION")
        self.assertEqual(log.execution_status, "SIMULATED_SUCCESS")
        self.assertIsNone(log.provider_message_id)

    # --------------------------------------------------------------------------
    # TEST 2: Credential Masking & Configuration Validation
    # --------------------------------------------------------------------------
    def test_02_smtp_config_validation_and_masking(self):
        """Config string representation must mask passwords and validate parameters correctly."""
        cfg = SMTPConfig(
            host="smtp.company.com",
            port=587,
            user="admin@company.com",
            password="SuperSecretPassword123!",
            from_email="admin@company.com"
        )
        # Ensure password is masked
        rep = repr(cfg)
        self.assertNotIn("SuperSecretPassword123!", rep)
        self.assertIn("password='***'", rep)

        # Validation success
        valid, err = cfg.validate()
        self.assertTrue(valid)
        self.assertIsNone(err)

        # Validation failure on invalid sender email
        invalid_cfg = SMTPConfig(
            host="smtp.company.com",
            port=587,
            user="admin@company.com",
            password="SecretPassword",
            from_email="invalid-sender-email"
        )
        valid2, err2 = invalid_cfg.validate()
        self.assertFalse(valid2)
        self.assertIn("Invalid sender address", err2)

    # --------------------------------------------------------------------------
    # TEST 3: Mocked Successful Live SMTP Delivery
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_03_mocked_smtp_successful_live_delivery(self, mock_smtp_cls):
        """Live delivery with valid SMTP mock must record SMTP_ACCEPTED and capture Message-ID."""
        mock_server = MagicMock()
        mock_server.noop.return_value = (250, b"2.0.0 OK")
        mock_server.send_message.return_value = {}
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Live Success",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        self.assertEqual(summary["dispatched"], 1)
        self.assertEqual(summary["simulated"], 0)

        # Inspect audit log
        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_mode, "LIVE_SMTP")
        self.assertEqual(log.execution_status, "SMTP_ACCEPTED")
        self.assertEqual(log.attempt_count, 1)
        self.assertIsNotNone(log.message_id)  # Locally generated RFC 5322 Message-ID
        self.assertIsNone(log.provider_message_id)  # Standard direct SMTP leaves provider_message_id NULL
        self.assertIn("250 Message accepted", log.smtp_response)
        self.assertIsNone(log.error_category)
        self.assertIsNone(log.next_retry_at)

    # --------------------------------------------------------------------------
    # TEST 4: Authentication Failure (Permanent Error - No Retries)
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_04_smtp_authentication_failure_permanent(self, mock_smtp_cls):
        """SMTP authentication failure must immediately set FAILED without scheduling retries."""
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Auth Fail",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        self.assertEqual(summary["dispatched"], 0)
        self.assertEqual(len(summary["errors"]), 1)

        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "FAILED")
        self.assertEqual(log.error_category, "AUTHENTICATION_ERROR")
        self.assertIsNone(log.next_retry_at)  # Must NOT schedule a retry for auth failures

    # --------------------------------------------------------------------------
    # TEST 5: Temporary Network Failure Triggers Exponential Backoff
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_05_temporary_network_failure_retry_pending(self, mock_smtp_cls):
        """Temporary socket timeout must set RETRY_PENDING and schedule next_retry_at."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = socket.timeout("The read operation timed out")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Temp Network Fail",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        self.assertEqual(summary["retry_pending"], 1)

        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "RETRY_PENDING")
        self.assertEqual(log.error_category, "TEMPORARY_NETWORK")
        self.assertEqual(log.attempt_count, 1)
        self.assertIsNotNone(log.next_retry_at)
        # Next retry should be in the future (roughly +60s from now)
        self.assertGreater(log.next_retry_at, datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

    # --------------------------------------------------------------------------
    # TEST 6: Inactive Employee Safety Filter
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_06_inactive_employee_safety_check(self, mock_smtp):
        """Inactive / terminated employees must be skipped and logged as SKIPPED_INACTIVE."""
        campaign = Campaign(
            campaign_name="Test P6 Inactive Filter",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.inactive_emp.id, recipient_email=self.inactive_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        mock_smtp.assert_not_called()
        self.assertEqual(summary["skipped_inactive"], 1)

        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.inactive_emp.id
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "SKIPPED_INACTIVE")
        self.assertIn("Employee status is 'Terminated'", log.error_message)

    # --------------------------------------------------------------------------
    # TEST 7: Duplicate Execution Prevention in Live Mode
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_07_duplicate_execution_prevention_live(self, mock_smtp_cls):
        """Repeated live execution must be blocked by idempotency service without second dispatch."""
        mock_server = MagicMock()
        mock_server.noop.return_value = (250, b"2.0.0 OK")
        mock_server.send_message.return_value = {}
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Idempotent Live",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        # Run 1: Successful live dispatch
        summary1 = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )
        self.assertEqual(summary1["dispatched"], 1)
        self.assertEqual(mock_server.send_message.call_count, 1)

        # Run 2: Repeated live evaluation of the same campaign
        campaign.status = "READY"  # Reset status artificially
        self.session.commit()

        summary2 = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )
        self.assertEqual(summary2["dispatched"], 0)
        self.assertEqual(summary2["skipped_duplicate"], 1)
        # Send message call count must remain 1
        self.assertEqual(mock_server.send_message.call_count, 1)

    # --------------------------------------------------------------------------
    # TEST 8: Full 18-Column Audit Log Completeness
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_08_audit_log_18_column_completeness(self, mock_smtp_cls):
        """All 18 audit columns in message_logs must be populated accurately."""
        mock_server = MagicMock()
        mock_server.noop.return_value = (250, b"2.0.0 OK")
        mock_server.send_message.return_value = {}
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Audit Schema Verification",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(campaign_id=campaign.id, employee_id=self.active_emp.id, recipient_email=self.active_emp.email, status="PENDING")
        self.session.add(rec)
        self.session.commit()

        scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()

        # Check 20 distinct model attributes (including separated message identifiers)
        expected_fields = [
            "id", "campaign_id", "reminder_id", "employee_id", "template_id",
            "recipient_email", "subject", "execution_key", "execution_mode",
            "execution_status", "attempt_count", "smtp_response",
            "message_id", "smtp_queue_id", "provider_message_id",
            "error_category", "error_message",
            "scheduled_at", "executed_at", "next_retry_at"
        ]
        for field in expected_fields:
            self.assertTrue(hasattr(log, field), f"Missing attribute '{field}' on MessageLog")

        self.assertEqual(log.campaign_id, campaign.id)
        self.assertEqual(log.employee_id, self.active_emp.id)
        self.assertEqual(log.template_id, self.template.id)
        self.assertEqual(log.recipient_email, self.active_emp.email)
        self.assertEqual(log.execution_mode, "LIVE_SMTP")
        self.assertEqual(log.execution_status, "SMTP_ACCEPTED")
        self.assertEqual(log.attempt_count, 1)
        self.assertIsNotNone(log.message_id)  # RFC 5322 Message-ID
        self.assertIsNone(log.provider_message_id)  # NULL in direct SMTP

    # --------------------------------------------------------------------------
    # TEST 9: API Verify SMTP Connection Endpoint
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_09_api_verify_smtp_endpoint(self, mock_smtp_cls):
        """API verify_smtp_connection tests connection and returns diagnostics without leaking pass."""
        mock_server = MagicMock()
        mock_server.noop.return_value = (250, b"2.0.0 OK")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        data = verify_smtp_connection()
        self.assertTrue(data["success"])
        self.assertIn("host", data)
        self.assertIn("port", data)
        self.assertNotIn("password", data)
        self.assertNotIn("SMTP_PASS", data)

    # --------------------------------------------------------------------------
    # TEST 10: API Trigger Safety Refusal
    # --------------------------------------------------------------------------
    def test_10_api_trigger_safety_refusal(self):
        """trigger_scheduler_cycle(simulation=False) must raise HTTP 400 without confirm_live=True."""
        with self.assertRaises(HTTPException) as ctx:
            trigger_scheduler_cycle(simulation=False, confirm_live=False, db=self.session)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Safety refusal", ctx.exception.detail)

    # --------------------------------------------------------------------------
    # TEST 11: Timeout After Message Submission Marked as DELIVERY_UNCERTAIN
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_11_timeout_after_message_submission_uncertain(self, mock_smtp_cls):
        """Timeout after message submission must mark DELIVERY_UNCERTAIN and disable retries."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = SMTPAwaitingResponseError(
            "Socket timed out while awaiting 250 OK acknowledgment after data submission"
        )
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        campaign = Campaign(
            campaign_name="Test P6 Post-Submission Timeout",
            template_id=self.template.id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),
            status="READY"
        )
        self.session.add(campaign)
        self.session.commit()

        rec = CampaignRecipient(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id,
            recipient_email=self.active_emp.email,
            status="PENDING"
        )
        self.session.add(rec)
        self.session.commit()

        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=campaign,
            simulation_mode=False
        )

        self.assertEqual(summary["dispatched"], 0)
        self.assertEqual(summary["delivery_uncertain"], 1)

        log = self.session.query(MessageLog).filter_by(
            campaign_id=campaign.id,
            employee_id=self.active_emp.id
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "DELIVERY_UNCERTAIN")
        self.assertEqual(log.error_category, "DELIVERY_UNCERTAIN")
        self.assertIsNone(log.next_retry_at)  # Must NEVER automatically retry an uncertain outcome
        self.assertIsNotNone(log.message_id)  # RFC 5322 Message-ID preserved for downstream tracing
        self.assertIsNone(log.provider_message_id)  # Kept NULL for direct SMTP

    # --------------------------------------------------------------------------
    # TEST 12: Uncertain Outcome Is Never Automatically Retried
    # --------------------------------------------------------------------------
    def test_12_uncertain_outcome_not_automatically_retried(self):
        """DELIVERY_UNCERTAIN records are skipped by process_pending_retries and idempotency guards."""
        exec_key = "test_key_uncertain_audit_999"
        log = MessageLog(
            execution_key=exec_key,
            recipient_email="kiran.patel@testcorp.com",
            subject="Test Uncertain Notice",
            execution_mode="LIVE_SMTP",
            execution_status="DELIVERY_UNCERTAIN",
            attempt_count=1,
            next_retry_at=None,
            error_category="DELIVERY_UNCERTAIN",
            error_message="Awaiting response timeout",
            scheduled_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        )
        self.session.add(log)
        self.session.commit()

        # 1. process_pending_retries must ignore DELIVERY_UNCERTAIN rows
        reprocessed = scheduling_service.process_pending_retries(db=self.session)
        self.assertEqual(reprocessed, 0)

        # 2. Idempotency guard must treat DELIVERY_UNCERTAIN as executed (blocking repeated automatic sends)
        self.assertTrue(is_already_executed(self.session, exec_key))

        # Cleanup
        self.session.delete(log)
        self.session.commit()

    # --------------------------------------------------------------------------
    # TEST 13: Live Mode Without Confirmation Fails Closed
    # --------------------------------------------------------------------------
    def test_13_live_mode_without_confirmation_fails_closed(self):
        """Unconfirmed live execution must fail closed without dispatching any emails."""
        # Unset env confirmation temporarily
        old_val = os.environ.pop("CONFIRM_LIVE_DELIVERY", None)
        try:
            # A. BackgroundWorker direct instantiation without confirmation must raise ValueError
            with self.assertRaises(ValueError) as ctx:
                BackgroundWorker(simulation_mode=False)
            self.assertIn("Safety Refusal", str(ctx.exception))

            # B. scheduling_service.run_pending_jobs must return refusal error and 0 processed
            res = scheduling_service.run_pending_jobs(db=self.session, simulation_mode=False)
            self.assertIn("Safety refusal", res["errors"][0])
            self.assertEqual(res["messages_accepted"], 0)
            self.assertEqual(res["campaigns_processed"], 0)

            # C. CLI invocation: python worker.py --live (without --confirm-live) must exit with code 1
            cmd = [sys.executable, "worker.py", "--live"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            output = proc.stdout + proc.stderr
            self.assertIn("SAFETY REFUSAL", output)
        finally:
            if old_val is not None:
                os.environ["CONFIRM_LIVE_DELIVERY"] = old_val

    # --------------------------------------------------------------------------
    # TEST 14: Maximum Retry Limit Enforced Terminal Failure
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_14_max_retry_limit_enforced_terminal_failure(self, mock_smtp_cls):
        """When attempt reaches max_retries, result transitions to terminal FAILED status."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = socket.timeout("Pre-submission connection timed out")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        client = SMTPClient()
        # Test final attempt (attempt == max_retries == 3)
        res = client.send_live_email(
            to_email="kiran.patel@testcorp.com",
            subject="Test Terminal Retry",
            html_content="<p>Body</p>",
            attempt=client.config.max_retries
        )

        self.assertEqual(res.status, "FAILED")
        self.assertEqual(res.error_category, "MAX_RETRIES_EXCEEDED")
        self.assertIsNone(res.next_retry_at)
        self.assertIsNone(res.retry_after_seconds)

    # --------------------------------------------------------------------------
    # TEST 15: Exponential Backoff Is Strictly Bounded
    # --------------------------------------------------------------------------
    @patch("src.smtp_client.smtplib.SMTP")
    def test_15_exponential_backoff_is_bounded(self, mock_smtp_cls):
        """Exponential backoff delay must be capped at max_backoff_seconds."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = socket.timeout("Pre-submission timeout")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        cfg = SMTPConfig(
            host="smtp.testserver.com",
            user="testuser@testcorp.com",
            password="mockpassword123",
            from_email="noreply@testcorp.com",
            backoff_base_seconds=60,
            max_backoff_seconds=180,  # Cap at 180s (3 minutes)
            max_retries=5
        )
        client = SMTPClient(config=cfg)

        # Attempt 1: 60 * 2^0 = 60s
        res1 = client.send_live_email("kiran.patel@testcorp.com", "Sub", "<p>Body</p>", attempt=1)
        self.assertEqual(res1.retry_after_seconds, 60)

        # Attempt 2: 60 * 2^1 = 120s
        res2 = client.send_live_email("kiran.patel@testcorp.com", "Sub", "<p>Body</p>", attempt=2)
        self.assertEqual(res2.retry_after_seconds, 120)

        # Attempt 3: 60 * 2^2 = 240s -> Capped at 180s!
        res3 = client.send_live_email("kiran.patel@testcorp.com", "Sub", "<p>Body</p>", attempt=3)
        self.assertEqual(res3.retry_after_seconds, 180)

    # --------------------------------------------------------------------------
    # TEST 16: Manual Recovery Option A - SQLite Re-Queueing & Successful Reprocessing
    # --------------------------------------------------------------------------
    def test_16_manual_recovery_option_a_reprocessing_end_to_end(self):
        """
        End-to-end verification of documented Option A manual recovery procedure:
        1. Create a DELIVERY_UNCERTAIN record.
        2. Confirm it is blocked from automatic retry.
        3. Apply Option A SQL: UPDATE message_logs SET execution_status = 'RETRY_PENDING', next_retry_at = CURRENT_TIMESTAMP WHERE id = ...
        4. Confirm worker reprocesses the record.
        5. Confirm unique execution key does not block legitimate re-attempt.
        6. Confirm existing audit record is updated in-place with attempt count incremented.
        7. Ensure no duplicate MessageLog record is created.
        """
        from sqlalchemy import text
        exec_key = "test_opt_a_e2e_recovery_key_123"

        # 1. Create DELIVERY_UNCERTAIN record
        uncertain_log = MessageLog(
            execution_key=exec_key,
            recipient_email=self.active_emp.email,
            subject="Urgent Security Advisory",
            execution_mode="LIVE_SMTP",
            execution_status="DELIVERY_UNCERTAIN",
            attempt_count=1,
            message_id="<orig-uncertain-uuid@testcorp.com>",
            smtp_response="UNKNOWN_TIMEOUT_POST_SUBMISSION",
            error_category="DELIVERY_UNCERTAIN",
            error_message="Socket timeout awaiting 250 OK after payload transmission",
            next_retry_at=None,
            executed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        self.session.add(uncertain_log)
        self.session.commit()
        record_id = uncertain_log.id

        # 2. Confirm automatic retry loop skips it
        mock_client = MagicMock()
        reprocessed = process_pending_retries(self.session, smtp_client=mock_client)
        self.assertEqual(reprocessed, 0)
        self.assertTrue(is_already_executed(self.session, exec_key))

        # 3. Apply documented Option A SQL
        self.session.execute(
            text(f"UPDATE message_logs SET execution_status = 'RETRY_PENDING', next_retry_at = CURRENT_TIMESTAMP WHERE id = {record_id}")
        )
        self.session.commit()

        # 4. Confirm idempotency guard does not block the legitimate retry
        self.assertFalse(is_already_executed(self.session, exec_key))

        # 5. Configure mock SMTP client to accept the re-attempt
        mock_client.send_live_email.return_value = SMTPDeliveryResult(
            status="SMTP_ACCEPTED",
            message_id="<retry-accepted-uuid@testcorp.com>",
            smtp_response="250 2.0.0 OK: queued as 4S9XYZ123",
            error_category=None,
            error_message=None,
            attempt=2,
            retry_after_seconds=None,
            next_retry_at=None,
            smtp_queue_id="4S9XYZ123",
            provider_message_id=None
        )

        # 6. Worker reprocesses the record
        reprocessed = process_pending_retries(self.session, smtp_client=mock_client)
        self.assertEqual(reprocessed, 1)

        # 7. Verify existing record was updated in-place with new attempt count and identifiers
        reloaded = self.session.query(MessageLog).filter_by(execution_key=exec_key).first()
        self.assertEqual(reloaded.id, record_id)
        self.assertEqual(reloaded.execution_status, "SMTP_ACCEPTED")
        self.assertEqual(reloaded.attempt_count, 2)
        self.assertEqual(reloaded.message_id, "<retry-accepted-uuid@testcorp.com>")
        self.assertEqual(reloaded.smtp_queue_id, "4S9XYZ123")
        self.assertIsNone(reloaded.provider_message_id)

        # 8. Ensure no duplicate MessageLog record was created
        total_for_key = self.session.query(MessageLog).filter_by(execution_key=exec_key).count()
        self.assertEqual(total_for_key, 1)

    # --------------------------------------------------------------------------
    # TEST 17: Manual Recovery Option B - Finalize Independently Confirmed Delivery
    # --------------------------------------------------------------------------
    def test_17_manual_recovery_option_b_confirmation_end_to_end(self):
        """
        End-to-end verification of documented Option B manual recovery procedure:
        1. Create a DELIVERY_UNCERTAIN record.
        2. Apply Option B SQL: UPDATE message_logs SET execution_status = 'DELIVERY_CONFIRMED' WHERE id = ...
        3. Confirm record transitions to DELIVERY_CONFIRMED.
        4. Confirm idempotency guard treats it as permanently executed.
        5. Confirm process_pending_retries never touches it.
        6. Confirm duplicate insertion via record_execution is safely rejected.
        """
        from sqlalchemy import text
        exec_key = "test_opt_b_e2e_confirmation_key_456"

        # 1. Create DELIVERY_UNCERTAIN record
        uncertain_log = MessageLog(
            execution_key=exec_key,
            recipient_email=self.active_emp.email,
            subject="All-Hands Meeting",
            execution_mode="LIVE_SMTP",
            execution_status="DELIVERY_UNCERTAIN",
            attempt_count=1,
            message_id="<confirmed-later-uuid@testcorp.com>",
            smtp_response="UNKNOWN_TIMEOUT_POST_SUBMISSION",
            next_retry_at=None,
            executed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        self.session.add(uncertain_log)
        self.session.commit()
        record_id = uncertain_log.id

        # 2. Apply documented Option B SQL
        self.session.execute(
            text(f"UPDATE message_logs SET execution_status = 'DELIVERY_CONFIRMED' WHERE id = {record_id}")
        )
        self.session.commit()

        # 3. Confirm status is DELIVERY_CONFIRMED
        reloaded = self.session.query(MessageLog).filter_by(id=record_id).first()
        self.assertEqual(reloaded.execution_status, "DELIVERY_CONFIRMED")

        # 4. Confirm idempotency guard blocks duplicate executions
        self.assertTrue(is_already_executed(self.session, exec_key))

        # 5. Confirm process_pending_retries does not process it
        mock_client = MagicMock()
        reprocessed = process_pending_retries(self.session, smtp_client=mock_client)
        self.assertEqual(reprocessed, 0)
        mock_client.send_live_email.assert_not_called()

        # 6. Confirm duplicate record_execution insert is safely blocked
        recorded, err = record_execution(
            session=self.session,
            execution_key=exec_key,
            recipient_email=self.active_emp.email,
            subject="All-Hands Meeting",
            status="SIMULATED_SUCCESS"
        )
        self.assertFalse(recorded)
        self.assertIn("Duplicate execution blocked", err)

        # 7. Confirm strictly 1 record exists
        total_records = self.session.query(MessageLog).filter_by(execution_key=exec_key).count()
        self.assertEqual(total_records, 1)


if __name__ == "__main__":
    unittest.main()
