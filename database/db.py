import sqlite3
from datetime import datetime, timedelta
from threading import Lock


DB_NAME = "flux_ai.db"
DB_LOCK = Lock()


def get_connection():
    connection = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    return connection


conn = get_connection()


def column_exists(table_name, column_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in rows
    )


def init_db():
    with DB_LOCK:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            plan TEXT DEFAULT 'FREE',
            pro_until TEXT,
            language TEXT DEFAULT 'ru',
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

        if not column_exists(
            "users",
            "language",
        ):
            conn.execute(
                "ALTER TABLE users "
                "ADD COLUMN language "
                "TEXT DEFAULT 'ru'"
            )

        conn.commit()


def add_user(user):
    if not user:
        return

    user_id = user.get("id")

    if not user_id:
        return

    with DB_LOCK:
        conn.execute("""
        INSERT OR IGNORE INTO users
        (
            telegram_id,
            username,
            first_name,
            language,
            created_at
        )
        VALUES (?, ?, ?, 'ru', ?)
        """, (
            user_id,
            user.get("username"),
            user.get("first_name"),
            datetime.utcnow().isoformat(),
        ))

        conn.execute("""
        UPDATE users
        SET username=?,
            first_name=?
        WHERE telegram_id=?
        """, (
            user.get("username"),
            user.get("first_name"),
            user_id,
        ))

        conn.commit()


def set_user_language(
    user_id,
    language,
):
    if language not in {"ru", "en"}:
        language = "ru"

    with DB_LOCK:
        conn.execute("""
        UPDATE users
        SET language=?
        WHERE telegram_id=?
        """, (
            language,
            user_id,
        ))

        conn.commit()


def get_user_language(user_id):
    if not user_id:
        return "ru"

    row = conn.execute("""
    SELECT language
    FROM users
    WHERE telegram_id=?
    """, (
        user_id,
    )).fetchone()

    if not row:
        return "ru"

    language = row["language"]

    if language not in {"ru", "en"}:
        return "ru"

    return language


def activate_pro(
    user_id,
    days=30,
):
    until = (
        datetime.utcnow()
        + timedelta(days=days)
    ).isoformat()

    with DB_LOCK:
        conn.execute("""
        UPDATE users
        SET plan='PRO',
            pro_until=?
        WHERE telegram_id=?
        """, (
            until,
            user_id,
        ))

        conn.commit()


def is_pro(user_id):
    row = conn.execute("""
    SELECT plan, pro_until
    FROM users
    WHERE telegram_id=?
    """, (
        user_id,
    )).fetchone()

    if not row:
        return False

    if (
        row["plan"] != "PRO"
        or not row["pro_until"]
    ):
        return False

    try:
        active = (
            datetime.fromisoformat(
                row["pro_until"]
            )
            > datetime.utcnow()
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if not active:
        with DB_LOCK:
            conn.execute("""
            UPDATE users
            SET plan='FREE'
            WHERE telegram_id=?
            """, (
                user_id,
            ))

            conn.commit()

    return active


def get_user(user_id):
    return conn.execute("""
    SELECT *
    FROM users
    WHERE telegram_id=?
    """, (
        user_id,
    )).fetchone()


def save_prediction(
    user_id,
    match_name,
    prediction,
):
    with DB_LOCK:
        conn.execute("""
        INSERT INTO predictions
        (
            telegram_id,
            match_name,
            prediction,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            match_name,
            prediction,
            datetime.utcnow().isoformat(),
        ))

        conn.commit()


def get_predictions(
    user_id,
    limit=20,
):
    return conn.execute("""
    SELECT *
    FROM predictions
    WHERE telegram_id=?
    ORDER BY id DESC
    LIMIT ?
    """, (
        user_id,
        limit,
    )).fetchall()


def save_payment(
    user_id,
    provider="telegram_stars",
    amount=0,
    currency="XTR",
    status="paid",
):
    with DB_LOCK:
        conn.execute("""
        INSERT INTO payments
        (
            telegram_id,
            provider,
            amount,
            currency,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            provider,
            amount,
            currency,
            status,
            datetime.utcnow().isoformat(),
        ))

        conn.commit()


def get_today_key():
    return datetime.utcnow().strftime(
        "%Y-%m-%d"
    )


def get_today_usage(user_id):
    day = get_today_key()

    row = conn.execute("""
    SELECT analyses
    FROM usage
    WHERE telegram_id=?
    AND day=?
    """, (
        user_id,
        day,
    )).fetchone()

    if not row:
        return 0

    return int(
        row["analyses"]
    )


def increase_today_usage(user_id):
    day = get_today_key()

    with DB_LOCK:
        conn.execute("""
        INSERT OR IGNORE INTO usage
        (
            telegram_id,
            day,
            analyses
        )
        VALUES (?, ?, 0)
        """, (
            user_id,
            day,
        ))

        conn.execute("""
        UPDATE usage
        SET analyses = analyses + 1
        WHERE telegram_id=?
        AND day=?
        """, (
            user_id,
            day,
        ))

        conn.commit()


def free_limit_message(
    language="ru",
):
    if language == "en":
        return (
            "🔒 You have used all "
            "2 free analyses for today.\n\n"
            "Activate FLUX AI PRO "
            "and get:\n"
            "✅ Unlimited match analysis\n"
            "✅ Extended statistics\n"
            "✅ Daily Top 3 predictions\n"
            "✅ World Cup analysis\n"
            "✅ New PRO features\n\n"
            "Press 💎 FLUX PRO "
            "in the menu."
        )

    return (
        "🔒 Вы использовали все "
        "2 бесплатных анализа на сегодня.\n\n"
        "Оформите FLUX AI PRO "
        "и получите:\n"
        "✅ Безлимитный анализ матчей\n"
        "✅ Расширенную статистику\n"
        "✅ ТОП-3 прогнозов дня\n"
        "✅ Анализ матчей ЧМ\n"
        "✅ Новые PRO-функции\n\n"
        "Нажмите кнопку 💎 FLUX PRO "
        "в меню."
    )


def get_admin_stats():
    now = datetime.utcnow().isoformat()

    total_users = conn.execute("""
    SELECT COUNT(*) AS count
    FROM users
    """).fetchone()["count"]

    active_pro = conn.execute("""
    SELECT COUNT(*) AS count
    FROM users
    WHERE plan='PRO'
    AND pro_until IS NOT NULL
    AND pro_until > ?
    """, (
        now,
    )).fetchone()["count"]

    total_payments = conn.execute("""
    SELECT COUNT(*) AS count
    FROM payments
    WHERE status='paid'
    """).fetchone()["count"]

    return {
        "total_users": total_users,
        "active_pro": active_pro,
        "total_payments": total_payments,
    }


init_db()
