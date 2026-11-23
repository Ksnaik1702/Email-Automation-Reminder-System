"""
SQLAlchemy Declarative Models for Email Automation & Reminder System.
Defines normalized tables, explicit foreign keys, indexes, and relationships.
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now():
    """Returns timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    company = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    employment_status = Column(String(20), default="Active", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    campaign_recipients = relationship("CampaignRecipient", back_populates="employee", cascade="all, delete-orphan")
    reminder_jobs = relationship("ReminderJob", back_populates="employee", cascade="all, delete-orphan")
    message_logs = relationship("MessageLog", back_populates="employee")

    def __repr__(self):
        return f"<Employee(id={self.id}, code='{self.employee_id}', email='{self.email}')>"


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(50), nullable=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    campaigns = relationship("Campaign", back_populates="template")

    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name='{self.template_name}')>"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    template_id = Column(Integer, ForeignKey("email_templates.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), default="Draft", nullable=False)  # Draft, Scheduled, Running, Completed, Paused
    scheduled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    template = relationship("EmailTemplate", back_populates="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")
    reminder_jobs = relationship("ReminderJob", back_populates="campaign", cascade="all, delete-orphan")
    message_logs = relationship("MessageLog", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.campaign_name}', status='{self.status}')>"


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email = Column(String(150), nullable=False)
    status = Column(String(20), default="Pending", nullable=False)  # Pending, Sent, Failed, Skipped

    __table_args__ = (
        UniqueConstraint("campaign_id", "employee_id", name="uq_campaign_employee"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
    employee = relationship("Employee", back_populates="campaign_recipients")

    def __repr__(self):
        return f"<CampaignRecipient(id={self.id}, campaign_id={self.campaign_id}, email='{self.recipient_email}')>"


class ReminderJob(Base):
    __tablename__ = "reminder_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    reminder_title = Column(String(200), nullable=False)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    recurrence_type = Column(String(20), default="None", nullable=False)  # None, Daily, Weekly, Monthly
    status = Column(String(20), default="Active", nullable=False)        # Active, Paused, Completed, Cancelled
    last_executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="reminder_jobs")
    employee = relationship("Employee", back_populates="reminder_jobs")
    message_logs = relationship("MessageLog", back_populates="reminder_job")

    def __repr__(self):
        return f"<ReminderJob(id={self.id}, title='{self.reminder_title}', status='{self.status}')>"


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    reminder_id = Column(Integer, ForeignKey("reminder_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_email = Column(String(150), nullable=False)
    subject = Column(String(255), nullable=False)
    execution_status = Column(String(30), nullable=False)  # SIMULATED_SUCCESS, SMTP_ACCEPTED, FAILED, RETRY_PENDING, SKIPPED_DUPLICATE, SKIPPED_INACTIVE, DELIVERY_CONFIRMED, BOUNCED
    execution_mode = Column(String(20), default="SIMULATION", nullable=False)  # SIMULATION or LIVE_SMTP
    attempt_count = Column(Integer, default=1, nullable=False)
    smtp_response = Column(String(255), nullable=True)
    # provider_message_id stores the locally generated RFC 5322 Message-ID (or provider-assigned ID if confirmed via webhook).
    # NOTE: Standard direct SMTP servers (e.g. Gmail SMTP) do not return a distinct provider ID over standard SMTP.
    provider_message_id = Column(String(150), nullable=True)
    error_category = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, default=utc_now, nullable=False)
    execution_key = Column(String(100), unique=True, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("execution_key", name="uq_message_execution_key"),
        Index("idx_message_logs_executed_at", "executed_at"),
        Index("idx_message_logs_status", "execution_status"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="message_logs")
    reminder_job = relationship("ReminderJob", back_populates="message_logs")
    employee = relationship("Employee", back_populates="message_logs")
    template = relationship("EmailTemplate")

    def __repr__(self):
        return f"<MessageLog(id={self.id}, email='{self.recipient_email}', status='{self.execution_status}')>"
