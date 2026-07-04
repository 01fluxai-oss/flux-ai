from providers.thesportsdb import get_match_data
from engine.v2_engine import calculate_v2
from engine.predictions import (
    calculate_risk_and_confidence,
    choose_best_pick,
)


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]

    v2 = calculate_v2(
        team1=team1,
        team2=team2,
        team1_form=team1_form,
        team2_form=team2_form,
    )

    risk_confidence = calculate_risk_and_confidence(
        v2["probabilities"],
        v2["totals"],
    )

    best_pick = choose_best_pick(
        v2["probabilities"],
        v2["totals"],
    )

    return {
        "team1": team1,
        "team2": team2,
        "source": data.get("source", "TheSportsDB"),
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_power": v2["team1_power"],
        "team2_power": v2["team2_power"],
        "attack": v2["attack"],
        "defense": v2["defense"],
        "form": v2["form"],
        "probabilities": v2["probabilities"],
        "totals": v2["totals"],
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
{team1}: {result["team1_power"]}/100
{team2}: {result["team2_power"]}/100

⚔️ Attack Index:
{team1}: {result["attack"]["team1"]}/100
{team2}: {result["attack"]["team2"]}/100

🛡 Defense Index:
{team1}: {result["defense"]["team1"]}/100
{team2}: {result["defense"]["team2"]}/100

📈 Form Index:
{team1}: {result["form"]["team1"]}/100
{team2}: {result["form"]["team2"]}/100

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
FLUX AI v2 оценивает матч через атаку, защиту, форму и вероятностную модель. Прогноз не является гарантией результата.
"""


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)
