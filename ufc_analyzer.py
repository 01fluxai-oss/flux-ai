from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from providers.ufc_provider import (
    UFCProviderError,
    compare_fighters,
)


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
        wins = int(parts[0])
        losses = int(parts[1])
        draws = int(parts[2])

        return wins, losses, draws
    except (TypeError, ValueError):
        return 0, 0, 0


def parse_height_inches(
    value: Optional[str],
) -> Optional[float]:
    text = clean_text(value)

    if not text or text in {"--", "---"}:
        return None

    try:
        feet = 0
        inches = 0

        if "'" in text:
            feet_part, remainder = text.split("'", 1)
            feet = int(feet_part.strip())

            remainder = (
                remainder
                .replace('"', "")
                .strip()
            )

            if remainder:
                inches = int(remainder)

        return feet * 12 + inches
    except (TypeError, ValueError):
        return None


def parse_reach_inches(
    value: Optional[str],
) -> Optional[float]:
    text = clean_text(value)

    if not text or text in {"--", "---"}:
        return None

    try:
        text = text.replace('"', "").strip()
        return float(text)
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
    ]

    birth_date = None

    for date_format in formats:
        try:
            birth_date = datetime.strptime(
                text,
                date_format,
            )
            break
        except ValueError:
            continue

    if not birth_date:
        return None

    today = datetime.utcnow()

    age = (
        today.year
        - birth_date.year
        - (
            (today.month, today.day)
            < (birth_date.month, birth_date.day)
        )
    )

    return age


def normalize_percentage(
    value: Any,
    default: float = 50.0,
) -> float:
    number = safe_float(value, default)

    if number <= 1:
        number *= 100

    return clamp(number)


def recent_form_score(
    recent_fights: List[Dict[str, Any]],
) -> Tuple[float, int, int, int]:
    if not recent_fights:
        return 50.0, 0, 0, 0

    weights = [
        1.00,
        0.90,
        0.80,
        0.70,
        0.60,
    ]

    earned = 0.0
    available = 0.0
    wins = 0
    losses = 0
    draws = 0

    for index, fight in enumerate(recent_fights[:5]):
        weight = weights[index]
        result = clean_text(
            fight.get("result")
        ).upper()

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

    score = earned / available * 100

    return clamp(score), wins, losses, draws


def record_score(
    record: Optional[str],
) -> Tuple[float, int, int, int]:
    wins, losses, draws = parse_record(record)
    total = wins + losses + draws

    if total <= 0:
        return 50.0, wins, losses, draws

    win_rate = (
        wins + draws * 0.5
    ) / total * 100

    experience_bonus = min(
        total,
        35,
    ) * 0.25

    score = (
        win_rate * 0.85
        + experience_bonus
        + 5
    )

    return clamp(score), wins, losses, draws


def striking_score(
    fighter: Dict[str, Any],
) -> float:
    slpm = safe_float(
        fighter.get("slpm"),
        2.5,
    )
    sapm = safe_float(
        fighter.get("sapm"),
        3.0,
    )

    accuracy = normalize_percentage(
        fighter.get("striking_accuracy"),
        45,
    )
    defense = normalize_percentage(
        fighter.get("striking_defense"),
        50,
    )

    output_score = clamp(
        slpm / 6.0 * 100
    )

    absorption_score = clamp(
        100 - sapm / 6.0 * 100
    )

    score = (
        output_score * 0.30
        + accuracy * 0.25
        + defense * 0.30
        + absorption_score * 0.15
    )

    return clamp(score)


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

    score = (
        takedown_volume_score * 0.25
        + takedown_accuracy * 0.25
        + takedown_defense * 0.35
        + submission_score * 0.15
    )

    return clamp(score)


def physical_score(
    fighter: Dict[str, Any],
) -> float:
    age = calculate_age(
        fighter.get("dob")
    )
    reach = parse_reach_inches(
        fighter.get("reach")
    )
    height = parse_height_inches(
        fighter.get("height")
    )

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

    score = 45 + min(
        total,
        40,
    ) * 1.25

    return clamp(score)


def build_fighter_rating(
    fighter: Dict[str, Any],
) -> Dict[str, Any]:
    form, recent_wins, recent_losses, recent_draws = (
        recent_form_score(
            fighter.get("recent_fights") or []
        )
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
        "name": clean_text(
            fighter.get("name")
        ),
        "record": clean_text(
            fighter.get("record")
        ) or "—",
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
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "slpm": safe_float(
            fighter.get("slpm")
        ),
        "sapm": safe_float(
            fighter.get("sapm")
        ),
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
        ) or "—",
        "reach": clean_text(
            fighter.get("reach")
        ) or "—",
        "stance": clean_text(
            fighter.get("stance")
        ) or "—",
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

    probability1 = 50 + difference * 1.35

    probability1 = clamp(
        probability1,
        18,
        82,
    )

    probability1 = round(probability1)
    probability2 = 100 - probability1

    return probability1, probability2


def confidence_from_difference(
    probability1: int,
    probability2: int,
) -> int:
    difference = abs(
        probability1 - probability2
    )

    confidence = 50 + difference * 0.75

    return round(
        clamp(
            confidence,
            50,
            82,
        )
    )


def confidence_label(
    confidence: int,
    language: str = "ru",
) -> str:
    if confidence >= 72:
        return (
            "High"
            if language == "en"
            else "Высокая"
        )

    if confidence >= 60:
        return (
            "Medium"
            if language == "en"
            else "Средняя"
        )

    return (
        "Low"
        if language == "en"
        else "Низкая"
    )


def risk_label(
    confidence: int,
    language: str = "ru",
) -> str:
    if confidence >= 72:
        return (
            "Low"
            if language == "en"
            else "Низкий"
        )

    if confidence >= 60:
        return (
            "Medium"
            if language == "en"
            else "Средний"
        )

    return (
        "High"
        if language == "en"
        else "Высокий"
    )


def choose_method(
    winner: Dict[str, Any],
    loser: Dict[str, Any],
    language: str = "ru",
) -> str:
    striking_advantage = (
        winner["striking"]
        - loser["striking"]
    )

    grappling_advantage = (
        winner["grappling"]
        - loser["grappling"]
    )

    submission_average = winner.get(
        "submission_average",
        0,
    )

    takedown_average = winner.get(
        "takedown_average",
        0,
    )

    slpm = winner.get(
        "slpm",
        0,
    )

    if (
        grappling_advantage >= 8
        and (
            submission_average >= 0.8
            or takedown_average >= 2.0
        )
    ):
        return (
            "Submission"
            if language == "en"
            else "Сабмишен"
        )

    if (
        striking_advantage >= 8
        and slpm >= 3.5
    ):
        return "KO/TKO"

    return (
        "Decision"
        if language == "en"
        else "Решение судей"
    )


def fighter_not_found_message(
    missing: List[str],
    language: str = "ru",
) -> str:
    names = ", ".join(missing)

    if language == "en":
        return (
            "⚠️ UFC fighter data was not found.\n\n"
            f"Not found: {names}\n\n"
            "Check the fighter names and use their full English names.\n\n"
            "Example:\n"
            "Islam Makhachev - Charles Oliveira"
        )

    return (
        "⚠️ Данные бойца UFC не найдены.\n\n"
        f"Не найдено: {names}\n\n"
        "Проверь имена и используй полные имена бойцов на английском языке.\n\n"
        "Пример:\n"
        "Islam Makhachev - Charles Oliveira"
    )


def provider_error_message(
    language: str = "ru",
) -> str:
    if language == "en":
        return (
            "⚠️ UFC statistics are temporarily unavailable.\n\n"
            "Please try again later."
        )

    return (
        "⚠️ Статистика UFC временно недоступна.\n\n"
        "Попробуй выполнить анализ позже."
    )


def format_age(
    age: Optional[int],
) -> str:
    return str(age) if age is not None else "—"


def analyze_ufc_match(
    fighter1: str,
    fighter2: str,
    language: str = "ru",
) -> str:
    fighter1 = clean_text(fighter1)
    fighter2 = clean_text(fighter2)

    if not fighter1 or not fighter2:
        if language == "en":
            return (
                "🥊 Send a UFC fight:\n\n"
                "Fighter 1 - Fighter 2"
            )

        return (
            "🥊 Отправь бой UFC:\n\n"
            "Боец 1 - Боец 2"
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

    missing = comparison.get("missing") or []

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

    expected_method = choose_method(
        winner,
        loser,
        language,
    )

    source = comparison.get(
        "source",
        "UFCStats",
    )

    response_time = comparison.get(
        "response_time_seconds",
        0,
    )

    if language == "en":
        return (
            "🥊 FLUX AI UFC — FIGHT ANALYSIS\n\n"
            f"{data1['name']} vs {data2['name']}\n\n"

            "📊 WIN PROBABILITY\n"
            f"• {data1['name']}: {probability1}%\n"
            f"• {data2['name']}: {probability2}%\n\n"

            "⚡ FLUX RATINGS\n"
            f"• {data1['name']}: {round(data1['total_score'])}/100\n"
            f"• {data2['name']}: {round(data2['total_score'])}/100\n\n"

            "🎯 MODEL PICK\n"
            f"Winner: {winner['name']}\n"
            f"Win probability: {winner_probability}%\n"
            f"Expected method: {expected_method}\n"
            f"AI Confidence: {confidence}% ({confidence_text})\n"
            f"Risk: {risk_text}\n\n"

            "📈 COMPARISON\n"
            f"• Record: {data1['record']} — {data2['record']}\n"
            f"• Recent form: {data1['form']} — {data2['form']}\n"
            f"• Striking: {data1['striking']} — {data2['striking']}\n"
            f"• Grappling: {data1['grappling']} — {data2['grappling']}\n"
            f"• Experience: {data1['experience']} — {data2['experience']}\n\n"

            "🥋 FIGHT STATISTICS\n"
            f"• SLpM: {data1['slpm']:.2f} — {data2['slpm']:.2f}\n"
            f"• Striking accuracy: "
            f"{round(data1['striking_accuracy'])}% — "
            f"{round(data2['striking_accuracy'])}%\n"
            f"• Striking defense: "
            f"{round(data1['striking_defense'])}% — "
            f"{round(data2['striking_defense'])}%\n"
            f"• Takedown average: "
            f"{data1['takedown_average']:.2f} — "
            f"{data2['takedown_average']:.2f}\n"
            f"• Takedown defense: "
            f"{round(data1['takedown_defense'])}% — "
            f"{round(data2['takedown_defense'])}%\n\n"

            "📏 PHYSICAL DATA\n"
            f"• Age: {format_age(data1['age'])} — "
            f"{format_age(data2['age'])}\n"
            f"• Height: {data1['height']} — {data2['height']}\n"
            f"• Reach: {data1['reach']} — {data2['reach']}\n"
            f"• Stance: {data1['stance']} — {data2['stance']}\n\n"

            f"📡 Source: {source}\n"
            f"⏱ Data load: {response_time} sec\n"
            "🧪 Model: FLUX AI UFC Beta v1.0\n\n"

            "⚠️ The prediction is based on available historical "
            "statistics. It does not guarantee the fight result."
        )

    return (
        "🥊 FLUX AI UFC — АНАЛИЗ БОЯ\n\n"
        f"{data1['name']} vs {data2['name']}\n\n"

        "📊 ВЕРОЯТНОСТЬ ПОБЕДЫ\n"
        f"• {data1['name']}: {probability1}%\n"
        f"• {data2['name']}: {probability2}%\n\n"

        "⚡ FLUX РЕЙТИНГИ\n"
        f"• {data1['name']}: {round(data1['total_score'])}/100\n"
        f"• {data2['name']}: {round(data2['total_score'])}/100\n\n"

        "🎯 ПРОГНОЗ МОДЕЛИ\n"
        f"Победитель: {winner['name']}\n"
        f"Вероятность победы: {winner_probability}%\n"
        f"Ожидаемый способ: {expected_method}\n"
        f"AI Confidence: {confidence}% ({confidence_text})\n"
        f"Риск: {risk_text}\n\n"

        "📈 СРАВНЕНИЕ\n"
        f"• Рекорд: {data1['record']} — {data2['record']}\n"
        f"• Последняя форма: {data1['form']} — {data2['form']}\n"
        f"• Стойка: {data1['striking']} — {data2['striking']}\n"
        f"• Борьба: {data1['grappling']} — {data2['grappling']}\n"
        f"• Опыт: {data1['experience']} — {data2['experience']}\n\n"

        "🥋 СТАТИСТИКА БОЯ\n"
        f"• Удары в минуту: {data1['slpm']:.2f} — {data2['slpm']:.2f}\n"
        f"• Точность ударов: "
        f"{round(data1['striking_accuracy'])}% — "
        f"{round(data2['striking_accuracy'])}%\n"
        f"• Защита от ударов: "
        f"{round(data1['striking_defense'])}% — "
        f"{round(data2['striking_defense'])}%\n"
        f"• Тейкдауны: "
        f"{data1['takedown_average']:.2f} — "
        f"{data2['takedown_average']:.2f}\n"
        f"• Защита от тейкдаунов: "
        f"{round(data1['takedown_defense'])}% — "
        f"{round(data2['takedown_defense'])}%\n\n"

        "📏 ФИЗИЧЕСКИЕ ДАННЫЕ\n"
        f"• Возраст: {format_age(data1['age'])} — "
        f"{format_age(data2['age'])}\n"
        f"• Рост: {data1['height']} — {data2['height']}\n"
        f"• Размах рук: {data1['reach']} — {data2['reach']}\n"
        f"• Стойка: {data1['stance']} — {data2['stance']}\n\n"

        f"📡 Источник: {source}\n"
        f"⏱ Загрузка данных: {response_time} сек.\n"
        "🧪 Модель: FLUX AI UFC Beta v1.0\n\n"

        "⚠️ Прогноз основан на доступной исторической статистике "
        "и не гарантирует результат боя."
    )
