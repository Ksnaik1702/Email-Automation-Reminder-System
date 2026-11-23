"""
Pydantic Schemas for API validation, request parsing, and response serialization.
Enforces strict email regex, timezone validation, and data formatting.
"""
import re
import zoneinfo
import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

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


# ----------------- Email Template Schemas ----------------- #

VALID_TEMPLATE_CATEGORIES = [
    "Technical Training",
    "Employee Onboarding",
    "Meeting Invitation",
    "Training Reminder",
    "Performance Review",
    "Webinar Invitation",
    "General Announcement",
    "Task Deadline",
    "Other"
]


class EmailTemplateBase(BaseModel):
    template_name: str = Field(..., min_length=2, max_length=100, description="Unique template name")
    category: str = Field("General Announcement", description="Template category")
    subject: str = Field(..., min_length=2, max_length=255, description="Email subject template")
    body: str = Field(..., min_length=5, description="HTML / text email body with Jinja2 placeholders")

    @field_validator("category")
    def validate_category(cls, v: str) -> str:
        clean = v.strip()
        if clean not in VALID_TEMPLATE_CATEGORIES:
            # Allow fallback if close
            for cat in VALID_TEMPLATE_CATEGORIES:
                if cat.lower() == clean.lower():
                    return cat
            raise ValueError(f"Invalid category '{v}'. Allowed categories: {VALID_TEMPLATE_CATEGORIES}")
        return clean


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=2, max_length=255)
    body: Optional[str] = Field(None, min_length=5)

    @field_validator("category")
    def validate_optional_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            for cat in VALID_TEMPLATE_CATEGORIES:
                if cat.lower() == clean.lower():
                    return cat
            if clean not in VALID_TEMPLATE_CATEGORIES:
                raise ValueError(f"Invalid category '{v}'. Allowed: {VALID_TEMPLATE_CATEGORIES}")
            return clean
        return v


class EmailTemplateResponse(EmailTemplateBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class EmailTemplateListResponse(BaseModel):
    items: List[EmailTemplateResponse]
    total: int


class TemplatePreviewRequest(BaseModel):
    subject: str = Field(..., description="Subject template to render")
    body: str = Field(..., description="Body template to render")
    employee_id: Optional[int] = Field(None, description="Optional employee ID to render with real DB record")
    event_context: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom event variables")
    sender_context: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom sender variables")


class TemplatePreviewResponse(BaseModel):
    rendered_subject: str
    rendered_html: str
    plain_text_fallback: str
    variables_used: List[str]
    missing_variables: List[str]
    is_valid: bool
    validation_error: Optional[str] = None


# ----------------- Campaign Schemas ----------------- #

VALID_CAMPAIGN_STATUSES = ["DRAFT", "READY", "SCHEDULED", "COMPLETED", "CANCELLED"]


class CampaignRecipientResponse(BaseModel):
    id: int
    campaign_id: int
    employee_id: int
    recipient_email: str
    status: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignBase(BaseModel):
    campaign_name: str = Field(..., min_length=2, max_length=150, description="Campaign title")
    description: Optional[str] = Field(None, description="Campaign description / notes")
    category: Optional[str] = Field("General Announcement", max_length=50)
    template_id: Optional[int] = Field(None, description="Optional ID of EmailTemplate to use")
    status: str = Field("DRAFT", description="Campaign lifecycle status")
    scheduled_at: Optional[datetime.datetime] = Field(None, description="Planned dispatch datetime in UTC")

    @field_validator("status")
    def validate_campaign_status(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in VALID_CAMPAIGN_STATUSES:
            raise ValueError(f"Invalid campaign status '{v}'. Allowed values: {VALID_CAMPAIGN_STATUSES}")
        return clean


class CampaignCreate(CampaignBase):
    recipient_employee_ids: List[int] = Field(default_factory=list, description="List of employee IDs to target")
    employee_ids: Optional[List[int]] = Field(None, description="Alias for recipient_employee_ids")

    @model_validator(mode="before")
    @classmethod
    def reconcile_employee_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            emp_ids = data.get("employee_ids")
            recip_ids = data.get("recipient_employee_ids")
            if emp_ids is not None and not recip_ids:
                data["recipient_employee_ids"] = emp_ids
        return data


class CampaignUpdate(BaseModel):
    campaign_name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = None
    template_id: Optional[int] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime.datetime] = None
    recipient_employee_ids: Optional[List[int]] = None
    employee_ids: Optional[List[int]] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_employee_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            emp_ids = data.get("employee_ids")
            recip_ids = data.get("recipient_employee_ids")
            if emp_ids is not None and recip_ids is None:
                data["recipient_employee_ids"] = emp_ids
        return data

    @field_validator("status")
    def validate_optional_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().upper()
            if clean not in VALID_CAMPAIGN_STATUSES:
                raise ValueError(f"Invalid status '{v}'. Allowed: {VALID_CAMPAIGN_STATUSES}")
            return clean
        return v


class CampaignResponse(CampaignBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    recipient_count: int = 0
    template_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignDetailResponse(CampaignResponse):
    template: Optional[EmailTemplateResponse] = None
    recipients: List[CampaignRecipientResponse] = []


class CampaignListResponse(BaseModel):
    items: List[CampaignResponse]
    total: int


class CampaignStatsResponse(BaseModel):
    total_campaigns: int
    draft_campaigns: int
    ready_campaigns: int
    scheduled_campaigns: int
    completed_campaigns: int
    total_recipients_targeted: int


class CampaignAddRecipientsRequest(BaseModel):
    employee_ids: Optional[List[int]] = None
    department: Optional[str] = None
    all_active: Optional[bool] = False


