import os
import requests

API_KEY = os.getenv("THESPORTSDB_API_KEY", "123")
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

TEAM_MAP = {
    "реал": {"id": "133738", "name": "Real Madrid"},
    "реал мадрид": {"id": "133738", "name": "Real Madrid"},
    "real madrid": {"id": "133738", "name": "Real Madrid"},

    "псж": {"id": "133714", "name": "Paris Saint-Germain"},
    "psg": {"id": "133714", "name": "Paris Saint-Germain"},
    "paris sg": {"id": "133714", "name": "Paris Saint-Germain"},
    "paris saint-germain": {"id": "133714", "name": "Paris Saint-Germain"},

    "барселона": {"id": "133739", "name": "Barcelona"},
    "barcelona": {"id": "133739", "name": "Barcelona"},

    "ман сити": {"id": "133613", "name": "Manchester City"},
    "man city": {"id": "133613", "name": "Manchester City"},
    "manchester city": {"id": "133613", "name": "Manchester City"},

    "бавария": {"id": "133664", "name": "Bayern Munich"},
    "bayern": {"id": "133664", "name": "Bayern Munich"},
    "bayern munich": {"id": "133664", "name": "Bayern Munich"},
}


def normalize_key(name):
    return name.lower().strip()


def search_team(team_name):
    key = normalize_key(team_name)

    if key in TEAM_MAP:
        return TEAM_MAP[key]

    raise Exception(f"Команда не найдена: {team_name}")


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params or {}, timeout=20)
    response.raise_for_status()
    data = response.json()
    print("THESPORTSDB_DEBUG:", endpoint, params, flush=True)
    return data


def same_team(a, b):
    if not a or not b:
        return False

    def clean(x):
        return (
            x.lower()
            .replace("-", "")
            .replace(" ", "")
            .replace(".", "")
            .strip()
        )

    return clean(a) == clean(b)


def get_last_matches(team_id, count=10):
    data = api_get("eventslast.php", {"id": team_id})
    events = data.get("results") or []

    finished = []

    for event in events:
        if event.get("intHomeScore") is not None and event.get("intAwayScore") is not None:
            finished.append(event)

    return finished[:count]


def convert_event(event, team_name):
    home = event.get("strHomeTeam", "")
    away = event.get("strAwayTeam", "")

    home_score = int(event.get("intHomeScore") or 0)
    away_score = int(event.get("intAwayScore") or 0)

    if same_team(home, team_name):
        goals_for = home_score
        goals_against = away_score
    elif same_team(away, team_name):
        goals_for = away_score
        goals_against = home_score
    else:
        return None

    if goals_for > goals_against:
        result = "win"
    elif goals_for == goals_against:
        result = "draw"
    else:
        result = "loss"

    return {
        "home": home,
        "away": away,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "result": result,
        "league": event.get("strLeague", ""),
        "date": event.get("dateEvent", ""),
    }


def build_form(matches, team_name):
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0
    converted = []

    for event in matches:
        item = convert_event(event, team_name)

        if not item:
            continue

        converted.append(item)

        goals_for += item["goals_for"]
        goals_against += item["goals_against"]

        if item["result"] == "win":
            wins += 1
        elif item["result"] == "draw":
            draws += 1
        else:
            losses += 1

    played = len(converted)
    points = wins * 3 + draws

    form = {
        "matches": played,
        "points": points,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / played, 2) if played else 0,
        "avg_goals_against": round(goals_against / played, 2) if played else 0,
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
