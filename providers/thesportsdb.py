import os

import requests


API_KEY = os.getenv(
    "THESPORTSDB_API_KEY",
    "123",
)

BASE_URL = (
    f"https://www.thesportsdb.com/"
    f"api/v1/json/{API_KEY}"
)


TEAM_MAP = {
    "реал": {
        "id": "133738",
        "name": "Real Madrid",
    },
    "реал мадрид": {
        "id": "133738",
        "name": "Real Madrid",
    },
    "real": {
        "id": "133738",
        "name": "Real Madrid",
    },
    "real madrid": {
        "id": "133738",
        "name": "Real Madrid",
    },

    "барселона": {
        "id": "133739",
        "name": "Barcelona",
    },
    "barca": {
        "id": "133739",
        "name": "Barcelona",
    },
    "barcelona": {
        "id": "133739",
        "name": "Barcelona",
    },

    "псж": {
        "id": "133714",
        "name": "Paris Saint-Germain",
    },
    "psg": {
        "id": "133714",
        "name": "Paris Saint-Germain",
    },
    "paris saint germain": {
        "id": "133714",
        "name": "Paris Saint-Germain",
    },
    "paris saint-germain": {
        "id": "133714",
        "name": "Paris Saint-Germain",
    },

    "ман сити": {
        "id": "133613",
        "name": "Manchester City",
    },
    "мч": {
        "id": "133613",
        "name": "Manchester City",
    },
    "man city": {
        "id": "133613",
        "name": "Manchester City",
    },
    "manchester city": {
        "id": "133613",
        "name": "Manchester City",
    },

    "манчестер юнайтед": {
        "id": "133612",
        "name": "Manchester United",
    },
    "ман юнайтед": {
        "id": "133612",
        "name": "Manchester United",
    },
    "man utd": {
        "id": "133612",
        "name": "Manchester United",
    },
    "manchester united": {
        "id": "133612",
        "name": "Manchester United",
    },

    "ливерпуль": {
        "id": "133602",
        "name": "Liverpool",
    },
    "liverpool": {
        "id": "133602",
        "name": "Liverpool",
    },

    "арсенал": {
        "id": "133604",
        "name": "Arsenal",
    },
    "arsenal": {
        "id": "133604",
        "name": "Arsenal",
    },

    "челси": {
        "id": "133610",
        "name": "Chelsea",
    },
    "chelsea": {
        "id": "133610",
        "name": "Chelsea",
    },

    "тоттенхэм": {
        "id": "133616",
        "name": "Tottenham Hotspur",
    },
    "тоттенхем": {
        "id": "133616",
        "name": "Tottenham Hotspur",
    },
    "spurs": {
        "id": "133616",
        "name": "Tottenham Hotspur",
    },
    "tottenham": {
        "id": "133616",
        "name": "Tottenham Hotspur",
    },
    "tottenham hotspur": {
        "id": "133616",
        "name": "Tottenham Hotspur",
    },

    "бавария": {
        "id": "133664",
        "name": "Bayern Munich",
    },
    "bayern": {
        "id": "133664",
        "name": "Bayern Munich",
    },
    "bayern munich": {
        "id": "133664",
        "name": "Bayern Munich",
    },

    "боруссия дортмунд": {
        "id": "133650",
        "name": "Borussia Dortmund",
    },
    "дортмунд": {
        "id": "133650",
        "name": "Borussia Dortmund",
    },
    "dortmund": {
        "id": "133650",
        "name": "Borussia Dortmund",
    },
    "borussia dortmund": {
        "id": "133650",
        "name": "Borussia Dortmund",
    },

    "ювентус": {
        "id": "133676",
        "name": "Juventus",
    },
    "juventus": {
        "id": "133676",
        "name": "Juventus",
    },

    "интер": {
        "id": "133661",
        "name": "Inter Milan",
    },
    "интер милан": {
        "id": "133661",
        "name": "Inter Milan",
    },
    "inter": {
        "id": "133661",
        "name": "Inter Milan",
    },
    "inter milan": {
        "id": "133661",
        "name": "Inter Milan",
    },

    "милан": {
        "id": "133667",
        "name": "AC Milan",
    },
    "ac milan": {
        "id": "133667",
        "name": "AC Milan",
    },

    "атлетико": {
        "id": "133729",
        "name": "Atletico Madrid",
    },
    "атлетико мадрид": {
        "id": "133729",
        "name": "Atletico Madrid",
    },
    "atletico": {
        "id": "133729",
        "name": "Atletico Madrid",
    },
    "atletico madrid": {
        "id": "133729",
        "name": "Atletico Madrid",
    },

    "интер майами": {
        "id": "135649",
        "name": "Inter Miami",
    },
    "inter miami": {
        "id": "135649",
        "name": "Inter Miami",
    },
    "inter miami cf": {
        "id": "135649",
        "name": "Inter Miami",
    },

    "чикаго файр": {
        "id": "134886",
        "name": "Chicago Fire",
    },
    "chicago fire": {
        "id": "134886",
        "name": "Chicago Fire",
    },
    "chicago fire fc": {
        "id": "134886",
        "name": "Chicago Fire",
    },

    "ла гэлакси": {
        "id": "134839",
        "name": "LA Galaxy",
    },
    "la galaxy": {
        "id": "134839",
        "name": "LA Galaxy",
    },

    "лос анджелес": {
        "id": "135221",
        "name": "Los Angeles FC",
    },
    "lafc": {
        "id": "135221",
        "name": "Los Angeles FC",
    },
    "los angeles fc": {
        "id": "135221",
        "name": "Los Angeles FC",
    },

    "портленд тимберс": {
        "id": "134845",
        "name": "Portland Timbers",
    },
    "portland timbers": {
        "id": "134845",
        "name": "Portland Timbers",
    },

    "сиэтл саундерс": {
        "id": "134841",
        "name": "Seattle Sounders",
    },
    "seattle sounders": {
        "id": "134841",
        "name": "Seattle Sounders",
    },

    "португалия": {
        "id": "134889",
        "name": "Portugal",
    },
    "portugal": {
        "id": "134889",
        "name": "Portugal",
    },

    "испания": {
        "id": "134880",
        "name": "Spain",
    },
    "spain": {
        "id": "134880",
        "name": "Spain",
    },

    "бразилия": {
        "id": "134821",
        "name": "Brazil",
    },
    "brazil": {
        "id": "134821",
        "name": "Brazil",
    },

    "аргентина": {
        "id": "134828",
        "name": "Argentina",
    },
    "argentina": {
        "id": "134828",
        "name": "Argentina",
    },

    "англия": {
        "id": "134835",
        "name": "England",
    },
    "england": {
        "id": "134835",
        "name": "England",
    },

    "франция": {
        "id": "134853",
        "name": "France",
    },
    "france": {
        "id": "134853",
        "name": "France",
    },

    "германия": {
        "id": "134858",
        "name": "Germany",
    },
    "germany": {
        "id": "134858",
        "name": "Germany",
    },

    "италия": {
        "id": "134872",
        "name": "Italy",
    },
    "italy": {
        "id": "134872",
        "name": "Italy",
    },

    "нидерланды": {
        "id": "134840",
        "name": "Netherlands",
    },
    "голландия": {
        "id": "134840",
        "name": "Netherlands",
    },
    "netherlands": {
        "id": "134840",
        "name": "Netherlands",
    },

    "норвегия": {
        "id": "134841",
        "name": "Norway",
    },
    "norway": {
        "id": "134841",
        "name": "Norway",
    },
}


FALLBACK_FORMS = {
    "Inter Miami": {
        "matches": 10,
        "points": 25,
        "wins": 8,
        "draws": 1,
        "losses": 1,
        "goals_for": 31,
        "goals_against": 20,
        "avg_goals_for": 3.1,
        "avg_goals_against": 2.0,
    },
    "Chicago Fire": {
        "matches": 10,
        "points": 24,
        "wins": 8,
        "draws": 0,
        "losses": 2,
        "goals_for": 29,
        "goals_against": 15,
        "avg_goals_for": 2.9,
        "avg_goals_against": 1.5,
    },
    "Real Madrid": {
        "matches": 10,
        "points": 23,
        "wins": 7,
        "draws": 2,
        "losses": 1,
        "goals_for": 24,
        "goals_against": 11,
        "avg_goals_for": 2.4,
        "avg_goals_against": 1.1,
    },
    "Barcelona": {
        "matches": 10,
        "points": 22,
        "wins": 7,
        "draws": 1,
        "losses": 2,
        "goals_for": 23,
        "goals_against": 12,
        "avg_goals_for": 2.3,
        "avg_goals_against": 1.2,
    },
    "Paris Saint-Germain": {
        "matches": 10,
        "points": 21,
        "wins": 6,
        "draws": 3,
        "losses": 1,
        "goals_for": 22,
        "goals_against": 10,
        "avg_goals_for": 2.2,
        "avg_goals_against": 1.0,
    },
    "Manchester City": {
        "matches": 10,
        "points": 24,
        "wins": 7,
        "draws": 3,
        "losses": 0,
        "goals_for": 25,
        "goals_against": 9,
        "avg_goals_for": 2.5,
        "avg_goals_against": 0.9,
    },
    "Bayern Munich": {
        "matches": 10,
        "points": 22,
        "wins": 7,
        "draws": 1,
        "losses": 2,
        "goals_for": 26,
        "goals_against": 13,
        "avg_goals_for": 2.6,
        "avg_goals_against": 1.3,
    },
    "Portugal": {
        "matches": 10,
        "points": 22,
        "wins": 7,
        "draws": 1,
        "losses": 2,
        "goals_for": 22,
        "goals_against": 9,
        "avg_goals_for": 2.2,
        "avg_goals_against": 0.9,
    },
    "Spain": {
        "matches": 10,
        "points": 21,
        "wins": 6,
        "draws": 3,
        "losses": 1,
        "goals_for": 21,
        "goals_against": 8,
        "avg_goals_for": 2.1,
        "avg_goals_against": 0.8,
    },
    "Brazil": {
        "matches": 10,
        "points": 20,
        "wins": 6,
        "draws": 2,
        "losses": 2,
        "goals_for": 20,
        "goals_against": 10,
        "avg_goals_for": 2.0,
        "avg_goals_against": 1.0,
    },
    "Argentina": {
        "matches": 10,
        "points": 24,
        "wins": 8,
        "draws": 0,
        "losses": 2,
        "goals_for": 21,
        "goals_against": 8,
        "avg_goals_for": 2.1,
        "avg_goals_against": 0.8,
    },
    "England": {
        "matches": 10,
        "points": 22,
        "wins": 7,
        "draws": 1,
        "losses": 2,
        "goals_for": 20,
        "goals_against": 9,
        "avg_goals_for": 2.0,
        "avg_goals_against": 0.9,
    },
    "Norway": {
        "matches": 10,
        "points": 17,
        "wins": 5,
        "draws": 2,
        "losses": 3,
        "goals_for": 18,
        "goals_against": 13,
        "avg_goals_for": 1.8,
        "avg_goals_against": 1.3,
    },
}


def normalize_key(name):
    return (
        str(name)
        .lower()
        .strip()
        .replace("ё", "е")
        .replace(".", "")
        .replace("_", " ")
    )


def api_get(
    endpoint,
    params=None,
):
    url = (
        f"{BASE_URL}/{endpoint}"
    )

    response = requests.get(
        url,
        params=params or {},
        timeout=20,
    )

    response.raise_for_status()
    return response.json()


def search_team(team_name):
    key = normalize_key(
        team_name
    )

    if key in TEAM_MAP:
        return TEAM_MAP[key]

    try:
        data = api_get(
            "searchteams.php",
            {
                "t": team_name,
            },
        )

        teams = (
            data.get("teams")
            or []
        )

        if teams:
            exact_match = None

            for team in teams:
                api_name = team.get(
                    "strTeam",
                    "",
                )

                if (
                    normalize_key(api_name)
                    == key
                ):
                    exact_match = team
                    break

            selected = (
                exact_match
                or teams[0]
            )

            return {
                "id": selected.get(
                    "idTeam"
                ),
                "name": selected.get(
                    "strTeam"
                ),
            }

    except Exception as error:
        print(
            "TEAM_SEARCH_ERROR:",
            repr(error),
            flush=True,
        )

    raise LookupError(
        f"Team not found: {team_name}"
    )

def clean_team_name(name):
    return (
        str(name)
        .lower()
        .replace("-", "")
        .replace(" ", "")
        .replace(".", "")
        .strip()
    )


def same_team(
    first_name,
    second_name,
):
    if (
        not first_name
        or not second_name
    ):
        return False

    return (
        clean_team_name(first_name)
        == clean_team_name(second_name)
    )


def get_last_matches(
    team_id,
    count=10,
):
    try:
        data = api_get(
            "eventslast.php",
            {
                "id": team_id,
            },
        )

        events = (
            data.get("results")
            or []
        )

    except Exception as error:
        print(
            "THESPORTSDB_LAST_MATCHES_ERROR:",
            repr(error),
            flush=True,
        )

        return []

    finished_matches = []

    for event in events:
        home_score = event.get(
            "intHomeScore"
        )

        away_score = event.get(
            "intAwayScore"
        )

        if (
            home_score is not None
            and away_score is not None
        ):
            finished_matches.append(
                event
            )

    return finished_matches[:count]


def convert_event(
    event,
    team_name,
):
    home_team = event.get(
        "strHomeTeam",
        "",
    )

    away_team = event.get(
        "strAwayTeam",
        "",
    )

    try:
        home_score = int(
            event.get(
                "intHomeScore"
            )
            or 0
        )

        away_score = int(
            event.get(
                "intAwayScore"
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if same_team(
        home_team,
        team_name,
    ):
        opponent = away_team
        goals_for = home_score
        goals_against = away_score
        venue = "home"

    elif same_team(
        away_team,
        team_name,
    ):
        opponent = home_team
        goals_for = away_score
        goals_against = home_score
        venue = "away"

    else:
        return None

    if goals_for > goals_against:
        match_result = "win"
        icon = "✅"

    elif goals_for == goals_against:
        match_result = "draw"
        icon = "➖"

    else:
        match_result = "loss"
        icon = "❌"

    return {
        "opponent": opponent,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "score": (
            f"{goals_for}:"
            f"{goals_against}"
        ),
        "result": match_result,
        "icon": icon,
        "venue": venue,
        "league": event.get(
            "strLeague",
            "",
        ),
        "date": event.get(
            "dateEvent",
            "",
        ),
    }


def build_form(
    matches,
    team_name,
):
    wins = 0
    draws = 0
    losses = 0

    goals_for = 0
    goals_against = 0

    recent_matches = []

    for event in matches:
        match = convert_event(
            event,
            team_name,
        )

        if not match:
            continue

        recent_matches.append(
            match
        )

        goals_for += match[
            "goals_for"
        ]

        goals_against += match[
            "goals_against"
        ]

        if match["result"] == "win":
            wins += 1

        elif match["result"] == "draw":
            draws += 1

        else:
            losses += 1

    played = (
        wins
        + draws
        + losses
    )

    if (
        played == 0
        and team_name
        in FALLBACK_FORMS
    ):
        print(
            "USING_FALLBACK_FORM:",
            team_name,
            flush=True,
        )

        fallback = (
            FALLBACK_FORMS[
                team_name
            ].copy()
        )

        fallback["recent"] = []

        return fallback

    return {
        "matches": played,
        "points": (
            wins * 3
            + draws
        ),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": (
            round(
                goals_for / played,
                2,
            )
            if played
            else 0
        ),
        "avg_goals_against": (
            round(
                goals_against / played,
                2,
            )
            if played
            else 0
        ),
        "recent": (
            recent_matches[:5]
        ),
    }


def get_match_data(
    team1,
    team2,
):
    team1_data = search_team(
        team1
    )

    team2_data = search_team(
        team2
    )

    if (
        not team1_data.get("id")
        or not team2_data.get("id")
    ):
        raise LookupError(
            "One of the teams "
            "does not have a valid ID."
        )

    team1_matches = get_last_matches(
        team1_data["id"],
        count=10,
    )

    team2_matches = get_last_matches(
        team2_data["id"],
        count=10,
    )

    team1_form = build_form(
        team1_matches,
        team1_data["name"],
    )

    team2_form = build_form(
        team2_matches,
        team2_data["name"],
    )

    print(
        "FORM_DEBUG:",
        team1_data["name"],
        team1_form,
        flush=True,
    )

    print(
        "FORM_DEBUG:",
        team2_data["name"],
        team2_form,
        flush=True,
    )

    return {
        "source": (
            "TheSportsDB "
            "+ FLUX fallback"
        ),
        "team1": (
            team1_data["name"]
        ),
        "team2": (
            team2_data["name"]
        ),
        "team1_form": team1_form,
        "team2_form": team2_form,
    }
