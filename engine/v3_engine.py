def clamp(
    value,
    minimum=1,
    maximum=99,
):
    return max(
        minimum,
        min(
            maximum,
            round(value),
        ),
    )


def safe_rate(
    value,
    total,
):
    if total <= 0:
        return 0

    return value / total


def calculate_team_rating(
    form,
    home_advantage=False,
):
    matches = max(
        form.get("matches", 0),
        0,
    )

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

    points = form.get(
        "points",
        0,
    )

    wins = form.get(
        "wins",
        0,
    )

    draws = form.get(
        "draws",
        0,
    )

    losses = form.get(
        "losses",
        0,
    )

    goals_for = form.get(
        "goals_for",
        0,
    )

    goals_against = form.get(
        "goals_against",
        0,
    )

    avg_for = form.get(
        "avg_goals_for",
        goals_for / max(matches, 1),
    )

    avg_against = form.get(
        "avg_goals_against",
        goals_against / max(matches, 1),
    )

    form_index = clamp(
        safe_rate(
            points,
            matches * 3,
        ) * 100,
        20,
        95,
    )

    attack_index = clamp(
        40 + avg_for * 19,
        25,
        95,
    )

    defense_index = clamp(
        92 - avg_against * 17,
        25,
        95,
    )

    win_rate = safe_rate(
        wins,
        matches,
    )

    loss_rate = safe_rate(
        losses,
        matches,
    )

    draw_rate = safe_rate(
        draws,
        matches,
    )

    streak_index = clamp(
        50
        + win_rate * 35
        - loss_rate * 28
        - draw_rate * 4,
        20,
        95,
    )

    data_quality = clamp(
        matches * 12,
        0,
        100,
    )

    home_bonus = (
        6
        if home_advantage
        else 0
    )

    rating = (
        form_index * 0.32
        + attack_index * 0.24
        + defense_index * 0.22
        + streak_index * 0.10
        + data_quality * 0.06
        + home_bonus
    )

    return {
        "rating": clamp(
            rating,
            20,
            95,
        ),
        "form": form_index,
        "attack": attack_index,
        "defense": defense_index,
        "home_bonus": home_bonus,
        "streak": streak_index,
        "data_quality": data_quality,
    }


def calculate_probabilities(
    team1_rating,
    team2_rating,
):
    rating1 = team1_rating[
        "rating"
    ]

    rating2 = team2_rating[
        "rating"
    ]

    difference = (
        rating1 - rating2
    )

    absolute_difference = abs(
        difference
    )

    draw = clamp(
        31
        - absolute_difference * 0.23,
        17,
        33,
    )

    available = (
        100 - draw
    )

    home_win = (
        available / 2
        + difference * 0.50
    )

    away_win = (
        available - home_win
    )

    home_win = clamp(
        home_win,
        6,
        84,
    )

    away_win = clamp(
        away_win,
        6,
        84,
    )

    total = (
        home_win
        + away_win
        + draw
    )

    correction = (
        100 - total
    )

    if correction:
        if home_win >= away_win:
            home_win += correction
        else:
            away_win += correction

    return {
        "p1": clamp(
            home_win,
            5,
            85,
        ),
        "draw": clamp(
            draw,
            10,
            40,
        ),
        "p2": clamp(
            away_win,
            5,
            85,
        ),
        "difference": round(
            absolute_difference,
            1,
        ),
    }


def calculate_totals(
    team1_form,
    team2_form,
    team1_rating,
    team2_rating,
):
    average_goals = (
        team1_form.get(
            "avg_goals_for",
            0,
        )
        + team2_form.get(
            "avg_goals_for",
            0,
        )
        + team1_form.get(
            "avg_goals_against",
            0,
        )
        + team2_form.get(
            "avg_goals_against",
            0,
        )
    ) / 2

    attack_pressure = (
        team1_rating["attack"]
        + team2_rating["attack"]
    ) / 2

    defense_resistance = (
        team1_rating["defense"]
        + team2_rating["defense"]
    ) / 2

    over_15 = clamp(
        average_goals * 18
        + attack_pressure * 0.22,
        42,
        91,
    )

    over_25 = clamp(
        average_goals * 17
        + attack_pressure * 0.25
        - defense_resistance * 0.08,
        26,
        82,
    )

    over_35 = clamp(
        average_goals * 13
        + attack_pressure * 0.18
        - defense_resistance * 0.10,
        14,
        66,
    )

    btts_yes = clamp(
        average_goals * 15
        + attack_pressure * 0.21
        - defense_resistance * 0.05,
        25,
        80,
    )

    return {
        "avg_goals": round(
            average_goals,
            2,
        ),
        "over_1_5": over_15,
        "under_1_5": (
            100 - over_15
        ),
        "over_2_5": over_25,
        "under_2_5": (
            100 - over_25
        ),
        "over_3_5": over_35,
        "under_3_5": (
            100 - over_35
        ),
        "btts_yes": btts_yes,
        "btts_no": (
            100 - btts_yes
        ),
    }


def calculate_double_chance(
    probabilities,
):
    return {
        "1X": clamp(
            probabilities["p1"]
            + probabilities["draw"],
            5,
            95,
        ),
        "12": clamp(
            probabilities["p1"]
            + probabilities["p2"],
            5,
            95,
        ),
        "X2": clamp(
            probabilities["draw"]
            + probabilities["p2"],
            5,
            95,
        ),
    }


def predict_score(
    team1_form,
    team2_form,
):
    team1_expected = (
        team1_form.get(
            "avg_goals_for",
            0,
        ) * 0.65
        + team2_form.get(
            "avg_goals_against",
            0,
        ) * 0.35
    )

    team2_expected = (
        team2_form.get(
            "avg_goals_for",
            0,
        ) * 0.65
        + team1_form.get(
            "avg_goals_against",
            0,
        ) * 0.35
    )

    team1_goals = clamp(
        team1_expected,
        0,
        5,
    )

    team2_goals = clamp(
        team2_expected,
        0,
        5,
    )

    return {
        "team1_goals": team1_goals,
        "team2_goals": team2_goals,
        "score": (
            f"{team1_goals}:"
            f"{team2_goals}"
        ),
    }

def choose_best_pick(
    probabilities,
    totals,
    double_chance,
):
    candidates = [
        (
            "over_1_5",
            totals["over_1_5"],
            1.00,
        ),
        (
            "over_2_5",
            totals["over_2_5"],
            1.12,
        ),
        (
            "under_2_5",
            totals["under_2_5"],
            1.05,
        ),
        (
            "btts_yes",
            totals["btts_yes"],
            1.08,
        ),
        (
            "btts_no",
            totals["btts_no"],
            1.03,
        ),
    ]

    if probabilities["p1"] >= 44:
        candidates.append(
            (
                "p1",
                probabilities["p1"],
                1.18,
            )
        )

    if probabilities["p2"] >= 44:
        candidates.append(
            (
                "p2",
                probabilities["p2"],
                1.18,
            )
        )

    if probabilities["draw"] >= 31:
        candidates.append(
            (
                "draw",
                probabilities["draw"],
                1.25,
            )
        )

    if (
        double_chance["1X"] >= 68
        and probabilities["p1"]
        >= probabilities["p2"]
    ):
        candidates.append(
            (
                "double_1x",
                double_chance["1X"],
                0.92,
            )
        )

    if (
        double_chance["X2"] >= 68
        and probabilities["p2"]
        >= probabilities["p1"]
    ):
        candidates.append(
            (
                "double_x2",
                double_chance["X2"],
                0.92,
            )
        )

    if (
        double_chance["12"] >= 76
        and probabilities["draw"] <= 24
    ):
        candidates.append(
            (
                "double_12",
                double_chance["12"],
                0.82,
            )
        )

    ranked = sorted(
        candidates,
        key=lambda item: (
            item[1] * item[2]
        ),
        reverse=True,
    )

    top_3 = [
        (
            name,
            value,
        )
        for name, value, _ in ranked[:3]
    ]

    return {
        "pick": ranked[0][0],
        "value": ranked[0][1],
        "top_3": top_3,
    }


def calculate_risk(
    best_pick,
    team1_rating,
    team2_rating,
):
    data_quality = min(
        team1_rating.get(
            "data_quality",
            0,
        ),
        team2_rating.get(
            "data_quality",
            0,
        ),
    )

    value = best_pick["value"]

    rating_difference = abs(
        team1_rating["rating"]
        - team2_rating["rating"]
    )

    confidence = clamp(
        value * 0.62
        + data_quality * 0.18
        + rating_difference * 0.20,
        35,
        92,
    )

    if data_quality < 30:
        risk = "high"

    elif confidence >= 75:
        risk = "low"

    elif confidence >= 60:
        risk = "medium"

    else:
        risk = "high"

    return {
        "risk": risk,
        "confidence": confidence,
        "data_quality": data_quality,
    }


def analyze_v3(
    team1,
    team2,
    team1_form,
    team2_form,
):
    team1_rating = (
        calculate_team_rating(
            team1_form,
            home_advantage=True,
        )
    )

    team2_rating = (
        calculate_team_rating(
            team2_form,
            home_advantage=False,
        )
    )

    probabilities = (
        calculate_probabilities(
            team1_rating,
            team2_rating,
        )
    )

    totals = calculate_totals(
        team1_form,
        team2_form,
        team1_rating,
        team2_rating,
    )

    double_chance = (
        calculate_double_chance(
            probabilities
        )
    )

    predicted_score = (
        predict_score(
            team1_form,
            team2_form,
        )
    )

    best_pick = choose_best_pick(
        probabilities,
        totals,
        double_chance,
    )

    risk_data = calculate_risk(
        best_pick,
        team1_rating,
        team2_rating,
    )

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
        "risk": risk_data["risk"],
        "confidence": risk_data["confidence"],
        "data_quality": (
            risk_data["data_quality"]
        ),
    }
