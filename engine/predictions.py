def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def calculate_totals(team1_form, team2_form):
    avg_goals = (
        team1_form.get("avg_goals_for", 0)
        + team2_form.get("avg_goals_for", 0)
        + team1_form.get("avg_goals_against", 0)
        + team2_form.get("avg_goals_against", 0)
    ) / 2

    over_2_5 = clamp(avg_goals * 23, 25, 80)
    under_2_5 = 100 - over_2_5

    btts_yes = clamp(avg_goals * 21, 25, 80)
    btts_no = 100 - btts_yes

    return {
        "avg_goals": round(avg_goals, 2),
        "over_2_5": over_2_5,
        "under_2_5": under_2_5,
        "btts_yes": btts_yes,
        "btts_no": btts_no,
    }


def calculate_risk_and_confidence(probabilities, totals):
    top_probability = max(
        probabilities["p1"],
        probabilities["draw"],
        probabilities["p2"],
    )

    confidence = clamp(top_probability / 10, 1, 10)

    if confidence >= 8:
        risk = "Низкий"
    elif confidence >= 6:
        risk = "Средний"
    else:
        risk = "Высокий"

    return {
        "risk": risk,
        "confidence": confidence,
    }


def choose_best_pick(probabilities, totals):
    picks = {
        "П1": probabilities["p1"],
        "X": probabilities["draw"],
        "П2": probabilities["p2"],
        "ТБ 2.5": totals["over_2_5"],
        "ТМ 2.5": totals["under_2_5"],
        "Обе забьют — Да": totals["btts_yes"],
        "Обе забьют — Нет": totals["btts_no"],
    }

    best_pick = max(picks, key=picks.get)

    return {
        "pick": best_pick,
        "value": picks[best_pick],
    }
