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
    "paris saint-germain": {"id": "133714", "name": "Paris Saint-Germain"},
    "paris sg": {"id": "133714", "name": "Paris Saint-Germain"},

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
    r = requests.get(url, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def get_last_matches(team_id):
    data = api_get("eventslast.php", {"id": team_id})
    return data.get("results", []) or []


def same_team(a, b):
    return a.lower().replace("-", "").replace(" ", "") == \
           b.lower().replace("-", "").replace(" ", "")
    def convert_event(event, team_name):
    home = event.get("strHomeTeam", "")
    away = event.get("strAwayTeam", "")

    if same_team(home, team_name):
        gf = int(event.get("intHomeScore") or 0)
        ga = int(event.get("intAwayScore") or 0)
    elif same_team(away, team_name):
        gf = int(event.get("intAwayScore") or 0)
        ga = int(event.get("intHomeScore") or 0)
    else:
        return None

    if gf > ga:
        result = "win"
    elif gf == ga:
        result = "draw"
    else:
        result = "loss"

    return {
        "goals_for": gf,
        "goals_against": ga,
        "result": result,
        "league": event.get("strLeague", ""),
        "date": event.get("dateEvent", "")
    }


def build_form(matches, team_name):
    wins = draws = losses = 0
    gf = ga = 0
    converted = []

    for event in matches:
        item = convert_event(event, team_name)
        if not item:
            continue

        converted.append(item)

        gf += item["goals_for"]
        ga += item["goals_against"]

        if item["result"] == "win":
            wins += 1
        elif item["result"] == "draw":
            draws += 1
        else:
            losses += 1

    played = len(converted)

    return {
        "matches": played,
        "points": wins * 3 + draws,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "avg_goals_for": round(gf / played, 2) if played else 0,
        "avg_goals_against": round(ga / played, 2) if played else 0,
    }
    def get_match_data(team1, team2):
    team1_data = search_team(team1)
    team2_data = search_team(team2)

    team1_matches = get_last_matches(team1_data["id"])
    team2_matches = get_last_matches(team2_data["id"])

    team1_form = build_form(team1_matches, team1_data["name"])
    team2_form = build_form(team2_matches, team2_data["name"])

    print("FORM_DEBUG:", team1_data["name"], team1_form, flush=True)
    print("FORM_DEBUG:", team2_data["name"], team2_form, flush=True)

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
