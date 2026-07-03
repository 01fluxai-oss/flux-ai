import os
import asyncio
from threading import Thread
from flask import Flask

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

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "FLUX AI Sports Bot is running!"


@web_app.route("/health")
def health():
    return "OK"


def detect_match(text):
    separators = ["—", "-", " vs ", " VS ", " v ", " V "]
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
    return None, None


def fmt_matches(matches):
    if not matches:
        return "Нет данных"

    lines = []
    for m in matches[:10]:
        if isinstance(m, dict):
            lines.append(
                f"{m.get('date')} | {m.get('league')} | "
                f"{m.get('home')} {m.get('score')} {m.get('away')}"
            )
        else:
            lines.append(str(m))
    return "\n".join(lines)


def build_prompt(team1, team2):
    data = build_match_context(team1, team2)

    if not data:
        return f"""
Матч: {team1} — {team2}

API-Football не нашёл данные по командам.
Сделай осторожный предварительный анализ и честно укажи, что данных недостаточно.
"""

    t1 = data["team1"]["name"]
    t2 = data["team2"]["name"]

    return f"""
Сделай профессиональный футбольный прогноз.

Матч:
{t1} — {t2}

Рассчитанные вероятности FLUX:
П1 — {data["probabilities"]["p1"]}%
Х — {data["probabilities"]["draw"]}%
П2 — {data["probabilities"]["p2"]}%

Форма {t1}:
{data["team1_form"]}

Форма {t2}:
{data["team2_form"]}

Очные встречи:
{data["h2h_analysis"]}

Последние матчи {t1}:
{fmt_matches(data["team1_last_matches"])}

Последние матчи {t2}:
{fmt_matches(data["team2_last_matches"])}

Последние очные встречи:
{fmt_matches(data["head_to_head"])}

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

Очные встречи:
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
Используй данные API-Football и расчёты FLUX.
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
        try:
            user_prompt = build_prompt(team1, team2)
        except Exception as e:
            print("Football API error:", e)
            user_prompt = f"""
Матч: {team1} — {team2}
Ошибка API-Football: {e}
Сделай осторожный предварительный анализ и честно укажи, что актуальные данные не получены.
"""
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


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)

        print("FLUX AI bot started")

    loop.run_until_complete(main())
    loop.run_forever()


if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    web_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
