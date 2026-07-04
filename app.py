import os
import requests
from threading import Thread
from flask import Flask, request
from openai import OpenAI
from engine.analyzer import analyze_match_v2

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
    separators = ["—", "-", " vs ", " VS ", " v ", " V "]
    for sep in separators:
        if sep in text:
            parts = text.split(sep, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    return None, None


def build_prompt(team1, team2):
    data = analyze_match(team1, team2)

    if not data.get("success"):
        return f"""
Матч: {team1} — {team2}

Ошибка API-Football:
{data.get("error", "Данные не получены")}

Сделай осторожный предварительный анализ. Честно укажи, что актуальных статистических данных недостаточно.
"""

    t1 = data["team1"]["name"]
    t2 = data["team2"]["name"]

    return f"""
Ты FLUX AI Sports — профессиональный AI-аналитик футбольных матчей.

Матч:
{t1} — {t2}

ВАЖНО:
Не изменяй рассчитанные проценты FLUX. Используй их как основу анализа.

📊 FLUX INDEX:
{t1}: {data["flux_index"][t1]}/100
{t2}: {data["flux_index"][t2]}/100

🎯 Вероятности FLUX:
П1 — {data["probabilities"]["p1"]}%
Х — {data["probabilities"]["draw"]}%
П2 — {data["probabilities"]["p2"]}%

⚽ Тотал 2.5:
Больше — {data["totals"]["over_2_5"]}%
Меньше — {data["totals"]["under_2_5"]}%

🥅 Обе забьют:
Да — {data["totals"]["btts_yes"]}%
Нет — {data["totals"]["btts_no"]}%

📈 Форма команд:
{t1}: {data["team1_form"]}
{t2}: {data["team2_form"]}

🤝 Очные встречи:
{data["h2h"]}

Последние матчи {t1}:
{data["team1_last_matches"]}

Последние матчи {t2}:
{data["team2_last_matches"]}

Последние очные встречи:
{data["head_to_head"]}

Ответь строго в формате:

⚽ FLUX AI Sports Analysis

Матч:
...

FLUX Index:
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

Очные встречи:
...

Ключевые факторы:
1.
2.
3.

Лучший вариант:
...

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
            {
                "role": "system",
                "content": "Ты FLUX AI Sports. Не обещай гарантированный выигрыш. Анализируй как профессиональный спортивный аналитик.",
            },
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
        send_message(
            chat_id,
            "👋 Привет! Я FLUX AI Sports.\n\nНапиши матч, например:\nРеал Мадрид — ПСЖ\nили\nReal Madrid — PSG",
        )
        return "OK"

    if text == "/help":
        send_message(
            chat_id,
            "Напиши матч в формате:\nКоманда 1 — Команда 2\n\nПример:\nРеал Мадрид — ПСЖ",
        )
        return "OK"

    send_message(chat_id, "⌛ Анализирую матч...")

        try:
            answer = analyze_with_ai(text)
        send_message(chat_id, answer)
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_message(chat_id, f"Ошибка:\n{e}")
        import traceback
        traceback.print_exc()
        send_message(chat_id, f"Ошибка:\n{e}")
    send_message(chat_id, f"Ошибка:\n{e}")

    return "OK"


def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"

    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={
            "url": webhook_url,
            "drop_pending_updates": True,
        },
        timeout=20,
    )

    print("Webhook set:", r.text)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
