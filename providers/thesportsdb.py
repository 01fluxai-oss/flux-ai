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

    "барселона": {"id": "133739", "name": "Barcelona"},
    "barcelona": {"id": "133739", "name": "Barcelona"},

    "ман сити": {"id": "133613", "name": "Manchester City"},
    "man city": {"id": "133613", "name": "Manchester City"},
    "manchester city": {"id": "133613", "name": "Manchester City"},

    "бавария": {"id": "133664", "name": "Bayern Munich"},
    "bayern": {"id": "133664", "name": "Bayern Munich"},
    "bayern munich": {"id": "133664", "name": "Bayern Munich"},

    "portugal": {"id": "134889", "name": "Portugal"},
    "португалия": {"id": "134889", "name": "Portugal"},

    "spain": {"id": "134880", "name": "Spain"},
    "испания": {"id": "134880", "name": "Spain"},

    "brazil": {"id": "134821", "name": "Brazil"},
    "бразилия": {"id": "134821", "name": "Brazil"},

    "norway": {"id": "134841", "name": "Norway"},
    "норвегия": {"id": "134841", "name": "Norway"},
}


FALLBACK_FORMS = {
    "Real Madrid": {
        "matches": 10, "points": 23, "wins": 7, "draws": 2, "losses": 1,
        "goals_for": 24, "goals_against": 11,
        "avg_goals_for": 2.4, "avg_goals_against": 1.1,
    },
    "Paris Saint-Germain": {
        "matches": 10, "points": 21, "wins": 6, "draws": 3, "losses": 1,
        "goals_for": 22, "goals_against": 10,
        "avg_goals_for": 2.2, "avg_goals_against": 1.0,
    },
    "Barcelona": {
        "matches": 10, "points": 22, "wins": 7, "draws": 1, "losses": 2,
        "goals_for": 23, "goals_against": 12,
        "avg_goals_for": 2.3, "avg_goals_against": 1.2,
    },
    "Manchester City": {
        "matches": 10, "points": 24, "wins": 7, "draws": 3, "losses": 0,
        "goals_for": 25, "goals_against": 9,
        "avg_goals_for": 2.5, "avg_goals_against": 0.9,
    },
    "Bayern Munich": {
        "matches": 10, "points": 22, "wins": 7, "draws": 1, "losses": 2,
        "goals_for": 26, "goals_against": 13,
        "avg_goals_for": 2.6, "avg_goals_against": 1.3,
    },
    "Portugal": {
        "matches": 10, "points": 22, "wins": 7, "draws": 1, "losses": 2,
        "goals_for": 22, "goals_against": 9,
        "avg_goals_for": 2.2, "avg_goals_against": 0.9,
    },
    "Spain": {
        "matches": 10, "points": 21, "wins": 6, "draws": 3, "losses": 1,
        "goals_for": 21, "goals_against": 8,
        "avg_goals_for": 2.1, "avg_goals_against": 0.8,
    },
    "Brazil": {
        "matches": 10, "points": 20, "wins": 6, "draws": 2, "losses": 2,
        "goals_for": 20, "goals_against": 10,
        "avg_goals_for": 2.0, "avg_goals_against": 1.0,
    },
    "Norway": {
        "matches": 10, "points": 17, "wins": 5, "draws": 2, "losses": 3,
        "goals_for": 18, "goals_against": 13,
        "avg_goals_for": 1.8, "avg_goals_against": 1.3,
    },
}


def normalize_key(name):
    return str(name).lower().strip()


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params or {}, timeout=20)
    response.raise_for_status()
    return response.json()


def search_team(team_name):
    key = normalize_key(team_name)

    if key in TEAM_MAP:
        return TEAM_MAP[key]

    try:
        data = api_get("searchteams.php", {"t": team_name})
        teams = data.get("teams") or []

        if teams:
            team = teams[0]
            return {
                "id": team.get("idTeam"),
                "name": team.get("strTeam"),
            }

    except Exception as e:
        print("TEAM_SEARCH_ERROR:", e, flush=True)

    raise Exception(f"Команда не найдена: {team_name}")


def clean_team_name(name):
    return (
        str(name)
        .lower()
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
        .strip()
    )


def same_team(a, b):
    if not a or not b:
        return False

    return clean_team_name(a) == clean_team_name(b)


def get_last_matches(team_id, count=10):
    try:
        data = api_get("eventslast.php", {"id": team_id})
        events = data.get("results") or []
    except Exception as e:
        print("THESPORTSDB_LAST_MATCHES_ERROR:", e, flush=True)
        return []

    finished = []

    for event in events:
        if event.get("intHomeScore") is not None and event.get("intAwayScore") is not None:
            finished.append(event)

    return finished[:count]


def convert_event(event, team_name):
    home = event.get("strHomeTeam", "")
    away = event.get("strAwayTeam", "")

    try:
        home_score = int(event.get("intHomeScore") or 0)
        away_score = int(event.get("intAwayScore") or 0)
    except Exception:
        return None

    if same_team(home, team_name):
        opponent = away
        gf = home_score
        ga = away_score
        venue = "home"
    elif same_team(away, team_name):
        opponent = home
        gf = away_score
        ga = home_score
        venue = "away"
    else:
        return None

    if gf > ga:
        result = "win"
        icon = "✅"
    elif gf == ga:
        result = "draw"
        icon = "➖"
    else:
        result = "loss"
        icon = "❌"

    return {
        "opponent": opponent,
        "goals_for": gf,
        "goals_against": ga,
        "score": f"{gf}:{ga}",
        "result": result,
        "icon": icon,
        "venue": venue,
        "league": event.get("strLeague", ""),
        "date": event.get("dateEvent", ""),
    }


def build_form(matches, team_name):
    wins = draws = losses = 0
    goals_for = goals_against = 0
    recent = []

    for event in matches:
        item = convert_event(event, team_name)

        if not item:
            continue

        recent.append(item)

        goals_for += item["goals_for"]
        goals_against += item["goals_against"]

        if item["result"] == "win":
            wins += 1
        elif item["result"] == "draw":
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses

    if played == 0 and team_name in FALLBACK_FORMS:
        print("USING_FALLBACK_FORM:", team_name, flush=True)
        form = FALLBACK_FORMS[team_name].copy()
        form["recent"] = []
        return form

    return {
        "matches": played,
        "points": wins * 3 + draws,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / played, 2) if played else 0,
        "avg_goals_against": round(goals_against / played, 2) if played else 0,
        "recent": recent[:5],
    }


def build_h2h_placeholder():
    return {
        "matches": 0,
        "team1_wins": 0,
        "draws": 0,
        "team2_wins": 0,
        "note": "H2H data not connected yet",
    }


def get_match_data(team1, team2):
    team1_data = search_team(team1)
    team2_data = search_team(team2)

    team1_matches = get_last_matches(team1_data["id"], 10)
    team2_matches = get_last_matches(team2_data["id"], 10)

    team1_form = build_form(team1_matches, team1_data["name"])
    team2_form = build_form(team2_matches, team2_data["name"])

    print("FORM_DEBUG:", team1_data["name"], team1_form, flush=True)
    print("FORM_DEBUG:", team2_data["name"], team2_form, flush=True)

    return {
        "source": "TheSportsDB + FLUX fallback",
        "team1": team1_data["name"],
        "team2": team2_data["name"],
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h": build_h2h_placeholder(),
    }
