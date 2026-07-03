def simplify_match(match):
    fixture = match.get("fixture", {})
    league = match.get("league", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})

    return {
        "date": fixture.get("date"),
        "league": league.get("name"),
        "home": teams.get("home", {}).get("name"),
        "away": teams.get("away", {}).get("name"),
        "score": f"{goals.get('home')}-{goals.get('away')}",
    }


def team_form_score(matches, team_name):
    points = 0
    wins = draws = losses = 0
    goals_for = 0
    goals_against = 0

    for match in matches:
        teams = match.get("teams", {})
        goals = match.get("goals", {})

        home = teams.get("home", {}).get("name")
        away = teams.get("away", {}).get("name")

        home_goals = goals.get("home") or 0
        away_goals = goals.get("away") or 0

        if team_name == home:
            gf, ga = home_goals, away_goals
        elif team_name == away:
            gf, ga = away_goals, home_goals
        else:
            continue

        goals_for += gf
        goals_against += ga

        if gf > ga:
            points += 3
            wins += 1
        elif gf == ga:
            points += 1
            draws += 1
        else:
            losses += 1

    matches_count = max(len(matches), 1)

    return {
        "matches": len(matches),
        "points": points,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / matches_count, 2),
        "avg_goals_against": round(goals_against / matches_count, 2),
    }


def h2h_summary(matches, team1_name, team2_name):
    team1_wins = team2_wins = draws = 0
    total_goals = 0

    for match in matches:
        teams = match.get("teams", {})
        goals = match.get("goals", {})

        home = teams.get("home", {}).get("name")
        away = teams.get("away", {}).get("name")

        home_goals = goals.get("home") or 0
        away_goals = goals.get("away") or 0
        total_goals += home_goals + away_goals

        if home_goals == away_goals:
            draws += 1
        elif home_goals > away_goals:
            if home == team1_name:
                team1_wins += 1
            elif home == team2_name:
                team2_wins += 1
        else:
            if away == team1_name:
                team1_wins += 1
            elif away == team2_name:
                team2_wins += 1

    count = max(len(matches), 1)

    return {
        "matches": len(matches),
        "team1_wins": team1_wins,
        "draws": draws,
        "team2_wins": team2_wins,
        "avg_total_goals": round(total_goals / count, 2),
    }
