def clamp(
    value,
    minimum=0,
    maximum=100,
):
    return max(
        minimum,
        min(
            maximum,
            round(value),
        ),
    )


def safe_number(
    value,
    default=0,
):
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return float(default)


def calculate_team_rating(
    form,
    home_advantage=False,
):
    matches = int(
        form.get(
            "matches",
            0,
        )
    )

    if matches <= 0:
        return {
            "rating": 50,
            "form": 50,
            "offense": 50,
            "defense": 50,
            "margin": 50,
            "home_bonus": 0,
            "data_quality": 0,
        }

    win_rate = safe_number(
        form.get(
            "win_rate",
            0,
        )
    )

    avg_points_for = safe_number(
        form.get(
            "avg_points_for",
            0,
        )
    )

    avg_points_against = safe_number(
        form.get(
            "avg_points_against",
            0,
        )
    )

    avg_margin = safe_number(
        form.get(
            "avg_margin",
            0,
        )
    )

    data_quality = safe_number(
        form.get(
            "data_quality",
            0,
        )
    )

    form_index = clamp(
        win_rate,
        20,
        95,
    )

    offense_index = clamp(
        50
        + (
            avg_points_for
            - 110
        ) * 2.2,
        25,
        95,
    )

    defense_index = clamp(
        50
        + (
            110
            - avg_points_against
        ) * 2.2,
        25,
        95,
    )

    margin_index = clamp(
        50
        + avg_margin * 3.0,
        20,
        95,
    )

    home_bonus = (
        4
        if home_advantage
        else 0
    )

    rating = (
        form_index * 0.34
        + offense_index * 0.25
        + defense_index * 0.21
        + margin_index * 0.14
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
        "offense": offense_index,
        "defense": defense_index,
        "margin": margin_index,
        "home_bonus": home_bonus,
        "data_quality": clamp(
            data_quality,
            0,
            100,
        ),
    }


def calculate_win_probabilities(
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
        rating1
        - rating2
    )

    home_probability = (
        50
        + difference * 0.82
    )

    home_probability = clamp(
        home_probability,
        12,
        88,
    )

    away_probability = (
        100
        - home_probability
    )

    return {
        "home": home_probability,
        "away": away_probability,
        "difference": abs(
            rating1 - rating2
        ),
    }


def calculate_expected_points(
    team1_form,
    team2_form,
):
    team1_scoring = safe_number(
        team1_form.get(
            "avg_points_for",
            110,
        ),
        110,
    )

    team1_allowed = safe_number(
        team1_form.get(
            "avg_points_against",
            110,
        ),
        110,
    )

    team2_scoring = safe_number(
        team2_form.get(
            "avg_points_for",
            110,
        ),
        110,
    )

    team2_allowed = safe_number(
        team2_form.get(
            "avg_points_against",
            110,
        ),
        110,
    )

    team1_expected = (
        team1_scoring * 0.58
        + team2_allowed * 0.42
        + 2.0
    )

    team2_expected = (
        team2_scoring * 0.58
        + team1_allowed * 0.42
    )

    team1_expected = round(
        max(
            85,
            min(
                145,
                team1_expected,
            ),
        )
    )

    team2_expected = round(
        max(
            85,
            min(
                145,
                team2_expected,
            ),
        )
    )

    projected_total = (
        team1_expected
        + team2_expected
    )

    return {
        "team1_points": team1_expected,
        "team2_points": team2_expected,
        "score": (
            f"{team1_expected}:"
            f"{team2_expected}"
        ),
        "projected_total": projected_total,
    }


def calculate_total_market(
    team1_form,
    team2_form,
    expected_points,
):
    team1_total = safe_number(
        team1_form.get(
            "avg_total_points",
            220,
        ),
        220,
    )

    team2_total = safe_number(
        team2_form.get(
            "avg_total_points",
            220,
        ),
        220,
    )

    historical_total = (
        team1_total
        + team2_total
    ) / 2

    projected_total = safe_number(
        expected_points.get(
            "projected_total",
            220,
        ),
        220,
    )

    model_total = (
        projected_total * 0.62
        + historical_total * 0.38
    )

    model_total = round(
        model_total * 2
    ) / 2

    reference_line = round(
        (
            model_total - 1.5
        ) * 2
    ) / 2

    edge = (
        model_total
        - reference_line
    )

    over_probability = clamp(
        50 + edge * 7,
        45,
        78,
    )

    under_probability = (
        100 - over_probability
    )

    return {
        "model_total": model_total,
        "reference_line": reference_line,
        "over_probability": over_probability,
        "under_probability": under_probability,
        "historical_total": round(
            historical_total,
            1,
        ),
    }


def calculate_recent_form_score(
    form,
):
    recent = form.get(
        "recent",
        [],
    )

    if not recent:
        return 50

    weighted_score = 0
    total_weight = 0

    weights = [
        5,
        4,
        3,
        2,
        1,
    ]

    for index, game in enumerate(
        recent[:5]
    ):
        weight = weights[index]

        if game.get(
            "result"
        ) == "win":
            result_value = 100
        else:
            result_value = 25

        margin = safe_number(
            game.get(
                "margin",
                0,
            )
        )

        margin_bonus = max(
            -15,
            min(
                15,
                margin,
            ),
        )

        weighted_score += (
            result_value
            + margin_bonus
        ) * weight

        total_weight += weight

    if total_weight == 0:
        return 50

    return clamp(
        weighted_score
        / total_weight,
        15,
        95,
    )


def calculate_pace_signal(
    team1_form,
    team2_form,
):
    team1_total = safe_number(
        team1_form.get(
            "avg_total_points",
            220,
        ),
        220,
    )

    team2_total = safe_number(
        team2_form.get(
            "avg_total_points",
            220,
        ),
        220,
    )

    combined = (
        team1_total
        + team2_total
    ) / 2

    if combined >= 232:
        return {
            "level": "high",
            "score": 85,
        }

    if combined >= 220:
        return {
            "level": "medium",
            "score": 65,
        }

    return {
        "level": "low",
        "score": 45,
    }

def build_top_insights(
    probabilities,
    total_market,
    team1_rating,
    team2_rating,
    recent_form1,
    recent_form2,
):
    candidates = []

    home_probability = probabilities[
        "home"
    ]

    away_probability = probabilities[
        "away"
    ]

    if home_probability >= 56:
        candidates.append(
            (
                "home_win",
                home_probability,
            )
        )

    if away_probability >= 56:
        candidates.append(
            (
                "away_win",
                away_probability,
            )
        )

    candidates.append(
        (
            "over_total",
            total_market[
                "over_probability"
            ],
        )
    )

    candidates.append(
        (
            "under_total",
            total_market[
                "under_probability"
            ],
        )
    )

    if recent_form1 >= 65:
        candidates.append(
            (
                "team1_form",
                recent_form1,
            )
        )

    if recent_form2 >= 65:
        candidates.append(
            (
                "team2_form",
                recent_form2,
            )
        )

    rating_difference = abs(
        team1_rating["rating"]
        - team2_rating["rating"]
    )

    if rating_difference <= 7:
        candidates.append(
            (
                "close_game",
                clamp(
                    72 - rating_difference,
                    55,
                    72,
                ),
            )
        )

    ranked = sorted(
        candidates,
        key=lambda item: item[1],
        reverse=True,
    )

    unique = []
    used_codes = set()

    for code, value in ranked:
        if code in used_codes:
            continue

        unique.append(
            (
                code,
                value,
            )
        )

        used_codes.add(code)

        if len(unique) == 3:
            break

    return unique


def choose_main_pick(
    probabilities,
    total_market,
):
    candidates = [
        (
            "home_win",
            probabilities["home"],
            1.08,
        ),
        (
            "away_win",
            probabilities["away"],
            1.08,
        ),
        (
            "over_total",
            total_market[
                "over_probability"
            ],
            1.03,
        ),
        (
            "under_total",
            total_market[
                "under_probability"
            ],
            1.03,
        ),
    ]

    ranked = sorted(
        candidates,
        key=lambda item: (
            item[1] * item[2]
        ),
        reverse=True,
    )

    return {
        "pick": ranked[0][0],
        "value": ranked[0][1],
    }


def calculate_risk(
    main_pick,
    data_quality,
    rating_difference,
):
    probability = safe_number(
        main_pick.get(
            "value",
            50,
        ),
        50,
    )

    confidence = (
        probability * 0.62
        + data_quality * 0.24
        + min(
            rating_difference,
            25,
        ) * 0.14
    )

    confidence = clamp(
        confidence,
        35,
        92,
    )

    if data_quality < 50:
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
    }


def analyze_nba_match(
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
        calculate_win_probabilities(
            team1_rating,
            team2_rating,
        )
    )

    expected_points = (
        calculate_expected_points(
            team1_form,
            team2_form,
        )
    )

    total_market = (
        calculate_total_market(
            team1_form,
            team2_form,
            expected_points,
        )
    )

    recent_form1 = (
        calculate_recent_form_score(
            team1_form
        )
    )

    recent_form2 = (
        calculate_recent_form_score(
            team2_form
        )
    )

    pace_signal = (
        calculate_pace_signal(
            team1_form,
            team2_form,
        )
    )

    main_pick = choose_main_pick(
        probabilities,
        total_market,
    )

    top_insights = build_top_insights(
        probabilities,
        total_market,
        team1_rating,
        team2_rating,
        recent_form1,
        recent_form2,
    )

    data_quality = min(
        team1_rating[
            "data_quality"
        ],
        team2_rating[
            "data_quality"
        ],
    )

    risk_data = calculate_risk(
        main_pick,
        data_quality,
        probabilities[
            "difference"
        ],
    )

    return {
        "team1": team1,
        "team2": team2,
        "team1_rating": team1_rating,
        "team2_rating": team2_rating,
        "probabilities": probabilities,
        "expected_points": expected_points,
        "total_market": total_market,
        "recent_form1": recent_form1,
        "recent_form2": recent_form2,
        "pace_signal": pace_signal,
        "main_pick": main_pick,
        "top_insights": top_insights,
        "risk": risk_data["risk"],
        "confidence": risk_data[
            "confidence"
        ],
        "data_quality": data_quality,
    }


__all__ = [
    "calculate_team_rating",
    "calculate_win_probabilities",
    "calculate_expected_points",
    "calculate_total_market",
    "calculate_recent_form_score",
    "calculate_pace_signal",
    "build_top_insights",
    "choose_main_pick",
    "calculate_risk",
    "analyze_nba_match",
]
