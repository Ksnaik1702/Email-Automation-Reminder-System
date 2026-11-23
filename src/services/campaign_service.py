"""
Campaign Service Layer: Implements business logic, recipient targeting,
template association, preview generation, and campaign lifecycle management.
"""
from typing import List, Tuple, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from db.models import Campaign, CampaignRecipient, Employee, EmailTemplate, utc_now
from api.schemas import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignDetailResponse,
    CampaignRecipientResponse, CampaignStatsResponse, TemplatePreviewResponse,
    VALID_CAMPAIGN_STATUSES
)
from src.services import template_service
from src.logger import logger


def get_campaign(db: Session, campaign_id: int) -> Optional[Campaign]:
    """Retrieves a campaign by database primary key ID."""
    return db.query(Campaign).filter(Campaign.id == campaign_id).first()


def list_campaigns(
    db: Session,
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Campaign], int]:
    """
    Lists campaigns with optional search query, status filter, and category filter.
    Returns (items, total_count).
    """
    query = db.query(Campaign)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Campaign.campaign_name.ilike(term),
                Campaign.description.ilike(term)
            )
        )

    if status and status.strip().upper() != "ALL":
        query = query.filter(Campaign.status == status.strip().upper())

    if category and category.strip().lower() != "all":
        query = query.filter(Campaign.category == category.strip())

    total = query.count()
    items = query.order_by(Campaign.id.desc()).offset(skip).limit(limit).all()
    return items, total


def create_campaign(db: Session, campaign_in: CampaignCreate) -> Campaign:
    """
    Creates a new campaign and associates target recipient employees.
    Validates that template exists (if provided) and prevents duplicate recipients.
    """
    # 1. Validate template existence if specified
    template = None
    if campaign_in.template_id is not None:
        template = template_service.get_template(db, campaign_in.template_id)
        if not template:
            raise ValueError(f"Template with ID {campaign_in.template_id} does not exist.")

    clean_status = campaign_in.status.strip().upper()
    if clean_status not in VALID_CAMPAIGN_STATUSES:
        clean_status = "DRAFT"

    campaign = Campaign(
        campaign_name=campaign_in.campaign_name.strip(),
        description=campaign_in.description.strip() if campaign_in.description else None,
        category=campaign_in.category.strip() if campaign_in.category else "General Announcement",
        template_id=template.id if template else None,
        status=clean_status,
        scheduled_at=campaign_in.scheduled_at,
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(campaign)
    db.flush()  # Populates campaign.id

    # 2. Add recipients with deduplication
    recip_ids = campaign_in.recipient_employee_ids or getattr(campaign_in, "employee_ids", None) or []
    if recip_ids:
        unique_employee_ids = list(dict.fromkeys(recip_ids))
        employees = db.query(Employee).filter(Employee.id.in_(unique_employee_ids)).all()
        emp_map = {e.id: e for e in employees}

        for emp_id in unique_employee_ids:
            emp = emp_map.get(emp_id)
            if emp:
                recipient = CampaignRecipient(
                    campaign_id=campaign.id,
                    employee_id=emp.id,
                    recipient_email=emp.email,
                    status="Pending"
                )
                db.add(recipient)

    db.commit()
    db.refresh(campaign)
    logger.info(f"Created Campaign ID={campaign.id} ('{campaign.campaign_name}') with {len(campaign.recipients)} recipients.")
    return campaign


def update_campaign(
    db: Session,
    campaign_id: int,
    campaign_in: CampaignUpdate
) -> Optional[Campaign]:
    """
    Updates campaign metadata and synchronizes the recipient cohort.
    """
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        return None

    update_data = campaign_in.model_dump(exclude_unset=True)

    # Validate template if provided
    if "template_id" in update_data and update_data["template_id"] is not None:
        new_tmpl_id = update_data["template_id"]
        if not template_service.get_template(db, new_tmpl_id):
            raise ValueError(f"Template ID {new_tmpl_id} does not exist.")
        campaign.template_id = new_tmpl_id

    if "campaign_name" in update_data and update_data["campaign_name"]:
        campaign.campaign_name = update_data["campaign_name"].strip()

    if "description" in update_data:
        campaign.description = update_data["description"].strip() if update_data["description"] else None

    if "category" in update_data and update_data["category"]:
        campaign.category = update_data["category"].strip()

    if "status" in update_data and update_data["status"]:
        clean_status = update_data["status"].strip().upper()
        if clean_status in VALID_CAMPAIGN_STATUSES:
            campaign.status = clean_status

    if "scheduled_at" in update_data:
        campaign.scheduled_at = update_data["scheduled_at"]

    # Synchronize recipients if provided
    if "recipient_employee_ids" in update_data and update_data["recipient_employee_ids"] is not None:
        target_ids = set(update_data["recipient_employee_ids"])
        existing_recipients = {r.employee_id: r for r in campaign.recipients}

        # Remove unselected
        for emp_id, rec in list(existing_recipients.items()):
            if emp_id not in target_ids:
                db.delete(rec)

        # Add newly selected
        to_add = target_ids - set(existing_recipients.keys())
        if to_add:
            employees = db.query(Employee).filter(Employee.id.in_(to_add)).all()
            for emp in employees:
                new_rec = CampaignRecipient(
                    campaign_id=campaign.id,
                    employee_id=emp.id,
                    recipient_email=emp.email,
                    status="Pending"
                )
                db.add(new_rec)

    campaign.updated_at = utc_now()
    db.commit()
    db.refresh(campaign)
    logger.info(f"Updated Campaign ID={campaign.id} ('{campaign.campaign_name}')")
    return campaign


def delete_campaign(db: Session, campaign_id: int) -> bool:
    """
    Deletes a campaign and cascades associated recipients.
    """
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        return False

    name = campaign.campaign_name
    db.delete(campaign)
    db.commit()
    logger.info(f"Deleted Campaign ID={campaign_id} ('{name}')")
    return True


def add_recipients_to_campaign(
    db: Session,
    campaign_id: int,
    employee_ids: List[int]
) -> int:
    """
    Adds employees to a campaign, preventing duplicate entries.
    Returns count of newly added recipients.
    """
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign ID {campaign_id} not found.")

    existing_ids = {r.employee_id for r in campaign.recipients}
    unique_new_ids = [eid for eid in dict.fromkeys(employee_ids) if eid not in existing_ids]

    if not unique_new_ids:
        return 0

    employees = db.query(Employee).filter(Employee.id.in_(unique_new_ids)).all()
    added_count = 0

    for emp in employees:
        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            employee_id=emp.id,
            recipient_email=emp.email,
            status="Pending"
        )
        db.add(recipient)
        added_count += 1

    campaign.updated_at = utc_now()
    db.commit()
    logger.info(f"Added {added_count} recipients to Campaign ID={campaign_id}")
    return added_count


def remove_recipient_from_campaign(
    db: Session,
    campaign_id: int,
    employee_id: int
) -> bool:
    """
    Removes a single recipient employee from a campaign.
    """
    recipient = db.query(CampaignRecipient).filter_by(
        campaign_id=campaign_id,
        employee_id=employee_id
    ).first()

    if not recipient:
        return False

    db.delete(recipient)
    db.commit()
    logger.info(f"Removed employee ID={employee_id} from Campaign ID={campaign_id}")
    return True


def preview_campaign_for_recipient(
    db: Session,
    campaign_id: int,
    employee_id: int
) -> TemplatePreviewResponse:
    """
    Renders personalized email preview for a specific employee within the campaign.
    Reuses template_service.render_template_preview to eliminate redundant logic.
    """
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign ID {campaign_id} not found.")

    template = campaign.template
    if not template:
        raise ValueError(f"Campaign {campaign_id} has no valid associated template.")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError(f"Employee ID {employee_id} not found.")

    # Verify recipient is part of this campaign
    recipient = db.query(CampaignRecipient).filter_by(
        campaign_id=campaign_id,
        employee_id=employee_id
    ).first()
    if not recipient:
        raise ValueError(f"Employee ID {employee_id} is not a recipient in Campaign ID {campaign_id}.")

    # Event context derived from campaign
    event_ctx = {
        "event_name": campaign.campaign_name,
        "event_description": campaign.description or "Company notification briefing.",
        "event_date": campaign.scheduled_at.strftime("%B %d, %Y") if campaign.scheduled_at else "Upcoming",
        "event_time": campaign.scheduled_at.strftime("%I:%M %p UTC") if campaign.scheduled_at else "TBD"
    }

    return template_service.render_template_preview(
        db=db,
        subject_tmpl=template.subject,
        body_tmpl=template.body,
        employee_id=employee.id,
        event_context=event_ctx
    )


def get_campaign_stats(db: Session) -> CampaignStatsResponse:
    """
    Calculates overview metrics for the Campaign Management Studio.
    Returns typed CampaignStatsResponse object.
    """
    total = db.query(Campaign).count()
    draft = db.query(Campaign).filter(Campaign.status == "DRAFT").count()
    ready = db.query(Campaign).filter(Campaign.status == "READY").count()
    scheduled = db.query(Campaign).filter(Campaign.status == "SCHEDULED").count()
    completed = db.query(Campaign).filter(Campaign.status == "COMPLETED").count()
    total_recipients = db.query(CampaignRecipient).count()

    return CampaignStatsResponse(
        total_campaigns=total,
        draft_campaigns=draft,
        ready_campaigns=ready,
        scheduled_campaigns=scheduled,
        completed_campaigns=completed,
        cancelled_campaigns=db.query(Campaign).filter(Campaign.status == "CANCELLED").count(),
        total_recipients_targeted=total_recipients
    )
