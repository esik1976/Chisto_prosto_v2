import sqlite3
from pathlib import Path

DB_PATH = Path("data/app.db")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                description TEXT,
                price INTEGER,
                status TEXT,
                assignee TEXT,
                paid INTEGER
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "latitude" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN latitude REAL")
        if "longitude" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN longitude REAL")
        if "customer_id" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN customer_id INTEGER")
        if "payment_status" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'not_started'")
        if "payment_id" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_id TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                actor TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
