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
    return "FLUX AI Sports Bot is running!"


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


def fixture_summary(match):
    fixture = match.get("fixture", {})
    league = match.get("league", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})

    home = teams.get("home", {}).get("name")
    away = teams.get("away", {}).get("name")
    home_goals = goals.get("home")
    away_goals = goals.get("away")

    return (
        f"{fixture.get('date')} | {league.get('name')} | "
        f"{home} {home_goals}:{away_goals} {away}"
    )


def build_context_text(team1: str, team2: str):
    context = build_match_context(team1, team2)

    if not context:
        return None

    team1_info = context["team1"]
    team2_info = context["team2"]

    team1_form = context["team1_form"]
    team2_form = context["team2_form"]
    h2h_analysis = context["h2h_analysis"]
    probabilities = context["probabilities"]

    team1_last = [fixture_summary(m) for m in context["team1_last_matches"][:10]]
    team2_last = [fixture_summary(m) for m in context["team2_last_matches"][:10]]
    h2h = [fixture_summary(m) for m in context["head_to_head"][:10]]

    return f"""
Матч:
{team1_info.get("name")} — {team2_info.get("name")}

Рассчитанные вероятности FLUX:
П1 — {probabilities.get("p1")}%
Х — {probabilities.get("draw")}%
П2 — {probabilities.get("p2")}%

Форма {team1_info.get("name")} за последние матчи:
Матчей: {team1_form.get("played")}
Победы: {team1_form.get("wins")}
Ничьи: {team1_form.get("draws")}
Поражения: {team1_form.get("losses")}
Голы забито: {team1_form.get("goals_for")}
Голы пропущено: {team1_form.get("goals_against")}
Средние голы забито: {team1_form.get("avg_goals_for")}
Средние голы пропущено: {team1_form.get("avg_goals_against")}

Форма {team2_info.get("name")} за последние матчи:
Матчей: {team2_form.get("played")}
Победы: {team2_form.get("wins")}
Ничьи: {team2_form.get("draws")}
Поражения: {team2_form.get("losses")}
Голы забито: {team2_form.get("goals_for")}
Голы пропущено: {team2_form.get("goals_against")}
Средние голы забито: {team2_form.get("avg_goals_for")}
Средние голы пропущено: {team2_form.get("avg_goals_against")}

Очные встречи:
Матчей: {h2h_analysis.get("played")}
Победы первой команды: {h2h_analysis.get("team1_wins")}
Ничьи: {h2h_analysis.get("draws")}
Победы второй команды: {h2h_analysis.get("team2_wins")}
Средний тотал голов: {h2h_analysis.get("avg_total_goals")}

Последние матчи {team1_info.get("name")}:
{team1_last}

Последние матчи {team2_info.get("name")}:
{team2_last}

Последние очные встречи:
{h2h}
"""


SYSTEM_PROMPT = """
Ты FLUX AI Sports — профессиональный AI-аналитик футбольных матчей.

Используй данные API-Football и рассчитанные вероятности FLUX.
Не игнорируй статистику. Не придумывай данные, которых нет.

Формат ответа:

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
от 1 до 10

Вывод:
...

Важно:
- Никогда не обещай гарантированный выигрыш.
- Если данных мало, честно скажи это.
- Не давай совет как финансовую гарантию.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я FLUX AI Sports.\n\n"
        "Напиши матч в формате:\n"
        "Real Madrid — PSG\n"
        "или\n"
        "Реал Мадрид — ПСЖ"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — запустить бота\n"
        "/help — помощь\n\n"
        "Для прогноза напиши матч:\n"
        "Real Madrid — PSG"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text("⌛ Анализирую матч...")

    team1, team2 = detect_match(user_text)

    if team1 and team2:
        try:
            match_context = build_context_text(team1, team2)

            if not match_context:
                user_prompt = (
                    f"Пользователь запросил матч: {team1} — {team2}. "
                    "API-Football не смог найти команды. "
                    "Сделай предварительный анализ и честно скажи, что данных мало."
                )
            else:
                user_prompt = f"""
Пользователь запросил прогноз.

Вот реальные данные API-Football и расчеты FLUX:

{match_context}

Сделай анализ строго по структуре.
Используй рассчитанные вероятности FLUX.
"""
        except Exception as e:
            print("Football API error:", e)
            user_prompt = (
                f"Матч: {team1} — {team2}. "
                f"Ошибка API-Football: {e}. "
                "Сделай предварительный анализ и честно укажи, что актуальные данные не получены."
            )
    else:
        user_prompt = user_text

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

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    loop.run_until_complete(application.updater.start_polling(drop_pending_updates=True))

    print("FLUX AI bot started")

    loop.run_forever()


if __name__ == "__main__":
    run_bot()
