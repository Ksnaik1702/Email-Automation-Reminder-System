"""
Template Management & Jinja2 Dynamic Personalization Service.
Implements secure sandboxed rendering, variable extraction, syntax validation,
HTML to plain-text conversion, and template lifecycle CRUD operations.
"""
import re
import html
import datetime
from typing import List, Tuple, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_

from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.meta import find_undeclared_variables

from db.models import EmailTemplate, Employee, utc_now
from api.schemas import (
    EmailTemplateCreate, EmailTemplateUpdate, TemplatePreviewResponse,
    VALID_TEMPLATE_CATEGORIES
)
from src.logger import logger

# Secure Sandboxed Jinja2 Environment (prevents access to dangerous Python builtins/os)
sandboxed_env = SandboxedEnvironment(
    autoescape=True,
    undefined=StrictUndefined
)

# Canonical variable catalog with descriptions and fallback default mock values
VARIABLE_CATALOG: Dict[str, Dict[str, str]] = {
    # Employee Variables
    "name": {
        "group": "Employee",
        "description": "Recipient full name",
        "sample": "Aarav Sharma"
    },
    "email": {
        "group": "Employee",
        "description": "Recipient corporate email",
        "sample": "aarav.sharma@example.com"
    },
    "employee_id": {
        "group": "Employee",
        "description": "Recipient employee code",
        "sample": "EMP-101"
    },
    "department": {
        "group": "Employee",
        "description": "Recipient department",
        "sample": "Engineering"
    },
    "designation": {
        "group": "Employee",
        "description": "Recipient job title",
        "sample": "Senior DevOps Engineer"
    },
    "company": {
        "group": "Employee",
        "description": "Recipient company name",
        "sample": "Nexus Tech"
    },

    # Event Variables
    "event_name": {
        "group": "Event",
        "description": "Title of the meeting or webinar",
        "sample": "Quarterly Technology Review & Roadmap"
    },
    "event_date": {
        "group": "Event",
        "description": "Scheduled date of the event",
        "sample": "November 28, 2026"
    },
    "event_time": {
        "group": "Event",
        "description": "Scheduled time with timezone",
        "sample": "10:30 AM IST"
    },
    "event_location": {
        "group": "Event",
        "description": "Physical room or virtual venue",
        "sample": "Conference Room Delta / Virtual Room A"
    },
    "meeting_link": {
        "group": "Event",
        "description": "Join URL for conference",
        "sample": "https://meet.google.com/abc-defg-hij"
    },
    "event_description": {
        "group": "Event",
        "description": "Summary or agenda details",
        "sample": "Quarterly milestone review and sprint retrospective."
    },

    # Sender Variables
    "sender_name": {
        "group": "Sender",
        "description": "Name of the sending manager or system",
        "sample": "Executive Operations Desk"
    },
    "sender_department": {
        "group": "Sender",
        "description": "Department issuing the reminder",
        "sample": "People Operations & HR"
    },
    "company_name": {
        "group": "Sender",
        "description": "Organization company name",
        "sample": "Nexus Tech"
    }
}


def get_default_sample_context() -> Dict[str, str]:
    """Returns sample context for all recognized variables."""
    return {k: v["sample"] for k, v in VARIABLE_CATALOG.items()}


def convert_html_to_plain_text(html_content: str) -> str:
    """
    Separates HTML content into clean plain-text fallback content.
    Transforms anchor links, headings, and paragraph breaks.
    """
    if not html_content:
        return ""

    text = html_content
    # Convert <a href="url">Label</a> to "Label (url)"
    text = re.sub(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'\2 (\1)', text, flags=re.IGNORECASE)

    # Convert line breaks and paragraph closings to newlines
    text = re.sub(r'<(?:br|br\s*/)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|tr|h[1-6])>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<hr[^>]*>', '\n----------------------------------------\n', text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Unescape HTML entities (&amp;, &bull;, etc.)
    text = html.unescape(text)

    # Normalize multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def validate_template_syntax(subject_tmpl: str, body_tmpl: str) -> Tuple[bool, Optional[str], Set[str]]:
    """
    Validates Jinja2 template syntax in subject and body.
    Returns: (is_valid, error_message, set_of_variables_used)
    """
    used_vars = set()
    try:
        # Validate Subject AST
        subject_ast = sandboxed_env.parse(subject_tmpl)
        used_vars.update(find_undeclared_variables(subject_ast))

        # Validate Body AST
        body_ast = sandboxed_env.parse(body_tmpl)
        used_vars.update(find_undeclared_variables(body_ast))

        return True, None, used_vars
    except TemplateSyntaxError as e:
        err = f"Jinja2 Syntax Error at line {e.lineno}: {e.message}"
        return False, err, used_vars
    except Exception as e:
        return False, f"Invalid template: {str(e)}", used_vars


def render_template_preview(
    db: Session,
    subject_tmpl: str,
    body_tmpl: str,
    employee_id: Optional[int] = None,
    event_context: Optional[Dict[str, str]] = None,
    sender_context: Optional[Dict[str, str]] = None
) -> TemplatePreviewResponse:
    """
    Renders email subject and body using Jinja2 SandboxedEnvironment.
    Supports previewing with real DB employee records or default mock data.
    """
    # 1. Validate Syntax
    is_valid, syntax_error, used_vars = validate_template_syntax(subject_tmpl, body_tmpl)
    if not is_valid:
        return TemplatePreviewResponse(
            rendered_subject=subject_tmpl,
            rendered_html=body_tmpl,
            plain_text_fallback=convert_html_to_plain_text(body_tmpl),
            variables_used=sorted(list(used_vars)),
            missing_variables=[],
            is_valid=False,
            validation_error=syntax_error
        )

    # 2. Build Context Dictionary
    context: Dict[str, Any] = get_default_sample_context()

    # If specific employee requested from DB, override employee variables
    if employee_id:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if emp:
            context.update({
                "name": emp.full_name,
                "email": emp.email,
                "employee_id": emp.employee_id,
                "department": emp.department or "Operations",
                "designation": emp.designation or "Associate",
                "company": emp.company or "Nexus Tech"
            })

    # Apply custom overrides
    if event_context:
        context.update(event_context)
    if sender_context:
        context.update(sender_context)

    # 3. Detect Missing Required Variables
    missing_vars = [var for var in used_vars if var not in context or context[var] is None or context[var] == ""]

    if missing_vars:
        error_msg = f"Undefined / missing required variable(s): {', '.join(sorted(missing_vars))}"
        return TemplatePreviewResponse(
            rendered_subject=subject_tmpl,
            rendered_html=body_tmpl,
            plain_text_fallback=convert_html_to_plain_text(body_tmpl),
            variables_used=sorted(list(used_vars)),
            missing_variables=sorted(missing_vars),
            is_valid=False,
            validation_error=error_msg
        )

    # 4. Render Subject & HTML Body
    try:
        subject_template_obj = sandboxed_env.from_string(subject_tmpl)
        rendered_subject = subject_template_obj.render(**context)

        body_template_obj = sandboxed_env.from_string(body_tmpl)
        rendered_html = body_template_obj.render(**context)
        plain_fallback = convert_html_to_plain_text(rendered_html)

        return TemplatePreviewResponse(
            rendered_subject=rendered_subject,
            rendered_html=rendered_html,
            plain_text_fallback=plain_fallback,
            variables_used=sorted(list(used_vars)),
            missing_variables=[],
            is_valid=True,
            validation_error=None
        )
    except UndefinedError as e:
        return TemplatePreviewResponse(
            rendered_subject=subject_tmpl,
            rendered_html=body_tmpl,
            plain_text_fallback=convert_html_to_plain_text(body_tmpl),
            variables_used=sorted(list(used_vars)),
            missing_variables=sorted(list(used_vars)),
            is_valid=False,
            validation_error=f"Template execution failed: {str(e)}"
        )
    except Exception as e:
        return TemplatePreviewResponse(
            rendered_subject=subject_tmpl,
            rendered_html=body_tmpl,
            plain_text_fallback=convert_html_to_plain_text(body_tmpl),
            variables_used=sorted(list(used_vars)),
            missing_variables=[],
            is_valid=False,
            validation_error=f"Rendering error: {str(e)}"
        )


# ----------------- CRUD Operations ----------------- #

def get_template(db: Session, template_id: int) -> Optional[EmailTemplate]:
    """Retrieves an email template by ID."""
    return db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()


def get_template_by_name(db: Session, name: str) -> Optional[EmailTemplate]:
    """Retrieves an email template by name."""
    return db.query(EmailTemplate).filter(EmailTemplate.template_name == name.strip()).first()


def list_templates(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[EmailTemplate], int]:
    """
    Lists email templates with search query and category filtering.
    """
    query = db.query(EmailTemplate)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                EmailTemplate.template_name.ilike(term),
                EmailTemplate.subject.ilike(term),
                EmailTemplate.body.ilike(term)
            )
        )

    if category and category.strip().lower() != "all":
        query = query.filter(EmailTemplate.category == category.strip())

    total = query.count()
    items = query.order_by(EmailTemplate.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_template(db: Session, template_in: EmailTemplateCreate) -> EmailTemplate:
    """
    Creates a new email template after validating syntax and name uniqueness.
    """
    clean_name = template_in.template_name.strip()
    if get_template_by_name(db, clean_name):
        raise ValueError(f"Template with name '{clean_name}' already exists.")

    is_valid, err_msg, _ = validate_template_syntax(template_in.subject, template_in.body)
    if not is_valid:
        raise ValueError(f"Template validation failed: {err_msg}")

    tmpl = EmailTemplate(
        template_name=clean_name,
        category=template_in.category,
        subject=template_in.subject.strip(),
        body=template_in.body.strip(),
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    logger.info(f"Created EmailTemplate ID={tmpl.id} ('{tmpl.template_name}')")
    return tmpl


def update_template(
    db: Session,
    template_id: int,
    template_in: EmailTemplateUpdate
) -> Optional[EmailTemplate]:
    """
    Updates an existing email template with syntax and uniqueness checks.
    """
    tmpl = get_template(db, template_id)
    if not tmpl:
        return None

    update_data = template_in.model_dump(exclude_unset=True)

    if "template_name" in update_data and update_data["template_name"]:
        new_name = update_data["template_name"].strip()
        if new_name != tmpl.template_name:
            existing = get_template_by_name(db, new_name)
            if existing and existing.id != tmpl.id:
                raise ValueError(f"Template name '{new_name}' is already in use.")
            tmpl.template_name = new_name

    subject_to_validate = update_data.get("subject", tmpl.subject)
    body_to_validate = update_data.get("body", tmpl.body)

    is_valid, err_msg, _ = validate_template_syntax(subject_to_validate, body_to_validate)
    if not is_valid:
        raise ValueError(f"Template validation failed: {err_msg}")

    for field, val in update_data.items():
        if field != "template_name" and val is not None:
            setattr(tmpl, field, val)

    tmpl.updated_at = utc_now()
    db.commit()
    db.refresh(tmpl)
    logger.info(f"Updated EmailTemplate ID={tmpl.id}")
    return tmpl


def delete_template(db: Session, template_id: int) -> bool:
    """
    Deletes an email template.
    """
    tmpl = get_template(db, template_id)
    if not tmpl:
        return False

    # Check if any campaigns rely on this template
    if tmpl.campaigns:
        raise ValueError(f"Cannot delete template '{tmpl.template_name}' because it is linked to {len(tmpl.campaigns)} campaign(s).")

    name = tmpl.template_name
    db.delete(tmpl)
    db.commit()
    logger.info(f"Deleted EmailTemplate ID={template_id} ('{name}')")
    return True


def duplicate_template(db: Session, template_id: int) -> Optional[EmailTemplate]:
    """
    Clones an existing template with a distinct non-colliding name.
    """
    original = get_template(db, template_id)
    if not original:
        return None

    # Generate unique copy name
    base_name = original.template_name
    counter = 1
    new_name = f"{base_name} (Copy)"
    while get_template_by_name(db, new_name):
        counter += 1
        new_name = f"{base_name} (Copy {counter})"

    clone = EmailTemplate(
        template_name=new_name,
        category=original.category,
        subject=original.subject,
        body=original.body,
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(clone)
    db.commit()
    db.refresh(clone)
    logger.info(f"Duplicated template ID={template_id} -> New ID={clone.id} ('{clone.template_name}')")
    return clone
