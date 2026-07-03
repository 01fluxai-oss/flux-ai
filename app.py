import os
import requests
from threading import Thread
from flask import Flask, request
from openai import OpenAI
from football import analyze_match

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)


def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )


def detect_match(text):
    for sep in ["—", "-", " vs ", " VS ", " v ", " V "]:
        if sep in text:
            parts = text.split(sep)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
    return None, None


def build_prompt(team1, team2):
    data = analyze_match(team1, team2)

    return f"""
Ты FLUX AI Sports — профессиональный AI-аналитик футбольных матчей.

Матч: {team1} — {team2}

Данные API-Football:
{data}

Сделай анализ строго в формате:

⚽ FLUX AI Sports Analysis

Матч:
...

Вероятности FLUX:
П1 — %
Х — %
П2 — %

Тотал 2.5:
Больше — %
Меньше — %

Обе забьют:
Да — %
Нет — %

Форма команд:
...

Ключевые факторы:
1.
2.
3.

Риск:
Низкий / Средний / Высокий

Уверенность:
1–10

Вывод:
...
"""


def analyze_with_ai(text):
    team1, team2 = detect_match(text)

    if team1 and team2:
        prompt = build_prompt(team1, team2)
    else:
        prompt = text

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты FLUX AI Sports. Не обещай гарантированный выигрыш."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content


@app.route("/")
def home():
    return "FLUX AI Sports Bot is running!"


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
        send_message(chat_id, "👋 Привет! Я FLUX AI Sports.\n\nНапиши матч, например:\nРеал Мадрид — ПСЖ")
        return "OK"

    send_message(chat_id, "⌛ Анализирую матч...")

    try:
        answer = analyze_with_ai(text)
        send_message(chat_id, answer)
    except Exception as e:
        print("ERROR:", e)
        send_message(chat_id, "⚠️ Ошибка анализа. Попробуйте ещё раз.")

    return "OK"


def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True},
        timeout=20,
    )
    print("Webhook set:", r.text)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
