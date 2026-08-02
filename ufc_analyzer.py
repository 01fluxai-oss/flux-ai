# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from providers.ufc_provider import (
    UFCProviderError,
    compare_fighters,
)


STANCE_FALLBACKS = {
    "charles oliveira": "Orthodox",
}


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def clamp(
    value: float,
    minimum: float = 0,
    maximum: float = 100,
) -> float:
    return max(minimum, min(maximum, value))


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_record(
    record: Optional[str],
) -> Tuple[int, int, int]:
    text = clean_text(record)

    if not text:
        return 0, 0, 0

    parts = text.split("-")

    if len(parts) < 3:
        return 0, 0, 0

    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except (TypeError, ValueError):
        return 0, 0, 0


def parse_height_inches(
    value: Optional[str],
) -> Optional[float]:
    text = clean_text(value)

    if not text or text in {"--", "---"}:
        return None

    try:
        if "'" in text:
            feet_part, remainder = text.split("'", 1)
            feet = int(feet_part.strip())
            inches_text = remainder.replace('"', "").strip()
            inches = int(inches_text) if inches_text else 0
            return feet * 12 + inches

        # Cito can return a numeric string already expressed in inches.
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_reach_inches(
    value: Optional[str],
) -> Optional[float]:
    text = clean_text(value)

    if not text or text in {"--", "---"}:
        return None

    try:
        return float(text.replace('"', "").strip())
    except (TypeError, ValueError):
        return None


def calculate_age(
    dob: Optional[str],
) -> Optional[int]:
    text = clean_text(dob)

    if not text or text in {"--", "---"}:
        return None

    formats = [
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]

    birth_date = None

    for date_format in formats:
        try:
            birth_date = datetime.strptime(text, date_format)
            break
        except ValueError:
            continue

    if not birth_date:
        return None

    today = datetime.now(timezone.utc)

    return (
        today.year
        - birth_date.year
        - (
            (today.month, today.day)
            < (birth_date.month, birth_date.day)
        )
    )


def normalize_percentage(
    value: Any,
    default: float = 50.0,
) -> float:
    number = safe_float(value, default)

    if number <= 1:
        number *= 100

    return clamp(number)


def normalize_result(value: Any) -> str:
    text = clean_text(value).upper()

    aliases = {
        "WIN": "W",
        "VICTORY": "W",
        "LOSS": "L",
        "DEFEAT": "L",
        "DRAW": "D",
        "NO CONTEST": "NC",
        "NO_CONTEST": "NC",
    }

    return aliases.get(text, text)


def recent_form_score(
    recent_fights: List[Dict[str, Any]],
) -> Tuple[float, int, int, int]:
    if not recent_fights:
        return 50.0, 0, 0, 0

    weights = [1.00, 0.90, 0.80, 0.70, 0.60]

    earned = 0.0
    available = 0.0
    wins = 0
    losses = 0
    draws = 0

    for index, fight in enumerate(recent_fights[:5]):
        weight = weights[index]
        result = normalize_result(fight.get("result"))

        available += weight

        if result == "W":
            earned += weight
            wins += 1
        elif result == "L":
            losses += 1
        else:
            earned += weight * 0.5
            draws += 1

    if available <= 0:
        return 50.0, wins, losses, draws

    return clamp(earned / available * 100), wins, losses, draws


def record_score(
    record: Optional[str],
) -> Tuple[float, int, int, int]:
    wins, losses, draws = parse_record(record)
    total = wins + losses + draws

    if total <= 0:
        return 50.0, wins, losses, draws

    win_rate = (wins + draws * 0.5) / total * 100
    experience_bonus = min(total, 35) * 0.25

    score = win_rate * 0.85 + experience_bonus + 5

    return clamp(score), wins, losses, draws


def striking_score(
    fighter: Dict[str, Any],
) -> float:
    slpm = safe_float(fighter.get("slpm"), 2.5)
    sapm = safe_float(fighter.get("sapm"), 3.0)
    accuracy = normalize_percentage(
        fighter.get("striking_accuracy"),
        45,
    )
    defense = normalize_percentage(
        fighter.get("striking_defense"),
        50,
    )

    output_score = clamp(slpm / 6.0 * 100)
    absorption_score = clamp(100 - sapm / 6.0 * 100)

    return clamp(
        output_score * 0.30
        + accuracy * 0.25
        + defense * 0.30
        + absorption_score * 0.15
    )


def grappling_score(
    fighter: Dict[str, Any],
) -> float:
    takedown_average = safe_float(
        fighter.get("takedown_average"),
        0.5,
    )
    submission_average = safe_float(
        fighter.get("submission_average"),
        0.2,
    )
    takedown_accuracy = normalize_percentage(
        fighter.get("takedown_accuracy"),
        35,
    )
    takedown_defense = normalize_percentage(
        fighter.get("takedown_defense"),
        50,
    )

    takedown_volume_score = clamp(
        takedown_average / 5.0 * 100
    )
    submission_score = clamp(
        submission_average / 2.5 * 100
    )

    return clamp(
        takedown_volume_score * 0.25
        + takedown_accuracy * 0.25
        + takedown_defense * 0.35
        + submission_score * 0.15
    )


def physical_score(
    fighter: Dict[str, Any],
) -> float:
    age = calculate_age(fighter.get("dob"))
    reach = parse_reach_inches(fighter.get("reach"))
    height = parse_height_inches(fighter.get("height"))

    age_score = 60.0

    if age is not None:
        if 27 <= age <= 32:
            age_score = 80
        elif 24 <= age <= 35:
            age_score = 72
        elif 21 <= age <= 38:
            age_score = 62
        else:
            age_score = 50

    reach_score = 60.0

    if reach is not None:
        reach_score = clamp(
            50 + (reach - 70) * 2
        )

    height_score = 60.0

    if height is not None:
        height_score = clamp(
            50 + (height - 68) * 2
        )

    return clamp(
        age_score * 0.50
        + reach_score * 0.30
        + height_score * 0.20
    )


def experience_score(
    fighter: Dict[str, Any],
) -> float:
    wins, losses, draws = parse_record(
        fighter.get("record")
    )
    total = wins + losses + draws

    return clamp(
        45 + min(total, 40) * 1.25
    )


def get_stance(
    fighter: Dict[str, Any],
) -> str:
    stance = clean_text(
        fighter.get("stance")
    )

    if stance and stance not in {"--", "---", "â"}:
        return stance

    name = clean_text(
        fighter.get("name")
    ).lower()

    return STANCE_FALLBACKS.get(name, "â")


def count_recent_finishes(
    recent_fights: List[Dict[str, Any]],
) -> Dict[str, int]:
    result = {
        "ko_tko": 0,
        "submission": 0,
        "decision": 0,
        "other": 0,
    }

    for fight in recent_fights[:5]:
        if normalize_result(fight.get("result")) != "W":
            continue

        method = clean_text(
            fight.get("method")
        ).lower()

        if any(
            word in method
            for word in (
                "ko",
                "tko",
                "knockout",
                "doctor stoppage",
            )
        ):
            result["ko_tko"] += 1
        elif any(
            word in method
            for word in (
                "submission",
                "sub",
                "choke",
                "armbar",
                "triangle",
                "kimura",
            )
        ):
            result["submission"] += 1
        elif "decision" in method:
            result["decision"] += 1
        else:
            result["other"] += 1

    return result


def build_fighter_rating(
    fighter: Dict[str, Any],
) -> Dict[str, Any]:
    recent_fights = fighter.get(
        "recent_fights"
    ) or []

    form, recent_wins, recent_losses, recent_draws = (
        recent_form_score(recent_fights)
    )

    career, wins, losses, draws = record_score(
        fighter.get("record")
    )

    striking = striking_score(fighter)
    grappling = grappling_score(fighter)
    physical = physical_score(fighter)
    experience = experience_score(fighter)

    total_score = (
        form * 0.24
        + career * 0.18
        + striking * 0.24
        + grappling * 0.20
        + physical * 0.06
        + experience * 0.08
    )

    return {
        "name": clean_text(fighter.get("name")),
        "record": clean_text(
            fighter.get("record")
        ) or "â",
        "form": round(form),
        "career": round(career),
        "striking": round(striking),
        "grappling": round(grappling),
        "physical": round(physical),
        "experience": round(experience),
        "total_score": round(
            clamp(total_score),
            2,
        ),
        "recent_wins": recent_wins,
        "recent_losses": recent_losses,
        "recent_draws": recent_draws,
        "recent_finishes": count_recent_finishes(
            recent_fights
        ),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "slpm": safe_float(fighter.get("slpm")),
        "sapm": safe_float(fighter.get("sapm")),
        "striking_accuracy": normalize_percentage(
            fighter.get("striking_accuracy")
        ),
        "striking_defense": normalize_percentage(
            fighter.get("striking_defense")
        ),
        "takedown_average": safe_float(
            fighter.get("takedown_average")
        ),
        "takedown_accuracy": normalize_percentage(
            fighter.get("takedown_accuracy")
        ),
        "takedown_defense": normalize_percentage(
            fighter.get("takedown_defense")
        ),
        "submission_average": safe_float(
            fighter.get("submission_average")
        ),
        "height": clean_text(
            fighter.get("height")
        ) or "â",
        "reach": clean_text(
            fighter.get("reach")
        ) or "â",
        "stance": get_stance(fighter),
        "age": calculate_age(
            fighter.get("dob")
        ),
        "profile_url": fighter.get(
            "profile_url"
        ),
    }


def calculate_probabilities(
    fighter1_score: float,
    fighter2_score: float,
) -> Tuple[int, int]:
    difference = fighter1_score - fighter2_score
    probability1 = clamp(
        50 + difference * 1.35,
        18,
        82,
    )

    probability1 = round(probability1)

    return probability1, 100 - probability1


def confidence_from_difference(
    probability1: int,
    probability2: int,
) -> int:
    difference = abs(
        probability1 - probability2
    )

    return round(
        clamp(
            50 + difference * 0.75,
            50,
            82,
        )
    )


def confidence_label(
    confidence: int,
    language: str = "ru",
) -> str:
    if confidence >= 72:
        return "High" if language == "en" else "ÐÑÑÐ¾ÐºÐ°Ñ"

    if confidence >= 60:
        return "Medium" if language == "en" else "Ð¡ÑÐµÐ´Ð½ÑÑ"

    return "Low" if language == "en" else "ÐÐ¸Ð·ÐºÐ°Ñ"


def risk_label(
    confidence: int,
    language: str = "ru",
) -> str:
    if confidence >= 72:
        return "Low" if language == "en" else "ÐÐ¸Ð·ÐºÐ¸Ð¹"

    if confidence >= 60:
        return "Medium" if language == "en" else "Ð¡ÑÐµÐ´Ð½Ð¸Ð¹"

    return "High" if language == "en" else "ÐÑÑÐ¾ÐºÐ¸Ð¹"


def method_scores(
    winner: Dict[str, Any],
    loser: Dict[str, Any],
) -> Dict[str, float]:
    finishes = winner.get(
        "recent_finishes"
    ) or {}

    striking_advantage = (
        winner["striking"]
        - loser["striking"]
    )
    grappling_advantage = (
        winner["grappling"]
        - loser["grappling"]
    )

    ko_score = (
        25
        + max(0, striking_advantage) * 2.0
        + winner.get("slpm", 0) * 5
        + finishes.get("ko_tko", 0) * 12
        + max(
            0,
            55 - loser.get(
                "striking_defense",
                50,
            ),
        ) * 0.8
    )

    submission_score = (
        20
        + max(0, grappling_advantage) * 2.2
        + winner.get(
            "submission_average",
            0,
        ) * 12
        + winner.get(
            "takedown_average",
            0,
        ) * 4
        + finishes.get("submission", 0) * 14
        + max(
            0,
            65 - loser.get(
                "takedown_defense",
                50,
            ),
        ) * 0.8
    )

    decision_score = (
        42
        + finishes.get("decision", 0) * 8
        + max(
            0,
            65 - abs(
                winner["total_score"]
                - loser["total_score"]
            ) * 2,
        ) * 0.35
    )

    return {
        "KO/TKO": ko_score,
        "Submission": submission_score,
        "Decision": decision_score,
    }


def choose_method(
    winner: Dict[str, Any],
    loser: Dict[str, Any],
    language: str = "ru",
) -> Tuple[str, int]:
    scores = method_scores(
        winner,
        loser,
    )

    method = max(
        scores,
        key=scores.get,
    )

    total = sum(scores.values())

    if total <= 0:
        confidence = 34
    else:
        confidence = round(
            scores[method] / total * 100
        )

    confidence = round(
        clamp(
            confidence,
            34,
            72,
        )
    )

    translations = {
        "KO/TKO": {
            "en": "KO/TKO",
            "ru": "KO/TKO",
        },
        "Submission": {
            "en": "Submission",
            "ru": "Ð¡Ð°Ð±Ð¼Ð¸ÑÐµÐ½",
        },
        "Decision": {
            "en": "Decision",
            "ru": "Ð ÐµÑÐµÐ½Ð¸Ðµ ÑÑÐ´ÐµÐ¹",
        },
    }

    return (
        translations[method][language],
        confidence,
    )


def fighter_not_found_message(
    missing: List[str],
    language: str = "ru",
) -> str:
    names = ", ".join(missing)

    if language == "en":
        return (
            "â ï¸ UFC fighter data was not found.\n\n"
            f"Not found: {names}\n\n"
            "Check the fighter names and use their full English names."
        )

    return (
        "â ï¸ ÐÐ°Ð½Ð½ÑÐµ Ð±Ð¾Ð¹ÑÐ° UFC Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ñ.\n\n"
        f"ÐÐµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾: {names}\n\n"
        "ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐ¹ Ð¿Ð¾Ð»Ð½ÑÐµ Ð¸Ð¼ÐµÐ½Ð° Ð±Ð¾Ð¹ÑÐ¾Ð² Ð½Ð° Ð°Ð½Ð³Ð»Ð¸Ð¹ÑÐºÐ¾Ð¼ ÑÐ·ÑÐºÐµ."
    )


def provider_error_message(
    language: str = "ru",
) -> str:
    if language == "en":
        return (
            "â ï¸ UFC statistics are temporarily unavailable.\n\n"
            "Please try again later."
        )

    return (
        "â ï¸ Ð¡ÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐ° UFC Ð²ÑÐµÐ¼ÐµÐ½Ð½Ð¾ Ð½ÐµÐ´Ð¾ÑÑÑÐ¿Ð½Ð°.\n\n"
        "ÐÐ¾Ð¿ÑÐ¾Ð±ÑÐ¹ Ð²ÑÐ¿Ð¾Ð»Ð½Ð¸ÑÑ Ð°Ð½Ð°Ð»Ð¸Ð· Ð¿Ð¾Ð·Ð¶Ðµ."
    )


def format_age(
    age: Optional[int],
) -> str:
    return str(age) if age is not None else "â"


def analyze_ufc_match(
    fighter1: str,
    fighter2: str,
    language: str = "ru",
) -> str:
    fighter1 = clean_text(fighter1)
    fighter2 = clean_text(fighter2)

    if not fighter1 or not fighter2:
        return (
            "ð¥ Send a UFC fight:\n\nFighter 1 - Fighter 2"
            if language == "en"
            else "ð¥ ÐÑÐ¿ÑÐ°Ð²Ñ Ð±Ð¾Ð¹ UFC:\n\nÐÐ¾ÐµÑ 1 - ÐÐ¾ÐµÑ 2"
        )

    try:
        comparison = compare_fighters(
            fighter1,
            fighter2,
        )
    except UFCProviderError as error:
        print(
            "UFC_PROVIDER_ERROR:",
            repr(error),
            flush=True,
        )
        return provider_error_message(language)
    except Exception as error:
        print(
            "UFC_ANALYZER_ERROR:",
            repr(error),
            flush=True,
        )
        return provider_error_message(language)

    missing = comparison.get(
        "missing"
    ) or []

    if missing:
        return fighter_not_found_message(
            missing,
            language,
        )

    raw_fighter1 = comparison.get("fighter1")
    raw_fighter2 = comparison.get("fighter2")

    if not raw_fighter1 or not raw_fighter2:
        return provider_error_message(language)

    data1 = build_fighter_rating(
        raw_fighter1
    )
    data2 = build_fighter_rating(
        raw_fighter2
    )

    probability1, probability2 = (
        calculate_probabilities(
            data1["total_score"],
            data2["total_score"],
        )
    )

    if probability1 >= probability2:
        winner = data1
        loser = data2
        winner_probability = probability1
    else:
        winner = data2
        loser = data1
        winner_probability = probability2

    confidence = confidence_from_difference(
        probability1,
        probability2,
    )

    confidence_text = confidence_label(
        confidence,
        language,
    )
    risk_text = risk_label(
        confidence,
        language,
    )

    expected_method, method_confidence = (
        choose_method(
            winner,
            loser,
            language,
        )
    )

    source = comparison.get(
        "source",
        "Cito API",
    )
    response_time = comparison.get(
        "response_time_seconds",
        0,
    )

    if language == "en":
        return (
            "ð¥ FLUX AI UFC â FIGHT ANALYSIS\n\n"
            f"{data1['name']} vs {data2['name']}\n\n"

            "ð WIN PROBABILITY\n"
            f"â¢ {data1['name']}: {probability1}%\n"
            f"â¢ {data2['name']}: {probability2}%\n\n"

            "â¡ FLUX RATINGS\n"
            f"â¢ {data1['name']}: {round(data1['total_score'])}/100\n"
            f"â¢ {data2['name']}: {round(data2['total_score'])}/100\n\n"

            "ð¯ MODEL PICK\n"
            f"Winner: {winner['name']}\n"
            f"Win probability: {winner_probability}%\n"
            f"Expected method: {expected_method}\n"
            f"Method confidence: {method_confidence}%\n"
            f"AI Confidence: {confidence}% ({confidence_text})\n"
            f"Risk: {risk_text}\n\n"

            "ð COMPARISON\n"
            f"â¢ Record: {data1['record']} â {data2['record']}\n"
            f"â¢ Recent form: {data1['form']} â {data2['form']}\n"
            f"â¢ Striking: {data1['striking']} â {data2['striking']}\n"
            f"â¢ Grappling: {data1['grappling']} â {data2['grappling']}\n"
            f"â¢ Experience: {data1['experience']} â {data2['experience']}\n\n"

            "ð¥ FIGHT STATISTICS\n"
            f"â¢ SLpM: {data1['slpm']:.2f} â {data2['slpm']:.2f}\n"
            f"â¢ Striking accuracy: "
            f"{round(data1['striking_accuracy'])}% â "
            f"{round(data2['striking_accuracy'])}%\n"
            f"â¢ Striking defense: "
            f"{round(data1['striking_defense'])}% â "
            f"{round(data2['striking_defense'])}%\n"
            f"â¢ Takedown average: "
            f"{data1['takedown_average']:.2f} â "
            f"{data2['takedown_average']:.2f}\n"
            f"â¢ Takedown defense: "
            f"{round(data1['takedown_defense'])}% â "
            f"{round(data2['takedown_defense'])}%\n"
            f"â¢ Submission average: "
            f"{data1['submission_average']:.2f} â "
            f"{data2['submission_average']:.2f}\n\n"

            "ð PHYSICAL DATA\n"
            f"â¢ Age: {format_age(data1['age'])} â "
            f"{format_age(data2['age'])}\n"
            f"â¢ Height: {data1['height']} â {data2['height']}\n"
            f"â¢ Reach: {data1['reach']} â {data2['reach']}\n"
            f"â¢ Stance: {data1['stance']} â {data2['stance']}\n\n"

            f"ð¡ Source: {source}\n"
            f"â± Data load: {response_time} sec\n"
            "ð§ª Model: FLUX AI UFC Beta v1.1\n\n"

            "â ï¸ The prediction is based on available historical "
            "statistics and does not guarantee the fight result."
        )

    return (
        "ð¥ FLUX AI UFC â ÐÐÐÐÐÐ ÐÐÐ¯\n\n"
        f"{data1['name']} vs {data2['name']}\n\n"

        "ð ÐÐÐ ÐÐ¯Ð¢ÐÐÐ¡Ð¢Ð¬ ÐÐÐÐÐÐ«\n"
        f"â¢ {data1['name']}: {probability1}%\n"
        f"â¢ {data2['name']}: {probability2}%\n\n"

        "â¡ FLUX Ð ÐÐÐ¢ÐÐÐÐ\n"
        f"â¢ {data1['name']}: {round(data1['total_score'])}/100\n"
        f"â¢ {data2['name']}: {round(data2['total_score'])}/100\n\n"

        "ð¯ ÐÐ ÐÐÐÐÐ ÐÐÐÐÐÐ\n"
        f"ÐÐ¾Ð±ÐµÐ´Ð¸ÑÐµÐ»Ñ: {winner['name']}\n"
        f"ÐÐµÑÐ¾ÑÑÐ½Ð¾ÑÑÑ Ð¿Ð¾Ð±ÐµÐ´Ñ: {winner_probability}%\n"
        f"ÐÐ¶Ð¸Ð´Ð°ÐµÐ¼ÑÐ¹ ÑÐ¿Ð¾ÑÐ¾Ð±: {expected_method}\n"
        f"Ð£Ð²ÐµÑÐµÐ½Ð½Ð¾ÑÑÑ Ð² ÑÐ¿Ð¾ÑÐ¾Ð±Ðµ: {method_confidence}%\n"
        f"AI Confidence: {confidence}% ({confidence_text})\n"
        f"Ð Ð¸ÑÐº: {risk_text}\n\n"

        "ð Ð¡Ð ÐÐÐÐÐÐÐ\n"
        f"â¢ Ð ÐµÐºÐ¾ÑÐ´: {data1['record']} â {data2['record']}\n"
        f"â¢ ÐÐ¾ÑÐ»ÐµÐ´Ð½ÑÑ ÑÐ¾ÑÐ¼Ð°: {data1['form']} â {data2['form']}\n"
        f"â¢ Ð¡ÑÐ¾Ð¹ÐºÐ°: {data1['striking']} â {data2['striking']}\n"
        f"â¢ ÐÐ¾ÑÑÐ±Ð°: {data1['grappling']} â {data2['grappling']}\n"
        f"â¢ ÐÐ¿ÑÑ: {data1['experience']} â {data2['experience']}\n\n"

        "ð¥ Ð¡Ð¢ÐÐ¢ÐÐ¡Ð¢ÐÐÐ ÐÐÐ¯\n"
        f"â¢ Ð£Ð´Ð°ÑÑ Ð² Ð¼Ð¸Ð½ÑÑÑ: {data1['slpm']:.2f} â {data2['slpm']:.2f}\n"
        f"â¢ Ð¢Ð¾ÑÐ½Ð¾ÑÑÑ ÑÐ´Ð°ÑÐ¾Ð²: "
        f"{round(data1['striking_accuracy'])}% â "
        f"{round(data2['striking_accuracy'])}%\n"
        f"â¢ ÐÐ°ÑÐ¸ÑÐ° Ð¾Ñ ÑÐ´Ð°ÑÐ¾Ð²: "
        f"{round(data1['striking_defense'])}% â "
        f"{round(data2['striking_defense'])}%\n"
        f"â¢ Ð¢ÐµÐ¹ÐºÐ´Ð°ÑÐ½Ñ: "
        f"{data1['takedown_average']:.2f} â "
        f"{data2['takedown_average']:.2f}\n"
        f"â¢ ÐÐ°ÑÐ¸ÑÐ° Ð¾Ñ ÑÐµÐ¹ÐºÐ´Ð°ÑÐ½Ð¾Ð²: "
        f"{round(data1['takedown_defense'])}% â "
        f"{round(data2['takedown_defense'])}%\n"
        f"â¢ Ð¡Ð°Ð±Ð¼Ð¸ÑÐµÐ½Ñ: "
        f"{data1['submission_average']:.2f} â "
        f"{data2['submission_average']:.2f}\n\n"

        "ð Ð¤ÐÐÐÐ§ÐÐ¡ÐÐÐ ÐÐÐÐÐ«Ð\n"
        f"â¢ ÐÐ¾Ð·ÑÐ°ÑÑ: {format_age(data1['age'])} â "
        f"{format_age(data2['age'])}\n"
        f"â¢ Ð Ð¾ÑÑ: {data1['height']} â {data2['height']}\n"
        f"â¢ Ð Ð°Ð·Ð¼Ð°Ñ ÑÑÐº: {data1['reach']} â {data2['reach']}\n"
        f"â¢ Ð¡ÑÐ¾Ð¹ÐºÐ°: {data1['stance']} â {data2['stance']}\n\n"

        f"ð¡ ÐÑÑÐ¾ÑÐ½Ð¸Ðº: {source}\n"
        f"â± ÐÐ°Ð³ÑÑÐ·ÐºÐ° Ð´Ð°Ð½Ð½ÑÑ: {response_time} ÑÐµÐº.\n"
        "ð§ª ÐÐ¾Ð´ÐµÐ»Ñ: FLUX AI UFC Beta v1.1\n\n"

        "â ï¸ ÐÑÐ¾Ð³Ð½Ð¾Ð· Ð¾ÑÐ½Ð¾Ð²Ð°Ð½ Ð½Ð° Ð´Ð¾ÑÑÑÐ¿Ð½Ð¾Ð¹ Ð¸ÑÑÐ¾ÑÐ¸ÑÐµÑÐºÐ¾Ð¹ ÑÑÐ°ÑÐ¸ÑÑÐ¸ÐºÐµ "
        "Ð¸ Ð½Ðµ Ð³Ð°ÑÐ°Ð½ÑÐ¸ÑÑÐµÑ ÑÐµÐ·ÑÐ»ÑÑÐ°Ñ Ð±Ð¾Ñ."
    )
