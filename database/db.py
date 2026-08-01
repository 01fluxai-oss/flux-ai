import os
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row


DATABASE_URL = os.environ["DATABASE_URL"]

VALID_LANGUAGES = {"ru", "en"}
VALID_SPORTS = {"football", "nba", "tennis"}


def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=15,
    )


def utc_now():
    return datetime.now(timezone.utc)


def init_db():
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        telegram_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        plan TEXT DEFAULT 'FREE',
                        pro_until TIMESTAMPTZ,
                        language TEXT DEFAULT 'ru',
                        sport TEXT DEFAULT 'football',
                        created_at TIMESTAMPTZ
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id BIGSERIAL PRIMARY KEY,
                        telegram_id BIGINT,
                        provider TEXT,
                        amount NUMERIC,
                        currency TEXT,
                        status TEXT,
                        created_at TIMESTAMPTZ
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id BIGSERIAL PRIMARY KEY,
                        telegram_id BIGINT,
                        match_name TEXT,
                        prediction TEXT,
                        created_at TIMESTAMPTZ
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usage (
                        telegram_id BIGINT,
                        day TEXT,
                        analyses INTEGER DEFAULT 0,
                        PRIMARY KEY (
                            telegram_id,
                            day
                        )
                    )
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS language
                    TEXT DEFAULT 'ru'
                """)

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS sport
                    TEXT DEFAULT 'football'
                """)

                cursor.execute("""
                    UPDATE users
                    SET language = 'ru'
                    WHERE language IS NULL
                    OR language NOT IN ('ru', 'en')
                """)

                cursor.execute("""
                    UPDATE users
                    SET sport = 'football'
                    WHERE sport IS NULL
                    OR sport NOT IN (
                        'football',
                        'nba',
                        'tennis'
                    )
                """)

    finally:
        connection.close()


def add_user(user):
    if not user:
        return

    user_id = user.get("id")

    if not user_id:
        return

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (
                        telegram_id,
                        username,
                        first_name,
                        language,
                        sport,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        'ru',
                        'football',
                        %s
                    )
                    ON CONFLICT (telegram_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name
                """, (
                    user_id,
                    user.get("username"),
                    user.get("first_name"),
                    utc_now(),
                ))

    finally:
        connection.close()


def set_user_language(user_id, language):
    if not user_id:
        return

    if language not in VALID_LANGUAGES:
        language = "ru"

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET language = %s
                    WHERE telegram_id = %s
                """, (
                    language,
                    user_id,
                ))

    finally:
        connection.close()


def get_user_language(user_id):
    if not user_id:
        return "ru"

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT language
                FROM users
                WHERE telegram_id = %s
            """, (
                user_id,
            ))

            row = cursor.fetchone()

    finally:
        connection.close()

    if not row:
        return "ru"

    language = row.get("language")

    if language not in VALID_LANGUAGES:
        return "ru"

    return language


def set_user_sport(user_id, sport):
    if not user_id:
        return

    sport = str(sport or "").strip().lower()

    if sport not in VALID_SPORTS:
        sport = "football"

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET sport = %s
                    WHERE telegram_id = %s
                """, (
                    sport,
                    user_id,
                ))

    finally:
        connection.close()


def get_user_sport(user_id):
    if not user_id:
        return "football"

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT sport
                FROM users
                WHERE telegram_id = %s
            """, (
                user_id,
            ))

            row = cursor.fetchone()

    finally:
        connection.close()

    if not row:
        return "football"

    sport = str(row.get("sport") or "").strip().lower()

    if sport not in VALID_SPORTS:
        return "football"

    return sport


def activate_pro(user_id, days=30):
    pro_until = utc_now() + timedelta(days=days)
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET
                        plan = 'PRO',
                        pro_until = %s
                    WHERE telegram_id = %s
                """, (
                    pro_until,
                    user_id,
                ))

    finally:
        connection.close()


def is_pro(user_id):
    if not user_id:
        return False

    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        plan,
                        pro_until
                    FROM users
                    WHERE telegram_id = %s
                """, (
                    user_id,
                ))

                row = cursor.fetchone()

                if not row:
                    return False

                if (
                    row.get("plan") != "PRO"
                    or not row.get("pro_until")
                ):
                    return False

                active = row["pro_until"] > utc_now()

                if not active:
                    cursor.execute("""
                        UPDATE users
                        SET
                            plan = 'FREE',
                            pro_until = NULL
                        WHERE telegram_id = %s
                    """, (
                        user_id,
                    ))

                return active

    finally:
        connection.close()


def get_user(user_id):
    if not user_id:
        return None

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM users
                WHERE telegram_id = %s
            """, (
                user_id,
            ))

            return cursor.fetchone()

    finally:
        connection.close()


def save_prediction(user_id, match_name, prediction):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO predictions (
                        telegram_id,
                        match_name,
                        prediction,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    user_id,
                    match_name,
                    prediction,
                    utc_now(),
                ))

    finally:
        connection.close()


def get_predictions(user_id, limit=20):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM predictions
                WHERE telegram_id = %s
                ORDER BY id DESC
                LIMIT %s
            """, (
                user_id,
                limit,
            ))

            return cursor.fetchall()

    finally:
        connection.close()


def save_payment(
    user_id,
    provider="telegram_stars",
    amount=0,
    currency="XTR",
    status="paid",
):
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO payments (
                        telegram_id,
                        provider,
                        amount,
                        currency,
                        status,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    user_id,
                    provider,
                    amount,
                    currency,
                    status,
                    utc_now(),
                ))

    finally:
        connection.close()


def get_today_key():
    return utc_now().strftime("%Y-%m-%d")


def get_today_usage(user_id):
    day = get_today_key()
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT analyses
                FROM usage
                WHERE telegram_id = %s
                AND day = %s
            """, (
                user_id,
                day,
            ))

            row = cursor.fetchone()

    finally:
        connection.close()

    if not row:
        return 0

    return int(row.get("analyses", 0))


def increase_today_usage(user_id):
    day = get_today_key()
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usage (
                        telegram_id,
                        day,
                        analyses
                    )
                    VALUES (
                        %s,
                        %s,
                        1
                    )
                    ON CONFLICT (
                        telegram_id,
                        day
                    )
                    DO UPDATE SET
                        analyses = usage.analyses + 1
                """, (
                    user_id,
                    day,
                ))

    finally:
        connection.close()


def free_limit_message(language="ru"):
    if language == "en":
        return (
            "ð You have reached today's free analysis limit.\n\n"
            "Activate FLUX AI PRO and get:\n"
            "â Unlimited sports analysis\n"
            "â Football, NBA and Tennis analysis\n"
            "â Extended statistics\n"
            "â Daily Top 3 predictions\n"
            "â New PRO features\n\n"
            "Press ð FLUX PRO in the menu."
        )

    return (
        "ð ÐÑ Ð´Ð¾ÑÑÐ¸Ð³Ð»Ð¸ Ð´Ð½ÐµÐ²Ð½Ð¾Ð³Ð¾ Ð»Ð¸Ð¼Ð¸ÑÐ° Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½ÑÑ Ð°Ð½Ð°Ð»Ð¸Ð·Ð¾Ð².\n\n"
        "ÐÑÐ¾ÑÐ¼Ð¸ÑÐµ FLUX AI PRO Ð¸ Ð¿Ð¾Ð»ÑÑÐ¸ÑÐµ:\n"
        "â ÐÐµÐ·Ð»Ð¸Ð¼Ð¸ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð· ÑÐ¿Ð¾ÑÑÐ°\n"
        "â ÐÐ½Ð°Ð»Ð¸Ð· ÑÑÑÐ±Ð¾Ð»Ð°, NBA Ð¸ ÑÐµÐ½Ð½Ð¸ÑÐ°\n"
        "â Ð Ð°ÑÑÐ¸ÑÐµÐ½Ð½ÑÑ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÑ\n"
        "â Ð¢ÐÐ-3 Ð¿ÑÐ¾Ð³Ð½Ð¾Ð·Ð¾Ð² Ð´Ð½Ñ\n"
        "â ÐÐ¾Ð²ÑÐµ PRO-ÑÑÐ½ÐºÑÐ¸Ð¸\n\n"
        "ÐÐ°Ð¶Ð¼Ð¸ÑÐµ ÐºÐ½Ð¾Ð¿ÐºÑ ð FLUX PRO Ð² Ð¼ÐµÐ½Ñ."
    )


def get_admin_stats():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM users
            """)
            total_users = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM users
                WHERE plan = 'PRO'
                AND pro_until IS NOT NULL
                AND pro_until > %s
            """, (
                utc_now(),
            ))
            active_pro = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM payments
                WHERE status = 'paid'
            """)
            total_payments = cursor.fetchone()["count"]

    finally:
        connection.close()

    return {
        "total_users": total_users,
        "active_pro": active_pro,
        "total_payments": total_payments,
    }
