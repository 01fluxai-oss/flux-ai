import os
from threading import Thread

import requests
from flask import Flask, request

from database.db import (
    activate_pro,
    add_user,
    free_limit_message,
    get_admin_stats,
    get_today_usage,
    get_user,
    get_user_language,
    get_user_sport,
    increase_today_usage,
    init_db,
    is_pro,
    save_payment,
    save_prediction,
    set_user_language,
    set_user_sport,
)
from payments.stars import send_stars_invoice
from tennis_analyzer import analyze_tennis_match


BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get(
    "PUBLIC_URL",
    "https://flux-ai-8p34.onrender.com",
).rstrip("/")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"

FREE_DAILY_LIMIT = 10
PRO_PRICE_STARS = 500
PRO_DAYS = 30

app = Flask(__name__)
init_db()


def telegram_api(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, json=payload, timeout=20)

    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Telegram returned invalid JSON: {response.text[:500]}"
        ) from error

    if not response.ok or not result.get("ok"):
        raise RuntimeError(f"Telegram API error in {method}: {result}")

    return result


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        return telegram_api("sendMessage", payload)
    except Exception as error:
        print("SEND_MESSAGE_ERROR:", repr(error), flush=True)
        return None


def answer_callback_query(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}

    if text:
        payload["text"] = text

    try:
        return telegram_api("answerCallbackQuery", payload)
    except Exception as error:
        print("ANSWER_CALLBACK_ERROR:", repr(error), flush=True)
        return None


def answer_pre_checkout_query(query_id, approved, error_message=None):
    payload = {"pre_checkout_query_id": query_id, "ok": approved}

    if not approved and error_message:
        payload["error_message"] = error_message

    return telegram_api("answerPreCheckoutQuery", payload)


def language_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "ðºð¸ English", "callback_data": "lang_en"},
            {"text": "ð·ðº Ð ÑÑÑÐºÐ¸Ð¹", "callback_data": "lang_ru"},
        ]]
    }


def main_menu(language="ru"):
    if language == "en":
        keyboard = [
            ["â½ Football", "ð NBA"],
            ["ð¾ Tennis"],
            ["â½ Analyze Match"],
            ["ð Top 3 Today", "ð World Cup 2026"],
            ["ð Results"],
            ["ð Channel", "ð FLUX PRO"],
            ["ð¤ My Profile"],
            ["â¹ï¸ About", "ð Status"],
            ["ð Language"],
        ]
    else:
        keyboard = [
            ["â½ Ð¤ÑÑÐ±Ð¾Ð»", "ð NBA"],
            ["ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ"],
            ["â½ ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐ°"],
            ["ð Ð¢ÐÐ-3 Ð´Ð½Ñ", "ð Ð§Ð-2026"],
            ["ð Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ"],
            ["ð ÐÐ°Ð½Ð°Ð»", "ð FLUX PRO"],
            ["ð¤ ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ"],
            ["â¹ï¸ Ð Ð¿ÑÐ¾ÐµÐºÑÐµ", "ð Ð¡ÑÐ°ÑÑÑ"],
            ["ð Ð¯Ð·ÑÐº"],
        ]

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        str(text)
        .replace("â", "-")
        .replace("â", "-")
        .replace("â", "-")
        .strip()
    )


def detect_match(line):
    line = normalize_text(line)

    for separator in [" - ", " vs ", " VS ", " Vs ", " v ", " V ", "-"]:
        if separator not in line:
            continue

        parts = line.split(separator, 1)

        if len(parts) == 2:
            participant1 = parts[0].strip()
            participant2 = parts[1].strip()

            if participant1 and participant2:
                return participant1, participant2

    return None, None


def detect_matches(text):
    matches = []

    for line in str(text).splitlines():
        participant1, participant2 = detect_match(line.strip())

        if participant1 and participant2:
            matches.append((participant1, participant2))

    return matches


def sport_title(sport, language="ru"):
    titles = {
        "football": {"ru": "â½ Ð¤ÑÑÐ±Ð¾Ð»", "en": "â½ Football"},
        "nba": {"ru": "ð NBA", "en": "ð NBA"},
        "tennis": {"ru": "ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ", "en": "ð¾ Tennis"},
    }
    return titles.get(sport, titles["football"]).get(language, "â½ Ð¤ÑÑÐ±Ð¾Ð»")


def start_message(language="ru"):
    if language == "en":
        return (
            "ð Welcome! I am FLUX AI Sports PRO v4.0\n\n"
            "â½ Football analysis\n"
            "ð NBA analysis\n"
            "ð¾ Tennis analysis (Beta)\n"
            "ð Top 3 of the day\n"
            "ð World Cup analysis\n"
            "ð Results\n"
            "ð FLUX PRO\n\n"
            f"FREE: {FREE_DAILY_LIMIT} analyses per day\n"
            "PRO: unlimited\n\n"
            "Choose a sport, then send a matchup."
        )

    return (
        "ð ÐÑÐ¸Ð²ÐµÑ! Ð¯ FLUX AI Sports PRO v4.0\n\n"
        "â½ ÐÐ½Ð°Ð»Ð¸Ð· ÑÑÑÐ±Ð¾Ð»Ð°\n"
        "ð ÐÐ½Ð°Ð»Ð¸Ð· NBA\n"
        "ð¾ ÐÐ½Ð°Ð»Ð¸Ð· ÑÐµÐ½Ð½Ð¸ÑÐ° (Beta)\n"
        "ð Ð¢ÐÐ-3 Ð´Ð½Ñ\n"
        "ð ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐµÐ¹ Ð§Ð\n"
        "ð Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ\n"
        "ð FLUX PRO\n\n"
        f"FREE: {FREE_DAILY_LIMIT} Ð°Ð½Ð°Ð»Ð¸Ð·Ð¾Ð² Ð² Ð´ÐµÐ½Ñ\n"
        "PRO: Ð±ÐµÐ·Ð»Ð¸Ð¼Ð¸Ñ\n\n"
        "ÐÑÐ±ÐµÑÐ¸ Ð²Ð¸Ð´ ÑÐ¿Ð¾ÑÑÐ° Ð¸ Ð¾ÑÐ¿ÑÐ°Ð²Ñ Ð¼Ð°ÑÑ."
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "Choose a sport first:\n\n"
            "â½ Football:\nReal Madrid - Barcelona\n\n"
            "ð NBA:\nLakers - Celtics\n\n"
            "ð¾ Tennis:\nCarlos Alcaraz - Jannik Sinner\n\n"
            "You can send several matchups, one per line."
        )

    return (
        "Ð¡Ð½Ð°ÑÐ°Ð»Ð° Ð²ÑÐ±ÐµÑÐ¸ Ð²Ð¸Ð´ ÑÐ¿Ð¾ÑÑÐ°:\n\n"
        "â½ Ð¤ÑÑÐ±Ð¾Ð»:\nReal Madrid - Barcelona\n\n"
        "ð NBA:\nLakers - Celtics\n\n"
        "ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ:\nCarlos Alcaraz - Jannik Sinner\n\n"
        "ÐÐ¾Ð¶Ð½Ð¾ Ð¾ÑÐ¿ÑÐ°Ð²Ð¸ÑÑ Ð½ÐµÑÐºÐ¾Ð»ÑÐºÐ¾ Ð¼Ð°ÑÑÐµÐ¹ ÑÐ¿Ð¸ÑÐºÐ¾Ð¼."
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "â¹ï¸ FLUX AI is an AI-powered sports analysis bot.\n\n"
            "It analyzes football, NBA and tennis matchups using "
            "form, probabilities, totals and model insights.\n\n"
            "Tennis is currently in Beta.\n\n"
            "Predictions are informational and do not guarantee results."
        )

    return (
        "â¹ï¸ FLUX AI â AI-Ð±Ð¾Ñ Ð´Ð»Ñ Ð°Ð½Ð°Ð»Ð¸Ð·Ð° ÑÐ¿Ð¾ÑÑÐ°.\n\n"
        "ÐÐ¾Ñ Ð°Ð½Ð°Ð»Ð¸Ð·Ð¸ÑÑÐµÑ ÑÑÑÐ±Ð¾Ð», NBA Ð¸ ÑÐµÐ½Ð½Ð¸Ñ, ÑÑÐ¸ÑÑÐ²Ð°Ñ ÑÐ¾ÑÐ¼Ñ, "
        "Ð²ÐµÑÐ¾ÑÑÐ½Ð¾ÑÑÐ¸, ÑÐ¾ÑÐ°Ð»Ñ Ð¸ Ð²ÑÐ²Ð¾Ð´Ñ Ð¼Ð¾Ð´ÐµÐ»Ð¸.\n\n"
        "Ð¢ÐµÐ½Ð½Ð¸Ñ ÑÐµÐ¹ÑÐ°Ñ ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ Ð² Beta-ÑÐµÐ¶Ð¸Ð¼Ðµ.\n\n"
        "ÐÑÐ¾Ð³Ð½Ð¾Ð· Ð½Ðµ ÑÐ²Ð»ÑÐµÑÑÑ Ð³Ð°ÑÐ°Ð½ÑÐ¸ÐµÐ¹ ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ°."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "â FLUX AI Sports is running.\n\n"
            "Version: PRO v4.0\n"
            "Sports: Football + NBA + Tennis Beta\n"
            "Mode: Public Beta\n"
            f"Channel: {CHANNEL_USERNAME}\n"
            "Status: Online"
        )

    return (
        "â FLUX AI Sports ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ.\n\n"
        "ÐÐµÑÑÐ¸Ñ: PRO v4.0\n"
        "Ð¡Ð¿Ð¾ÑÑ: Ð¤ÑÑÐ±Ð¾Ð» + NBA + Ð¢ÐµÐ½Ð½Ð¸Ñ Beta\n"
        "Ð ÐµÐ¶Ð¸Ð¼: Public Beta\n"
        f"ÐÐ°Ð½Ð°Ð»: {CHANNEL_USERNAME}\n"
        "Ð¡ÑÐ°ÑÑÑ: Online"
    )


def admin_panel_message(language="ru"):
    stats = get_admin_stats()

    if language == "en":
        return (
            "ð FLUX AI ADMIN\n\nââââââââââââââââââââ\n\n"
            f"ð¥ Total users: {stats['total_users']}\n"
            f"ð Active PRO: {stats['active_pro']}\n"
            f"ð§¾ Total payments: {stats['total_payments']}\n\n"
            "ð Statistics update automatically."
        )

    return (
        "ð FLUX AI ADMIN\n\nââââââââââââââââââââ\n\n"
        f"ð¥ ÐÑÐµÐ³Ð¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÐµÐ¹: {stats['total_users']}\n"
        f"ð ÐÐºÑÐ¸Ð²Ð½ÑÑ PRO: {stats['active_pro']}\n"
        f"ð§¾ ÐÑÐµÐ³Ð¾ Ð¾Ð¿Ð»Ð°Ñ: {stats['total_payments']}\n\n"
        "ð Ð¡ÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ° Ð¾Ð±Ð½Ð¾Ð²Ð»ÑÐµÑÑÑ Ð°Ð²ÑÐ¾Ð¼Ð°ÑÐ¸ÑÐµÑÐºÐ¸."
    )


def profile_message(user_id, language="ru"):
    user = get_user(user_id)

    if not user:
        return (
            "ð¤ Profile not found. Press /start."
            if language == "en"
            else "ð¤ ÐÑÐ¾ÑÐ¸Ð»Ñ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½. ÐÐ°Ð¶Ð¼Ð¸ /start."
        )

    pro_active = is_pro(user_id)
    sport = get_user_sport(user_id) or "football"
    usage = get_today_usage(user_id)

    if language == "en":
        pro_status = "â Active" if pro_active else "â Inactive"
        limit_text = "Unlimited" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} today"

        return (
            "ð¤ MY PROFILE\n\nââââââââââââââââââââ\n\n"
            f"ð ID: {user_id}\n\n"
            f"ð FLUX PRO: {pro_status}\n"
            f"ð¯ Selected sport: {sport_title(sport, 'en')}\n\n"
            "ð Statistics:\n"
            f"â¢ Analyses today: {limit_text}\n"
            "â¢ Winning predictions: coming soon\n\n"
            "ð FLUX AI v4.0"
        )

    pro_status = "â ÐÐºÑÐ¸Ð²ÐµÐ½" if pro_active else "â ÐÐµ Ð°ÐºÑÐ¸Ð²ÐµÐ½"
    limit_text = "ÐÐµÐ·Ð»Ð¸Ð¼Ð¸Ñ" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} ÑÐµÐ³Ð¾Ð´Ð½Ñ"

    return (
        "ð¤ ÐÐÐ ÐÐ ÐÐ¤ÐÐÐ¬\n\nââââââââââââââââââââ\n\n"
        f"ð ID: {user_id}\n\n"
        f"ð FLUX PRO: {pro_status}\n"
        f"ð¯ ÐÑÐ±ÑÐ°Ð½Ð½ÑÐ¹ ÑÐ¿Ð¾ÑÑ: {sport_title(sport, 'ru')}\n\n"
        "ð Ð¡ÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ°:\n"
        f"â¢ ÐÐ½Ð°Ð»Ð¸Ð·Ñ ÑÐµÐ³Ð¾Ð´Ð½Ñ: {limit_text}\n"
        "â¢ ÐÐ¾Ð±ÐµÐ´Ð½ÑÑ Ð¿ÑÐ¾Ð³Ð½Ð¾Ð·Ð¾Ð²: ÑÐºÐ¾ÑÐ¾\n\n"
        "ð FLUX AI v4.0"
    )


def channel_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI DAILY\n\n"
            "Official FLUX AI channel.\n\n"
            "â½ Football predictions\n"
            "ð NBA predictions\n"
            "ð¾ Tennis predictions\n"
            "ð AI sports analysis\n"
            "ð FLUX PRO news\n\n"
            f"ð¢ Subscribe: {CHANNEL_URL}"
        )

    return (
        "ð FLUX AI DAILY\n\n"
        "ÐÑÐ¸ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹ ÐºÐ°Ð½Ð°Ð» FLUX AI.\n\n"
        "â½ ÐÑÐ¾Ð³Ð½Ð¾Ð·Ñ Ð½Ð° ÑÑÑÐ±Ð¾Ð»\n"
        "ð ÐÑÐ¾Ð³Ð½Ð¾Ð·Ñ Ð½Ð° NBA\n"
        "ð¾ ÐÑÐ¾Ð³Ð½Ð¾Ð·Ñ Ð½Ð° ÑÐµÐ½Ð½Ð¸Ñ\n"
        "ð AI-Ð°Ð½Ð°Ð»Ð¸Ð· ÑÐ¿Ð¾ÑÑÐ°\n"
        "ð ÐÐ¾Ð²Ð¾ÑÑÐ¸ FLUX PRO\n\n"
        f"ð¢ ÐÐ¾Ð´Ð¿Ð¸ÑÐ°ÑÑÑÑ: {CHANNEL_URL}"
    )


def results_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI Results\n\n"
            "Public result tracking is being prepared.\n\n"
            "Predictions are informational and do not guarantee results."
        )

    return (
        "ð FLUX AI Results\n\n"
        "ÐÑÐ±Ð»Ð¸ÑÐ½Ð°Ñ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ° ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ¾Ð² Ð³Ð¾ÑÐ¾Ð²Ð¸ÑÑÑ.\n\n"
        "ÐÑÐ¾Ð³Ð½Ð¾Ð· Ð½Ðµ ÑÐ²Ð»ÑÐµÑÑÑ Ð³Ð°ÑÐ°Ð½ÑÐ¸ÐµÐ¹ ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ°."
    )


def worldcup_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI | World Cup\n\n"
            "Football mode has been selected.\n\n"
            "Send any match:\nTeam 1 - Team 2"
        )

    return (
        "ð FLUX AI | Ð§ÐµÐ¼Ð¿Ð¸Ð¾Ð½Ð°Ñ Ð¼Ð¸ÑÐ°\n\n"
        "ÐÑÐ±ÑÐ°Ð½ ÑÐµÐ¶Ð¸Ð¼ ÑÑÑÐ±Ð¾Ð»Ð°.\n\n"
        "ÐÑÐ¿ÑÐ°Ð²Ñ Ð»ÑÐ±Ð¾Ð¹ Ð¼Ð°ÑÑ:\nÐÐ¾Ð¼Ð°Ð½Ð´Ð° 1 - ÐÐ¾Ð¼Ð°Ð½Ð´Ð° 2"
    )


def today_top_3_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI DAILY\n\n"
            "The current Top 3 is published in our channel.\n\n"
            f"ð¢ {CHANNEL_URL}"
        )

    return (
        "ð FLUX AI DAILY\n\n"
        "ÐÐºÑÑÐ°Ð»ÑÐ½ÑÐ¹ Ð¢ÐÐ-3 Ð¿ÑÐ±Ð»Ð¸ÐºÑÐµÑÑÑ Ð² Ð½Ð°ÑÐµÐ¼ ÐºÐ°Ð½Ð°Ð»Ðµ.\n\n"
        f"ð¢ {CHANNEL_URL}"
    )


def pro_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI PRO\n\n"
            "â Unlimited sports analysis\n"
            "â Football, NBA and Tennis\n"
            "â Extended statistics\n"
            "â Daily Top 3\n"
            "â New PRO features\n\n"
            f"Price: â­{PRO_PRICE_STARS} / {PRO_DAYS} days\n\n"
            "ð Use the payment invoice below."
        )

    return (
        "ð FLUX AI PRO\n\n"
        "â ÐÐµÐ·Ð»Ð¸Ð¼Ð¸ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð· ÑÐ¿Ð¾ÑÑÐ°\n"
        "â Ð¤ÑÑÐ±Ð¾Ð», NBA Ð¸ ÑÐµÐ½Ð½Ð¸Ñ\n"
        "â Ð Ð°ÑÑÐ¸ÑÐµÐ½Ð½Ð°Ñ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ°\n"
        "â Ð¢ÐÐ-3 Ð´Ð½Ñ\n"
        "â ÐÐ¾Ð²ÑÐµ PRO-ÑÑÐ½ÐºÑÐ¸Ð¸\n\n"
        f"Ð¡ÑÐ¾Ð¸Ð¼Ð¾ÑÑÑ: â­{PRO_PRICE_STARS} / {PRO_DAYS} Ð´Ð½ÐµÐ¹\n\n"
        "ð ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ÑÐµ ÑÑÑÑ Ð¾Ð¿Ð»Ð°ÑÑ Ð½Ð¸Ð¶Ðµ."
    )


def payment_success_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI PRO activated!\n\n"
            "ð Status: PRO\n"
            f"ð Period: {PRO_DAYS} days\n"
            "â Unlimited analysis is available."
        )

    return (
        "ð FLUX AI PRO Ð°ÐºÑÐ¸Ð²Ð¸ÑÐ¾Ð²Ð°Ð½!\n\n"
        "ð Ð¡ÑÐ°ÑÑÑ: PRO\n"
        f"ð Ð¡ÑÐ¾Ðº: {PRO_DAYS} Ð´Ð½ÐµÐ¹\n"
        "â ÐÐµÐ·Ð»Ð¸Ð¼Ð¸ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð· Ð´Ð¾ÑÑÑÐ¿ÐµÐ½."
    )


def analyze_match_text(text, language="ru"):
    from engine.analyzer import analyze_and_format

    matches = detect_matches(text)

    if not matches:
        return help_message(language)

    if len(matches) == 1:
        return analyze_and_format(matches[0][0], matches[0][1], language)

    results = []

    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            result = analyze_and_format(team1, team2, language)
            results.append(f"#{index}\n{result}")
        except Exception as error:
            print("MULTI_ANALYSIS_ERROR:", repr(error), flush=True)
            message = (
                f"â ï¸ Could not analyze: {team1} - {team2}"
                if language == "en"
                else f"â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ: {team1} - {team2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analyze_nba_text(text, language="ru"):
    from engine.nba_analyzer import analyze_and_format_nba

    matches = detect_matches(text)

    if not matches:
        return (
            "ð Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks"
            if language == "en"
            else "ð ÐÐ°Ð¿Ð¸ÑÐ¸ Ð¼Ð°ÑÑ NBA:\n\nLakers - Celtics\nWarriors - Knicks"
        )

    if len(matches) == 1:
        return analyze_and_format_nba(matches[0][0], matches[0][1], language)

    results = []

    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            result = analyze_and_format_nba(team1, team2, language)
            results.append(f"#{index}\n{result}")
        except Exception as error:
            print("MULTI_NBA_ANALYSIS_ERROR:", repr(error), flush=True)
            message = (
                f"â ï¸ Could not analyze: {team1} - {team2}"
                if language == "en"
                else f"â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ: {team1} - {team2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analyze_tennis_text(text, language="ru"):
    matches = detect_matches(text)

    if not matches:
        return (
            "ð¾ Send a tennis match:\n\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "ð¾ ÐÑÐ¿ÑÐ°Ð²Ñ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ:\n\nCarlos Alcaraz - Jannik Sinner"
        )

    if len(matches) == 1:
        return analyze_tennis_match(matches[0][0], matches[0][1], language)

    results = []

    for index, (player1, player2) in enumerate(matches[:5], start=1):
        try:
            result = analyze_tennis_match(player1, player2, language)
            results.append(f"#{index}\n{result}")
        except Exception as error:
            print("MULTI_TENNIS_ANALYSIS_ERROR:", repr(error), flush=True)
            message = (
                f"â ï¸ Could not analyze: {player1} - {player2}"
                if language == "en"
                else f"â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ: {player1} - {player2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analysis_prompt(sport_mode, language="ru"):
    if sport_mode == "nba":
        return (
            "ð Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks"
            if language == "en"
            else "ð ÐÐ°Ð¿Ð¸ÑÐ¸ Ð¼Ð°ÑÑ NBA:\n\nLakers - Celtics\nWarriors - Knicks"
        )

    if sport_mode == "tennis":
        return (
            "ð¾ Send a tennis match:\n\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "ð¾ ÐÑÐ¿ÑÐ°Ð²Ñ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ:\n\nCarlos Alcaraz - Jannik Sinner"
        )

    return (
        "â½ Send a football match:\n\nReal Madrid - Barcelona"
        if language == "en"
        else "â½ ÐÐ°Ð¿Ð¸ÑÐ¸ ÑÑÑÐ±Ð¾Ð»ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ:\n\nReal Madrid - Barcelona"
    )


def analysis_error_message(sport_mode, language="ru"):
    if sport_mode == "nba":
        return (
            "â ï¸ Could not complete the NBA analysis.\n\n"
            "Check the format:\nLakers - Celtics"
            if language == "en"
            else "â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ ÑÐ´ÐµÐ»Ð°ÑÑ Ð°Ð½Ð°Ð»Ð¸Ð· NBA.\n\n"
            "ÐÑÐ¾Ð²ÐµÑÑ ÑÐ¾ÑÐ¼Ð°Ñ:\nLakers - Celtics"
        )

    if sport_mode == "tennis":
        return (
            "â ï¸ Could not complete the tennis analysis.\n\n"
            "Check the format:\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ ÑÐ´ÐµÐ»Ð°ÑÑ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð·.\n\n"
            "ÐÑÐ¾Ð²ÐµÑÑ ÑÐ¾ÑÐ¼Ð°Ñ:\nCarlos Alcaraz - Jannik Sinner"
        )

    return (
        "â ï¸ Could not complete the football analysis.\n\n"
        "Check the format:\nReal Madrid - Barcelona"
        if language == "en"
        else "â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ ÑÐ´ÐµÐ»Ð°ÑÑ ÑÑÑÐ±Ð¾Ð»ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð·.\n\n"
        "ÐÑÐ¾Ð²ÐµÑÑ ÑÐ¾ÑÐ¼Ð°Ñ:\nReal Madrid - Barcelona"
    )


def handle_analysis(chat_id, user_id, text, language="ru"):
    matches = detect_matches(text)

    if not matches:
        sport_mode = get_user_sport(user_id) or "football"
        send_message(
            chat_id,
            analysis_prompt(sport_mode, language),
            reply_markup=main_menu(language),
        )
        return

    if not is_pro(user_id):
        used = get_today_usage(user_id)
        remaining = FREE_DAILY_LIMIT - used

        if remaining <= 0:
            send_message(
                chat_id,
                free_limit_message(language),
                reply_markup=main_menu(language),
            )
            return

        if len(matches) > remaining:
            message_text = (
                f"ð Free analyses remaining today: {remaining}\n\n"
                "Send fewer matchups or activate FLUX PRO."
                if language == "en"
                else f"ð Ð£ Ð²Ð°Ñ Ð¾ÑÑÐ°Ð»Ð¾ÑÑ Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½ÑÑ Ð°Ð½Ð°Ð»Ð¸Ð·Ð¾Ð² ÑÐµÐ³Ð¾Ð´Ð½Ñ: {remaining}\n\n"
                "ÐÑÐ¿ÑÐ°Ð²ÑÑÐµ Ð¼ÐµÐ½ÑÑÐµ Ð¼Ð°ÑÑÐµÐ¹ Ð¸Ð»Ð¸ Ð¾ÑÐ¾ÑÐ¼Ð¸ÑÐµ FLUX PRO."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return

    sport_mode = get_user_sport(user_id) or "football"

    if len(matches) > 1:
        analyzing_text = (
            f"â³ Analyzing {len(matches)} matchups..."
            if language == "en"
            else f"â³ ÐÐ½Ð°Ð»Ð¸Ð·Ð¸ÑÑÑ {len(matches)} Ð¼Ð°ÑÑÐµÐ¹..."
        )
    elif sport_mode == "nba":
        analyzing_text = (
            "â³ Analyzing the NBA game..."
            if language == "en"
            else "â³ ÐÐ½Ð°Ð»Ð¸Ð·Ð¸ÑÑÑ Ð¼Ð°ÑÑ NBA..."
        )
    elif sport_mode == "tennis":
        analyzing_text = (
            "â³ Analyzing the tennis match..."
            if language == "en"
            else "â³ ÐÐ½Ð°Ð»Ð¸Ð·Ð¸ÑÑÑ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ..."
        )
    else:
        analyzing_text = (
            "â³ Analyzing the football match..."
            if language == "en"
            else "â³ ÐÐ½Ð°Ð»Ð¸Ð·Ð¸ÑÑÑ ÑÑÑÐ±Ð¾Ð»ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ..."
        )

    send_message(chat_id, analyzing_text, reply_markup=main_menu(language))

    try:
        if sport_mode == "nba":
            answer = analyze_nba_text(text, language)
            sport_prefix = "NBA"
        elif sport_mode == "tennis":
            answer = analyze_tennis_text(text, language)
            sport_prefix = "TENNIS"
        else:
            answer = analyze_match_text(text, language)
            sport_prefix = "FOOTBALL"

        send_message(chat_id, answer, reply_markup=main_menu(language))

        for participant1, participant2 in matches:
            save_prediction(
                user_id,
                f"[{sport_prefix}] {participant1} - {participant2}",
                answer,
            )

            if not is_pro(user_id):
                increase_today_usage(user_id)

    except Exception as error:
        print("MATCH_ANALYSIS_ERROR:", repr(error), flush=True)
        send_message(
            chat_id,
            analysis_error_message(sport_mode, language),
            reply_markup=main_menu(language),
        )


def parse_invoice_user_id(invoice_payload):
    prefix = "flux_pro_30_days:"
    invoice_payload = str(invoice_payload)

    if not invoice_payload.startswith(prefix):
        return None

    try:
        return int(invoice_payload[len(prefix):])
    except (TypeError, ValueError):
        return None


def process_pre_checkout_query(pre_checkout_query):
    query_id = pre_checkout_query.get("id")
    payer_id = pre_checkout_query.get("from", {}).get("id")
    language = get_user_language(payer_id) or "ru"
    invoice_payload = pre_checkout_query.get("invoice_payload", "")
    currency = pre_checkout_query.get("currency", "")
    total_amount = pre_checkout_query.get("total_amount", 0)
    payload_user_id = parse_invoice_user_id(invoice_payload)

    is_valid = bool(
        query_id
        and payer_id
        and payload_user_id == payer_id
        and currency == "XTR"
        and int(total_amount) == PRO_PRICE_STARS
    )

    error_message = None

    if not is_valid:
        error_message = (
            "Payment verification failed. Please create a new invoice."
            if language == "en"
            else "ÐÐµ ÑÐ´Ð°Ð»Ð¾ÑÑ Ð¿ÑÐ¾Ð²ÐµÑÐ¸ÑÑ Ð¿Ð»Ð°ÑÑÐ¶. Ð¡Ð¾Ð·Ð´Ð°Ð¹ÑÐµ Ð½Ð¾Ð²ÑÐ¹ ÑÑÑÑ."
        )

    answer_pre_checkout_query(query_id, is_valid, error_message)


def process_successful_payment(message):
    payment = message.get("successful_payment", {})
    user = message.get("from", {})
    chat = message.get("chat", {})

    user_id = user.get("id")
    chat_id = chat.get("id")
    language = get_user_language(user_id) or "ru"

    payload_user_id = parse_invoice_user_id(payment.get("invoice_payload", ""))
    currency = payment.get("currency", "")
    total_amount = payment.get("total_amount", 0)

    payment_is_valid = bool(
        user_id
        and chat_id
        and payload_user_id == user_id
        and currency == "XTR"
        and int(total_amount) == PRO_PRICE_STARS
    )

    if not payment_is_valid:
        error_text = (
            "â ï¸ Payment data failed verification."
            if language == "en"
            else "â ï¸ ÐÐ°Ð½Ð½ÑÐµ Ð¿Ð»Ð°ÑÐµÐ¶Ð° Ð½Ðµ Ð¿ÑÐ¾ÑÐ»Ð¸ Ð¿ÑÐ¾Ð²ÐµÑÐºÑ."
        )
        send_message(chat_id, error_text, reply_markup=main_menu(language))
        return

    add_user(user)
    activate_pro(user_id, days=PRO_DAYS)
    save_payment(
        user_id,
        provider="telegram_stars",
        amount=total_amount,
        currency="XTR",
        status="paid",
    )

    send_message(
        chat_id,
        payment_success_message(language),
        reply_markup=main_menu(language),
    )


def process_callback_query(callback_query):
    callback_id = callback_query.get("id")
    user = callback_query.get("from", {})
    user_id = user.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")

    if not user_id or not chat_id:
        if callback_id:
            answer_callback_query(callback_id)
        return

    add_user(user)

    if data == "lang_en":
        set_user_language(user_id, "en")
        answer_callback_query(callback_id, "Language changed to English.")
        send_message(chat_id, start_message("en"), reply_markup=main_menu("en"))
        return

    if data == "lang_ru":
        set_user_language(user_id, "ru")
        answer_callback_query(callback_id, "Ð¯Ð·ÑÐº Ð¸Ð·Ð¼ÐµÐ½ÑÐ½ Ð½Ð° ÑÑÑÑÐºÐ¸Ð¹.")
        send_message(chat_id, start_message("ru"), reply_markup=main_menu("ru"))
        return

    answer_callback_query(callback_id)


@app.route("/")
def home():
    return "FLUX AI Sports PRO v4.0 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return "OK", 200

        if data.get("callback_query"):
            process_callback_query(data["callback_query"])
            return "OK", 200

        if data.get("pre_checkout_query"):
            process_pre_checkout_query(data["pre_checkout_query"])
            return "OK", 200

        message = data.get("message")

        if not message:
            return "OK", 200

        if message.get("successful_payment"):
            process_successful_payment(message)
            return "OK", 200

        chat_id = message.get("chat", {}).get("id")
        user = message.get("from", {})
        user_id = user.get("id")
        text = (message.get("text") or "").strip()

        if not chat_id:
            return "OK", 200

        if user_id:
            add_user(user)

        language = get_user_language(user_id) or "ru"

        if text == "/start":
            send_message(
                chat_id,
                "â¡ Welcome to Flux AI\nChoose your language.\n\n"
                "â¡ ÐÐ¾Ð±ÑÐ¾ Ð¿Ð¾Ð¶Ð°Ð»Ð¾Ð²Ð°ÑÑ Ð² Flux AI\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº.",
                reply_markup=language_keyboard(),
            )
            return "OK", 200

        if text in ["/language", "ð Language", "ð Ð¯Ð·ÑÐº"]:
            send_message(
                chat_id,
                "Choose your language.\n\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº.",
                reply_markup=language_keyboard(),
            )
            return "OK", 200

        if text in ["â½ Ð¤ÑÑÐ±Ð¾Ð»", "â½ Football"]:
            set_user_sport(user_id, "football")
            message_text = (
                "â½ Football mode selected.\n\n"
                "Send a match:\nReal Madrid - Barcelona"
                if language == "en"
                else "â½ ÐÑÐ±ÑÐ°Ð½ ÑÐµÐ¶Ð¸Ð¼ ÑÑÑÐ±Ð¾Ð»Ð°.\n\n"
                "ÐÐ°Ð¿Ð¸ÑÐ¸ Ð¼Ð°ÑÑ:\nReal Madrid - Barcelona"
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if text == "ð NBA":
            set_user_sport(user_id, "nba")
            message_text = (
                "ð NBA mode selected.\n\n"
                "Send a game:\nLakers - Celtics\n\n"
                "The first team is treated as the home team."
                if language == "en"
                else "ð ÐÑÐ±ÑÐ°Ð½ ÑÐµÐ¶Ð¸Ð¼ NBA.\n\n"
                "ÐÐ°Ð¿Ð¸ÑÐ¸ Ð¼Ð°ÑÑ:\nLakers - Celtics\n\n"
                "ÐÐµÑÐ²Ð°Ñ ÐºÐ¾Ð¼Ð°Ð½Ð´Ð° ÑÑÐ¸ÑÐ°ÐµÑÑÑ ÑÐ¾Ð·ÑÐ¸Ð½Ð¾Ð¼ Ð¿Ð»Ð¾ÑÐ°Ð´ÐºÐ¸."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if text in ["ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ", "ð¾ Tennis"]:
            set_user_sport(user_id, "tennis")
            message_text = (
                "ð¾ Tennis mode selected.\n\n"
                "Send a match:\nCarlos Alcaraz - Jannik Sinner\n\n"
                "Tennis AI is currently in Beta."
                if language == "en"
                else "ð¾ ÐÑÐ±ÑÐ°Ð½ ÑÐµÐ¶Ð¸Ð¼ ÑÐµÐ½Ð½Ð¸ÑÐ°.\n\n"
                "ÐÑÐ¿ÑÐ°Ð²Ñ Ð¼Ð°ÑÑ:\nCarlos Alcaraz - Jannik Sinner\n\n"
                "Tennis AI ÑÐµÐ¹ÑÐ°Ñ ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ Ð² Beta-ÑÐµÐ¶Ð¸Ð¼Ðµ."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if not text:
            send_message(
                chat_id,
                help_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text in ["â½ ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐ°", "â½ Analyze Match"]:
            sport_mode = get_user_sport(user_id) or "football"
            send_message(
                chat_id,
                analysis_prompt(sport_mode, language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        button_commands = {
            "ð Ð¢ÐÐ-3 Ð´Ð½Ñ": "/today",
            "ð Top 3 Today": "/today",
            "ð Ð§Ð-2026": "/worldcup",
            "ð World Cup 2026": "/worldcup",
            "ð Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ": "/results",
            "ð Results": "/results",
            "ð ÐÐ°Ð½Ð°Ð»": "/channel",
            "ð Channel": "/channel",
            "ð FLUX PRO": "/pro",
            "ð¤ ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ": "/profile",
            "ð¤ My Profile": "/profile",
            "â¹ï¸ Ð Ð¿ÑÐ¾ÐµÐºÑÐµ": "/about",
            "â¹ï¸ About": "/about",
            "ð Ð¡ÑÐ°ÑÑÑ": "/status",
            "ð Status": "/status",
        }
        text = button_commands.get(text, text)

        if text in ["/help", "/analyze"]:
            send_message(
                chat_id,
                help_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/about":
            send_message(
                chat_id,
                about_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/status":
            send_message(
                chat_id,
                status_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/profile":
            send_message(
                chat_id,
                profile_message(user_id, language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/admin":
            if user_id != ADMIN_TELEGRAM_ID:
                denied = (
                    "â Access denied."
                    if language == "en"
                    else "â ÐÐ¾ÑÑÑÐ¿ Ð·Ð°Ð¿ÑÐµÑÑÐ½."
                )
                send_message(chat_id, denied, reply_markup=main_menu(language))
                return "OK", 200

            send_message(
                chat_id,
                admin_panel_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/channel":
            button_text = (
                "ð Open channel"
                if language == "en"
                else "ð ÐÑÐºÑÑÑÑ ÐºÐ°Ð½Ð°Ð»"
            )
            send_message(
                chat_id,
                channel_message(language),
                reply_markup={
                    "inline_keyboard": [[
                        {"text": button_text, "url": CHANNEL_URL}
                    ]]
                },
            )
            return "OK", 200

        if text == "/worldcup":
            set_user_sport(user_id, "football")
            send_message(
                chat_id,
                worldcup_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/results":
            send_message(
                chat_id,
                results_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/today":
            send_message(
                chat_id,
                today_top_3_message(language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "/pro":
            try:
                send_message(
                    chat_id,
                    pro_message(language),
                    reply_markup=main_menu(language),
                )
                send_stars_invoice(
                    bot_token=BOT_TOKEN,
                    chat_id=chat_id,
                    user_id=user_id,
                    stars_price=PRO_PRICE_STARS,
                    language=language,
                )
            except Exception as error:
                print("PRO_PAYMENT_ERROR:", repr(error), flush=True)
                error_text = (
                    "â ï¸ Could not open Telegram Stars payment."
                    if language == "en"
                    else "â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ Ð¾ÑÐºÑÑÑÑ Ð¾Ð¿Ð»Ð°ÑÑ Telegram Stars."
                )
                send_message(
                    chat_id,
                    error_text,
                    reply_markup=main_menu(language),
                )

            return "OK", 200

        handle_analysis(chat_id, user_id, text, language)
        return "OK", 200

    except Exception as error:
        print("TELEGRAM_WEBHOOK_ERROR:", repr(error), flush=True)
        return "OK", 200


def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"

    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": webhook_url,
                "drop_pending_updates": False,
                "allowed_updates": [
                    "message",
                    "callback_query",
                    "pre_checkout_query",
                ],
            },
        )
        print("WEBHOOK_SET:", result, flush=True)
    except Exception as error:
        print("WEBHOOK_SET_ERROR:", repr(error), flush=True)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()

    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
