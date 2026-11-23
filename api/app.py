"""
FastAPI REST API for Email Automation & Reminder System.
Exposes CRUD endpoints for contacts, templates, campaigns, reminders, and delivery stats.
"""
import uuid
import datetime as dt
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from db.database import get_connection, init_db
from src.webhooks import router as tracking_router
from api.routes.employees import router as employees_router
from src.scheduler import dispatch_batch
from src.data_loader import validate_email

# Ensure DB is created on startup
init_db()

app = FastAPI(
    title="Email Automation & Reminder API",
    description="REST backend for scheduled reminder management, message dispatch, and open/click tracking.",
    version="1.0.0"
)

# CORS setup for dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(tracking_router)
app.include_router(employees_router)

# ----------------- Schemas ----------------- #
class ContactCreate(BaseModel):
    name: str
    email: str
    timezone: str = "Asia/Kolkata"

    @field_validator("email")
    def validate_recipient_email(cls, v):
        if not validate_email(v):
            raise ValueError(f"Invalid email format: '{v}'")
        return v

class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_md: str

class CampaignCreate(BaseModel):
    name: str
    template_id: str
    sender_name: str
    sender_email: str

    @field_validator("sender_email")
    def validate_sender(cls, v):
        if not validate_email(v):
            raise ValueError(f"Invalid sender email format: '{v}'")
        return v

class ReminderCreate(BaseModel):
    title: str
    contact_id: str
    campaign_id: str
    start_at_utc: str
    rrule: Optional[str] = None

# ----------------- Endpoints ----------------- #

@app.get("/")
def root():
    return {
        "system": "Email Automation & Reminder System API",
        "status": "operational",
        "docs_url": "/docs"
    }

@app.post("/contacts", status_code=status.HTTP_201_CREATED)
def create_contact(c: ContactCreate):
    cid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO contacts(id, name, email, timezone, unsubscribed) VALUES (?, ?, ?, ?, 0);",
            (cid, c.name, c.email, c.timezone)
        )
        conn.commit()
        return {"id": cid, "name": c.name, "email": c.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create contact: {str(e)}")
    finally:
        conn.close()

@app.get("/contacts")
def list_contacts():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM contacts;").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(t: TemplateCreate):
    tid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO templates(id, name, subject, body_md) VALUES (?, ?, ?, ?);",
            (tid, t.name, t.subject, t.body_md)
        )
        conn.commit()
        return {"id": tid, "name": t.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create template: {str(e)}")
    finally:
        conn.close()

@app.get("/templates")
def list_templates():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM templates;").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_campaign(camp: CampaignCreate):
    cid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO campaigns(id, name, template_id, sender_name, sender_email) VALUES (?, ?, ?, ?, ?);",
            (cid, camp.name, camp.template_id, camp.sender_name, camp.sender_email)
        )
        conn.commit()
        return {"id": cid, "name": camp.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create campaign: {str(e)}")
    finally:
        conn.close()

@app.get("/campaigns")
def list_campaigns():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM campaigns;").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.post("/reminders", status_code=status.HTTP_201_CREATED)
def create_reminder(r: ReminderCreate):
    rid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO reminders(id, title, contact_id, campaign_id, start_at_utc, rrule, active) "
            "VALUES (?, ?, ?, ?, ?, ?, 1);",
            (rid, r.title, r.contact_id, r.campaign_id, r.start_at_utc, r.rrule)
        )
        conn.commit()
        return {"id": rid, "title": r.title}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create reminder: {str(e)}")
    finally:
        conn.close()

@app.get("/reminders")
def list_reminders():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM reminders;").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/messages")
def list_messages(limit: int = 50):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM messages ORDER BY scheduled_at_utc DESC LIMIT ?;", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.post("/dispatch-batch")
def trigger_dispatch(dry_run: bool = True):
    """Triggers an immediate dispatch batch cycle."""
    results = dispatch_batch(dry_run=dry_run)
    return {"message": "Batch dispatch executed", "processed": len(results), "dry_run": dry_run}
