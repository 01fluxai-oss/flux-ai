# -*- coding: ascii -*-
import os
from datetime import datetime
from threading import Thread
from zoneinfo import ZoneInfo

import requests
from flask import Flask, request

from database.db import (
    activate_pro, add_user, free_limit_message, get_admin_stats,
    get_today_usage, get_user, get_user_language, get_user_sport,
    increase_today_usage, init_db, is_pro, save_payment,
    save_prediction, set_user_language, set_user_sport,
)
from payments.stars import send_stars_invoice
from tennis_analyzer import analyze_tennis_match
from ufc_analyzer import analyze_ufc_match


BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get(
    "PUBLIC_URL",
    "https://flux-ai-8p34.onrender.com",
).rstrip("/")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"
FREE_DAILY_LIMIT = 100
PRO_PRICE_STARS = 500
PRO_DAYS = 30

app = Flask(__name__)
init_db()


def telegram_api(method, payload):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        json=payload,
        timeout=20,
    )
    result = response.json()
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


def answer_callback_query(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        return telegram_api("answerCallbackQuery", payload)
    except Exception as error:
        print("CALLBACK_ERROR:", repr(error), flush=True)
        return None


def language_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "\U0001f1fa\U0001f1f8 English", "callback_data": "lang_en"},
            {"text": "\U0001f1f7\U0001f1fa \u0420\u0443\u0441\u0441\u043a\u0438\u0439", "callback_data": "lang_ru"},
        ]]
    }


def main_menu(language="ru"):
    if language == "en":
        rows = [
            ["\u26bd Football", "\U0001f3c0 NBA"],
            ["\U0001f3be Tennis", "\U0001f94a UFC"],
            ["\U0001f4c5 Tennis Today"],
            ["\U0001f3af Analyze Match"],
            ["\U0001f3c6 Top 3 Today", "\U0001f30d World Cup 2026"],
            ["\U0001f4c8 Results"],
            ["\U0001f3c6 Channel", "\U0001f48e FLUX PRO"],
            ["\U0001f464 My Profile"],
            ["\u2139\ufe0f About", "\U0001f4ca Status"],
            ["\U0001f310 Language"],
        ]
    else:
        rows = [
            ["\u26bd \u0424\u0443\u0442\u0431\u043e\u043b", "\U0001f3c0 NBA"],
            ["\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441", "\U0001f94a UFC"],
            ["\U0001f4c5 \u0422\u0435\u043d\u043d\u0438\u0441 \u0441\u0435\u0433\u043e\u0434\u043d\u044f"],
            ["\U0001f3af \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0430"],
            ["\U0001f3c6 \u0422\u041e\u041f-3 \u0434\u043d\u044f", "\U0001f30d \u0427\u041c-2026"],
            ["\U0001f4c8 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b"],
            ["\U0001f3c6 \u041a\u0430\u043d\u0430\u043b", "\U0001f48e FLUX PRO"],
            ["\U0001f464 \u041c\u043e\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c"],
            ["\u2139\ufe0f \u041e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", "\U0001f4ca \u0421\u0442\u0430\u0442\u0443\u0441"],
            ["\U0001f310 \u042f\u0437\u044b\u043a"],
        ]
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        str(text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2212", "-")
        .strip()
    )


def detect_match(line):
    line = normalize_text(line).split("|", 1)[0].strip()
    for separator in [" - ", " vs ", " VS ", " Vs ", " v ", " V ", "-"]:
        if separator in line:
            left, right = line.split(separator, 1)
            left, right = left.strip(), right.strip()
            if left and right:
                return left, right
    return None, None


def detect_matches(text):
    matches = []
    for line in str(text or "").splitlines():
        left, right = detect_match(line)
        if left and right:
            matches.append((left, right))
    return matches


def sport_title(sport, language="ru"):
    titles = {
        "football": {"ru": "\u26bd \u0424\u0443\u0442\u0431\u043e\u043b", "en": "\u26bd Football"},
        "nba": {"ru": "\U0001f3c0 NBA", "en": "\U0001f3c0 NBA"},
        "tennis": {"ru": "\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441", "en": "\U0001f3be Tennis"},
        "ufc": {"ru": "\U0001f94a UFC", "en": "\U0001f94a UFC"},
    }
    return titles.get(sport, titles["football"]).get(language)


def start_message(language="ru"):
    if language == "en":
        return (
            "\U0001f44b Welcome! I am FLUX AI Sports PRO v5.1\n\n"
            "\u26bd Football analysis\n\U0001f3c0 NBA analysis\n"
            "\U0001f3be Tennis analysis (Beta)\n\U0001f94a UFC analysis (Beta)\n"
            "\U0001f3c6 Top 3 of the day\n\U0001f30d World Cup analysis\n"
            "\U0001f4c8 Results\n\U0001f48e FLUX PRO\n\n"
            f"FREE: {FREE_DAILY_LIMIT} analyses per day\n"
            "PRO: unlimited\n\nChoose a sport, then send a matchup."
        )
    return (
        "\U0001f44b \u041f\u0440\u0438\u0432\u0435\u0442! \u042f FLUX AI Sports PRO v5.1\n\n"
        "\u26bd \u0410\u043d\u0430\u043b\u0438\u0437 \u0444\u0443\u0442\u0431\u043e\u043b\u0430\n\U0001f3c0 \u0410\u043d\u0430\u043b\u0438\u0437 NBA\n"
        "\U0001f3be \u0410\u043d\u0430\u043b\u0438\u0437 \u0442\u0435\u043d\u043d\u0438\u0441\u0430 (Beta)\n\U0001f94a \u0410\u043d\u0430\u043b\u0438\u0437 UFC (Beta)\n"
        "\U0001f3c6 \u0422\u041e\u041f-3 \u0434\u043d\u044f\n\U0001f30d \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0435\u0439 \u0427\u041c\n"
        "\U0001f4c8 \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b\n\U0001f48e FLUX PRO\n\n"
        f"FREE: {FREE_DAILY_LIMIT} \u0430\u043d\u0430\u043b\u0438\u0437\u043e\u0432 \u0432 \u0434\u0435\u043d\u044c\n"
        "PRO: \u0431\u0435\u0437\u043b\u0438\u043c\u0438\u0442\n\n\u0412\u044b\u0431\u0435\u0440\u0438 \u0432\u0438\u0434 \u0441\u043f\u043e\u0440\u0442\u0430 \u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u044c \u0441\u043e\u0431\u044b\u0442\u0438\u0435."
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "Choose a sport first:\n\n"
            "\u26bd Real Madrid - Barcelona\n"
            "\U0001f3c0 Lakers - Celtics\n"
            "\U0001f3be Carlos Alcaraz - Jannik Sinner\n"
            "\U0001f94a Fighter 1 - Fighter 2"
        )
    return (
        "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438 \u0432\u0438\u0434 \u0441\u043f\u043e\u0440\u0442\u0430:\n\n"
        "\u26bd Real Madrid - Barcelona\n"
        "\U0001f3c0 Lakers - Celtics\n"
        "\U0001f3be Carlos Alcaraz - Jannik Sinner\n"
        "\U0001f94a \u0411\u043e\u0435\u0446 1 - \u0411\u043e\u0435\u0446 2"
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "\u2139\ufe0f FLUX AI analyzes football, NBA, tennis and UFC.\n\n"
            "Tennis and UFC are in Beta. The current UFC module is a "
            "demo model until verified live statistics are connected.\n\n"
            "Predictions are informational and do not guarantee results."
        )
    return (
        "\u2139\ufe0f FLUX AI \u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u0444\u0443\u0442\u0431\u043e\u043b, NBA, \u0442\u0435\u043d\u043d\u0438\u0441 \u0438 UFC.\n\n"
        "\u0422\u0435\u043d\u043d\u0438\u0441 \u0438 UFC \u0440\u0430\u0431\u043e\u0442\u0430\u044e\u0442 \u0432 Beta. \u0422\u0435\u043a\u0443\u0449\u0438\u0439 UFC-\u043c\u043e\u0434\u0443\u043b\u044c \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f "
        "\u0434\u0435\u043c\u043e\u043d\u0441\u0442\u0440\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u043c \u0434\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0439 \u0440\u0435\u0430\u043b\u044c\u043d\u043e\u0439 \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0438.\n\n"
        "\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0440\u0443\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "\u2705 FLUX AI Sports is running.\n\n"
            "Version: PRO v5.1\n"
            "Sports: Football + NBA + Tennis Beta + UFC Beta\n"
            f"Channel: {CHANNEL_USERNAME}\nStatus: Online"
        )
    return (
        "\u2705 FLUX AI Sports \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442.\n\n"
        "\u0412\u0435\u0440\u0441\u0438\u044f: PRO v5.1\n"
        "\u0421\u043f\u043e\u0440\u0442: \u0424\u0443\u0442\u0431\u043e\u043b + NBA + \u0422\u0435\u043d\u043d\u0438\u0441 Beta + UFC Beta\n"
        f"\u041a\u0430\u043d\u0430\u043b: {CHANNEL_USERNAME}\n\u0421\u0442\u0430\u0442\u0443\u0441: Online"
    )


def profile_message(user_id, language="ru"):
    user = get_user(user_id)
    if not user:
        return "Profile not found." if language == "en" else "\u041f\u0440\u043e\u0444\u0438\u043b\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d."

    pro_active = is_pro(user_id)
    usage = get_today_usage(user_id)
    sport = get_user_sport(user_id) or "football"

    if language == "en":
        return (
            "\U0001f464 MY PROFILE\n\n"
            f"\U0001f194 ID: {user_id}\n"
            f"\U0001f48e FLUX PRO: {'\u2705 Active' if pro_active else '\u274c Inactive'}\n"
            f"\U0001f3af Selected sport: {sport_title(sport, 'en')}\n"
            f"\U0001f4ca Analyses today: {'Unlimited' if pro_active else f'{usage}/{FREE_DAILY_LIMIT}'}"
        )
    return (
        "\U0001f464 \u041c\u041e\u0419 \u041f\u0420\u041e\u0424\u0418\u041b\u042c\n\n"
        f"\U0001f194 ID: {user_id}\n"
        f"\U0001f48e FLUX PRO: {'\u2705 \u0410\u043a\u0442\u0438\u0432\u0435\u043d' if pro_active else '\u274c \u041d\u0435 \u0430\u043a\u0442\u0438\u0432\u0435\u043d'}\n"
        f"\U0001f3af \u0412\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 \u0441\u043f\u043e\u0440\u0442: {sport_title(sport, 'ru')}\n"
        f"\U0001f4ca \u0410\u043d\u0430\u043b\u0438\u0437\u044b \u0441\u0435\u0433\u043e\u0434\u043d\u044f: {'\u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442' if pro_active else f'{usage}/{FREE_DAILY_LIMIT}'}"
    )


def pro_message(language="ru"):
    if language == "en":
        return (
            "\U0001f48e FLUX AI PRO\n\n"
            "\u2705 Unlimited analysis\n"
            "\u2705 Football, NBA, Tennis and UFC\n"
            "\u2705 Extended statistics\n\u2705 Daily Top 3\n\n"
            f"Price: \u2b50{PRO_PRICE_STARS} / {PRO_DAYS} days"
        )
    return (
        "\U0001f48e FLUX AI PRO\n\n"
        "\u2705 \u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437\n"
        "\u2705 \u0424\u0443\u0442\u0431\u043e\u043b, NBA, \u0442\u0435\u043d\u043d\u0438\u0441 \u0438 UFC\n"
        "\u2705 \u0420\u0430\u0441\u0448\u0438\u0440\u0435\u043d\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430\n\u2705 \u0422\u041e\u041f-3 \u0434\u043d\u044f\n\n"
        f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c: \u2b50{PRO_PRICE_STARS} / {PRO_DAYS} \u0434\u043d\u0435\u0439"
    )


def analyze_football(text, language):
    from engine.analyzer import analyze_and_format
    return analyze_group(text, language, analyze_and_format)


def analyze_nba(text, language):
    from engine.nba_analyzer import analyze_and_format_nba
    return analyze_group(text, language, analyze_and_format_nba)


def analyze_tennis(text, language):
    return analyze_group(text, language, analyze_tennis_match)


def analyze_ufc(text, language):
    return analyze_group(text, language, analyze_ufc_match)


def analyze_group(text, language, analyzer):
    matches = detect_matches(text)
    if not matches:
        return help_message(language)

    results = []
    for index, (left, right) in enumerate(matches[:5], start=1):
        try:
            result = analyzer(left, right, language)
            results.append(result if len(matches) == 1 else f"#{index}\n{result}")
        except Exception as error:
            print("ANALYSIS_ITEM_ERROR:", repr(error), flush=True)
            message = (
                f"\u26a0\ufe0f Could not analyze: {left} - {right}"
                if language == "en"
                else f"\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c: {left} - {right}"
            )
            results.append(message if len(matches) == 1 else f"#{index}\n{message}")
    return "\n\n".join(results)


def analysis_prompt(sport, language="ru"):
    prompts = {
        "football": {
            "en": "\u26bd Send a football match:\nReal Madrid - Barcelona",
            "ru": "\u26bd \u041d\u0430\u043f\u0438\u0448\u0438 \u0444\u0443\u0442\u0431\u043e\u043b\u044c\u043d\u044b\u0439 \u043c\u0430\u0442\u0447:\nReal Madrid - Barcelona",
        },
        "nba": {
            "en": "\U0001f3c0 Send an NBA game:\nLakers - Celtics",
            "ru": "\U0001f3c0 \u041d\u0430\u043f\u0438\u0448\u0438 \u043c\u0430\u0442\u0447 NBA:\nLakers - Celtics",
        },
        "tennis": {
            "en": "\U0001f3be Send a tennis match:\nCarlos Alcaraz - Jannik Sinner",
            "ru": "\U0001f3be \u041e\u0442\u043f\u0440\u0430\u0432\u044c \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0439 \u043c\u0430\u0442\u0447:\nCarlos Alcaraz - Jannik Sinner",
        },
        "ufc": {
            "en": "\U0001f94a Send a UFC fight:\nFighter 1 - Fighter 2",
            "ru": "\U0001f94a \u041e\u0442\u043f\u0440\u0430\u0432\u044c \u0431\u043e\u0439 UFC:\n\u0411\u043e\u0435\u0446 1 - \u0411\u043e\u0435\u0446 2",
        },
    }
    return prompts.get(sport, prompts["football"])[language]


def handle_analysis(chat_id, user_id, text, language):
    matches = detect_matches(text)
    sport = get_user_sport(user_id) or "football"

    if not matches:
        send_message(chat_id, analysis_prompt(sport, language), main_menu(language))
        return

    if not is_pro(user_id):
        remaining = FREE_DAILY_LIMIT - get_today_usage(user_id)
        if remaining <= 0:
            send_message(chat_id, free_limit_message(language), main_menu(language))
            return
        if len(matches) > remaining:
            message = (
                f"\U0001f512 Free analyses remaining: {remaining}"
                if language == "en"
                else f"\U0001f512 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0445 \u0430\u043d\u0430\u043b\u0438\u0437\u043e\u0432: {remaining}"
            )
            send_message(chat_id, message, main_menu(language))
            return

    send_message(
        chat_id,
        "\u23f3 Analyzing..." if language == "en" else "\u23f3 \u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e...",
        main_menu(language),
    )

    analyzers = {
        "football": (analyze_football, "FOOTBALL"),
        "nba": (analyze_nba, "NBA"),
        "tennis": (analyze_tennis, "TENNIS"),
        "ufc": (analyze_ufc, "UFC"),
    }

    try:
        analyzer, prefix = analyzers.get(sport, analyzers["football"])
        answer = analyzer(text, language)
        send_message(chat_id, answer, main_menu(language))

        for left, right in matches:
            save_prediction(user_id, f"[{prefix}] {left} - {right}", answer)
            if not is_pro(user_id):
                increase_today_usage(user_id)
    except Exception as error:
        print("MATCH_ANALYSIS_ERROR:", repr(error), flush=True)
        send_message(
            chat_id,
            "\u26a0\ufe0f Analysis failed." if language == "en" else "\u26a0\ufe0f \u0410\u043d\u0430\u043b\u0438\u0437 \u043d\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d.",
            main_menu(language),
        )


def parse_invoice_user_id(payload):
    prefix = "flux_pro_30_days:"
    payload = str(payload or "")
    if not payload.startswith(prefix):
        return None
    try:
        return int(payload[len(prefix):])
    except ValueError:
        return None


def process_pre_checkout_query(query):
    query_id = query.get("id")
    user_id = query.get("from", {}).get("id")
    valid = bool(
        query_id
        and user_id
        and parse_invoice_user_id(query.get("invoice_payload")) == user_id
        and query.get("currency") == "XTR"
        and int(query.get("total_amount", 0)) == PRO_PRICE_STARS
    )
    payload = {"pre_checkout_query_id": query_id, "ok": valid}
    if not valid:
        payload["error_message"] = "Payment verification failed."
    telegram_api("answerPreCheckoutQuery", payload)


def process_successful_payment(message):
    payment = message.get("successful_payment", {})
    user = message.get("from", {})
    user_id = user.get("id")
    chat_id = message.get("chat", {}).get("id")
    language = get_user_language(user_id) or "ru"

    valid = bool(
        user_id
        and chat_id
        and parse_invoice_user_id(payment.get("invoice_payload")) == user_id
        and payment.get("currency") == "XTR"
        and int(payment.get("total_amount", 0)) == PRO_PRICE_STARS
    )

    if not valid:
        send_message(
            chat_id,
            "\u26a0\ufe0f Payment verification failed."
            if language == "en"
            else "\u26a0\ufe0f \u041f\u043b\u0430\u0442\u0451\u0436 \u043d\u0435 \u043f\u0440\u043e\u0448\u0451\u043b \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0443.",
            main_menu(language),
        )
        return

    add_user(user)
    activate_pro(user_id, PRO_DAYS)
    save_payment(
        user_id,
        provider="telegram_stars",
        amount=payment.get("total_amount", 0),
        currency="XTR",
        status="paid",
    )
    send_message(
        chat_id,
        "\U0001f389 FLUX AI PRO activated!"
        if language == "en"
        else "\U0001f389 FLUX AI PRO \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d!",
        main_menu(language),
    )


def process_callback_query(callback):
    callback_id = callback.get("id")
    user = callback.get("from", {})
    user_id = user.get("id")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    data = callback.get("data")

    if not user_id or not chat_id:
        if callback_id:
            answer_callback_query(callback_id)
        return

    add_user(user)

    if data == "lang_en":
        set_user_language(user_id, "en")
        answer_callback_query(callback_id, "Language changed.")
        send_message(chat_id, start_message("en"), main_menu("en"))
        return

    if data == "lang_ru":
        set_user_language(user_id, "ru")
        answer_callback_query(callback_id, "\u042f\u0437\u044b\u043a \u0438\u0437\u043c\u0435\u043d\u0451\u043d.")
        send_message(chat_id, start_message("ru"), main_menu("ru"))
        return

    answer_callback_query(callback_id)


def send_tennis_today(chat_id, language="ru"):
    try:
        from providers.tennis_provider import get_today_singles_matches

        date_text = datetime.now(ZoneInfo("Asia/Yerevan")).strftime("%Y-%m-%d")
        matches = get_today_singles_matches(
            date_text=date_text,
            timezone_name="Asia/Yerevan",
            max_matches=10,
        )

        if not matches:
            send_message(
                chat_id,
                "\U0001f4c5 No matches found today."
                if language == "en"
                else "\U0001f4c5 \u041c\u0430\u0442\u0447\u0438 \u043d\u0430 \u0441\u0435\u0433\u043e\u0434\u043d\u044f \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b.",
                main_menu(language),
            )
            return

        lines = ["\U0001f4c5 TENNIS TODAY" if language == "en" else "\U0001f4c5 \u0422\u0415\u041d\u041d\u0418\u0421 \u0421\u0415\u0413\u041e\u0414\u041d\u042f"]
        for index, match in enumerate(matches, 1):
            live = " \U0001f534 LIVE" if match.get("live") else ""
            tournament = match.get("tournament") or ""
            tournament_line = f"\n\U0001f3df {tournament[:70]}" if tournament else ""
            lines.append(
                f"{index}. {match.get('time') or '\u2014'}{live} | "
                f"{match.get('player1') or '\u2014'} \u2014 {match.get('player2') or '\u2014'}"
                f"{tournament_line}\n\U0001f3be {(match.get('surface') or 'hard').title()}"
            )

        instruction = (
            "\n\nTo analyze, send:\nPlayer 1 - Player 2 | surface"
            if language == "en"
            else "\n\n\u0414\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430 \u043e\u0442\u043f\u0440\u0430\u0432\u044c:\n\u0418\u0433\u0440\u043e\u043a 1 - \u0418\u0433\u0440\u043e\u043a 2 | \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u0435"
        )
        send_message(chat_id, "\n\n".join(lines) + instruction, main_menu(language))
    except Exception as error:
        print("TENNIS_TODAY_ERROR:", repr(error), flush=True)
        send_message(
            chat_id,
            "\u26a0\ufe0f Could not load tennis matches."
            if language == "en"
            else "\u26a0\ufe0f \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u044b\u0435 \u043c\u0430\u0442\u0447\u0438.",
            main_menu(language),
        )


@app.route("/")
def home():
    return "FLUX AI Sports PRO v5.1 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}

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
                language_keyboard(),
            )
            return "OK", 200

        if text in ["/language", "\U0001f310 Language", "\U0001f310 \u042f\u0437\u044b\u043a"]:
            send_message(
                chat_id,
                "Choose your language.\n\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u044f\u0437\u044b\u043a.",
                language_keyboard(),
            )
            return "OK", 200

        sport_buttons = {
            "\u26bd \u0424\u0443\u0442\u0431\u043e\u043b": "football",
            "\u26bd Football": "football",
            "\U0001f3c0 NBA": "nba",
            "\U0001f3be \u0422\u0435\u043d\u043d\u0438\u0441": "tennis",
            "\U0001f3be Tennis": "tennis",
            "\U0001f94a UFC": "ufc",
        }

        if text in sport_buttons:
            sport = sport_buttons[text]
            set_user_sport(user_id, sport)
            send_message(
                chat_id,
                analysis_prompt(sport, language),
                main_menu(language),
            )
            return "OK", 200

        if text in ["\U0001f3af \u0410\u043d\u0430\u043b\u0438\u0437 \u043c\u0430\u0442\u0447\u0430", "\U0001f3af Analyze Match"]:
            send_message(
                chat_id,
                analysis_prompt(get_user_sport(user_id) or "football", language),
                main_menu(language),
            )
            return "OK", 200

        commands = {
            "\U0001f4c5 \u0422\u0435\u043d\u043d\u0438\u0441 \u0441\u0435\u0433\u043e\u0434\u043d\u044f": "/tennis_today",
            "\U0001f4c5 Tennis Today": "/tennis_today",
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
        text = commands.get(text, text)

        if text in ["/help", "/analyze"]:
            send_message(chat_id, help_message(language), main_menu(language))
        elif text == "/tennis_today":
            set_user_sport(user_id, "tennis")
            send_tennis_today(chat_id, language)
        elif text == "/about":
            send_message(chat_id, about_message(language), main_menu(language))
        elif text == "/status":
            send_message(chat_id, status_message(language), main_menu(language))
        elif text == "/profile":
            send_message(chat_id, profile_message(user_id, language), main_menu(language))
        elif text == "/admin":
            if user_id != ADMIN_TELEGRAM_ID:
                send_message(
                    chat_id,
                    "\u26d4 Access denied." if language == "en" else "\u26d4 \u0414\u043e\u0441\u0442\u0443\u043f \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d.",
                    main_menu(language),
                )
            else:
                stats = get_admin_stats()
                send_message(chat_id, str(stats), main_menu(language))
        elif text == "/channel":
            send_message(
                chat_id,
                CHANNEL_URL,
                {"inline_keyboard": [[{"text": "\U0001f3c6 FLUX AI", "url": CHANNEL_URL}]]},
            )
        elif text == "/worldcup":
            set_user_sport(user_id, "football")
            send_message(chat_id, analysis_prompt("football", language), main_menu(language))
        elif text == "/results":
            send_message(
                chat_id,
                "\U0001f4c8 Results are being prepared."
                if language == "en"
                else "\U0001f4c8 \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u043e\u0432 \u0433\u043e\u0442\u043e\u0432\u0438\u0442\u0441\u044f.",
                main_menu(language),
            )
        elif text == "/today":
            send_message(chat_id, CHANNEL_URL, main_menu(language))
        elif text == "/pro":
            send_message(chat_id, pro_message(language), main_menu(language))
            send_stars_invoice(
                bot_token=BOT_TOKEN,
                chat_id=chat_id,
                user_id=user_id,
                stars_price=PRO_PRICE_STARS,
                language=language,
            )
        elif text:
            handle_analysis(chat_id, user_id, text, language)
        else:
            send_message(chat_id, help_message(language), main_menu(language))

        return "OK", 200

    except Exception as error:
        print("TELEGRAM_WEBHOOK_ERROR:", repr(error), flush=True)
        return "OK", 200


def set_webhook():
    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": f"{PUBLIC_URL}/telegram/{BOT_TOKEN}",
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
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
