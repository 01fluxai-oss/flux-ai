def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def safe_rate(value, total):
    if total <= 0:
        return 0
    return value / total


def calculate_team_rating(form, home_advantage=False):
    matches = max(form.get("matches", 0), 0)

    if matches == 0:
        return {
            "rating": 50,
            "form": 50,
            "attack": 50,
            "defense": 50,
            "data_quality": 0,
        }

    points = form.get("points", 0)
    goals_for = form.get("goals_for", 0)
    goals_against = form.get("goals_against", 0)

    avg_for = form.get("avg_goals_for", goals_for / max(matches, 1))
    avg_against = form.get("avg_goals_against", goals_against / max(matches, 1))

    form_index = clamp(safe_rate(points, matches * 3) * 100, 20, 95)
    attack_index = clamp(40 + avg_for * 18, 25, 92)
    defense_index = clamp(90 - avg_against * 18, 25, 92)

    home_bonus = 5 if home_advantage else 0
    "data_quality":     clamp(matches * 12, 0, 100)

    rating = (
        form_index * 0.40
        + attack_index * 0.25
        + defense_index * 0.20
        + home_bonus
        + data_quality * 0.10
    )

    return {
        "rating": clamp(rating, 20, 95),
        "form": form_index,
        "attack": attack_index,
        "defense": defense_index,
        "data_quality": data_quality,
    }


def calculate_probabilities(team1_rating, team2_rating):
    r1 = team1_rating["rating"]
    r2 = team2_rating["rating"]

    diff = r1 - r2
    abs_diff = abs(diff)

    draw = clamp(30 - abs_diff * 0.20, 18, 32)

    available = 100 - draw
    base_p1 = available / 2 + diff * 0.45
    base_p2 = available - base_p1

    p1 = clamp(base_p1, 8, 80)
    p2 = clamp(base_p2, 8, 80)

    total = p1 + p2 + draw
    if total != 100:
        correction = 100 - total
        if p1 >= p2:
            p1 += correction
        else:
            p2 += correction

    return {
        "p1": clamp(p1, 5, 85),
        "draw": clamp(draw, 10, 40),
        "p2": clamp(p2, 5, 85),
        "difference": round(abs_diff, 1),
    }


def calculate_totals(team1_form, team2_form, team1_rating, team2_rating):
    avg_goals = (
        team1_form.get("avg_goals_for", 0)
        + team2_form.get("avg_goals_for", 0)
        + team1_form.get("avg_goals_against", 0)
        + team2_form.get("avg_goals_against", 0)
    ) / 2

    attack_pressure = (team1_rating["attack"] + team2_rating["attack"]) / 2
    defense_resistance = (team1_rating["defense"] + team2_rating["defense"]) / 2

    over = clamp((avg_goals * 18) + (attack_pressure * 0.25) - (defense_resistance * 0.08), 25, 78)
    under = 100 - over

    btts_yes = clamp((avg_goals * 16) + (attack_pressure * 0.22) - (defense_resistance * 0.06), 25, 75)
    btts_no = 100 - btts_yes

    return {
        "avg_goals": round(avg_goals, 2),
        "over_2_5": over,
        "under_2_5": under,
        "btts_yes": btts_yes,
        "btts_no": btts_no,
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

    pick = max(picks, key=picks.get)

    return {
        "pick": pick,
        "value": picks[pick],
    }


def calculate_risk(probabilities, best_pick, team1_rating, team2_rating):
    data_quality = min(team1_rating["data_quality"], team2_rating["data_quality"])
    value = best_pick["value"]

    confidence = clamp((value / 10) + (data_quality / 30), 1, 10)

    if data_quality < 30:
        risk = "Высокий"
    elif confidence >= 8:
        risk = "Низкий"
    elif confidence >= 6:
        risk = "Средний"
    else:
        risk = "Высокий"

    return {
        "risk": risk,
        "confidence": confidence,
        "data_quality": data_quality,
    }


def analyze_v3(team1, team2, team1_form, team2_form):
    team1_rating = calculate_team_rating(team1_form, home_advantage=True)
    team2_rating = calculate_team_rating(team2_form, home_advantage=False)

    probabilities = calculate_probabilities(team1_rating, team2_rating)
    totals = calculate_totals(team1_form, team2_form, team1_rating, team2_rating)
    best_pick = choose_best_pick(probabilities, totals)
    risk = calculate_risk(probabilities, best_pick, team1_rating, team2_rating)

    return {
        "team1": team1,
        "team2": team2,
        "team1_rating": team1_rating,
        "team2_rating": team2_rating,
        "probabilities": probabilities,
        "totals": totals,
        "best_pick": best_pick,
        "risk": risk["risk"],
        "confidence": risk["confidence"],
        "data_quality": risk["data_quality"],
    }
