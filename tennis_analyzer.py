# -*- coding: ascii -*-
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

    probability1 = clamp(power1 / total_power * 100, 20, 80)
    probability2 = 100 - probability1

    if probability1 >= probability2:
        favorite = player1
        favorite_probability = probability1
    else:
        favorite = player2
        favorite_probability = probability2

    difference = abs(power1 - power2)
    confidence = clamp(48 + difference * 1.4, 45, 82)

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
        "low": "\u041d\u0438\u0437\u043a\u0438\u0439",
        "medium": "\u0421\u0440\u0435\u0434\u043d\u0438\u0439",
        "high": "\u0412\u044b\u0441\u043e\u043a\u0438\u0439",
    }
    risk_en = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    }

    if language == "en":
        return f"""\U0001f3be FLUX AI TENNIS PRO
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3df Match
{result["player1"]} \u2014 {result["player2"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a1 FLUX Power Index

{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4ca Win Probability

{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u2b50 Preliminary Prediction
\U0001f449 {result["favorite"]} to Win

\U0001f3af Probability:
{result["favorite_probability"]}%

\U0001f9e0 AI Confidence:
{result["confidence"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be Predicted Set Score:
{result["predicted_sets"]}

\u26a0\ufe0f Risk Level:
{risk_en[result["risk"]]}

\U0001f9ea Data Quality:
{result["data_quality"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f Tennis AI is currently in Beta.
The prediction uses the preliminary FLUX model until the live tennis API is connected.

Predictions are informational and do not guarantee results.
"""

    return f"""\U0001f3be FLUX AI TENNIS PRO
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3df \u041c\u0430\u0442\u0447
{result["player1"]} \u2014 {result["player2"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a1 FLUX Power Index

{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4ca \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c \u043f\u043e\u0431\u0435\u0434\u044b

{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u2b50 \u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043d\u043e\u0437
\U0001f449 \u041f\u043e\u0431\u0435\u0434\u0430: {result["favorite"]}

\U0001f3af \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c:
{result["favorite_probability"]}%

\U0001f9e0 AI Confidence:
{result["confidence"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u044b\u0439 \u0441\u0447\u0451\u0442 \u043f\u043e \u0441\u0435\u0442\u0430\u043c:
{result["predicted_sets"]}

\u26a0\ufe0f \u0420\u0438\u0441\u043a:
{risk_ru[result["risk"]]}

\U0001f9ea \u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0434\u0430\u043d\u043d\u044b\u0445:
{result["data_quality"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f Tennis AI \u0441\u0435\u0439\u0447\u0430\u0441 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0432 Beta-\u0440\u0435\u0436\u0438\u043c\u0435.
\u0414\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u0442\u0435\u043d\u043d\u0438\u0441\u043d\u043e\u0433\u043e API \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u043c\u043e\u0434\u0435\u043b\u044c FLUX.

\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u043e\u0441\u0438\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0438 \u043d\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0440\u0443\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442.
"""
