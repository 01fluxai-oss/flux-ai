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
        "double_chance": v3.get("double_chance", {}),
        "predicted_score": v3.get("predicted_score", {}),
        "best_pick": v3["best_pick"],
        "risk": v3["risk"],
        "confidence": v3["confidence"],
        "data_quality": v3["data_quality"],
    }


def format_top_3(best_pick):
    top_3 = best_pick.get("top_3", [])

    if not top_3:
        return f"🥇 {best_pick['pick']} — {best_pick['value']}%"

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for index, item in enumerate(top_3[:3]):
        name, value = item
        lines.append(f"{medals[index]} {name} — {value}%")

    return "\n".join(lines)


def format_analysis(result):
    team1 = result["team1"]
    team2 = result["team2"]
    probabilities = result["probabilities"]
    totals = result["totals"]
    score = result.get("predicted_score", {}).get("score", "—")
    top_3_text = format_top_3(result["best_pick"])

    return f"""
⚽ FLUX AI PRO

🏆 Матч:
{team1} — {team2}

📊 FLUX Rating:
{team1}: {result["team1_rating"]["rating"]}/100
{team2}: {result["team2_rating"]["rating"]}/100

🎯 Вероятности:
П1 — {probabilities["p1"]}%
X — {probabilities["draw"]}%
П2 — {probabilities["p2"]}%

🏆 ТОП-3 рекомендации:
{top_3_text}

⚽ Голы:
ТБ 1.5 — {totals.get("over_1_5", "—")}%
ТБ 2.5 — {totals.get("over_2_5", "—")}%
ТБ 3.5 — {totals.get("over_3_5", "—")}%

🥅 Обе забьют:
Да — {totals["btts_yes"]}%
Нет — {totals["btts_no"]}%

🔮 Возможный счет:
{score}

📡 Качество данных:
{result["data_quality"]}/100

⚠️ Риск:
{result["risk"]}

🎯 Уверенность:
{result["confidence"]}/10

Источник:
{result["source"]}

Важно:
Прогноз не является гарантией результата.
"""


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)
