"""
FastAPI Email Template Management Router.
Exposes endpoints for template CRUD, category filtering, variable catalog,
template cloning, and real-time Jinja2 sandboxed rendering.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from db.database import get_db
from api.schemas import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    EmailTemplateListResponse, TemplatePreviewRequest, TemplatePreviewResponse,
    VALID_TEMPLATE_CATEGORIES
)
from src.services import template_service

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/categories", response_model=List[str])
def list_template_categories():
    """Returns the list of valid enterprise email template categories."""
    return VALID_TEMPLATE_CATEGORIES


@router.get("/variables")
def get_variable_reference_catalog():
    """
    Returns reference catalog of all supported Jinja2 template variables
    grouped by Employee, Event, and Sender with descriptions and sample values.
    """
    return template_service.VARIABLE_CATALOG


@router.post("/preview", response_model=TemplatePreviewResponse)
def render_template_live_preview(
    preview_req: TemplatePreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Renders live email subject and HTML body with variable replacement,
    plain-text fallback, and strict syntax/undefined-variable validation.
    """
    result = template_service.render_template_preview(
        db=db,
        subject_tmpl=preview_req.subject,
        body_tmpl=preview_req.body,
        employee_id=preview_req.employee_id,
        event_context=preview_req.event_context,
        sender_context=preview_req.sender_context
    )
    return result


@router.get("", response_model=EmailTemplateListResponse)
def list_email_templates(
    search: Optional[str] = Query(None, description="Search term in template name or subject"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Lists email templates with search query and category filtering."""
    items, total = template_service.list_templates(
        db,
        search=search,
        category=category,
        skip=skip,
        limit=limit
    )
    return EmailTemplateListResponse(items=items, total=total)


@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_email_template(
    template_in: EmailTemplateCreate,
    db: Session = Depends(get_db)
):
    """Creates a new email template after validating syntax and uniqueness."""
    try:
        new_tmpl = template_service.create_template(db, template_in)
        return new_tmpl
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{template_id}", response_model=EmailTemplateResponse)
def get_email_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves an individual template by ID."""
    tmpl = template_service.get_template(db, template_id)
    if not tmpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found."
        )
    return tmpl


@router.put("/{template_id}", response_model=EmailTemplateResponse)
def update_email_template(
    template_id: int,
    template_in: EmailTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Updates an email template."""
    try:
        updated = template_service.update_template(db, template_id, template_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found."
            )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{template_id}", status_code=status.HTTP_200_OK)
def delete_email_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Deletes an email template if not linked to active campaigns."""
    try:
        deleted = template_service.delete_template(db, template_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found."
            )
        return {"message": f"Template {template_id} deleted successfully.", "deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{template_id}/duplicate", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
def duplicate_email_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Clones an existing email template with a copy suffix."""
    cloned = template_service.duplicate_template(db, template_id)
    if not cloned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found."
        )
    return cloned
