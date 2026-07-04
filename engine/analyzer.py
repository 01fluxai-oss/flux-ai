from providers.thesportsdb import get_match_data
from engine.v3_engine import analyze_v3


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]

    v3 = analyze_v3(
        team1=data.get("team1", team1),
        team2=data.get("team2", team2),
        team1_form=team1_form,
        team2_form=team2_form,
    )

    return {
        "team1": v3["team1"],
        "team2": v3["team2"],
        "source": data.get("source", "TheSportsDB"),
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_rating": v3["team1_rating"],
        "team2_rating": v3["team2_rating"],
        "probabilities": v3["probabilities"],
        "totals": v3["totals"],
        "best_pick": v3["best_pick"],
        "risk": v3["risk"],
        "confidence": v3["confidence"],
        "data_quality": v3["data_quality"],
    }


def format_analysis(result):
    team1 = result["team1"]
    team2 = result["team2"]

    return f"""
⚽ FLUX AI Sports Analysis

Матч:
{team1} — {team2}

📊 FLUX Rating:
{team1}: {result["team1_rating"]["rating"]}/100
{team2}: {result["team2_rating"]["rating"]}/100

⚔️ Attack:
{team1}: {result["team1_rating"]["attack"]}/100
{team2}: {result["team2_rating"]["attack"]}/100

🛡 Defense:
{team1}: {result["team1_rating"]["defense"]}/100
{team2}: {result["team2_rating"]["defense"]}/100

📈 Form:
{team1}: {result["team1_rating"]["form"]}/100
{team2}: {result["team2_rating"]["form"]}/100

📡 Data Quality:
{result["data_quality"]}/100

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
FLUX AI v3 оценивает матч через рейтинг формы, атаки, защиты, качество данных и вероятностную модель. Прогноз не является гарантией результата.
"""


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)
