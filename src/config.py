"""
Configuration management using environment variables.
Provides fallback safe defaults for simulation / dry-run mode.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'db' / 'email.db').as_posix()}")

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "demo.student@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Operations Reminder Desk")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)

# Execution flags
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")

# Paths
DATA_DIR = BASE_DIR / "data"
CONTACTS_FILE = DATA_DIR / "contacts.csv"
REMINDERS_FILE = DATA_DIR / "reminders.csv"
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "outputs"
PREVIEWS_DIR = OUTPUTS_DIR / "previews"
REPORT_FILE = OUTPUTS_DIR / "delivery_report.csv"

# Ensure runtime directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
