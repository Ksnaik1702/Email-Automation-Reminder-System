"""
FastAPI Email Campaign Management Router.
Provides endpoints for campaign lifecycle, multi-recipient targeting,
department cohort filtering, and recipient-level email previews.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Employee
from api.schemas import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignDetailResponse,
    CampaignListResponse, CampaignStatsResponse, CampaignRecipientResponse,
    CampaignAddRecipientsRequest, TemplatePreviewResponse
)
from src.services import campaign_service

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def serialize_campaign_summary(camp) -> CampaignResponse:
    """Helper to convert Campaign ORM to summary response with counts."""
    return CampaignResponse(
        id=camp.id,
        campaign_name=camp.campaign_name,
        description=camp.description,
        category=camp.category,
        template_id=camp.template_id,
        status=camp.status,
        scheduled_at=camp.scheduled_at,
        created_at=camp.created_at,
        updated_at=camp.updated_at,
        recipient_count=len(camp.recipients),
        template_name=camp.template.template_name if camp.template else None
    )


def serialize_campaign_detail(camp) -> CampaignDetailResponse:
    """Helper to convert Campaign ORM to full detail response with recipients."""
    recipients_out = []
    for r in camp.recipients:
        recipients_out.append(CampaignRecipientResponse(
            id=r.id,
            campaign_id=r.campaign_id,
            employee_id=r.employee_id,
            recipient_email=r.recipient_email,
            status=r.status,
            employee_name=r.employee.full_name if r.employee else None,
            department=r.employee.department if r.employee else None,
            designation=r.employee.designation if r.employee else None
        ))

    return CampaignDetailResponse(
        id=camp.id,
        campaign_name=camp.campaign_name,
        description=camp.description,
        category=camp.category,
        template_id=camp.template_id,
        status=camp.status,
        scheduled_at=camp.scheduled_at,
        created_at=camp.created_at,
        updated_at=camp.updated_at,
        recipient_count=len(camp.recipients),
        template_name=camp.template.template_name if camp.template else None,
        template=camp.template,
        recipients=recipients_out
    )


@router.get("/stats", response_model=CampaignStatsResponse)
def get_campaign_overview_metrics(db: Session = Depends(get_db)):
    """Returns overview metrics: total campaigns, status distribution, and total recipients."""
    return campaign_service.get_campaign_stats(db)


@router.get("", response_model=CampaignListResponse)
def list_email_campaigns(
    search: Optional[str] = Query(None, description="Search term in campaign title or description"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, READY, SCHEDULED, COMPLETED, CANCELLED)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Lists email campaigns with search query and status filtering."""
    items, total = campaign_service.list_campaigns(
        db,
        search=search,
        status=status,
        category=category,
        skip=skip,
        limit=limit
    )
    summaries = [serialize_campaign_summary(c) for c in items]
    return CampaignListResponse(items=summaries, total=total)


@router.post("", response_model=CampaignDetailResponse, status_code=status.HTTP_201_CREATED)
def create_email_campaign(
    campaign_in: CampaignCreate,
    db: Session = Depends(get_db)
):
    """Creates a new campaign, connects template, and targets recipient employees."""
    try:
        new_camp = campaign_service.create_campaign(db, campaign_in)
        return serialize_campaign_detail(new_camp)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign_details(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves full campaign details including template and recipient cohort."""
    camp = campaign_service.get_campaign(db, campaign_id)
    if not camp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found."
        )
    return serialize_campaign_detail(camp)


@router.put("/{campaign_id}", response_model=CampaignDetailResponse)
def update_email_campaign(
    campaign_id: int,
    campaign_in: CampaignUpdate,
    db: Session = Depends(get_db)
):
    """Updates campaign parameters and synchronizes recipient list."""
    try:
        updated = campaign_service.update_campaign(db, campaign_id, campaign_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found."
            )
        return serialize_campaign_detail(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{campaign_id}", status_code=status.HTTP_200_OK)
def delete_email_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Deletes a campaign and cascades associated recipients."""
    deleted = campaign_service.delete_campaign(db, campaign_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found."
        )
    return {"message": f"Campaign {campaign_id} deleted successfully.", "deleted": True}


@router.post("/{campaign_id}/recipients", status_code=status.HTTP_200_OK)
def add_recipients(
    campaign_id: int,
    req: CampaignAddRecipientsRequest,
    db: Session = Depends(get_db)
):
    """
    Adds recipients to an existing campaign.
    Supports targeting by explicit ID list or department cohort.
    """
    target_ids = list(req.employee_ids or [])

    if req.department:
        dept_emps = db.query(Employee.id).filter(Employee.department == req.department.strip()).all()
        target_ids.extend([e[0] for e in dept_emps])

    if req.all_active:
        active_emps = db.query(Employee.id).filter(Employee.employment_status == "Active").all()
        target_ids.extend([e[0] for e in active_emps])

    try:
        added_count = campaign_service.add_recipients_to_campaign(db, campaign_id, target_ids)
        return {
            "campaign_id": campaign_id,
            "added_count": added_count,
            "message": f"Successfully added {added_count} new recipients to campaign."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{campaign_id}/recipients/{employee_id}", status_code=status.HTTP_200_OK)
def remove_recipient(
    campaign_id: int,
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Removes an individual employee from a campaign recipient list."""
    removed = campaign_service.remove_recipient_from_campaign(db, campaign_id, employee_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient employee {employee_id} not found in campaign {campaign_id}."
        )
    return {"message": f"Employee {employee_id} removed from campaign {campaign_id}.", "removed": True}


@router.get("/{campaign_id}/preview/{employee_id}", response_model=TemplatePreviewResponse)
def preview_campaign_for_employee(
    campaign_id: int,
    employee_id: int,
    db: Session = Depends(get_db)
):
    """
    Renders personalized email output for an individual employee within the campaign.
    Reuses template_service.render_template_preview to guarantee zero code duplication.
    """
    try:
        preview = campaign_service.preview_campaign_for_recipient(db, campaign_id, employee_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
