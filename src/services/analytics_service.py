"""
Analytics Service Layer: Implements high-performance SQL aggregation queries,
KPI computation, trend calculations, campaign performance summaries, failure analysis,
and streaming CSV report generation for the Delivery Analytics & Reporting Dashboard.
"""
import io
import csv
import datetime
from typing import Optional, List, Dict, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc

from db.models import MessageLog, Campaign, ReminderJob, Employee, EmailTemplate, utc_now
from src.timezone_utils import ensure_utc
from src.logger import logger


def parse_date_param(val: Any, is_end: bool = False) -> Optional[datetime.datetime]:
    """
    Safely parses incoming date strings (YYYY-MM-DD or ISO 8601) into UTC datetime objects.
    Expands YYYY-MM-DD start dates to 00:00:00 UTC and end dates to 23:59:59.999999 UTC for inclusive filtering.
    """
    if not val or not isinstance(val, str):
        return None
    cleaned = val.strip()
    if not cleaned:
        return None

    # Try full ISO format first
    try:
        dt = datetime.datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        if is_end and len(cleaned) <= 10:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif not is_end and len(cleaned) <= 10:
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt
    except Exception:
        pass

    # Try standard YYYY-MM-DD
    try:
        dt = datetime.datetime.strptime(cleaned, "%Y-%m-%d")
        if is_end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return dt
    except Exception:
        logger.warning(f"Failed to parse date filter parameter: '{val}'")
        return None


def apply_analytics_filters(
    query,
    start_date: Any = None,
    end_date: Any = None,
    campaign_id: Any = None,
    execution_mode: Any = None,
    status: Any = None,
    search: Any = None
):
    """
    Applies standard multi-dimensional filters across MessageLog queries.
    Validates parameter values and enforces database-level index usage.
    """
    start_dt = parse_date_param(start_date, is_end=False)
    if start_dt:
        query = query.filter(MessageLog.executed_at >= start_dt)

    end_dt = parse_date_param(end_date, is_end=True)
    if end_dt:
        query = query.filter(MessageLog.executed_at <= end_dt)

    if campaign_id is not None and isinstance(campaign_id, int) and campaign_id > 0:
        query = query.filter(MessageLog.campaign_id == campaign_id)

    if execution_mode and isinstance(execution_mode, str) and execution_mode.strip().upper() not in ("ALL", ""):
        query = query.filter(MessageLog.execution_mode == execution_mode.strip().upper())

    if status and isinstance(status, str) and status.strip().upper() not in ("ALL", ""):
        query = query.filter(MessageLog.execution_status == status.strip().upper())

    if search and isinstance(search, str) and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                MessageLog.recipient_email.ilike(term),
                MessageLog.subject.ilike(term)
            )
        )

    return query


# ----------------- 1. Overview KPIs ----------------- #

def get_overview_kpis(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None,
    execution_mode: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes top-level KPI metrics via grouped SQL aggregation.
    Guarantees strict separation between SIMULATION and LIVE_SMTP, and never
    conflates SMTP_ACCEPTED with DELIVERY_CONFIRMED.
    """
    base_query = apply_analytics_filters(
        db.query(MessageLog.execution_status, func.count(MessageLog.id)),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id,
        execution_mode=execution_mode,
        status=status,
        search=search
    )

    counts_by_status = dict(base_query.group_by(MessageLog.execution_status).all())

    # Map actual execution statuses
    simulated_emails = counts_by_status.get("SIMULATED_SUCCESS", 0)
    smtp_accepted = counts_by_status.get("SMTP_ACCEPTED", 0)
    delivery_confirmed = counts_by_status.get("DELIVERY_CONFIRMED", 0)
    failed_emails = counts_by_status.get("FAILED", 0)
    retry_pending = counts_by_status.get("RETRY_PENDING", 0)
    delivery_uncertain = counts_by_status.get("DELIVERY_UNCERTAIN", 0)
    skipped_inactive = counts_by_status.get("SKIPPED_INACTIVE", 0)
    skipped_duplicate = counts_by_status.get("SKIPPED_DUPLICATE", 0)

    total_executions = sum(counts_by_status.values())

    # Live attempts metric
    live_total = total_executions - simulated_emails

    # Delivery & failure rates based on live attempts
    if live_total > 0:
        delivery_rate = round(((smtp_accepted + delivery_confirmed) / live_total) * 100, 2)
        failure_rate = round((failed_emails / live_total) * 100, 2)
    else:
        delivery_rate = 0.0
        failure_rate = 0.0

    return {
        "total_executions": total_executions,
        "simulated_emails": simulated_emails,
        "smtp_accepted": smtp_accepted,
        "delivery_confirmed": delivery_confirmed,
        "failed_emails": failed_emails,
        "retry_pending": retry_pending,
        "delivery_uncertain": delivery_uncertain,
        "skipped_inactive": skipped_inactive,
        "skipped_duplicate": skipped_duplicate,
        "live_total": live_total,
        "delivery_rate": delivery_rate,
        "failure_rate": failure_rate
    }


# ----------------- 2. Daily Trends ----------------- #

def get_execution_trends(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None,
    execution_mode: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Computes daily execution counts split by execution mode (SIMULATION vs LIVE_SMTP).
    """
    date_col = func.strftime('%Y-%m-%d', MessageLog.executed_at).label("day")

    query = apply_analytics_filters(
        db.query(date_col, MessageLog.execution_mode, func.count(MessageLog.id)),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id,
        execution_mode=execution_mode,
        status=status,
        search=search
    )

    rows = query.group_by(date_col, MessageLog.execution_mode).order_by(date_col.asc()).all()

    # Aggregate by date
    days_map: Dict[str, Dict[str, int]] = {}
    for day_str, mode, count in rows:
        if not day_str:
            continue
        if day_str not in days_map:
            days_map[day_str] = {"simulated": 0, "live": 0, "total": 0}
        
        if mode == "SIMULATION":
            days_map[day_str]["simulated"] += count
        else:
            days_map[day_str]["live"] += count
        days_map[day_str]["total"] += count

    trends: List[Dict[str, Any]] = []
    for day in sorted(days_map.keys()):
        trends.append({
            "date": day,
            "simulated": days_map[day]["simulated"],
            "live": days_map[day]["live"],
            "total": days_map[day]["total"]
        })

    return trends


# ----------------- 3. Delivery Status Distribution ----------------- #

def get_status_distribution(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None,
    execution_mode: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns breakdown of executions by status with counts and percentages.
    """
    query = apply_analytics_filters(
        db.query(MessageLog.execution_status, func.count(MessageLog.id)),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id,
        execution_mode=execution_mode,
        status=status,
        search=search
    )

    rows = query.group_by(MessageLog.execution_status).order_by(func.count(MessageLog.id).desc()).all()
    total = sum(c for _, c in rows)

    results: List[Dict[str, Any]] = []
    for stat_name, count in rows:
        pct = round((count / total) * 100, 2) if total > 0 else 0.0
        results.append({
            "status": stat_name,
            "count": count,
            "percentage": pct
        })

    return results


# ----------------- 4. Campaign Performance ----------------- #

def get_campaign_performance(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Aggregates message execution performance grouped by campaign.
    Handles unassociated dispatches (e.g. direct reminders) gracefully.
    """
    # 1. Fetch campaigns with recipient counts
    campaigns = db.query(Campaign).all()
    camp_dict = {
        c.id: {
            "campaign_id": c.id,
            "campaign_name": c.campaign_name,
            "total_recipients": len(c.recipients) if c.recipients else 0,
            "total_logged": 0,
            "simulated": 0,
            "smtp_accepted": 0,
            "delivery_confirmed": 0,
            "failed": 0,
            "retry_pending": 0,
            "delivery_uncertain": 0,
            "skipped_inactive": 0
        }
        for c in campaigns
    }

    # Add bucket for reminders / unlinked campaigns
    unlinked_key = 0
    camp_dict[unlinked_key] = {
        "campaign_id": None,
        "campaign_name": "Direct Reminders / System Notifications",
        "total_recipients": 0,
        "total_logged": 0,
        "simulated": 0,
        "smtp_accepted": 0,
        "delivery_confirmed": 0,
        "failed": 0,
        "retry_pending": 0,
        "delivery_uncertain": 0,
        "skipped_inactive": 0
    }

    # 2. Query aggregated counts from message_logs
    query = apply_analytics_filters(
        db.query(MessageLog.campaign_id, MessageLog.execution_status, func.count(MessageLog.id)),
        start_date=start_date,
        end_date=end_date
    )
    rows = query.group_by(MessageLog.campaign_id, MessageLog.execution_status).all()

    for c_id, stat, count in rows:
        target_id = c_id if c_id in camp_dict else unlinked_key
        item = camp_dict[target_id]
        item["total_logged"] += count

        if stat == "SIMULATED_SUCCESS":
            item["simulated"] += count
        elif stat == "SMTP_ACCEPTED":
            item["smtp_accepted"] += count
        elif stat == "DELIVERY_CONFIRMED":
            item["delivery_confirmed"] += count
        elif stat == "FAILED":
            item["failed"] += count
        elif stat == "RETRY_PENDING":
            item["retry_pending"] += count
        elif stat == "DELIVERY_UNCERTAIN":
            item["delivery_uncertain"] += count
        elif stat == "SKIPPED_INACTIVE":
            item["skipped_inactive"] += count

    # Filter out empty unlinked bucket if no unlinked records exist
    results = [v for k, v in camp_dict.items() if k != unlinked_key or v["total_logged"] > 0]
    return sorted(results, key=lambda x: x["total_logged"], reverse=True)


# ----------------- 5. Failure Analysis ----------------- #

def get_failure_analysis(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Returns breakdown of errors by category and list of most frequent failure messages.
    """
    # Categories query
    cat_query = apply_analytics_filters(
        db.query(
            func.coalesce(MessageLog.error_category, "Uncategorized").label("category"),
            func.count(MessageLog.id).label("count")
        ),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id
    ).filter(
        or_(
            MessageLog.execution_status.in_(["FAILED", "DELIVERY_UNCERTAIN"]),
            MessageLog.error_category.isnot(None)
        )
    )
    cat_rows = cat_query.group_by("category").order_by(func.count(MessageLog.id).desc()).all()

    categories = [{"category": row[0], "count": row[1]} for row in cat_rows]
    total_failures = sum(c["count"] for c in categories)

    # Top recurring error messages
    msg_query = apply_analytics_filters(
        db.query(
            MessageLog.error_message,
            MessageLog.error_category,
            func.count(MessageLog.id).label("occurrences"),
            func.max(MessageLog.executed_at).label("last_seen")
        ),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id
    ).filter(
        MessageLog.error_message.isnot(None),
        MessageLog.error_message != ""
    )
    msg_rows = (
        msg_query
        .group_by(MessageLog.error_message, MessageLog.error_category)
        .order_by(func.count(MessageLog.id).desc())
        .limit(10)
        .all()
    )

    top_errors = []
    for err_msg, cat, count, last_seen in msg_rows:
        last_seen_str = last_seen.isoformat() if last_seen else None
        top_errors.append({
            "error_message": err_msg,
            "category": cat or "Uncategorized",
            "occurrences": count,
            "last_seen": last_seen_str
        })

    return {
        "categories": categories,
        "top_errors": top_errors,
        "total_failures": total_failures
    }


# ----------------- 6. Recent Activity Log (Paginated) ----------------- #

def get_recent_activity(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None,
    execution_mode: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Returns paginated execution logs with associated campaign and reminder titles.
    Returns: (items, total_count, total_pages)
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    base_query = apply_analytics_filters(
        db.query(MessageLog),
        start_date=start_date,
        end_date=end_date,
        campaign_id=campaign_id,
        execution_mode=execution_mode,
        status=status,
        search=search
    )

    total_count = base_query.count()
    total_pages = max(1, (total_count + page_size - 1) // page_size)

    logs = (
        base_query
        .order_by(desc(MessageLog.executed_at), desc(MessageLog.id))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for log in logs:
        camp_name = log.campaign.campaign_name if log.campaign else None
        rem_title = log.reminder_job.reminder_title if log.reminder_job else None

        items.append({
            "id": log.id,
            "recipient_email": log.recipient_email,
            "subject": log.subject,
            "campaign_id": log.campaign_id,
            "campaign_name": camp_name,
            "reminder_id": log.reminder_id,
            "reminder_title": rem_title,
            "execution_mode": log.execution_mode,
            "execution_status": log.execution_status,
            "attempt_count": log.attempt_count,
            "error_category": log.error_category,
            "error_message": log.error_message,
            "message_id": log.message_id,
            "smtp_queue_id": log.smtp_queue_id,
            "provider_message_id": log.provider_message_id,
            "executed_at": log.executed_at.isoformat() if log.executed_at else ""
        })

    return items, total_count, total_pages


# ----------------- 7. CSV Export Generator ----------------- #

def sanitize_csv_cell(val: Any) -> Any:
    """
    Mitigates CSV Formula Injection (CWE-1236 / Spreadsheet formula injection).
    If a string value begins with formula characters (=, +, -, @, \t, \r),
    prepend a single quote (') to force spreadsheets to interpret it strictly as plain text.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def export_analytics_csv(
    db: Session,
    export_type: str = "complete",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    campaign_id: Optional[int] = None,
    execution_mode: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generates a CSV string representation of the requested report type.
    Ensures zero leakage of credentials, passwords, or secret connection strings.
    Sanitizes values against CSV Formula Injection.
    Returns: (csv_content_string, filename)
    """
    timestamp_str = utc_now().strftime("%Y%m%d_%H%M%SZ")
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    clean_type = (export_type or "complete").strip().lower()

    if clean_type in ("complete", "all"):
        filename = f"delivery_audit_complete_{timestamp_str}.csv"
        headers = [
            "Log ID", "Execution Key", "Mode", "Status", "Attempt",
            "Recipient Email", "Subject", "Campaign ID", "Campaign Name",
            "Reminder ID", "Error Category", "Error Message",
            "RFC 5322 Message-ID", "SMTP Queue ID", "Provider ID",
            "Executed At (UTC)"
        ]
        writer.writerow(headers)

        query = apply_analytics_filters(
            db.query(MessageLog),
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id,
            execution_mode=execution_mode,
            status=status,
            search=search
        ).order_by(desc(MessageLog.executed_at))

        for log in query.all():
            camp_name = log.campaign.campaign_name if log.campaign else "N/A"
            writer.writerow([
                sanitize_csv_cell(c) for c in [
                    log.id,
                    log.execution_key,
                    log.execution_mode,
                    log.execution_status,
                    log.attempt_count,
                    log.recipient_email,
                    log.subject,
                    log.campaign_id or "",
                    camp_name,
                    log.reminder_id or "",
                    log.error_category or "",
                    log.error_message or "",
                    log.message_id or "",
                    log.smtp_queue_id or "",
                    log.provider_message_id or "",
                    log.executed_at.isoformat() if log.executed_at else ""
                ]
            ])

    elif clean_type == "campaigns":
        filename = f"campaign_performance_summary_{timestamp_str}.csv"
        headers = [
            "Campaign ID", "Campaign Name", "Total Targeted Recipients",
            "Total Dispatched Records", "Simulated", "SMTP Accepted",
            "Delivery Confirmed", "Failed", "Retry Pending",
            "Delivery Uncertain", "Skipped Inactive"
        ]
        writer.writerow(headers)

        camp_data = get_campaign_performance(db, start_date=start_date, end_date=end_date)
        for c in camp_data:
            writer.writerow([
                sanitize_csv_cell(cell) for cell in [
                    c["campaign_id"] or "N/A",
                    c["campaign_name"],
                    c["total_recipients"],
                    c["total_logged"],
                    c["simulated"],
                    c["smtp_accepted"],
                    c["delivery_confirmed"],
                    c["failed"],
                    c["retry_pending"],
                    c["delivery_uncertain"],
                    c["skipped_inactive"]
                ]
            ])

    elif clean_type == "failures":
        filename = f"failed_executions_report_{timestamp_str}.csv"
        headers = [
            "Log ID", "Execution Key", "Recipient Email", "Subject",
            "Campaign Name", "Attempt Count", "Error Category",
            "Error Message", "SMTP Response", "RFC 5322 Message-ID",
            "Executed At (UTC)"
        ]
        writer.writerow(headers)

        query = apply_analytics_filters(
            db.query(MessageLog),
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id,
            execution_mode=execution_mode,
            status=status or "FAILED",
            search=search
        ).filter(
            or_(
                MessageLog.execution_status == "FAILED",
                MessageLog.error_category.isnot(None)
            )
        ).order_by(desc(MessageLog.executed_at))

        for log in query.all():
            camp_name = log.campaign.campaign_name if log.campaign else "N/A"
            writer.writerow([
                sanitize_csv_cell(cell) for cell in [
                    log.id,
                    log.execution_key,
                    log.recipient_email,
                    log.subject,
                    camp_name,
                    log.attempt_count,
                    log.error_category or "Uncategorized",
                    log.error_message or "",
                    log.smtp_response or "",
                    log.message_id or "",
                    log.executed_at.isoformat() if log.executed_at else ""
                ]
            ])

    elif clean_type == "uncertain":
        filename = f"delivery_uncertain_records_{timestamp_str}.csv"
        headers = [
            "Log ID", "Execution Key", "Recipient Email", "Subject",
            "Campaign Name", "Attempt Count", "RFC 5322 Message-ID",
            "SMTP Response", "Diagnostic Detail", "Executed At (UTC)"
        ]
        writer.writerow(headers)

        query = apply_analytics_filters(
            db.query(MessageLog),
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id,
            execution_mode=execution_mode,
            status="DELIVERY_UNCERTAIN",
            search=search
        ).order_by(desc(MessageLog.executed_at))

        for log in query.all():
            camp_name = log.campaign.campaign_name if log.campaign else "N/A"
            writer.writerow([
                sanitize_csv_cell(cell) for cell in [
                    log.id,
                    log.execution_key,
                    log.recipient_email,
                    log.subject,
                    camp_name,
                    log.attempt_count,
                    log.message_id or "",
                    log.smtp_response or "",
                    log.error_message or "",
                    log.executed_at.isoformat() if log.executed_at else ""
                ]
            ])

    else:
        raise ValueError(f"Unknown export type '{clean_type}'. Expected: complete, campaigns, failures, or uncertain.")

    return output.getvalue(), filename
