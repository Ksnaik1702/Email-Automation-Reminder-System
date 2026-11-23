"""
Automated Unit Tests for Email Automation & Reminder System.
Run with: python -m unittest tests/test_system.py
"""
import unittest
from pathlib import Path
from src.data_loader import validate_email, get_merged_reminder_jobs
from src.templating import simple_substitute, render_email_content
from src.mailer import EmailSender
from src.renderer import render_email
from db.database import get_connection, init_db

class TestEmailAutomationSystem(unittest.TestCase):

    def test_email_validation(self):
        """Tests that regex catches valid and malformed email addresses."""
        self.assertTrue(validate_email("aarav.sharma@example.com"))
        self.assertTrue(validate_email("user123@subdomain.company.org"))
        self.assertFalse(validate_email("invalid-email-at-example.com"))
        self.assertFalse(validate_email("@missinguser.com"))
        self.assertFalse(validate_email(""))

    def test_data_loader_merge(self):
        """Verifies contacts.csv and reminders.csv merge correctly."""
        jobs = get_merged_reminder_jobs()
        self.assertGreater(len(jobs), 0)
        first_job = jobs[0]
        self.assertIn("contact_id", first_job)
        self.assertIn("email", first_job)
        self.assertIn("title", first_job)

    def test_templating_substitution(self):
        """Verifies template variable replacement with custom context."""
        template_text = "Hello {{ name }}, invoice for ₹{{ amount_due }} is due on {{ due_date }}."
        context = {"name": "Priya", "amount_due": "45000", "due_date": "2026-11-25"}
        result = simple_substitute(template_text, context)
        self.assertEqual(result, "Hello Priya, invoice for ₹45000 is due on 2026-11-25.")

    def test_dry_run_simulation(self):
        """Verifies mailer runs safely in simulation mode without sending network packets."""
        sender = EmailSender(dry_run=True)
        job = {"reminder_id": "TEST_R101", "name": "Test User"}
        result = sender.send_email(
            to_email="test.user@example.com",
            subject="Test Subject",
            html_content="<p>Test Body</p>",
            job_context=job
        )
        self.assertEqual(result["status"], "SIMULATED_SUCCESS")
        self.assertIsNotNone(result["preview_path"])
        self.assertTrue(Path(result["preview_path"]).exists())

    def test_database_tables(self):
        """Verifies that SQLite schema creates all required normalized tables."""
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        conn.close()

        expected_tables = [
            "employees", "email_templates", "campaigns",
            "campaign_recipients", "reminder_jobs", "message_logs"
        ]
        for table in expected_tables:
            self.assertIn(table, tables, f"Expected table '{table}' was not found in database.")

    def test_markdown_renderer(self):
        """Tests markdown rendering and automatic unsubscribe slot inclusion."""
        subject, html = render_email(
            subject_tmpl="Update for {{ name }}",
            body_md_tmpl="Hello **{{ name }}**, please review your *schedule*.",
            context={"name": "Vikram"}
        )
        self.assertIn("Vikram", subject)
        self.assertIn("<strong>Vikram</strong>", html)
        self.assertIn("STOP", html)

if __name__ == "__main__":
    unittest.main()
