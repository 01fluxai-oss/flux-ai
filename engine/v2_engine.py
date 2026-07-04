def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def calculate_v2(team1, team2, team1_form, team2_form):
    t1_attack = clamp(45 + team1_form["avg_goals_for"] * 18, 30, 90)
    t2_attack = clamp(45 + team2_form["avg_goals_for"] * 18, 30, 90)

    t1_defense = clamp(85 - team1_form["avg_goals_against"] * 18, 25, 90)
    t2_defense = clamp(85 - team2_form["avg_goals_against"] * 18, 25, 90)

    t1_form_score = clamp((team1_form["points"] / max(team1_form["matches"] * 3, 1)) * 100, 20, 95)
    t2_form_score = clamp((team2_form["points"] / max(team2_form["matches"] * 3, 1)) * 100, 20, 95)

    t1_power = clamp(t1_attack * 0.3 + t1_defense * 0.25 + t1_form_score * 0.35 + 5)
    t2_power = clamp(t2_attack * 0.3 + t2_defense * 0.25 + t2_form_score * 0.35)

    diff = abs(t1_power - t2_power)
    draw = clamp(30 - diff * 0.25, 18, 32)

    available = 100 - draw
    total = max(t1_power + t2_power, 1)

    p1 = clamp((t1_power / total) * available, 5, 80)
    p2 = 100 - draw - p1

    avg_goals = (
        team1_form["avg_goals_for"]
        + team2_form["avg_goals_for"]
        + team1_form["avg_goals_against"]
        + team2_form["avg_goals_against"]
    ) / 2

    over = clamp(avg_goals * 22, 25, 80)
    under = 100 - over

    btts_yes = clamp(avg_goals * 20, 25, 80)
    btts_no = 100 - btts_yes

    return {
        "team1": team1,
        "team2": team2,
        "team1_power": t1_power,
        "team2_power": t2_power,
        "attack": {"team1": t1_attack, "team2": t2_attack},
        "defense": {"team1": t1_defense, "team2": t2_defense},
        "form": {"team1": t1_form_score, "team2": t2_form_score},
        "probabilities": {"p1": p1, "draw": draw, "p2": p2},
        "totals": {
            "over_2_5": over,
            "under_2_5": under,
            "btts_yes": btts_yes,
            "btts_no": btts_no,
        },
    }
