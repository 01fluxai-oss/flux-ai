import os
import requests

API_KEY = os.getenv("THESPORTSDB_API_KEY", "123")
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

ALIASES = {
    "реал мадрид": "Real Madrid",
    "real madrid": "Real Madrid",
    "псж": "Paris SG",
    "psg": "Paris SG",
    "paris saint-germain": "Paris SG",
    "барселона": "Barcelona",
    "barcelona": "Barcelona",
    "ман сити": "Manchester City",
    "man city": "Manchester City",
    "бавария": "Bayern Munich",
    "bayern": "Bayern Munich",
}


def normalize_team_name(name):
    key = name.lower().strip()
    return ALIASES.get(key, name.strip())


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params or {}, timeout=20)
    data = response.json()
    print("THESPORTSDB_DEBUG:", endpoint, params, data, flush=True)
    return data


def search_team(team_name):
    team_name = normalize_team_name(team_name)
    data = api_get("searchteams.php", {"t": team_name})

    teams = data.get("teams") or []
    if not teams:
        raise Exception(f"Команда не найдена: {team_name}")

    team = teams[0]

    return {
        "id": team.get("idTeam"),
        "name": team.get("strTeam"),
        "league": team.get("strLeague"),
        "country": team.get("strCountry"),
    }


def get_last_matches(team_id, count=10):
    data = api_get("eventslast.php", {"id": team_id})
    events = data.get("results") or []

    finished = []
    for event in events:
        if event.get("intHomeScore") is not None and event.get("intAwayScore") is not None:
            finished.append(event)

    return finished[:count]


def convert_event(event, team_name):
    home = event.get("strHomeTeam")
    away = event.get("strAwayTeam")

    home_goals = int(event.get("intHomeScore") or 0)
    away_goals = int(event.get("intAwayScore") or 0)

    if team_name == home:
        gf, ga = home_goals, away_goals
    elif team_name == away:
        gf, ga = away_goals, home_goals
    else:
        gf, ga = 0, 0

    if gf > ga:
        result = "win"
    elif gf == ga:
        result = "draw"
    else:
        result = "loss"

    return {
        "home": home,
        "away": away,
        "goals_for": gf,
        "goals_against": ga,
        "result": result,
        "date": event.get("dateEvent"),
        "league": event.get("strLeague"),
    }


def build_form(matches, team_name):
    wins = draws = losses = 0
    goals_for = 0
    goals_against = 0
    counted = 0

    converted = []

    for event in matches:
        item = convert_event(event, team_name)
        converted.append(item)

        if item["result"] == "win":
            wins += 1
        elif item["result"] == "draw":
            draws += 1
        else:
            losses += 1

        goals_for += item["goals_for"]
        goals_against += item["goals_against"]
        counted += 1

    points = wins * 3 + draws
    matches_count = max(counted, 1)

    form = {
        "matches": counted,
        "points": points,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / matches_count, 2),
        "avg_goals_against": round(goals_against / matches_count, 2),
    }

    print("FORM_DEBUG:", team_name, form, converted, flush=True)

    return form


def get_match_data(team1, team2):
    team1_data = search_team(team1)
    team2_data = search_team(team2)

    team1_matches = get_last_matches(team1_data["id"], 10)
    team2_matches = get_last_matches(team2_data["id"], 10)

    team1_form = build_form(team1_matches, team1_data["name"])
    team2_form = build_form(team2_matches, team2_data["name"])

    return {
        "source": "TheSportsDB",
        "team1": team1_data["name"],
        "team2": team2_data["name"],
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h": {
            "matches": 0,
            "team1_wins": 0,
            "draws": 0,
            "team2_wins": 0,
        },
    }
