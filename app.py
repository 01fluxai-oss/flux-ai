import os
import asyncio
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI
from football import build_match_context


BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)


@app.route("/")
def home():
    return "FLUX AI Bot is running!"


@app.route("/health")
def health():
    return "OK"


def detect_match(text: str):
    separators = ["—", "-", " vs ", " VS ", " v ", " V "]

    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            if len(parts) >= 2:
                team1 = parts[0].strip()
                team2 = parts[1].strip()
                if team1 and team2:
                    return team1, team2

    return None, None


def simplify_fixture(match):
    fixture = match.get("fixture", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})
    league = match.get("league", {})

    return {
        "date": fixture.get("date"),
        "league": league.get("name"),
        "country": league.get("country"),
        "home": teams.get("home", {}).get("name"),
        "away": teams.get("away", {}).get("name"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "status": fixture.get("status", {}).get("short"),
    }


def build_context_text(team1: str, team2: str):
    try:
        context = build_match_context(team1, team2)

        if not context:
            return (
                f"Матч: {team1} — {team2}\n"
                "API-Football не смог найти одну из команд. "
                "Сделай предварительный анализ и честно укажи, что данных API недостаточно."
            )

        team1_info = context["team1"]
        team2_info = context["team2"]

        team1_last = [simplify_fixture(m) for m in context["team1_last_matches"]]
        team2_last = [simplify_fixture(m) for m in context["team2_last_matches"]]
        h2h = [simplify_fixture(m) for m in context["head_to_head"]]

        return f"""
Матч: {team1_info.get("name")} — {team2_info.get("name")}

Данные API-Football:

Команда 1:
ID: {team1_info.get("id")}
Название: {team1_info.get("name")}
Страна: {team1_info.get("country")}

Команда 2:
ID: {team2_info.get("id")}
Название: {team2_info.get("name")}
Страна: {team2_info.get("country")}

Последние матчи команды 1:
{team1_last}

Последние матчи команды 2:
{team2_last}

Очные встречи:
{h2h}

На основе этих данных сделай профессиональный прогноз.
"""
    except Exception as e:
        return (
            f"Матч: {team1} — {team2}\n"
            f"Ошибка получения данных API-Football: {e}\n"
            "Сделай предварительный анализ и честно укажи, что актуальные данные получить не удалось."
        )


SYSTEM_PROMPT = """
Ты FLUX AI Sports — профессиональный AI-аналитик футбольных матчей.

Твоя задача — анализировать матчи на основе данных API-Football и спортивной логики.

Всегда отвечай структурировано:

⚽ FLUX AI Sports Analysis

Матч:
...

Вероятности:
П1 — %
Х — %
П2 — %

Тотал 2.5:
Больше — %
Меньше — %

Обе забьют:
Да — %
Нет — %

Ключевые факторы:
1.
2.
3.

Риск:
Низкий / Средний / Высокий

Уверенность:
от 1 до 10

Вывод:
...

Важно:
- Никогда не обещай гарантированный выигрыш.
- Не пиши, что ставка точно зайдет.
- Если данных мало, честно скажи, что анализ предварительный.
- Не выдумывай травмы, составы и коэффициенты, если их нет в данных.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я FLUX AI Sports.\n\n"
        "Напиши матч в формате:\n"
        "Реал Мадрид — ПСЖ\n\n"
        "Я проанализирую форму команд, последние матчи и очные встречи."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды FLUX AI:\n"
        "/start — запустить бота\n"
        "/help — помощь\n\n"
        "Для прогноза просто напиши матч:\n"
        "Манчестер Сити — Ливерпуль"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("⌛ Анализирую матч...")

    team1, team2 = detect_match(user_text)

    if team1 and team2:
        match_context = build_context_text(team1, team2)
        user_prompt = f"""
Пользователь запросил прогноз на матч.

{match_context}

Сделай прогноз строго по структуре FLUX AI Sports Analysis.
"""
    else:
        user_prompt = user_text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0.4,
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        print("OpenAI error:", e)
        await update.message.reply_text(
            "⚠️ Сейчас не получилось получить ответ от AI. Попробуйте ещё раз позже."
        )


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await application.initialize()
        await application.start()
        await application.updater.start_polling()

    loop.run_until_complete(main())
    loop.run_forever()


if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
