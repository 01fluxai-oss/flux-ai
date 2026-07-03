import os
import requests

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"

def api_get(endpoint, params=None):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    return response.json()

def search_team(team_name):
    aliases = {
        "psg": "Paris Saint Germain",
        "paris": "Paris Saint Germain",
        "real madrid": "Real Madrid",
        "barcelona": "Barcelona",
        "man city": "Manchester City",
        "manchester city": "Manchester City",
        "liverpool": "Liverpool",
        "arsenal": "Arsenal",
        "chelsea": "Chelsea",
        "bayern": "Bayern Munich"
    }

    key = team_name.lower().strip()
    if key in aliases:
        team_name = aliases[key]

    data = api_get("teams", {"search": team_name})
    return data.get("response", [])[:5]

def get_today_fixtures():
    from datetime import date
    today = date.today().isoformat()
    data = api_get("fixtures", {"date": today})
    return data.get("response", [])[:10]

def get_h2h(team1_id, team2_id):
    data = api_get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": 5})
    return data.get("response", [])

def get_team_last_matches(team_id, last=5):
    data = api_get("fixtures", {"team": team_id, "last": last})
    return data.get("response", [])

def build_match_context(team1_name, team2_name):
    team1_results = search_team(team1_name)
    team2_results = search_team(team2_name)

    if not team1_results or not team2_results:
        return None

    team1 = team1_results[0]["team"]
    team2 = team2_results[0]["team"]

    team1_last = get_team_last_matches(team1["id"], 5)
    team2_last = get_team_last_matches(team2["id"], 5)
    h2h = get_h2h(team1["id"], team2["id"])

    return {
        "team1": team1,
        "team2": team2,
        "team1_last_matches": team1_last,
        "team2_last_matches": team2_last,
        "head_to_head": h2h,
    }
