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
    increase_today_usage,
    is_pro,
    save_payment,
    save_prediction,
    set_user_language,
)
from payments.stars import send_stars_invoice


BOT_TOKEN = os.environ["BOT_TOKEN"]

PUBLIC_URL = os.environ.get(
    "PUBLIC_URL",
    "https://flux-ai-8p34.onrender.com",
).rstrip("/")

ADMIN_TELEGRAM_ID = int(
    os.environ.get("ADMIN_TELEGRAM_ID", "0")
)

CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"

FREE_DAILY_LIMIT = 2
PRO_PRICE_STARS = 500
PRO_DAYS = 30

app = Flask(__name__)

USER_SPORT_MODE = {}


def telegram_api(method, payload):
    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    response = requests.post(
        url,
        json=payload,
        timeout=20,
    )

    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Telegram returned invalid JSON: "
            f"{response.text[:500]}"
        ) from error

    if not response.ok or not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error in {method}: {result}"
        )

    return result


def send_message(
    chat_id,
    text,
    reply_markup=None,
):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        return telegram_api(
            "sendMessage",
            payload,
        )

    except Exception as error:
        print(
            "SEND_MESSAGE_ERROR:",
            repr(error),
            flush=True,
        )
        return None


def answer_callback_query(
    callback_query_id,
    text=None,
):
    payload = {
        "callback_query_id": callback_query_id,
    }

    if text:
        payload["text"] = text

    try:
        return telegram_api(
            "answerCallbackQuery",
            payload,
        )

    except Exception as error:
        print(
            "ANSWER_CALLBACK_ERROR:",
            repr(error),
            flush=True,
        )
        return None


def answer_pre_checkout_query(
    query_id,
    approved,
    error_message=None,
):
    payload = {
        "pre_checkout_query_id": query_id,
        "ok": approved,
    }

    if not approved and error_message:
        payload["error_message"] = error_message

    return telegram_api(
        "answerPreCheckoutQuery",
        payload,
    )


def language_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🇺🇸 English",
                    "callback_data": "lang_en",
                },
                {
                    "text": "🇷🇺 Русский",
                    "callback_data": "lang_ru",
                },
            ]
        ]
    }


def main_menu(language="ru"):
    if language == "en":
        keyboard = [
            [
                "⚽ Football",
                "🏀 NBA",
            ],
            [
                "⚽ Analyze Match",
            ],
            [
                "🏆 Top 3 Today",
                "🌍 World Cup 2026",
            ],
            ["📈 Results"],
            [
                "🏆 Channel",
                "💎 FLUX PRO",
            ],
            ["👤 My Profile"],
            [
                "ℹ️ About",
                "📊 Status",
            ],
            ["🌐 Language"],
        ]

    else:
        keyboard = [
            [
                "⚽ Футбол",
                "🏀 NBA",
            ],
            [
                "⚽ Анализ матча",
            ],
            [
                "🏆 ТОП-3 дня",
                "🌍 ЧМ-2026",
            ],
            ["📈 Результаты"],
            [
                "🏆 Канал",
                "💎 FLUX PRO",
            ],
            ["👤 Мой профиль"],
            [
                "ℹ️ О проекте",
                "📊 Статус",
            ],
            ["🌐 Язык"],
        ]

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        str(text)
        .replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .strip()
    )


def detect_match(line):
    line = normalize_text(line)

    separators = [
        " - ",
        " vs ",
        " VS ",
        " Vs ",
        " v ",
        " V ",
        "-",
    ]

    for separator in separators:
        if separator not in line:
            continue

        parts = line.split(separator, 1)

        if len(parts) != 2:
            continue

        team1 = parts[0].strip()
        team2 = parts[1].strip()

        if team1 and team2:
            return team1, team2

    return None, None


def detect_matches(text):
    matches = []

    for line in str(text).splitlines():
        team1, team2 = detect_match(
            line.strip()
        )

        if team1 and team2:
            matches.append(
                (team1, team2)
            )

    return matches


def start_message(language="ru"):
    if language == "en":
        return (
            "👋 Welcome! I am FLUX AI Sports PRO v3.0\n\n"
            "⚽ Match analysis\n"
            "🏆 Top 3 of the day\n"
            "🌍 World Cup analysis\n"
            "📈 Results\n"
            "💎 FLUX PRO\n\n"
            "FREE: 2 analyses per day\n"
            "PRO: unlimited\n\n"
            "Send a match:\n"
            "Real Madrid - Barcelona"
        )

    return (
        "👋 Привет! Я FLUX AI Sports PRO v3.0\n\n"
        "⚽ Анализ матчей\n"
        "🏆 ТОП-3 дня\n"
        "🌍 Анализ матчей ЧМ\n"
        "📈 Результаты\n"
        "💎 FLUX PRO\n\n"
        "FREE: 2 анализа в день\n"
        "PRO: безлимит\n\n"
        "Напиши матч:\n"
        "Real Madrid - Barcelona"
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "⚽ Send a match in this format:\n\n"
            "Real Madrid - Barcelona\n"
            "Brazil - Norway\n"
            "Portugal - Spain\n\n"
            "You can send several matches, "
            "one per line."
        )

    return (
        "⚽ Напиши матч в формате:\n\n"
        "Real Madrid - Barcelona\n"
        "Brazil - Norway\n"
        "Portugal - Spain\n\n"
        "Можно отправить несколько "
        "матчей списком."
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "ℹ️ FLUX AI is an AI-powered "
            "football analysis bot.\n\n"
            "It evaluates team form, "
            "probabilities, totals, "
            "double chance and model insights.\n\n"
            "Predictions are informational "
            "and do not guarantee results."
        )

    return (
        "ℹ️ FLUX AI — AI-бот "
        "для анализа футбольных матчей.\n\n"
        "Бот оценивает форму команд, "
        "вероятности, тоталы, "
        "двойной шанс и выводы модели.\n\n"
        "Прогноз не является "
        "гарантией результата."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "✅ FLUX AI Sports is running.\n\n"
            "Version: PRO v3.0\n"
            "Mode: Public Beta\n"
            f"Channel: {CHANNEL_USERNAME}\n"
            "Status: Online"
        )

    return (
        "✅ FLUX AI Sports работает.\n\n"
        "Версия: PRO v3.0\n"
        "Режим: Public Beta\n"
        f"Канал: {CHANNEL_USERNAME}\n"
        "Статус: Online"
    )


def admin_panel_message(language="ru"):
    stats = get_admin_stats()

    if language == "en":
        return (
            "🔐 FLUX AI ADMIN\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total users: "
            f"{stats['total_users']}\n"
            f"💎 Active PRO: "
            f"{stats['active_pro']}\n"
            f"🧾 Total payments: "
            f"{stats['total_payments']}\n\n"
            "📊 Statistics update automatically."
        )

    return (
        "🔐 FLUX AI ADMIN\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего пользователей: "
        f"{stats['total_users']}\n"
        f"💎 Активных PRO: "
        f"{stats['active_pro']}\n"
        f"🧾 Всего оплат: "
        f"{stats['total_payments']}\n\n"
        "📊 Статистика обновляется автоматически."
    )


def profile_message(
    user_id,
    language="ru",
):
    user = get_user(user_id)

    if not user:
        if language == "en":
            return (
                "👤 Profile not found. "
                "Press /start."
            )

        return (
            "👤 Профиль не найден. "
            "Нажми /start."
        )

    pro_active = is_pro(user_id)

    if language == "en":
        pro_status = (
            "✅ Active"
            if pro_active
            else "❌ Inactive"
        )
    else:
        pro_status = (
            "✅ Активен"
            if pro_active
            else "❌ Не активен"
        )

    usage = get_today_usage(user_id)

    if pro_active:
        limit_text = (
            "Unlimited"
            if language == "en"
            else "Безлимит"
        )
    else:
        if language == "en":
            limit_text = (
                f"{usage}/"
                f"{FREE_DAILY_LIMIT} today"
            )
        else:
            limit_text = (
                f"{usage}/"
                f"{FREE_DAILY_LIMIT} сегодня"
            )

    if language == "en":
        return (
            "👤 MY PROFILE\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: {user_id}\n\n"
            f"💎 FLUX PRO: {pro_status}\n\n"
            "📊 Statistics:\n"
            f"• Analyses today: {limit_text}\n"
            "• Winning predictions: coming soon\n\n"
            "🚀 FLUX AI v3.0"
        )

    return (
        "👤 МОЙ ПРОФИЛЬ\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user_id}\n\n"
        f"💎 FLUX PRO: {pro_status}\n\n"
        "📊 Статистика:\n"
        f"• Анализы сегодня: {limit_text}\n"
        "• Победных прогнозов: скоро\n\n"
        "🚀 FLUX AI v3.0"
    )

def channel_message(language="ru"):
    if language == "en":
        return (
            "🏆 FLUX AI DAILY\n\n"
            "Official FLUX AI channel.\n\n"
            "⚽ Daily Top 3 predictions\n"
            "📊 AI match analysis\n"
            "💎 FLUX PRO news\n\n"
            f"📢 Subscribe: {CHANNEL_URL}"
        )

    return (
        "🏆 FLUX AI DAILY\n\n"
        "Официальный канал FLUX AI.\n\n"
        "⚽ ТОП-3 прогнозов дня\n"
        "📊 AI-анализ матчей\n"
        "💎 Новости FLUX PRO\n\n"
        f"📢 Подписаться: {CHANNEL_URL}"
    )


def results_message(language="ru"):
    if language == "en":
        return (
            "📈 FLUX AI Results\n\n"
            "Public result tracking "
            "is being prepared.\n\n"
            "Predictions are informational "
            "and do not guarantee results."
        )

    return (
        "📈 FLUX AI Results\n\n"
        "Публичная статистика результатов "
        "готовится.\n\n"
        "Прогноз не является "
        "гарантией результата."
    )


def worldcup_message(language="ru"):
    if language == "en":
        return (
            "🌍 FLUX AI | World Cup\n\n"
            "Send any match "
            "to the analyzer:\n\n"
            "Team 1 - Team 2\n\n"
            "Predictions are informational "
            "and do not guarantee results."
        )

    return (
        "🌍 FLUX AI | Чемпионат мира\n\n"
        "Отправь любой матч "
        "в анализатор:\n\n"
        "Команда 1 - Команда 2\n\n"
        "Прогноз не является "
        "гарантией результата."
    )


def today_top_3_message(language="ru"):
    if language == "en":
        return (
            "🏆 FLUX AI DAILY\n\n"
            "The current Top 3 "
            "is published in our channel.\n\n"
            f"📢 {CHANNEL_URL}"
        )

    return (
        "🏆 FLUX AI DAILY\n\n"
        "Актуальный ТОП-3 "
        "публикуется в нашем канале.\n\n"
        f"📢 {CHANNEL_URL}"
    )


def pro_message(language="ru"):
    if language == "en":
        return (
            "💎 FLUX AI PRO\n\n"
            "✅ Unlimited AI analysis\n"
            "✅ Extended statistics\n"
            "✅ Daily Top 3\n"
            "✅ New PRO features\n\n"
            f"Price: ⭐{PRO_PRICE_STARS} / "
            f"{PRO_DAYS} days\n\n"
            "👇 Use the payment invoice below."
        )

    return (
        "💎 FLUX AI PRO\n\n"
        "✅ Безлимитный AI-анализ\n"
        "✅ Расширенная статистика\n"
        "✅ ТОП-3 дня\n"
        "✅ Новые PRO-функции\n\n"
        f"Стоимость: ⭐{PRO_PRICE_STARS} / "
        f"{PRO_DAYS} дней\n\n"
        "👇 Используйте счёт оплаты ниже."
    )


def payment_success_message(language="ru"):
    if language == "en":
        return (
            "🎉 FLUX AI PRO activated!\n\n"
            "💎 Status: PRO\n"
            f"📅 Period: {PRO_DAYS} days\n"
            "✅ Unlimited analysis is available."
        )

    return (
        "🎉 FLUX AI PRO активирован!\n\n"
        "💎 Статус: PRO\n"
        f"📅 Срок: {PRO_DAYS} дней\n"
        "✅ Безлимитный анализ доступен."
    )


def analyze_match_text(
    text,
    language="ru",
):
    from engine.analyzer import (
        analyze_and_format,
    )

    matches = detect_matches(text)

    if not matches:
        return help_message(language)

    if len(matches) == 1:
        team1, team2 = matches[0]

        return analyze_and_format(
            team1,
            team2,
            language,
        )

    results = []

    for index, (
        team1,
        team2,
    ) in enumerate(
        matches[:5],
        start=1,
    ):
        try:
            result = analyze_and_format(
                team1,
                team2,
                language,
            )

            results.append(
                f"#{index}\n{result}"
            )

        except Exception as error:
            print(
                "MULTI_ANALYSIS_ERROR:",
                repr(error),
                flush=True,
            )

            if language == "en":
                results.append(
                    f"#{index}\n"
                    f"⚠️ Could not analyze: "
                    f"{team1} - {team2}"
                )
            else:
                results.append(
                    f"#{index}\n"
                    f"⚠️ Не получилось: "
                    f"{team1} - {team2}"
                )

    return "\n\n".join(results)

def analyze_nba_text(
    text,
    language="ru",
):
    from engine.nba_analyzer import (
        analyze_and_format_nba,
    )

    matches = detect_matches(text)

    if not matches:
        if language == "en":
            return (
                "🏀 Send an NBA game:\n\n"
                "Lakers - Celtics\n"
                "Warriors - Knicks"
            )

        return (
            "🏀 Напиши матч NBA:\n\n"
            "Lakers - Celtics\n"
            "Warriors - Knicks"
        )

    if len(matches) == 1:
        team1, team2 = matches[0]

        return analyze_and_format_nba(
            team1,
            team2,
            language,
        )

    results = []

    for index, (
        team1,
        team2,
    ) in enumerate(
        matches[:5],
        start=1,
    ):
        try:
            result = analyze_and_format_nba(
                team1,
                team2,
                language,
            )

            results.append(
                f"#{index}\n{result}"
            )

        except Exception as error:
            print(
                "MULTI_NBA_ANALYSIS_ERROR:",
                repr(error),
                flush=True,
            )

            if language == "en":
                results.append(
                    f"#{index}\n"
                    f"⚠️ Could not analyze: "
                    f"{team1} - {team2}"
                )
            else:
                results.append(
                    f"#{index}\n"
                    f"⚠️ Не получилось: "
                    f"{team1} - {team2}"
                )

    return "\n\n".join(results)


def handle_analysis(
    chat_id,
    user_id,
    text,
    language="ru",
):
    matches = detect_matches(text)

    if not matches:
        send_message(
            chat_id,
            help_message(language),
            reply_markup=main_menu(language),
        )
        return

    if not is_pro(user_id):
        used = get_today_usage(user_id)

        remaining = (
            FREE_DAILY_LIMIT - used
        )

        if remaining <= 0:
            send_message(
                chat_id,
                free_limit_message(language),
                reply_markup=main_menu(language),
            )
            return

        if len(matches) > remaining:
            if language == "en":
                message_text = (
                    "🔒 Free analyses remaining "
                    f"today: {remaining}\n\n"
                    "Send fewer matches "
                    "or activate FLUX PRO."
                )
            else:
                message_text = (
                    "🔒 У вас осталось бесплатных "
                    f"анализов сегодня: {remaining}\n\n"
                    "Отправьте меньше матчей "
                    "или оформите FLUX PRO."
                )

            send_message(
                chat_id,
                message_text,
                reply_markup=main_menu(language),
            )
            return

    if len(matches) > 1:
        analyzing_text = (
            f"⏳ Analyzing "
            f"{len(matches)} matches..."
            if language == "en"
            else
            f"⏳ Анализирую "
            f"{len(matches)} матчей..."
        )
    else:
        analyzing_text = (
            "⏳ Analyzing the match..."
            if language == "en"
            else "⏳ Анализирую матч..."
        )

    send_message(
        chat_id,
        analyzing_text,
        reply_markup=main_menu(language),
    )

    try:
        sport_mode = USER_SPORT_MODE.get(
            user_id,
            "football",
        )

        if sport_mode == "nba":
            answer = analyze_nba_text(
                text,
                language,
            )
        
        else:
            answer = analyze_match_text(
                text,
                language,
            )

        send_message(
            chat_id,
            answer,
            reply_markup=main_menu(language),
        )

        sport_mode = USER_SPORT_MODE.get(
            user_id,
            "football",
        )

        sport_prefix = (
            "NBA"
            if sport_mode == "nba"
            else "FOOTBALL"
        )

        for team1, team2 in matches:
            save_prediction(
                user_id,
                f"[{sport_prefix}] "
                f"{team1} - {team2}",
                answer,
            )

            if not is_pro(user_id):
                increase_today_usage(
                    user_id
                )

    except Exception as error:
        print(
            "MATCH_ANALYSIS_ERROR:",
            repr(error),
            flush=True,
        )

        if language == "en":
            error_text = (
                "⚠️ Could not complete "
                "the analysis.\n\n"
                "Try another match "
                "or check the format:\n"
                "Real Madrid - Barcelona"
            )
        else:
            error_text = (
                "⚠️ Не получилось "
                "сделать анализ.\n\n"
                "Попробуй другой матч "
                "или проверь формат:\n"
                "Real Madrid - Barcelona"
            )

        send_message(
            chat_id,
            error_text,
            reply_markup=main_menu(language),
        )


def parse_invoice_user_id(
    invoice_payload,
):
    prefix = "flux_pro_30_days:"

    invoice_payload = str(
        invoice_payload
    )

    if not invoice_payload.startswith(
        prefix
    ):
        return None

    try:
        return int(
            invoice_payload[len(prefix):]
        )

    except (TypeError, ValueError):
        return None


def process_pre_checkout_query(
    pre_checkout_query,
):
    query_id = pre_checkout_query.get(
        "id"
    )

    payer_id = (
        pre_checkout_query
        .get("from", {})
        .get("id")
    )

    language = get_user_language(
        payer_id
    )

    invoice_payload = (
        pre_checkout_query.get(
            "invoice_payload",
            "",
        )
    )

    currency = pre_checkout_query.get(
        "currency",
        "",
    )

    total_amount = pre_checkout_query.get(
        "total_amount",
        0,
    )

    payload_user_id = (
        parse_invoice_user_id(
            invoice_payload
        )
    )

    is_valid = (
        query_id
        and payer_id
        and payload_user_id == payer_id
        and currency == "XTR"
        and int(total_amount)
        == PRO_PRICE_STARS
    )

    error_message = None

    if not is_valid:
        error_message = (
            "Payment verification failed. "
            "Please create a new invoice."
            if language == "en"
            else
            "Не удалось проверить платёж. "
            "Создайте новый счёт."
        )

    answer_pre_checkout_query(
        query_id=query_id,
        approved=is_valid,
        error_message=error_message,
    )


def process_successful_payment(message):
    payment = message.get(
        "successful_payment",
        {},
    )

    user = message.get("from", {})
    chat = message.get("chat", {})

    user_id = user.get("id")
    chat_id = chat.get("id")

    language = get_user_language(
        user_id
    )

    invoice_payload = payment.get(
        "invoice_payload",
        "",
    )

    currency = payment.get(
        "currency",
        "",
    )

    total_amount = payment.get(
        "total_amount",
        0,
    )

    payload_user_id = (
        parse_invoice_user_id(
            invoice_payload
        )
    )

    payment_is_valid = (
        user_id
        and chat_id
        and payload_user_id == user_id
        and currency == "XTR"
        and int(total_amount)
        == PRO_PRICE_STARS
    )

    if not payment_is_valid:
        error_text = (
            "⚠️ Payment data "
            "failed verification."
            if language == "en"
            else
            "⚠️ Данные платежа "
            "не прошли проверку."
        )

        send_message(
            chat_id,
            error_text,
            reply_markup=main_menu(language),
        )
        return

    add_user(user)

    activate_pro(
        user_id,
        days=PRO_DAYS,
    )

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


def process_callback_query(
    callback_query,
):
    callback_id = callback_query.get(
        "id"
    )

    user = callback_query.get(
        "from",
        {},
    )

    user_id = user.get("id")

    chat_id = (
        callback_query
        .get("message", {})
        .get("chat", {})
        .get("id")
    )

    data = callback_query.get(
        "data",
        "",
    )

    if not user_id or not chat_id:
        if callback_id:
            answer_callback_query(
                callback_id
            )
        return

    add_user(user)

    if data == "lang_en":
        set_user_language(
            user_id,
            "en",
        )

        answer_callback_query(
            callback_id,
            "Language changed to English.",
        )

        send_message(
            chat_id,
            start_message("en"),
            reply_markup=main_menu("en"),
        )
        return

    if data == "lang_ru":
        set_user_language(
            user_id,
            "ru",
        )

        answer_callback_query(
            callback_id,
            "Язык изменён на русский.",
        )

        send_message(
            chat_id,
            start_message("ru"),
            reply_markup=main_menu("ru"),
        )
        return

    answer_callback_query(
        callback_id
    )

@app.route("/")
def home():
    return (
        "FLUX AI Sports PRO v3.0 "
        "is running!"
    )


@app.route("/health")
def health():
    return "OK"


@app.route(
    f"/telegram/{BOT_TOKEN}",
    methods=["POST"],
)
def telegram_webhook():
    try:
        data = request.get_json(
            force=True,
            silent=True,
        )

        if not data:
            return "OK", 200

        callback_query = data.get(
            "callback_query"
        )

        if callback_query:
            process_callback_query(
                callback_query
            )
            return "OK", 200

        pre_checkout_query = data.get(
            "pre_checkout_query"
        )

        if pre_checkout_query:
            process_pre_checkout_query(
                pre_checkout_query
            )
            return "OK", 200

        message = data.get("message")

        if not message:
            return "OK", 200

        if message.get(
            "successful_payment"
        ):
            process_successful_payment(
                message
            )
            return "OK", 200

        chat = message.get(
            "chat",
            {},
        )

        user = message.get(
            "from",
            {},
        )

        chat_id = chat.get("id")
        user_id = user.get("id")

        text = (
            message.get("text")
            or ""
        ).strip()

        if not chat_id:
            return "OK", 200

        if user_id:
            add_user(user)

        language = get_user_language(
            user_id
        )

        if text == "/start":
            send_message(
                chat_id,
                (
                    "⚡ Welcome to Flux AI\n"
                    "Choose your language.\n\n"
                    "⚡ Добро пожаловать "
                    "в Flux AI\n"
                    "Выберите язык."
                ),
                reply_markup=(
                    language_keyboard()
                ),
            )
            return "OK", 200

        if text in [
            "/language",
            "🌐 Language",
            "🌐 Язык",
        ]:
            send_message(
                chat_id,
                (
                    "Choose your language.\n\n"
                    "Выберите язык."
                ),
                reply_markup=(
                    language_keyboard()
                ),
            )
            return "OK", 200

        if not text:
            send_message(
                chat_id,
                help_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text in [
            "⚽ Футбол",
            "⚽ Football",
        ]:
            USER_SPORT_MODE[user_id] = "football"

            message_text = (
                "⚽ Football mode selected.\n\n"
                "Send a match:\n"
                "Real Madrid - Barcelona"
                if language == "en"
                else
                "⚽ Выбран режим футбола.\n\n"
                "Напиши матч:\n"
                "Real Madrid - Barcelona"
            )

            send_message(
                chat_id,
                message_text,
                reply_markup=main_menu(language),
            )
            return "OK", 200

        if text == "🏀 NBA":
            USER_SPORT_MODE[user_id] = "nba"

            message_text = (
                "🏀 NBA mode selected.\n\n"
                "Send a game:\n"
                "Lakers - Celtics\n\n"
                "The first team is treated as the home team."
                if language == "en"
                else
                "🏀 Выбран режим NBA.\n\n"
                "Напиши матч:\n"
                "Lakers - Celtics\n\n"
                "Первая команда считается хозяином площадки."
            )

            send_message(
                chat_id,
                message_text,
                reply_markup=main_menu(language),
            )
            return "OK", 200

        button_commands = {
            "🏆 ТОП-3 дня": "/today",
            "🏆 Top 3 Today": "/today",
            "🌍 ЧМ-2026": "/worldcup",
            "🌍 World Cup 2026": "/worldcup",
            "📈 Результаты": "/results",
            "📈 Results": "/results",
            "🏆 Канал": "/channel",
            "🏆 Channel": "/channel",
            "💎 FLUX PRO": "/pro",
            "👤 Мой профиль": "/profile",
            "👤 My Profile": "/profile",
            "ℹ️ О проекте": "/about",
            "ℹ️ About": "/about",
            "📊 Статус": "/status",
            "📊 Status": "/status",
        }

        text = button_commands.get(
            text,
            text,
        )

        if text in [
            "/help",
            "/analyze",
        ]:
            send_message(
                chat_id,
                help_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/about":
            send_message(
                chat_id,
                about_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/status":
            send_message(
                chat_id,
                status_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/profile":
            send_message(
                chat_id,
                profile_message(
                    user_id,
                    language,
                ),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/admin":
            if (
                user_id
                != ADMIN_TELEGRAM_ID
            ):
                if language == "en":
                    denied = (
                        "⛔ Access denied."
                    )
                else:
                    denied = (
                        "⛔ Доступ запрещён."
                    )

                send_message(
                    chat_id,
                    denied,
                    reply_markup=(
                        main_menu(language)
                    ),
                )
                return "OK", 200

            send_message(
                chat_id,
                admin_panel_message(
                    language
                ),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/channel":
            if language == "en":
                button_text = (
                    "🏆 Open channel"
                )
            else:
                button_text = (
                    "🏆 Открыть канал"
                )

            send_message(
                chat_id,
                channel_message(language),
                reply_markup={
                    "inline_keyboard": [
                        [
                            {
                                "text": button_text,
                                "url": CHANNEL_URL,
                            }
                        ]
                    ]
                },
            )
            return "OK", 200

        if text == "/worldcup":
            send_message(
                chat_id,
                worldcup_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/results":
            send_message(
                chat_id,
                results_message(language),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/today":
            send_message(
                chat_id,
                today_top_3_message(
                    language
                ),
                reply_markup=(
                    main_menu(language)
                ),
            )
            return "OK", 200

        if text == "/pro":
            try:
                send_message(
                    chat_id,
                    pro_message(language),
                    reply_markup=(
                        main_menu(language)
                    ),
                )

                send_stars_invoice(
                    bot_token=BOT_TOKEN,
                    chat_id=chat_id,
                    user_id=user_id,
                    stars_price=(
                        PRO_PRICE_STARS
                    ),
                    language=language,
                )

            except Exception as error:
                print(
                    "PRO_PAYMENT_ERROR:",
                    repr(error),
                    flush=True,
                )

                if language == "en":
                    error_text = (
                        "⚠️ Could not open "
                        "Telegram Stars payment."
                    )
                else:
                    error_text = (
                        "⚠️ Не получилось открыть "
                        "оплату Telegram Stars."
                    )

                send_message(
                    chat_id,
                    error_text,
                    reply_markup=(
                        main_menu(language)
                    ),
                )

            return "OK", 200

        handle_analysis(
            chat_id,
            user_id,
            text,
            language,
        )

        return "OK", 200

    except Exception as error:
        print(
            "TELEGRAM_WEBHOOK_ERROR:",
            repr(error),
            flush=True,
        )

        return "OK", 200


def set_webhook():
    webhook_url = (
        f"{PUBLIC_URL}/telegram/"
        f"{BOT_TOKEN}"
    )

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

        print(
            "WEBHOOK_SET:",
            result,
            flush=True,
        )

    except Exception as error:
        print(
            "WEBHOOK_SET_ERROR:",
            repr(error),
            flush=True,
        )


if __name__ == "__main__":
    Thread(
        target=set_webhook,
        daemon=True,
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                "10000",
            )
        ),
    )
