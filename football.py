import os
import requests

API_KEY = os.getenv("FOOTBALL_API_KEY")

HEADERS = {
    "x-apisports-key": API_KEY
}

BASE_URL = "https://v3.football.api-sports.io"


def search_team(team_name):
    r = requests.get(
        f"{BASE_URL}/teams",
        headers=HEADERS,
        params={"search": team_name},
        timeout=20,
    )

    data = r.json()
    print("TEAM SEARCH:", team_name)
    print(data)

    if not data.get("response"):
        return None
    return data["response"][0]["team"]["id"]


def get_team_statistics(team_id):
    r = requests.get(
        f"{BASE_URL}/fixtures",
        headers=HEADERS,
        params={
            "team": team_id,
            "last": 5
        },
        timeout=20,
    )

    return r.json()


def analyze_match(team1, team2):
    team1_id = search_team(team1)
    team2_id = search_team(team2)

    if not team1_id:
        return {
            "success": False,
            "error": f"Команда '{team1}' не найдена."
        }

    if not team2_id:
        return {
            "success": False,
            "error": f"Команда '{team2}' не найдена."
        }

    data1 = get_team_statistics(team1_id)
    data2 = get_team_statistics(team2_id)

    return {
        "success": True,
        "team1": team1,
        "team2": team2,
        "team1_data": data1,
        "team2_data": data2
    }
