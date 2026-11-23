"""
Pydantic Schemas for API validation, request parsing, and response serialization.
Enforces strict email regex, timezone validation, and data formatting.
"""
import re
import zoneinfo
import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
VALID_STATUSES = {"Active", "Inactive", "On Leave", "Terminated"}


class EmployeeBase(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=50, description="Unique corporate employee code")
    full_name: str = Field(..., min_length=2, max_length=100, description="Employee full name")
    email: str = Field(..., description="Unique email address")
    company: Optional[str] = Field("Nexus Tech", max_length=100)
    department: Optional[str] = Field("Operations", max_length=100)
    designation: Optional[str] = Field("Staff Member", max_length=100)
    timezone: str = Field("Asia/Kolkata", max_length=50)
    employment_status: str = Field("Active", max_length=20)

    @field_validator("email")
    def validate_email_syntax(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address syntax: '{v}'")
        return clean

    @field_validator("timezone")
    def validate_timezone_name(cls, v: str) -> str:
        clean = v.strip()
        available = zoneinfo.available_timezones()
        if clean not in available:
            # Common aliases
            if clean in ("UTC", "GMT", "IST"):
                return clean
            raise ValueError(f"Invalid IANA timezone '{v}'. Must be a recognized timezone name (e.g., 'Asia/Kolkata', 'America/New_York', 'UTC').")
        return clean

    @field_validator("employment_status")
    def validate_employment_status(cls, v: str) -> str:
        clean = v.strip().title()
        if clean not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed values: {sorted(list(VALID_STATUSES))}")
        return clean


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    timezone: Optional[str] = None
    employment_status: Optional[str] = None

    @field_validator("email")
    def validate_optional_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().lower()
            if not EMAIL_REGEX.match(clean):
                raise ValueError(f"Invalid email format: '{v}'")
            return clean
        return v

    @field_validator("timezone")
    def validate_optional_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if clean not in zoneinfo.available_timezones() and clean not in ("UTC", "GMT", "IST"):
                raise ValueError(f"Invalid timezone: '{v}'")
            return clean
        return v

    @field_validator("employment_status")
    def validate_optional_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().title()
            if clean not in VALID_STATUSES:
                raise ValueError(f"Status must be one of: {sorted(list(VALID_STATUSES))}")
            return clean
        return v


class EmployeeResponse(EmployeeBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int


class EmployeeStatsResponse(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    departments_count: int
    department_distribution: Dict[str, int]


class CSVImportErrorDetail(BaseModel):
    row_number: int
    employee_id: Optional[str] = None
    email: Optional[str] = None
    reason: str


class CSVImportSummary(BaseModel):
    total_rows: int
    successfully_imported: int
    skipped_records: int
    failed_records: int
    errors: List[CSVImportErrorDetail]
