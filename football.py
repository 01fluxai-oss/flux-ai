import os
import requests

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}


ALIASES = {
    "псж": "Paris Saint Germain",
    "psg": "Paris Saint Germain",
    "реал мадрид": "Real Madrid",
    "real madrid": "Real Madrid",
    "барселона": "Barcelona",
    "barcelona": "Barcelona",
    "ман сити": "Manchester City",
    "man city": "Manchester City",
    "манчестер сити": "Manchester City",
    "ливерпуль": "Liverpool",
    "liverpool": "Liverpool",
    "арсенал": "Arsenal",
    "arsenal": "Arsenal",
    "челси": "Chelsea",
    "chelsea": "Chelsea",
    "бавария": "Bayern Munich",
    "bayern": "Bayern Munich",
}


def normalize_team_name(name):
    key = name.lower().strip()
    return ALIASES.get(key, name.strip())


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params or {}, timeout=20)
    data = r.json()
    print("API:", endpoint, params, data)
    return data


def search_team(team_name):
    team_name = normalize_team_name(team_name)

    data = api_get("teams", {"search": team_name})

    response = data.get("response", [])
    if not response:
        return None

    team = response[0]["team"]

    return {
        "id": team["id"],
        "name": team["name"],
        "country": team.get("country"),
    }


def get_last_matches(team_id, count=5):
    data = api_get("fixtures", {"team": team_id, "last": count})
    return data.get("response", [])


def get_h2h(team1_id, team2_id):
    data = api_get(
        "fixtures/headtohead",
        {
            "h2h": f"{team1_id}-{team2_id}",
            "last": 5,
        },
    )
    return data.get("response", [])


def simplify_match(match):
    fixture = match.get("fixture", {})
    league = match.get("league", {})
    teams = match.get("teams", {})
    goals = match.get("goals", {})

    home = teams.get("home", {}).get("name")
    away = teams.get("away", {}).get("name")

    home_goals = goals.get("home")
    away_goals = goals.get("away")

    return {
        "date": fixture.get("date"),
        "league": league.get("name"),
        "home": home,
        "away": away,
        "score": f"{home_goals}-{away_goals}",
    }


def team_form_score(matches, team_name):
    if not matches:
        return 0

    score = 0
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
            gf = home_goals
            ga = away_goals
        elif team_name == away:
            gf = away_goals
            ga = home_goals
        else:
            continue

        goals_for += gf
        goals_against += ga

        if gf > ga:
            score += 3
        elif gf == ga:
            score += 1

    return {
        "points": score,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "matches": len(matches),
    }


def calculate_probabilities(form1, form2):
    p1_strength = form1["points"] + form1["goals_for"] - form1["goals_against"]
    p2_strength = form2["points"] + form2["goals_for"] - form2["goals_against"]

    p1_strength = max(p1_strength, 1)
    p2_strength = max(p2_strength, 1)

    total = p1_strength + p2_strength + 4

    p1 = round((p1_strength / total) * 100)
    p2 = round((p2_strength / total) * 100)
    draw = 100 - p1 - p2

    if draw < 15:
        diff = 15 - draw
        draw = 15
        if p1 > p2:
            p1 -= diff
        else:
            p2 -= diff

    return {
        "p1": p1,
        "draw": draw,
        "p2": p2,
    }


def calculate_totals(form1, form2):
    total_goals = (
        form1["goals_for"]
        + form1["goals_against"]
        + form2["goals_for"]
        + form2["goals_against"]
    )

    games = max(form1["matches"] + form2["matches"], 1)
    avg_goals = total_goals / games

    over = round(min(max(avg_goals / 3.2 * 100, 35), 80))
    under = 100 - over

    both_score = round(min(max(avg_goals / 3.0 * 100, 35), 80))

    return {
        "over_2_5": over,
        "under_2_5": under,
        "btts_yes": both_score,
        "btts_no": 100 - both_score,
        "avg_goals": round(avg_goals, 2),
    }


def analyze_match(team1_name, team2_name):
    team1 = search_team(team1_name)
    team2 = search_team(team2_name)

    if not team1:
        return {
            "success": False,
            "error": f"Команда '{team1_name}' не найдена",
        }

    if not team2:
        return {
            "success": False,
            "error": f"Команда '{team2_name}' не найдена",
        }

    team1_matches_raw = get_last_matches(team1["id"], 5)
    team2_matches_raw = get_last_matches(team2["id"], 5)
    h2h_raw = get_h2h(team1["id"], team2["id"])

    team1_form = team_form_score(team1_matches_raw, team1["name"])
    team2_form = team_form_score(team2_matches_raw, team2["name"])

    probabilities = calculate_probabilities(team1_form, team2_form)
    totals = calculate_totals(team1_form, team2_form)

    return {
        "success": True,
        "team1": team1,
        "team2": team2,
        "probabilities": probabilities,
        "totals": totals,
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_last_matches": [simplify_match(m) for m in team1_matches_raw],
        "team2_last_matches": [simplify_match(m) for m in team2_matches_raw],
        "head_to_head": [simplify_match(m) for m in h2h_raw],
    }
