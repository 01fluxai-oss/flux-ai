import os
import requests

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"

TEAM_ALIASES = {
    "psg": "Paris Saint Germain",
    "псж": "Paris Saint Germain",
    "real madrid": "Real Madrid",
    "реал мадрид": "Real Madrid",
    "barcelona": "Barcelona",
    "барселона": "Barcelona",
    "manchester city": "Manchester City",
    "манчестер сити": "Manchester City",
    "man city": "Manchester City",
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
    return TEAM_ALIASES.get(name.lower().strip(), name.strip())

def api_get(endpoint, params=None):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        params=params,
        timeout=20
    )
    response.raise_for_status()
    return response.json()

def search_team(team_name):
    team_name = normalize_team_name(team_name)
    data = api_get("teams", {"search": team_name})
    results = data.get("response", [])

    if not results:
        return None

    for item in results:
        name = item.get("team", {}).get("name", "").lower()
        if team_name.lower() == name:
            return item["team"]

    return results[0]["team"]

def get_last_matches(team_id, last=10):
    data = api_get("fixtures", {
        "team": team_id,
        "last": last,
        "status": "FT"
    })
    return data.get("response", [])

def get_h2h(team1_id, team2_id):
    data = api_get("fixtures/headtohead", {
        "h2h": f"{team1_id}-{team2_id}",
        "last": 10
    })
    return data.get("response", [])

def analyze_form(matches, team_id):
    played = len(matches)
    wins = draws = losses = 0
    goals_for = goals_against = 0

    for m in matches:
        teams = m.get("teams", {})
        goals = m.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")

        hg = goals.get("home") or 0
        ag = goals.get("away") or 0

        if team_id == home_id:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg

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
    team1_wins = team2_wins = draws = 0
    total_goals = 0

    for m in matches:
        teams = m.get("teams", {})
        goals = m.get("goals", {})

        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")

        hg = goals.get("home") or 0
        ag = goals.get("away") or 0
        total_goals += hg + ag

        if hg == ag:
            draws += 1
        elif hg > ag:
            if home_id == team1_id:
                team1_wins += 1
            else:
                team2_wins += 1
        else:
            if away_id == team1_id:
                team1_wins += 1
            else:
                team2_wins += 1

    played = len(matches)

    return {
        "played": played,
        "team1_wins": team1_wins,
        "draws": draws,
        "team2_wins": team2_wins,
        "avg_total_goals": round(total_goals / played, 2) if played else 0,
    }

def calculate_probabilities(team1_form, team2_form, h2h):
    s1 = 50
    s2 = 50
    draw = 22

    s1 += team1_form["wins"] * 5
    s1 -= team1_form["losses"] * 4
    s1 += team1_form["avg_goals_for"] * 5
    s1 -= team1_form["avg_goals_against"] * 4

    s2 += team2_form["wins"] * 5
    s2 -= team2_form["losses"] * 4
    s2 += team2_form["avg_goals_for"] * 5
    s2 -= team2_form["avg_goals_against"] * 4

    s1 += h2h["team1_wins"] * 3
    s2 += h2h["team2_wins"] * 3
    draw += h2h["draws"] * 2

    total = max(s1 + s2 + draw, 1)

    p1 = round(s1 / total * 100)
    p2 = round(s2 / total * 100)
    x = 100 - p1 - p2

    return {
        "p1": max(5, p1),
        "draw": max(5, x),
        "p2": max(5, p2),
    }

def fixture_text(match):
    fixture = match.get("fixture", {})
    league = match.get("league", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})

    return {
        "date": fixture.get("date"),
        "league": league.get("name"),
        "home": teams.get("home", {}).get("name"),
        "away": teams.get("away", {}).get("name"),
        "score": f"{goals.get('home')}:{goals.get('away')}",
    }

def build_match_context(team1_name, team2_name):
    team1 = search_team(team1_name)
    team2 = search_team(team2_name)

    if not team1 or not team2:
        return None

    team1_last = get_last_matches(team1["id"], 10)
    team2_last = get_last_matches(team2["id"], 10)
    h2h_matches = get_h2h(team1["id"], team2["id"])

    team1_form = analyze_form(team1_last, team1["id"])
    team2_form = analyze_form(team2_last, team2["id"])
    h2h_analysis = analyze_h2h(h2h_matches, team1["id"], team2["id"])
    probabilities = calculate_probabilities(team1_form, team2_form, h2h_analysis)

    return {
        "team1": team1,
        "team2": team2,
        "team1_last_matches": [fixture_text(m) for m in team1_last],
        "team2_last_matches": [fixture_text(m) for m in team2_last],
        "head_to_head": [fixture_text(m) for m in h2h_matches],
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h_analysis": h2h_analysis,
        "probabilities": probabilities,
    }
