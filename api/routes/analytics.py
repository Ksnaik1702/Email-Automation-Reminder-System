"""
FastAPI Analytics & Reporting Router.
Exposes REST endpoints for the Delivery Analytics & Reporting Dashboard:
overview KPIs, daily execution trends, status distribution, campaign performance,
failure root-cause analysis, paginated execution log, and CSV exports.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from fastapi.params import Query as QueryType
from sqlalchemy.orm import Session

from db.database import get_db
from api.schemas import (
    AnalyticsOverviewResponse,
    TrendItem,
    StatusDistributionItem,
    CampaignPerformanceItem,
    FailureAnalysisResponse,
    RecentActivityResponse
)
from src.services import analytics_service
from src.logger import logger

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _val(param, default=None):
    """Unwraps default Query instances when route functions are called directly in unit tests."""
    return default if isinstance(param, QueryType) else param


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    campaign_id: Optional[int] = Query(None, description="Filter by campaign primary key ID"),
    execution_mode: Optional[str] = Query(None, description="Filter by mode: SIMULATION or LIVE_SMTP"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    search: Optional[str] = Query(None, description="Search recipient email or subject"),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated KPI metrics across the execution history.
    Strictly distinguishes SIMULATION from LIVE_SMTP dispatches and handles empty datasets.
    """
    data = analytics_service.get_overview_kpis(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date),
        campaign_id=_val(campaign_id),
        execution_mode=_val(execution_mode),
        status=_val(status),
        search=_val(search)
    )
    return data


@router.get("/trends", response_model=List[TrendItem])
def get_execution_trends(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO 8601)"),
    campaign_id: Optional[int] = Query(None, description="Filter by campaign ID"),
    execution_mode: Optional[str] = Query(None, description="Filter by mode"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search recipient or subject"),
    db: Session = Depends(get_db)
):
    """
    Returns daily execution volume grouped by date, splitting simulated and live dispatches.
    """
    trends = analytics_service.get_execution_trends(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date),
        campaign_id=_val(campaign_id),
        execution_mode=_val(execution_mode),
        status=_val(status),
        search=_val(search)
    )
    return trends


@router.get("/status-distribution", response_model=List[StatusDistributionItem])
def get_status_distribution(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    campaign_id: Optional[int] = Query(None, description="Campaign filter"),
    execution_mode: Optional[str] = Query(None, description="Execution mode filter"),
    status: Optional[str] = Query(None, description="Execution status filter"),
    search: Optional[str] = Query(None, description="Search term"),
    db: Session = Depends(get_db)
):
    """
    Returns delivery status breakdown with exact counts and calculated percentages.
    """
    distribution = analytics_service.get_status_distribution(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date),
        campaign_id=_val(campaign_id),
        execution_mode=_val(execution_mode),
        status=_val(status),
        search=_val(search)
    )
    return distribution


@router.get("/campaign-performance", response_model=List[CampaignPerformanceItem])
def get_campaign_performance(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    db: Session = Depends(get_db)
):
    """
    Returns campaign-by-campaign delivery statistics, including target recipient counts,
    simulated runs, live dispatches, failures, and uncertain outcomes.
    """
    performance = analytics_service.get_campaign_performance(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date)
    )
    return performance


@router.get("/failures", response_model=FailureAnalysisResponse)
def get_failure_analysis(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    campaign_id: Optional[int] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
):
    """
    Returns root-cause failure breakdown grouped by error category, plus top 10 recurring error messages.
    """
    analysis = analytics_service.get_failure_analysis(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date),
        campaign_id=_val(campaign_id)
    )
    return analysis


@router.get("/recent-activity", response_model=RecentActivityResponse)
def get_recent_activity(
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    campaign_id: Optional[int] = Query(None, description="Campaign ID filter"),
    execution_mode: Optional[str] = Query(None, description="Mode filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    search: Optional[str] = Query(None, description="Search recipient email or subject"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Returns paginated execution logs sorted chronologically descending.
    Includes campaign names, reminder titles, attempt counts, and message identifiers.
    """
    items, total_count, total_pages = analytics_service.get_recent_activity(
        db=db,
        start_date=_val(start_date),
        end_date=_val(end_date),
        campaign_id=_val(campaign_id),
        execution_mode=_val(execution_mode),
        status=_val(status),
        search=_val(search),
        page=_val(page, 1),
        page_size=_val(page_size, 20)
    )
    return {
        "items": items,
        "total_count": total_count,
        "page": _val(page, 1),
        "page_size": _val(page_size, 20),
        "total_pages": total_pages
    }


@router.get("/export")
def export_analytics_csv(
    export_type: str = Query("complete", description="Export type: complete, campaigns, failures, or uncertain"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    campaign_id: Optional[int] = Query(None, description="Campaign filter"),
    execution_mode: Optional[str] = Query(None, description="Mode filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    search: Optional[str] = Query(None, description="Search filter"),
    db: Session = Depends(get_db)
):
    """
    Generates and downloads a CSV report for audit compliance, campaign review,
    or failure diagnostics. Never exposes passwords, API tokens, or credentials.
    """
    try:
        csv_data, filename = analytics_service.export_analytics_csv(
            db=db,
            export_type=_val(export_type, "complete"),
            start_date=_val(start_date),
            end_date=_val(end_date),
            campaign_id=_val(campaign_id),
            execution_mode=_val(execution_mode),
            status=_val(status),
            search=_val(search)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
