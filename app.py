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
            "⚠️ Напиши матч в формате:\n\n"
            "Реал Мадрид — ПСЖ\n"
            "или\n"
            "Real Madrid — PSG"
        )

    from engine.analyzer import analyze_and_format
    return analyze_and_format(team1, team2)


def start_message():
    return (
        "👋 Привет! Я FLUX AI Sports v1.0\n\n"
        "Я анализирую футбольные матчи и рассчитываю:\n"
        "📊 FLUX Rating\n"
        "🎯 вероятности П1 / X / П2\n"
        "⚽ тотал 2.5\n"
        "🥅 обе забьют\n"
        "🔥 лучший вариант\n"
        "⚠️ риск и уверенность\n\n"
        "Напиши матч, например:\n"
        "Реал Мадрид — ПСЖ"
    )
