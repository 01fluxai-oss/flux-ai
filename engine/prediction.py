def calculate_probabilities(flux_score):
    team1_score = flux_score.get("team1", 50)
    team2_score = flux_score.get("team2", 50)

    total = max(team1_score + team2_score, 1)

    p1 = round((team1_score / total) * 100)
    p2 = round((team2_score / total) * 100)

    difference = abs(p1 - p2)

    draw = max(18, 32 - round(difference / 2))

    scale = 100 - draw
    p1 = round((p1 / (p1 + p2)) * scale)
    p2 = 100 - draw - p1

    return {
        "p1": p1,
        "draw": draw,
        "p2": p2,
    }


def calculate_totals(team1_form, team2_form):
    avg_goals = (
        team1_form.get("avg_goals_for", 0)
        + team2_form.get("avg_goals_for", 0)
        + team1_form.get("avg_goals_against", 0)
        + team2_form.get("avg_goals_against", 0)
    ) / 2

    over = round(min(80, max(25, avg_goals * 22)))
    under = 100 - over

    btts_yes = round(min(80, max(25, avg_goals * 20)))
    btts_no = 100 - btts_yes

    return {
        "over_2_5": over,
        "under_2_5": under,
        "btts_yes": btts_yes,
        "btts_no": btts_no,
    }
