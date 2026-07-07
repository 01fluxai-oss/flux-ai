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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS usage (
        telegram_id INTEGER,
        day TEXT,
        analyses INTEGER DEFAULT 0,
        PRIMARY KEY (telegram_id, day)
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

    try:
        return datetime.fromisoformat(row["pro_until"]) > datetime.utcnow()
    except Exception:
        return False


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


def save_payment(user_id, provider="stripe", amount=9.99, currency="USD", status="paid"):
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


def get_today_key():
    return datetime.utcnow().strftime("%Y-%m-%d")


def get_today_usage(user_id):
    day = get_today_key()

    row = conn.execute("""
    SELECT analyses
    FROM usage
    WHERE telegram_id=? AND day=?
    """, (user_id, day)).fetchone()

    if row:
        return int(row["analyses"])

    return 0


def increase_today_usage(user_id):
    day = get_today_key()

    conn.execute("""
    INSERT OR IGNORE INTO usage
    (telegram_id, day, analyses)
    VALUES (?, ?, 0)
    """, (user_id, day))

    conn.execute("""
    UPDATE usage
    SET analyses = analyses + 1
    WHERE telegram_id=? AND day=?
    """, (user_id, day))

    conn.commit()


def can_analyze(user_id):
    if is_pro(user_id):
        return True

    return get_today_usage(user_id) < 2


def free_limit_message():
    return (
        "🔒 Вы использовали все 2 бесплатных анализа на сегодня.\n\n"
        "Оформите FLUX AI PRO и получите:\n"
        "✅ Безлимитный анализ матчей\n"
        "✅ Расширенную статистику\n"
        "✅ ТОП-3 прогнозов дня\n"
        "✅ Прогнозы ЧМ-2026\n"
        "✅ Все новые PRO-функции\n\n"
        "💎 Стоимость: $9.99 / месяц\n\n"
        "Нажмите кнопку 💎 FLUX PRO в меню."
    )


init_db()
