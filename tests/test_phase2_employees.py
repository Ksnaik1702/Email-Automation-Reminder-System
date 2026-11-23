"""
Comprehensive Phase 2 Test Suite: Employee Management & CSV Ingestion.
Validates CRUD, Validation, Search, Filtering, CSV Import/Export, and Single Source of Truth.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, init_db
from db.models import Employee
from api.schemas import EmployeeCreate, EmployeeUpdate
from src.services import employee_service


class TestPhase2EmployeeManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.session = SessionLocal()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_01_create_and_retrieve_employee(self):
        """Test successful employee creation and field retrieval."""
        emp_in = EmployeeCreate(
            employee_id="EMP_P2_001",
            full_name="Meera Krishnan",
            email="meera.krishnan@testcorp.com",
            company="TestCorp",
            department="Human Resources",
            designation="HR Business Partner",
            timezone="Asia/Kolkata",
            employment_status="Active"
        )
        emp = employee_service.create_employee(self.session, emp_in)
        self.assertIsNotNone(emp.id)
        self.assertEqual(emp.employee_id, "EMP_P2_001")
        self.assertEqual(emp.email, "meera.krishnan@testcorp.com")

        # Retrieve
        fetched = employee_service.get_employee(self.session, emp.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.full_name, "Meera Krishnan")

        # Cleanup
        employee_service.delete_employee(self.session, emp.id)

    def test_02_duplicate_employee_id_prevention(self):
        """Test that duplicate employee_id is rejected with ValueError."""
        emp1_in = EmployeeCreate(
            employee_id="EMP_DUP_ID",
            full_name="First Employee",
            email="first.emp@testcorp.com"
        )
        emp1 = employee_service.create_employee(self.session, emp1_in)

        # Attempt to create second employee with identical code
        emp2_in = EmployeeCreate(
            employee_id="EMP_DUP_ID",
            full_name="Second Employee",
            email="second.emp@testcorp.com"
        )
        with self.assertRaises(ValueError) as ctx:
            employee_service.create_employee(self.session, emp2_in)
        self.assertIn("already exists", str(ctx.exception))

        # Cleanup
        employee_service.delete_employee(self.session, emp1.id)

    def test_03_duplicate_email_prevention(self):
        """Test that duplicate email is rejected with ValueError."""
        emp1_in = EmployeeCreate(
            employee_id="EMP_EMAIL_1",
            full_name="User Alpha",
            email="shared.email@testcorp.com"
        )
        emp1 = employee_service.create_employee(self.session, emp1_in)

        # Attempt to create second employee with identical email
        emp2_in = EmployeeCreate(
            employee_id="EMP_EMAIL_2",
            full_name="User Beta",
            email="shared.email@testcorp.com"
        )
        with self.assertRaises(ValueError) as ctx:
            employee_service.create_employee(self.session, emp2_in)
        self.assertIn("already registered", str(ctx.exception))

        # Cleanup
        employee_service.delete_employee(self.session, emp1.id)

    def test_04_invalid_email_syntax(self):
        """Test that invalid email format raises validation error."""
        with self.assertRaises(Exception):
            EmployeeCreate(
                employee_id="EMP_BAD_EMAIL",
                full_name="Bad Email User",
                email="not-an-email-at-all"
            )

    def test_05_invalid_timezone_validation(self):
        """Test that non-existent timezone raises validation error."""
        with self.assertRaises(Exception):
            EmployeeCreate(
                employee_id="EMP_BAD_TZ",
                full_name="Bad TZ User",
                email="good.email@testcorp.com",
                timezone="Mars/Olympus_Mons"
            )

    def test_06_update_employee(self):
        """Test updating employee fields."""
        emp = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="EMP_UPDATE_TEST",
            full_name="Original Name",
            email="orig.name@testcorp.com",
            department="Sales"
        ))

        # Update designation and department
        updated = employee_service.update_employee(
            self.session,
            emp.id,
            EmployeeUpdate(full_name="Updated Name", department="Marketing", designation="Lead")
        )
        self.assertEqual(updated.full_name, "Updated Name")
        self.assertEqual(updated.department, "Marketing")

        # Cleanup
        employee_service.delete_employee(self.session, emp.id)

    def test_07_search_and_department_filtering(self):
        """Test searching employees and filtering by department."""
        emp1 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="SEARCH_01",
            full_name="Harish Chandra",
            email="harish.chandra@company.com",
            department="Research"
        ))
        emp2 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="SEARCH_02",
            full_name="Deepa Malik",
            email="deepa.malik@company.com",
            department="Research"
        ))
        emp3 = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="SEARCH_03",
            full_name="Sanjay Gupta",
            email="sanjay.gupta@company.com",
            department="Finance"
        ))

        # Search for "Chandra"
        results, count = employee_service.list_employees(self.session, search="Chandra")
        self.assertEqual(count, 1)
        self.assertEqual(results[0].employee_id, "SEARCH_01")

        # Filter by department "Research"
        res_dept, dept_count = employee_service.list_employees(self.session, department="Research")
        self.assertGreaterEqual(dept_count, 2)
        dept_codes = [e.employee_id for e in res_dept]
        self.assertIn("SEARCH_01", dept_codes)
        self.assertIn("SEARCH_02", dept_codes)
        self.assertNotIn("SEARCH_03", dept_codes)

        # Cleanup
        employee_service.delete_employee(self.session, emp1.id)
        employee_service.delete_employee(self.session, emp2.id)
        employee_service.delete_employee(self.session, emp3.id)

    def test_08_employee_overview_statistics(self):
        """Test stats calculation: total, active, inactive, and department counts."""
        stats = employee_service.get_employee_stats(self.session)
        self.assertIn("total_employees", stats)
        self.assertIn("active_employees", stats)
        self.assertIn("department_distribution", stats)
        self.assertGreaterEqual(stats["total_employees"], 5)  # Historical contacts preserved

    def test_09_csv_export(self):
        """Test exporting employee records to CSV string."""
        csv_text = employee_service.export_employees_to_csv(self.session)
        self.assertIn("employee_id,full_name,email", csv_text)
        self.assertIn("aarav.sharma@example.com", csv_text)

    def test_10_csv_import_valid_and_missing_and_duplicates(self):
        """Test CSV import handling valid records, missing fields, and duplicate detection."""
        csv_payload = (
            "employee_id,full_name,email,department,role\n"
            "IMP_001,Valid Candidate,valid.candidate@company.com,Technology,Engineer\n"
            "IMP_002,,missing.name@company.com,Technology,Engineer\n"          # Missing name (Fail)
            "IMP_003,Bad Email User,invalid-email-address,Technology,Engineer\n" # Bad email (Fail)
            "IMP_001,Duplicate in CSV,another.email@company.com,Technology,Staff\n" # Duplicate ID in batch (Skip)
            "IMP_004,Valid Candidate 2,valid.candidate2@company.com,Design,Designer\n"
        ).encode("utf-8")

        summary = employee_service.import_employees_from_csv(self.session, csv_payload)
        self.assertEqual(summary.total_rows, 5)
        self.assertEqual(summary.successfully_imported, 2)  # IMP_001 and IMP_004
        self.assertEqual(summary.failed_records, 2)         # Missing name & bad email
        self.assertEqual(summary.skipped_records, 1)        # Duplicate IMP_001

        # Verify imported in DB
        emp1 = employee_service.get_employee_by_code(self.session, "IMP_001")
        self.assertIsNotNone(emp1)
        self.assertEqual(emp1.full_name, "Valid Candidate")

        emp2 = employee_service.get_employee_by_code(self.session, "IMP_004")
        self.assertIsNotNone(emp2)

        # Cleanup
        employee_service.delete_employee(self.session, emp1.id)
        employee_service.delete_employee(self.session, emp2.id)

    def test_11_csv_import_empty_file_and_invalid_headers(self):
        """Test CSV import with empty file or missing critical headers."""
        # Empty file
        empty_res = employee_service.import_employees_from_csv(self.session, b"")
        self.assertEqual(empty_res.failed_records, 1)

        # Incorrect headers
        bad_headers = "col1,col2,col3\nval1,val2,val3\n".encode("utf-8")
        bad_res = employee_service.import_employees_from_csv(self.session, bad_headers)
        self.assertEqual(bad_res.failed_records, 1)
        self.assertIn("Missing required columns", bad_res.errors[0].reason)

    def test_12_single_source_of_truth_integration(self):
        """
        Verify that an employee created through Phase 2 service
        is immediately visible in the unified database for other modules.
        """
        new_emp = employee_service.create_employee(self.session, EmployeeCreate(
            employee_id="EMP_SSOT_VERIFY",
            full_name="Unified DB Employee",
            email="unified.db@testcorp.com",
            department="Infrastructure"
        ))

        # Query directly from DB session using raw Employee model
        db_record = self.session.query(Employee).filter_by(employee_id="EMP_SSOT_VERIFY").first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.full_name, "Unified DB Employee")

        # Cleanup
        employee_service.delete_employee(self.session, new_emp.id)


if __name__ == "__main__":
    unittest.main()
