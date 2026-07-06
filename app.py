from database.db import add_user, get_user, is_pro, activate_pro, save_payment
import os
import requests
from payments.stripe import create_checkout_session
from threading import Thread
from flask import Flask, request


BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

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


def main_menu():
    return {
        "keyboard": [
            ["⚽ Анализ матча"],
            ["🏆 ТОП-3 дня", "🌍 ЧМ-2026"],
            ["📈 Результаты"],
            ["🏆 Канал", "💎 FLUX PRO"],
            ["ℹ️ О проекте", "📊 Статус"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


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

    for sep in [" — ", " vs ", " VS ", " Vs ", " v ", " V "]:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()

    return None, None


def detect_matches(text):
    matches = []
    for line in text.splitlines():
        team1, team2 = detect_match(line.strip())
        if team1 and team2:
            matches.append((team1, team2))
    return matches


def analyze_match_text(text):
    from engine.analyzer import analyze_and_format

    matches = detect_matches(text)

    if not matches:
        return (
            "⚠️ Напиши матч в формате:\n\n"
            "Brazil — Norway\n\n"
            "Можно несколько матчей:\n"
            "Brazil — Norway\n"
            "England — Mexico"
        )

    if len(matches) == 1:
        return analyze_and_format(matches[0][0], matches[0][1])

    results = []
    for i, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            results.append(f"#{i}\n{analyze_and_format(team1, team2)}")
        except Exception:
            results.append(f"#{i}\n⚠️ Не получилось: {team1} — {team2}")

    return "\n\n".join(results)


def start_message():
    return (
        "👋 Привет! Я FLUX AI Sports PRO v3.0\n\n"
        "⚽ Анализ матчей\n"
        "🏆 ТОП-3 дня\n"
        "🌍 ЧМ-2026\n"
        "📈 Результаты\n"
        "💎 FLUX PRO\n\n"
        "Напиши матч:\n"
        "Brazil — Norway"
    )


def help_message():
    return (
        "📌 Как пользоваться:\n\n"
        "Один матч:\n"
        "Brazil — Norway\n\n"
        "Несколько матчей:\n"
        "Brazil — Norway\n"
        "England — Mexico\n\n"
        "/today — ТОП-3 дня\n"
        "/worldcup — ЧМ-2026\n"
        "/results — результаты\n"
        "/channel — канал\n"
        "/pro — FLUX PRO"
    )


def about_message():
    return (
        "⚽ FLUX AI Sports PRO\n\n"
        "AI-система футбольной аналитики.\n"
        "FLUX анализирует форму, атаку, защиту, вероятности, тоталы и рекомендации.\n\n"
        f"Официальный канал: {CHANNEL_USERNAME}\n\n"
        "Прогноз не является гарантией результата."
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


def pro_message():
    return (
        "💎 FLUX AI PRO\n\n"
        "Полный доступ к возможностям FLUX AI:\n\n"
        "🔥 VIP-прогнозы дня\n"
        "🎯 Экспрессы\n"
        "💰 Value Bets\n"
        "⚡ Ранние уведомления\n"
        "📊 Полная статистика\n\n"
        "💳 Цена: $9.99 / месяц\n\n"
        "Оформить подписку:\n"
        "https://buy.stripe.com/test_4gM14o2Pb2Cg5vNdDzefC00"
    )


def worldcup_message():
    return (
        "🌍 FLUX AI | ЧМ-2026\n\n"
        "🏆 Ближайшие прогнозы:\n\n"
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
        "🧠 FLUX AI считает, что в плей-офф ЧМ лучше осторожно работать с тоталами, двойными шансами и проходом дальше.\n\n"
        f"📢 Канал: {CHANNEL_URL}\n\n"
        "Прогноз не является гарантией результата."
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


def status_message():
    return (
        "✅ FLUX AI Sports работает.\n\n"
        "Версия: PRO v3.0\n"
        "Режим: Public Beta\n"
        f"Канал: {CHANNEL_USERNAME}\n"
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
            "ТОП-3 пока формируется.\n\n"
            "Попробуй:\n"
            "Brazil — Norway"
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

    message = data.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")
    text = message.get("text", "").strip()

    if user_id:
        add_user(user)

    if not chat_id:
        return "OK"

    if not text:
        send_message(chat_id, help_message(), reply_markup=main_menu())
        return "OK"

    if text == "⚽ Анализ матча":
        send_message(chat_id, "⚽ Напиши матч:\n\nBrazil — Norway", reply_markup=main_menu())
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
    elif text == "ℹ️ О проекте":
        text = "/about"
    elif text == "📊 Статус":
        text = "/status"

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
           url = create_checkout_session(user_id)

        send_message(
            chat_id,
            "💎 FLUX AI PRO\n\n"
            "Полный доступ ко всем возможностям FLUX AI.\n\n"
            "💳 Цена: $9.99 / месяц\n\n"
            f"Оформить подписку:\n{url}",
            reply_markup=main_menu(),
        )

        return "OK"

    send_message(
        chat_id,
        "💎 FLUX AI PRO\n\n"
        "Полный доступ ко всем возможностям FLUX AI.\n\n"
        "💳 Цена: $9.99 / месяц\n\n"
        f"Оформить подписку:\n{url}",
        reply_markup=main_menu(),
    )

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
            "Brazil — Norway",
            reply_markup=main_menu(),
        )

    return "OK"


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    ...
    return "OK"




def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True},
        timeout=20,
    )

    print("Webhook set:", response.text, flush=True)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
