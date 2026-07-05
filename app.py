import os
import requests
from threading import Thread
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")

CHANNEL_ID = "-1003654137478"
CHANNEL_USERNAME = "@FluxAIDaily"
CHANNEL_URL = "https://t.me/FluxAIDaily"

app = Flask(__name__)


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print("SEND_MESSAGE_ERROR:", e, flush=True)


def answer_callback(callback_id, text=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(
            url,
            json={"callback_query_id": callback_id, "text": text, "show_alert": False},
            timeout=20,
        )
    except Exception as e:
        print("ANSWER_CALLBACK_ERROR:", e, flush=True)


def main_menu():
    return {
        "keyboard": [
            ["⚽ Анализ матча"],
            ["🏆 ТОП-3 дня"],
            ["🏆 Канал", "💎 FLUX PRO"],
            ["ℹ️ О проекте", "📊 Статус"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def subscribe_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🏆 Подписаться на канал", "url": CHANNEL_URL}],
            [{"text": "✅ Проверить подписку", "callback_data": "check_subscription"}],
        ]
    }


def is_subscribed(user_id):
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
            params={"chat_id": CHANNEL_ID, "user_id": user_id},
            timeout=20,
        )
        data = response.json()

        if not data.get("ok"):
            print("SUBSCRIPTION_CHECK_NOT_OK:", data, flush=True)
            return False

        status = data.get("result", {}).get("status")
        return status in ["member", "administrator", "creator"]

    except Exception as e:
        print("SUBSCRIPTION_CHECK_ERROR:", e, flush=True)
        return False


def subscription_message():
    return (
        "🔒 Для использования FLUX AI нужно подписаться на официальный канал.\n\n"
        "🏆 FLUX AI DAILY\n"
        f"{CHANNEL_USERNAME}\n\n"
        "1️⃣ Нажми «🏆 Подписаться на канал»\n"
        "2️⃣ Подпишись\n"
        "3️⃣ Вернись сюда и нажми «✅ Проверить подписку»"
    )


def normalize_text(text):
    return (
        text.replace("—", " — ")
        .replace("–", " — ")
        .replace("-", " — ")
        .replace("  ", " ")
        .strip()
    )


def detect_match(line):
    line = normalize_text(line)

    separators = [" — ", " vs ", " VS ", " Vs ", " v ", " V "]

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
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matches = []

    for line in lines:
        team1, team2 = detect_match(line)
        if team1 and team2:
            matches.append((team1, team2))

    return matches


def analyze_match_text(text):
    from engine.analyzer import analyze_and_format

    matches = detect_matches(text)

    if not matches:
        return (
            "⚠️ Напиши матч в формате:\n\n"
            "Liverpool — Arsenal\n\n"
            "Можно отправить несколько матчей, каждый с новой строки:\n\n"
            "Liverpool — Arsenal\n"
            "Real Madrid — PSG\n"
            "Barcelona — Bayern"
        )

    if len(matches) == 1:
        team1, team2 = matches[0]
        return analyze_and_format(team1, team2)

    messages = []

    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            result = analyze_and_format(team1, team2)
            messages.append(f"#{index}\n{result}")
        except Exception as e:
            print("MULTI_MATCH_ERROR:", team1, team2, e, flush=True)
            messages.append(f"#{index}\n⚠️ Не получилось проанализировать:\n{team1} — {team2}")

    return "\n\n".join(messages)


def start_message():
    return (
        "👋 Привет! Я FLUX AI Sports PRO v2.3\n\n"
        "Я анализирую футбольные матчи и рассчитываю:\n"
        "📊 FLUX Rating\n"
        "🎯 вероятности П1 / X / П2\n"
        "🏆 ТОП-3 рекомендации\n"
        "⚽ тоталы\n"
        "🥅 обе забьют\n"
        "🧠 вердикт FLUX AI\n"
        "⚠️ риск и уверенность\n\n"
        "Можно отправить один матч или несколько матчей списком.\n\n"
        "Пример:\n"
        "Liverpool — Arsenal\n"
        "Real Madrid — PSG"
    )


def help_message():
    return (
        "📌 Как пользоваться FLUX AI:\n\n"
        "Один матч:\n"
        "Liverpool — Arsenal\n\n"
        "Несколько матчей:\n"
        "Liverpool — Arsenal\n"
        "Real Madrid — PSG\n"
        "Barcelona — Bayern\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/about — о проекте\n"
        "/status — статус бота\n"
        "/today — ТОП-3 прогнозов дня\n"
        "/channel — канал FLUX AI\n"
        "/pro — FLUX PRO"
    )


def about_message():
    return (
        "⚽ FLUX AI Sports PRO\n\n"
        "AI-система футбольной аналитики.\n"
        "FLUX анализирует форму команд, атаку, защиту, вероятности, тоталы "
        "и формирует рекомендации.\n\n"
        "Официальный канал:\n"
        f"{CHANNEL_USERNAME}\n\n"
        "Важно: прогноз не является гарантией результата."
    )


def pro_message():
    return (
        "💎 FLUX AI PRO\n\n"
        "Открой полный доступ к возможностям FLUX AI.\n\n"
        "🔥 Что входит:\n"
        "• VIP-прогнозы дня\n"
        "• Экспрессы с высокой вероятностью\n"
        "• Value Bets\n"
        "• Ранний доступ к прогнозам\n"
        "• Уведомления перед матчами\n"
        "• Полная статистика FLUX AI\n\n"
        "💰 Стоимость:\n"
        "$9.99 / месяц\n\n"
        "🚀 Скоро будет доступно."
    )


def channel_message():
    return (
        "🏆 FLUX AI DAILY\n\n"
        "Официальный канал FLUX AI.\n\n"
        "Там публикуются:\n"
        "⚽ ТОП-3 прогнозов дня\n"
        "📊 AI-анализ матчей\n"
        "🔥 Лучшие ставки\n"
        "💎 Новости FLUX PRO\n\n"
        "📢 Подписаться:\n"
        f"{CHANNEL_URL}"
    )


def status_message():
    return (
        "✅ FLUX AI Sports работает.\n\n"
        "Версия: PRO v2.3\n"
        "Режим: Public Beta\n"
        f"Канал: {CHANNEL_USERNAME}\n"
        "Источник данных: TheSportsDB + FLUX Engine\n"
        "Статус: Online"
    )


def today_top_3_message():
    try:
        from engine.today import today_top_3
        return today_top_3()
    except Exception as e:
        print("TODAY_ERROR:", e, flush=True)
        return (
            "🏆 FLUX AI DAILY\n\n"
            "ТОП-3 прогнозов дня пока формируется.\n\n"
            "Попробуй отправить матч вручную:\n"
            "Liverpool — Arsenal"
        )


@app.route("/")
def home():
    return "FLUX AI Sports PRO v2.3 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        user_id = callback["from"]["id"]
        chat_id = callback["message"]["chat"]["id"]
        callback_data = callback.get("data", "")

        if callback_data == "check_subscription":
            if is_subscribed(user_id):
                answer_callback(callback_id, "✅ Подписка подтверждена")
                send_message(chat_id, start_message(), reply_markup=main_menu())
            else:
                answer_callback(callback_id, "❌ Подписка не найдена")
                send_message(chat_id, subscription_message(), reply_markup=subscribe_keyboard())

        return "OK"

    message = data.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")
    text = message.get("text", "").strip()

    if not chat_id:
        return "OK"

    if not is_subscribed(user_id):
        send_message(chat_id, subscription_message(), reply_markup=subscribe_keyboard())
        return "OK"

    if not text:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "🏆 ТОП-3 дня":
        text = "/today"
    elif text == "🏆 Канал":
        text = "/channel"
    elif text == "ℹ️ О проекте":
        text = "/about"
    elif text == "📊 Статус":
        text = "/status"
    elif text == "💎 FLUX PRO":
        text = "/pro"
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

    if text == "/pro":
        send_message(chat_id, pro_message(), reply_markup=main_menu())
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

    if text == "/today":
        send_message(chat_id, "🏆 Собираю ТОП-3 прогнозов дня...", reply_markup=main_menu())
        send_message(chat_id, today_top_3_message(), reply_markup=main_menu())
        return "OK"

    matches = detect_matches(text)

    if len(matches) > 1:
        send_message(chat_id, f"⌛ Анализирую {len(matches)} матчей...", reply_markup=main_menu())
    else:
        send_message(chat_id, "⌛ Анализирую матч...", reply_markup=main_menu())

    try:
        answer = analyze_match_text(text)
        send_message(chat_id, answer, reply_markup=main_menu())
    except Exception as e:
        print("MATCH_ANALYSIS_ERROR:", e, flush=True)
        send_message(
            chat_id,
            "⚠️ Не получилось сделать анализ.\n\n"
            "Проверь формат:\n"
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
