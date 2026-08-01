# -*- coding: ascii -*-
import hashlib

from providers.tennis_provider import TennisAPIError, get_real_tennis_data


FALLBACK_DATA_QUALITY = 25


def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def stable_number(text, minimum, maximum, salt=""):
    key = f"{salt}:{text}".lower().encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    number = int(digest[:8], 16)
    return minimum + number % (maximum - minimum + 1)


def safe_rate(wins, losses):
    wins = int(wins or 0)
    losses = int(losses or 0)
    total = wins + losses

    if total <= 0:
        return None

    return round(wins / total * 100)


def rank_score(rank):
    if not rank:
        return 50

    rank = max(1, int(rank))
    return clamp(100 - min(rank, 200) * 0.35, 30, 98)


def recent_score(recent):
    win_rate = recent.get("win_rate")

    if win_rate is None:
        return 50

    return clamp(win_rate, 25, 90)


def surface_score(stats, surface="hard"):
    won = int(stats.get(f"{surface}_won") or 0)
    lost = int(stats.get(f"{surface}_lost") or 0)
    rate = safe_rate(won, lost)

    if rate is None:
        return 50

    return clamp(rate, 25, 90)


def build_real_form(recent):
    form = []

    for item in recent.get("matches", [])[:5]:
        form.append("W" if item.get("won") else "L")

    while len(form) < 5:
        form.append("?")

    return form


def format_form(form):
    mapping = {
        "W": "\U0001f7e2",
        "L": "\U0001f534",
        "?": "\u26aa",
    }
    return "".join(mapping[item] for item in form)


def verdict_key(probability):
    if probability <= 54:
        return "slight"
    if probability <= 64:
        return "preliminary"
    return "main"


def analyze_tennis_match(player1, player2, language="ru"):
    try:
        real_data = get_real_tennis_data(player1, player2)
        return analyze_with_real_data(real_data, language)
    except Exception as error:
        print("TENNIS_API_FALLBACK:", repr(error), flush=True)
        return analyze_with_fallback(player1, player2, language)


def analyze_with_real_data(real_data, language="ru"):
    player1 = real_data["player1"]
    player2 = real_data["player2"]

    recent1 = player1.get("recent") or {}
    recent2 = player2.get("recent") or {}

    stats1 = player1.get("season_stats") or {}
    stats2 = player2.get("season_stats") or {}

    power1 = round(
        rank_score(player1.get("rank")) * 0.45
        + recent_score(recent1) * 0.35
        + surface_score(stats1, "hard") * 0.20
    )
    power2 = round(
        rank_score(player2.get("rank")) * 0.45
        + recent_score(recent2) * 0.35
        + surface_score(stats2, "hard") * 0.20
    )

    total_power = max(power1 + power2, 1)
    probability1 = clamp(power1 / total_power * 100, 20, 80)
    probability2 = 100 - probability1

    if probability1 >= probability2:
        favorite = player1["player_name"]
        favorite_probability = probability1
    else:
        favorite = player2["player_name"]
        favorite_probability = probability2

    difference = abs(power1 - power2)
    data_quality = clamp(real_data.get("data_quality") or 0, 1, 100)

    confidence = clamp(
        30 + difference * 0.9 + data_quality * 0.35,
        30,
        88,
    )

    if data_quality < 45:
        confidence = min(confidence, 48)
        risk = "high"
    elif confidence >= 72:
        risk = "low"
    elif confidence >= 55:
        risk = "medium"
    else:
        risk = "high"

    predicted_sets = "2:0" if difference >= 14 else "2:1"

    h2h = real_data.get("h2h") or {}
    h2h_first = int(h2h.get("first_wins") or 0)
    h2h_second = int(h2h.get("second_wins") or 0)

    result = {
        "player1": player1["player_name"],
        "player2": player2["player_name"],
        "power1": power1,
        "power2": power2,
        "probability1": probability1,
        "probability2": probability2,
        "favorite": favorite,
        "favorite_probability": favorite_probability,
        "confidence": confidence,
        "risk": risk,
        "predicted_sets": predicted_sets,
        "data_quality": data_quality,
        "form1": build_real_form(recent1),
        "form2": build_real_form(recent2),
        "rank1": player1.get("rank"),
        "rank2": player2.get("rank"),
        "recent_win_rate1": recent1.get("win_rate"),
        "recent_win_rate2": recent2.get("win_rate"),
        "hard_rate1": surface_score(stats1, "hard"),
        "hard_rate2": surface_score(stats2, "hard"),
        "h2h_first": h2h_first,
        "h2h_second": h2h_second,
        "verdict": verdict_key(favorite_probability),
        "source": "API-Tennis",
        "is_fallback": False,
    }

    return format_tennis_analysis(result, language)


def analyze_with_fallback(player1, player2, language="ru"):
    power1 = stable_number(player1, 58, 88, "power")
    power2 = stable_number(player2, 58, 88, "power")

    total_power = power1 + power2
    probability1 = clamp(power1 / total_power * 100, 25, 75)
    probability2 = 100 - probability1

    if probability1 >= probability2:
        favorite = player1
        favorite_probability = probability1
    else:
        favorite = player2
        favorite_probability = probability2

    difference = abs(power1 - power2)
    confidence = clamp(35 + difference * 0.8, 32, 48)

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
        "risk": "high",
        "predicted_sets": "2:0" if difference >= 15 else "2:1",
        "data_quality": FALLBACK_DATA_QUALITY,
        "form1": ["?", "?", "?", "?", "?"],
        "form2": ["?", "?", "?", "?", "?"],
        "rank1": None,
        "rank2": None,
        "recent_win_rate1": None,
        "recent_win_rate2": None,
        "hard_rate1": None,
        "hard_rate2": None,
        "h2h_first": 0,
        "h2h_second": 0,
        "verdict": verdict_key(favorite_probability),
        "source": "FLUX fallback",
        "is_fallback": True,
    }

    return format_tennis_analysis(result, language)


def format_value(value, suffix=""):
    if value is None:
        return "\u2014"

    return f"{value}{suffix}"


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

    verdict_ru = {
        "slight": "\u041d\u0435\u0431\u043e\u043b\u044c\u0448\u043e\u0435 \u043f\u0440\u0435\u0438\u043c\u0443\u0449\u0435\u0441\u0442\u0432\u043e",
        "preliminary": "\u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u0440\u043e\u0433\u043d\u043e\u0437",
        "main": "\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u043f\u0440\u043e\u0433\u043d\u043e\u0437",
    }
    verdict_en = {
        "slight": "Slight Edge",
        "preliminary": "Preliminary Prediction",
        "main": "Main Prediction",
    }

    form1 = format_form(result["form1"])
    form2 = format_form(result["form2"])

    if language == "en":
        note = (
            "Live tennis data could not be loaded, so FLUX fallback was used."
            if result["is_fallback"]
            else "The model uses live API-Tennis data."
        )

        return f"""\U0001f3be FLUX AI TENNIS PRO
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3df Match
{result["player1"]} \u2014 {result["player2"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a1 FLUX Power Index
{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

\U0001f4ca Win Probability
{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u2b50 {verdict_en[result["verdict"]]}
\U0001f449 {result["favorite"]}

\U0001f3af Probability: {result["favorite_probability"]}%
\U0001f9e0 AI Confidence: {result["confidence"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4c8 Recent Form
{result["player1"]}: {form1}
{result["player2"]}: {form2}

\U0001f3c5 Ranking
{result["player1"]}: {format_value(result["rank1"], "#")}
{result["player2"]}: {format_value(result["rank2"], "#")}

\U0001f4ca Recent Win Rate
{result["player1"]}: {format_value(result["recent_win_rate1"], "%")}
{result["player2"]}: {format_value(result["recent_win_rate2"], "%")}

\U0001f3df Hard Court Rate
{result["player1"]}: {format_value(result["hard_rate1"], "%")}
{result["player2"]}: {format_value(result["hard_rate2"], "%")}

\U0001f91d H2H
{result["player1"]}: {result["h2h_first"]}
{result["player2"]}: {result["h2h_second"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be Predicted Set Score: {result["predicted_sets"]}
\u26a0\ufe0f Risk Level: {risk_en[result["risk"]]}
\U0001f9ea Data Quality: {result["data_quality"]}%
\U0001f4e1 Data Source: {result["source"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f {note}

Predictions are informational and do not guarantee results.
"""

    note = (
        "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c live-\u0434\u0430\u043d\u043d\u044b, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d FLUX fallback."
        if result["is_fallback"]
        else "\u041c\u043e\u0434\u0435\u043b\u044c \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b API-Tennis."
    )

    return f"""\U0001f3be FLUX AI TENNIS PRO
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3df \u041c\u0430\u0442\u0447
{result["player1"]} \u2014 {result["player2"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a1 FLUX Power Index
{result["player1"]}: {result["power1"]}/100
{result["player2"]}: {result["power2"]}/100

\U0001f4ca \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c \u043f\u043e\u0431\u0435\u0434\u044b
{result["player1"]}: {result["probability1"]}%
{result["player2"]}: {result["probability2"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u2b50 {verdict_ru[result["verdict"]]}
\U0001f449 {result["favorite"]}

\U0001f3af \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c: {result["favorite_probability"]}%
\U0001f9e0 AI Confidence: {result["confidence"]}%

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f4c8 \u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0444\u043e\u0440\u043c\u0430
{result["player1"]}: {form1}
{result["player2"]}: {form2}

\U0001f3c5 \u0420\u0435\u0439\u0442\u0438\u043d\u0433
{result["player1"]}: {format_value(result["rank1"], "#")}
{result["player2"]}: {format_value(result["rank2"], "#")}

\U0001f4ca \u041f\u0440\u043e\u0446\u0435\u043d\u0442 \u043f\u043e\u0431\u0435\u0434 \u0432 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0445 \u043c\u0430\u0442\u0447\u0430\u0445
{result["player1"]}: {format_value(result["recent_win_rate1"], "%")}
{result["player2"]}: {format_value(result["recent_win_rate2"], "%")}

\U0001f3df \u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c \u043d\u0430 hard
{result["player1"]}: {format_value(result["hard_rate1"], "%")}
{result["player2"]}: {format_value(result["hard_rate2"], "%")}

\U0001f91d H2H
{result["player1"]}: {result["h2h_first"]}
{result["player2"]}: {result["h2h_second"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\U0001f3be \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u044b\u0439 \u0441\u0447\u0451\u0442 \u043f\u043e \u0441\u0435\u0442\u0430\u043c: {result["predicted_sets"]}
\u26a0\ufe0f \u0420\u0438\u0441\u043a: {risk_ru[result["risk"]]}
\U0001f9ea \u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0434\u0430\u043d\u043d\u044b\u0445: {result["data_quality"]}%
\U0001f4e1 \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: {result["source"]}

\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u26a0\ufe0f {note}

\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043d\u043e\u0441\u0438\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u043e\u043d\u043d\u044b\u0439 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440 \u0438 \u043d\u0435 \u0433\u0430\u0440\u0430\u043d\u0442\u0438\u0440\u0443\u0435\u0442 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442.
"""
