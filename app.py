import os
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я FLUX AI.\n\n"
        "Напишите мне любой вопрос, и я отвечу как AI-ассистент."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды FLUX AI:\n"
        "/start — запустить бота\n"
        "/help — помощь\n\n"
        "Также вы можете просто написать любой вопрос."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("⏳ Думаю...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
"content": (
    "Ты FLUX AI Sports — профессиональный AI-аналитик спортивных матчей. "
    "Твоя задача — анализировать матчи, форму команд, статистику, мотивацию, травмы, коэффициенты и риски. "
    "Никогда не обещай гарантированный выигрыш. "
    "Давай прогноз только как аналитическое мнение с вероятностями и уровнем риска. "
    "Отвечай структурировано: вероятности, ключевые факторы, риск, вывод. "
    "Если у тебя нет свежих данных, честно скажи, что анализ предварительный и нужны актуальные составы, травмы и коэффициенты."
)
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            temperature=0.7
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(
            "⚠️ Сейчас не получилось получить ответ от AI. Попробуйте ещё раз позже."
        )
        print("OpenAI error:", e)

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
