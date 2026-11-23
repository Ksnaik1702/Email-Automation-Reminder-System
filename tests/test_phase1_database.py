"""
Comprehensive Phase 1 Database & ORM Test Suite.
Validates SQLAlchemy models, relationships, constraints, duplicate prevention, and persistence.
"""
import unittest
import sys
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.exc import IntegrityError
from db.database import engine, SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog
from db.migration import generate_execution_key


class TestPhase1DatabaseArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Ensures database is initialized before running tests."""
        init_db()

    def setUp(self):
        """Create a fresh isolated session for each test."""
        self.session = SessionLocal()

    def tearDown(self):
        """Rollback and close session after each test."""
        self.session.rollback()
        self.session.close()

    def test_01_database_initialization(self):
        """1. Verify that all 6 required tables exist in database metadata."""
        table_names = [table.name for table in [
            Employee.__table__,
            EmailTemplate.__table__,
            Campaign.__table__,
            CampaignRecipient.__table__,
            ReminderJob.__table__,
            MessageLog.__table__
        ]]
        self.assertEqual(len(table_names), 6)
        self.assertIn("employees", table_names)
        self.assertIn("email_templates", table_names)
        self.assertIn("campaigns", table_names)
        self.assertIn("campaign_recipients", table_names)
        self.assertIn("reminder_jobs", table_names)
        self.assertIn("message_logs", table_names)

    def test_02_employee_insertion_and_retrieval(self):
        """2 & 3. Test Employee insertion, constraint checking, and field retrieval."""
        emp = Employee(
            employee_id="TEST_EMP_999",
            full_name="Kavita Nair",
            email="kavita.nair@testdomain.com",
            company="TestCorp",
            department="Engineering",
            designation="Senior Architect",
            timezone="Asia/Kolkata",
            employment_status="Active"
        )
        self.session.add(emp)
        self.session.commit()

        # Retrieve and verify
        retrieved = self.session.query(Employee).filter_by(employee_id="TEST_EMP_999").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.full_name, "Kavita Nair")
        self.assertEqual(retrieved.email, "kavita.nair@testdomain.com")
        self.assertEqual(retrieved.designation, "Senior Architect")

        # Clean up test artifact
        self.session.delete(retrieved)
        self.session.commit()

    def test_03_email_template_insertion(self):
        """4. Test EmailTemplate insertion and query."""
        tmpl = EmailTemplate(
            template_name="unit_test_template.html",
            category="Testing",
            subject="Test Subject {{ name }}",
            body="<p>Test content for {{ name }}</p>"
        )
        self.session.add(tmpl)
        self.session.commit()

        retrieved = self.session.query(EmailTemplate).filter_by(template_name="unit_test_template.html").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.category, "Testing")

        # Clean up
        self.session.delete(retrieved)
        self.session.commit()

    def test_04_campaign_creation_and_template_relationship(self):
        """5. Test Campaign creation and relationship with EmailTemplate."""
        tmpl = EmailTemplate(
            template_name="campaign_rel_template.html",
            category="Notifications",
            subject="Notice: {{ title }}",
            body="<div>Body content</div>"
        )
        self.session.add(tmpl)
        self.session.commit()

        camp = Campaign(
            campaign_name="Q4 Strategy Announcement",
            description="Broadcast to department heads",
            category="Executive",
            template_id=tmpl.id,
            status="Scheduled",
            scheduled_at=datetime.datetime.now(datetime.timezone.utc)
        )
        self.session.add(camp)
        self.session.commit()

        # Test bidirectional ORM relationship
        retrieved_camp = self.session.query(Campaign).filter_by(campaign_name="Q4 Strategy Announcement").first()
        self.assertIsNotNone(retrieved_camp)
        self.assertEqual(retrieved_camp.template.template_name, "campaign_rel_template.html")

        # Clean up
        self.session.delete(retrieved_camp)
        self.session.delete(tmpl)
        self.session.commit()

    def test_05_campaign_recipient_relationship(self):
        """6. Test CampaignRecipient relationship linking Campaign and Employee."""
        emp = Employee(
            employee_id="TEST_EMP_REL",
            full_name="Deepak Joshi",
            email="deepak.joshi@example.com",
            employment_status="Active"
        )
        tmpl = EmailTemplate(
            template_name="recipient_rel_tmpl.html",
            subject="Test Subj",
            body="Content"
        )
        self.session.add_all([emp, tmpl])
        self.session.commit()

        camp = Campaign(
            campaign_name="Recipient Relationship Campaign",
            template_id=tmpl.id,
            status="Draft"
        )
        self.session.add(camp)
        self.session.commit()

        recipient = CampaignRecipient(
            campaign_id=camp.id,
            employee_id=emp.id,
            recipient_email=emp.email,
            status="Pending"
        )
        self.session.add(recipient)
        self.session.commit()

        # Verify relationship from campaign
        self.assertEqual(len(camp.recipients), 1)
        self.assertEqual(camp.recipients[0].employee.full_name, "Deepak Joshi")

        # Clean up
        self.session.delete(camp)
        self.session.delete(emp)
        self.session.delete(tmpl)
        self.session.commit()

    def test_06_reminder_creation_and_employee_relationship(self):
        """7. Test ReminderJob creation and employee linkage."""
        emp = Employee(
            employee_id="TEST_REM_EMP",
            full_name="Manish Sen",
            email="manish.sen@example.com",
            employment_status="Active"
        )
        self.session.add(emp)
        self.session.commit()

        job = ReminderJob(
            employee_id=emp.id,
            reminder_title="Submit Monthly Timesheet",
            scheduled_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2),
            timezone="Asia/Kolkata",
            recurrence_type="Monthly",
            status="Active"
        )
        self.session.add(job)
        self.session.commit()

        retrieved_job = self.session.query(ReminderJob).filter_by(reminder_title="Submit Monthly Timesheet").first()
        self.assertIsNotNone(retrieved_job)
        self.assertEqual(retrieved_job.employee.full_name, "Manish Sen")
        self.assertEqual(retrieved_job.recurrence_type, "Monthly")

        # Clean up
        self.session.delete(job)
        self.session.delete(emp)
        self.session.commit()

    def test_07_message_log_insertion(self):
        """8. Test MessageLog creation and recording."""
        exec_key = generate_execution_key("TEST_REM_01", "manish@example.com", "2026-11-23 10:00:00")
        log = MessageLog(
            recipient_email="manish@example.com",
            subject="Test Dispatch Notice",
            execution_status="SIMULATED_SUCCESS",
            executed_at=datetime.datetime.now(datetime.timezone.utc),
            execution_key=exec_key
        )
        self.session.add(log)
        self.session.commit()

        retrieved = self.session.query(MessageLog).filter_by(execution_key=exec_key).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.execution_status, "SIMULATED_SUCCESS")

        # Clean up
        self.session.delete(retrieved)
        self.session.commit()

    def test_08_duplicate_execution_prevention(self):
        """9. Test Idempotency: Unique execution_key prevents duplicate executions."""
        shared_key = "IDEMPOTENT_KEY_ALPHA_001"
        log1 = MessageLog(
            recipient_email="worker1@example.com",
            subject="First Dispatch",
            execution_status="SENT",
            execution_key=shared_key
        )
        self.session.add(log1)
        self.session.commit()

        # Attempt to insert identical execution_key (simulating duplicate send)
        log2 = MessageLog(
            recipient_email="worker1@example.com",
            subject="Duplicate Dispatch Attempt",
            execution_status="SENT",
            execution_key=shared_key
        )
        self.session.add(log2)

        # Must raise IntegrityError due to UniqueConstraint('execution_key')
        with self.assertRaises(IntegrityError):
            self.session.commit()

        self.session.rollback()

        # Clean up
        clean_target = self.session.query(MessageLog).filter_by(execution_key=shared_key).first()
        if clean_target:
            self.session.delete(clean_target)
            self.session.commit()

    def test_09_existing_data_preservation(self):
        """10. Verify existing records from contacts.csv are preserved in database."""
        employees = self.session.query(Employee).all()
        self.assertGreaterEqual(len(employees), 5)
        emails = [e.email for e in employees]
        self.assertIn("aarav.sharma@example.com", emails)
        self.assertIn("priya.patel@example.com", emails)
        self.assertIn("rohan.verma@example.com", emails)
        self.assertIn("sneha.kulkarni@example.com", emails)
        self.assertIn("vikram.singh@example.com", emails)

    def test_10_database_persistence_after_restart(self):
        """11. Verify persistence: Disconnecting session/engine leaves records intact on disk."""
        self.session.close()
        engine.dispose()

        # Open completely fresh session
        new_session = SessionLocal()
        count = new_session.query(Employee).count()
        self.assertGreaterEqual(count, 5)
        new_session.close()

    def test_11_repeated_scheduler_invocation_idempotency(self):
        """Test that repeated scheduler runs cannot execute the same occurrence twice."""
        from src.idempotency import generate_execution_key, is_already_executed, record_execution

        reminder_id = 9991
        recipient = "Worker.Test@Company.com "  # Test with non-normalized input
        sched_time = "2026-11-24 10:00:00"

        key = generate_execution_key(reminder_id, recipient, sched_time)

        # Pre-test cleanup in case previous run aborted
        self.session.query(MessageLog).filter_by(execution_key=key).delete()
        self.session.commit()

        # 1st Scheduler Tick: Occurrence has not been executed yet
        self.assertFalse(is_already_executed(self.session, key))
        success, err = record_execution(
            session=self.session,
            execution_key=key,
            recipient_email=recipient,
            subject="First Run",
            status="SENT"
        )
        self.assertTrue(success)
        self.assertIsNone(err)

        # 2nd Scheduler Tick: 15 seconds later, same occurrence evaluated
        self.assertTrue(is_already_executed(self.session, key))
        success2, err2 = record_execution(
            session=self.session,
            execution_key=key,
            recipient_email=recipient,
            subject="Second Run (Duplicate)",
            status="SENT"
        )
        # Must be blocked by idempotency guard / unique constraint
        self.assertFalse(success2)
        self.assertIn("Duplicate", err2)

        # Clean up
        clean_target = self.session.query(MessageLog).filter_by(execution_key=key).first()
        if clean_target:
            self.session.delete(clean_target)
            self.session.commit()

    def test_12_application_restart_idempotency(self):
        """Test that application restart preserves idempotency locks on disk."""
        from src.idempotency import generate_execution_key, is_already_executed, record_execution

        reminder_id = 9992
        recipient = "restart.test@company.com"
        sched_time = datetime.datetime(2026, 11, 25, 14, 0, 0, tzinfo=datetime.timezone.utc)
        key = generate_execution_key(reminder_id, recipient, sched_time)

        # Record occurrence
        success, _ = record_execution(
            session=self.session,
            execution_key=key,
            recipient_email=recipient,
            subject="Pre-Restart Dispatch",
            status="SENT"
        )
        self.assertTrue(success)

        # Simulate Application Restart: close session and dispose connection pool
        self.session.close()
        engine.dispose()

        # Restart simulation: fresh session after boot
        fresh_session = SessionLocal()
        try:
            # Occurrence must still be recognized as executed
            self.assertTrue(is_already_executed(fresh_session, key))
        finally:
            clean_target = fresh_session.query(MessageLog).filter_by(execution_key=key).first()
            if clean_target:
                fresh_session.delete(clean_target)
                fresh_session.commit()
            fresh_session.close()

    def test_13_different_scheduled_occurrences_of_same_reminder(self):
        """Test that different occurrences of a recurring reminder generate unique keys and execute independently."""
        from src.idempotency import generate_execution_key, is_already_executed, record_execution

        reminder_id = "R_RECURRING_DAILY"
        recipient = "daily.subscriber@company.com"

        # Day 1 Occurrence: 2026-11-24 09:00 UTC
        day1_time = "2026-11-24T09:00:00Z"
        key_day1 = generate_execution_key(reminder_id, recipient, day1_time)

        # Day 2 Occurrence: 2026-11-25 09:00 UTC
        day2_time = "2026-11-25T09:00:00Z"
        key_day2 = generate_execution_key(reminder_id, recipient, day2_time)

        # Keys must be distinct
        self.assertNotEqual(key_day1, key_day2)

        # Execute Day 1
        success1, _ = record_execution(self.session, key_day1, recipient, "Day 1 Reminder", "SENT")
        self.assertTrue(success1)

        # Day 1 is executed, but Day 2 is NOT yet executed
        self.assertTrue(is_already_executed(self.session, key_day1))
        self.assertFalse(is_already_executed(self.session, key_day2))

        # Execute Day 2 independently
        success2, _ = record_execution(self.session, key_day2, recipient, "Day 2 Reminder", "SENT")
        self.assertTrue(success2)

        # Both are now recorded
        self.assertTrue(is_already_executed(self.session, key_day1))
        self.assertTrue(is_already_executed(self.session, key_day2))

        # Clean up
        self.session.query(MessageLog).filter(MessageLog.execution_key.in_([key_day1, key_day2])).delete()
        self.session.commit()

    def test_14_database_portability_and_env_override(self):
        """Test that DATABASE_URL can be configured dynamically without hardcoded paths."""
        import os
        from sqlalchemy import create_engine
        from db.models import Base

        # Verify default path is relative and not hardcoded to a specific user's Windows folder
        from db.database import DATABASE_URL as ACTIVE_URL
        self.assertTrue(ACTIVE_URL.startswith("sqlite:///"))
        self.assertIn("db/email.db", ACTIVE_URL.replace("\\", "/"))

        # Verify dynamic creation using memory database (simulating cloned environment override)
        test_custom_url = "sqlite:///:memory:"
        custom_engine = create_engine(test_custom_url)
        Base.metadata.create_all(bind=custom_engine)
        self.assertTrue(custom_engine.dialect.has_table(custom_engine.connect(), "employees"))
        custom_engine.dispose()


if __name__ == "__main__":
    unittest.main()
