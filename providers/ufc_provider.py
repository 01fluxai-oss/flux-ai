# -*- coding: utf-8 -*-
import os
import re
import time
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests


BASE_URL = "https://api.citoapi.com/api/v1"
REQUEST_TIMEOUT = 25
CITO_API_KEY = os.environ.get("CITO_API_KEY", "").strip()

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "FLUX-AI-Sports/5.1",
})


class UFCProviderError(Exception):
    pass


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_name(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    text = clean_text(value)
    text = text.replace("%", "").replace(",", ".")

    if not text or text in {"--", "---", "null", "none"}:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def similarity(first: str, second: str) -> float:
    return SequenceMatcher(
        None,
        normalize_name(first),
        normalize_name(second),
    ).ratio()


def require_api_key() -> str:
    if not CITO_API_KEY:
        raise UFCProviderError(
            "CITO_API_KEY is missing in Render Environment."
        )

    return CITO_API_KEY


def api_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    api_key = require_api_key()
    url = f"{BASE_URL}{path}"

    try:
        response = session.get(
            url,
            params=params,
            headers={"x-api-key": api_key},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as error:
        raise UFCProviderError(
            f"Cito API connection failed: {type(error).__name__}: {error}"
        ) from error

    if response.status_code == 401:
        raise UFCProviderError(
            "Cito API rejected the key. Check CITO_API_KEY."
        )

    if response.status_code == 403:
        raise UFCProviderError(
            "Cito API access denied for this endpoint or plan."
        )

    if response.status_code == 404:
        raise UFCProviderError(
            f"Cito API endpoint or record was not found: {path}"
        )

    if response.status_code == 429:
        raise UFCProviderError(
            "Cito API rate limit reached. Try again later."
        )

    if not response.ok:
        raise UFCProviderError(
            f"Cito API error {response.status_code}: "
            f"{response.text[:300]}"
        )

    try:
        return response.json()
    except ValueError as error:
        raise UFCProviderError(
            "Cito API returned invalid JSON."
        ) from error


def walk_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value

        for nested in value.values():
            yield from walk_dicts(nested)

    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def first_value(
    data: Dict[str, Any],
    *keys: str,
) -> Any:
    lowered = {
        str(key).lower(): value
        for key, value in data.items()
    }

    for key in keys:
        value = lowered.get(key.lower())

        if value not in (None, "", [], {}):
            return value

    return None


def extract_name(data: Dict[str, Any]) -> str:
    direct = first_value(
        data,
        "name",
        "fullName",
        "full_name",
        "displayName",
        "display_name",
        "fighterName",
        "fighter_name",
        "athleteName",
        "athlete_name",
    )

    if direct:
        return clean_text(direct)

    first_name = first_value(
        data,
        "firstName",
        "first_name",
        "givenName",
        "given_name",
    )
    last_name = first_value(
        data,
        "lastName",
        "last_name",
        "familyName",
        "family_name",
    )

    return clean_text(f"{first_name or ''} {last_name or ''}")


def extract_slug(data: Dict[str, Any]) -> str:
    value = first_value(
        data,
        "slug",
        "fighterSlug",
        "fighter_slug",
        "athleteSlug",
        "athlete_slug",
        "id",
        "fighterId",
        "fighter_id",
        "athleteId",
        "athlete_id",
    )

    return clean_text(value)


def looks_like_fighter(data: Dict[str, Any]) -> bool:
    name = extract_name(data)
    slug = extract_slug(data)

    if not name or not slug:
        return False

    type_value = clean_text(
        first_value(
            data,
            "type",
            "entityType",
            "entity_type",
            "kind",
            "category",
        )
    ).lower()

    if type_value and not any(
        word in type_value
        for word in ("fighter", "athlete", "competitor")
    ):
        return False

    return True


def find_best_fighter(
    search_payload: Any,
    requested_name: str,
) -> Optional[Dict[str, Any]]:
    candidates = []

    for item in walk_dicts(search_payload):
        if not looks_like_fighter(item):
            continue

        name = extract_name(item)
        score = similarity(requested_name, name)

        candidates.append({
            "name": name,
            "slug": extract_slug(item),
            "similarity": score,
            "raw": item,
        })

    if not candidates:
        return None

    target = normalize_name(requested_name)

    for candidate in candidates:
        if normalize_name(candidate["name"]) == target:
            candidate["similarity"] = 1.0
            return candidate

    candidates.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    best = candidates[0]

    if best["similarity"] < 0.66:
        return None

    return best


@lru_cache(maxsize=256)
def search_fighter(fighter_name: str) -> Optional[Dict[str, Any]]:
    fighter_name = clean_text(fighter_name)

    if not fighter_name:
        return None

    payload = api_get(
        "/ufc/search",
        params={"q": fighter_name},
    )

    best = find_best_fighter(
        payload,
        fighter_name,
    )

    if best:
        print(
            f"CITO_UFC_SEARCH requested={fighter_name!r} "
            f"found={best['name']!r} "
            f"slug={best['slug']!r} "
            f"score={best['similarity']:.3f}",
            flush=True,
        )
    else:
        print(
            f"CITO_UFC_SEARCH_NOT_FOUND requested={fighter_name!r}",
            flush=True,
        )

    return best


def nested_value(
    payload: Any,
    *keys: str,
) -> Any:
    for item in walk_dicts(payload):
        value = first_value(item, *keys)

        if value not in (None, "", [], {}):
            return value

    return None


def make_record(profile: Any) -> Optional[str]:
    record = nested_value(
        profile,
        "record",
        "professionalRecord",
        "professional_record",
    )

    if isinstance(record, str) and re.match(
        r"^\d+\s*-\s*\d+\s*-\s*\d+",
        record.strip(),
    ):
        return record.strip().replace(" ", "")

    wins = nested_value(
        profile,
        "wins",
        "winCount",
        "win_count",
    )
    losses = nested_value(
        profile,
        "losses",
        "lossCount",
        "loss_count",
    )
    draws = nested_value(
        profile,
        "draws",
        "drawCount",
        "draw_count",
    )

    if wins is None or losses is None:
        return None

    return f"{int(float(wins))}-{int(float(losses))}-{int(float(draws or 0))}"


def extract_stat(
    payload: Any,
    *keys: str,
) -> Optional[float]:
    value = nested_value(payload, *keys)
    return safe_float(value)


def normalize_outcome(value: Any) -> str:
    text = clean_text(value).lower()

    mapping = {
        "w": "W",
        "win": "W",
        "winner": "W",
        "victory": "W",
        "l": "L",
        "loss": "L",
        "lost": "L",
        "defeat": "L",
        "d": "D",
        "draw": "D",
        "nc": "NC",
        "no contest": "NC",
        "no_contest": "NC",
    }

    return mapping.get(text, "")


def extract_recent_fights(
    payload: Any,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    rows = payload.get("data")

    if not isinstance(rows, list):
        return []

    fights = []

    for item in rows:
        if not isinstance(item, dict):
            continue

        outcome = normalize_outcome(
            item.get("outcome")
        )

        # Upcoming/unconfirmed bouts can have outcome=None.
        if not outcome:
            continue

        opponent = item.get("opponent") or {}
        event = item.get("event") or {}
        bout = item.get("bout") or {}

        if not isinstance(opponent, dict):
            opponent = {}

        if not isinstance(event, dict):
            event = {}

        if not isinstance(bout, dict):
            bout = {}

        fights.append({
            "result": outcome,
            "fighters": [
                clean_text(opponent.get("name"))
            ] if clean_text(opponent.get("name")) else [],
            "event": clean_text(
                event.get("title")
            ),
            "date": clean_text(
                event.get("eventDate")
                or event.get("startsAt")
                or event.get("venueDate")
            ),
            "method": clean_text(
                bout.get("method")
            ),
            "round": clean_text(
                bout.get("resultRound")
            ),
            "time": clean_text(
                bout.get("resultTime")
            ),
        })

        if len(fights) >= limit:
            break

    return fights


@lru_cache(maxsize=256)
def get_fighter_profile_by_slug(
    slug: str,
) -> Dict[str, Any]:
    slug = clean_text(slug)

    if not slug:
        raise UFCProviderError("Fighter slug is missing.")

    encoded_slug = quote(slug, safe="")

    profile_payload = api_get(
        f"/ufc/fighters/{encoded_slug}"
    )
    stats_payload = api_get(
        f"/ufc/fighters/{encoded_slug}/stats"
    )
    fights_payload = api_get(
        f"/ufc/fighters/{encoded_slug}/fights"
    )

    name = clean_text(
        nested_value(
            profile_payload,
            "name",
            "fullName",
            "full_name",
            "displayName",
            "display_name",
        )
    )

    if not name:
        for item in walk_dicts(profile_payload):
            possible = extract_name(item)

            if possible:
                name = possible
                break

    if not name:
        raise UFCProviderError(
            f"Could not read fighter name for slug: {slug}"
        )

    profile = {
        "name": name,
        "record": make_record(profile_payload),
        "height": clean_text(
            nested_value(
                profile_payload,
                "height",
                "heightText",
                "height_text",
            )
        ) or None,
        "weight": clean_text(
            nested_value(
                profile_payload,
                "weight",
                "weightText",
                "weight_text",
                "weightClass",
                "weight_class",
            )
        ) or None,
        "reach": clean_text(
            nested_value(
                profile_payload,
                "reach",
                "reachText",
                "reach_text",
            )
        ) or None,
        "stance": clean_text(
            nested_value(
                profile_payload,
                "stance",
                "fightingStance",
                "fighting_stance",
            )
        ) or None,
        "dob": clean_text(
            nested_value(
                profile_payload,
                "dob",
                "dateOfBirth",
                "date_of_birth",
                "birthDate",
                "birth_date",
            )
        ) or None,
        "slpm": extract_stat(
            stats_payload,
            "slpm",
            "sigStrikesLandedPerMin",
            "significantStrikesLandedPerMinute",
            "significant_strikes_landed_per_minute",
            "sigStrikesLandedPerMinute",
            "sig_strikes_landed_per_minute",
        ),
        "striking_accuracy": extract_stat(
            stats_payload,
            "strikingAccuracy",
            "striking_accuracy",
            "significantStrikeAccuracy",
            "significant_strike_accuracy",
            "sigStrAccuracy",
            "sig_str_accuracy",
        ),
        "sapm": extract_stat(
            stats_payload,
            "sapm",
            "sigStrikesAbsorbedPerMin",
            "significantStrikesAbsorbedPerMinute",
            "significant_strikes_absorbed_per_minute",
            "sigStrikesAbsorbedPerMinute",
            "sig_strikes_absorbed_per_minute",
        ),
        "striking_defense": extract_stat(
            stats_payload,
            "strikingDefense",
            "striking_defense",
            "sigStrikeDefense",
            "significantStrikeDefense",
            "significant_strike_defense",
            "sigStrDefense",
            "sig_str_defense",
        ),
        "takedown_average": extract_stat(
            stats_payload,
            "takedownAvgPer15Min",
            "takedownAverage",
            "takedown_average",
            "takedownsPer15Minutes",
            "takedowns_per_15_minutes",
            "tdAvg",
            "td_avg",
        ),
        "takedown_accuracy": extract_stat(
            stats_payload,
            "takedownAccuracy",
            "takedown_accuracy",
            "tdAccuracy",
            "td_accuracy",
        ),
        "takedown_defense": extract_stat(
            stats_payload,
            "takedownDefense",
            "takedown_defense",
            "tdDefense",
            "td_defense",
        ),
        "submission_average": extract_stat(
            stats_payload,
            "submissionAvgPer15Min",
            "submissionAverage",
            "submission_average",
            "submissionAttemptsPer15Minutes",
            "submission_attempts_per_15_minutes",
            "subAvg",
            "sub_avg",
        ),
        "recent_fights": extract_recent_fights(
            fights_payload,
            limit=5,
        ),
        "profile_url": (
            f"https://citoapi.com/docs/api/ufc/"
        ),
        "source": "Cito API",
        "data_quality": "real",
        "slug": slug,
    }

    print(
        f"CITO_UFC_PROFILE name={name!r} "
        f"record={profile['record']!r} "
        f"recent_fights={len(profile['recent_fights'])}",
        flush=True,
    )

    return profile


def get_fighter_profile(
    fighter_name: str,
) -> Optional[Dict[str, Any]]:
    found = search_fighter(fighter_name)

    if not found:
        return None

    profile = dict(
        get_fighter_profile_by_slug(
            found["slug"]
        )
    )

    profile["search_name"] = clean_text(fighter_name)
    profile["match_similarity"] = round(
        found.get("similarity", 1.0),
        3,
    )

    return profile


def compare_fighters(
    fighter1_name: str,
    fighter2_name: str,
) -> Dict[str, Any]:
    started_at = time.time()
    fighter1 = None
    fighter2 = None
    errors = []

    try:
        fighter1 = get_fighter_profile(
            fighter1_name
        )
    except UFCProviderError as error:
        errors.append(
            f"{clean_text(fighter1_name)}: {error}"
        )

    try:
        fighter2 = get_fighter_profile(
            fighter2_name
        )
    except UFCProviderError as error:
        errors.append(
            f"{clean_text(fighter2_name)}: {error}"
        )

    if errors:
        print(
            "CITO_UFC_COMPARE_ERRORS:",
            " | ".join(errors),
            flush=True,
        )

    missing = []

    if not fighter1:
        missing.append(clean_text(fighter1_name))

    if not fighter2:
        missing.append(clean_text(fighter2_name))

    return {
        "fighter1": fighter1,
        "fighter2": fighter2,
        "missing": missing,
        "errors": errors,
        "source": "Cito API",
        "real_data": bool(fighter1 and fighter2),
        "response_time_seconds": round(
            time.time() - started_at,
            2,
        ),
    }
