def calculate_flux_score(team1_form, team2_form, h2h):
    team1_points = team1_form.get("points", 0)
    team2_points = team2_form.get("points", 0)

    team1_goals_for = team1_form.get("goals_for", 0)
    team2_goals_for = team2_form.get("goals_for", 0)

    team1_goals_against = team1_form.get("goals_against", 0)
    team2_goals_against = team2_form.get("goals_against", 0)

    team1_score = (
        team1_points * 2
        + team1_goals_for * 1.5
        - team1_goals_against
    )

    team2_score = (
        team2_points * 2
        + team2_goals_for * 1.5
        - team2_goals_against
    )

    team1_score = max(1, min(100, round(team1_score)))
    team2_score = max(1, min(100, round(team2_score)))

    return {
        "team1": team1_score,
        "team2": team2_score,
        "difference": abs(team1_score - team2_score),
    }
