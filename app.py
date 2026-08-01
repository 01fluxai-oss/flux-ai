import os
from threading import Thread

import requests
from flask import Flask, request

from database.db import (
    activate_pro,
    add_user,
    free_limit_message,
    get_admin_stats,
    get_today_usage,
    get_user,
    get_user_language,
    get_user_sport,
    increase_today_usage,
    init_db,
    is_pro,
    save_payment,
    save_prediction,
    set_user_language,
    set_user_sport,
)
from payments.stars import send_stars_invoice

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://flux-ai-8p34.onrender.com").rstrip("/")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))
CHANNEL_URL = "https://t.me/FluxAIDaily"
CHANNEL_USERNAME = "@FluxAIDaily"

# Временно 10 для тестирования NBA. После успешного теста вернуть 2.
FREE_DAILY_LIMIT = 10
PRO_PRICE_STARS = 500
PRO_DAYS = 30

app = Flask(__name__)
init_db()


def telegram_api(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, json=payload, timeout=20)
    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError(f"Telegram returned invalid JSON: {response.text[:500]}") from error
    if not response.ok or not result.get("ok"):
        raise RuntimeError(f"Telegram API error in {method}: {result}")
    return result


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        return telegram_api("sendMessage", payload)
    except Exception as error:
        print("SEND_MESSAGE_ERROR:", repr(error), flush=True)
        return None


def answer_callback_query(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        return telegram_api("answerCallbackQuery", payload)
    except Exception as error:
        print("ANSWER_CALLBACK_ERROR:", repr(error), flush=True)
        return None


def answer_pre_checkout_query(query_id, approved, error_message=None):
    payload = {"pre_checkout_query_id": query_id, "ok": approved}
    if not approved and error_message:
        payload["error_message"] = error_message
    return telegram_api("answerPreCheckoutQuery", payload)


def language_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "🇺🇸 English", "callback_data": "lang_en"},
            {"text": "🇷🇺 Русский", "callback_data": "lang_ru"},
        ]]
    }


def main_menu(language="ru"):
    if language == "en":
        keyboard = [
            ["⚽ Football", "🏀 NBA"],
            ["⚽ Analyze Match"],
            ["🏆 Top 3 Today", "🌍 World Cup 2026"],
            ["📈 Results"],
            ["🏆 Channel", "💎 FLUX PRO"],
            ["👤 My Profile"],
            ["ℹ️ About", "📊 Status"],
            ["🌐 Language"],
        ]
    else:
        keyboard = [
            ["⚽ Футбол", "🏀 NBA"],
            ["⚽ Анализ матча"],
            ["🏆 ТОП-3 дня", "🌍 ЧМ-2026"],
            ["📈 Результаты"],
            ["🏆 Канал", "💎 FLUX PRO"],
            ["👤 Мой профиль"],
            ["ℹ️ О проекте", "📊 Статус"],
            ["🌐 Язык"],
        ]
    return {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}


def normalize_text(text):
    return str(text).replace("—", "-").replace("–", "-").replace("−", "-").strip()


def detect_match(line):
    line = normalize_text(line)
    for separator in [" - ", " vs ", " VS ", " Vs ", " v ", " V ", "-"]:
        if separator not in line:
            continue
        parts = line.split(separator, 1)
        if len(parts) == 2:
            team1, team2 = parts[0].strip(), parts[1].strip()
            if team1 and team2:
                return team1, team2
    return None, None


def detect_matches(text):
    matches = []
    for line in str(text).splitlines():
        team1, team2 = detect_match(line.strip())
        if team1 and team2:
            matches.append((team1, team2))
    return matches


def start_message(language="ru"):
    if language == "en":
        return (
            "👋 Welcome! I am FLUX AI Sports PRO v3.1\n\n"
            "⚽ Football analysis\n🏀 NBA analysis\n🏆 Top 3 of the day\n"
            "🌍 World Cup analysis\n📈 Results\n💎 FLUX PRO\n\n"
            f"FREE: {FREE_DAILY_LIMIT} analyses per day\nPRO: unlimited\n\n"
            "Choose a sport, then send a matchup."
        )
    return (
        "👋 Привет! Я FLUX AI Sports PRO v3.1\n\n"
        "⚽ Анализ футбола\n🏀 Анализ NBA\n🏆 ТОП-3 дня\n"
        "🌍 Анализ матчей ЧМ\n📈 Результаты\n💎 FLUX PRO\n\n"
        f"FREE: {FREE_DAILY_LIMIT} анализов в день\nPRO: безлимит\n\n"
        "Выбери вид спорта и отправь матч."
    )


def help_message(language="ru"):
    if language == "en":
        return (
            "Choose a sport first:\n\n⚽ Football:\nReal Madrid - Barcelona\n\n"
            "🏀 NBA:\nLakers - Celtics\n\nYou can send several matchups, one per line."
        )
    return (
        "Сначала выбери вид спорта:\n\n⚽ Футбол:\nReal Madrid - Barcelona\n\n"
        "🏀 NBA:\nLakers - Celtics\n\nМожно отправить несколько матчей списком."
    )


def about_message(language="ru"):
    if language == "en":
        return (
            "ℹ️ FLUX AI is an AI-powered sports analysis bot.\n\n"
            "It analyzes football and NBA matchups using recent form, probabilities, totals and model insights.\n\n"
            "Predictions are informational and do not guarantee results."
        )
    return (
        "ℹ️ FLUX AI — AI-бот для анализа спорта.\n\n"
        "Бот анализирует футбол и NBA, учитывая форму команд, вероятности, тоталы и выводы модели.\n\n"
        "Прогноз не является гарантией результата."
    )


def status_message(language="ru"):
    if language == "en":
        return (
            "✅ FLUX AI Sports is running.\n\nVersion: PRO v3.1\n"
            "Sports: Football + NBA\nMode: Public Beta\n"
            f"Channel: {CHANNEL_USERNAME}\nStatus: Online"
        )
    return (
        "✅ FLUX AI Sports работает.\n\nВерсия: PRO v3.1\n"
        "Спорт: Футбол + NBA\nРежим: Public Beta\n"
        f"Канал: {CHANNEL_USERNAME}\nСтатус: Online"
    )


def admin_panel_message(language="ru"):
    stats = get_admin_stats()
    if language == "en":
        return (
            "🔐 FLUX AI ADMIN\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total users: {stats['total_users']}\n"
            f"💎 Active PRO: {stats['active_pro']}\n"
            f"🧾 Total payments: {stats['total_payments']}\n\n"
            "📊 Statistics update automatically."
        )
    return (
        "🔐 FLUX AI ADMIN\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"💎 Активных PRO: {stats['active_pro']}\n"
        f"🧾 Всего оплат: {stats['total_payments']}\n\n"
        "📊 Статистика обновляется автоматически."
    )


def profile_message(user_id, language="ru"):
    user = get_user(user_id)
    if not user:
        return "👤 Profile not found. Press /start." if language == "en" else "👤 Профиль не найден. Нажми /start."

    pro_active = is_pro(user_id)
    sport = get_user_sport(user_id)
    usage = get_today_usage(user_id)

    if language == "en":
        pro_status = "✅ Active" if pro_active else "❌ Inactive"
        sport_text = "🏀 NBA" if sport == "nba" else "⚽ Football"
        limit_text = "Unlimited" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} today"
        return (
            "👤 MY PROFILE\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: {user_id}\n\n💎 FLUX PRO: {pro_status}\n"
            f"🎯 Selected sport: {sport_text}\n\n📊 Statistics:\n"
            f"• Analyses today: {limit_text}\n• Winning predictions: coming soon\n\n🚀 FLUX AI v3.1"
        )

    pro_status = "✅ Активен" if pro_active else "❌ Не активен"
    sport_text = "🏀 NBA" if sport == "nba" else "⚽ Футбол"
    limit_text = "Безлимит" if pro_active else f"{usage}/{FREE_DAILY_LIMIT} сегодня"
    return (
        "👤 МОЙ ПРОФИЛЬ\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: {user_id}\n\n💎 FLUX PRO: {pro_status}\n"
        f"🎯 Выбранный спорт: {sport_text}\n\n📊 Статистика:\n"
        f"• Анализы сегодня: {limit_text}\n• Победных прогнозов: скоро\n\n🚀 FLUX AI v3.1"
    )


def channel_message(language="ru"):
    if language == "en":
        return (
            "🏆 FLUX AI DAILY\n\nOfficial FLUX AI channel.\n\n"
            "⚽ Football predictions\n🏀 NBA predictions\n📊 AI sports analysis\n💎 FLUX PRO news\n\n"
            f"📢 Subscribe: {CHANNEL_URL}"
        )
    return (
        "🏆 FLUX AI DAILY\n\nОфициальный канал FLUX AI.\n\n"
        "⚽ Прогнозы на футбол\n🏀 Прогнозы на NBA\n📊 AI-анализ спорта\n💎 Новости FLUX PRO\n\n"
        f"📢 Подписаться: {CHANNEL_URL}"
    )


def results_message(language="ru"):
    if language == "en":
        return "📈 FLUX AI Results\n\nPublic result tracking is being prepared.\n\nPredictions are informational and do not guarantee results."
    return "📈 FLUX AI Results\n\nПубличная статистика результатов готовится.\n\nПрогноз не является гарантией результата."


def worldcup_message(language="ru"):
    if language == "en":
        return "🌍 FLUX AI | World Cup\n\nFootball mode has been selected.\n\nSend any match:\nTeam 1 - Team 2"
    return "🌍 FLUX AI | Чемпионат мира\n\nВыбран режим футбола.\n\nОтправь любой матч:\nКоманда 1 - Команда 2"


def today_top_3_message(language="ru"):
    if language == "en":
        return f"🏆 FLUX AI DAILY\n\nThe current Top 3 is published in our channel.\n\n📢 {CHANNEL_URL}"
    return f"🏆 FLUX AI DAILY\n\nАктуальный ТОП-3 публикуется в нашем канале.\n\n📢 {CHANNEL_URL}"


def pro_message(language="ru"):
    if language == "en":
        return (
            "💎 FLUX AI PRO\n\n✅ Unlimited sports analysis\n✅ Football and NBA\n"
            "✅ Extended statistics\n✅ Daily Top 3\n✅ New PRO features\n\n"
            f"Price: ⭐{PRO_PRICE_STARS} / {PRO_DAYS} days\n\n👇 Use the payment invoice below."
        )
    return (
        "💎 FLUX AI PRO\n\n✅ Безлимитный анализ спорта\n✅ Футбол и NBA\n"
        "✅ Расширенная статистика\n✅ ТОП-3 дня\n✅ Новые PRO-функции\n\n"
        f"Стоимость: ⭐{PRO_PRICE_STARS} / {PRO_DAYS} дней\n\n👇 Используйте счёт оплаты ниже."
    )


def payment_success_message(language="ru"):
    if language == "en":
        return f"🎉 FLUX AI PRO activated!\n\n💎 Status: PRO\n📅 Period: {PRO_DAYS} days\n✅ Unlimited analysis is available."
    return f"🎉 FLUX AI PRO активирован!\n\n💎 Статус: PRO\n📅 Срок: {PRO_DAYS} дней\n✅ Безлимитный анализ доступен."


def analyze_match_text(text, language="ru"):
    from engine.analyzer import analyze_and_format
    matches = detect_matches(text)
    if not matches:
        return help_message(language)
    if len(matches) == 1:
        return analyze_and_format(matches[0][0], matches[0][1], language)

    results = []
    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            results.append(f"#{index}\n{analyze_and_format(team1, team2, language)}")
        except Exception as error:
            print("MULTI_ANALYSIS_ERROR:", repr(error), flush=True)
            message = f"⚠️ Could not analyze: {team1} - {team2}" if language == "en" else f"⚠️ Не получилось: {team1} - {team2}"
            results.append(f"#{index}\n{message}")
    return "\n\n".join(results)


def analyze_nba_text(text, language="ru"):
    from engine.nba_analyzer import analyze_and_format_nba
    matches = detect_matches(text)
    if not matches:
        return "🏀 Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks" if language == "en" else "🏀 Напиши матч NBA:\n\nLakers - Celtics\nWarriors - Knicks"
    if len(matches) == 1:
        return analyze_and_format_nba(matches[0][0], matches[0][1], language)

    results = []
    for index, (team1, team2) in enumerate(matches[:5], start=1):
        try:
            results.append(f"#{index}\n{analyze_and_format_nba(team1, team2, language)}")
        except Exception as error:
            print("MULTI_NBA_ANALYSIS_ERROR:", repr(error), flush=True)
            message = f"⚠️ Could not analyze: {team1} - {team2}" if language == "en" else f"⚠️ Не получилось: {team1} - {team2}"
            results.append(f"#{index}\n{message}")
    return "\n\n".join(results)


def handle_analysis(chat_id, user_id, text, language="ru"):
    matches = detect_matches(text)
    if not matches:
        send_message(chat_id, help_message(language), reply_markup=main_menu(language))
        return

    if not is_pro(user_id):
        used = get_today_usage(user_id)
        remaining = FREE_DAILY_LIMIT - used
        if remaining <= 0:
            send_message(chat_id, free_limit_message(language), reply_markup=main_menu(language))
            return
        if len(matches) > remaining:
            message_text = (
                f"🔒 Free analyses remaining today: {remaining}\n\nSend fewer matchups or activate FLUX PRO."
                if language == "en"
                else f"🔒 У вас осталось бесплатных анализов сегодня: {remaining}\n\nОтправьте меньше матчей или оформите FLUX PRO."
            )
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return

    sport_mode = get_user_sport(user_id)
    if len(matches) > 1:
        analyzing_text = f"⏳ Analyzing {len(matches)} matchups..." if language == "en" else f"⏳ Анализирую {len(matches)} матчей..."
    elif sport_mode == "nba":
        analyzing_text = "⏳ Analyzing the NBA game..." if language == "en" else "⏳ Анализирую матч NBA..."
    else:
        analyzing_text = "⏳ Analyzing the football match..." if language == "en" else "⏳ Анализирую футбольный матч..."

    send_message(chat_id, analyzing_text, reply_markup=main_menu(language))

    try:
        if sport_mode == "nba":
            answer = analyze_nba_text(text, language)
            sport_prefix = "NBA"
        else:
            answer = analyze_match_text(text, language)
            sport_prefix = "FOOTBALL"

        send_message(chat_id, answer, reply_markup=main_menu(language))

        for team1, team2 in matches:
            save_prediction(user_id, f"[{sport_prefix}] {team1} - {team2}", answer)
            if not is_pro(user_id):
                increase_today_usage(user_id)

    except Exception as error:
        print("MATCH_ANALYSIS_ERROR:", repr(error), flush=True)
        if sport_mode == "nba":
            error_text = "⚠️ Could not complete the NBA analysis.\n\nCheck the format:\nLakers - Celtics" if language == "en" else "⚠️ Не получилось сделать анализ NBA.\n\nПроверь формат:\nLakers - Celtics"
        else:
            error_text = "⚠️ Could not complete the football analysis.\n\nCheck the format:\nReal Madrid - Barcelona" if language == "en" else "⚠️ Не получилось сделать футбольный анализ.\n\nПроверь формат:\nReal Madrid - Barcelona"
        send_message(chat_id, error_text, reply_markup=main_menu(language))


def parse_invoice_user_id(invoice_payload):
    prefix = "flux_pro_30_days:"
    invoice_payload = str(invoice_payload)
    if not invoice_payload.startswith(prefix):
        return None
    try:
        return int(invoice_payload[len(prefix):])
    except (TypeError, ValueError):
        return None


def process_pre_checkout_query(pre_checkout_query):
    query_id = pre_checkout_query.get("id")
    payer_id = pre_checkout_query.get("from", {}).get("id")
    language = get_user_language(payer_id)
    invoice_payload = pre_checkout_query.get("invoice_payload", "")
    currency = pre_checkout_query.get("currency", "")
    total_amount = pre_checkout_query.get("total_amount", 0)
    payload_user_id = parse_invoice_user_id(invoice_payload)
    is_valid = query_id and payer_id and payload_user_id == payer_id and currency == "XTR" and int(total_amount) == PRO_PRICE_STARS
    error_message = None
    if not is_valid:
        error_message = "Payment verification failed. Please create a new invoice." if language == "en" else "Не удалось проверить платёж. Создайте новый счёт."
    answer_pre_checkout_query(query_id, is_valid, error_message)


def process_successful_payment(message):
    payment = message.get("successful_payment", {})
    user = message.get("from", {})
    chat = message.get("chat", {})
    user_id, chat_id = user.get("id"), chat.get("id")
    language = get_user_language(user_id)
    payload_user_id = parse_invoice_user_id(payment.get("invoice_payload", ""))
    currency = payment.get("currency", "")
    total_amount = payment.get("total_amount", 0)
    payment_is_valid = user_id and chat_id and payload_user_id == user_id and currency == "XTR" and int(total_amount) == PRO_PRICE_STARS

    if not payment_is_valid:
        error_text = "⚠️ Payment data failed verification." if language == "en" else "⚠️ Данные платежа не прошли проверку."
        send_message(chat_id, error_text, reply_markup=main_menu(language))
        return

    add_user(user)
    activate_pro(user_id, days=PRO_DAYS)
    save_payment(user_id, provider="telegram_stars", amount=total_amount, currency="XTR", status="paid")
    send_message(chat_id, payment_success_message(language), reply_markup=main_menu(language))


def process_callback_query(callback_query):
    callback_id = callback_query.get("id")
    user = callback_query.get("from", {})
    user_id = user.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")

    if not user_id or not chat_id:
        if callback_id:
            answer_callback_query(callback_id)
        return

    add_user(user)
    if data == "lang_en":
        set_user_language(user_id, "en")
        answer_callback_query(callback_id, "Language changed to English.")
        send_message(chat_id, start_message("en"), reply_markup=main_menu("en"))
        return
    if data == "lang_ru":
        set_user_language(user_id, "ru")
        answer_callback_query(callback_id, "Язык изменён на русский.")
        send_message(chat_id, start_message("ru"), reply_markup=main_menu("ru"))
        return
    answer_callback_query(callback_id)


@app.route("/")
def home():
    return "FLUX AI Sports PRO v3.1 is running!"


@app.route("/health")
def health():
    return "OK"


@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return "OK", 200

        if data.get("callback_query"):
            process_callback_query(data["callback_query"])
            return "OK", 200
        if data.get("pre_checkout_query"):
            process_pre_checkout_query(data["pre_checkout_query"])
            return "OK", 200

        message = data.get("message")
        if not message:
            return "OK", 200
        if message.get("successful_payment"):
            process_successful_payment(message)
            return "OK", 200

        chat_id = message.get("chat", {}).get("id")
        user = message.get("from", {})
        user_id = user.get("id")
        text = (message.get("text") or "").strip()

        if not chat_id:
            return "OK", 200
        if user_id:
            add_user(user)

        language = get_user_language(user_id)

        if text == "/start":
            send_message(chat_id, "⚡ Welcome to Flux AI\nChoose your language.\n\n⚡ Добро пожаловать в Flux AI\nВыберите язык.", reply_markup=language_keyboard())
            return "OK", 200

        if text in ["/language", "🌐 Language", "🌐 Язык"]:
            send_message(chat_id, "Choose your language.\n\nВыберите язык.", reply_markup=language_keyboard())
            return "OK", 200

        if text in ["⚽ Футбол", "⚽ Football"]:
            set_user_sport(user_id, "football")
            message_text = "⚽ Football mode selected.\n\nSend a match:\nReal Madrid - Barcelona" if language == "en" else "⚽ Выбран режим футбола.\n\nНапиши матч:\nReal Madrid - Barcelona"
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if text == "🏀 NBA":
            set_user_sport(user_id, "nba")
            message_text = "🏀 NBA mode selected.\n\nSend a game:\nLakers - Celtics\n\nThe first team is treated as the home team." if language == "en" else "🏀 Выбран режим NBA.\n\nНапиши матч:\nLakers - Celtics\n\nПервая команда считается хозяином площадки."
            send_message(chat_id, message_text, reply_markup=main_menu(language))
            return "OK", 200

        if not text:
            send_message(chat_id, help_message(language), reply_markup=main_menu(language))
            return "OK", 200

        if text in ["⚽ Анализ матча", "⚽ Analyze Match"]:
            sport_mode = get_user_sport(user_id)
            if sport_mode == "nba":
                prompt = "🏀 Send an NBA game:\n\nLakers - Celtics\nWarriors - Knicks" if language == "en" else "🏀 Напиши матч NBA:\n\nLakers - Celtics\nWarriors - Knicks"
            else:
                prompt = "⚽ Send a match:\n\nReal Madrid - Barcelona" if language == "en" else "⚽ Напиши матч:\n\nReal Madrid - Barcelona"
            send_message(chat_id, prompt, reply_markup=main_menu(language))
            return "OK", 200

        button_commands = {
            "🏆 ТОП-3 дня": "/today", "🏆 Top 3 Today": "/today",
            "🌍 ЧМ-2026": "/worldcup", "🌍 World Cup 2026": "/worldcup",
            "📈 Результаты": "/results", "📈 Results": "/results",
            "🏆 Канал": "/channel", "🏆 Channel": "/channel",
            "💎 FLUX PRO": "/pro",
            "👤 Мой профиль": "/profile", "👤 My Profile": "/profile",
            "ℹ️ О проекте": "/about", "ℹ️ About": "/about",
            "📊 Статус": "/status", "📊 Status": "/status",
        }
        text = button_commands.get(text, text)

        if text in ["/help", "/analyze"]:
            send_message(chat_id, help_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/about":
            send_message(chat_id, about_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/status":
            send_message(chat_id, status_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/profile":
            send_message(chat_id, profile_message(user_id, language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/admin":
            if user_id != ADMIN_TELEGRAM_ID:
                denied = "⛔ Access denied." if language == "en" else "⛔ Доступ запрещён."
                send_message(chat_id, denied, reply_markup=main_menu(language))
                return "OK", 200
            send_message(chat_id, admin_panel_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/channel":
            button_text = "🏆 Open channel" if language == "en" else "🏆 Открыть канал"
            send_message(chat_id, channel_message(language), reply_markup={"inline_keyboard": [[{"text": button_text, "url": CHANNEL_URL}]]})
            return "OK", 200
        if text == "/worldcup":
            set_user_sport(user_id, "football")
            send_message(chat_id, worldcup_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/results":
            send_message(chat_id, results_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/today":
            send_message(chat_id, today_top_3_message(language), reply_markup=main_menu(language))
            return "OK", 200
        if text == "/pro":
            try:
                send_message(chat_id, pro_message(language), reply_markup=main_menu(language))
                send_stars_invoice(
                    bot_token=BOT_TOKEN,
                    chat_id=chat_id,
                    user_id=user_id,
                    stars_price=PRO_PRICE_STARS,
                    language=language,
                )
            except Exception as error:
                print("PRO_PAYMENT_ERROR:", repr(error), flush=True)
                error_text = "⚠️ Could not open Telegram Stars payment." if language == "en" else "⚠️ Не получилось открыть оплату Telegram Stars."
                send_message(chat_id, error_text, reply_markup=main_menu(language))
            return "OK", 200

        handle_analysis(chat_id, user_id, text, language)
        return "OK", 200

    except Exception as error:
        print("TELEGRAM_WEBHOOK_ERROR:", repr(error), flush=True)
        return "OK", 200


def set_webhook():
    webhook_url = f"{PUBLIC_URL}/telegram/{BOT_TOKEN}"
    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": webhook_url,
                "drop_pending_updates": False,
                "allowed_updates": ["message", "callback_query", "pre_checkout_query"],
            },
        )
        print("WEBHOOK_SET:", result, flush=True)
    except Exception as error:
        print("WEBHOOK_SET_ERROR:", repr(error), flush=True)


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
