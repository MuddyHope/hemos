import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "health.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table_name, column_name, column_def):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {col["name"] for col in cols}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


init_conn = get_db()
init_cur = init_conn.cursor()

init_cur.execute("""
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    timestamp TEXT,
    heart_rate REAL,
    body_temperature REAL
)
""")

init_cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL
)
""")

init_cur.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    sex TEXT,
    smoking_status TEXT,
    age INTEGER,
    height_cm REAL,
    weight_kg REAL,
    preferred_unit TEXT DEFAULT 'metric',
    created_at TEXT NOT NULL
)
""")

ensure_column(init_conn, "patients", "height_ft", "INTEGER")
ensure_column(init_conn, "patients", "height_in", "INTEGER")
ensure_column(init_conn, "patients", "weight_lb", "REAL")

init_cur.execute(
    "INSERT OR IGNORE INTO users (username, password, full_name) VALUES (?, ?, ?)",
    ("demo", "demo123", "Demo Patient")
)

init_conn.commit()
init_conn.close()