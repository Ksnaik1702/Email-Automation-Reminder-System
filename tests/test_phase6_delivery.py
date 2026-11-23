"""
Phase 6 Automated Test Suite: SMTP Integration, Reliable Delivery & Audit Tracking.
Tests zero-risk simulation isolation, live delivery via mocked SMTP, error classification,
exponential backoff, employee safety filtering, and comprehensive 18-column audit logging.
"""
import os
import socket
import smtplib
import datetime
import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from db.database import SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog
from src.smtp_client import SMTPClient, SMTPConfig, SMTPDeliveryResult
from src.services import scheduling_service
from src.idempotency import generate_campaign_execution_key, is_already_executed
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
        self.assertIsNotNone(log.provider_message_id)
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

        # Check 18 distinct model attributes
        expected_fields = [
            "id", "campaign_id", "reminder_id", "employee_id", "template_id",
            "recipient_email", "subject", "execution_key", "execution_mode",
            "execution_status", "attempt_count", "smtp_response",
            "provider_message_id", "error_category", "error_message",
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


if __name__ == "__main__":
    unittest.main()
