import os
import asyncio
from threading import Thread
from flask import Flask, request

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI
from football import analyze_match


BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com")

client = OpenAI(api_key=OPENAI_API_KEY)

web_app = Flask(__name__)

bot_loop = asyncio.new_event_loop()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()


def detect_match(text):
    separators = ["—", "-", " vs ", " VS ", " v ", " V "]
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
    return None, None


def build_prompt(team1, team2):
    data = analyze_match(team1, team2)

    if not data.get("success"):
        return f"""
Матч: {team1} — {team2}

API-Football ошибка:
{data.get("error", "Данные не получены")}

Сделай осторожный предварительный анализ. Честно укажи, что актуальные данные ограничены.
"""

    return f"""
Сделай профессиональный футбольный прогноз.

Матч:
{data["team1"]} — {data["team2"]}

Данные команды 1:
{data["team1_data"]}

Данные команды 2:
{data["team2_data"]}

Ответь строго в формате:

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


SYSTEM_PROMPT = """
Ты FLUX AI Sports — профессиональный AI-аналитик футбольных матчей.
Используй данные API-Football.
Не обещай гарантированный выигрыш.
Если данных мало, честно скажи об этом.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я FLUX AI Sports.\n\n"
        "Напиши матч, например:\n"
        "Реал Мадрид — ПСЖ\n"
        "или\n"
        "Real Madrid — PSG"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши матч в формате:\n"
        "Команда 1 — Команда 2\n\n"
        "Пример:\n"
        "Реал Мадрид — ПСЖ"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text("⌛ Анализирую матч...")

    team1, team2 = detect_match(text)

    if team1 and team2:
        user_prompt = build_prompt(team1, team2)
    else:
        user_prompt = text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        print("OpenAI error:", e)
        await update.message.reply_text(
            "⚠️ Сейчас не получилось получить ответ от AI. Попробуйте ещё раз позже."
        )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)


def run_bot_loop():
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_until_complete(telegram_app.initialize())
    bot_loop.run_until_complete(telegram_app.start())
    print("FLUX AI webhook bot started")
    bot_loop.run_forever()


@web_app.route("/")
def home():
    return "FLUX AI Sports Bot is running!"


@web_app.route("/health")
def health():
    return "OK"


@web_app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run_coroutine_threadsafe(
        telegram_app.process_update(update),
        bot_loop
    )
    return "OK"


def set_webhook():
    import requests

    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        data={
            "url": webhook_url,
            "drop_pending_updates": True,
        },
        timeout=20,
    )

    print("Webhook set:", response.text)


if __name__ == "__main__":
    Thread(target=run_bot_loop, daemon=True).start()
    set_webhook()

    web_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
