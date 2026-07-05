import os
import requests
from threading import Thread
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")

app = Flask(__name__)


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(url, json=payload, timeout=20)


def main_menu():
    return {
        "keyboard": [
            ["⚽ Анализ матча"],
            ["🏆 ТОП-3 дня"],
            ["ℹ️ О проекте", "📊 Статус"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def detect_match(text):
    text = text.strip()

    separators = [
        " — ",
        " – ",
        " - ",
        "—",
        "–",
        "-",
        " vs ",
        " VS ",
        " Vs ",
        " v ",
        " V ",
    ]

    for sep in separators:
        if sep in text:
            parts = text.split(sep, 1)

            if len(parts) == 2:
                team1 = parts[0].strip()
                team2 = parts[1].strip()

                if team1 and team2:
                    return team1, team2

    return None, None


def analyze_match_text(text):
    team1, team2 = detect_match(text)

    if not team1 or not team2:
        return (
            "⚠️ Напиши матч в формате:\n\n"
            "Реал Мадрид — ПСЖ\n"
            "или\n"
            "Liverpool — Arsenal"
        )

    from engine.analyzer import analyze_and_format
    return analyze_and_format(team1, team2)


def start_message():
    return (
        "👋 Привет! Я FLUX AI Sports PRO v1.2\n\n"
        "Я анализирую футбольные матчи и рассчитываю:\n"
        "📊 FLUX Rating\n"
        "🎯 вероятности П1 / X / П2\n"
        "🏆 ТОП-3 рекомендации\n"
        "⚽ тоталы\n"
        "🥅 обе забьют\n"
        "🧠 вердикт FLUX AI\n"
        "⚠️ риск и уверенность\n\n"
        "Выбери действие в меню ниже или напиши матч вручную.\n\n"
        "Пример:\n"
        "Liverpool — Arsenal"
    )


def help_message():
    return (
        "📌 Как пользоваться FLUX AI:\n\n"
        "Просто напиши матч в формате:\n"
        "Команда 1 — Команда 2\n\n"
        "Примеры:\n"
        "Реал Мадрид — ПСЖ\n"
        "Liverpool — Arsenal\n"
        "Inter — Milan\n"
        "Barcelona — Bayern\n"
        "Man City — Real Madrid\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/about — о проекте\n"
        "/status — статус бота\n"
        "/today — ТОП-3 прогнозов дня"
    )


def about_message():
    return (
        "⚽ FLUX AI Sports PRO\n\n"
        "Это AI-система футбольной аналитики.\n\n"
        "FLUX анализирует форму команд, атаку, защиту, вероятности исходов, "
        "тоталы, обе забьют и формирует ТОП-3 рекомендации.\n\n"
        "Важно: прогноз не является гарантией результата."
    )


def status_message():
    return (
        "✅ FLUX AI Sports работает.\n\n"
        "Версия: PRO v1.2\n"
        "Режим: Public Beta\n"
        "Источник данных: TheSportsDB + FLUX Engine\n"
        "Статус: Online"
    )


def today_message():
    return (
        "🏆 FLUX AI DAILY\n\n"
        "ТОП-3 прогнозов дня пока формируется.\n\n"
        "Попробуй отправить матч вручную:\n"
        "Liverpool — Arsenal"
    )


def today_top_3_message():
    try:
        from engine.today import today_top_3
        return today_top_3()
    except Exception as e:
        print("TODAY_ERROR:", e, flush=True)
        return today_message()


@app.route("/")
def home():
    return "FLUX AI Sports PRO v1.2 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()

    if not chat_id:
        return "OK"

    if not text:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "🏆 ТОП-3 дня":
        text = "/today"
    elif text == "ℹ️ О проекте":
        text = "/about"
    elif text == "📊 Статус":
        text = "/status"
    elif text == "⚽ Анализ матча":
        send_message(
            chat_id,
            "⚽ Напиши матч в формате:\n\nLiverpool — Arsenal",
            reply_markup=main_menu(),
        )
        return "OK"

    if text == "/start":
        send_message(chat_id, start_message(), reply_markup=main_menu())
        return "OK"

    if text == "/help":
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "/about":
        send_message(chat_id, about_message(), reply_markup=main_menu())
        return "OK"

    if text == "/status":
        send_message(chat_id, status_message(), reply_markup=main_menu())
        return "OK"

    if text == "/today":
        send_message(chat_id, "🏆 Собираю ТОП-3 прогнозов дня...", reply_markup=main_menu())
        send_message(chat_id, today_top_3_message(), reply_markup=main_menu())
        return "OK"

    send_message(chat_id, "⌛ Анализирую матч...", reply_markup=main_menu())

    try:
        answer = analyze_match_text(text)
        send_message(chat_id, answer, reply_markup=main_menu())
    except Exception as e:
        print("MATCH_ANALYSIS_ERROR:", e, flush=True)
        send_message(
            chat_id,
            "⚠️ Не получилось сделать анализ.\n\n"
            "Проверь формат запроса:\n"
            "Liverpool — Arsenal",
            reply_markup=main_menu(),
        )

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
