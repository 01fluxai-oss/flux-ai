import os
import requests

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"

TEAM_ALIASES = {
    "psg": "Paris Saint Germain",
    "псж": "Paris Saint Germain",
    "paris": "Paris Saint Germain",
    "real madrid": "Real Madrid",
    "реал мадрид": "Real Madrid",
    "barcelona": "Barcelona",
    "барселона": "Barcelona",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "манчестер сити": "Manchester City",
    "liverpool": "Liverpool",
    "ливерпуль": "Liverpool",
    "arsenal": "Arsenal",
    "арсенал": "Arsenal",
    "chelsea": "Chelsea",
    "челси": "Chelsea",
    "bayern": "Bayern Munich",
    "бавария": "Bayern Munich",
}

def normalize_team_name(name):
    key = name.lower().strip()
    return TEAM_ALIASES.get(key, name.strip())

def api_get(endpoint, params=None):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    return response.json()

def search_team(team_name):
    team_name = normalize_team_name(team_name)
    data = api_get("teams", {"search": team_name})
    return data.get("response", [])[:5]

def get_team_last_matches(team_id, last=10):
    data = api_get("fixtures", {"team": team_id, "last": last})
    return data.get("response", [])

def get_h2h(team1_id, team2_id):
    data = api_get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": 10})
    return data.get("response", [])

def analyze_team_form(matches, team_id):
    played = len(matches)
    wins = draws = losses = 0
    goals_for = goals_against = 0

    for match in matches:
        teams = match.get("teams", {})
        goals = match.get("goals", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        home_id = home.get("id")
        away_id = away.get("id")

        home_goals = goals.get("home") or 0
        away_goals = goals.get("away") or 0

        if team_id == home_id:
            gf = home_goals
            ga = away_goals
        else:
            gf = away_goals
            ga = home_goals

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    return {
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / played, 2) if played else 0,
        "avg_goals_against": round(goals_against / played, 2) if played else 0,
    }

def analyze_h2h(matches, team1_id, team2_id):
    result = {
        "played": len(matches),
        "team1_wins": 0,
        "draws": 0,
        "team2_wins": 0,
        "avg_total_goals": 0,
    }

    total_goals = 0

    for match in matches:
        teams = match.get("teams", {})
        goals = match.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")

        home_goals = goals.get("home") or 0
        away_goals = goals.get("away") or 0
        total_goals += home_goals + away_goals

        if home_goals == away_goals:
            result["draws"] += 1
        elif home_goals > away_goals:
            if home_id == team1_id:
                result["team1_wins"] += 1
            else:
                result["team2_wins"] += 1
        else:
            if away_id == team1_id:
                result["team1_wins"] += 1
            else:
                result["team2_wins"] += 1

    if result["played"]:
        result["avg_total_goals"] = round(total_goals / result["played"], 2)

    return result

def calculate_probabilities(team1_form, team2_form, h2h):
    team1_score = 50
    team2_score = 50

    team1_score += team1_form["wins"] * 4
    team1_score -= team1_form["losses"] * 3
    team1_score += team1_form["avg_goals_for"] * 4
    team1_score -= team1_form["avg_goals_against"] * 3

    team2_score += team2_form["wins"] * 4
    team2_score -= team2_form["losses"] * 3
    team2_score += team2_form["avg_goals_for"] * 4
    team2_score -= team2_form["avg_goals_against"] * 3

    team1_score += h2h["team1_wins"] * 2
    team2_score += h2h["team2_wins"] * 2

    draw_score = 25 + (team1_form["draws"] + team2_form["draws"] + h2h["draws"]) * 2

    total = team1_score + team2_score + draw_score

    p1 = round(team1_score / total * 100)
    p2 = round(team2_score / total * 100)
    x = max(5, 100 - p1 - p2)

    return {
        "p1": p1,
        "draw": x,
        "p2": p2,
    }

def build_match_context(team1_name, team2_name):
    team1_results = search_team(team1_name)
    team2_results = search_team(team2_name)

    if not team1_results or not team2_results:
        return None

    team1 = team1_results[0]["team"]
    team2 = team2_results[0]["team"]

    team1_last = get_team_last_matches(team1["id"], 10)
    team2_last = get_team_last_matches(team2["id"], 10)
    h2h_matches = get_h2h(team1["id"], team2["id"])

    team1_form = analyze_team_form(team1_last, team1["id"])
    team2_form = analyze_team_form(team2_last, team2["id"])
    h2h_analysis = analyze_h2h(h2h_matches, team1["id"], team2["id"])
    probabilities = calculate_probabilities(team1_form, team2_form, h2h_analysis)

    return {
        "team1": team1,
        "team2": team2,
        "team1_last_matches": team1_last,
        "team2_last_matches": team2_last,
        "head_to_head": h2h_matches,
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h_analysis": h2h_analysis,
        "probabilities": probabilities,
    }
