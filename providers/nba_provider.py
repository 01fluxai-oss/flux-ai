import os
from datetime import date, timedelta

import requests


API_KEY = os.environ["BALLDONTLIE_API_KEY"]

BASE_URL = "https://api.balldontlie.io/v1"

REQUEST_TIMEOUT = 20
MIN_VALID_GAMES = 5
FORM_GAMES_LIMIT = 10


TEAM_ALIASES = {
    # Boston Celtics
    "boston": "Boston Celtics",
    "boston celtics": "Boston Celtics",
    "celtics": "Boston Celtics",
    "бостон": "Boston Celtics",
    "селтикс": "Boston Celtics",

    # Los Angeles Lakers
    "la lakers": "Los Angeles Lakers",
    "los angeles lakers": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers",
    "лейкерс": "Los Angeles Lakers",
    "лос анджелес лейкерс": "Los Angeles Lakers",

    # Golden State Warriors
    "golden state": "Golden State Warriors",
    "golden state warriors": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "голден стэйт": "Golden State Warriors",
    "уорриорз": "Golden State Warriors",

    # New York Knicks
    "new york": "New York Knicks",
    "new york knicks": "New York Knicks",
    "knicks": "New York Knicks",
    "никс": "New York Knicks",
    "нью йорк никс": "New York Knicks",

    # Brooklyn Nets
    "brooklyn": "Brooklyn Nets",
    "brooklyn nets": "Brooklyn Nets",
    "nets": "Brooklyn Nets",
    "бруклин": "Brooklyn Nets",
    "бруклин нетс": "Brooklyn Nets",

    # Miami Heat
    "miami": "Miami Heat",
    "miami heat": "Miami Heat",
    "heat": "Miami Heat",
    "майами": "Miami Heat",
    "майами хит": "Miami Heat",

    # Chicago Bulls
    "chicago": "Chicago Bulls",
    "chicago bulls": "Chicago Bulls",
    "bulls": "Chicago Bulls",
    "чикаго": "Chicago Bulls",
    "чикаго буллз": "Chicago Bulls",

    # Milwaukee Bucks
    "milwaukee": "Milwaukee Bucks",
    "milwaukee bucks": "Milwaukee Bucks",
    "bucks": "Milwaukee Bucks",
    "милуоки": "Milwaukee Bucks",
    "милуоки бакс": "Milwaukee Bucks",

    # Philadelphia 76ers
    "philadelphia": "Philadelphia 76ers",
    "philadelphia 76ers": "Philadelphia 76ers",
    "76ers": "Philadelphia 76ers",
    "sixers": "Philadelphia 76ers",
    "филадельфия": "Philadelphia 76ers",
    "сиксерс": "Philadelphia 76ers",

    # Cleveland Cavaliers
    "cleveland": "Cleveland Cavaliers",
    "cleveland cavaliers": "Cleveland Cavaliers",
    "cavaliers": "Cleveland Cavaliers",
    "cavs": "Cleveland Cavaliers",
    "кливленд": "Cleveland Cavaliers",
    "кавалерс": "Cleveland Cavaliers",

    # Denver Nuggets
    "denver": "Denver Nuggets",
    "denver nuggets": "Denver Nuggets",
    "nuggets": "Denver Nuggets",
    "денвер": "Denver Nuggets",
    "наггетс": "Denver Nuggets",

    # Dallas Mavericks
    "dallas": "Dallas Mavericks",
    "dallas mavericks": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks",
    "mavs": "Dallas Mavericks",
    "даллас": "Dallas Mavericks",
    "маверикс": "Dallas Mavericks",

    # Phoenix Suns
    "phoenix": "Phoenix Suns",
    "phoenix suns": "Phoenix Suns",
    "suns": "Phoenix Suns",
    "финикс": "Phoenix Suns",
    "санс": "Phoenix Suns",

    # Los Angeles Clippers
    "la clippers": "LA Clippers",
    "los angeles clippers": "LA Clippers",
    "clippers": "LA Clippers",
    "клипперс": "LA Clippers",
    "лос анджелес клипперс": "LA Clippers",

    # Oklahoma City Thunder
    "oklahoma city": "Oklahoma City Thunder",
    "oklahoma city thunder": "Oklahoma City Thunder",
    "okc": "Oklahoma City Thunder",
    "thunder": "Oklahoma City Thunder",
    "оклахома": "Oklahoma City Thunder",
    "тандер": "Oklahoma City Thunder",

    # Minnesota Timberwolves
    "minnesota": "Minnesota Timberwolves",
    "minnesota timberwolves": "Minnesota Timberwolves",
    "timberwolves": "Minnesota Timberwolves",
    "wolves": "Minnesota Timberwolves",
    "миннесота": "Minnesota Timberwolves",
    "тимбервулвз": "Minnesota Timberwolves",

    # Houston Rockets
    "houston": "Houston Rockets",
    "houston rockets": "Houston Rockets",
    "rockets": "Houston Rockets",
    "хьюстон": "Houston Rockets",
    "рокетс": "Houston Rockets",

    # San Antonio Spurs
    "san antonio": "San Antonio Spurs",
    "san antonio spurs": "San Antonio Spurs",
    "spurs": "San Antonio Spurs",
    "сан антонио": "San Antonio Spurs",
    "сперс": "San Antonio Spurs",

    # Memphis Grizzlies
    "memphis": "Memphis Grizzlies",
    "memphis grizzlies": "Memphis Grizzlies",
    "grizzlies": "Memphis Grizzlies",
    "мемфис": "Memphis Grizzlies",
    "гриззлис": "Memphis Grizzlies",

    # Sacramento Kings
    "sacramento": "Sacramento Kings",
    "sacramento kings": "Sacramento Kings",
    "kings": "Sacramento Kings",
    "сакраменто": "Sacramento Kings",
    "кингз": "Sacramento Kings",

    # Atlanta Hawks
    "atlanta": "Atlanta Hawks",
    "atlanta hawks": "Atlanta Hawks",
    "hawks": "Atlanta Hawks",
    "атланта": "Atlanta Hawks",
    "хокс": "Atlanta Hawks",

    # Indiana Pacers
    "indiana": "Indiana Pacers",
    "indiana pacers": "Indiana Pacers",
    "pacers": "Indiana Pacers",
    "индиана": "Indiana Pacers",
    "пэйсерс": "Indiana Pacers",

    # Orlando Magic
    "orlando": "Orlando Magic",
    "orlando magic": "Orlando Magic",
    "magic": "Orlando Magic",
    "орландо": "Orlando Magic",
    "мэджик": "Orlando Magic",

    # Toronto Raptors
    "toronto": "Toronto Raptors",
    "toronto raptors": "Toronto Raptors",
    "raptors": "Toronto Raptors",
    "торонто": "Toronto Raptors",
    "рэпторс": "Toronto Raptors",

    # Detroit Pistons
    "detroit": "Detroit Pistons",
    "detroit pistons": "Detroit Pistons",
    "pistons": "Detroit Pistons",
    "детройт": "Detroit Pistons",
    "пистонс": "Detroit Pistons",

    # Washington Wizards
    "washington": "Washington Wizards",
    "washington wizards": "Washington Wizards",
    "wizards": "Washington Wizards",
    "вашингтон": "Washington Wizards",
    "уизардс": "Washington Wizards",

    # Charlotte Hornets
    "charlotte": "Charlotte Hornets",
    "charlotte hornets": "Charlotte Hornets",
    "hornets": "Charlotte Hornets",
    "шарлотт": "Charlotte Hornets",
    "хорнетс": "Charlotte Hornets",

    # New Orleans Pelicans
    "new orleans": "New Orleans Pelicans",
    "new orleans pelicans": "New Orleans Pelicans",
    "pelicans": "New Orleans Pelicans",
    "нью орлеан": "New Orleans Pelicans",
    "пеликанс": "New Orleans Pelicans",

    # Portland Trail Blazers
    "portland": "Portland Trail Blazers",
    "portland trail blazers": "Portland Trail Blazers",
    "trail blazers": "Portland Trail Blazers",
    "blazers": "Portland Trail Blazers",
    "портленд": "Portland Trail Blazers",
    "блэйзерс": "Portland Trail Blazers",

    # Utah Jazz
    "utah": "Utah Jazz",
    "utah jazz": "Utah Jazz",
    "jazz": "Utah Jazz",
    "юта": "Utah Jazz",
    "джаз": "Utah Jazz",
}


def normalize_name(value):
    return (
        str(value)
        .lower()
        .strip()
        .replace("ё", "е")
        .replace(".", "")
        .replace("_", " ")
        .replace("-", " ")
    )


def api_get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"

    response = requests.get(
        url,
        headers={
            "Authorization": API_KEY,
            "Accept": "application/json",
        },
        params=params or {},
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 401:
        raise RuntimeError(
            "BALLDONTLIE authorization failed. "
            "Check BALLDONTLIE_API_KEY in Render."
        )

    if response.status_code == 429:
        raise RuntimeError(
            "BALLDONTLIE rate limit reached. "
            "Try again in one minute."
        )

    response.raise_for_status()

    try:
        return response.json()

    except ValueError as error:
        raise RuntimeError(
            "BALLDONTLIE returned invalid JSON."
        ) from error


def get_all_teams():
    payload = api_get("teams")
    teams = payload.get("data") or []

    if not teams:
        raise LookupError(
            "BALLDONTLIE returned no NBA teams."
        )

    return teams


def team_search_values(team):
    return {
        normalize_name(team.get("full_name", "")),
        normalize_name(team.get("name", "")),
        normalize_name(team.get("city", "")),
        normalize_name(team.get("abbreviation", "")),
    }


def search_team(team_name):
    normalized_input = normalize_name(team_name)

    canonical_name = TEAM_ALIASES.get(
        normalized_input,
        team_name,
    )

    normalized_canonical = normalize_name(
        canonical_name
    )

    teams = get_all_teams()

    for team in teams:
        values = team_search_values(team)

        if normalized_canonical in values:
            return team

    for team in teams:
        full_name = normalize_name(
            team.get("full_name", "")
        )

        if (
            normalized_canonical
            and normalized_canonical in full_name
        ):
            return team

    raise LookupError(
        f"NBA team not found: {team_name}"
    )


def get_finished_games(
    team_id,
    limit=FORM_GAMES_LIMIT,
):
    today = date.today()
    start_date = today - timedelta(days=420)

    params = {
        "team_ids[]": team_id,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "per_page": 100,
    }

    payload = api_get(
        "games",
        params=params,
    )

    games = payload.get("data") or []

    finished_games = []

    for game in games:
        status = normalize_name(
            game.get("status", "")
        )

        home_score = game.get(
            "home_team_score"
        )

        visitor_score = game.get(
            "visitor_team_score"
        )

        is_final = (
            status == "final"
            or (
                isinstance(home_score, int)
                and isinstance(visitor_score, int)
                and home_score > 0
                and visitor_score > 0
                and game.get("period", 0) >= 4
            )
        )

        if is_final:
            finished_games.append(game)

    finished_games.sort(
        key=lambda item: item.get(
            "date",
            "",
        ),
        reverse=True,
    )

    return finished_games[:limit]


def convert_game(game, team_id):
    home_team = game.get(
        "home_team",
        {},
    )

    visitor_team = game.get(
        "visitor_team",
        {},
    )

    home_id = home_team.get("id")
    visitor_id = visitor_team.get("id")

    home_score = int(
        game.get("home_team_score") or 0
    )

    visitor_score = int(
        game.get("visitor_team_score") or 0
    )

    if team_id == home_id:
        opponent = visitor_team.get(
            "full_name",
            "Unknown",
        )

        points_for = home_score
        points_against = visitor_score
        venue = "home"

    elif team_id == visitor_id:
        opponent = home_team.get(
            "full_name",
            "Unknown",
        )

        points_for = visitor_score
        points_against = home_score
        venue = "away"

    else:
        return None

    if points_for > points_against:
        result = "win"
        icon = "✅"

    else:
        result = "loss"
        icon = "❌"

    return {
        "opponent": opponent,
        "points_for": points_for,
        "points_against": points_against,
        "total_points": (
            points_for + points_against
        ),
        "margin": (
            points_for - points_against
        ),
        "result": result,
        "icon": icon,
        "venue": venue,
        "date": game.get("date", ""),
        "season": game.get("season"),
        "postseason": bool(
            game.get("postseason", False)
        ),
        "score": (
            f"{points_for}:"
            f"{points_against}"
        ),
    }


def build_team_form(
    team,
    games,
):
    team_id = team["id"]

    converted_games = []

    for game in games:
        converted = convert_game(
            game,
            team_id,
        )

        if converted:
            converted_games.append(
                converted
            )

    played = len(converted_games)

    if played == 0:
        return {
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "points_for": 0,
            "points_against": 0,
            "avg_points_for": 0,
            "avg_points_against": 0,
            "avg_total_points": 0,
            "avg_margin": 0,
            "home_matches": 0,
            "away_matches": 0,
            "recent": [],
            "data_quality": 0,
            "data_source": "BALLDONTLIE",
        }

    wins = sum(
        1
        for game in converted_games
        if game["result"] == "win"
    )

    losses = played - wins

    points_for = sum(
        game["points_for"]
        for game in converted_games
    )

    points_against = sum(
        game["points_against"]
        for game in converted_games
    )

    total_points = sum(
        game["total_points"]
        for game in converted_games
    )

    total_margin = sum(
        game["margin"]
        for game in converted_games
    )

    home_matches = sum(
        1
        for game in converted_games
        if game["venue"] == "home"
    )

    away_matches = (
        played - home_matches
    )

    data_quality = min(
        100,
        round(
            played
            / FORM_GAMES_LIMIT
            * 100
        ),
    )

    return {
        "matches": played,
        "wins": wins,
        "losses": losses,
        "win_rate": round(
            wins / played * 100,
        ),
        "points_for": points_for,
        "points_against": points_against,
        "avg_points_for": round(
            points_for / played,
            1,
        ),
        "avg_points_against": round(
            points_against / played,
            1,
        ),
        "avg_total_points": round(
            total_points / played,
            1,
        ),
        "avg_margin": round(
            total_margin / played,
            1,
        ),
        "home_matches": home_matches,
        "away_matches": away_matches,
        "recent": converted_games[:5],
        "data_quality": data_quality,
        "data_source": "BALLDONTLIE",
    }


def get_team_data(team_name):
    team = search_team(team_name)

    games = get_finished_games(
        team["id"],
        limit=FORM_GAMES_LIMIT,
    )

    form = build_team_form(
        team,
        games,
    )

    return {
        "team": team,
        "form": form,
    }


def get_nba_match_data(
    team1_name,
    team2_name,
):
    team1_data = get_team_data(
        team1_name
    )

    team2_data = get_team_data(
        team2_name
    )

    team1 = team1_data["team"]
    team2 = team2_data["team"]

    if team1["id"] == team2["id"]:
        raise ValueError(
            "Choose two different NBA teams."
        )

    team1_form = team1_data["form"]
    team2_form = team2_data["form"]

    if (
        team1_form["matches"]
        < MIN_VALID_GAMES
        or team2_form["matches"]
        < MIN_VALID_GAMES
    ):
        data_warning = (
            "Limited recent game data"
        )
    else:
        data_warning = None

    return {
        "source": "BALLDONTLIE",
        "team1": {
            "id": team1["id"],
            "name": team1["full_name"],
            "abbreviation": team1[
                "abbreviation"
            ],
            "conference": team1[
                "conference"
            ],
            "division": team1[
                "division"
            ],
        },
        "team2": {
            "id": team2["id"],
            "name": team2["full_name"],
            "abbreviation": team2[
                "abbreviation"
            ],
            "conference": team2[
                "conference"
            ],
            "division": team2[
                "division"
            ],
        },
        "team1_form": team1_form,
        "team2_form": team2_form,
        "data_warning": data_warning,
        "data_quality": min(
            team1_form["data_quality"],
            team2_form["data_quality"],
        ),
    }


__all__ = [
    "search_team",
    "get_finished_games",
    "build_team_form",
    "get_team_data",
    "get_nba_match_data",
]
