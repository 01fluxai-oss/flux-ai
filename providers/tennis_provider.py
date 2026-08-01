import os
import re
import unicodedata
from difflib import SequenceMatcher

import requests


BASE_URL = "https://api.api-tennis.com/tennis/"
API_KEY = os.environ.get("TENNIS_API_KEY", "").strip()
TIMEOUT = 25


class TennisAPIError(RuntimeError):
    pass


def _normalize_name(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _name_similarity(query, candidate):
    query_norm = _normalize_name(query)
    candidate_norm = _normalize_name(candidate)

    if not query_norm or not candidate_norm:
        return 0.0

    if query_norm == candidate_norm:
        return 1.0

    query_parts = query_norm.split()
    candidate_parts = candidate_norm.split()

    surname_match = (
        query_parts[-1] == candidate_parts[-1]
        if query_parts and candidate_parts
        else False
    )

    score = SequenceMatcher(
        None,
        query_norm,
        candidate_norm,
    ).ratio()

    if surname_match:
        score += 0.15

    return min(score, 1.0)


def _request(method, **params):
    if not API_KEY:
        raise TennisAPIError(
            "TENNIS_API_KEY is missing in environment variables."
        )

    payload = {
        "method": method,
        "APIkey": API_KEY,
        **params,
    }

    try:
        response = requests.get(
            BASE_URL,
            params=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise TennisAPIError(
            f"API-Tennis request failed: {error}"
        ) from error
    except ValueError as error:
        raise TennisAPIError(
            "API-Tennis returned invalid JSON."
        ) from error

    if int(data.get("success", 0)) != 1:
        raise TennisAPIError(
            f"API-Tennis error: {data}"
        )

    return data.get("result")


def get_standings(event_type):
    event_type = str(event_type).upper()

    if event_type not in {"ATP", "WTA"}:
        raise ValueError("event_type must be ATP or WTA")

    result = _request(
        "get_standings",
        event_type=event_type,
    )

    return result if isinstance(result, list) else []


def find_player(player_name):
    candidates = []

    for league in ("ATP", "WTA"):
        try:
            standings = get_standings(league)
        except TennisAPIError:
            standings = []

        for row in standings:
            name = row.get("player")
            player_key = row.get("player_key")

            if not name or not player_key:
                continue

            score = _name_similarity(
                player_name,
                name,
            )

            candidates.append({
                "player_key": str(player_key),
                "player_name": name,
                "league": league,
                "rank": _safe_int(row.get("place")),
                "points": _safe_int(row.get("points")),
                "country": row.get("country"),
                "match_score": score,
            })

    if not candidates:
        raise TennisAPIError(
            f"No standings data available for player: {player_name}"
        )

    candidates.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    best = candidates[0]

    if best["match_score"] < 0.58:
        raise TennisAPIError(
            f"Player not found with enough confidence: {player_name}"
        )

    return best


def get_player_profile(player_key):
    result = _request(
        "get_players",
        player_key=player_key,
    )

    if isinstance(result, list) and result:
        return result[0]

    return {}


def get_h2h(first_player_key, second_player_key):
    result = _request(
        "get_H2H",
        first_player_key=first_player_key,
        second_player_key=second_player_key,
    )

    return result if isinstance(result, dict) else {}


def _safe_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _winner_for_player(match, player_key):
    first_key = str(match.get("first_player_key") or "")
    second_key = str(match.get("second_player_key") or "")
    winner = str(match.get("event_winner") or "")

    if str(player_key) == first_key:
        return winner == "First Player"

    if str(player_key) == second_key:
        return winner == "Second Player"

    return None


def summarize_recent_results(matches, player_key, limit=10):
    recent = []

    for match in matches or []:
        won = _winner_for_player(
            match,
            player_key,
        )

        if won is None:
            continue

        recent.append({
            "won": won,
            "date": match.get("event_date"),
            "tournament": match.get("tournament_name"),
            "round": match.get("tournament_round"),
            "result": match.get("event_final_result"),
            "event_type": match.get("event_type_type"),
        })

        if len(recent) >= limit:
            break

    wins = sum(1 for item in recent if item["won"])
    losses = len(recent) - wins

    return {
        "matches": recent,
        "wins": wins,
        "losses": losses,
        "count": len(recent),
        "win_rate": (
            round(wins / len(recent) * 100)
            if recent
            else None
        ),
    }


def summarize_h2h(matches, first_player_key, second_player_key):
    first_wins = 0
    second_wins = 0
    counted = 0

    for match in matches or []:
        winner = str(match.get("event_winner") or "")
        first_key = str(match.get("first_player_key") or "")
        second_key = str(match.get("second_player_key") or "")

        if {
            first_key,
            second_key,
        } != {
            str(first_player_key),
            str(second_player_key),
        }:
            continue

        if winner == "First Player":
            winner_key = first_key
        elif winner == "Second Player":
            winner_key = second_key
        else:
            continue

        if winner_key == str(first_player_key):
            first_wins += 1
        elif winner_key == str(second_player_key):
            second_wins += 1

        counted += 1

    return {
        "matches": counted,
        "first_wins": first_wins,
        "second_wins": second_wins,
    }


def latest_singles_stats(profile):
    stats = profile.get("stats") or []

    singles_rows = [
        row for row in stats
        if str(row.get("type") or "").lower() == "singles"
    ]

    if not singles_rows:
        return {}

    singles_rows.sort(
        key=lambda row: _safe_int(
            row.get("season"),
            0,
        ),
        reverse=True,
    )

    row = singles_rows[0]

    return {
        "season": row.get("season"),
        "rank": _safe_int(row.get("rank")),
        "titles": _safe_int(row.get("titles"), 0),
        "matches_won": _safe_int(row.get("matches_won"), 0),
        "matches_lost": _safe_int(row.get("matches_lost"), 0),
        "hard_won": _safe_int(row.get("hard_won"), 0),
        "hard_lost": _safe_int(row.get("hard_lost"), 0),
        "clay_won": _safe_int(row.get("clay_won"), 0),
        "clay_lost": _safe_int(row.get("clay_lost"), 0),
        "grass_won": _safe_int(row.get("grass_won"), 0),
        "grass_lost": _safe_int(row.get("grass_lost"), 0),
    }


def get_real_tennis_data(player1_name, player2_name):
    player1 = find_player(player1_name)
    player2 = find_player(player2_name)

    profile1 = get_player_profile(
        player1["player_key"]
    )
    profile2 = get_player_profile(
        player2["player_key"]
    )

    h2h_payload = get_h2h(
        player1["player_key"],
        player2["player_key"],
    )

    recent1 = summarize_recent_results(
        h2h_payload.get("firstPlayerResults"),
        player1["player_key"],
    )
    recent2 = summarize_recent_results(
        h2h_payload.get("secondPlayerResults"),
        player2["player_key"],
    )
    h2h = summarize_h2h(
        h2h_payload.get("H2H"),
        player1["player_key"],
        player2["player_key"],
    )

    profile_stats1 = latest_singles_stats(profile1)
    profile_stats2 = latest_singles_stats(profile2)

    quality_components = [
        bool(player1.get("rank")),
        bool(player2.get("rank")),
        recent1["count"] >= 3,
        recent2["count"] >= 3,
        bool(profile_stats1),
        bool(profile_stats2),
        h2h["matches"] > 0,
    ]

    data_quality = round(
        sum(quality_components)
        / len(quality_components)
        * 100
    )

    return {
        "source": "API-Tennis",
        "player1": {
            **player1,
            "profile": profile1,
            "season_stats": profile_stats1,
            "recent": recent1,
        },
        "player2": {
            **player2,
            "profile": profile2,
            "season_stats": profile_stats2,
            "recent": recent2,
        },
        "h2h": h2h,
        "data_quality": data_quality,
    }
