def calculate_probabilities(form1, form2, h2h):
    team1_strength = (
        form1["points"] * 2
        + form1["goals_for"] * 1.5
        - form1["goals_against"]
        + h2h["team1_wins"] * 2
    )

    team2_strength = (
        form2["points"] * 2
        + form2["goals_for"] * 1.5
        - form2["goals_against"]
        + h2h["team2_wins"] * 2
    )

    team1_strength = max(team1_strength, 1)
    team2_strength = max(team2_strength, 1)

    draw_strength = 18 + h2h["draws"] * 2

    total = team1_strength + team2_strength + draw_strength

    p1 = round(team1_strength / total * 100)
    p2 = round(team2_strength / total * 100)
    draw = 100 - p1 - p2

    return {
        "p1": p1,
        "draw": draw,
        "p2": p2,
    }


def calculate_totals(form1, form2):
    avg_goals = (
        form1["avg_goals_for"]
        + form1["avg_goals_against"]
        + form2["avg_goals_for"]
        + form2["avg_goals_against"]
    ) / 2

    over_2_5 = round(min(max(avg_goals / 3.2 * 100, 35), 80))
    under_2_5 = 100 - over_2_5

    btts_yes = round(min(max(avg_goals / 3.0 * 100, 35), 80))
    btts_no = 100 - btts_yes

    return {
        "avg_goals": round(avg_goals, 2),
        "over_2_5": over_2_5,
        "under_2_5": under_2_5,
        "btts_yes": btts_yes,
        "btts_no": btts_no,
    }


def flux_index(form, totals):
    score = (
        form["points"] * 4
        + form["goals_for"] * 2
        - form["goals_against"] * 2
    )

    return max(1, min(100, round(score)))
