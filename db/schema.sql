-- Database Schema for Email Automation & Reminder System
-- Compatible with SQLite and PostgreSQL

CREATE TABLE IF NOT EXISTS contacts(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  timezone TEXT DEFAULT 'Asia/Kolkata',
  unsubscribed BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates(
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  subject TEXT NOT NULL,
  body_md TEXT NOT NULL,             -- Markdown with {{ vars }}
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  template_id TEXT REFERENCES templates(id),
  sender_name TEXT NOT NULL,
  sender_email TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reminders(
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  contact_id TEXT REFERENCES contacts(id),
  campaign_id TEXT REFERENCES campaigns(id),
  start_at_utc TIMESTAMP NOT NULL,   -- First fire time in UTC (ISO 8601)
  rrule TEXT,                        -- RFC 5545 RRULE (e.g. FREQ=WEEKLY;BYDAY=MO,WE or FREQ=DAILY)
  active BOOLEAN DEFAULT 1,
  last_fired_at_utc TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages(
  id TEXT PRIMARY KEY,
  campaign_id TEXT REFERENCES campaigns(id),
  contact_id TEXT REFERENCES contacts(id),
  scheduled_at_utc TIMESTAMP NOT NULL,
  sent_at_utc TIMESTAMP,
  provider_msg_id TEXT,
  status TEXT DEFAULT 'scheduled',   -- 'scheduled'|'sent'|'failed'|'bounced'|'opened'|'clicked'
  subject TEXT,
  body_rendered_html TEXT,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_sched ON messages(scheduled_at_utc, status);
