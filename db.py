import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("cleaning_demo.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                service_type TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                time_window TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_state (
                phone TEXT PRIMARY KEY,
                last_intent TEXT,
                pending_date TEXT,
                pending_time_window TEXT,
                pending_service TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
