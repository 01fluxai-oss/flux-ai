import os
import requests
import stripe
from threading import Thread
from flask import Flask, request

from database.db import (
    add_user,
    get_user,
    is_pro,
    activate_pro,
    save_payment,
    save_prediction,
    can_analyze,
    increase_today_usage,
    get_today_usage,
    free_limit_message,
)

from payments.stars import send_stars_invoice


BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"

FREE_DAILY_LIMIT = 2

app = Flask(__name__)


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print("SEND_MESSAGE_ERROR:", e, flush=True)


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

    separators = [" - ", "-", " vs ", " VS ", " Vs ", " v ", " V "]

    for sep in separators:
        if sep in line:
            parts = line.split(sep, 1)

            if len(parts) == 2:
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
        "Бот оценивает форму команд, вероятности, тоталы, двойной шанс и лучший прогноз.\n\n"
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


def profile_message(user_id):
    user = get_user(user_id)

    if not user:
        return "👤 Профиль не найден. Нажми /start."

    pro_status = "✅ Активен" if is_pro(user_id) else "❌ Не активен"
    usage = get_today_usage(user_id)

    if is_pro(user_id):
        limit_text = "Безлимит"
    else:
        limit_text = f"{usage}/{FREE_DAILY_LIMIT} сегодня"

    return (
        "👤 МОЙ ПРОФИЛЬ\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user_id}\n\n"
        f"💎 FLUX PRO: {pro_status}\n\n"
        "📊 Статистика:\n"
        f"• Анализы сегодня: {limit_text}\n"
        "• Победных прогнозов: скоро\n\n"
        "🚀 FLUX AI v1.0\n\n"
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
        "Скоро здесь будет реальная статистика всех прогнозов FLUX AI."
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
        "🎯 Уверенность: 60/10\n"
        "⚠️ Риск: Высокий\n\n"
        "🥈 Real Madrid — Paris Saint-Germain\n"
        "🔥 Прогноз: ТБ 2.5 — 82%\n"
        "🎯 Уверенность: 55/10\n"
        "⚠️ Риск: Высокий\n\n"
        "🥉 Barcelona — Bayern Munich\n"
        "🔥 Прогноз: ТБ 2.5 — 77%\n"
        "🎯 Уверенность: 50/10\n"
        "⚠️ Риск: Высокий\n\n"
        "Важно: прогноз не является гарантией результата."
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
        "Стоимость: $9.99 / месяц\n\n"
        "👇 Нажми кнопку ниже для оплаты:"
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

    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            result = analyze_and_format(team1, team2)
            results.append(f"#{index}\n{result}")
        except Exception as e:
            print("MULTI_ANALYSIS_ERROR:", e, flush=True)
            results.append(f"#{index}\n⚠️ Не получилось: {team1} - {team2}")

    return "\n\n".join(results)


def handle_analysis(chat_id, user_id, text):
    matches = detect_matches(text)

    print(">>> MATCHES:", matches, flush=True)

    if not matches:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return

    if not is_pro(user_id):
        used = get_today_usage(user_id)
        remaining = FREE_DAILY_LIMIT - used

        if remaining <= 0:
            send_message(chat_id, free_limit_message(), reply_markup=main_menu())
            return

        if len(matches) > remaining:
            send_message(
                chat_id,
                "🔒 У вас осталось бесплатных анализов сегодня: "
                f"{remaining}\n\n"
                "Отправьте меньше матчей или оформите FLUX PRO.",
                reply_markup=main_menu(),
            )
            return

    if len(matches) > 1:
        send_message(chat_id, f"⏳ Анализирую {len(matches)} матчей...", reply_markup=main_menu())
    else:
        send_message(chat_id, "⏳ Анализирую матч...", reply_markup=main_menu())

    try:
        answer = analyze_match_text(text)
        send_message(chat_id, answer, reply_markup=main_menu())

        for team1, team2 in matches:
            save_prediction(user_id, f"{team1} - {team2}", answer)
            increase_today_usage(user_id)

    except Exception as e:
        print("MATCH_ANALYSIS_ERROR:", e, flush=True)
        send_message(
            chat_id,
            "⚠️ Не получилось сделать анализ.\n\n"
            "Попробуй другой матч или проверь формат:\n"
            "Real Madrid - Barcelona",
            reply_markup=main_menu(),
        )


@app.route("/")
def home():
    return "FLUX AI Sports PRO v3.0 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    if not data:
        return "OK"

    message = data.get("message", {})

    if not message:
        return "OK"

    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")
    text = message.get("text", "").strip()

    print("==========", flush=True)
    print("TEXT:", repr(text), flush=True)

    if not chat_id:
        return "OK"

    if user_id:
        add_user(user)

    if not text:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "⚽ Анализ матча":
        send_message(
            chat_id,
            "⚽ Напиши матч:\n\nReal Madrid - Barcelona",
            reply_markup=main_menu(),
        )
        return "OK"

    if text == "🏆 ТОП-3 дня":
        text = "/today"
    elif text == "🌍 ЧМ-2026":
        text = "/worldcup"
    elif text == "📈 Результаты":
        text = "/results"
    elif text == "🏆 Канал":
        text = "/channel"
    elif text == "💎 FLUX PRO":
        text = "/pro"
    elif text == "👤 Мой профиль":
        text = "/profile"
    elif text == "ℹ️ О проекте":
        text = "/about"
    elif text == "📊 Статус":
        text = "/status"

    if text == "/start":
        send_message(chat_id, start_message(), reply_markup=main_menu())
        return "OK"

    if text in ["/help", "/analyze"]:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "/about":
        send_message(chat_id, about_message(), reply_markup=main_menu())
        return "OK"

    if text == "/status":
        send_message(chat_id, status_message(), reply_markup=main_menu())
        return "OK"

    if text == "/profile":
        send_message(chat_id, profile_message(user_id), reply_markup=main_menu())
        return "OK"

    if text == "/channel":
        send_message(
            chat_id,
            channel_message(),
            reply_markup={
                "inline_keyboard": [
                    [{"text": "🏆 Открыть канал", "url": CHANNEL_URL}]
                ]
            },
        )
        return "OK"

    if text == "/worldcup":
        send_message(chat_id, worldcup_message(), reply_markup=main_menu())
        return "OK"

    if text == "/results":
        send_message(chat_id, results_message(), reply_markup=main_menu())
        return "OK"

    if text == "/today":
        send_message(chat_id, "🏆 Собираю ТОП-3 прогнозов дня...", reply_markup=main_menu())
        send_message(chat_id, today_top_3_message(), reply_markup=main_menu())
        return "OK"

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
                stars_price=500,
            )

        except Exception as e:
            print("PRO_PAYMENT_ERROR:", e, flush=True)
            send_message(
                chat_id,
                "⚠️ Не получилось открыть оплату Telegram Stars.\n\n"
                "Попробуйте ещё раз немного позже.",
                reply_markup=main_menu(),
            )

        return "OK"

    handle_analysis(chat_id, user_id, text)

    return "OK"


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                STRIPE_WEBHOOK_SECRET,
            )
        else:
            event = request.get_json(force=True)

    except Exception as e:
        print("STRIPE_WEBHOOK_ERROR:", e, flush=True)
        return "BAD", 400

    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})

    print("STRIPE_EVENT:", event_type, flush=True)

    if event_type in [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
    ]:
        metadata = obj.get("metadata", {})
        user_id = metadata.get("telegram_id")

        if not user_id:
            subscription_details = obj.get("subscription_details", {})
            metadata = subscription_details.get("metadata", {})
            user_id = metadata.get("telegram_id")

        if user_id:
            activate_pro(int(user_id))
            save_payment(
                int(user_id),
                provider="stripe",
                amount=9.99,
                currency="USD",
                status="paid",
            )
            print("PRO_ACTIVATED:", user_id, flush=True)

    return "OK"


def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={
            "url": webhook_url,
            "drop_pending_updates": True,
        },
        timeout=20,
    )

    print("Webhook set:", response.text, flush=True)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
