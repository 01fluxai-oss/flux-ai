# -*- coding: utf-8 -*-
import re
import time
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ufcstats.com"
REQUEST_TIMEOUT = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Verified direct UFCStats profile links.
# These two entries also make the first production test independent
# from the fighters-list search page.
DIRECT_FIGHTERS = {
    "islam makhachev": (
        "Islam Makhachev",
        "https://ufcstats.com/fighter-details/275aca31f61ba28c",
    ),
    "charles oliveira": (
        "Charles Oliveira",
        "https://ufcstats.com/fighter-details/07225ba28ae309b6",
    ),
}

session = requests.Session()
session.headers.update(HEADERS)


class UFCProviderError(Exception):
    pass


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_name(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def safe_float(value: Any) -> Optional[float]:
    text = clean_text(value)
    text = text.replace("%", "").replace(",", ".")

    if not text or text in {"--", "---"}:
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


def request_page(url: str) -> BeautifulSoup:
    url = clean_text(url).replace("http://ufcstats.com", BASE_URL)

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise UFCProviderError(
            f"UFCStats request failed: {type(error).__name__}: {error}"
        ) from error

    html = response.text or ""

    if len(html) < 500:
        raise UFCProviderError(
            f"UFCStats returned an unexpectedly short page "
            f"(status={response.status_code}, chars={len(html)})."
        )

    lowered = html.lower()

    blocked_markers = (
        "access denied",
        "captcha",
        "cloudflare",
        "temporarily unavailable",
        "request blocked",
    )

    if any(marker in lowered for marker in blocked_markers):
        raise UFCProviderError(
            "UFCStats appears to have blocked or challenged the request."
        )

    return BeautifulSoup(html, "html.parser")


def direct_fighter(fighter_name: str) -> Optional[Dict[str, Any]]:
    normalized = normalize_name(fighter_name)
    direct = DIRECT_FIGHTERS.get(normalized)

    if not direct:
        return None

    display_name, profile_url = direct

    return {
        "name": display_name,
        "url": profile_url,
        "record": "",
        "similarity": 1.0,
        "lookup": "direct",
    }


def get_search_letters(name: str) -> List[str]:
    parts = normalize_name(name).split()

    if not parts:
        return []

    # UFCStats list pages are organized by surname initial.
    # Try last-name initial first, then first-name initial.
    letters = []

    for part in [parts[-1], parts[0], *parts[1:-1]]:
        if part and part[0].isalpha() and part[0] not in letters:
            letters.append(part[0])

    return letters[:3]


@lru_cache(maxsize=64)
def get_fighters_by_letter(letter: str) -> List[Dict[str, str]]:
    letter = clean_text(letter).lower()[:1]

    if not letter or not letter.isalpha():
        return []

    soup = request_page(
        f"{BASE_URL}/statistics/fighters?char={letter}&page=all"
    )

    fighters: List[Dict[str, str]] = []

    for row in soup.select("tr.b-statistics__table-row"):
        columns = row.select("td.b-statistics__table-col")

        if len(columns) < 10:
            continue

        profile_links = row.select(
            "a.b-link.b-link_style_black[href*='/fighter-details/']"
        )

        if not profile_links:
            profile_links = row.select("a[href*='/fighter-details/']")

        if not profile_links:
            continue

        profile_url = clean_text(profile_links[0].get("href"))
        profile_url = profile_url.replace("http://ufcstats.com", BASE_URL)

        first_name = clean_text(columns[0].get_text(" ", strip=True))
        last_name = clean_text(columns[1].get_text(" ", strip=True))
        full_name = clean_text(f"{first_name} {last_name}")

        if not full_name or not profile_url:
            continue

        wins = clean_text(columns[7].get_text(" ", strip=True))
        losses = clean_text(columns[8].get_text(" ", strip=True))
        draws = clean_text(columns[9].get_text(" ", strip=True))

        record = (
            f"{wins}-{losses}-{draws}"
            if wins and losses and draws
            else ""
        )

        fighters.append({
            "name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "url": profile_url,
            "record": record,
            "lookup": "list",
        })

    print(
        f"UFC_LIST_PARSED letter={letter} fighters={len(fighters)}",
        flush=True,
    )

    return fighters


def find_fighter(
    fighter_name: str,
    minimum_similarity: float = 0.70,
) -> Optional[Dict[str, Any]]:
    fighter_name = clean_text(fighter_name)

    if not fighter_name:
        return None

    direct = direct_fighter(fighter_name)

    if direct:
        return direct

    target = normalize_name(fighter_name)
    candidates: List[Dict[str, Any]] = []
    seen_urls = set()
    errors = []

    for letter in get_search_letters(fighter_name):
        try:
            letter_fighters = get_fighters_by_letter(letter)
        except UFCProviderError as error:
            errors.append(f"{letter}: {error}")
            continue

        for fighter in letter_fighters:
            url = fighter.get("url")

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            candidates.append(fighter)

    for fighter in candidates:
        if normalize_name(fighter["name"]) == target:
            result = dict(fighter)
            result["similarity"] = 1.0
            return result

    if not candidates:
        if errors:
            print(
                "UFC_SEARCH_ERRORS:",
                " | ".join(errors),
                flush=True,
            )
        return None

    scored = sorted(
        (
            similarity(fighter_name, fighter["name"]),
            fighter,
        )
        for fighter in candidates
    )
    best_score, best_fighter = scored[-1]

    print(
        f"UFC_SEARCH name={fighter_name!r} "
        f"best={best_fighter['name']!r} score={best_score:.3f}",
        flush=True,
    )

    if best_score < minimum_similarity:
        return None

    result = dict(best_fighter)
    result["similarity"] = round(best_score, 3)
    return result


def parse_profile_item(
    soup: BeautifulSoup,
    label: str,
) -> Optional[str]:
    wanted = normalize_name(label)

    for item in soup.select("li.b-list__box-list-item"):
        title = item.select_one("i.b-list__box-item-title")

        if not title:
            continue

        title_text = normalize_name(title.get_text(" ", strip=True))

        if not title_text.startswith(wanted):
            continue

        full_text = clean_text(item.get_text(" ", strip=True))
        visible_title = clean_text(title.get_text(" ", strip=True))
        value = full_text.replace(visible_title, "", 1).strip()

        return value or None

    return None


def parse_record_from_title(soup: BeautifulSoup) -> Optional[str]:
    title = soup.select_one("span.b-content__title-record")

    if not title:
        return None

    text = clean_text(title.get_text(" ", strip=True))
    match = re.search(
        r"Record:\s*([0-9]+-[0-9]+-[0-9]+)",
        text,
        flags=re.IGNORECASE,
    )

    return match.group(1) if match else None


def parse_fighter_name(soup: BeautifulSoup) -> Optional[str]:
    title = soup.select_one("span.b-content__title-highlight")

    if not title:
        return None

    return clean_text(title.get_text(" ", strip=True)) or None


def parse_recent_fights(
    soup: BeautifulSoup,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    fights = []

    rows = soup.select(
        "tr.b-fight-details__table-row.b-fight-details__table-row__hover"
    )

    if not rows:
        rows = soup.select("tr.b-fight-details__table-row[data-link]")

    for row in rows[:limit]:
        columns = row.select("td.b-fight-details__table-col")

        if len(columns) < 10:
            continue

        result = clean_text(columns[0].get_text(" ", strip=True))
        fighter_names = [
            clean_text(link.get_text(" ", strip=True))
            for link in columns[1].select("a")
            if clean_text(link.get_text(" ", strip=True))
        ]

        event_link = columns[6].select_one("a")
        event_name = (
            clean_text(event_link.get_text(" ", strip=True))
            if event_link
            else ""
        )
        event_url = clean_text(event_link.get("href")) if event_link else ""
        event_url = event_url.replace("http://ufcstats.com", BASE_URL)

        method_lines = [
            clean_text(item.get_text(" ", strip=True))
            for item in columns[7].select("p")
            if clean_text(item.get_text(" ", strip=True))
        ]

        method = (
            " ".join(method_lines)
            if method_lines
            else clean_text(columns[7].get_text(" ", strip=True))
        )

        date_element = columns[6].select_one(
            ".b-fight-details__table-text"
        )

        fights.append({
            "result": result,
            "fighters": fighter_names,
            "event": event_name,
            "event_url": event_url,
            "date": (
                clean_text(date_element.get_text(" ", strip=True))
                if date_element
                else ""
            ),
            "method": method,
            "round": clean_text(columns[8].get_text(" ", strip=True)),
            "time": clean_text(columns[9].get_text(" ", strip=True)),
            "fight_url": clean_text(row.get("data-link")).replace(
                "http://ufcstats.com",
                BASE_URL,
            ),
        })

    return fights


@lru_cache(maxsize=256)
def get_fighter_profile_by_url(profile_url: str) -> Dict[str, Any]:
    profile_url = clean_text(profile_url).replace(
        "http://ufcstats.com",
        BASE_URL,
    )

    if not profile_url:
        raise UFCProviderError("Fighter profile URL is missing.")

    soup = request_page(profile_url)
    name = parse_fighter_name(soup)

    if not name:
        page_title = clean_text(
            soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )
        raise UFCProviderError(
            f"Could not parse fighter profile. title={page_title!r}"
        )

    profile = {
        "name": name,
        "record": parse_record_from_title(soup),
        "height": parse_profile_item(soup, "Height"),
        "weight": parse_profile_item(soup, "Weight"),
        "reach": parse_profile_item(soup, "Reach"),
        "stance": parse_profile_item(soup, "STANCE"),
        "dob": parse_profile_item(soup, "DOB"),
        "slpm": safe_float(parse_profile_item(soup, "SLpM")),
        "striking_accuracy": safe_float(
            parse_profile_item(soup, "Str. Acc.")
        ),
        "sapm": safe_float(parse_profile_item(soup, "SApM")),
        "striking_defense": safe_float(
            parse_profile_item(soup, "Str. Def")
        ),
        "takedown_average": safe_float(
            parse_profile_item(soup, "TD Avg.")
        ),
        "takedown_accuracy": safe_float(
            parse_profile_item(soup, "TD Acc.")
        ),
        "takedown_defense": safe_float(
            parse_profile_item(soup, "TD Def.")
        ),
        "submission_average": safe_float(
            parse_profile_item(soup, "Sub. Avg.")
        ),
        "recent_fights": parse_recent_fights(soup, limit=5),
        "profile_url": profile_url,
        "source": "UFCStats",
        "data_quality": "real",
    }

    print(
        f"UFC_PROFILE_PARSED name={name!r} "
        f"record={profile['record']!r} "
        f"recent_fights={len(profile['recent_fights'])}",
        flush=True,
    )

    return profile


def get_fighter_profile(
    fighter_name: str,
) -> Optional[Dict[str, Any]]:
    found = find_fighter(fighter_name)

    if not found:
        return None

    profile = get_fighter_profile_by_url(found["url"])
    profile = dict(profile)
    profile["search_name"] = clean_text(fighter_name)
    profile["match_similarity"] = found.get("similarity", 1.0)
    profile["lookup"] = found.get("lookup", "unknown")

    return profile


def compare_fighters(
    fighter1_name: str,
    fighter2_name: str,
) -> Dict[str, Any]:
    started_at = time.time()
    errors = []

    fighter1 = None
    fighter2 = None

    try:
        fighter1 = get_fighter_profile(fighter1_name)
    except UFCProviderError as error:
        errors.append(f"{clean_text(fighter1_name)}: {error}")

    try:
        fighter2 = get_fighter_profile(fighter2_name)
    except UFCProviderError as error:
        errors.append(f"{clean_text(fighter2_name)}: {error}")

    if errors:
        print("UFC_COMPARE_ERRORS:", " | ".join(errors), flush=True)

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
        "source": "UFCStats",
        "real_data": bool(fighter1 and fighter2),
        "response_time_seconds": round(time.time() - started_at, 2),
    }
