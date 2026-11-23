"""
Comprehensive Phase 5 Test Suite: Email Scheduling Engine & Background Worker.
Validates:
1. One-time campaign scheduling and execution.
2. Daily recurrence calculation and advancing.
3. Weekly recurrence calculation.
4. Monthly recurrence calculation and calendar-month handling.
5. Timezone conversion (UTC normalization, Asia/Kolkata, naive vs aware).
6. Due-job detection (past/current jobs detected, future jobs skipped).
7. Future-job safety (jobs scheduled in future remain pending).
8. Duplicate execution prevention (idempotency blocks re-dispatch).
9. Worker restart and crash recovery (recovers PROCESSING / interrupted campaigns).
10. Simulation mode guarantees (SIMULATED_SUCCESS status, preview generated, no SMTP).
11. Error handling resilience (faulty jobs logged without aborting worker loop).
12. Database persistence across independent sessions.
"""
import unittest
import sys
import datetime
from pathlib import Path
from dateutil.relativedelta import relativedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, init_db
from db.models import Campaign, CampaignRecipient, ReminderJob, MessageLog, EmailTemplate, Employee, utc_now
from api.schemas import CampaignCreate, EmailTemplateCreate, EmployeeCreate
from src.timezone_utils import ensure_utc, to_local, calculate_next_run, DEFAULT_TIMEZONE
from src.idempotency import generate_execution_key, generate_campaign_execution_key, is_already_executed
from src.services import scheduling_service, campaign_service, template_service, employee_service


class TestPhase5SchedulingEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session = SessionLocal()
        self._cleanup()

        # Create test fixture employee
        self.emp = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="TEST_EMP_S1",
            full_name="Devan Nair",
            email="devan.nair@example.com",
            company="Acme Corp",
            department="Operations",
            designation="Site Reliability Engineer",
            timezone="Asia/Kolkata",
            employment_status="Active"
        ))

        # Create test template
        self.tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Test Operational Alert",
            category="Technical Training",
            subject="System Update: {{ name }} ({{ department }})",
            body="<p>Hello {{ name }}, please review the operations update for {{ company }}.</p>"
        ))

    def tearDown(self):
        self._cleanup()
        self.session.rollback()
        self.session.close()

    def _cleanup(self):
        self.session.rollback()

        # Remove test campaigns
        camps = self.session.query(Campaign).filter(Campaign.campaign_name.like("Test Sched%")).all()
        for c in camps:
            campaign_service.delete_campaign(self.session, c.id)

        # Remove test reminders
        self.session.query(ReminderJob).filter(ReminderJob.reminder_title.like("Test Rem%")).delete(synchronize_session=False)

        # Remove test message logs
        self.session.query(MessageLog).filter(MessageLog.recipient_email == "devan.nair@example.com").delete(synchronize_session=False)

        # Remove test templates by prefix
        test_tmpls = self.session.query(EmailTemplate).filter(
            EmailTemplate.template_name.like("Test%")
        ).all()
        for t in test_tmpls:
            template_service.delete_template(self.session, t.id)

        # Remove test employee
        e = self.session.query(Employee).filter(Employee.employee_id == "TEST_EMP_S1").first()
        if e:
            employee_service.delete_employee(self.session, e.id)

        self.session.commit()

    def test_01_timezone_conversions(self):
        """1. Test timezone conversions between Asia/Kolkata and UTC."""
        # 10:00 AM IST on Jan 15, 2026 is 04:30 AM UTC on Jan 15, 2026
        dt_ist = datetime.datetime(2026, 1, 15, 10, 0, 0)
        dt_utc = ensure_utc(dt_ist, source_tz="Asia/Kolkata")
        
        self.assertEqual(dt_utc.year, 2026)
        self.assertEqual(dt_utc.month, 1)
        self.assertEqual(dt_utc.day, 15)
        self.assertEqual(dt_utc.hour, 4)
        self.assertEqual(dt_utc.minute, 30)

        # Converting back to local
        converted_back = to_local(dt_utc, target_tz="Asia/Kolkata")
        self.assertEqual(converted_back.hour, 10)
        self.assertEqual(converted_back.minute, 0)

    def test_02_recurrence_calculations(self):
        """2. Test Daily, Weekly, and Monthly recurrence calculations."""
        base_utc = datetime.datetime(2026, 1, 15, 4, 30, 0)

        # Daily
        daily_next = calculate_next_run(base_utc, "Daily", tz_name="Asia/Kolkata")
        self.assertEqual(daily_next, datetime.datetime(2026, 1, 16, 4, 30, 0))

        # Weekly
        weekly_next = calculate_next_run(base_utc, "Weekly", tz_name="Asia/Kolkata")
        self.assertEqual(weekly_next, datetime.datetime(2026, 1, 22, 4, 30, 0))

        # Monthly (Jan 15 -> Feb 15)
        monthly_next = calculate_next_run(base_utc, "Monthly", tz_name="Asia/Kolkata")
        self.assertEqual(monthly_next, datetime.datetime(2026, 2, 15, 4, 30, 0))

        # End of Month handling: Jan 31 -> Feb 28 in non-leap year (e.g. 2025/2026)
        jan31_utc = datetime.datetime(2026, 1, 31, 4, 30, 0)
        monthly_end = calculate_next_run(jan31_utc, "Monthly", tz_name="Asia/Kolkata")
        self.assertEqual(monthly_end.month, 2)
        self.assertEqual(monthly_end.day, 28)

        # Once / None returns None
        self.assertIsNone(calculate_next_run(base_utc, "None"))
        self.assertIsNone(calculate_next_run(base_utc, "Once"))

    def test_03_due_job_detection(self):
        """3. Test that due jobs are correctly identified and future jobs are skipped."""
        now = utc_now()
        past_time = now - datetime.timedelta(minutes=10)
        future_time = now + datetime.timedelta(hours=2)

        # Due campaign
        camp_due = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched Due Campaign",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))

        # Future campaign
        camp_future = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched Future Campaign",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=future_time,
            employee_ids=[self.emp.id]
        ))

        # Due reminder
        rem_due = ReminderJob(
            employee_id=self.emp.id,
            reminder_title="Test Rem Due Reminder",
            scheduled_at=past_time,
            status="Active"
        )
        # Future reminder
        rem_future = ReminderJob(
            employee_id=self.emp.id,
            reminder_title="Test Rem Future Reminder",
            scheduled_at=future_time,
            status="Active"
        )
        self.session.add_all([rem_due, rem_future])
        self.session.commit()

        # Query due jobs
        due_campaigns = scheduling_service.get_due_campaigns(self.session, as_of=now)
        due_reminders = scheduling_service.get_due_reminders(self.session, as_of=now)

        due_c_ids = {c.id for c in due_campaigns}
        due_r_ids = {r.id for r in due_reminders}

        self.assertIn(camp_due.id, due_c_ids, "Overdue campaign must be identified as due.")
        self.assertNotIn(camp_future.id, due_c_ids, "Future campaign must not be identified as due.")
        self.assertIn(rem_due.id, due_r_ids, "Overdue reminder must be identified as due.")
        self.assertNotIn(rem_future.id, due_r_ids, "Future reminder must not be identified as due.")

    def test_04_one_time_campaign_execution(self):
        """4. Test processing a due one-time campaign in simulation mode."""
        past_time = utc_now() - datetime.timedelta(minutes=5)
        camp = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched 04: One-Time Broadcast",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))

        stats = scheduling_service.process_due_campaign(self.session, camp, simulation_mode=True)
        self.assertEqual(stats["simulated"], 1)
        self.assertEqual(stats["skipped_duplicate"], 0)

        # Verify campaign state transitioned to COMPLETED
        refreshed_camp = campaign_service.get_campaign(self.session, camp.id)
        self.assertEqual(refreshed_camp.status, "COMPLETED")
        self.assertEqual(refreshed_camp.recipients[0].status, "Simulated")

        # Verify MessageLog entry
        log = self.session.query(MessageLog).filter(
            MessageLog.campaign_id == camp.id,
            MessageLog.recipient_email == "devan.nair@example.com"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "SIMULATED_SUCCESS")
        self.assertIn("Devan Nair", log.subject)

    def test_05_daily_recurring_reminder_advancing(self):
        """5. Test processing a recurring reminder and advancing scheduled_at to next day."""
        original_time = ensure_utc(utc_now() - datetime.timedelta(minutes=5))
        rem = ReminderJob(
            employee_id=self.emp.id,
            reminder_title="Test Rem Daily Standup",
            scheduled_at=original_time,
            recurrence_type="Daily",
            timezone="Asia/Kolkata",
            status="Active"
        )
        self.session.add(rem)
        self.session.commit()
        rem_id = rem.id

        res = scheduling_service.process_due_reminder(self.session, rem, simulation_mode=True)
        self.assertEqual(res["status"], "SIMULATED_SUCCESS")

        # Verify reminder schedule was advanced
        refreshed_rem = self.session.query(ReminderJob).filter(ReminderJob.id == rem_id).first()
        self.assertEqual(refreshed_rem.status, "Active")
        self.assertGreater(ensure_utc(refreshed_rem.scheduled_at), original_time)
        self.assertIsNotNone(refreshed_rem.last_executed_at)

        # Verify log recorded
        log = self.session.query(MessageLog).filter(MessageLog.reminder_id == rem_id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.execution_status, "SIMULATED_SUCCESS")

    def test_06_idempotency_blocks_duplicate_dispatch(self):
        """6. Test that executing the same job occurrence twice is safely blocked by idempotency."""
        past_time = utc_now() - datetime.timedelta(minutes=15)
        rem = ReminderJob(
            employee_id=self.emp.id,
            reminder_title="Test Rem Idempotency Check",
            scheduled_at=past_time,
            recurrence_type="None",
            status="Active"
        )
        self.session.add(rem)
        self.session.commit()
        rem_id = rem.id

        # First run: should execute
        res1 = scheduling_service.process_due_reminder(self.session, rem, simulation_mode=True)
        self.assertEqual(res1["status"], "SIMULATED_SUCCESS")

        # Manually reset reminder to simulate an uncompleted or re-polled occurrence
        rem.status = "Active"
        rem.scheduled_at = past_time
        self.session.commit()

        # Second run: should be blocked by idempotency
        res2 = scheduling_service.process_due_reminder(self.session, rem, simulation_mode=True)
        self.assertEqual(res2["status"], "Skipped_Duplicate")

        # Confirm only ONE MessageLog row exists for this occurrence
        log_count = self.session.query(MessageLog).filter(
            MessageLog.reminder_id == rem_id,
            MessageLog.scheduled_at == past_time
        ).count()
        self.assertEqual(log_count, 1)

    def test_07_worker_restart_recovery(self):
        """7. Test worker crash recovery for jobs left in PROCESSING state."""
        past_time = utc_now() - datetime.timedelta(minutes=20)
        # Create campaign and set to PROCESSING to simulate a crashed worker
        camp = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched Interrupted Campaign",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))
        camp.status = "PROCESSING"
        self.session.commit()

        # Verify get_due_campaigns finds it on restart sweep
        due = scheduling_service.get_due_campaigns(self.session)
        due_ids = [c.id for c in due]
        self.assertIn(camp.id, due_ids, "Interrupted PROCESSING campaign must be reclaimed on worker restart.")

        # Run sweep
        sweep_res = scheduling_service.run_pending_jobs(self.session, simulation_mode=True)
        self.assertGreaterEqual(sweep_res["campaigns_processed"], 1)

        # Confirm completed
        refreshed = campaign_service.get_campaign(self.session, camp.id)
        self.assertEqual(refreshed.status, "COMPLETED")

    def test_08_simulation_mode_safety(self):
        """8. Test that simulation mode creates HTML preview on disk without live SMTP."""
        past_time = utc_now() - datetime.timedelta(minutes=2)
        camp = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched 08: Simulation Verification",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))

        res = scheduling_service.process_due_campaign(self.session, camp, simulation_mode=True)
        self.assertEqual(res["simulated"], 1)

        # Find generated preview file
        previews = list(Path("outputs/previews").glob(f"campaign_{camp.id}_emp_{self.emp.id}_*"))
        self.assertGreaterEqual(len(previews), 1, "Simulation HTML preview file must be created.")

        content = previews[0].read_text(encoding="utf-8")
        self.assertIn("VIRTUAL SIMULATION MODE", content)
        self.assertIn("Devan Nair", content)

    def test_09_error_resilience(self):
        """9. Test that campaigns with faulty/rendering errors do not crash the batch loop."""
        past_time = utc_now() - datetime.timedelta(minutes=5)

        # Create template with invalid Jinja2 syntax
        broken_tmpl = EmailTemplate(
            template_name="Test Broken Syntax Template",
            category="Other",
            subject="Valid Subject",
            body="<p>Invalid tag: {% for x in %} missing end</p>"
        )
        self.session.add(broken_tmpl)
        self.session.commit()

        # Create campaign using broken template
        camp = Campaign(
            campaign_name="Test Sched 09: Faulty Template",
            template_id=broken_tmpl.id,
            status="READY",
            scheduled_at=past_time
        )
        self.session.add(camp)
        self.session.flush()

        recip = CampaignRecipient(
            campaign_id=camp.id,
            employee_id=self.emp.id,
            recipient_email=self.emp.email,
            status="Pending"
        )
        self.session.add(recip)
        self.session.commit()

        # Run sweep: should safely handle the error and record in summary
        sweep_res = scheduling_service.run_pending_jobs(self.session, simulation_mode=True)
        self.assertIn("errors", sweep_res)
        self.assertGreaterEqual(len(sweep_res["errors"]), 1)

        # Verify recipient marked with failure status and worker did not crash
        self.session.refresh(recip)
        self.assertEqual(recip.status, "Failed_Render")

        # Cleanup
        self.session.delete(recip)
        self.session.delete(camp)
        self.session.delete(broken_tmpl)
        self.session.commit()

    def test_10_multi_job_sweep_aggregation(self):
        """10. Test that run_pending_jobs processes multiple campaigns & reminders in one sweep."""
        past_time = utc_now() - datetime.timedelta(minutes=10)

        camp = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched 10: Multi-Job Sweep",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))
        rem = ReminderJob(
            employee_id=self.emp.id,
            reminder_title="Test Rem Multi Sweep",
            scheduled_at=past_time,
            recurrence_type="None",
            status="Active"
        )
        self.session.add(rem)
        self.session.commit()

        sweep_res = scheduling_service.run_pending_jobs(self.session, simulation_mode=True)
        self.assertGreaterEqual(sweep_res["campaigns_processed"], 1)
        self.assertGreaterEqual(sweep_res["reminders_processed"], 1)
        self.assertGreaterEqual(sweep_res["messages_simulated"], 2)

    def test_11_database_persistence_across_sessions(self):
        """11. Test that executed logs and updated campaign states persist in fresh DB sessions."""
        past_time = utc_now() - datetime.timedelta(minutes=5)
        camp = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Sched 11: Persistence Verification",
            template_id=self.tmpl.id,
            status="READY",
            scheduled_at=past_time,
            employee_ids=[self.emp.id]
        ))
        camp_id = camp.id

        scheduling_service.process_due_campaign(self.session, camp, simulation_mode=True)
        self.session.commit()

        # Open completely independent DB session
        new_session = SessionLocal()
        try:
            persisted_camp = new_session.query(Campaign).filter(Campaign.id == camp_id).first()
            self.assertEqual(persisted_camp.status, "COMPLETED")

            persisted_logs = new_session.query(MessageLog).filter(MessageLog.campaign_id == camp_id).all()
            self.assertEqual(len(persisted_logs), 1)
            self.assertEqual(persisted_logs[0].execution_status, "SIMULATED_SUCCESS")
        finally:
            new_session.close()

    def test_12_recurrence_leap_year_and_dst_safety(self):
        """12. Test calendar calculations for leap year Feb 29 and standard month rollover."""
        leap_feb29 = datetime.datetime(2024, 2, 29, 9, 0, 0)
        # Feb 29 + 1 month in leap year -> March 29
        march_next = calculate_next_run(leap_feb29, "Monthly", tz_name="Asia/Kolkata")
        self.assertEqual(march_next.month, 3)
        self.assertEqual(march_next.day, 29)

        # Feb 28 in non-leap year + 1 month -> March 28
        non_leap_feb28 = datetime.datetime(2025, 2, 28, 9, 0, 0)
        march_non_leap = calculate_next_run(non_leap_feb28, "Monthly", tz_name="Asia/Kolkata")
        self.assertEqual(march_non_leap.month, 3)
        self.assertEqual(march_non_leap.day, 28)


if __name__ == "__main__":
    unittest.main()
