"""
Employee Service Layer: Implements business logic, validation,
CRUD operations, and CSV import/export for the Employee module.
"""
import io
import csv
import zoneinfo
import datetime
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from db.models import Employee, utc_now
from api.schemas import (
    EmployeeCreate, EmployeeUpdate, CSVImportSummary, CSVImportErrorDetail,
    EMAIL_REGEX, VALID_STATUSES
)
from src.logger import logger


def get_employee(db: Session, employee_id: int) -> Optional[Employee]:
    """Retrieves an employee by database primary key ID."""
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_employee_by_code(db: Session, code: str) -> Optional[Employee]:
    """Retrieves an employee by company employee code (e.g., C101)."""
    return db.query(Employee).filter(Employee.employee_id == code.strip()).first()


def get_employee_by_email(db: Session, email: str) -> Optional[Employee]:
    """Retrieves an employee by email address."""
    return db.query(Employee).filter(Employee.email == email.strip().lower()).first()


def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    """
    Creates a new employee with duplicate validation.
    Raises ValueError if employee_id or email already exists.
    """
    clean_code = employee_in.employee_id.strip()
    clean_email = employee_in.email.strip().lower()

    if get_employee_by_code(db, clean_code):
        raise ValueError(f"Employee ID '{clean_code}' already exists in database.")

    if get_employee_by_email(db, clean_email):
        raise ValueError(f"Email address '{clean_email}' is already registered to another employee.")

    emp = Employee(
        employee_id=clean_code,
        full_name=employee_in.full_name.strip(),
        email=clean_email,
        company=employee_in.company.strip() if employee_in.company else "Nexus Tech",
        department=employee_in.department.strip() if employee_in.department else "Operations",
        designation=employee_in.designation.strip() if employee_in.designation else "Staff Member",
        timezone=employee_in.timezone.strip(),
        employment_status=employee_in.employment_status.strip().title(),
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(emp)
    db.commit()
    db.refresh(emp)
    logger.info(f"Created employee: ID={emp.id}, Code='{emp.employee_id}', Email='{emp.email}'")
    return emp


def list_employees(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Employee], int]:
    """
    Lists employees with multi-field search and department/status filtering.
    Returns (items, total_count).
    """
    query = db.query(Employee)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(term),
                Employee.email.ilike(term),
                Employee.employee_id.ilike(term),
                Employee.designation.ilike(term)
            )
        )

    if department and department.strip().lower() != "all":
        query = query.filter(Employee.department.ilike(department.strip()))

    if status and status.strip().lower() != "all":
        query = query.filter(Employee.employment_status == status.strip().title())

    total = query.count()
    items = query.order_by(Employee.id.desc()).offset(skip).limit(limit).all()
    return items, total


def update_employee(db: Session, employee_id: int, employee_in: EmployeeUpdate) -> Optional[Employee]:
    """
    Updates existing employee fields with email uniqueness validation.
    """
    emp = get_employee(db, employee_id)
    if not emp:
        return None

    update_data = employee_in.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].strip().lower()
        if new_email != emp.email:
            existing = get_employee_by_email(db, new_email)
            if existing and existing.id != emp.id:
                raise ValueError(f"Email '{new_email}' is already in use by employee {existing.employee_id}.")
            emp.email = new_email

    for field, val in update_data.items():
        if field != "email" and val is not None:
            setattr(emp, field, val)

    emp.updated_at = utc_now()
    db.commit()
    db.refresh(emp)
    logger.info(f"Updated employee ID={emp.id} ({emp.employee_id})")
    return emp


def delete_employee(db: Session, employee_id: int) -> bool:
    """
    Deletes an employee record and cascades associated records.
    """
    emp = get_employee(db, employee_id)
    if not emp:
        return False

    code = emp.employee_id
    db.delete(emp)
    db.commit()
    logger.info(f"Deleted employee ID={employee_id} ({code})")
    return True


def get_employee_stats(db: Session) -> Dict[str, Any]:
    """
    Calculates summary metrics for employee management dashboard.
    """
    total = db.query(Employee).count()
    active = db.query(Employee).filter(Employee.employment_status == "Active").count()
    inactive = total - active

    # Department distribution
    dept_rows = db.query(
        Employee.department, func.count(Employee.id)
    ).group_by(Employee.department).all()

    distribution = {dept or "Unassigned": count for dept, count in dept_rows}

    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": inactive,
        "departments_count": len(distribution),
        "department_distribution": distribution
    }


def import_employees_from_csv(db: Session, file_content: bytes) -> CSVImportSummary:
    """
    Parses, validates, and imports employee records from CSV file bytes.
    Enforces header verification, format checks, duplicate detection,
    and returns a structured audit summary.
    """
    try:
        text_stream = io.StringIO(file_content.decode("utf-8-sig"))
    except UnicodeDecodeError:
        text_stream = io.StringIO(file_content.decode("latin-1"))

    reader = csv.DictReader(text_stream)

    if not reader.fieldnames:
        return CSVImportSummary(
            total_rows=0,
            successfully_imported=0,
            skipped_records=0,
            failed_records=1,
            errors=[CSVImportErrorDetail(row_number=0, reason="Empty CSV file or missing headers")]
        )

    # Clean headers
    headers = [h.strip().lower() for h in reader.fieldnames if h]

    # Flexible header aliases
    code_field = next((h for h in reader.fieldnames if h.strip().lower() in ("employee_id", "contact_id", "emp_id", "id")), None)
    name_field = next((h for h in reader.fieldnames if h.strip().lower() in ("full_name", "name", "employee_name")), None)
    email_field = next((h for h in reader.fieldnames if h.strip().lower() in ("email", "email_address")), None)

    if not code_field or not name_field or not email_field:
        return CSVImportSummary(
            total_rows=0,
            successfully_imported=0,
            skipped_records=0,
            failed_records=1,
            errors=[CSVImportErrorDetail(
                row_number=1,
                reason=f"Missing required columns. Found: {reader.fieldnames}. Required: ['employee_id', 'full_name', 'email']"
            )]
        )

    available_tz = zoneinfo.available_timezones()

    total_rows = 0
    success_count = 0
    skip_count = 0
    fail_count = 0
    errors: List[CSVImportErrorDetail] = []

    seen_codes_in_batch = set()
    seen_emails_in_batch = set()
    new_employees: List[Employee] = []

    for row_idx, row in enumerate(reader, start=2):  # Row 2 is first data row
        total_rows += 1
        raw_code = (row.get(code_field) or "").strip()
        raw_name = (row.get(name_field) or "").strip()
        raw_email = (row.get(email_field) or "").strip().lower()

        # Missing required values
        if not raw_code or not raw_name or not raw_email:
            fail_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code or "N/A",
                email=raw_email or "N/A",
                reason="Missing required field (employee_id, full_name, or email cannot be empty)"
            ))
            continue

        # Email syntax validation
        if not EMAIL_REGEX.match(raw_email):
            fail_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code,
                email=raw_email,
                reason=f"Invalid email syntax: '{raw_email}'"
            ))
            continue

        # In-batch duplicate checks
        if raw_code in seen_codes_in_batch:
            skip_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code,
                email=raw_email,
                reason=f"Duplicate employee_id '{raw_code}' within the uploaded file (Skipped)"
            ))
            continue

        if raw_email in seen_emails_in_batch:
            skip_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code,
                email=raw_email,
                reason=f"Duplicate email '{raw_email}' within the uploaded file (Skipped)"
            ))
            continue

        # Database duplicate checks
        if get_employee_by_code(db, raw_code):
            skip_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code,
                email=raw_email,
                reason=f"Employee ID '{raw_code}' already exists in database (Skipped)"
            ))
            continue

        if get_employee_by_email(db, raw_email):
            skip_count += 1
            errors.append(CSVImportErrorDetail(
                row_number=row_idx,
                employee_id=raw_code,
                email=raw_email,
                reason=f"Email '{raw_email}' already registered to another employee in database (Skipped)"
            ))
            continue

        # Parse optional fields
        company = (row.get("company") or "Nexus Tech").strip()
        dept = (row.get("department") or "Operations").strip()
        role = (row.get("designation") or row.get("role") or "Staff Member").strip()

        tz = (row.get("timezone") or "Asia/Kolkata").strip()
        if tz not in available_tz and tz not in ("UTC", "GMT", "IST"):
            tz = "Asia/Kolkata"

        status_val = (row.get("employment_status") or row.get("status") or "Active").strip().title()
        if status_val not in VALID_STATUSES:
            status_val = "Active"

        seen_codes_in_batch.add(raw_code)
        seen_emails_in_batch.add(raw_email)

        emp = Employee(
            employee_id=raw_code,
            full_name=raw_name,
            email=raw_email,
            company=company,
            department=dept,
            designation=role,
            timezone=tz,
            employment_status=status_val,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        new_employees.append(emp)
        success_count += 1

    # Bulk commit valid records
    if new_employees:
        db.add_all(new_employees)
        db.commit()
        logger.info(f"CSV import completed: {len(new_employees)} new employees added to database.")

    return CSVImportSummary(
        total_rows=total_rows,
        successfully_imported=success_count,
        skipped_records=skip_count,
        failed_records=fail_count,
        errors=errors
    )


def export_employees_to_csv(
    db: Session,
    search: Optional[str] = None,
    department: Optional[str] = None
) -> str:
    """
    Exports filtered employees from database to CSV string format.
    """
    employees, _ = list_employees(db, search=search, department=department, limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)

    # Standard corporate headers
    writer.writerow([
        "employee_id",
        "full_name",
        "email",
        "company",
        "department",
        "designation",
        "timezone",
        "employment_status",
        "created_at"
    ])

    for emp in employees:
        writer.writerow([
            emp.employee_id,
            emp.full_name,
            emp.email,
            emp.company,
            emp.department,
            emp.designation,
            emp.timezone,
            emp.employment_status,
            emp.created_at.strftime("%Y-%m-%d %H:%M:%S") if emp.created_at else ""
        ])

    return output.getvalue()
