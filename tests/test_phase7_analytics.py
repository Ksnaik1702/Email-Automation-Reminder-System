"""
Phase 7 Automated Test Suite: Delivery Analytics & Reporting Dashboard.
Covers SQL aggregations, KPI calculations, daily trends, status distribution,
campaign performance, failure diagnostics, pagination, multi-dimensional filtering,
CSV exports, and strict separation between simulated and live executions.
"""
import csv
import io
import datetime
import unittest
from sqlalchemy.orm import Session

from db.database import SessionLocal, init_db
from db.models import Employee, EmailTemplate, Campaign, CampaignRecipient, ReminderJob, MessageLog, utc_now
from src.services import analytics_service
from api.routes.analytics import (
    get_analytics_overview,
    get_execution_trends,
    get_status_distribution,
    get_campaign_performance,
    get_failure_analysis,
    get_recent_activity,
    export_analytics_csv
)


class TestPhase7AnalyticsEngine(unittest.TestCase):
    """Integration and Unit Tests for Phase 7 Delivery Analytics & Reporting Engine."""

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session: Session = SessionLocal()
        self.test_prefix = f"p7_test_{datetime.datetime.now().strftime('%H%M%S%f')}"

        # Setup test employee
        self.emp = Employee(
            employee_id=f"EMP_{self.test_prefix}",
            full_name="Analytics Test Employee",
            email=f"{self.test_prefix}@testcorp.com",
            company="TestCorp Analytics",
            department="Operations",
            designation="Analyst",
            employment_status="Active"
        )
        self.session.add(self.emp)
        self.session.commit()

        # Setup test template
        self.tmpl = EmailTemplate(
            template_name=f"Template {self.test_prefix}",
            category="General Announcement",
            subject="Analytics Notice",
            body="Hello {{full_name}}"
        )
        self.session.add(self.tmpl)
        self.session.commit()

        # Setup test campaign 1
        self.camp1 = Campaign(
            campaign_name=f"Campaign Alpha {self.test_prefix}",
            category="General Announcement",
            template_id=self.tmpl.id,
            status="COMPLETED"
        )
        self.session.add(self.camp1)
        self.session.commit()

        # Setup campaign 1 recipient
        self.recip1 = CampaignRecipient(
            campaign_id=self.camp1.id,
            employee_id=self.emp.id,
            recipient_email=self.emp.email,
            status="Accepted"
        )
        self.session.add(self.recip1)
        self.session.commit()

        # Track logs created for clean cleanup
        self.created_log_ids = []

    def tearDown(self):
        # Clean up any created message logs
        if self.created_log_ids:
            self.session.query(MessageLog).filter(MessageLog.id.in_(self.created_log_ids)).delete(synchronize_session=False)
            self.session.commit()

        # Clean up recipients, campaigns, templates, employees
        self.session.query(CampaignRecipient).filter_by(employee_id=self.emp.id).delete()
        self.session.query(Campaign).filter_by(id=self.camp1.id).delete()
        self.session.query(EmailTemplate).filter_by(id=self.tmpl.id).delete()
        self.session.query(Employee).filter_by(id=self.emp.id).delete()
        self.session.commit()
        self.session.close()

    def _create_log(
        self,
        key_suffix: str,
        status: str,
        mode: str = "LIVE_SMTP",
        campaign_id: int = None,
        recipient_email: str = None,
        subject: str = "Analytics Update",
        attempt: int = 1,
        executed_at: datetime.datetime = None,
        error_category: str = None,
        error_message: str = None,
        message_id: str = None,
        smtp_queue_id: str = None,
        provider_message_id: str = None
    ) -> MessageLog:
        """Helper to create and track a test MessageLog record."""
        exec_key = f"{self.test_prefix}_{key_suffix}"
        log = MessageLog(
            execution_key=exec_key,
            recipient_email=recipient_email or self.emp.email,
            subject=subject,
            execution_mode=mode,
            execution_status=status,
            attempt_count=attempt,
            campaign_id=campaign_id or self.camp1.id,
            employee_id=self.emp.id,
            template_id=self.tmpl.id,
            executed_at=executed_at or utc_now(),
            error_category=error_category,
            error_message=error_message,
            message_id=message_id,
            smtp_queue_id=smtp_queue_id,
            provider_message_id=provider_message_id
        )
        self.session.add(log)
        self.session.commit()
        self.created_log_ids.append(log.id)
        return log

    # --------------------------------------------------------------------------
    # TEST 1: Empty / Zero-Match Database Handling
    # --------------------------------------------------------------------------
    def test_01_empty_dataset_graceful_handling(self):
        """Analytics functions must return clean zeroed metrics without crashing when no records match."""
        # Non-matching filter ensures zero results
        non_matching_search = "nonexistent_recipient_email_never_found_xyz@testcorp.com"
        
        kpis = analytics_service.get_overview_kpis(self.session, search=non_matching_search)
        self.assertEqual(kpis["total_executions"], 0)
        self.assertEqual(kpis["simulated_emails"], 0)
        self.assertEqual(kpis["smtp_accepted"], 0)
        self.assertEqual(kpis["delivery_confirmed"], 0)
        self.assertEqual(kpis["failed_emails"], 0)
        self.assertEqual(kpis["delivery_rate"], 0.0)
        self.assertEqual(kpis["failure_rate"], 0.0)

        trends = analytics_service.get_execution_trends(self.session, search=non_matching_search)
        self.assertEqual(trends, [])

        dist = analytics_service.get_status_distribution(self.session, search=non_matching_search)
        self.assertEqual(dist, [])

        fails = analytics_service.get_failure_analysis(self.session, campaign_id=999999)
        self.assertEqual(fails["total_failures"], 0)
        self.assertEqual(fails["categories"], [])
        self.assertEqual(fails["top_errors"], [])

        items, total_count, total_pages = analytics_service.get_recent_activity(self.session, search=non_matching_search)
        self.assertEqual(total_count, 0)
        self.assertEqual(items, [])
        self.assertEqual(total_pages, 1)

    # --------------------------------------------------------------------------
    # TEST 2: Strict Separation of Simulation vs Live & Status Classification
    # --------------------------------------------------------------------------
    def test_02_kpi_cards_and_mode_separation(self):
        """
        Verifies:
        - Never combines simulated executions with actual SMTP acceptance.
        - Never classifies SMTP_ACCEPTED as DELIVERY_CONFIRMED.
        - Computes delivery rate and failure rate accurately on live volume.
        """
        # 3 Simulated
        for i in range(3):
            self._create_log(f"sim_{i}", status="SIMULATED_SUCCESS", mode="SIMULATION")

        # 2 SMTP Accepted
        for i in range(2):
            self._create_log(f"accepted_{i}", status="SMTP_ACCEPTED", mode="LIVE_SMTP", message_id=f"<msg-acc-{i}@testcorp.com>")

        # 1 Delivery Confirmed
        self._create_log("confirmed_0", status="DELIVERY_CONFIRMED", mode="LIVE_SMTP")

        # 1 Failed
        self._create_log("failed_0", status="FAILED", mode="LIVE_SMTP", error_category="AUTHENTICATION_ERROR", error_message="535 Bad Credentials")

        # 1 Retry Pending
        self._create_log("retrying_0", status="RETRY_PENDING", mode="LIVE_SMTP")

        # 1 Delivery Uncertain
        self._create_log("uncertain_0", status="DELIVERY_UNCERTAIN", mode="LIVE_SMTP", error_category="DELIVERY_UNCERTAIN")

        # 1 Skipped Inactive
        self._create_log("skipped_0", status="SKIPPED_INACTIVE", mode="LIVE_SMTP")

        # Total inserted = 10
        kpis = analytics_service.get_overview_kpis(self.session, search=self.test_prefix)

        self.assertEqual(kpis["total_executions"], 10)
        self.assertEqual(kpis["simulated_emails"], 3)
        self.assertEqual(kpis["smtp_accepted"], 2)
        self.assertEqual(kpis["delivery_confirmed"], 1)
        self.assertEqual(kpis["failed_emails"], 1)
        self.assertEqual(kpis["retry_pending"], 1)
        self.assertEqual(kpis["delivery_uncertain"], 1)
        self.assertEqual(kpis["skipped_inactive"], 1)

        # Live total = 10 - 3 = 7
        self.assertEqual(kpis["live_total"], 7)

        # Delivery rate = (2 accepted + 1 confirmed) / 7 = 3/7 = 42.86%
        self.assertEqual(kpis["delivery_rate"], 42.86)

        # Failure rate = 1 failed / 7 = 14.29%
        self.assertEqual(kpis["failure_rate"], 14.29)

        # Ensure SMTP_ACCEPTED and DELIVERY_CONFIRMED are strictly distinct
        self.assertNotEqual(kpis["smtp_accepted"], kpis["delivery_confirmed"])

    # --------------------------------------------------------------------------
    # TEST 3: Status Distribution Percentages
    # --------------------------------------------------------------------------
    def test_03_status_distribution_calculation(self):
        """Status distribution must accurately calculate percentages and counts."""
        self._create_log("dist_sim1", status="SIMULATED_SUCCESS", mode="SIMULATION")
        self._create_log("dist_sim2", status="SIMULATED_SUCCESS", mode="SIMULATION")
        self._create_log("dist_acc1", status="SMTP_ACCEPTED", mode="LIVE_SMTP")
        self._create_log("dist_fail1", status="FAILED", mode="LIVE_SMTP")

        dist = analytics_service.get_status_distribution(self.session, search=self.test_prefix)
        self.assertEqual(len(dist), 3)

        dist_dict = {d["status"]: d for d in dist}
        self.assertEqual(dist_dict["SIMULATED_SUCCESS"]["count"], 2)
        self.assertEqual(dist_dict["SIMULATED_SUCCESS"]["percentage"], 50.0)

        self.assertEqual(dist_dict["SMTP_ACCEPTED"]["count"], 1)
        self.assertEqual(dist_dict["SMTP_ACCEPTED"]["percentage"], 25.0)

        self.assertEqual(dist_dict["FAILED"]["count"], 1)
        self.assertEqual(dist_dict["FAILED"]["percentage"], 25.0)

    # --------------------------------------------------------------------------
    # TEST 4: Daily Execution Trends Grouping
    # --------------------------------------------------------------------------
    def test_04_execution_trends_daily_grouping(self):
        """Trends must group records by calendar day and split simulated vs live counts."""
        day1 = datetime.datetime(2026, 11, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        day2 = datetime.datetime(2026, 11, 21, 14, 0, 0, tzinfo=datetime.timezone.utc)

        self._create_log("trend_1", status="SIMULATED_SUCCESS", mode="SIMULATION", executed_at=day1)
        self._create_log("trend_2", status="SMTP_ACCEPTED", mode="LIVE_SMTP", executed_at=day1)
        self._create_log("trend_3", status="SMTP_ACCEPTED", mode="LIVE_SMTP", executed_at=day2)

        trends = analytics_service.get_execution_trends(
            self.session,
            start_date="2026-11-20",
            end_date="2026-11-21",
            search=self.test_prefix
        )

        self.assertEqual(len(trends), 2)
        self.assertEqual(trends[0]["date"], "2026-11-20")
        self.assertEqual(trends[0]["simulated"], 1)
        self.assertEqual(trends[0]["live"], 1)
        self.assertEqual(trends[0]["total"], 2)

        self.assertEqual(trends[1]["date"], "2026-11-21")
        self.assertEqual(trends[1]["simulated"], 0)
        self.assertEqual(trends[1]["live"], 1)
        self.assertEqual(trends[1]["total"], 1)

    # --------------------------------------------------------------------------
    # TEST 5: Date Range Filtering (Inclusive Boundaries)
    # --------------------------------------------------------------------------
    def test_05_date_range_filtering(self):
        """Date filtering must cleanly include matching window and exclude out-of-range logs."""
        in_range_dt = datetime.datetime(2026, 11, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        out_range_early = datetime.datetime(2026, 11, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
        out_range_late = datetime.datetime(2026, 11, 25, 12, 0, 0, tzinfo=datetime.timezone.utc)

        self._create_log("in_win", status="SMTP_ACCEPTED", executed_at=in_range_dt)
        self._create_log("early_win", status="SMTP_ACCEPTED", executed_at=out_range_early)
        self._create_log("late_win", status="SMTP_ACCEPTED", executed_at=out_range_late)

        # Filter window: 2026-11-14 to 2026-11-16
        kpis = analytics_service.get_overview_kpis(
            self.session,
            start_date="2026-11-14",
            end_date="2026-11-16",
            search=self.test_prefix
        )
        self.assertEqual(kpis["total_executions"], 1)
        self.assertEqual(kpis["smtp_accepted"], 1)

    # --------------------------------------------------------------------------
    # TEST 6: Execution Status and Mode Filtering
    # --------------------------------------------------------------------------
    def test_06_status_and_mode_filtering(self):
        """Status and mode filters must restrict returned records accordingly."""
        self._create_log("stat_sim", status="SIMULATED_SUCCESS", mode="SIMULATION")
        self._create_log("stat_live_acc", status="SMTP_ACCEPTED", mode="LIVE_SMTP")
        self._create_log("stat_live_fail", status="FAILED", mode="LIVE_SMTP")

        # Filter status = FAILED
        failed_kpis = analytics_service.get_overview_kpis(self.session, status="FAILED", search=self.test_prefix)
        self.assertEqual(failed_kpis["total_executions"], 1)
        self.assertEqual(failed_kpis["failed_emails"], 1)

        # Filter mode = SIMULATION
        sim_kpis = analytics_service.get_overview_kpis(self.session, execution_mode="SIMULATION", search=self.test_prefix)
        self.assertEqual(sim_kpis["total_executions"], 1)
        self.assertEqual(sim_kpis["simulated_emails"], 1)

    # --------------------------------------------------------------------------
    # TEST 7: Campaign Performance Aggregation & Filtering
    # --------------------------------------------------------------------------
    def test_07_campaign_performance_aggregation(self):
        """Campaign performance must aggregate status metrics per campaign."""
        # Create second test campaign
        camp2 = Campaign(
            campaign_name=f"Campaign Beta {self.test_prefix}",
            category="Technical Training",
            template_id=self.tmpl.id,
            status="READY"
        )
        self.session.add(camp2)
        self.session.commit()

        # Log dispatches for campaign 1
        self._create_log("c1_acc", status="SMTP_ACCEPTED", campaign_id=self.camp1.id)
        self._create_log("c1_fail", status="FAILED", campaign_id=self.camp1.id)

        # Log dispatches for campaign 2
        self._create_log("c2_sim1", status="SIMULATED_SUCCESS", mode="SIMULATION", campaign_id=camp2.id)
        self._create_log("c2_sim2", status="SIMULATED_SUCCESS", mode="SIMULATION", campaign_id=camp2.id)

        perf = analytics_service.get_campaign_performance(self.session)
        perf_map = {p["campaign_id"]: p for p in perf if p["campaign_id"] in (self.camp1.id, camp2.id)}

        self.assertEqual(perf_map[self.camp1.id]["smtp_accepted"], 1)
        self.assertEqual(perf_map[self.camp1.id]["failed"], 1)
        self.assertEqual(perf_map[self.camp1.id]["total_logged"], 2)

        self.assertEqual(perf_map[camp2.id]["simulated"], 2)
        self.assertEqual(perf_map[camp2.id]["total_logged"], 2)

        # Clean up camp2
        self.session.query(Campaign).filter_by(id=camp2.id).delete()
        self.session.commit()

    # --------------------------------------------------------------------------
    # TEST 8: Failure Diagnostics & Root-Cause Grouping
    # --------------------------------------------------------------------------
    def test_08_failure_analysis_categorization(self):
        """Failure analysis must group errors by category and list top messages."""
        self._create_log("fail_auth1", status="FAILED", error_category="AUTHENTICATION_ERROR", error_message="535 Auth Failed")
        self._create_log("fail_auth2", status="FAILED", error_category="AUTHENTICATION_ERROR", error_message="535 Auth Failed")
        self._create_log("fail_net1", status="FAILED", error_category="TEMPORARY_NETWORK", error_message="Connection timed out")

        analysis = analytics_service.get_failure_analysis(self.session, campaign_id=self.camp1.id)
        self.assertEqual(analysis["total_failures"], 3)

        cat_counts = {c["category"]: c["count"] for c in analysis["categories"]}
        self.assertEqual(cat_counts["AUTHENTICATION_ERROR"], 2)
        self.assertEqual(cat_counts["TEMPORARY_NETWORK"], 1)

        self.assertTrue(len(analysis["top_errors"]) >= 2)
        top_msg = analysis["top_errors"][0]
        self.assertEqual(top_msg["error_message"], "535 Auth Failed")
        self.assertEqual(top_msg["occurrences"], 2)

    # --------------------------------------------------------------------------
    # TEST 9: Recipient Email & Subject Search
    # --------------------------------------------------------------------------
    def test_09_search_filtering(self):
        """Searching by recipient or subject must return only relevant records."""
        unique_email = f"unique_special_{self.test_prefix}@targetdomain.com"
        self._create_log("search_hit", status="SMTP_ACCEPTED", recipient_email=unique_email, subject="Important Notice")
        self._create_log("search_miss", status="SMTP_ACCEPTED", subject="Standard Report")

        items, total_count, _ = analytics_service.get_recent_activity(self.session, search="unique_special")
        self.assertEqual(total_count, 1)
        self.assertEqual(items[0]["recipient_email"], unique_email)

    # --------------------------------------------------------------------------
    # TEST 10: Pagination Offset and Limits
    # --------------------------------------------------------------------------
    def test_10_recent_activity_pagination(self):
        """Recent activity must paginate cleanly with page, page_size, total_pages, and total_count."""
        for i in range(5):
            self._create_log(f"page_{i}", status="SMTP_ACCEPTED", subject=f"Page Item {i}")

        # Page 1 of size 2
        p1_items, total, total_pages = analytics_service.get_recent_activity(
            self.session, search=self.test_prefix, page=1, page_size=2
        )
        self.assertEqual(total, 5)
        self.assertEqual(total_pages, 3)
        self.assertEqual(len(p1_items), 2)

        # Page 2 of size 2
        p2_items, _, _ = analytics_service.get_recent_activity(
            self.session, search=self.test_prefix, page=2, page_size=2
        )
        self.assertEqual(len(p2_items), 2)
        self.assertNotEqual(p1_items[0]["id"], p2_items[0]["id"])

        # Page 3 of size 2 (1 item remainder)
        p3_items, _, _ = analytics_service.get_recent_activity(
            self.session, search=self.test_prefix, page=3, page_size=2
        )
        self.assertEqual(len(p3_items), 1)

    # --------------------------------------------------------------------------
    # TEST 11: CSV Export - Complete Audit History
    # --------------------------------------------------------------------------
    def test_11_csv_export_complete_history(self):
        """Complete CSV export must produce valid CSV with proper headers and zero credential leakage."""
        self._create_log(
            "csv_rec_1",
            status="SMTP_ACCEPTED",
            mode="LIVE_SMTP",
            message_id="<csv-test-uuid@testcorp.com>",
            smtp_queue_id="4S9XYZ123"
        )

        csv_str, filename = analytics_service.export_analytics_csv(
            self.session, export_type="complete", search=self.test_prefix
        )

        self.assertTrue(filename.startswith("delivery_audit_complete_"))
        self.assertTrue(filename.endswith(".csv"))

        # Parse CSV
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)

        header = rows[0]
        self.assertIn("Log ID", header)
        self.assertIn("Execution Key", header)
        self.assertIn("RFC 5322 Message-ID", header)
        self.assertIn("SMTP Queue ID", header)

        # Inspect data row
        data_row = rows[1]
        row_str = " ".join(data_row)
        self.assertIn("<csv-test-uuid@testcorp.com>", row_str)
        self.assertIn("4S9XYZ123", row_str)

        # Security check: Never leak password or SMTP secrets
        for cell in data_row:
            self.assertNotIn("password", cell.lower())
            self.assertNotIn("mock_pass", cell.lower())

    # --------------------------------------------------------------------------
    # TEST 12: CSV Export - Campaigns, Failures, and Uncertain Reports
    # --------------------------------------------------------------------------
    def test_12_csv_export_specialized_reports(self):
        """Specialized CSV exports for campaigns, failures, and uncertain attempts."""
        self._create_log("csv_fail", status="FAILED", error_category="AUTHENTICATION_ERROR", error_message="Login Rejected")
        self._create_log("csv_uncert", status="DELIVERY_UNCERTAIN", error_message="Timeout awaiting response")

        # 1. Campaigns summary
        camp_csv, camp_fn = analytics_service.export_analytics_csv(self.session, export_type="campaigns")
        self.assertTrue(camp_fn.startswith("campaign_performance_summary_"))
        self.assertIn("Campaign Name", camp_csv)

        # 2. Failures report
        fail_csv, fail_fn = analytics_service.export_analytics_csv(self.session, export_type="failures", search=self.test_prefix)
        self.assertTrue(fail_fn.startswith("failed_executions_report_"))
        self.assertIn("AUTHENTICATION_ERROR", fail_csv)

        # 3. Uncertain report
        uncert_csv, uncert_fn = analytics_service.export_analytics_csv(self.session, export_type="uncertain", search=self.test_prefix)
        self.assertTrue(uncert_fn.startswith("delivery_uncertain_records_"))
        self.assertIn("Timeout awaiting response", uncert_csv)

        # 4. Invalid export type raises ValueError
        with self.assertRaises(ValueError):
            analytics_service.export_analytics_csv(self.session, export_type="invalid_type_xyz")

    # --------------------------------------------------------------------------
    # TEST 13: FastAPI Route Handler Verification
    # --------------------------------------------------------------------------
    def test_13_api_route_handlers(self):
        """FastAPI route functions in api/routes/analytics.py must return correct response shapes."""
        self._create_log("api_test_log", status="SMTP_ACCEPTED")

        # Test overview route
        overview_resp = get_analytics_overview(search=self.test_prefix, db=self.session)
        self.assertIsInstance(overview_resp, dict)
        self.assertIn("total_executions", overview_resp)

        # Test trends route
        trends_resp = get_execution_trends(search=self.test_prefix, db=self.session)
        self.assertIsInstance(trends_resp, list)

        # Test distribution route
        dist_resp = get_status_distribution(search=self.test_prefix, db=self.session)
        self.assertIsInstance(dist_resp, list)

        # Test recent activity route
        act_resp = get_recent_activity(search=self.test_prefix, db=self.session)
        self.assertIsInstance(act_resp, dict)
        self.assertIn("items", act_resp)
        self.assertIn("total_count", act_resp)

        # Test CSV export route
        csv_resp = export_analytics_csv(export_type="complete", search=self.test_prefix, db=self.session)
        self.assertEqual(csv_resp.media_type, "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", csv_resp.headers["Content-Disposition"])


if __name__ == "__main__":
    unittest.main()
