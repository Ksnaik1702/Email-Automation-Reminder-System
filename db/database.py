"""
Database initialization and connection management using SQLite.
Uses Python's built-in sqlite3 standard library with dictionary row access.
"""
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
DB_FILE = DB_DIR / "email.db"
SCHEMA_FILE = DB_DIR / "schema.sql"

def get_connection():
    """Returns an active SQLite connection configured with Row factory."""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes database schema from schema.sql if not already present."""
    conn = get_connection()
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database successfully initialized at {DB_FILE}")
