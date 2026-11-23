"""
Centralized Database Engine & Session Management using SQLAlchemy.
Configured for SQLite with foreign key enforcement and connection pooling.
"""
import sys
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base

DB_DIR = Path(__file__).resolve().parent
DB_FILE = DB_DIR / "email.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"

# Engine with SQLite specific multi-threading allowances
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enforce SQLite foreign key constraints
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

# Session Factory
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
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

if __name__ == "__main__":
    init_db()
    print(f"SQLAlchemy ORM tables initialized successfully at {DB_FILE}")
