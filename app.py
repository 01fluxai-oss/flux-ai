import os
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]

app = Flask(__name__)

@app.route("/")
def home():
    return "FLUX AI Bot is running!"

@app.route("/health")
def health():
    return "OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! FLUX AI успешно запущен.\n\n"
        "Я готов стать вашим AI-ассистентом."
    )

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))

        await application.initialize()
        await application.start()
        await application.updater.start_polling()

    loop.run_until_complete(main())
    loop.run_forever()

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
