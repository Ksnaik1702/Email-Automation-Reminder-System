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
11. [Safe GitHub Best Practices](#-safe-github-best-practices)
12. [Interview Preparation Guide](#-interview-preparation-guide)

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
The system strictly distinguishes between SMTP acceptance and inbox delivery:
- `SIMULATED_SUCCESS`: Email successfully rendered and saved to local previews (Simulation Mode).
- `SMTP_ACCEPTED`: Upstream SMTP relay accepted the message (`250 OK`) into its transmission queue.
- `RETRY_PENDING`: Temporary failure encountered; scheduled for automated retry with exponential backoff.
- `SKIPPED_INACTIVE`: Recipient employee is not active (`employment_status != 'Active'`); delivery prevented.
- `FAILED`: Permanent error encountered (e.g., auth failure, invalid recipient format) or max retries exceeded.
- `DELIVERY_CONFIRMED`: Reserved for downstream webhook delivery receipts (SendGrid/Mailgun).

### 2. Error Categorization & Retry Backoff
- **Temporary Errors (`TEMPORARY_NETWORK_ERROR`, `TEMPORARY_RATE_LIMIT`):**
  - Socket timeouts, 421 Service not available, 450 Mailbox busy, 451 Local error.
  - Automatically retried with exponential backoff: $T_{\text{wait}} = \text{backoff\_base} \times 2^{(\text{attempt} - 1)}$.
  - Maximum retry attempts default to 3 before marking as `FAILED`.
- **Permanent Errors (`AUTHENTICATION_FAILED`, `INVALID_RECIPIENT_ADDRESS`, `RECIPIENT_REJECTED`):**
  - Invalid SMTP login credentials, malformed email addresses (e.g. missing `@` or domain), 550 Mailbox not found.
  - Immediately marked `FAILED` without retrying.

### 3. Unified Audit Log Schema (`message_logs`)
Every execution records 18 diagnostic columns in the centralized SQLite database:
`id`, `campaign_id`, `reminder_id`, `employee_id`, `template_id`, `recipient_email`, `subject`, `execution_key`, `execution_mode`, `execution_status`, `attempt_count`, `smtp_response`, `provider_message_id`, `error_category`, `error_message`, `scheduled_at`, `executed_at`, `next_retry_at`.
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
