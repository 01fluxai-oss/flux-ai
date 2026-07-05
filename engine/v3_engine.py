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
            "home_bonus": 0,
            "streak": 50,
            "data_quality": 0,
        }

    points = form.get("points", 0)
    wins = form.get("wins", 0)
    draws = form.get("draws", 0)
    losses = form.get("losses", 0)
    goals_for = form.get("goals_for", 0)
    goals_against = form.get("goals_against", 0)

    avg_for = form.get("avg_goals_for", goals_for / max(matches, 1))
    avg_against = form.get("avg_goals_against", goals_against / max(matches, 1))

    form_index = clamp(safe_rate(points, matches * 3) * 100, 20, 95)
    attack_index = clamp(38 + avg_for * 20, 25, 95)
    defense_index = clamp(92 - avg_against * 18, 25, 95)

    win_rate = safe_rate(wins, matches)
    loss_rate = safe_rate(losses, matches)
    draw_rate = safe_rate(draws, matches)

    streak_index = clamp(50 + win_rate * 35 - loss_rate * 30 - draw_rate * 5, 20, 95)
    data_quality = clamp(matches * 12, 0, 100)
    home_bonus = 8 if home_advantage else 0

    rating = (
        form_index * 0.30
        + attack_index * 0.25
        + defense_index * 0.20
        + home_bonus
        + data_quality * 0.10
        + streak_index * 0.05
    )

    return {
        "rating": clamp(rating, 20, 95),
        "form": form_index,
        "attack": attack_index,
        "defense": defense_index,
        "home_bonus": home_bonus,
        "streak": streak_index,
        "data_quality": data_quality,
    }


def calculate_probabilities(team1_rating, team2_rating):
    r1 = team1_rating["rating"]
    r2 = team2_rating["rating"]

    diff = r1 - r2
    abs_diff = abs(diff)

    draw = clamp(30 - abs_diff * 0.25, 16, 32)
    available = 100 - draw

    p1 = available / 2 + diff * 0.55
    p2 = available - p1

    p1 = clamp(p1, 5, 85)
    p2 = clamp(p2, 5, 85)

    total = p1 + p2 + draw
    correction = 100 - total

    if correction != 0:
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

    over_15 = clamp(avg_goals * 18 + attack_pressure * 0.20, 40, 90)
    over_25 = clamp(avg_goals * 17 + attack_pressure * 0.23 - defense_resistance * 0.08, 25, 80)
    over_35 = clamp(avg_goals * 13 + attack_pressure * 0.18 - defense_resistance * 0.10, 15, 65)

    btts_yes = clamp(avg_goals * 15 + attack_pressure * 0.20 - defense_resistance * 0.05, 25, 78)

    return {
        "avg_goals": round(avg_goals, 2),
        "over_1_5": over_15,
        "under_1_5": 100 - over_15,
        "over_2_5": over_25,
        "under_2_5": 100 - over_25,
        "over_3_5": over_35,
        "under_3_5": 100 - over_35,
        "btts_yes": btts_yes,
        "btts_no": 100 - btts_yes,
    }


def calculate_double_chance(probabilities):
    return {
        "1X": clamp(probabilities["p1"] + probabilities["draw"], 5, 95),
        "12": clamp(probabilities["p1"] + probabilities["p2"], 5, 95),
        "X2": clamp(probabilities["draw"] + probabilities["p2"], 5, 95),
    }


def predict_score(team1_form, team2_form):
    team1_expected = (
        team1_form.get("avg_goals_for", 0) * 0.65
        + team2_form.get("avg_goals_against", 0) * 0.35
    )

    team2_expected = (
        team2_form.get("avg_goals_for", 0) * 0.65
        + team1_form.get("avg_goals_against", 0) * 0.35
    )

    team1_goals = clamp(team1_expected, 0, 5)
    team2_goals = clamp(team2_expected, 0, 5)

    return {
        "team1_goals": team1_goals,
        "team2_goals": team2_goals,
        "score": f"{team1_goals}:{team2_goals}",
    }


def choose_best_pick(probabilities, totals, double_chance):
    picks = {
        "П1": probabilities["p1"],
        "X": probabilities["draw"],
        "П2": probabilities["p2"],
        "1X": double_chance["1X"],
        "12": double_chance["12"],
        "X2": double_chance["X2"],
        "ТБ 2.5": totals["over_2_5"],
        "ТМ 2.5": totals["under_2_5"],
        "ТБ 3.5": totals["over_3_5"],
        "Обе забьют — Да": totals["btts_yes"],
        "Обе забьют — Нет": totals["btts_no"],
    }

    sorted_picks = sorted(picks.items(), key=lambda x: x[1], reverse=True)

    return {
        "pick": sorted_picks[0][0],
        "value": sorted_picks[0][1],
        "top_3": sorted_picks[:3],
    }


def calculate_risk(best_pick, team1_rating, team2_rating):
    data_quality = min(
        team1_rating.get("data_quality", 0),
        team2_rating.get("data_quality", 0),
    )

    value = best_pick["value"]
    rating_diff = abs(team1_rating["rating"] - team2_rating["rating"])

    confidence = clamp(
        value / 13 + data_quality / 35 + rating_diff / 25,
        1,
        10,
    )

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
    double_chance = calculate_double_chance(probabilities)
    predicted_score = predict_score(team1_form, team2_form)
    best_pick = choose_best_pick(probabilities, totals, double_chance)
    risk = calculate_risk(best_pick, team1_rating, team2_rating)

    return {
        "team1": team1,
        "team2": team2,
        "team1_rating": team1_rating,
        "team2_rating": team2_rating,
        "probabilities": probabilities,
        "totals": totals,
        "double_chance": double_chance,
        "predicted_score": predicted_score,
        "best_pick": best_pick,
        "risk": risk["risk"],
        "confidence": risk["confidence"],
        "data_quality": risk["data_quality"],
    }
