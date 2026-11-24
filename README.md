# 📧 Email Automation & Reminder System

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Automation](https://img.shields.io/badge/Workflow-Scheduled_Reminders-green.svg)](https://github.com)
[![Status](https://img.shields.io/badge/Status-Industry--Ready-brightgreen.svg)](https://github.com)

> An enterprise-grade, student-friendly Python automation engine designed to schedule, personalize, dispatch, and track automated email alerts, corporate notifications, payment reminders, and calendar tasks. Equipped with a **zero-risk Virtual Simulation (Dry-Run) mode**, automated CSV auditing, and an optional interactive dashboard.

---

## 📌 Table of Contents
1. [Project Overview](#-project-overview)
2. [Problem Statement & Industry Impact](#-problem-statement--industry-impact)
3. [Architecture & Data Flow](#-architecture--data-flow)
4. [Key Features](#-key-features)
5. [Tech Stack](#-tech-stack)
6. [Folder Structure](#-folder-structure)
7. [Installation & Setup](#-installation--setup)
8. [Virtual Simulation (Zero-Risk Dry-Run)](#-virtual-simulation-zero-risk-dry-run)
9. [How to Run](#-how-to-run)
10. [Sample Output & Audit Reports](#-sample-output--audit-reports)
11. [Phase 9: Enterprise SaaS UI/UX Transformation](#-phase-9-enterprise-saas-uiux-transformation)
12. [Safe GitHub Best Practices](#-safe-github-best-practices)
13. [Interview Preparation Guide](#-interview-preparation-guide)

---

## 📖 Project Overview

In corporate environments, hundreds of hours are lost each month to repetitive communication: sending payment due dates, meeting check-ins, webinar onboarding links, and project milestone alerts. 

The **Email Automation & Reminder System** solves this by decoupling reminder schedules from human memory:
- Reads recipient lists (`data/contacts.csv`) and task agendas (`data/reminders.csv`).
- Injects recipient and task attributes into responsive HTML templates.
- Dispatches emails via SMTP (or safely simulates sending in dry-run mode).
- Tracks delivery statuses and logs every transaction to `logs/automation.log` and an audit report `outputs/delivery_report.csv`.

---

## 🏢 Problem Statement & Industry Impact

### The Problem
- **Human Error & Omission:** Teams frequently miss follow-ups, resulting in late payments, missed meetings, and delayed project milestones.
- **Wasted Operational Bandwidth:** Operations, HR, and sales professionals spend 15–20% of their workweek copying and pasting templated emails.
- **Inconsistent Messaging:** Manual emails often lack proper branding, structured agenda cards, or important action links.

### How Industry Teams Use This:
| Team / Role | Real-World Use Case |
| :--- | :--- |
| **Finance & Accounts** | Outstanding invoice alerts, recurring retainer reminders, payment gateway links. |
| **People Operations (HR)** | Performance appraisal deadlines, policy acknowledgement nudges, onboarding workflows. |
| **Sales & Client Success** | Demo reminders, proposal follow-up sequences, renewal notifications. |
| **Educators & Trainers** | Batch webinar announcements, assignment deadlines, lab link distributions. |
| **DevOps & IT** | SSL certificate expiry notices, planned maintenance windows, incident updates. |

---

## 🏗️ Architecture & Data Flow

```text
+-----------------------+     +------------------------+
|   data/contacts.csv   |     |   data/reminders.csv   |
| (Recipient Metadata)  |     | (Due Dates, Priorities)|
+-----------+-----------+     +-----------+------------+
            |                             |
            +------------+   +------------+
                         |   |
                         v   v
            +----------------------------+
            |    src/data_loader.py      |
            | (Validation & Job Merging) |
            +--------------+-------------+
                           |
                           v
            +----------------------------+
            |    src/templating.py       |
            | (HTML Template Injection)  | <--- templates/*.html
            +--------------+-------------+
                           |
                           v
            +----------------------------+
            |      src/mailer.py         |
            +--------------+-------------+
              /                         \
    [Dry Run = True]               [Dry Run = False]
            |                               |
            v                               v
+-----------------------+      +-------------------------+
| outputs/previews/*.html|     | Live SMTP (Gmail/SES)   |
| (Zero-Risk Simulation)|      | (Encrypted TLS Dispatch)|
+-----------+-----------+      +------------+------------+
            \                               /
             \                             /
              v                           v
            +----------------------------+
            |      src/reporter.py       |
            +--------------+-------------+
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
+--------------------+            +--------------------+
| logs/automation.log|            |outputs/delivery_   |
| (Execution History)|            |     report.csv     |
+--------------------+            +--------------------+
```

---

## ✨ Key Features

1. **Dual Execution Engine:**
   - **Virtual Dry-Run (Default):** Generates full responsive HTML email previews on disk (`outputs/previews/`) without touching live SMTP servers. Perfect for GitHub portfolio demonstration, testing, and grading.
   - **Live SMTP Engine:** Connects over secure TLS (port 587) or SSL (port 465) using standard library `smtplib`.
2. **Dynamic HTML Templating:**
   - Multi-template support: `meeting_reminder.html`, `payment_due_reminder.html`, and `class_webinar_reminder.html`.
   - Variable substitution supporting recipient names, company names, amounts due, priorities, dates, and meeting links.
3. **Data Integrity & Validation:**
   - Regular expression validation for email addresses.
   - Missing field fallbacks and unmapped foreign key prevention.
4. **Structured Auditing & Observability:**
   - Dual-stream logging (colorized console output + persistent file logs).
   - Real-time CSV generation tracking timestamps, message IDs, and error diagnoses.
5. **Interactive Dashboard (Optional):**
   - Includes `dashboard.py` (Streamlit) for real-time contact review, template inspection, and single-click batch dispatches.

---

## 🧰 Tech Stack

- **Core Language:** Python 3.9+
- **Data Ingestion:** `csv` (Standard Library) / `pandas`
- **Email Protocol:** `smtplib`, `email.message.EmailMessage`
- **Templating:** `jinja2` (with built-in regex fallback)
- **Scheduling:** `schedule` / `datetime`
- **Configuration & Security:** `python-dotenv`
- **Dashboard:** `streamlit`

---

## 📁 Folder Structure

```text
Email-Automation-Reminder-System/
│
├── data/
│   ├── contacts.csv            # Recipient database (names, emails, departments, timezones)
│   └── reminders.csv           # Task schedule (priorities, dates, categories, templates)
│
├── templates/
│   ├── class_webinar_reminder.html   # Learning and webinar reminder template
│   ├── meeting_reminder.html         # Corporate meeting and calendar alert template
│   └── payment_due_reminder.html     # Finance and outstanding balance notice template
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Central environment variable and directory loader
│   ├── data_loader.py          # Data ingestion, schema validation, and job merging
│   ├── logger.py               # Console and file logger configuration
│   ├── mailer.py               # SMTP engine & Virtual Simulation handler
│   ├── reporter.py             # CSV audit log generation and statistical summary
│   ├── scheduler.py            # Batch processor and recurring schedule runner
│   └── templating.py           # HTML rendering and placeholder substitution
│
├── outputs/
│   ├── delivery_report.csv     # Generated audit log containing send status
│   └── previews/               # Rendered HTML email files (generated in Dry-Run mode)
│
├── logs/
│   └── automation.log          # Detailed execution trace logs
│
├── docs/                       # Architectural documentation & flowcharts
├── images/                     # Screenshots for GitHub README
├── .env.example                # Safe environment variable template
├── .gitignore                  # Prevents secrets, venv, and cache from being committed
├── dashboard.py                # Optional interactive Streamlit web dashboard
├── main.py                     # Primary command-line interface
├── requirements.txt            # Python package dependencies
└── README.md                   # Complete project documentation
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Email-Automation-Reminder-System.git
cd Email-Automation-Reminder-System
```

### 2. Set Up a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template file to `.env`:
```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```
*(By default, `DRY_RUN=true` is set. You do not need real email passwords to test or showcase this project!)*

---

## 🧪 Virtual Simulation (Zero-Risk Dry-Run)

Students and evaluators do not need access to live company email servers. When executed in dry-run mode:
1. The engine reads `data/contacts.csv` and `data/reminders.csv`.
2. Resolves template variables (`{{ name }}`, `{{ amount_due }}`, etc.).
3. Generates complete HTML files in `outputs/previews/`.
4. Double-click any generated `.html` file inside `outputs/previews/` to view the exact rendered email as it would look in Gmail or Outlook.
5. Logs records to `logs/automation.log` and marks `SIMULATED_SUCCESS` in `outputs/delivery_report.csv`.

---

## 💻 How to Run

### Option 1: Run One-Off Simulation (Dry-Run Sweep)
Runs a single evaluation sweep through due campaigns and recurring reminders in safe simulation mode:
```bash
python worker.py --once
```

### Option 2: Run Continuous APScheduler Worker (Simulation Mode - Default)
Continuously evaluates due campaigns, recurring reminders, and retry queues without sending real emails:
```bash
python worker.py
```

### Option 3: Run One-Off Live SMTP Delivery (Explicit Safety Confirmation Required)
To dispatch real emails to inboxes via SMTP, both `--live` and `--confirm-live` are strictly mandatory:
```bash
python worker.py --once --live --confirm-live
```

### Option 4: Run Continuous Background Worker in Live SMTP Mode
```bash
python worker.py --live --confirm-live
```

### Option 5: Launch FastAPI Backend Server
Starts the REST API service with Swagger UI at `http://127.0.0.1:8000/docs`:
```bash
uvicorn api.app:app --reload --port 8000
```

### Option 6: Verify SMTP Connection via API
Test SMTP credentials safely without sending an email:
```bash
curl -X POST http://127.0.0.1:8000/api/scheduler/verify-smtp
```

---

## 🔒 Gmail SMTP Setup Guide (Google App Passwords)

When configuring Google Workspace or personal Gmail accounts for live email delivery:

1. **Enable 2-Step Verification:**
   - Navigate to [Google Account Security](https://myaccount.google.com/signinoptions/two-step-verification) and turn on 2-Step Verification.
2. **Generate an App Password:**
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords).
   - Enter an app name (e.g. `Email Automation Engine`) and click **Create**.
   - Copy the generated 16-character code (format: `xxxx xxxx xxxx xxxx`).
3. **Configure `.env`:**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USER=your_email@gmail.com
   SMTP_PASS=xxxxxxxxxxxxxxxx
   SMTP_FROM_EMAIL=your_email@gmail.com
   SMTP_FROM_NAME="Email Automation Hub"
   ```
4. **Safety Confirmation Rule:**
   - To prevent accidental transmissions, live delivery is strictly blocked unless `CONFIRM_LIVE_DELIVERY=true` is set in `.env` OR `--confirm-live` is provided on the command line.

---

## 📊 Delivery Reliability & Audit Logging Architecture

### 1. Delivery Status Lifecycle
The system strictly distinguishes between SMTP relay acceptance and confirmed inbox delivery:
- `SIMULATED_SUCCESS`: Email successfully rendered and saved to local previews in `outputs/previews/` (Simulation Mode).
- `SMTP_ACCEPTED`: Upstream SMTP relay accepted the message (`250 OK`) into its transmission queue. *Note: Under RFC 5321, this confirms relay ingestion, not recipient inbox arrival.*
- `DELIVERY_UNCERTAIN`: Timeout or connection loss occurred *after* message payload transmission while awaiting the server's final acknowledgment. Automatic retries are disabled to prevent duplicate transmissions.
- `RETRY_PENDING`: Pre-submission temporary failure encountered; scheduled for automated retry with bounded exponential backoff.
- `SKIPPED_INACTIVE`: Recipient employee is not active (`employment_status != 'Active'`); delivery safely prevented.
- `FAILED`: Permanent error encountered (e.g., auth failure, invalid recipient syntax) or maximum retry limit exceeded.
- `DELIVERY_CONFIRMED`: Reserved for downstream webhook delivery receipts (SendGrid, Mailgun, Postmark).

### 2. Stage-Aware SMTP Error Handling & Uncertain Outcomes
A critical failure mode in SMTP automation occurs when a network connection drops or times out **after** the message payload has been transmitted over the socket, while awaiting the server's final acknowledgment (`250 OK`):
- **Pre-Submission Failures:** If a timeout or socket error occurs during connection, TLS negotiation, authentication, or envelope creation (`MAIL FROM` / `RCPT TO`), the message was never submitted to the SMTP relay. The attempt is safely marked `RETRY_PENDING` and scheduled for automatic retry.
- **Post-Submission Uncertainties:** If the timeout occurs after data submission while awaiting `250 OK`, the upstream relay may have already spooled and dispatched the email. Automatically resending would produce duplicate emails in the recipient's inbox.
- **Fail-Safe Policy:** The attempt is recorded as `DELIVERY_UNCERTAIN` (`next_retry_at = None`). Automatic retry loops ignore it, preserving the execution key and complete audit history until an explicit administrative recovery decision is made.
- **Delivery Guarantee Terminology:** The system prevents automatic resubmission of messages with uncertain SMTP outcomes. This reduces duplicate submission risk but does not guarantee exactly-once or at-most-once recipient delivery.

### 3. Message Identifier Classification & Database Separation
The system strictly separates message identifiers into distinct, dedicated database columns:
1. **`message_logs.message_id` (Locally Generated RFC 5322 Message-ID):** Formatted as `<uuid@domain>`, generated client-side by `SMTPClient.build_multipart_message` before submission. This ID satisfies RFC 5322 requirements and provides an immutable reference for local idempotency.
2. **`message_logs.smtp_queue_id` (SMTP Server Queue ID):** An internal queue reference assigned by the receiving MTA relay if returned in the `250 OK` response line (e.g., `250 2.0.0 OK: queued as 4S9XYZ123`).
3. **`message_logs.provider_message_id` (Provider-Specific Message ID):** An identifier generated by managed transactional providers (SendGrid, Mailgun, Postmark), which is typically exposed via REST API responses or downstream webhook events.

> **SMTP Protocol Limitation:** Standard direct SMTP servers (including Google Workspace and Gmail SMTP at `smtp.gmail.com`) accept the client's locally generated `Message-ID` header and return a standard `250 OK` status, but do **not** return a distinct provider-generated message ID during the standard SMTP session. For direct SMTP transmissions, `message_id` stores the RFC 5322 identifier, while `provider_message_id` remains `NULL`.

### 4. Uncertain-Record Recovery Mechanism
Manual database-level resolution is currently required to resolve `DELIVERY_UNCERTAIN` records. No administrative API currently exists in the application for updating or resolving uncertain records.

When an uncertain outcome occurs:
1. The execution key remains locked to block automated duplicate submissions.
2. An administrator must check server or gateway logs out-of-band using the locally generated RFC 5322 `Message-ID`.
3. If confirmed that the recipient did not receive the email, manual database-level resolution can be performed directly in SQLite:
   ```sql
   -- Mark for re-attempt by background worker
   UPDATE message_logs
   SET execution_status = 'RETRY_PENDING', next_retry_at = CURRENT_TIMESTAMP
   WHERE id = <record_id>;
   ```
4. If confirmed that the recipient did receive the email:
   ```sql
   -- Mark as confirmed delivery
   UPDATE message_logs
   SET execution_status = 'DELIVERY_CONFIRMED'
   WHERE id = <record_id>;
   ```

### 5. Configurable Retry Limits & Bounded Exponential Backoff
- **Configurable Attempt Limit:** `MAX_RETRIES` (default: `3`) governs maximum delivery attempts before terminal failure.
- **Bounded Exponential Backoff:** Delay between retry attempts is governed by:
  $$T_{\text{wait}} = \min\left(\text{MAX\_BACKOFF\_SECONDS},\, \text{RETRY\_BACKOFF\_BASE\_SECONDS} \times 2^{(\text{attempt} - 1)}\right)$$
  Default: 60s (attempt 1), 120s (attempt 2), 240s (attempt 3), capped at `MAX_BACKOFF_SECONDS` (3600s).
- **Permanent Errors:** Authentication errors (`535`), recipient syntax errors, and mailbox rejections (`550`) are marked as `FAILED` immediately without retries.
- **Terminal Exhaustion:** When `attempt >= MAX_RETRIES`, the message transitions to `FAILED` with `error_category="MAX_RETRIES_EXCEEDED"`.
- **Complete Audit Trail:** Every attempt increments `attempt_count` and updates `executed_at`, `error_message`, and `smtp_response` in `message_logs`.

### 6. Fail-Closed Live Mode Confirmation
To guarantee safety across automation pipelines and CI/CD:
- **Default Mode:** Simulation Mode is strictly active by default whenever live mode is not explicitly invoked.
- **Fail Closed Behavior:** If `--live` is provided without `--confirm-live` (and without `CONFIRM_LIVE_DELIVERY=true` in `.env`), the system **fails closed**:
  - Displays an explicit refusal error explaining the missing safety confirmation.
  - Exits immediately with exit code 1.
  - Does **not** process any campaigns or reminders.
  - Does **not** silently fall back to simulation mode.

---

## 🧪 How to Conduct a Safe Single-Recipient SMTP Test

To test real SMTP delivery to your own personal email with zero risk of sending unwanted messages:

1. **Configure Credentials in `.env`:**
   ```env
   SIMULATION_MODE=false
   CONFIRM_LIVE_DELIVERY=true
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USER=your_email@gmail.com
   SMTP_PASS=xxxx-xxxx-xxxx-xxxx
   SMTP_FROM_EMAIL=your_email@gmail.com
   SMTP_FROM_NAME="Test Dispatcher"
   ```

2. **Verify Connectivity via API Handshake (No Email Sent):**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/scheduler/verify-smtp
   ```
   *Expected Response:* `{"success": true, "host": "smtp.gmail.com", "port": 587, ...}`

3. **Create a Single-Recipient Test Campaign:**
   - Using the web dashboard or REST API (`POST /api/campaigns`):
     - Select an existing template (e.g., "Meeting Invitation").
     - Target **only your own employee record** (e.g., `your_email@gmail.com`).
     - Save and mark the campaign as `READY`.

4. **Execute One-Off Single Sweep:**
   ```bash
   python worker.py --once --live --confirm-live
   ```

5. **Verify Delivery & Audit Log:**
   - Check your inbox for the delivered email.
   - Inspect the SQLite audit log:
     ```sql
     SELECT execution_key, execution_mode, execution_status, attempt_count, smtp_response, message_id, smtp_queue_id, provider_message_id
     FROM message_logs ORDER BY id DESC LIMIT 1;
     ```
   - Confirm status is `SMTP_ACCEPTED` with a valid `message_id` (and `provider_message_id` NULL for direct SMTP).
```

### Option 4: Launch Interactive Streamlit Dashboard
```bash
streamlit run dashboard.py
```

### Option 5: Live SMTP Sending (When credentials are ready)
1. In `.env`, set `DRY_RUN=false` and configure `SMTP_USER` and `SMTP_PASSWORD` (use a 16-character Google App Password).
2. Run:
```bash
python main.py --send-real
```

---

## 📊 Sample Output & Audit Reports

### Terminal Execution Output
```text
========================================================================
     ___ _  _   _   ___ _       _   _   _ _____ ___  __  __   _ _____ ___ ___  _  _ 
    | __|  \/  |   /_\ |_| |   /_\ | | | |_   _/ _ \|  \/  | /_\_   _|_ _/ _ \| \| |
    | _|| |\/| |  / _ \| | |__/ _ \| |_| | | || (_) | |\/| |/ _ \| |  | | (_) | .` |
    |___|_|  |_| /_/ \_\_|____/_/ \_\\___/  |_| \___/|_|  |_/_/ \_\_| |___\___/|_|\_|
                                & REMINDER SYSTEM
========================================================================

Active Mode : 🟢 VIRTUAL SIMULATION (DRY-RUN) MODE
Safety Note : No real emails will be sent. HTML previews will be generated in outputs/previews/.

18:44:31 [INFO] === Starting Reminder Dispatch Cycle (dry_run=True) ===
18:44:31 [INFO] Loading contacts from: .../data/contacts.csv
18:44:31 [INFO] Loaded 5 valid contacts successfully.
18:44:31 [INFO] Loading reminders from: .../data/reminders.csv
18:44:31 [INFO] Loaded 5 reminders.
18:44:31 [INFO] Generated 5 merged notification jobs ready for processing.
18:44:31 [INFO] [SIMULATION] Dry-run send for 'aarav.sharma@example.com' (Reminder R201) | Subject: '🔔 [Meeting] Sprint Planning & Retro - Aarav Sharma' | Preview saved: R201_aarav_sharma_at_example_com.html
18:44:31 [INFO] [SIMULATION] Dry-run send for 'priya.patel@example.com' (Reminder R202) | Subject: '🚨 [URGENT] [Payment] Invoice #INV-8821 Payment Due - Priya Patel' | Preview saved: R202_priya_patel_at_example_com.html

============================================================
              AUTOMATION EXECUTION SUMMARY
============================================================
  Total Reminders Processed : 5
  Successful / Simulated    : 5
  Failed Dispatches         : 0
  Delivery Success Rate     : 100.0%
  Audit Report Saved To     : .../outputs/delivery_report.csv
============================================================
```

### Generated CSV Report (`outputs/delivery_report.csv`)
| reminder_id | recipient_email | category | priority | status | timestamp | error |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `R201` | `aarav.sharma@example.com` | Meeting | High | SIMULATED_SUCCESS | 2026-11-23 18:44:31 | None |
| `R202` | `priya.patel@example.com` | Payment | Critical | SIMULATED_SUCCESS | 2026-11-23 18:44:31 | None |
| `R203` | `rohan.verma@example.com` | Webinar | Medium | SIMULATED_SUCCESS | 2026-11-23 18:44:31 | None |

---

## 📈 Phase 7: Delivery Analytics & Reporting Dashboard

The Delivery Analytics & Reporting Dashboard provides enterprise observability into the execution history, campaign performance, error root-causes, and audit logs stored in the centralized SQLite database.

### 1. Dashboard Capabilities
- **8 Dedicated KPI Metrics:** Total Executions, Simulated Emails, SMTP Accepted, Delivery Confirmed, Failed Emails, Retry Pending, Delivery Uncertain, and Skipped Inactive.
- **Strict Metric Isolation:** Simulated dry-run executions are strictly isolated from real SMTP relay acceptances. `SMTP_ACCEPTED` is never conflated with `DELIVERY_CONFIRMED`.
- **Daily Execution Trends:** Timeline view visualizing daily volume with stacked bars distinguishing simulation vs live SMTP traffic.
- **Status Distribution:** Real-time breakdown of execution outcomes with exact counts and calculated percentages.
- **Campaign Performance Summary:** Per-campaign table detailing targeted recipients, fulfillment, accepted messages, failures, retries, and uncertain states.
- **Failure Root-Cause Analysis:** Categorized failure counts (`AUTHENTICATION_ERROR`, `TEMPORARY_NETWORK`, `MAX_RETRIES_EXCEEDED`, etc.) alongside top 10 recurring error diagnostics with last-seen timestamps.
- **Paginated Audit Trail:** Chronological log table featuring full diagnostic metadata (RFC 5322 `Message-ID`, SMTP queue ID, error details, and attempt counts).
- **Multi-Dimensional Filters:** Filter dynamically by start date, end date, campaign, execution mode (`SIMULATION` / `LIVE_SMTP`), execution status, and recipient/subject search text.

### 2. REST API Endpoints (`/api/analytics`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/analytics/overview` | Aggregated KPI metrics (totals, counts by status, live delivery/failure rates) |
| `GET` | `/api/analytics/trends` | Daily execution counts grouped by calendar date and execution mode |
| `GET` | `/api/analytics/status-distribution` | Delivery status distribution with counts and percentages |
| `GET` | `/api/analytics/campaign-performance`| Per-campaign recipient targeting and fulfillment summary |
| `GET` | `/api/analytics/failures` | Error category breakdown and top 10 recurring failure messages |
| `GET` | `/api/analytics/recent-activity` | Paginated message log table (supports `page`, `page_size`, and all filters) |
| `GET` | `/api/analytics/export` | Generates and downloads audit CSV reports respecting active filters |

### 3. CSV Export Reports
The system provides on-demand CSV exports without exposing SMTP passwords or secrets:
- **Complete Audit History (`export_type=complete`):**
  Full message execution log including `Log ID`, `Execution Key`, `Mode`, `Status`, `Recipient Email`, `Subject`, `Campaign Name`, `Attempt Count`, `Error Category`, `RFC 5322 Message-ID`, `SMTP Queue ID`, and `Executed At (UTC)`.
- **Campaign Performance Summary (`export_type=campaigns`):**
  Fulfillment metrics per campaign (Targeted, Logged, Simulated, Accepted, Confirmed, Failed, Retrying, Uncertain).
- **Failed Executions Report (`export_type=failures`):**
  Isolated failure diagnostics log for fast debugging and post-mortem analysis.
- **Uncertain Delivery Records (`export_type=uncertain`):**
  Post-submission timeout records requiring manual gateway verification.

```bash
# Example: Download complete execution report filtered to live failures
curl -o failures_audit.csv "http://localhost:8000/api/analytics/export?export_type=failures&execution_mode=LIVE_SMTP"
```

### 4. UI Dashboard Screenshots
*(Placeholder section for visual dashboard previews)*
- **Overview & KPI Grid:** `docs/screenshots/phase7_kpi_overview.png`
- **Execution Trends & Status Distribution:** `docs/screenshots/phase7_trends_distribution.png`
- **Campaign Performance & Failure Diagnostics:** `docs/screenshots/phase7_campaign_performance.png`
- **Paginated Activity Table & CSV Export:** `docs/screenshots/phase7_activity_table.png`

---

## 🛡️ Phase 8: Security Hardening & End-to-End Validation

The system has undergone a comprehensive security audit and end-to-end reliability verification across all layers:

### 1. Security Mitigations Implemented
- **CSV Formula Injection Mitigation (CWE-1236):**
  All user-controllable text exported to CSV files (Analytics reports, Employee exports, Delivery reports) is sanitized against formula injection. Any string starting with `= , + , - , @ , \t , \r` is prepended with a single quote (`'`), ensuring spreadsheet software (Excel, LibreOffice Calc) treats it strictly as safe text.
- **SMTP Header Injection / CRLF Defense (CWE-93):**
  Carriage returns (`\r`) and line feeds (`\n`) are stripped from email subjects, sender/recipient addresses, and custom headers in `SMTPClient` and `EmailSender`, preventing header injection, Bcc leakage, or MIME envelope manipulation.
- **Stored XSS Elimination (Frontend Sandboxing):**
  Template and campaign HTML previews in the Next.js frontend are rendered inside an isolated `<iframe>` with an empty sandbox (`sandbox=""` and `srcDoc={rendered_html}`). JavaScript execution and cross-origin access are completely blocked by the browser.
- **Jinja2 Sandboxed Execution:**
  Template parsing enforces `jinja2.sandbox.SandboxedEnvironment` with `autoescape=True` and `undefined=StrictUndefined`. Access to dangerous Python internals (`__class__`, `__mro__`, `__subclasses__`) is blocked at runtime.
- **Fail-Closed Live Delivery Policy:**
  Live email dispatch across CLI (`main.py --send-real`, `worker.py --live`), Background Worker (`BackgroundWorker(simulation_mode=False)`), Service Layer (`scheduling_service`), Mailer (`EmailSender(dry_run=False)`), and API endpoints (`POST /dispatch-batch`, `POST /api/scheduler/trigger`) strictly fails closed unless explicit confirmation (`confirm_live=true` / `CONFIRM_LIVE_DELIVERY=true`) is provided.
- **CSV File Upload Limitations:**
  Employee CSV imports (`POST /api/employees/import-csv`) enforce file format checks (`.csv`) and a strict 10MB file size limit (`HTTP 413 Content Too Large`), mitigating resource exhaustion / DoS attacks.
- **CORS Hardening & Zero Credential Disclosure:**
  Cross-Origin Resource Sharing is configurable via `CORS_ORIGINS` (defaults to frontend port 3000) and disallows credentials when wildcards are active. API endpoints and exported reports guarantee zero exposure of SMTP passwords, connection strings, or system secrets.

### 2. Comprehensive Test Verification
Execute the dedicated security and end-to-end test suite:
```bash
python -m unittest tests/test_phase8_security_e2e.py
```

Run the complete repository regression test suite (114 tests, 100% pass):
```bash
python -m unittest discover tests
```

---

## 🎨 Phase 9: Enterprise SaaS UI/UX Transformation

The frontend was completely transformed from a basic internal admin interface into an enterprise-grade commercial SaaS web application built with **Next.js 14**, **Tailwind CSS**, and **Lucide React**.

### 1. Enterprise Design System & Tokens
- **Primary Color Palette:**
  - Deep Navy Sidebar: `#172554` (Solid contrast with white brand typography)
  - Primary Indigo Accent: `#4F46E5` / `#3730A3`
  - Teal Secondary Accent: `#0D9488`
  - Clean Slate Surface: `#F8FAFC` / `#F1F5F9`
  - Card & Container Radius: `rounded-2xl` with subtle border `border-slate-200/80` and crisp shadows
- **Typography:** Inter sans-serif typeface with strict hierarchy (`tracking-tight` headings, uppercase micro-labels with `tracking-wider`).
- **Icons:** Comprehensive icon system using `lucide-react` across navigation, metric cards, actions, and status badges.

### 2. Standardized UI Components
- **`AppLayout` & `Sidebar`:** Deep Navy sidebar with responsive collapse drawer for mobile, active route indicators, brand identity, and Simulation Mode pulse indicator.
- **`Header`:** Clean top bar with dynamic breadcrumb trail, page titles, simulation safety indicator, and action buttons.
- **`KPICard`:** Standardized metric presentation with Lucide iconography, accent colors, trend indicators, and loading skeletons.
- **`StatusBadge`:** Unified badges for 13 distinct workflow states (`SIMULATED_SUCCESS`, `SMTP_ACCEPTED`, `DELIVERY_CONFIRMED`, `ACTIVE`, `COMPLETED`, `READY`, `SCHEDULED`, `PROCESSING`, `DRAFT`, `RETRY_PENDING`, `FAILED`, `DELIVERY_UNCERTAIN`, `INACTIVE`).
- **`Drawer` & `Modal`:** Accessible sliding drawer and centered modal overlays with backdrop blur and escape key handlers for deep record inspection.
- **`SearchInput` & `Button`:** Standardized search bar with instant clear action and multi-variant buttons with loading spinners.
- **`EmptyState`:** Contextual empty state displays with actionable guidance.

### 3. Application Navigation & Pages
1. **Overview & Dispatch Console (`/`):** High-level KPI summary, Simulation vs Live SMTP dispatch mode selector with fail-closed safety warnings, manual trigger buttons, registered employee quick view, active reminder preview, and recent execution stream.
2. **Corporate Employee Directory (`/employees`):** Full workforce management, search and department/status filtering, paginated employee table, CSV import modal with audit statistics, and add/edit employee modals.
3. **Campaign Studio (`/campaigns`):** 4-step Campaign Creation Wizard (Details → Template Selection → Recipient Targeting with select-all/filtered selection → Schedule & Sandboxed Preview), campaign directory, and campaign detail slide-over drawer.
4. **Scheduled Reminders (`/reminders`):** Background worker trigger monitor, active personal reminders, recurring cron/rrule jobs, timezone indicators, status filters, and job inspection drawer.
5. **Template Studio & Jinja2 Previews (`/templates`):** Split-screen workspace featuring a template library catalog, Jinja2 syntax validation, variable tag insertion panel, recipient persona switcher, and sandboxed `<iframe>` live preview.
6. **Delivery Analytics & Reporting (`/analytics`):** 8 core KPI cards, daily delivery volume trends bar chart, status percentage distribution, campaign performance table, failure root-cause analysis, and sanitized CSV exports.
7. **Delivery Audit Logs (`/logs`):** Dedicated chronological audit trail, technical message identifiers (RFC 5322 Message-ID, SMTP Queue ID, Provider ID) with copy buttons, and full failure diagnostics.

### 4. Running the Web Application
```bash
# Start backend API (FastAPI)
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000

# Start frontend dashboard (Next.js)
npm --prefix apps/web run dev
# Or build and run production server:
npm --prefix apps/web run build
npm --prefix apps/web run start
```
Open [http://localhost:3000](http://localhost:3000) to access the application.

---

## 🔒 Safe GitHub Best Practices

To ensure complete cybersecurity and compliance when publishing this project on GitHub:
1. **Never Commit Passwords:** Real passwords and `.env` files must be included in `.gitignore`.
2. **Provide `.env.example`:** Commit an example configuration with placeholder values so other developers know which keys are required.
3. **Commit Clean Sample Data:** Only commit dummy emails (`@example.com`) to avoid leaking real people's contact details.
4. **Track Folder Structure:** Use `.gitkeep` files in empty directories (`logs/`, `outputs/previews/`) so git tracks the folder hierarchy.

---

## 🎯 Interview Preparation Guide

### Top 10 Technical & HR Questions
1. **"Explain your project."**
   - *Answer:* "I engineered an automated email and scheduled reminder system in Python that automates recurring business notifications (meetings, invoices, webinars). It ingests recipient data and reminder schedules from CSV files, dynamically personalizes HTML email templates, dispatches notifications using SMTP with TLS encryption, and provides full observability via structured logging and CSV delivery reports. It also features a zero-risk dry-run mode for local simulation."
2. **"What happens if an email address in the CSV is malformed or invalid?"**
   - *Answer:* "The `src/data_loader.py` module applies regex email validation during data ingestion. If an address fails validation, it logs a warning, skips the faulty record without crashing the execution cycle, and records a failed status in the audit log."
3. **"Why did you use environment variables instead of hardcoding credentials?"**
   - *Answer:* "Hardcoding credentials violates 12-factor application security best practices and risks credential leaks on public Git repositories. Storing credentials in `.env` and referencing them via `os.getenv` keeps secrets separated from source code."
4. **"How do you handle SMTP network timeouts or authentication failures?"**
   - *Answer:* "The `src/mailer.py` module wraps network transport calls in a granular `try-except` block catching `smtplib.SMTPAuthenticationError`, `smtplib.SMTPConnectError`, and general socket exceptions. The error is logged and written to the CSV report, allowing the system to continue processing subsequent recipients."
5. **"What is the difference between dry-run mode and live dispatch?"**
   - *Answer:* "Dry-run mode renders the personalized HTML content and writes it directly to disk (`outputs/previews/`) with full logging and audit tracking, verifying the business logic without initiating external network calls or incurring SMTP quotas."

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
