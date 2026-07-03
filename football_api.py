import os
import requests

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

TEAMS = {
    "реал мадрид": {"id": 86, "name": "Real Madrid"},
    "real madrid": {"id": 86, "name": "Real Madrid"},
    "псж": {"id": 524, "name": "Paris Saint-Germain"},
    "psg": {"id": 524, "name": "Paris Saint-Germain"},
    "барселона": {"id": 81, "name": "FC Barcelona"},
    "barcelona": {"id": 81, "name": "FC Barcelona"},
    "ман сити": {"id": 65, "name": "Manchester City FC"},
    "man city": {"id": 65, "name": "Manchester City FC"},
    "бавария": {"id": 5, "name": "FC Bayern München"},
    "bayern": {"id": 5, "name": "FC Bayern München"},
}


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

    print("FOOTBALL_DATA_DEBUG:", endpoint, params, data, flush=True)
    return data


def search_team(team_name):
    key = team_name.lower().strip()
    team = TEAMS.get(key)

    if not team:
        return None

    return {
        "id": team["id"],
        "name": team["name"],
        "country": None,
    }


def convert_match(match):
    home = match.get("homeTeam", {})
    away = match.get("awayTeam", {})
    score = match.get("score", {}).get("fullTime", {})

    return {
        "fixture": {
            "date": match.get("utcDate"),
        },
        "league": {
            "name": match.get("competition", {}).get("name"),
        },
        "teams": {
            "home": {"name": home.get("name")},
            "away": {"name": away.get("name")},
        },
        "goals": {
            "home": score.get("home"),
            "away": score.get("away"),
        },
    }


def get_last_matches(team_id, count=10):
    data = api_get(
        f"teams/{team_id}/matches",
        {
            "status": "FINISHED",
            "limit": count,
        },
    )

    matches = data.get("matches", [])
    return [convert_match(m) for m in matches[:count]]


def get_h2h(team1_id, team2_id, count=5):
    # Football-Data free tier не всегда дает прямой H2H.
    # Пока возвращаем пустой список, чтобы бот работал стабильно.
    return []
