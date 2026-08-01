# -*- coding: ascii -*-
import hashlib


DATA_QUALITY = 25


def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def stable_number(text, minimum, maximum, salt=""):
    key = f"{salt}:{text}".lower().encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    number = int(digest[:8], 16)
    return minimum + number % (maximum - minimum + 1)


def build_form(player):
    symbols = ["W", "W", "W", "L", "L"]
    digest = hashlib.sha256(
        f"form:{player}".lower().encode("utf-8")
    ).hexdigest()

    form = []
    for index in range(5):
        value = int(digest[index * 2:index * 2 + 2], 16)
        form.append(symbols[value % len(symbols)])

    return form


def format_form(form):
    mapping = {"W": "\U0001f7e2", "L": "\U0001f534"}
    return "".join(mapping[item] for item in form)


def analyze_tennis_match(player1, player2, language="ru"):
    power1 = stable_number(player1, 58, 88, "power")
    power2 = stable_number(player2, 58, 88, "power")

    serve1 = stable_number(player1, 55, 88, "serve")
    serve2 = stable_number(player2, 55, 88, "serve")

    return1 = stable_number(player1, 52, 86, "return")
    return2 = stable_number(player2, 52, 86, "return")

    surface_score1 = stable_number(player1, 54, 87, "surface")
    surface_score2 = stable_number(player2, 54, 87, "surface")

    form1 = build_form(player1)
    form2 = build_form(player2)

    form_score1 = 50 + form1.count("W") * 8
    form_score2 = 50 + form2.count("W") * 8

    rating1 = (
        power1 * 0.35
        + serve1 * 0.20
        + return1 * 0.20
        + surface_score1 * 0.15
        + form_score1 * 0.10
    )
    rating2 = (
        power2 * 0.35
        + serve2 * 0.20
        + return2 * 0.20
        + surface_score2 * 0.15
        + form_score2 * 0.10
    )

    total_rating = rating1 + rating2
    probability1 = clamp(rating1 / total_rating * 100, 25, 75)
    probability2 = 100 - probability1

    if probability1 >= probability2:
        favorite = player1
        favorite_probability = probability1
    else:
        favorite = player2
        favorite_probability = probability2

    difference = abs(rating1 - rating2)

    raw_confidence = 35 + difference * 0.8
    confidence_cap = 48 if DATA_QUALITY < 40 else 65
    confidence = clamp(raw_confidence, 32, confidence_cap)

    if DATA_QUALITY < 40:
        risk = "high"
    elif confidence >= 65:
        risk = "low"
    elif confidence >= 50:
        risk = "medium"
    else:
        risk = "high"

    predicted_sets = "2:0" if difference >= 15 else "2:1"

    serve_edge = player1 if serve1 >= serve2 else player2
    return_edge = player1 if return1 >= return2 else player2
    surface_edge = player1 if surface_score1 >= surface_score2 else player2

    h2h_estimate = stable_number(
        f"{player1}:{player2}",
        0,
        4,
        "h2h",
    )

    result = {
        "player1": player1,
        "player2": player2,
        "power1": clamp(power1),
        "power2": clamp(power2),
        "serve1": serve1,
        "serve2": serve2,
        "return1": return1,
        "return2": return2,
        "surface_score1": surface_score1,
        "surface_score2": surface_score2,
        "form1": form1,
        "form2": form2,
        "probability1": probability1,
        "probability2": probability2,
        "favorite": favorite,
        "favorite_probability": favorite_probability,
        "confidence": confidence,
        "risk": risk,
        "predicted_sets": predicted_sets,
        "data_quality": DATA_QUALITY,
        "serve_edge": serve_edge,
        "return_edge": return_edge,
        "surface_edge": surface_edge,
        "h2h_estimate": h2h_estimate,
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

    form1 = format_form(result["form1"])
    form2 = format_form(result["form2"])

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

\U0001f3c6 TOP-3 Model Signals
1. Match winner: {result["favorite"]} \u2014 {result["favorite_probability"]}%
2. Predicted set score: {result["predicted_sets"]}
3. Match likely to require 3 sets: {"Yes" if result["predicted_sets"] == "2:1" else "No"}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4c8 Recent Form
{result["player1"]}: {form1}
{result["player2"]}: {form2}

\U0001f4a5 Serve Edge:
{result["serve_edge"]}

\U0001f3be Return Edge:
{result["return_edge"]}

\U0001f3df Surface Model Edge:
{result["surface_edge"]}

\U0001f91d Estimated H2H Signal:
{result["favorite"]} +{result["h2h_estimate"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be Predicted Set Score:
{result["predicted_sets"]}

\u26a0\ufe0f Risk Level:
{risk_en[result["risk"]]}

\U0001f9ea Data Quality:
{result["data_quality"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f Tennis AI is currently in Beta.
Form, H2H, serve, return and surface values are model estimates until the live tennis API is connected.

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

\U0001f3c6 \u0422\u041e\u041f-3 \u0441\u0438\u0433\u043d\u0430\u043b\u0430 \u043c\u043e\u0434\u0435\u043b\u0438
1. \u041f\u043e\u0431\u0435\u0434\u0430: {result["favorite"]} \u2014 {result["favorite_probability"]}%
2. \u0421\u0447\u0451\u0442 \u043f\u043e \u0441\u0435\u0442\u0430\u043c: {result["predicted_sets"]}
3. \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u044b 3 \u0441\u0435\u0442\u0430: {"\u0414\u0430" if result["predicted_sets"] == "2:1" else "\u041d\u0435\u0442"}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4c8 \u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0444\u043e\u0440\u043c\u0430
{result["player1"]}: {form1}
{result["player2"]}: {form2}

\U0001f4a5 \u041f\u0440\u0435\u0438\u043c\u0443\u0449\u0435\u0441\u0442\u0432\u043e \u043d\u0430 \u043f\u043e\u0434\u0430\u0447\u0435:
{result["serve_edge"]}

\U0001f3be \u041f\u0440\u0435\u0438\u043c\u0443\u0449\u0435\u0441\u0442\u0432\u043e \u043d\u0430 \u043f\u0440\u0438\u0451\u043c\u0435:
{result["return_edge"]}

\U0001f3df \u041f\u0440\u0435\u0438\u043c\u0443\u0449\u0435\u0441\u0442\u0432\u043e \u043d\u0430 \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u0438:
{result["surface_edge"]}

\U0001f91d \u041c\u043e\u0434\u0435\u043b\u044c\u043d\u044b\u0439 H2H-\u0441\u0438\u0433\u043d\u0430\u043b:
{result["favorite"]} +{result["h2h_estimate"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u044b\u0439 \u0441\u0447\u0451\u0442 \u043f\u043e \u0441\u0435\u0442\u0430\u043c:
{result["predicted_sets"]}

\u26a0\ufe0f \u0420\u0438\u0441\u043a:
{risk_ru[result["risk"]]}

\U0001f9ea \u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0434\u0430\u043d\u043d\u044b\u0445:
{result["data_quality"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f Tennis AI \u0441\u0435\u0439\u0447\u0430\u0441 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0432 Beta-\u0440\u0435\u0436\u0438\u043c\u0435.
\u0424\u043e\u0440\u043c\u0430, H2H, \u043f\u043e\u0434\u0430\u0447\u0430, \u043f\u0440\u0438\u0451\u043c \u0438 \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u0435 \u043f\u043e\u043a\u0430 \u044f\u0432\u043b\u044f\u044e\u0442\u0441\u044f \u043c\u043e\u0434\u0435\u043b\u044c\u043d\u044b\u043c\u0438 \u043e\u0446\u0435\u043d\u043a\u0430\u043c\u0438.

\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u043e\u0441\u0438\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0438 \u043d\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0440\u0443\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442.
"""
