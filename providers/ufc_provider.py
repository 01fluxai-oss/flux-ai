import re
import time
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "http://ufcstats.com"
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FLUX-AI-Sports/5.1; "
        "+https://t.me/FluxAIDaily)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)


class UFCProviderError(Exception):
    """Ошибка получения или обработки данных UFCStats."""


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_name(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9а-яё ]+", " ", value)
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


def safe_int(value: Any) -> Optional[int]:
    number = safe_float(value)

    if number is None:
        return None

    return int(number)


def request_page(url: str) -> BeautifulSoup:
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise UFCProviderError(
            f"Не удалось загрузить UFCStats: {error}"
        ) from error

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def similarity(first: str, second: str) -> float:
    return SequenceMatcher(
        None,
        normalize_name(first),
        normalize_name(second),
    ).ratio()


def get_search_letters(name: str) -> List[str]:
    normalized = normalize_name(name)

    if not normalized:
        return []

    parts = normalized.split()
    letters = []

    for part in parts:
        first_letter = part[0]

        if first_letter.isalpha() and first_letter not in letters:
            letters.append(first_letter)

    return letters[:3]


@lru_cache(maxsize=64)
def get_fighters_by_letter(letter: str) -> List[Dict[str, str]]:
    letter = clean_text(letter).lower()[:1]

    if not letter or not letter.isalpha():
        return []

    url = (
        f"{BASE_URL}/statistics/fighters"
        f"?char={letter}&page=all"
    )

    soup = request_page(url)
    fighters = []

    rows = soup.select(
        "tr.b-statistics__table-row"
    )

    for row in rows:
        links = row.select(
            "a.b-link.b-link_style_black"
        )

        if len(links) < 2:
            continue

        first_name = clean_text(
            links[0].get_text()
        )
        last_name = clean_text(
            links[1].get_text()
        )

        profile_url = clean_text(
            links[0].get("href")
        )

        full_name = clean_text(
            f"{first_name} {last_name}"
        )

        if not full_name or not profile_url:
            continue

        columns = row.select(
            "td.b-statistics__table-col"
        )

        record = ""

        if len(columns) >= 10:
            wins = clean_text(
                columns[7].get_text()
            )
            losses = clean_text(
                columns[8].get_text()
            )
            draws = clean_text(
                columns[9].get_text()
            )

            if wins and losses and draws:
                record = f"{wins}-{losses}-{draws}"

        fighters.append({
            "name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "url": profile_url,
            "record": record,
        })

    return fighters


def find_fighter(
    fighter_name: str,
    minimum_similarity: float = 0.72,
) -> Optional[Dict[str, str]]:
    fighter_name = clean_text(fighter_name)

    if not fighter_name:
        return None

    candidates = []
    seen_urls = set()

    for letter in get_search_letters(fighter_name):
        try:
            letter_fighters = get_fighters_by_letter(
                letter
            )
        except UFCProviderError:
            continue

        for fighter in letter_fighters:
            url = fighter.get("url")

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            candidates.append(fighter)

    if not candidates:
        return None

    target = normalize_name(fighter_name)

    for fighter in candidates:
        if normalize_name(fighter["name"]) == target:
            fighter["similarity"] = 1.0
            return fighter

    scored = []

    for fighter in candidates:
        score = similarity(
            fighter_name,
            fighter["name"],
        )

        scored.append((
            score,
            fighter,
        ))

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score, best_fighter = scored[0]

    if best_score < minimum_similarity:
        return None

    result = dict(best_fighter)
    result["similarity"] = round(
        best_score,
        3,
    )

    return result


def parse_profile_item(
    soup: BeautifulSoup,
    label: str,
) -> Optional[str]:
    label_normalized = normalize_name(label)

    items = soup.select(
        "li.b-list__box-list-item"
    )

    for item in items:
        title = item.select_one(
            "i.b-list__box-item-title"
        )

        if not title:
            continue

        title_text = normalize_name(
            title.get_text()
        )

        if not title_text.startswith(
            label_normalized
        ):
            continue

        full_text = clean_text(
            item.get_text(" ", strip=True)
        )

        title_visible = clean_text(
            title.get_text(" ", strip=True)
        )

        value = full_text.replace(
            title_visible,
            "",
            1,
        ).strip()

        return value or None

    return None


def parse_record_from_title(
    soup: BeautifulSoup,
) -> Optional[str]:
    title = soup.select_one(
        "span.b-content__title-record"
    )

    if not title:
        return None

    text = clean_text(
        title.get_text()
    )

    match = re.search(
        r"Record:\s*([0-9]+-[0-9]+-[0-9]+)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)


def parse_fighter_name(
    soup: BeautifulSoup,
) -> Optional[str]:
    title = soup.select_one(
        "span.b-content__title-highlight"
    )

    if not title:
        return None

    return clean_text(
        title.get_text()
    ) or None


def parse_recent_fights(
    soup: BeautifulSoup,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    fights = []

    rows = soup.select(
        "tr.b-fight-details__table-row"
        "[data-link]"
    )

    for row in rows[:limit]:
        columns = row.select(
            "td.b-fight-details__table-col"
        )

        if len(columns) < 10:
            continue

        result = clean_text(
            columns[0].get_text()
        )

        fighter_names = [
            clean_text(link.get_text())
            for link in columns[1].select("a")
            if clean_text(link.get_text())
        ]

        event_link = columns[6].select_one("a")
        event_name = (
            clean_text(event_link.get_text())
            if event_link
            else ""
        )

        event_url = (
            clean_text(event_link.get("href"))
            if event_link
            else ""
        )

        method_lines = [
            clean_text(item.get_text())
            for item in columns[7].select("p")
            if clean_text(item.get_text())
        ]

        method = (
            " ".join(method_lines)
            if method_lines
            else clean_text(
                columns[7].get_text()
            )
        )

        round_number = clean_text(
            columns[8].get_text()
        )
        fight_time = clean_text(
            columns[9].get_text()
        )

        date_text = ""

        date_element = columns[6].select_one(
            ".b-fight-details__table-text"
        )

        if date_element:
            date_text = clean_text(
                date_element.get_text()
            )

        fights.append({
            "result": result,
            "fighters": fighter_names,
            "event": event_name,
            "event_url": event_url,
            "date": date_text,
            "method": method,
            "round": round_number,
            "time": fight_time,
            "fight_url": clean_text(
                row.get("data-link")
            ),
        })

    return fights


@lru_cache(maxsize=256)
def get_fighter_profile_by_url(
    profile_url: str,
) -> Dict[str, Any]:
    profile_url = clean_text(profile_url)

    if not profile_url:
        raise UFCProviderError(
            "Не указана ссылка на бойца."
        )

    soup = request_page(profile_url)

    name = parse_fighter_name(soup)

    if not name:
        raise UFCProviderError(
            "Не удалось прочитать профиль бойца."
        )

    record = parse_record_from_title(soup)

    fighter = {
        "name": name,
        "record": record,
        "height": parse_profile_item(
            soup,
            "Height",
        ),
        "weight": parse_profile_item(
            soup,
            "Weight",
        ),
        "reach": parse_profile_item(
            soup,
            "Reach",
        ),
        "stance": parse_profile_item(
            soup,
            "STANCE",
        ),
        "dob": parse_profile_item(
            soup,
            "DOB",
        ),
        "slpm": safe_float(
            parse_profile_item(
                soup,
                "SLpM",
            )
        ),
        "striking_accuracy": safe_float(
            parse_profile_item(
                soup,
                "Str. Acc.",
            )
        ),
        "sapm": safe_float(
            parse_profile_item(
                soup,
                "SApM",
            )
        ),
        "striking_defense": safe_float(
            parse_profile_item(
                soup,
                "Str. Def",
            )
        ),
        "takedown_average": safe_float(
            parse_profile_item(
                soup,
                "TD Avg.",
            )
        ),
        "takedown_accuracy": safe_float(
            parse_profile_item(
                soup,
                "TD Acc.",
            )
        ),
        "takedown_defense": safe_float(
            parse_profile_item(
                soup,
                "TD Def.",
            )
        ),
        "submission_average": safe_float(
            parse_profile_item(
                soup,
                "Sub. Avg.",
            )
        ),
        "recent_fights": parse_recent_fights(
            soup,
            limit=5,
        ),
        "profile_url": profile_url,
        "source": "UFCStats",
        "data_quality": "real",
    }

    return fighter


def get_fighter_profile(
    fighter_name: str,
) -> Optional[Dict[str, Any]]:
    found = find_fighter(fighter_name)

    if not found:
        return None

    profile = get_fighter_profile_by_url(
        found["url"]
    )

    profile["search_name"] = clean_text(
        fighter_name
    )
    profile["match_similarity"] = found.get(
        "similarity",
        1.0,
    )

    return profile


def compare_fighters(
    fighter1_name: str,
    fighter2_name: str,
) -> Dict[str, Any]:
    started_at = time.time()

    fighter1 = get_fighter_profile(
        fighter1_name
    )
    fighter2 = get_fighter_profile(
        fighter2_name
    )

    missing = []

    if not fighter1:
        missing.append(
            clean_text(fighter1_name)
        )

    if not fighter2:
        missing.append(
            clean_text(fighter2_name)
        )

    return {
        "fighter1": fighter1,
        "fighter2": fighter2,
        "missing": missing,
        "source": "UFCStats",
        "real_data": bool(
            fighter1 and fighter2
        ),
        "response_time_seconds": round(
            time.time() - started_at,
            2,
        ),
    }
