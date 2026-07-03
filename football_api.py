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
    "бавария": "Bayern Munich",
    "bayern": "Bayern Munich",
}


def normalize_team_name(name):
    key = name.lower().strip()
    return ALIASES.get(key, name.strip())


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params or {},
        timeout=20,
    )

    try:
        data = response.json()
    except Exception:
        data = {"error": "Invalid JSON", "text": response.text}

    print("API_DEBUG:", endpoint, params, data, flush=True)
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


def get_last_matches(team_id, count=10):
    data = api_get("fixtures", {"team": team_id, "last": count})
    return data.get("response", [])


def get_h2h(team1_id, team2_id, count=5):
    data = api_get(
        "fixtures/headtohead",
        {
            "h2h": f"{team1_id}-{team2_id}",
            "last": count,
        },
    )
    return data.get("response", [])
