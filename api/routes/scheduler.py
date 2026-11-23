"""
FastAPI Scheduler & Background Worker Router.
Provides endpoints for monitoring scheduling status, inspecting due jobs,
and triggering manual processing cycles.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Campaign, ReminderJob, MessageLog
from src.services import scheduling_service
from src.timezone_utils import DEFAULT_TIMEZONE

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/status")
def get_scheduler_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns scheduling engine status, counts of pending/due work, and configuration.
    """
    due_campaigns = scheduling_service.get_due_campaigns(db)
    due_reminders = scheduling_service.get_due_reminders(db)

    pending_campaigns = db.query(Campaign).filter(Campaign.status.in_(["READY", "SCHEDULED"])).count()
    active_reminders = db.query(ReminderJob).filter(ReminderJob.status == "Active").count()
    total_executions = db.query(MessageLog).count()

    return {
        "status": "online",
        "default_timezone": DEFAULT_TIMEZONE,
        "simulation_mode": True,
        "due_campaigns_count": len(due_campaigns),
        "due_reminders_count": len(due_reminders),
        "total_scheduled_campaigns": pending_campaigns,
        "total_active_reminders": active_reminders,
        "total_message_executions": total_executions
    }


@router.post("/trigger", status_code=status.HTTP_200_OK)
def trigger_scheduler_cycle(
    simulation: bool = Query(True, description="Run in simulation mode (default: True)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually triggers one background evaluation cycle to process due campaigns & reminders.
    """
    result = scheduling_service.run_pending_jobs(db=db, simulation_mode=simulation)
    return {
        "message": "Scheduler cycle executed successfully.",
        "result": result
    }
