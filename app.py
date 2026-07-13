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
    increase_today_usage,
    is_pro,
    save_payment,
    save_prediction,
)
from payments.stars import send_stars_invoice


BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get(
    "PUBLIC_URL",
    "https://flux-ai-8p34.onrender.com",
)
ADMIN_TELEGRAM_ID = int(
    os.environ.get("ADMIN_TELEGRAM_ID", "0")
)

CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"

FREE_DAILY_LIMIT = 2
PRO_PRICE_STARS = 500
PRO_DAYS = 30

app = Flask(__name__)


def telegram_api(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    response = requests.post(
        url,
        json=payload,
        timeout=20,
    )

    result = response.json()

    if not response.ok or not result.get("ok"):
        raise RuntimeError(
            f"Telegram API error in {method}: {result}"
        )

    return result


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        return telegram_api("sendMessage", payload)

    except Exception as error:
        print(
            "SEND_MESSAGE_ERROR:",
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


def main_menu():
    return {
        "keyboard": [
            ["⚽ Анализ матча"],
            ["🏆 ТОП-3 дня", "🌍 ЧМ-2026"],
            ["📈 Результаты"],
            ["🏆 Канал", "💎 FLUX PRO"],
            ["👤 Мой профиль"],
            ["ℹ️ О проекте", "📊 Статус"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def normalize_text(text):
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .strip()
    )


def detect_match(line):
    line = normalize_text(line)

    separators = [
        " - ",
        "-",
        " vs ",
        " VS ",
        " Vs ",
        " v ",
        " V ",
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

    for line in text.splitlines():
        team1, team2 = detect_match(line.strip())

        if team1 and team2:
            matches.append((team1, team2))

    return matches


def start_message():
    return (
        "👋 Привет! Я FLUX AI Sports PRO v3.0\n\n"
        "⚽ Анализ матчей\n"
        "🏆 ТОП-3 дня\n"
        "🌍 ЧМ-2026\n"
        "📈 Результаты\n"
        "💎 FLUX PRO\n\n"
        "FREE: 2 анализа в день\n"
        "PRO: безлимит\n\n"
        "Напиши матч:\n"
        "Real Madrid - Barcelona"
    )


def help_message():
    return (
        "⚽ Напиши матч в формате:\n\n"
        "Real Madrid - Barcelona\n"
        "Brazil - Norway\n"
        "Portugal - Spain\n\n"
        "Можно отправить несколько матчей списком."
    )


def about_message():
    return (
        "ℹ️ FLUX AI — AI-бот для анализа футбольных матчей.\n\n"
        "Бот оценивает форму команд, вероятности, тоталы, "
        "двойной шанс и лучший прогноз.\n\n"
        "Прогноз не является гарантией результата."
    )


def status_message():
    return (
        "✅ FLUX AI Sports работает.\n\n"
        "Версия: PRO v3.0\n"
        "Режим: Public Beta\n"
        f"Канал: {CHANNEL_USERNAME}\n"
        "Статус: Online"
    )


def admin_panel_message():
    stats = get_admin_stats()

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


def profile_message(user_id):
    user = get_user(user_id)

    if not user:
        return "👤 Профиль не найден. Нажми /start."

    pro_active = is_pro(user_id)
    pro_status = (
        "✅ Активен"
        if pro_active
        else "❌ Не активен"
    )

    usage = get_today_usage(user_id)

    if pro_active:
        limit_text = "Безлимит"
    else:
        limit_text = (
            f"{usage}/{FREE_DAILY_LIMIT} сегодня"
        )

    return (
        "👤 МОЙ ПРОФИЛЬ\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user_id}\n\n"
        f"💎 FLUX PRO: {pro_status}\n\n"
        "📊 Статистика:\n"
        f"• Анализы сегодня: {limit_text}\n"
        "• Победных прогнозов: скоро\n\n"
        "🚀 FLUX AI v3.0\n\n"
        "Спасибо, что пользуетесь FLUX AI ❤️"
    )


def channel_message():
    return (
        "🏆 FLUX AI DAILY\n\n"
        "Официальный канал FLUX AI.\n\n"
        "Там публикуются:\n"
        "⚽ ТОП-3 прогнозов дня\n"
        "🌍 Прогнозы ЧМ-2026\n"
        "📊 AI-анализ\n"
        "💎 Новости FLUX PRO\n\n"
        f"📢 Подписаться: {CHANNEL_URL}"
    )


def results_message():
    return (
        "📈 FLUX AI Results\n\n"
        "Статистика тестовой версии:\n\n"
        "✅ Всего прогнозов: 24\n"
        "🎯 Успешных: 17\n"
        "❌ Не зашло: 7\n\n"
        "📊 Точность: 70.8%\n\n"
        "Лучший рынок:\n"
        "⚽ ТБ 2.5\n\n"
        "Скоро здесь будет реальная статистика "
        "всех прогнозов FLUX AI."
    )


def worldcup_message():
    return (
        "🌍 FLUX AI | ЧМ-2026 🏆\n\n"
        "Ближайшие прогнозы:\n\n"
        "🇧🇷 Brazil — Norway\n"
        "🔥 ТБ 2.5 — 74%\n"
        "🎯 Проход Brazil — 72%\n"
        "⚠️ Риск: Средний\n\n"
        "🏴 England — Mexico\n"
        "🔥 ТМ 3.5 — 78%\n"
        "🎯 1X / осторожный матч\n"
        "⚠️ Риск: Средний\n\n"
        "🇵🇹 Portugal — Spain\n"
        "🔥 Обе забьют — Да — 69%\n"
        "🎯 ТБ 1.5 — 82%\n\n"
        f"📢 Канал: {CHANNEL_URL}\n\n"
        "Прогноз не является гарантией результата."
    )


def today_top_3_message():
    return (
        "🏆 FLUX AI DAILY\n\n"
        "ТОП-3 прогнозов на сегодня\n\n"
        "🥇 Manchester City — Real Madrid\n"
        "🔥 Прогноз: ТБ 2.5 — 82%\n"
        "🎯 Уверенность: 8.2/10\n"
        "⚠️ Риск: Средний\n\n"
        "🥈 Real Madrid — Paris Saint-Germain\n"
        "🔥 Прогноз: ТБ 2.5 — 82%\n"
        "🎯 Уверенность: 7.8/10\n"
        "⚠️ Риск: Средний\n\n"
        "🥉 Barcelona — Bayern Munich\n"
        "🔥 Прогноз: ТБ 2.5 — 77%\n"
        "🎯 Уверенность: 7.5/10\n"
        "⚠️ Риск: Средний\n\n"
        "Важно: прогноз не является "
        "гарантией результата."
    )


def pro_message():
    return (
        "💎 FLUX AI PRO\n\n"
        "Что входит:\n\n"
        "✅ Безлимитный AI-анализ матчей\n"
        "✅ Расширенная статистика\n"
        "✅ TOP-3 прогнозов дня\n"
        "✅ Прогнозы ЧМ-2026\n"
        "✅ Доступ к новым PRO-функциям\n\n"
        f"Стоимость: ⭐{PRO_PRICE_STARS} / "
        f"{PRO_DAYS} дней\n\n"
        "👇 Нажми кнопку оплаты ниже:"
    )


def payment_success_message():
    return (
        "🎉 FLUX AI PRO активирован!\n\n"
        "💎 Статус: PRO\n"
        f"📅 Срок: {PRO_DAYS} дней\n"
        "✅ Безлимитный анализ доступен.\n\n"
        "Спасибо за поддержку FLUX AI! 🚀"
    )


def analyze_match_text(text):
    from engine.analyzer import analyze_and_format

    matches = detect_matches(text)

    if not matches:
        return help_message()

    if len(matches) == 1:
        team1, team2 = matches[0]
        return analyze_and_format(team1, team2)

    results = []

    for index, (team1, team2) in enumerate(
        matches[:5],
        start=1,
    ):
        try:
            result = analyze_and_format(
                team1,
                team2,
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

            results.append(
                f"#{index}\n"
                f"⚠️ Не получилось: "
                f"{team1} - {team2}"
            )

    return "\n\n".join(results)


def handle_analysis(chat_id, user_id, text):
    matches = detect_matches(text)

    print(
        "MATCHES:",
        matches,
        flush=True,
    )

    if not matches:
        send_message(
            chat_id,
            help_message(),
            reply_markup=main_menu(),
        )
        return

    if not is_pro(user_id):
        used = get_today_usage(user_id)
        remaining = FREE_DAILY_LIMIT - used

        if remaining <= 0:
            send_message(
                chat_id,
                free_limit_message(),
                reply_markup=main_menu(),
            )
            return

        if len(matches) > remaining:
            send_message(
                chat_id,
                "🔒 У вас осталось бесплатных "
                f"анализов сегодня: {remaining}\n\n"
                "Отправьте меньше матчей или "
                "оформите FLUX PRO.",
                reply_markup=main_menu(),
            )
            return

    if len(matches) > 1:
        send_message(
            chat_id,
            f"⏳ Анализирую "
            f"{len(matches)} матчей...",
            reply_markup=main_menu(),
        )
    else:
        send_message(
            chat_id,
            "⏳ Анализирую матч...",
            reply_markup=main_menu(),
        )

    try:
        answer = analyze_match_text(text)

        send_message(
            chat_id,
            answer,
            reply_markup=main_menu(),
        )

        for team1, team2 in matches:
            save_prediction(
                user_id,
                f"{team1} - {team2}",
                answer,
            )

            if not is_pro(user_id):
                increase_today_usage(user_id)

    except Exception as error:
        print(
            "MATCH_ANALYSIS_ERROR:",
            repr(error),
            flush=True,
        )

        send_message(
            chat_id,
            "⚠️ Не получилось сделать анализ.\n\n"
            "Попробуй другой матч или "
            "проверь формат:\n"
            "Real Madrid - Barcelona",
            reply_markup=main_menu(),
        )


def parse_invoice_user_id(invoice_payload):
    prefix = "flux_pro_30_days:"

    if not invoice_payload.startswith(prefix):
        return None

    raw_user_id = invoice_payload[len(prefix):]

    try:
        return int(raw_user_id)
    except (TypeError, ValueError):
        return None


def process_pre_checkout_query(
    pre_checkout_query,
):
    query_id = pre_checkout_query.get("id")
    payer = pre_checkout_query.get("from", {})
    payer_id = payer.get("id")

    invoice_payload = pre_checkout_query.get(
        "invoice_payload",
        "",
    )

    currency = pre_checkout_query.get(
        "currency",
        "",
    )

    total_amount = pre_checkout_query.get(
        "total_amount",
        0,
    )

    payload_user_id = parse_invoice_user_id(
        invoice_payload
    )

    is_valid = (
        query_id
        and payer_id
        and payload_user_id == payer_id
        and currency == "XTR"
        and int(total_amount) == PRO_PRICE_STARS
    )

    try:
        answer_pre_checkout_query(
            query_id=query_id,
            approved=is_valid,
            error_message=(
                None
                if is_valid
                else (
                    "Не удалось проверить платёж. "
                    "Создайте новый счёт."
                )
            ),
        )

        print(
            "PRE_CHECKOUT:",
            {
                "payer_id": payer_id,
                "payload_user_id": payload_user_id,
                "amount": total_amount,
                "approved": is_valid,
            },
            flush=True,
        )

    except Exception as error:
        print(
            "PRE_CHECKOUT_ERROR:",
            repr(error),
            flush=True,
        )


def process_successful_payment(message):
    payment = message.get("successful_payment", {})
    user = message.get("from", {})
    chat = message.get("chat", {})

    user_id = user.get("id")
    chat_id = chat.get("id")

    invoice_payload = payment.get(
        "invoice_payload",
        "",
    )

    currency = payment.get("currency", "")
    total_amount = payment.get(
        "total_amount",
        0,
    )

    telegram_charge_id = payment.get(
        "telegram_payment_charge_id",
        "",
    )

    payload_user_id = parse_invoice_user_id(
        invoice_payload
    )

    payment_is_valid = (
        user_id
        and chat_id
        and payload_user_id == user_id
        and currency == "XTR"
        and int(total_amount) == PRO_PRICE_STARS
    )

    if not payment_is_valid:
        print(
            "INVALID_STARS_PAYMENT:",
            {
                "user_id": user_id,
                "payload_user_id": payload_user_id,
                "currency": currency,
                "amount": total_amount,
                "charge_id": telegram_charge_id,
            },
            flush=True,
        )

        if chat_id:
            send_message(
                chat_id,
                "⚠️ Платёж получен, но его данные "
                "не прошли проверку.\n\n"
                "Напишите в поддержку FLUX AI.",
                reply_markup=main_menu(),
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

    print(
        "STARS_PAYMENT_SUCCESS:",
        {
            "user_id": user_id,
            "amount": total_amount,
            "charge_id": telegram_charge_id,
        },
        flush=True,
    )

    send_message(
        chat_id,
        payment_success_message(),
        reply_markup=main_menu(),
    )


@app.route("/")
def home():
    return "FLUX AI Sports PRO v3.0 is running!"


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

        if message.get("successful_payment"):
            process_successful_payment(message)
            return "OK", 200

        chat = message.get("chat", {})
        user = message.get("from", {})

        chat_id = chat.get("id")
        user_id = user.get("id")

        text = message.get("text") or ""
        text = text.strip()

        print(
            "TELEGRAM_MESSAGE:",
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "text": text,
            },
            flush=True,
        )

        if not chat_id:
            return "OK", 200

        if user_id:
            add_user(user)

        if not text:
            send_message(
                chat_id,
                help_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "⚽ Анализ матча":
            send_message(
                chat_id,
                "⚽ Напиши матч:\n\n"
                "Real Madrid - Barcelona",
                reply_markup=main_menu(),
            )
            return "OK", 200

        button_commands = {
            "🏆 ТОП-3 дня": "/today",
            "🌍 ЧМ-2026": "/worldcup",
            "📈 Результаты": "/results",
            "🏆 Канал": "/channel",
            "💎 FLUX PRO": "/pro",
            "👤 Мой профиль": "/profile",
            "ℹ️ О проекте": "/about",
            "📊 Статус": "/status",
        }

        text = button_commands.get(text, text)

        if text == "/start":
            send_message(
                chat_id,
                start_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text in ["/help", "/analyze"]:
            send_message(
                chat_id,
                help_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/about":
            send_message(
                chat_id,
                about_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/status":
            send_message(
                chat_id,
                status_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/profile":
            send_message(
                chat_id,
                profile_message(user_id),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/admin":
            if user_id != ADMIN_TELEGRAM_ID:
                send_message(
                    chat_id,
                    "⛔ Доступ запрещён.",
                    reply_markup=main_menu(),
                )
                return "OK", 200

            send_message(
                chat_id,
                admin_panel_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/channel":
            send_message(
                chat_id,
                channel_message(),
                reply_markup={
                    "inline_keyboard": [
                        [
                            {
                                "text": "🏆 Открыть канал",
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
                worldcup_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/results":
            send_message(
                chat_id,
                results_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/today":
            send_message(
                chat_id,
                "🏆 Собираю ТОП-3 "
                "прогнозов дня...",
                reply_markup=main_menu(),
            )

            send_message(
                chat_id,
                today_top_3_message(),
                reply_markup=main_menu(),
            )
            return "OK", 200

        if text == "/pro":
            try:
                send_message(
                    chat_id,
                    pro_message(),
                    reply_markup=main_menu(),
                )

                send_stars_invoice(
                    bot_token=BOT_TOKEN,
                    chat_id=chat_id,
                    user_id=user_id,
                    stars_price=PRO_PRICE_STARS,
                )

            except Exception as error:
                print(
                    "PRO_PAYMENT_ERROR:",
                    repr(error),
                    flush=True,
                )

                send_message(
                    chat_id,
                    "⚠️ Не получилось открыть "
                    "оплату Telegram Stars.\n\n"
                    "Попробуйте ещё раз немного позже.",
                    reply_markup=main_menu(),
                )

            return "OK", 200

        handle_analysis(
            chat_id,
            user_id,
            text,
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
        f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"
    )

    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": webhook_url,
                "drop_pending_updates": False,
                "allowed_updates": [
                    "message",
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
            os.environ.get("PORT", "10000")
        ),
    )
