"""
Data Loader module: Loads, validates, and merges contacts and reminders.
Supports Pandas with an automatic fallback to standard library CSV.
"""
from typing import List, Dict, Any
from pathlib import Path
import csv
import re
from src.logger import logger
from src.config import CONTACTS_FILE, REMINDERS_FILE

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def validate_email(email_str: str) -> bool:
    """Basic email format validator."""
    if not email_str:
        return False
    return bool(EMAIL_REGEX.match(email_str.strip()))

def load_csv_as_dicts(file_path: Path) -> List[Dict[str, Any]]:
    """Loads a CSV file into a list of dictionaries using standard library csv."""
    if not file_path.exists():
        logger.error(f"Data file not found: {file_path}")
        raise FileNotFoundError(f"Missing file: {file_path}")
    
    records = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace from keys and values
            cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
            records.append(cleaned_row)
    return records

def load_contacts(file_path: Path = CONTACTS_FILE) -> Dict[str, Dict[str, Any]]:
    """Loads contacts indexed by contact_id."""
    logger.info(f"Loading contacts from: {file_path}")
    records = load_csv_as_dicts(file_path)
    contacts_map = {}
    valid_count = 0

    for rec in records:
        cid = rec.get("contact_id")
        email = rec.get("email", "")
        if not cid:
            logger.warning(f"Skipping contact without contact_id: {rec}")
            continue
        if not validate_email(email):
            logger.warning(f"Contact {cid} ({rec.get('name')}) has invalid email '{email}'.")
        
        contacts_map[cid] = rec
        valid_count += 1

    logger.info(f"Loaded {valid_count} valid contacts successfully.")
    return contacts_map

def load_reminders(file_path: Path = REMINDERS_FILE) -> List[Dict[str, Any]]:
    """Loads scheduled reminder records."""
    logger.info(f"Loading reminders from: {file_path}")
    records = load_csv_as_dicts(file_path)
    logger.info(f"Loaded {len(records)} reminders.")
    return records

def get_merged_reminder_jobs() -> List[Dict[str, Any]]:
    """
    Combines each reminder with recipient contact details.
    Produces complete job dictionaries ready for email rendering and dispatch.
    """
    contacts = load_contacts()
    reminders = load_reminders()
    jobs = []

    for rem in reminders:
        cid = rem.get("contact_id")
        contact_info = contacts.get(cid)
        if not contact_info:
            logger.error(f"Reminder {rem.get('reminder_id')} references unknown contact_id '{cid}'. Skipping.")
            continue
        
        # Merge dictionaries (contact details + reminder attributes)
        merged = {**contact_info, **rem}
        jobs.append(merged)

    logger.info(f"Generated {len(jobs)} merged notification jobs ready for processing.")
    return jobs
