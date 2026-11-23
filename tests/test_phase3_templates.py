"""
Comprehensive Phase 3 Test Suite: Email Template Management & Jinja2 Personalization.
Validates CRUD, Duplication, Variable Substitution, Multi-Employee Personalization,
Syntax Checking, Undefined Variable Trapping, Plain-Text Fallback, and Sandboxing.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, init_db, engine
from db.models import EmailTemplate, Employee
from api.schemas import EmailTemplateCreate, EmailTemplateUpdate
from src.services import template_service, employee_service


class TestPhase3TemplateManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session = SessionLocal()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_01_template_creation(self):
        """1. Test creating an email template with valid syntax."""
        tmpl_in = EmailTemplateCreate(
            template_name="Test Onboarding Welcome",
            category="Employee Onboarding",
            subject="Welcome to {{ company }}, {{ name }}!",
            body="<p>Dear {{ name }}, welcome to your new role as {{ designation }}.</p>"
        )
        tmpl = template_service.create_template(self.session, tmpl_in)
        self.assertIsNotNone(tmpl.id)
        self.assertEqual(tmpl.template_name, "Test Onboarding Welcome")
        self.assertEqual(tmpl.category, "Employee Onboarding")

        # Cleanup
        template_service.delete_template(self.session, tmpl.id)

    def test_02_template_retrieval(self):
        """2. Test retrieving an email template by ID."""
        tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Retrieval Test Template",
            category="Meeting Invitation",
            subject="Meeting: {{ event_name }}",
            body="<div>Join link: {{ meeting_link }}</div>"
        ))
        fetched = template_service.get_template(self.session, tmpl.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.template_name, "Retrieval Test Template")

        # Cleanup
        template_service.delete_template(self.session, tmpl.id)

    def test_03_template_updating(self):
        """3. Test updating subject, body, and category of a template."""
        tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Original Template Name",
            category="Technical Training",
            subject="Initial Subject",
            body="<p>Initial body for {{ name }}</p>"
        ))
        updated = template_service.update_template(
            self.session,
            tmpl.id,
            EmailTemplateUpdate(
                subject="Updated Subject for {{ name }}",
                category="Training Reminder"
            )
        )
        self.assertEqual(updated.subject, "Updated Subject for {{ name }}")
        self.assertEqual(updated.category, "Training Reminder")

        # Cleanup
        template_service.delete_template(self.session, tmpl.id)

    def test_04_template_deletion(self):
        """4. Test deleting a template."""
        tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="To Be Deleted",
            category="Other",
            subject="Delete Me",
            body="<p>Temporary</p>"
        ))
        t_id = tmpl.id
        deleted = template_service.delete_template(self.session, t_id)
        self.assertTrue(deleted)
        self.assertIsNone(template_service.get_template(self.session, t_id))

    def test_05_template_duplication(self):
        """5. Test duplicating/cloning an existing template with copy suffix."""
        original = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Performance Review Q4",
            category="Performance Review",
            subject="Self-Evaluation Deadline for {{ name }}",
            body="<p>Please submit by {{ event_date }}.</p>"
        ))
        clone = template_service.duplicate_template(self.session, original.id)
        self.assertIsNotNone(clone)
        self.assertEqual(clone.template_name, "Performance Review Q4 (Copy)")
        self.assertEqual(clone.subject, original.subject)
        self.assertEqual(clone.body, original.body)

        # Cleanup
        template_service.delete_template(self.session, original.id)
        template_service.delete_template(self.session, clone.id)

    def test_06_jinja2_variable_substitution(self):
        """6. Test dynamic substitution of Employee, Event, and Sender variables."""
        subject_tmpl = "Urgent: {{ event_name }} for {{ name }}"
        body_tmpl = (
            "<p>Hello {{ name }} ({{ employee_id }}),</p>"
            "<p>Your session '{{ event_name }}' is on {{ event_date }} at {{ event_time }}.</p>"
            "<p>Location: {{ event_location }}. Link: <a href='{{ meeting_link }}'>Join Now</a></p>"
            "<p>Regards,<br>{{ sender_name }}, {{ sender_department }} - {{ company_name }}</p>"
        )
        context = {
            "name": "Priya Patel",
            "employee_id": "EMP-404",
            "event_name": "Kubernetes Architecture Briefing",
            "event_date": "2026-12-01",
            "event_time": "14:00 IST",
            "event_location": "Virtual Room 3",
            "meeting_link": "https://meet.google.com/xyz-uvw",
            "sender_name": "DevOps Lead",
            "sender_department": "Cloud Platforms",
            "company_name": "Nexus Tech"
        }
        res = template_service.render_template_preview(
            db=self.session,
            subject_tmpl=subject_tmpl,
            body_tmpl=body_tmpl,
            event_context=context,
            sender_context=context
        )
        self.assertTrue(res.is_valid)
        self.assertIn("Urgent: Kubernetes Architecture Briefing for Priya Patel", res.rendered_subject)
        self.assertIn("Priya Patel (EMP-404)", res.rendered_html)
        self.assertIn("Join Now", res.rendered_html)

    def test_07_multiple_employee_personalization(self):
        """7. Test personalizing the exact same template for distinct employees."""
        emp1 = Employee(
            employee_id="MULTI_01",
            full_name="Alice Smith",
            email="alice@company.com",
            department="Finance",
            designation="Accountant"
        )
        emp2 = Employee(
            employee_id="MULTI_02",
            full_name="Bob Jones",
            email="bob@company.com",
            department="Engineering",
            designation="Developer"
        )
        self.session.add_all([emp1, emp2])
        self.session.commit()

        template_text = "Hi {{ name }}, your department is {{ department }} and designation is {{ designation }}."

        res1 = template_service.render_template_preview(self.session, "Subject", template_text, employee_id=emp1.id)
        res2 = template_service.render_template_preview(self.session, "Subject", template_text, employee_id=emp2.id)

        self.assertIn("Alice Smith", res1.rendered_html)
        self.assertIn("Accountant", res1.rendered_html)

        self.assertIn("Bob Jones", res2.rendered_html)
        self.assertIn("Developer", res2.rendered_html)

        # Cleanup
        self.session.delete(emp1)
        self.session.delete(emp2)
        self.session.commit()

    def test_08_undefined_variable_detection(self):
        """8. Test detection of undeclared/missing required variables."""
        subject_tmpl = "Notice for {{ name }}"
        # Injects undefined non-standard variables: {{ unassigned_custom_code }} and {{ missing_date }}
        body_tmpl = "<p>Hello {{ name }}, code: {{ unassigned_custom_code }} on {{ missing_date }}.</p>"

        # Use an empty custom context that does not supply unassigned_custom_code
        res = template_service.render_template_preview(
            db=self.session,
            subject_tmpl=subject_tmpl,
            body_tmpl=body_tmpl
        )
        self.assertFalse(res.is_valid)
        self.assertIn("missing_date", res.missing_variables)
        self.assertIn("unassigned_custom_code", res.missing_variables)
        self.assertIn("missing required variable", res.validation_error.lower())

    def test_09_invalid_template_syntax(self):
        """9. Test Jinja2 syntax error detection (e.g. unclosed tags)."""
        malformed_subject = "Hello {{ name %}"  # Mismatched bracket
        body = "<p>Valid body</p>"

        is_valid, err_msg, _ = template_service.validate_template_syntax(malformed_subject, body)
        self.assertFalse(is_valid)
        self.assertIn("Syntax Error", err_msg)

    def test_10_html_rendering_and_autoescaping(self):
        """10. Test that HTML formatting works and untrusted user input is escaped."""
        subject = "Security Test"
        body = "<p>Hello <b>{{ name }}</b>, alert: {{ event_name }}</p>"
        # Attempt XSS injection inside event_name
        malicious_context = {
            "name": "Jane",
            "event_name": "<script>alert('xss')</script>"
        }
        res = template_service.render_template_preview(
            self.session, subject, body, event_context=malicious_context
        )
        self.assertTrue(res.is_valid)
        # Template markup <b> is preserved
        self.assertIn("<b>Jane</b>", res.rendered_html)
        # Untrusted variable script tag is safely escaped by SandboxedEnvironment
        self.assertNotIn("<script>", res.rendered_html)
        self.assertIn("&lt;script&gt;", res.rendered_html)

    def test_11_plain_text_fallback_generation(self):
        """11. Test conversion of rich HTML to clean plain-text fallback."""
        html_input = (
            "<h2>Meeting Notice</h2>\n"
            "<p>Hello <strong>Aarav</strong>,</p>\n"
            "<p>Join the conference at <a href='https://meet.google.com/abc'>Google Meet</a>.</p>\n"
            "<hr>\n"
            "<p>Thanks &amp; Regards,<br>Operations</p>"
        )
        plain = template_service.convert_html_to_plain_text(html_input)
        self.assertNotIn("<h2>", plain)
        self.assertNotIn("<strong>", plain)
        self.assertIn("Google Meet (https://meet.google.com/abc)", plain)
        self.assertIn("Thanks & Regards", plain)

    def test_12_database_persistence(self):
        """12. Test database persistence across engine/session disposal."""
        tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Persisted Template",
            category="General Announcement",
            subject="General Announcement Subject",
            body="<div>Body content</div>"
        ))
        t_id = tmpl.id
        self.session.close()
        engine.dispose()

        # Reopen fresh session
        fresh = SessionLocal()
        persisted = template_service.get_template(fresh, t_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.template_name, "Persisted Template")

        # Cleanup
        template_service.delete_template(fresh, t_id)
        fresh.close()

    def test_13_security_sandboxed_environment(self):
        """13. Test that Jinja2 SandboxedEnvironment blocks dangerous Python introspection."""
        subject = "Probe"
        # Attempt sandbox escape accessing Python class hierarchy
        dangerous_body = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
        res = template_service.render_template_preview(self.session, subject, dangerous_body)
        self.assertFalse(res.is_valid)
        self.assertTrue(
            "access to attribute '__class__' of 'str' object is unsafe" in (res.validation_error or "").lower()
            or "undefined" in (res.validation_error or "").lower()
            or "syntax" in (res.validation_error or "").lower()
        )


if __name__ == "__main__":
    unittest.main()
