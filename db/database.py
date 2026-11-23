"""
Centralized Database Engine & Session Management using SQLAlchemy.
Configured for cross-platform portability with configurable DATABASE_URL,
project-relative SQLite paths, and foreign key enforcement.
"""
import sys
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

# Ensure project root is in sys.path dynamically
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base

# Portable Database URL Configuration
# 1. Use DATABASE_URL from environment if provided (e.g. for PostgreSQL, custom path, or testing)
# 2. Otherwise default to a portable, project-relative SQLite path
DEFAULT_DB_FILE = PROJECT_ROOT / "db" / "email.db"
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Ensure directory exists
    DEFAULT_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

# Configure engine arguments based on dialect
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Enforce SQLite foreign key constraints dynamically whenever connecting to SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

# Central Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes and creates all declarative tables if they do not exist."""
    Base.metadata.create_all(bind=engine)

    # Safe SQLite auto-migration for newly added columns in message_logs
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                cursor = conn.connection.cursor()
                cursor.execute("PRAGMA table_info(message_logs)")
                existing_cols = {row[1] for row in cursor.fetchall()}

                migrations = [
                    ("template_id", "INTEGER REFERENCES email_templates(id) ON DELETE SET NULL"),
                    ("execution_mode", "VARCHAR(20) DEFAULT 'SIMULATION' NOT NULL"),
                    ("attempt_count", "INTEGER DEFAULT 1 NOT NULL"),
                    ("smtp_response", "VARCHAR(255)"),
                    ("message_id", "VARCHAR(150)"),
                    ("smtp_queue_id", "VARCHAR(150)"),
                    ("provider_message_id", "VARCHAR(150)"),
                    ("error_category", "VARCHAR(50)"),
                    ("next_retry_at", "DATETIME")
                ]

                for col_name, col_def in migrations:
                    if col_name not in existing_cols:
                        cursor.execute(f"ALTER TABLE message_logs ADD COLUMN {col_name} {col_def}")

                # Non-destructive data migration:
                # If provider_message_id contains a locally generated RFC 5322 Message-ID (<...@...>),
                # move it to message_id and set provider_message_id to NULL.
                cursor.execute("""
                    UPDATE message_logs
                    SET message_id = provider_message_id, provider_message_id = NULL
                    WHERE (message_id IS NULL OR message_id = '')
                      AND provider_message_id IS NOT NULL
                      AND (provider_message_id LIKE '<%@%>' OR provider_message_id LIKE '%@%')
                """)
                conn.connection.commit()
                cursor.close()
        except Exception:
            pass

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for standalone scripts, workers, and background jobs."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Backward compatibility helper for legacy code
def get_connection():
    """Returns a raw sqlite3 connection with Row factory."""
    db_path = DEFAULT_DB_FILE
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

if __name__ == "__main__":
    init_db()
    print(f"SQLAlchemy ORM tables initialized successfully using URL: {DATABASE_URL}")
