import hashlib


def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def stable_number(text, minimum, maximum):
    digest = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()
    number = int(digest[:8], 16)

    return minimum + number % (maximum - minimum + 1)


def analyze_tennis_match(player1, player2, language="ru"):
    seed1 = stable_number(player1, 58, 88)
    seed2 = stable_number(player2, 58, 88)

    power1 = clamp(seed1, 45, 95)
    power2 = clamp(seed2, 45, 95)

    total_power = power1 + power2

    probability1 = clamp(
        power1 / total_power * 100,
        20,
        80,
    )
    probability2 = 100 - probability1

    if probability1 >= probability2:
        favorite = player1
        favorite_probability = probability1
    else:
        favorite = player2
        favorite_probability = probability2

    difference = abs(power1 - power2)

    confidence = clamp(
        48 + difference * 1.4,
        45,
        82,
    )

    if confidence >= 72:
        risk = "low"
    elif confidence >= 58:
        risk = "medium"
    else:
        risk = "high"

    predicted_sets = "2:0" if difference >= 12 else "2:1"

    result = {
        "player1": player1,
        "player2": player2,
        "power1": power1,
        "power2": power2,
        "probability1": probability1,
        "probability2": probability2,
        "favorite": favorite,
        "favorite_probability": favorite_probability,
        "confidence": confidence,
        "risk": risk,
        "predicted_sets": predicted_sets,
        "data_quality": 25,
    }

    return format_tennis_analysis(result, language)


def format_tennis_analysis(result, language="ru"):
    risk_ru = {
        "low": "Низкий",
        "medium": "Средний",
        "high": "Высокий",
    }

    risk_en = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }

    if language == "en":
        return f"""🎾 FLUX AI TENNIS PRO
━━━━━━━━━━━━━━━━━━━━

🏟 Match
{result["player1"]} — {result["player2"]}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

━━━━━━━━━━━━━━━━━━━━

📊 Win Probability

{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

━━━━━━━━━━━━━━━━━━━━

⭐ Preliminary Prediction

👉 {result["favorite"]} to Win

🎯 Probability:
{result["favorite_probability"]}%

🧠 AI Confidence:
{result["confidence"]}%

━━━━━━━━━━━━━━━━━━━━

🎾 Predicted Set Score:
{result["predicted_sets"]}

⚠️ Risk Level:
{risk_en[result["risk"]]}

🧪 Data Quality:
{result["data_quality"]}%

━━━━━━━━━━━━━━━━━━━━

⚠️ Tennis AI is currently in Beta.
The prediction uses the preliminary FLUX model until the live tennis API is connected.

Predictions are informational and do not guarantee results.
"""

    return f"""🎾 FLUX AI TENNIS PRO
━━━━━━━━━━━━━━━━━━━━

🏟 Матч
{result["player1"]} — {result["player2"]}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

━━━━━━━━━━━━━━━━━━━━

📊 Вероятность победы

{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

━━━━━━━━━━━━━━━━━━━━

⭐ Предварительный прогноз

👉 Победа: {result["favorite"]}

🎯 Вероятность:
{result["favorite_probability"]}%

🧠 AI Confidence:
{result["confidence"]}%

━━━━━━━━━━━━━━━━━━━━

🎾 Вероятный счёт по сетам:
{result["predicted_sets"]}

⚠️ Риск:
{risk_ru[result["risk"]]}

🧪 Качество данных:
{result["data_quality"]}%

━━━━━━━━━━━━━━━━━━━━

⚠️ Tennis AI сейчас работает в Beta-режиме.
До подключения теннисного API используется предварительная модель FLUX.

Прогноз носит информационный характер и не гарантирует результат.
"""
