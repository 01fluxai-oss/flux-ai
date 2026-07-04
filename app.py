import os
import requests
from threading import Thread
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")

app = Flask(__name__)


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )


def detect_match(text):
    separators = ["—", "-", " vs ", " VS ", " v ", " V "]
    for sep in separators:
        if sep in text:
            parts = text.split(sep, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    return None, None


def analyze_match_text(text):
    team1, team2 = detect_match(text)

    if not team1 or not team2:
        return (
            "Напишите матч в формате:\n"
            "Реал Мадрид — ПСЖ\n"
            "или\n"
            "Real Madrid — PSG"
        )

    from flux_engine import calculate_match, format_analysis

    team1_form = {
        "matches": 10,
        "points": 23,
        "wins": 7,
        "draws": 2,
        "losses": 1,
        "goals_for": 23,
        "goals_against": 9,
        "avg_goals_for": 2.3,
        "avg_goals_against": 0.9,
    }

    team2_form = {
        "matches": 10,
        "points": 20,
        "wins": 6,
        "draws": 2,
        "losses": 2,
        "goals_for": 20,
        "goals_against": 12,
        "avg_goals_for": 2.0,
        "avg_goals_against": 1.2,
    }

    result = calculate_match(
        team1=team1,
        team2=team2,
        team1_form=team1_form,
        team2_form=team2_form,
    )

    return format_analysis(result, team1_form, team2_form)
    team1, team2 = detect_match(text)

    if not team1 or not team2:
        return (
            "Напишите матч в формате:\n"
            "Реал Мадрид — ПСЖ\n"
            "или\n"
            "Real Madrid — PSG"
        )

    # Временный чистый FLUX Engine v2 без внешнего API
    return f"""
⚽ FLUX AI Sports Analysis

Матч:
{team1} — {team2}

📊 FLUX Score:
82 / 100

📈 FLUX Index:
{team1}: 84 / 100
{team2}: 78 / 100

🎯 Вероятности FLUX:
П1 — 48%
X — 27%
П2 — 25%

⚽ Тотал 2.5:
Больше — 64%
Меньше — 36%

🥅 Обе забьют:
Да — 69%
Нет — 31%

🔥 Лучший вариант:
Обе забьют — Да

⚠️ Риск:
Средний

🎯 Уверенность:
8.1 / 10

Вывод:
FLUX AI оценивает матч на основе базовой модели формы, атаки, защиты и баланса сил. Это аналитический прогноз, а не гарантия результата.
"""


@app.route("/")
def home():
    return "FLUX AI Sports v2 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if not chat_id:
        return "OK"

    if text == "/start":
        send_message(
            chat_id,
            "👋 Привет! Я FLUX AI Sports v2.\n\n"
            "Напиши матч, например:\n"
            "Реал Мадрид — ПСЖ",
        )
        return "OK"

    if text == "/help":
        send_message(
            chat_id,
            "Формат запроса:\n"
            "Команда 1 — Команда 2\n\n"
            "Пример:\n"
            "Реал Мадрид — ПСЖ",
        )
        return "OK"

    send_message(chat_id, "⌛ Анализирую матч...")

    try:
        answer = analyze_match_text(text)
        send_message(chat_id, answer)
    except Exception as e:
        print("ERROR:", e, flush=True)
        send_message(chat_id, "⚠️ Ошибка анализа. Попробуйте ещё раз.")

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
