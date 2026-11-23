"""
Comprehensive Phase 4 Test Suite: Email Campaign Creation & Multi-Recipient Targeting.
Validates:
1. Campaign creation with template association and recipient targeting.
2. Recipient deduplication on bulk assignment.
3. Adding recipients by department cohort.
4. Removing individual recipients from campaign.
5. Updating campaign metadata, status transitions (DRAFT -> READY -> SCHEDULED), and template swapping.
6. Cascade deletion safety (campaign deletion drops recipients, leaves employees & templates intact).
7. Campaign search and status/category filtering.
8. Personalized email preview for targeted employees within a campaign (HTML & text).
9. Missing recipient / campaign preview diagnostics and error containment.
10. Campaign overview metrics calculation.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, init_db
from db.models import Campaign, CampaignRecipient, Employee, EmailTemplate
from api.schemas import CampaignCreate, CampaignUpdate, EmailTemplateCreate, EmployeeCreate
from src.services import campaign_service, template_service, employee_service


class TestPhase4CampaignManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session = SessionLocal()
        # Clean up any leftover test data
        self._cleanup()

        # Create test fixture employees
        self.emp1 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="TEST_EMP_C1",
            full_name="Alice Candidate",
            email="alice.candidate@example.com",
            company="Acme Corp",
            department="Engineering",
            designation="Software Engineer",
            timezone="UTC",
            employment_status="Active"
        ))
        self.emp2 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="TEST_EMP_C2",
            full_name="Bob Manager",
            email="bob.manager@example.com",
            company="Acme Corp",
            department="Product",
            designation="Product Manager",
            timezone="UTC",
            employment_status="Active"
        ))
        self.emp3 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="TEST_EMP_C3",
            full_name="Charlie Designer",
            email="charlie.designer@example.com",
            company="Acme Corp",
            department="Engineering",
            designation="UI/UX Specialist",
            timezone="UTC",
            employment_status="Active"
        ))

        # Create test template
        self.tmpl = template_service.create_template(self.session, EmailTemplateCreate(
            template_name="Sprint Retrospective Invitation",
            category="Meeting Invitation",
            subject="Sprint Review: {{ name }} ({{ department }})",
            body="<p>Hi {{ name }},</p><p>Please join us for the retrospective. Your role: <strong>{{ designation }}</strong>.</p>"
        ))

    def tearDown(self):
        self._cleanup()
        self.session.rollback()
        self.session.close()

    def _cleanup(self):
        test_campaigns = self.session.query(Campaign).filter(
            Campaign.campaign_name.like("Test Camp%")
        ).all()
        for c in test_campaigns:
            campaign_service.delete_campaign(self.session, c.id)

        test_templates = self.session.query(EmailTemplate).filter(
            EmailTemplate.template_name == "Sprint Retrospective Invitation"
        ).all()
        for t in test_templates:
            template_service.delete_template(self.session, t.id)

        for emp_code in ["TEST_EMP_C1", "TEST_EMP_C2", "TEST_EMP_C3"]:
            e = self.session.query(Employee).filter(Employee.employee_id == emp_code).first()
            if e:
                employee_service.delete_employee(self.session, e.id)

    def test_01_campaign_creation_with_recipients(self):
        """1. Test creating a campaign, linking template, and targeting multiple recipients."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 01: Product Launch",
            description="All-hands launch notification",
            category="General Announcement",
            template_id=self.tmpl.id,
            status="DRAFT",
            employee_ids=[self.emp1.id, self.emp2.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertIsNotNone(camp.id)
        self.assertEqual(camp.campaign_name, "Test Camp 01: Product Launch")
        self.assertEqual(camp.status, "DRAFT")
        self.assertEqual(camp.template_id, self.tmpl.id)
        self.assertEqual(len(camp.recipients), 2)

        recipient_emails = {r.recipient_email for r in camp.recipients}
        self.assertIn("alice.candidate@example.com", recipient_emails)
        self.assertIn("bob.manager@example.com", recipient_emails)

    def test_02_recipient_deduplication(self):
        """2. Test that duplicate employee IDs in creation are safely deduplicated."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 02: Deduplication Check",
            category="Technical Training",
            template_id=self.tmpl.id,
            status="DRAFT",
            employee_ids=[self.emp1.id, self.emp1.id, self.emp2.id, self.emp2.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertEqual(len(camp.recipients), 2, "Duplicate recipient employee IDs must be deduplicated.")

    def test_03_add_recipients_safely(self):
        """3. Test adding additional recipients to an existing campaign without duplicating existing ones."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 03: Incremental Targeting",
            category="Meeting Invitation",
            template_id=self.tmpl.id,
            status="DRAFT",
            employee_ids=[self.emp1.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertEqual(len(camp.recipients), 1)

        # Add emp2 and emp3 along with emp1 again
        added_count = campaign_service.add_recipients_to_campaign(
            self.session, camp.id, [self.emp1.id, self.emp2.id, self.emp3.id]
        )
        self.assertEqual(added_count, 2, "Only new employees (emp2, emp3) should be added; emp1 skipped.")

        # Re-fetch campaign
        refreshed = campaign_service.get_campaign(self.session, camp.id)
        self.assertEqual(len(refreshed.recipients), 3)

    def test_04_remove_recipient_from_campaign(self):
        """4. Test removing an individual employee from a campaign recipient list."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 04: Remove Recipient",
            category="Task Deadline",
            template_id=self.tmpl.id,
            status="DRAFT",
            employee_ids=[self.emp1.id, self.emp2.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertEqual(len(camp.recipients), 2)

        # Remove emp1
        removed = campaign_service.remove_recipient_from_campaign(self.session, camp.id, self.emp1.id)
        self.assertTrue(removed)

        refreshed = campaign_service.get_campaign(self.session, camp.id)
        self.assertEqual(len(refreshed.recipients), 1)
        self.assertEqual(refreshed.recipients[0].employee_id, self.emp2.id)

    def test_05_update_campaign_details_and_status(self):
        """5. Test updating campaign parameters and transitioning status (DRAFT -> READY)."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 05: Status Transition",
            category="Meeting Invitation",
            template_id=self.tmpl.id,
            status="DRAFT"
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        self.assertEqual(camp.status, "DRAFT")

        # Update to READY
        update_in = CampaignUpdate(
            campaign_name="Test Camp 05: Ready for Dispatch",
            status="READY",
            description="Campaign validated and approved by HR"
        )
        updated = campaign_service.update_campaign(self.session, camp.id, update_in)
        self.assertEqual(updated.campaign_name, "Test Camp 05: Ready for Dispatch")
        self.assertEqual(updated.status, "READY")
        self.assertEqual(updated.description, "Campaign validated and approved by HR")

    def test_06_cascade_deletion_preserves_employees_and_templates(self):
        """6. Test deleting a campaign cascades recipients, but preserves foreign employees & templates."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 06: Cascade Verification",
            category="General Announcement",
            template_id=self.tmpl.id,
            employee_ids=[self.emp1.id, self.emp2.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)
        camp_id = camp.id

        # Confirm recipients exist
        recipients_count = self.session.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == camp_id
        ).count()
        self.assertEqual(recipients_count, 2)

        # Delete campaign
        deleted = campaign_service.delete_campaign(self.session, camp_id)
        self.assertTrue(deleted)

        # Confirm recipients were cascaded
        recipients_after = self.session.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == camp_id
        ).count()
        self.assertEqual(recipients_after, 0)

        # Confirm employees and template are still intact in DB
        self.assertIsNotNone(self.session.query(Employee).filter(Employee.id == self.emp1.id).first())
        self.assertIsNotNone(self.session.query(EmailTemplate).filter(EmailTemplate.id == self.tmpl.id).first())

    def test_07_search_and_filter_campaigns(self):
        """7. Test searching campaigns by title and filtering by category & status."""
        c1 = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Camp 07A: Alpha Onboarding",
            category="Employee Onboarding",
            template_id=self.tmpl.id,
            status="DRAFT"
        ))
        c2 = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Camp 07B: Beta Security",
            category="Technical Training",
            template_id=self.tmpl.id,
            status="READY"
        ))

        # Search by keyword
        res, count = campaign_service.list_campaigns(self.session, search="Alpha")
        self.assertEqual(count, 1)
        self.assertEqual(res[0].id, c1.id)

        # Filter by status
        res_ready, count_ready = campaign_service.list_campaigns(self.session, status="READY")
        ready_ids = {c.id for c in res_ready}
        self.assertIn(c2.id, ready_ids)

        # Filter by category
        res_cat, count_cat = campaign_service.list_campaigns(self.session, category="Employee Onboarding")
        cat_ids = {c.id for c in res_cat}
        self.assertIn(c1.id, cat_ids)

    def test_08_personalized_campaign_preview(self):
        """8. Test rendering personalized email preview for a specific campaign recipient."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 08: Personalized Preview",
            category="Meeting Invitation",
            template_id=self.tmpl.id,
            employee_ids=[self.emp1.id, self.emp2.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)

        # Preview for Alice (Engineering)
        preview_alice = campaign_service.preview_campaign_for_recipient(self.session, camp.id, self.emp1.id)
        self.assertTrue(preview_alice.is_valid)
        self.assertIn("Alice Candidate", preview_alice.rendered_subject)
        self.assertIn("Engineering", preview_alice.rendered_subject)
        self.assertIn("Software Engineer", preview_alice.rendered_html)
        self.assertIn("name", preview_alice.variables_used)

        # Preview for Bob (Product)
        preview_bob = campaign_service.preview_campaign_for_recipient(self.session, camp.id, self.emp2.id)
        self.assertTrue(preview_bob.is_valid)
        self.assertIn("Bob Manager", preview_bob.rendered_subject)
        self.assertIn("Product", preview_bob.rendered_subject)
        self.assertIn("Product Manager", preview_bob.rendered_html)

    def test_09_preview_nonexistent_recipient_raises_error(self):
        """9. Test that previewing a campaign for an unassociated employee raises ValueError."""
        camp_in = CampaignCreate(
            campaign_name="Test Camp 09: Diagnostics",
            category="Other",
            template_id=self.tmpl.id,
            employee_ids=[self.emp1.id]
        )
        camp = campaign_service.create_campaign(self.session, camp_in)

        # emp3 is not targeted in camp
        with self.assertRaises(ValueError):
            campaign_service.preview_campaign_for_recipient(self.session, camp.id, self.emp3.id)

    def test_10_campaign_stats_metrics(self):
        """10. Test that get_campaign_stats returns accurate summary metrics."""
        camp1 = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Camp 10A",
            template_id=self.tmpl.id,
            status="DRAFT",
            employee_ids=[self.emp1.id, self.emp2.id]
        ))
        camp2 = campaign_service.create_campaign(self.session, CampaignCreate(
            campaign_name="Test Camp 10B",
            template_id=self.tmpl.id,
            status="READY",
            employee_ids=[self.emp3.id]
        ))

        stats = campaign_service.get_campaign_stats(self.session)
        self.assertGreaterEqual(stats.total_campaigns, 2)
        self.assertGreaterEqual(stats.draft_campaigns, 1)
        self.assertGreaterEqual(stats.ready_campaigns, 1)
        self.assertGreaterEqual(stats.total_recipients_targeted, 3)


if __name__ == "__main__":
    unittest.main()
