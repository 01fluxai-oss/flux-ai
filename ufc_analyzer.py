from typing import Dict, Tuple


def clean_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def calculate_probabilities(
    fighter1_score: float,
    fighter2_score: float,
) -> Tuple[int, int]:
    total = fighter1_score + fighter2_score

    if total <= 0:
        return 50, 50

    fighter1_probability = round(
        fighter1_score / total * 100
    )
    fighter2_probability = 100 - fighter1_probability

    return fighter1_probability, fighter2_probability


def confidence_label(confidence: int, language: str = "ru") -> str:
    if confidence >= 75:
        return "High" if language == "en" else "Высокая"

    if confidence >= 60:
        return "Medium" if language == "en" else "Средняя"

    return "Low" if language == "en" else "Низкая"


def risk_label(confidence: int, language: str = "ru") -> str:
    if confidence >= 75:
        return "Low" if language == "en" else "Низкий"

    if confidence >= 60:
        return "Medium" if language == "en" else "Средний"

    return "High" if language == "en" else "Высокий"


def build_base_fighter_data(name: str) -> Dict:
    """
    Временная базовая модель.

    На следующем этапе здесь будут реальные данные:
    рекорд, возраст, рост, размах рук, последние бои,
    удары, тейкдауны, защита и способы побед.
    """

    normalized_name = clean_name(name)

    name_score = sum(ord(symbol) for symbol in normalized_name.lower())

    form_score = 60 + name_score % 21
    striking_score = 58 + name_score % 25
    grappling_score = 55 + name_score % 26
    durability_score = 60 + name_score % 21
    experience_score = 58 + name_score % 23

    total_score = (
        form_score * 0.25
        + striking_score * 0.25
        + grappling_score * 0.20
        + durability_score * 0.15
        + experience_score * 0.15
    )

    return {
        "name": normalized_name,
        "form": form_score,
        "striking": striking_score,
        "grappling": grappling_score,
        "durability": durability_score,
        "experience": experience_score,
        "total_score": round(total_score, 2),
    }


def choose_method(
    winner: Dict,
    loser: Dict,
    language: str = "ru",
) -> str:
    striking_advantage = (
        winner["striking"] - loser["striking"]
    )
    grappling_advantage = (
        winner["grappling"] - loser["grappling"]
    )

    if grappling_advantage >= 8:
        return (
            "Submission"
            if language == "en"
            else "Сабмишен"
        )

    if striking_advantage >= 8:
        return (
            "KO/TKO"
            if language == "en"
            else "KO/TKO"
        )

    return (
        "Decision"
        if language == "en"
        else "Решение судей"
    )


def analyze_ufc_match(
    fighter1: str,
    fighter2: str,
    language: str = "ru",
) -> str:
    fighter1 = clean_name(fighter1)
    fighter2 = clean_name(fighter2)

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

    data1 = build_base_fighter_data(fighter1)
    data2 = build_base_fighter_data(fighter2)

    probability1, probability2 = calculate_probabilities(
        data1["total_score"],
        data2["total_score"],
    )

    if probability1 >= probability2:
        winner = data1
        loser = data2
        winner_probability = probability1
    else:
        winner = data2
        loser = data1
        winner_probability = probability2

    confidence = max(
        52,
        min(
            82,
            50 + abs(probability1 - probability2),
        ),
    )

    method = choose_method(
        winner,
        loser,
        language,
    )

    confidence_text = confidence_label(
        confidence,
        language,
    )
    risk_text = risk_label(
        confidence,
        language,
    )

    if language == "en":
        return (
            "🥊 FLUX AI UFC — FIGHT ANALYSIS\n\n"
            f"{fighter1} vs {fighter2}\n\n"
            "📊 WIN PROBABILITY\n"
            f"• {fighter1}: {probability1}%\n"
            f"• {fighter2}: {probability2}%\n\n"
            "⚡ FIGHTER RATINGS\n"
            f"• {fighter1}: {round(data1['total_score'])}/100\n"
            f"• {fighter2}: {round(data2['total_score'])}/100\n\n"
            "🎯 MODEL PICK\n"
            f"Winner: {winner['name']}\n"
            f"Expected method: {method}\n"
            f"AI Confidence: {confidence}% ({confidence_text})\n"
            f"Risk: {risk_text}\n\n"
            "📈 ANALYSIS FACTORS\n"
            f"• Form: {data1['form']} — {data2['form']}\n"
            f"• Striking: {data1['striking']} — {data2['striking']}\n"
            f"• Grappling: {data1['grappling']} — {data2['grappling']}\n"
            f"• Durability: {data1['durability']} — {data2['durability']}\n"
            f"• Experience: {data1['experience']} — {data2['experience']}\n\n"
            "🧪 Mode: UFC Beta\n"
            "⚠️ Real UFC statistics will be connected in the next update.\n\n"
            "Predictions are informational and do not guarantee results."
        )

    return (
        "🥊 FLUX AI UFC — АНАЛИЗ БОЯ\n\n"
        f"{fighter1} vs {fighter2}\n\n"
        "📊 ВЕРОЯТНОСТЬ ПОБЕДЫ\n"
        f"• {fighter1}: {probability1}%\n"
        f"• {fighter2}: {probability2}%\n\n"
        "⚡ РЕЙТИНГИ БОЙЦОВ\n"
        f"• {fighter1}: {round(data1['total_score'])}/100\n"
        f"• {fighter2}: {round(data2['total_score'])}/100\n\n"
        "🎯 ПРОГНОЗ МОДЕЛИ\n"
        f"Победитель: {winner['name']}\n"
        f"Ожидаемый способ: {method}\n"
        f"AI Confidence: {confidence}% ({confidence_text})\n"
        f"Риск: {risk_text}\n\n"
        "📈 ФАКТОРЫ АНАЛИЗА\n"
        f"• Форма: {data1['form']} — {data2['form']}\n"
        f"• Стойка: {data1['striking']} — {data2['striking']}\n"
        f"• Борьба: {data1['grappling']} — {data2['grappling']}\n"
        f"• Выносливость: {data1['durability']} — {data2['durability']}\n"
        f"• Опыт: {data1['experience']} — {data2['experience']}\n\n"
        "🧪 Режим: UFC Beta\n"
        "⚠️ Реальную статистику UFC подключим следующим обновлением.\n\n"
        "Прогноз носит информационный характер и не гарантирует результат."
    )
