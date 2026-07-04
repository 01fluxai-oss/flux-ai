from providers.mock import get_match_data
from engine.flux_rating import calculate_flux_power
from engine.probability import calculate_match_probabilities
from engine.predictions import (
    calculate_totals,
    calculate_risk_and_confidence,
    choose_best_pick,
)


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]
    h2h = data.get("h2h", {})

    team1_power = calculate_flux_power(team1_form, home_advantage=True)
    team2_power = calculate_flux_power(team2_form, home_advantage=False)

    probabilities = calculate_match_probabilities(team1_power, team2_power)
    totals = calculate_totals(team1_form, team2_form)
    risk_confidence = calculate_risk_and_confidence(probabilities, totals)
    best_pick = choose_best_pick(probabilities, totals)

    return {
        "team1": team1,
        "team2": team2,
        "source": data.get("source", "mock"),
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h": h2h,
        "team1_power": team1_power,
        "team2_power": team2_power,
        "probabilities": probabilities,
        "totals": totals,
        "risk": risk_confidence["risk"],
        "confidence": risk_confidence["confidence"],
        "best_pick": best_pick,
    }


def format_analysis(result):
    team1 = result["team1"]
    team2 = result["team2"]

    return f"""
⚽ FLUX AI Sports Analysis

Матч:
{team1} — {team2}

📊 FLUX Power:
{team1}: {result["team1_power"]["power"]}/100
{team2}: {result["team2_power"]["power"]}/100

⚔️ Attack Index:
{team1}: {result["team1_power"]["attack"]}/100
{team2}: {result["team2_power"]["attack"]}/100

🛡 Defense Index:
{team1}: {result["team1_power"]["defense"]}/100
{team2}: {result["team2_power"]["defense"]}/100

🧠 Momentum:
{team1}: {result["team1_power"]["momentum"]}/100
{team2}: {result["team2_power"]["momentum"]}/100

🎯 Вероятности FLUX:
П1 — {result["probabilities"]["p1"]}%
X — {result["probabilities"]["draw"]}%
П2 — {result["probabilities"]["p2"]}%

⚽ Тотал 2.5:
Больше — {result["totals"]["over_2_5"]}%
Меньше — {result["totals"]["under_2_5"]}%

🥅 Обе забьют:
Да — {result["totals"]["btts_yes"]}%
Нет — {result["totals"]["btts_no"]}%

🔥 Лучший вариант:
{result["best_pick"]["pick"]} — {result["best_pick"]["value"]}%

⚠️ Риск:
{result["risk"]}

🎯 Уверенность:
{result["confidence"]}/10

Источник данных:
{result["source"]}

Вывод:
FLUX AI рассчитывает прогноз на основе формы, атаки, обороны, momentum и вероятностной модели. Прогноз не является гарантией результата.
"""


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)
