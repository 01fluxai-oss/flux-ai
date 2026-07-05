import sqlite3
from datetime import datetime, timedelta

DB_NAME = "flux_ai.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = get_connection()


def init_db():
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        plan TEXT DEFAULT 'FREE',
        pro_until TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        provider TEXT,
        amount REAL,
        currency TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        match_name TEXT,
        prediction TEXT,
        created_at TEXT
    )
    """)

    conn.commit()


def add_user(user):
    conn.execute("""
    INSERT OR IGNORE INTO users
    (telegram_id, username, first_name, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        user["id"],
        user.get("username"),
        user.get("first_name"),
        datetime.utcnow().isoformat()
    ))

    conn.commit()


def activate_pro(user_id, days=30):
    until = (datetime.utcnow() + timedelta(days=days)).isoformat()

    conn.execute("""
    UPDATE users
    SET plan='PRO',
        pro_until=?
    WHERE telegram_id=?
    """, (until, user_id))

    conn.commit()


def is_pro(user_id):
    row = conn.execute("""
    SELECT plan, pro_until
    FROM users
    WHERE telegram_id=?
    """, (user_id,)).fetchone()

    if not row:
        return False

    if row["plan"] != "PRO":
        return False

    if not row["pro_until"]:
        return False

    return datetime.fromisoformat(row["pro_until"]) > datetime.utcnow()


def get_user(user_id):
    return conn.execute("""
    SELECT *
    FROM users
    WHERE telegram_id=?
    """, (user_id,)).fetchone()


def save_prediction(user_id, match_name, prediction):
    conn.execute("""
    INSERT INTO predictions
    (telegram_id, match_name, prediction, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        match_name,
        prediction,
        datetime.utcnow().isoformat()
    ))

    conn.commit()


def get_predictions(user_id, limit=20):
    return conn.execute("""
    SELECT *
    FROM predictions
    WHERE telegram_id=?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit)).fetchall()


def save_payment(user_id, provider, amount, currency, status):
    conn.execute("""
    INSERT INTO payments
    (telegram_id, provider, amount, currency, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        provider,
        amount,
        currency,
        status,
        datetime.utcnow().isoformat()
    ))

    conn.commit()


init_db()
