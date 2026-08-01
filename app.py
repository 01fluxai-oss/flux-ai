# -*- coding: ascii -*-
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
            {"text": "\U0001f1fa\U0001f1f8 English", "callback_data": "lang_en"},
            {"text": "\U0001f1f7\U0001f1fa \u0420\u0443\u0441\u0441\u043a\u0438\u0439", "callback_data": "lang_ru"},
        ]]
    }


def main_menu(language="ru"):
    if language == "en":
        keyboard = [
            ["\u26bd Football", "\U0001f3c0 NBA"],
            ["\U0001f3be Tennis"],
            ["\U0001f4c5 Tennis Today"],
            ["\u26bd Analyze Match"],
            ["\U0001f3c6 Top 3 Today", "\U0001f30d World Cup 2026"],
            ["\U0001f4c8 Results"],
            ["\U0001f3c6 Channel", "\U0001f48e FLUX PRO"],
            ["\U0001f464 My Profile"],
            ["\u2139\ufe0f About", "\U0001f4ca Status"],
            ["\U0001f310 Language"],
        ]
    else:
        keyboard = [
            ["\u26bd \u0424\u0443\u0442\u0431\u043e\u043b", "\U0001f3c0 NBA"],
            ["\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441"],
            ["\U0001f4c5 \u0422\u0435\u043d\u043d\u0438\u0441 \u0441\u0435\u0433\u043e\u0434\u043d\u044f"],
            ["\u26bd \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0430"],
            ["\U0001f3c6 \u0422\u041e\u041f-3 \u0434\u043d\u044f", "\U0001f30d \u0427\u041c-2026"],
            ["\U0001f4c8 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b"],
            ["\U0001f3c6 \u041a\u0430\u043d\u0430\u043b", "\U0001f48e FLUX PRO"],
            ["\U0001f464 \u041c\u043e\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c"],
            ["\u2139\ufe0f \u041e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", "\U0001f4ca \u0421\u0442\u0430\u0442\u0443\u0441"],
            ["\U0001f310 \u042f\u0437\u044b\u043a"],
        ]

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        str(text)
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2212", "-")
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
        "football": {"ru": "\u26bd \u0424\u0443\u0442\u0431\u043e\u043b", "en": "\u26bd Football"},
        "nba": {"ru": "\U0001f3c0 NBA", "en": "\U0001f3c0 NBA"},
        "tennis": {"ru": "\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441", "en": "\U0001f3be Tennis"},
    }
    return titles.get(sport, titles["football"]).get(language, "\u26bd \u0424\u0443\u0442\u0431\u043e\u043b")


def start_message(language="ru"):
    if language == "en":
        return (
            "\U0001f44b Welcome! I am FLUX AI Sports PRO v5.0\n\n"
            "\u26bd Football analysis\n"
            "\U0001f3c0 NBA analysis\n"
            "\U0001f3be Tennis analysis (Beta)\n"
            "\U0001f3c6 Top 3 of the day\n"
            "\U0001f30d World Cup analysis\n"
            "\U0001f4c8 Results\n"
            "\U0001f48e FLUX PRO\n\n"
            f"FREE: {FREE_DAILY_LIMIT} analyses per day\n"
            "PRO: unlimited\n\n"
            "Choose a sport, then send a matchup."
        )

    return (
        "\U0001f44b \u041f\u0440\u0438\u0432\u0435\u0442! \u042f FLUX AI Sports PRO v5.0\n\n"
        "\u26bd \u0410\u043d\u0430\u043b\u0438\u0437 \u0444\u0443\u0442\u0431\u043e\u043b\u0430\n"
        "\U0001f3c0 \u0410\u043d\u0430\u043b\u0438\u0437 NBA\n"
        "\U0001f3be \u0410\u043d\u0430\u043b\u0438\u0437 \u0442\u0435\u043d\u043d\u0438\u0441\u0430 (Beta)\n"
        "\U0001f3c6 \u0422\u041e\u041f-3 \u0434\u043d\u044f\n"
        "\U0001f30d \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0435\u0439 \u0427\u041c\n"
        "\U0001f4c8 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b\n"
        "\U0001f48e FLUX PRO\n\n"
        f"FREE: {FREE_DAILY_LIMIT} \u0430\u043d\u0430\u043b\u0438\u0437\u043e\u0432 \u0432 \u0434\u0435\u043d\u044c\n"
        "PRO: \u0431\u0435\u0437\u043b\u0438\u043c\u0438\u0442\n\n"
        "\u0412\u044b\u0431\u0435\u0440\u0438 \u0432\u0438\u0434 \u0441\u043f\u043e\u0440\u0442\u0430 \u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u044c \u043c\u0430\u0442\u0447."
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "Choose a sport first:\n\n"
            "\u26bd Football:\nReal Madrid - Barcelona\n\n"
            "\U0001f3c0 NBA:\nLakers - Celtics\n\n"
            "\U0001f3be Tennis:\nCarlos Alcaraz - Jannik Sinner\n\n"
            "You can send several matchups, one per line."
        )

    return (
        "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438 \u0432\u0438\u0434 \u0441\u043f\u043e\u0440\u0442\u0430:\n\n"
        "\u26bd \u0424\u0443\u0442\u0431\u043e\u043b:\nReal Madrid - Barcelona\n\n"
        "\U0001f3c0 NBA:\nLakers - Celtics\n\n"
        "\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441:\nCarlos Alcaraz - Jannik Sinner\n\n"
        "\u041c\u043e\u0436\u043d\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u0430\u0442\u0447\u0435\u0439 \u0441\u043f\u0438\u0441\u043a\u043e\u043c."
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "\u2139\ufe0f FLUX AI is an AI-powered sports analysis bot.\n\n"
            "It analyzes football, NBA and tennis matchups using "
            "form, probabilities, totals and model insights.\n\n"
            "Tennis is currently in Beta.\n\n"
            "Predictions are informational and do not guarantee results."
        )

    return (
        "\u2139\ufe0f FLUX AI \u2014 AI-\u0431\u043e\u0442 \u0434\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430 \u0441\u043f\u043e\u0440\u0442\u0430.\n\n"
        "\u0411\u043e\u0442 \u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u0444\u0443\u0442\u0431\u043e\u043b, NBA \u0438 \u0442\u0435\u043d\u043d\u0438\u0441, \u0443\u0447\u0438\u0442\u044b\u0432\u0430\u044f \u0444\u043e\u0440\u043c\u0443, "
        "\u0432\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u0438, \u0442\u043e\u0442\u0430\u043b\u044b \u0438 \u0432\u044b\u0432\u043e\u0434\u044b \u043c\u043e\u0434\u0435\u043b\u0438.\n\n"
        "\u0422\u0435\u043d\u043d\u0438\u0441 \u0441\u0435\u0439\u0447\u0430\u0441 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0432 Beta-\u0440\u0435\u0436\u0438\u043c\u0435.\n\n"
        "\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0435\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "\u2705 FLUX AI Sports is running.\n\n"
            "Version: PRO v5.0\n"
            "Sports: Football + NBA + Tennis Beta\n"
            "Mode: Public Beta\n"
            f"Channel: {CHANNEL_USERNAME}\n"
            "Status: Online"
        )

    return (
        "\u2705 FLUX AI Sports \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442.\n\n"
        "\u0412\u0435\u0440\u0441\u0438\u044f: PRO v5.0\n"
        "\u0421\u043f\u043e\u0440\u0442: \u0424\u0443\u0442\u0431\u043e\u043b + NBA + \u0422\u0435\u043d\u043d\u0438\u0441 Beta\n"
        "\u0420\u0435\u0436\u0438\u043c: Public Beta\n"
        f"\u041a\u0430\u043d\u0430\u043b: {CHANNEL_USERNAME}\n"
        "\u0421\u0442\u0430\u0442\u0443\u0441: Online"
    )


def admin_panel_message(language="ru"):
    stats = get_admin_stats()

    if language == "en":
        return (
            "\U0001f510 FLUX AI ADMIN\n\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            f"\U0001f465 Total users: {stats['total_users']}\n"
            f"\U0001f48e Active PRO: {stats['active_pro']}\n"
            f"\U0001f9fe Total payments: {stats['total_payments']}\n\n"
            "\U0001f4ca Statistics update automatically."
        )

    return (
        "\U0001f510 FLUX AI ADMIN\n\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\U0001f465 \u0412\u0441\u0435\u0433\u043e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439: {stats['total_users']}\n"
        f"\U0001f48e \u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0445 PRO: {stats['active_pro']}\n"
        f"\U0001f9fe \u0412\u0441\u0435\u0433\u043e \u043e\u043f\u043b\u0430\u0442: {stats['total_payments']}\n\n"
        "\U0001f4ca \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438."
    )


def profile_message(user_id, language="ru"):
    user = get_user(user_id)

    if not user:
        return (
            "\U0001f464 Profile not found. Press /start."
            if language == "en"
            else "\U0001f464 \u041f\u0440\u043e\u0444\u0438\u043b\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d. \u041d\u0430\u0436\u043c\u0438 /start."
        )

    pro_active = is_pro(user_id)
    sport = get_user_sport(user_id) or "football"
    usage = get_today_usage(user_id)

    if language == "en":
        pro_status = "\u2705 Active" if pro_active else "\u274c Inactive"
        limit_text = "Unlimited" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} today"

        return (
            "\U0001f464 MY PROFILE\n\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            f"\U0001f194 ID: {user_id}\n\n"
            f"\U0001f48e FLUX PRO: {pro_status}\n"
            f"\U0001f3af Selected sport: {sport_title(sport, 'en')}\n\n"
            "\U0001f4ca Statistics:\n"
            f"\u2022 Analyses today: {limit_text}\n"
            "\u2022 Winning predictions: coming soon\n\n"
            "\U0001f680 FLUX AI v5.0"
        )

    pro_status = "\u2705 \u0410\u043a\u0442\u0438\u0432\u0435\u043d" if pro_active else "\u274c \u041d\u0435 \u0430\u043a\u0442\u0438\u0432\u0435\u043d"
    limit_text = "\u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} \u0441\u0435\u0433\u043e\u0434\u043d\u044f"

    return (
        "\U0001f464 \u041c\u041e\u0419 \u041f\u0420\u041e\u0424\u0418\u041b\u042c\n\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\U0001f194 ID: {user_id}\n\n"
        f"\U0001f48e FLUX PRO: {pro_status}\n"
        f"\U0001f3af \u0412\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 \u0441\u043f\u043e\u0440\u0442: {sport_title(sport, 'ru')}\n\n"
        "\U0001f4ca \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430:\n"
        f"\u2022 \u0410\u043d\u0430\u043b\u0438\u0437\u044b \u0441\u0435\u0433\u043e\u0434\u043d\u044f: {limit_text}\n"
        "\u2022 \u041f\u043e\u0431\u0435\u0434\u043d\u044b\u0445 \u043f\u0440\u043e\u0433\u043d\u043e\u0437\u043e\u0432: \u0441\u043a\u043e\u0440\u043e\n\n"
        "\U0001f680 FLUX AI v5.0"
    )


def channel_message(language="ru"):
    if language == "en":
        return (
            "\U0001f3c6 FLUX AI DAILY\n\n"
            "Official FLUX AI channel.\n\n"
            "\u26bd Football predictions\n"
            "\U0001f3c0 NBA predictions\n"
            "\U0001f3be Tennis predictions\n"
            "\U0001f4ca AI sports analysis\n"
            "\U0001f48e FLUX PRO news\n\n"
            f"\U0001f4e2 Subscribe: {CHANNEL_URL}"
        )

    return (
        "\U0001f3c6 FLUX AI DAILY\n\n"
        "\u041e\u0444\u0438\u0446\u0438\u0430\u043b\u044c\u043d\u044b\u0439 \u043a\u0430\u043d\u0430\u043b FLUX AI.\n\n"
        "\u26bd \u041f\u0440\u043e\u0433\u043d\u043e\u0437\u044b \u043d\u0430 \u0444\u0443\u0442\u0431\u043e\u043b\n"
        "\U0001f3c0 \u041f\u0440\u043e\u0433\u043d\u043e\u0437\u044b \u043d\u0430 NBA\n"
        "\U0001f3be \u041f\u0440\u043e\u0433\u043d\u043e\u0437\u044b \u043d\u0430 \u0442\u0435\u043d\u043d\u0438\u0441\n"
        "\U0001f4ca AI-\u0430\u043d\u0430\u043b\u0438\u0437 \u0441\u043f\u043e\u0440\u0442\u0430\n"
        "\U0001f48e \u041d\u043e\u0432\u043e\u0441\u0442\u0438 FLUX PRO\n\n"
        f"\U0001f4e2 \u041f\u043e\u0434\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f: {CHANNEL_URL}"
    )


def results_message(language="ru"):
    if language == "en":
        return (
            "\U0001f4c8 FLUX AI Results\n\n"
            "Public result tracking is being prepared.\n\n"
            "Predictions are informational and do not guarantee results."
        )

    return (
        "\U0001f4c8 FLUX AI Results\n\n"
        "\u041f\u0443\u0431\u043b\u0438\u0447\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u043e\u0432 \u0433\u043e\u0442\u043e\u0432\u0438\u0442\u0441\u044f.\n\n"
        "\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0435\u0439 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430."
    )


def worldcup_message(language="ru"):
    if language == "en":
        return (
            "\U0001f30d FLUX AI | World Cup\n\n"
            "Football mode has been selected.\n\n"
            "Send any match:\nTeam 1 - Team 2"
        )

    return (
        "\U0001f30d FLUX AI | \u0427\u0435\u043c\u043f\u0438\u043e\u043d\u0430\u0442 \u043c\u0438\u0440\u0430\n\n"
        "\u0412\u044b\u0431\u0440\u0430\u043d \u0440\u0435\u0436\u0438\u043c \u0444\u0443\u0442\u0431\u043e\u043b\u0430.\n\n"
        "\u041e\u0442\u043f\u0440\u0430\u0432\u044c \u043b\u044e\u0431\u043e\u0439 \u043c\u0430\u0442\u0447:\n\u041a\u043e\u043c\u0430\u043d\u0434\u0430 1 - \u041a\u043e\u043c\u0430\u043d\u0434\u0430 2"
    )


def today_top_3_message(language="ru"):
    if language == "en":
        return (
            "\U0001f3c6 FLUX AI DAILY\n\n"
            "The current Top 3 is published in our channel.\n\n"
            f"\U0001f4e2 {CHANNEL_URL}"
        )

    return (
        "\U0001f3c6 FLUX AI DAILY\n\n"
        "\u0410\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439 \u0422\u041e\u041f-3 \u043f\u0443\u0431\u043b\u0438\u043a\u0443\u0435\u0442\u0441\u044f \u0432 \u043d\u0430\u0448\u0435\u043c \u043a\u0430\u043d\u0430\u043b\u0435.\n\n"
        f"\U0001f4e2 {CHANNEL_URL}"
    )


def pro_message(language="ru"):
    if language == "en":
        return (
            "\U0001f48e FLUX AI PRO\n\n"
            "\u2705 Unlimited sports analysis\n"
            "\u2705 Football, NBA and Tennis\n"
            "\u2705 Extended statistics\n"
            "\u2705 Daily Top 3\n"
            "\u2705 New PRO features\n\n"
            f"Price: \u2b50{PRO_PRICE_STARS} / {PRO_DAYS} days\n\n"
            "\U0001f447 Use the payment invoice below."
        )

    return (
        "\U0001f48e FLUX AI PRO\n\n"
        "\u2705 \u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u0441\u043f\u043e\u0440\u0442\u0430\n"
        "\u2705 \u0424\u0443\u0442\u0431\u043e\u043b, NBA \u0438 \u0442\u0435\u043d\u043d\u0438\u0441\n"
        "\u2705 \u0420\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430\n"
        "\u2705 \u0422\u041e\u041f-3 \u0434\u043d\u044f\n"
        "\u2705 \u041d\u043e\u0432\u044b\u0435 PRO-\u0444\u0443\u043d\u043a\u0446\u0438\u0438\n\n"
        f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c: \u2b50{PRO_PRICE_STARS} / {PRO_DAYS} \u0434\u043d\u0435\u0439\n\n"
        "\U0001f447 \u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 \u0441\u0447\u0451\u0442 \u043e\u043f\u043b\u0430\u0442\u044b \u043d\u0438\u0436\u0435."
    )


def payment_success_message(language="ru"):
    if language == "en":
        return (
            "\U0001f389 FLUX AI PRO activated!\n\n"
            "\U0001f48e Status: PRO\n"
            f"\U0001f4c5 Period: {PRO_DAYS} days\n"
            "\u2705 Unlimited analysis is available."
        )

    return (
        "\U0001f389 FLUX AI PRO \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d!\n\n"
        "\U0001f48e \u0421\u0442\u0430\u0442\u0443\u0441: PRO\n"
        f"\U0001f4c5 \u0421\u0440\u043e\u043a: {PRO_DAYS} \u0434\u043d\u0435\u0439\n"
        "\u2705 \u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d."
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
                f"\u26a0\ufe0f Could not analyze: {team1} - {team2}"
                if language == "en"
                else f"\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c: {team1} - {team2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analyze_nba_text(text, language="ru"):
    from engine.nba_analyzer import analyze_and_format_nba

    matches = detect_matches(text)

    if not matches:
        return (
            "\U0001f3c0 Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks"
            if language == "en"
            else "\U0001f3c0 \u041d\u0430\u043f\u0438\u0448\u0438 \u043c\u0430\u0442\u0447 NBA:\n\nLakers - Celtics\nWarriors - Knicks"
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
                f"\u26a0\ufe0f Could not analyze: {team1} - {team2}"
                if language == "en"
                else f"\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c: {team1} - {team2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analyze_tennis_text(text, language="ru"):
    matches = detect_matches(text)

    if not matches:
        return (
            "\U0001f3be Send a tennis match:\n\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "\U0001f3be \u041e\u0442\u043f\u0440\u0430\u0432\u044c \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0439 \u043c\u0430\u0442\u0447:\n\nCarlos Alcaraz - Jannik Sinner"
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
                f"\u26a0\ufe0f Could not analyze: {player1} - {player2}"
                if language == "en"
                else f"\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c: {player1} - {player2}"
            )
            results.append(f"#{index}\n{message}")

    return "\n\n".join(results)


def analysis_prompt(sport_mode, language="ru"):
    if sport_mode == "nba":
        return (
            "\U0001f3c0 Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks"
            if language == "en"
            else "\U0001f3c0 \u041d\u0430\u043f\u0438\u0448\u0438 \u043c\u0430\u0442\u0447 NBA:\n\nLakers - Celtics\nWarriors - Knicks"
        )

    if sport_mode == "tennis":
        return (
            "\U0001f3be Send a tennis match:\n\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "\U0001f3be \u041e\u0442\u043f\u0440\u0430\u0432\u044c \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0439 \u043c\u0430\u0442\u0447:\n\nCarlos Alcaraz - Jannik Sinner"
        )

    return (
        "\u26bd Send a football match:\n\nReal Madrid - Barcelona"
        if language == "en"
        else "\u26bd \u041d\u0430\u043f\u0438\u0448\u0438 \u0444\u0443\u0442\u0431\u043e\u043b\u044c\u043d\u044b\u0439 \u043c\u0430\u0442\u0447:\n\nReal Madrid - Barcelona"
    )


def analysis_error_message(sport_mode, language="ru"):
    if sport_mode == "nba":
        return (
            "\u26a0\ufe0f Could not complete the NBA analysis.\n\n"
            "Check the format:\nLakers - Celtics"
            if language == "en"
            else "\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0430\u043d\u0430\u043b\u0438\u0437 NBA.\n\n"
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0444\u043e\u0440\u043c\u0430\u0442:\nLakers - Celtics"
        )

    if sport_mode == "tennis":
        return (
            "\u26a0\ufe0f Could not complete the tennis analysis.\n\n"
            "Check the format:\nCarlos Alcaraz - Jannik Sinner"
            if language == "en"
            else "\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437.\n\n"
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0444\u043e\u0440\u043c\u0430\u0442:\nCarlos Alcaraz - Jannik Sinner"
        )

    return (
        "\u26a0\ufe0f Could not complete the football analysis.\n\n"
        "Check the format:\nReal Madrid - Barcelona"
        if language == "en"
        else "\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0444\u0443\u0442\u0431\u043e\u043b\u044c\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437.\n\n"
        "\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u0444\u043e\u0440\u043c\u0430\u0442:\nReal Madrid - Barcelona"
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
                f"\U0001f512 Free analyses remaining today: {remaining}\n\n"
                "Send fewer matchups or activate FLUX PRO."
                if language == "en"
                else f"\U0001f512 \u0423 \u0432\u0430\u0441 \u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0445 \u0430\u043d\u0430\u043b\u0438\u0437\u043e\u0432 \u0441\u0435\u0433\u043e\u0434\u043d\u044f: {remaining}\n\n"
                "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u043c\u0435\u043d\u044c\u0448\u0435 \u043c\u0430\u0442\u0447\u0435\u0439 \u0438\u043b\u0438 \u043e\u0444\u043e\u0440\u043c\u0438\u0442\u0435 FLUX PRO."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return

    sport_mode = get_user_sport(user_id) or "football"

    if len(matches) > 1:
        analyzing_text = (
            f"\u23f3 Analyzing {len(matches)} matchups..."
            if language == "en"
            else f"\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e {len(matches)} \u043c\u0430\u0442\u0447\u0435\u0439..."
        )
    elif sport_mode == "nba":
        analyzing_text = (
            "\u23f3 Analyzing the NBA game..."
            if language == "en"
            else "\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e \u043c\u0430\u0442\u0447 NBA..."
        )
    elif sport_mode == "tennis":
        analyzing_text = (
            "\u23f3 Analyzing the tennis match..."
            if language == "en"
            else "\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0439 \u043c\u0430\u0442\u0447..."
        )
    else:
        analyzing_text = (
            "\u23f3 Analyzing the football match..."
            if language == "en"
            else "\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e \u0444\u0443\u0442\u0431\u043e\u043b\u044c\u043d\u044b\u0439 \u043c\u0430\u0442\u0447..."
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
            else "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043f\u043b\u0430\u0442\u0451\u0436. \u0421\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u043d\u043e\u0432\u044b\u0439 \u0441\u0447\u0451\u0442."
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
            "\u26a0\ufe0f Payment data failed verification."
            if language == "en"
            else "\u26a0\ufe0f \u0414\u0430\u043d\u043d\u044b\u0435 \u043f\u043b\u0430\u0442\u0435\u0436\u0430 \u043d\u0435 \u043f\u0440\u043e\u0448\u043b\u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0443."
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
        answer_callback_query(callback_id, "\u042f\u0437\u044b\u043a \u0438\u0437\u043c\u0435\u043d\u0451\u043d \u043d\u0430 \u0440\u0443\u0441\u0441\u043a\u0438\u0439.")
        send_message(chat_id, start_message("ru"), reply_markup=main_menu("ru"))
        return

    answer_callback_query(callback_id)


@app.route("/")
def home():
    return "FLUX AI Sports PRO v5.0 is running!"


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
                "\u26a1 Welcome to Flux AI\nChoose your language.\n\n"
                "\u26a1 \u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 Flux AI\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a.",
                reply_markup=language_keyboard(),
            )
            return "OK", 200

        if text in ["/language", "\U0001f310 Language", "\U0001f310 \u042f\u0437\u044b\u043a"]:
            send_message(
                chat_id,
                "Choose your language.\n\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a.",
                reply_markup=language_keyboard(),
            )
            return "OK", 200

        if text in ["\u26bd \u0424\u0443\u0442\u0431\u043e\u043b", "\u26bd Football"]:
            set_user_sport(user_id, "football")
            message_text = (
                "\u26bd Football mode selected.\n\n"
                "Send a match:\nReal Madrid - Barcelona"
                if language == "en"
                else "\u26bd \u0412\u044b\u0431\u0440\u0430\u043d \u0440\u0435\u0436\u0438\u043c \u0444\u0443\u0442\u0431\u043e\u043b\u0430.\n\n"
                "\u041d\u0430\u043f\u0438\u0448\u0438 \u043c\u0430\u0442\u0447:\nReal Madrid - Barcelona"
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if text == "\U0001f3c0 NBA":
            set_user_sport(user_id, "nba")
            message_text = (
                "\U0001f3c0 NBA mode selected.\n\n"
                "Send a game:\nLakers - Celtics\n\n"
                "The first team is treated as the home team."
                if language == "en"
                else "\U0001f3c0 \u0412\u044b\u0431\u0440\u0430\u043d \u0440\u0435\u0436\u0438\u043c NBA.\n\n"
                "\u041d\u0430\u043f\u0438\u0448\u0438 \u043c\u0430\u0442\u0447:\nLakers - Celtics\n\n"
                "\u041f\u0435\u0440\u0432\u0430\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430 \u0441\u0447\u0438\u0442\u0430\u0435\u0442\u0441\u044f \u0445\u043e\u0437\u044f\u0438\u043d\u043e\u043c \u043f\u043b\u043e\u0449\u0430\u0434\u043a\u0438."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if text in ["\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441", "\U0001f3be Tennis"]:
            set_user_sport(user_id, "tennis")
            message_text = (
                "\U0001f3be Tennis mode selected.\n\n"
                "Send a match:\nCarlos Alcaraz - Jannik Sinner\n\n"
                "Tennis AI is currently in Beta."
                if language == "en"
                else "\U0001f3be \u0412\u044b\u0431\u0440\u0430\u043d \u0440\u0435\u0436\u0438\u043c \u0442\u0435\u043d\u043d\u0438\u0441\u0430.\n\n"
                "\u041e\u0442\u043f\u0440\u0430\u0432\u044c \u043c\u0430\u0442\u0447:\nCarlos Alcaraz - Jannik Sinner\n\n"
                "Tennis AI \u0441\u0435\u0439\u0447\u0430\u0441 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0432 Beta-\u0440\u0435\u0436\u0438\u043c\u0435."
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

        if text in ["\u26bd \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0430", "\u26bd Analyze Match"]:
            sport_mode = get_user_sport(user_id) or "football"
            send_message(
                chat_id,
                analysis_prompt(sport_mode, language),
                reply_markup=main_menu(language),
            )
            return "OK", 200

        button_commands = {
            "\U0001f3c6 \u0422\u041e\u041f-3 \u0434\u043d\u044f": "/today",
            "\U0001f3c6 Top 3 Today": "/today",
            "\U0001f30d \u0427\u041c-2026": "/worldcup",
            "\U0001f30d World Cup 2026": "/worldcup",
            "\U0001f4c8 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b": "/results",
            "\U0001f4c8 Results": "/results",
            "\U0001f3c6 \u041a\u0430\u043d\u0430\u043b": "/channel",
            "\U0001f3c6 Channel": "/channel",
            "\U0001f48e FLUX PRO": "/pro",
            "\U0001f464 \u041c\u043e\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c": "/profile",
            "\U0001f464 My Profile": "/profile",
            "\u2139\ufe0f \u041e \u043f\u0440\u043e\u0435\u043a\u0442\u0435": "/about",
            "\u2139\ufe0f About": "/about",
            "\U0001f4ca \u0421\u0442\u0430\u0442\u0443\u0441": "/status",
            "\U0001f4ca Status": "/status",
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
                    "\u26d4 Access denied."
                    if language == "en"
                    else "\u26d4 \u0414\u043e\u0441\u0442\u0443\u043f \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d."
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
                "\U0001f3c6 Open channel"
                if language == "en"
                else "\U0001f3c6 \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u043d\u0430\u043b"
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
                    "\u26a0\ufe0f Could not open Telegram Stars payment."
                    if language == "en"
                    else "\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043e\u043f\u043b\u0430\u0442\u0443 Telegram Stars."
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
