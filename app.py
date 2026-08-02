# -*- coding: utf-8 -*-
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
FREE_DAILY_LIMIT = 10
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
            {"text": "ðºð¸ English", "callback_data": "lang_en"},
            {"text": "ð·ðº Ð ÑÑÑÐºÐ¸Ð¹", "callback_data": "lang_ru"},
        ]]
    }


def main_menu(language="ru"):
    if language == "en":
        rows = [
            ["â½ Football", "ð NBA"],
            ["ð¾ Tennis", "ð¥ UFC"],
            ["ð Tennis Today"],
            ["ð¯ Analyze Match"],
            ["ð Top 3 Today", "ð World Cup 2026"],
            ["ð Results"],
            ["ð Channel", "ð FLUX PRO"],
            ["ð¤ My Profile"],
            ["â¹ï¸ About", "ð Status"],
            ["ð Language"],
        ]
    else:
        rows = [
            ["â½ Ð¤ÑÑÐ±Ð¾Ð»", "ð NBA"],
            ["ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ", "ð¥ UFC"],
            ["ð Ð¢ÐµÐ½Ð½Ð¸Ñ ÑÐµÐ³Ð¾Ð´Ð½Ñ"],
            ["ð¯ ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐ°"],
            ["ð Ð¢ÐÐ-3 Ð´Ð½Ñ", "ð Ð§Ð-2026"],
            ["ð Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ"],
            ["ð ÐÐ°Ð½Ð°Ð»", "ð FLUX PRO"],
            ["ð¤ ÐÐ¾Ð¹ Ð¿ÑÐ¾ÑÐ¸Ð»Ñ"],
            ["â¹ï¸ Ð Ð¿ÑÐ¾ÐµÐºÑÐµ", "ð Ð¡ÑÐ°ÑÑÑ"],
            ["ð Ð¯Ð·ÑÐº"],
        ]
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        str(text or "")
        .replace("â", "-")
        .replace("â", "-")
        .replace("â", "-")
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
        "football": {"ru": "â½ Ð¤ÑÑÐ±Ð¾Ð»", "en": "â½ Football"},
        "nba": {"ru": "ð NBA", "en": "ð NBA"},
        "tennis": {"ru": "ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ", "en": "ð¾ Tennis"},
        "ufc": {"ru": "ð¥ UFC", "en": "ð¥ UFC"},
    }
    return titles.get(sport, titles["football"]).get(language)


def start_message(language="ru"):
    if language == "en":
        return (
            "ð Welcome! I am FLUX AI Sports PRO v5.1\n\n"
            "â½ Football analysis\nð NBA analysis\n"
            "ð¾ Tennis analysis (Beta)\nð¥ UFC analysis (Beta)\n"
            "ð Top 3 of the day\nð World Cup analysis\n"
            "ð Results\nð FLUX PRO\n\n"
            f"FREE: {FREE_DAILY_LIMIT} analyses per day\n"
            "PRO: unlimited\n\nChoose a sport, then send a matchup."
        )
    return (
        "ð ÐÑÐ¸Ð²ÐµÑ! Ð¯ FLUX AI Sports PRO v5.1\n\n"
        "â½ ÐÐ½Ð°Ð»Ð¸Ð· ÑÑÑÐ±Ð¾Ð»Ð°\nð ÐÐ½Ð°Ð»Ð¸Ð· NBA\n"
        "ð¾ ÐÐ½Ð°Ð»Ð¸Ð· ÑÐµÐ½Ð½Ð¸ÑÐ° (Beta)\nð¥ ÐÐ½Ð°Ð»Ð¸Ð· UFC (Beta)\n"
        "ð Ð¢ÐÐ-3 Ð´Ð½Ñ\nð ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐµÐ¹ Ð§Ð\n"
        "ð Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ\nð FLUX PRO\n\n"
        f"FREE: {FREE_DAILY_LIMIT} Ð°Ð½Ð°Ð»Ð¸Ð·Ð¾Ð² Ð² Ð´ÐµÐ½Ñ\n"
        "PRO: Ð±ÐµÐ·Ð»Ð¸Ð¼Ð¸Ñ\n\nÐÑÐ±ÐµÑÐ¸ Ð²Ð¸Ð´ ÑÐ¿Ð¾ÑÑÐ° Ð¸ Ð¾ÑÐ¿ÑÐ°Ð²Ñ ÑÐ¾Ð±ÑÑÐ¸Ðµ."
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "Choose a sport first:\n\n"
            "â½ Real Madrid - Barcelona\n"
            "ð Lakers - Celtics\n"
            "ð¾ Carlos Alcaraz - Jannik Sinner\n"
            "ð¥ Fighter 1 - Fighter 2"
        )
    return (
        "Ð¡Ð½Ð°ÑÐ°Ð»Ð° Ð²ÑÐ±ÐµÑÐ¸ Ð²Ð¸Ð´ ÑÐ¿Ð¾ÑÑÐ°:\n\n"
        "â½ Real Madrid - Barcelona\n"
        "ð Lakers - Celtics\n"
        "ð¾ Carlos Alcaraz - Jannik Sinner\n"
        "ð¥ ÐÐ¾ÐµÑ 1 - ÐÐ¾ÐµÑ 2"
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "â¹ï¸ FLUX AI analyzes football, NBA, tennis and UFC.\n\n"
            "Tennis and UFC are in Beta. The current UFC module is a "
            "demo model until verified live statistics are connected.\n\n"
            "Predictions are informational and do not guarantee results."
        )
    return (
        "â¹ï¸ FLUX AI Ð°Ð½Ð°Ð»Ð¸Ð·Ð¸ÑÑÐµÑ ÑÑÑÐ±Ð¾Ð», NBA, ÑÐµÐ½Ð½Ð¸Ñ Ð¸ UFC.\n\n"
        "Ð¢ÐµÐ½Ð½Ð¸Ñ Ð¸ UFC ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð² Beta. Ð¢ÐµÐºÑÑÐ¸Ð¹ UFC-Ð¼Ð¾Ð´ÑÐ»Ñ ÑÐ²Ð»ÑÐµÑÑÑ "
        "Ð´ÐµÐ¼Ð¾Ð½ÑÑÑÐ°ÑÐ¸Ð¾Ð½Ð½ÑÐ¼ Ð´Ð¾ Ð¿Ð¾Ð´ÐºÐ»ÑÑÐµÐ½Ð¸Ñ Ð¿ÑÐ¾Ð²ÐµÑÐµÐ½Ð½Ð¾Ð¹ ÑÐµÐ°Ð»ÑÐ½Ð¾Ð¹ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ¸.\n\n"
        "ÐÑÐ¾Ð³Ð½Ð¾Ð· Ð½Ðµ Ð³Ð°ÑÐ°Ð½ÑÐ¸ÑÑÐµÑ ÑÐµÐ·ÑÐ»ÑÑÐ°Ñ."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "â FLUX AI Sports is running.\n\n"
            "Version: PRO v5.1\n"
            "Sports: Football + NBA + Tennis Beta + UFC Beta\n"
            f"Channel: {CHANNEL_USERNAME}\nStatus: Online"
        )
    return (
        "â FLUX AI Sports ÑÐ°Ð±Ð¾ÑÐ°ÐµÑ.\n\n"
        "ÐÐµÑÑÐ¸Ñ: PRO v5.1\n"
        "Ð¡Ð¿Ð¾ÑÑ: Ð¤ÑÑÐ±Ð¾Ð» + NBA + Ð¢ÐµÐ½Ð½Ð¸Ñ Beta + UFC Beta\n"
        f"ÐÐ°Ð½Ð°Ð»: {CHANNEL_USERNAME}\nÐ¡ÑÐ°ÑÑÑ: Online"
    )


def profile_message(user_id, language="ru"):
    user = get_user(user_id)
    if not user:
        return "Profile not found." if language == "en" else "ÐÑÐ¾ÑÐ¸Ð»Ñ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½."

    pro_active = is_pro(user_id)
    usage = get_today_usage(user_id)
    sport = get_user_sport(user_id) or "football"

    if language == "en":
        return (
            "ð¤ MY PROFILE\n\n"
            f"ð ID: {user_id}\n"
            f"ð FLUX PRO: {'â Active' if pro_active else 'â Inactive'}\n"
            f"ð¯ Selected sport: {sport_title(sport, 'en')}\n"
            f"ð Analyses today: {'Unlimited' if pro_active else f'{usage}/{FREE_DAILY_LIMIT}'}"
        )
    return (
        "ð¤ ÐÐÐ ÐÐ ÐÐ¤ÐÐÐ¬\n\n"
        f"ð ID: {user_id}\n"
        f"ð FLUX PRO: {'â ÐÐºÑÐ¸Ð²ÐµÐ½' if pro_active else 'â ÐÐµ Ð°ÐºÑÐ¸Ð²ÐµÐ½'}\n"
        f"ð¯ ÐÑÐ±ÑÐ°Ð½Ð½ÑÐ¹ ÑÐ¿Ð¾ÑÑ: {sport_title(sport, 'ru')}\n"
        f"ð ÐÐ½Ð°Ð»Ð¸Ð·Ñ ÑÐµÐ³Ð¾Ð´Ð½Ñ: {'ÐÐµÐ·Ð»Ð¸Ð¼Ð¸Ñ' if pro_active else f'{usage}/{FREE_DAILY_LIMIT}'}"
    )


def pro_message(language="ru"):
    if language == "en":
        return (
            "ð FLUX AI PRO\n\n"
            "â Unlimited analysis\n"
            "â Football, NBA, Tennis and UFC\n"
            "â Extended statistics\nâ Daily Top 3\n\n"
            f"Price: â­{PRO_PRICE_STARS} / {PRO_DAYS} days"
        )
    return (
        "ð FLUX AI PRO\n\n"
        "â ÐÐµÐ·Ð»Ð¸Ð¼Ð¸ÑÐ½ÑÐ¹ Ð°Ð½Ð°Ð»Ð¸Ð·\n"
        "â Ð¤ÑÑÐ±Ð¾Ð», NBA, ÑÐµÐ½Ð½Ð¸Ñ Ð¸ UFC\n"
        "â Ð Ð°ÑÑÐ¸ÑÐµÐ½Ð½Ð°Ñ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ°\nâ Ð¢ÐÐ-3 Ð´Ð½Ñ\n\n"
        f"Ð¡ÑÐ¾Ð¸Ð¼Ð¾ÑÑÑ: â­{PRO_PRICE_STARS} / {PRO_DAYS} Ð´Ð½ÐµÐ¹"
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
                f"â ï¸ Could not analyze: {left} - {right}"
                if language == "en"
                else f"â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ: {left} - {right}"
            )
            results.append(message if len(matches) == 1 else f"#{index}\n{message}")
    return "\n\n".join(results)


def analysis_prompt(sport, language="ru"):
    prompts = {
        "football": {
            "en": "â½ Send a football match:\nReal Madrid - Barcelona",
            "ru": "â½ ÐÐ°Ð¿Ð¸ÑÐ¸ ÑÑÑÐ±Ð¾Ð»ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ:\nReal Madrid - Barcelona",
        },
        "nba": {
            "en": "ð Send an NBA game:\nLakers - Celtics",
            "ru": "ð ÐÐ°Ð¿Ð¸ÑÐ¸ Ð¼Ð°ÑÑ NBA:\nLakers - Celtics",
        },
        "tennis": {
            "en": "ð¾ Send a tennis match:\nCarlos Alcaraz - Jannik Sinner",
            "ru": "ð¾ ÐÑÐ¿ÑÐ°Ð²Ñ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐ¹ Ð¼Ð°ÑÑ:\nCarlos Alcaraz - Jannik Sinner",
        },
        "ufc": {
            "en": "ð¥ Send a UFC fight:\nFighter 1 - Fighter 2",
            "ru": "ð¥ ÐÑÐ¿ÑÐ°Ð²Ñ Ð±Ð¾Ð¹ UFC:\nÐÐ¾ÐµÑ 1 - ÐÐ¾ÐµÑ 2",
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
                f"ð Free analyses remaining: {remaining}"
                if language == "en"
                else f"ð ÐÑÑÐ°Ð»Ð¾ÑÑ Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½ÑÑ Ð°Ð½Ð°Ð»Ð¸Ð·Ð¾Ð²: {remaining}"
            )
            send_message(chat_id, message, main_menu(language))
            return

    send_message(
        chat_id,
        "â³ Analyzing..." if language == "en" else "â³ ÐÐ½Ð°Ð»Ð¸Ð·Ð¸ÑÑÑ...",
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
            "â ï¸ Analysis failed." if language == "en" else "â ï¸ ÐÐ½Ð°Ð»Ð¸Ð· Ð½Ðµ Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½.",
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
            "â ï¸ Payment verification failed."
            if language == "en"
            else "â ï¸ ÐÐ»Ð°ÑÑÐ¶ Ð½Ðµ Ð¿ÑÐ¾ÑÑÐ» Ð¿ÑÐ¾Ð²ÐµÑÐºÑ.",
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
        "ð FLUX AI PRO activated!"
        if language == "en"
        else "ð FLUX AI PRO Ð°ÐºÑÐ¸Ð²Ð¸ÑÐ¾Ð²Ð°Ð½!",
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
        answer_callback_query(callback_id, "Ð¯Ð·ÑÐº Ð¸Ð·Ð¼ÐµÐ½ÑÐ½.")
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
                "ð No matches found today."
                if language == "en"
                else "ð ÐÐ°ÑÑÐ¸ Ð½Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ñ.",
                main_menu(language),
            )
            return

        lines = ["ð TENNIS TODAY" if language == "en" else "ð Ð¢ÐÐÐÐÐ¡ Ð¡ÐÐÐÐÐÐ¯"]
        for index, match in enumerate(matches, 1):
            live = " ð´ LIVE" if match.get("live") else ""
            tournament = match.get("tournament") or ""
            tournament_line = f"\nð {tournament[:70]}" if tournament else ""
            lines.append(
                f"{index}. {match.get('time') or 'â'}{live} | "
                f"{match.get('player1') or 'â'} â {match.get('player2') or 'â'}"
                f"{tournament_line}\nð¾ {(match.get('surface') or 'hard').title()}"
            )

        instruction = (
            "\n\nTo analyze, send:\nPlayer 1 - Player 2 | surface"
            if language == "en"
            else "\n\nÐÐ»Ñ Ð°Ð½Ð°Ð»Ð¸Ð·Ð° Ð¾ÑÐ¿ÑÐ°Ð²Ñ:\nÐÐ³ÑÐ¾Ðº 1 - ÐÐ³ÑÐ¾Ðº 2 | Ð¿Ð¾ÐºÑÑÑÐ¸Ðµ"
        )
        send_message(chat_id, "\n\n".join(lines) + instruction, main_menu(language))
    except Exception as error:
        print("TENNIS_TODAY_ERROR:", repr(error), flush=True)
        send_message(
            chat_id,
            "â ï¸ Could not load tennis matches."
            if language == "en"
            else "â ï¸ ÐÐµ Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð¾ÑÑ Ð·Ð°Ð³ÑÑÐ·Ð¸ÑÑ ÑÐµÐ½Ð½Ð¸ÑÐ½ÑÐµ Ð¼Ð°ÑÑÐ¸.",
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
                "â¡ Welcome to Flux AI\nChoose your language.\n\n"
                "â¡ ÐÐ¾Ð±ÑÐ¾ Ð¿Ð¾Ð¶Ð°Ð»Ð¾Ð²Ð°ÑÑ Ð² Flux AI\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº.",
                language_keyboard(),
            )
            return "OK", 200

        if text in ["/language", "ð Language", "ð Ð¯Ð·ÑÐº"]:
            send_message(
                chat_id,
                "Choose your language.\n\nÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº.",
                language_keyboard(),
            )
            return "OK", 200

        sport_buttons = {
            "â½ Ð¤ÑÑÐ±Ð¾Ð»": "football",
            "â½ Football": "football",
            "ð NBA": "nba",
            "ð¾ Ð¢ÐµÐ½Ð½Ð¸Ñ": "tennis",
            "ð¾ Tennis": "tennis",
            "ð¥ UFC": "ufc",
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

        if text in ["ð¯ ÐÐ½Ð°Ð»Ð¸Ð· Ð¼Ð°ÑÑÐ°", "ð¯ Analyze Match"]:
            send_message(
                chat_id,
                analysis_prompt(get_user_sport(user_id) or "football", language),
                main_menu(language),
            )
            return "OK", 200

        commands = {
            "ð Ð¢ÐµÐ½Ð½Ð¸Ñ ÑÐµÐ³Ð¾Ð´Ð½Ñ": "/tennis_today",
            "ð Tennis Today": "/tennis_today",
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
                    "â Access denied." if language == "en" else "â ÐÐ¾ÑÑÑÐ¿ Ð·Ð°Ð¿ÑÐµÑÑÐ½.",
                    main_menu(language),
                )
            else:
                stats = get_admin_stats()
                send_message(chat_id, str(stats), main_menu(language))
        elif text == "/channel":
            send_message(
                chat_id,
                CHANNEL_URL,
                {"inline_keyboard": [[{"text": "ð FLUX AI", "url": CHANNEL_URL}]]},
            )
        elif text == "/worldcup":
            set_user_sport(user_id, "football")
            send_message(chat_id, analysis_prompt("football", language), main_menu(language))
        elif text == "/results":
            send_message(
                chat_id,
                "ð Results are being prepared."
                if language == "en"
                else "ð Ð¡ÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ° ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ¾Ð² Ð³Ð¾ÑÐ¾Ð²Ð¸ÑÑÑ.",
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
