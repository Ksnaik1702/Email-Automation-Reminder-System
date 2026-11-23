"""
FastAPI Scheduler & Background Worker Router.
Provides endpoints for monitoring scheduling status, inspecting due jobs,
verifying SMTP connections safely, and triggering evaluation cycles.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Campaign, ReminderJob, MessageLog
from src.services import scheduling_service
from src.smtp_client import SMTPClient, SMTPConfig
from src.timezone_utils import DEFAULT_TIMEZONE
from src.logger import logger

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/status")
def get_scheduler_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns scheduling engine status, counts of pending/due work, retry queue, and SMTP readiness.
    """
    due_campaigns = scheduling_service.get_due_campaigns(db)
    due_reminders = scheduling_service.get_due_reminders(db)

    pending_campaigns = db.query(Campaign).filter(Campaign.status.in_(["READY", "SCHEDULED"])).count()
    active_reminders = db.query(ReminderJob).filter(ReminderJob.status == "Active").count()
    total_executions = db.query(MessageLog).count()
    pending_retries = db.query(MessageLog).filter(MessageLog.execution_status == "RETRY_PENDING").count()

    smtp_config = SMTPConfig.from_env()
    is_valid, _ = smtp_config.validate()

    return {
        "status": "online",
        "default_timezone": DEFAULT_TIMEZONE,
        "simulation_mode": True,
        "smtp_configured": is_valid,
        "smtp_host": smtp_config.host,
        "smtp_port": smtp_config.port,
        "from_email": smtp_config.from_email,
        "due_campaigns_count": len(due_campaigns),
        "due_reminders_count": len(due_reminders),
        "total_scheduled_campaigns": pending_campaigns,
        "total_active_reminders": active_reminders,
        "pending_retries_count": pending_retries,
        "total_message_executions": total_executions
    }


@router.post("/verify-smtp")
def verify_smtp_connection() -> Dict[str, Any]:
    """
    Tests SMTP handshake with configured credentials without sending any email.
    Guarantees no credential leakage in API responses or logs.
    """
    client = SMTPClient()
    success, msg = client.verify_connection()
    return {
        "success": success,
        "host": client.config.host,
        "port": client.config.port,
        "use_tls": client.config.use_tls,
        "from_email": client.config.from_email,
        "message": msg
    }


@router.post("/trigger", status_code=status.HTTP_200_OK)
def trigger_scheduler_cycle(
    simulation: bool = Query(True, description="Run in simulation mode (default: True)"),
    confirm_live: bool = Query(False, description="Mandatory confirmation required if simulation=False"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually triggers one background evaluation cycle to process due campaigns, reminders, and retries.
    Requires explicit confirm_live=true if simulation=False.
    """
    if not simulation and not confirm_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety refusal: Live SMTP delivery mode requires confirm_live=true to execute."
        )

    result = scheduling_service.run_pending_jobs(db=db, simulation_mode=simulation)
    return {
        "message": "Scheduler cycle executed successfully.",
        "execution_mode": "SIMULATION" if simulation else "LIVE_SMTP",
        "result": result
    }
