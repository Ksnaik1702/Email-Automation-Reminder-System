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
