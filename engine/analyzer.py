from providers.thesportsdb import get_match_data
from engine.v3_engine import analyze_v3


CHANNEL_URL = "https://t.me/FluxAIDaily"


PICK_LABELS = {
    "ru": {
        "over_1_5": "ТБ 1.5",
        "over_2_5": "ТБ 2.5",
        "under_2_5": "ТМ 2.5",
        "btts_yes": "Обе забьют — Да",
        "btts_no": "Обе забьют — Нет",
        "p1": "П1",
        "p2": "П2",
        "draw": "X",
        "double_1x": "1X",
        "double_x2": "X2",
        "double_12": "12",
    },
    "en": {
        "over_1_5": "Over 1.5 Goals",
        "over_2_5": "Over 2.5 Goals",
        "under_2_5": "Under 2.5 Goals",
        "btts_yes": "Both Teams to Score — Yes",
        "btts_no": "Both Teams to Score — No",
        "p1": "Home Win",
        "p2": "Away Win",
        "draw": "Draw",
        "double_1x": "Home or Draw (1X)",
        "double_x2": "Draw or Away (X2)",
        "double_12": "Either Team to Win (12)",
    },
}


RISK_LABELS = {
    "ru": {
        "low": "Низкий",
        "medium": "Средний",
        "high": "Высокий",
    },
    "en": {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
    },
}


def pick_label(
    code,
    language="ru",
):
    labels = PICK_LABELS.get(
        language,
        PICK_LABELS["ru"],
    )

    return labels.get(
        code,
        str(code),
    )


def risk_label(
    code,
    language="ru",
):
    labels = RISK_LABELS.get(
        language,
        RISK_LABELS["ru"],
    )

    return labels.get(
        code,
        str(code),
    )


def bar(value):
    value = max(
        0,
        min(
            100,
            int(value),
        ),
    )

    blocks = round(
        value / 10
    )

    return (
        "█" * blocks
        + "░" * (10 - blocks)
    )


def form_bar(value):
    value = int(value)

    if value >= 85:
        return "🟢🟢🟢🟢🟢"

    if value >= 75:
        return "🟢🟢🟢🟢🟡"

    if value >= 65:
        return "🟢🟢🟢🟡🔴"

    if value >= 55:
        return "🟢🟢🟡🔴🔴"

    return "🟢🟡🔴🔴🔴"


def strength_icon(value):
    value = int(value)

    if value >= 80:
        return "🟢"

    if value >= 65:
        return "🟡"

    return "🔴"


def format_top_3(
    best_pick,
    language="ru",
):
    top_3 = best_pick.get(
        "top_3",
        [],
    )

    if not top_3:
        code = best_pick.get(
            "pick",
            "—",
        )

        value = best_pick.get(
            "value",
            "—",
        )

        return (
            f"🥇 {pick_label(code, language)} "
            f"— {value}%"
        )

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    lines = []

    for index, item in enumerate(
        top_3[:3]
    ):
        code, value = item

        lines.append(
            f"{medals[index]} "
            f"{pick_label(code, language)} "
            f"— {value}% "
            f"{strength_icon(value)}"
        )

    return "\n".join(lines)


def build_ai_comment(
    result,
    main_pick,
    main_value,
    language="ru",
):
    team1 = result["team1"]
    team2 = result["team2"]

    rating1 = result["team1_rating"]
    rating2 = result["team2_rating"]

    form1 = rating1["form"]
    form2 = rating2["form"]

    attack1 = rating1["attack"]
    attack2 = rating2["attack"]

    defense1 = rating1["defense"]
    defense2 = rating2["defense"]

    totals = result["totals"]

    over_25 = totals["over_2_5"]
    btts_yes = totals["btts_yes"]

    data_quality = int(
        result.get(
            "data_quality",
            0,
        )
    )

    preliminary = (
        data_quality < 25
    )

    lines = [
        "🧠 FLUX AI Coach",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if language == "en":
        lines.extend([
            "📈 Recent Form",
            "",
            f"{team1}: {form_bar(form1)}",
            f"{team2}: {form_bar(form2)}",
            "",
            "📊 Overall Form",
        ])

        if form1 > form2 + 5:
            lines.append(
                f"✅ {team1} is in better form."
            )
        elif form2 > form1 + 5:
            lines.append(
                f"✅ {team2} is in better form."
            )
        else:
            lines.append(
                "⚖️ The teams are in similar form."
            )

        lines.extend([
            "",
            "⚔️ Attack",
        ])

        if attack1 > attack2 + 5:
            lines.append(
                f"🔥 {team1}'s attack looks stronger."
            )
        elif attack2 > attack1 + 5:
            lines.append(
                f"🔥 {team2}'s attack looks stronger."
            )
        else:
            lines.append(
                "⚖️ Attacking potential is similar."
            )

        lines.extend([
            "",
            "🛡 Defense",
        ])

        if defense1 > defense2 + 5:
            lines.append(
                f"🧱 {team1}'s defense looks stronger."
            )
        elif defense2 > defense1 + 5:
            lines.append(
                f"🧱 {team2}'s defense looks stronger."
            )
        else:
            lines.append(
                "⚖️ Defensive strength is similar."
            )

        lines.append("")

        if over_25 >= 70:
            lines.append(
                "⚽ The model expects a high-scoring game."
            )
        elif over_25 <= 40:
            lines.append(
                "⚽ The model expects a cautious game."
            )
        else:
            lines.append(
                "⚽ An open game is possible."
            )

        if btts_yes >= 65:
            lines.append(
                "🥅 There is a strong chance both teams score."
            )

        title = (
            "⚠️ Preliminary Option"
            if preliminary
            else "⭐ Main Recommendation"
        )

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            title,
            f"👉 {pick_label(main_pick, language)}",
            f"🎯 Probability: {main_value}%",
        ])

        return "\n".join(lines)

    lines.extend([
        "📈 Последняя форма",
        "",
        f"{team1}: {form_bar(form1)}",
        f"{team2}: {form_bar(form2)}",
        "",
        "📊 Общая форма",
    ])

    if form1 > form2 + 5:
        lines.append(
            f"✅ {team1} находится в лучшей форме."
        )
    elif form2 > form1 + 5:
        lines.append(
            f"✅ {team2} находится в лучшей форме."
        )
    else:
        lines.append(
            "⚖️ Команды находятся примерно в одинаковой форме."
        )

    lines.extend([
        "",
        "⚔️ Атака",
    ])

    if attack1 > attack2 + 5:
        lines.append(
            f"🔥 Атака {team1} выглядит опаснее."
        )
    elif attack2 > attack1 + 5:
        lines.append(
            f"🔥 Атака {team2} выглядит опаснее."
        )
    else:
        lines.append(
            "⚖️ Атакующий потенциал примерно одинаковый."
        )

    lines.extend([
        "",
        "🛡 Защита",
    ])

    if defense1 > defense2 + 5:
        lines.append(
            f"🧱 Защита {team1} выглядит надежнее."
        )
    elif defense2 > defense1 + 5:
        lines.append(
            f"🧱 Защита {team2} выглядит надежнее."
        )
    else:
        lines.append(
            "⚖️ Защита команд примерно одинаковая."
        )

    lines.append("")

    if over_25 >= 70:
        lines.append(
            "⚽ Модель ожидает большое количество голов."
        )
    elif over_25 <= 40:
        lines.append(
            "⚽ Ожидается осторожный матч."
        )
    else:
        lines.append(
            "⚽ Возможен открытый футбол."
        )

    if btts_yes >= 65:
        lines.append(
            "🥅 Высока вероятность обмена голами."
        )

    title = (
        "⚠️ Предварительный вариант"
        if preliminary
        else "⭐ Главная рекомендация"
    )

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        title,
        f"👉 {pick_label(main_pick, language)}",
        f"🎯 Вероятность: {main_value}%",
    ])

    return "\n".join(lines)


def analyze_match_v2(
    team1,
    team2,
):
    data = get_match_data(
        team1,
        team2,
    )

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]

    result = analyze_v3(
        team1=data.get(
            "team1",
            team1,
        ),
        team2=data.get(
            "team2",
            team2,
        ),
        team1_form=team1_form,
        team2_form=team2_form,
    )

    source_parts = []

    team1_source = team1_form.get(
        "data_source",
        "api",
    )

    team2_source = team2_form.get(
        "data_source",
        "api",
    )

    if team1_source == "fallback":
        source_parts.append(
            f"{result['team1']}: FLUX fallback"
        )
    else:
        source_parts.append(
            f"{result['team1']}: TheSportsDB"
        )

    if team2_source == "fallback":
        source_parts.append(
            f"{result['team2']}: FLUX fallback"
        )
    else:
        source_parts.append(
            f"{result['team2']}: TheSportsDB"
        )

    data_source = " | ".join(
        source_parts
    )

    return {
        "team1": result["team1"],
        "team2": result["team2"],
        "source": data_source,
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_rating": result["team1_rating"],
        "team2_rating": result["team2_rating"],
        "probabilities": result["probabilities"],
        "totals": result["totals"],
        "double_chance": result["double_chance"],
        "predicted_score": result["predicted_score"],
        "best_pick": result["best_pick"],
        "risk": result["risk"],
        "confidence": result["confidence"],
        "data_quality": result["data_quality"],
    }


def format_analysis(
    result,
    language="ru",
):
    team1 = result["team1"]
    team2 = result["team2"]

    probabilities = result["probabilities"]
    totals = result["totals"]
    double_chance = result["double_chance"]

    score = result["predicted_score"].get(
        "score",
        "—",
    )

    top_3 = result["best_pick"].get(
        "top_3",
        [],
    )

    if top_3:
        main_pick = top_3[0][0]
        main_value = top_3[0][1]
    else:
        main_pick = result["best_pick"]["pick"]
        main_value = result["best_pick"]["value"]

    confidence = int(
        result["confidence"]
    )

    team1_rating = result[
        "team1_rating"
    ]["rating"]

    team2_rating = result[
        "team2_rating"
    ]["rating"]

    power_diff = (
        team1_rating
        - team2_rating
    )

    if power_diff > 0:
        power_text = (
            f"{team1} +{power_diff}"
        )
    elif power_diff < 0:
        power_text = (
            f"{team2} +{abs(power_diff)}"
        )
    else:
        power_text = (
            "Equal balance"
            if language == "en"
            else "Равный баланс"
        )

    top_3_text = format_top_3(
        result["best_pick"],
        language,
    )

    main_pick_text = pick_label(
        main_pick,
        language,
    )

    risk_text = risk_label(
        result["risk"],
        language,
    )

    raw_data_quality = int(
        result.get(
            "data_quality",
            0,
        )
    )

    data_source = result.get(
        "source",
        "FLUX AI",
    )

    fallback_count = data_source.count(
        "FLUX fallback"
    )

    if fallback_count >= 2:
        data_quality = min(
            raw_data_quality,
            55,
        )
    elif fallback_count == 1:
        data_quality = min(
            raw_data_quality,
            70,
        )
    else:
        data_quality = min(
            raw_data_quality,
            100,
        )

    result["data_quality"] = data_quality

    if data_quality >= 80:
        quality_icon = "🟢"
    elif data_quality >= 50:
        quality_icon = "🟡"
    else:
        quality_icon = "🔴"

    if data_quality < 25:
        quality_warning = (
            "⚠️ Very limited data. "
            "This is a preliminary forecast."
            if language == "en"
            else
            "⚠️ Очень мало данных. "
            "Прогноз предварительный."
        )
        prediction_title = (
            "⚠️ Preliminary Prediction"
            if language == "en"
            else "⚠️ Предварительный прогноз"
        )
    elif data_quality < 40:
        quality_warning = (
            "⚠️ Low data quality. "
            "Use this forecast cautiously."
            if language == "en"
            else
            "⚠️ Низкое качество данных. "
            "Используйте прогноз осторожно."
        )
        prediction_title = (
            "⭐ Main Prediction"
            if language == "en"
            else "⭐ Главный прогноз"
        )
    else:
        quality_warning = ""
        prediction_title = (
            "⭐ Main Prediction"
            if language == "en"
            else "⭐ Главный прогноз"
        )

    ai_comment = build_ai_comment(
        result,
        main_pick,
        main_value,
        language,
    )

    warning_block = (
        f"\n\n{quality_warning}"
        if quality_warning
        else ""
    )

    if language == "en":
        return f"""🏆 FLUX AI PRO
━━━━━━━━━━━━━━━━━━━━

⚽ Match
{team1} — {team2}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{team1}
{bar(team1_rating)} {team1_rating}/100

{team2}
{bar(team2_rating)} {team2_rating}/100

Advantage:
{power_text}

━━━━━━━━━━━━━━━━━━━━

🔥 FLUX Rating

{team1}
{bar(team1_rating)} {team1_rating}/100

{team2}
{bar(team2_rating)} {team2_rating}/100

━━━━━━━━━━━━━━━━━━━━

📊 Match Outcome

Home {bar(probabilities["p1"])} {probabilities["p1"]}%
Draw {bar(probabilities["draw"])} {probabilities["draw"]}%
Away {bar(probabilities["p2"])} {probabilities["p2"]}%

━━━━━━━━━━━━━━━━━━━━

{prediction_title}
👉 {main_pick_text}

🎯 Probability:
{main_value}%

🧠 AI Confidence:
{bar(confidence)} {confidence}%
{warning_block}

━━━━━━━━━━━━━━━━━━━━

🏆 TOP-3 Predictions
{top_3_text}

━━━━━━━━━━━━━━━━━━━━

⚽ Goal Totals

Over 1.5 — {totals.get("over_1_5", "—")}%
Over 2.5 — {totals.get("over_2_5", "—")}%
Over 3.5 — {totals.get("over_3_5", "—")}%

🥅 Both Teams to Score:
Yes — {totals.get("btts_yes", "—")}%
No — {totals.get("btts_no", "—")}%

━━━━━━━━━━━━━━━━━━━━

🔒 Double Chance

1X — {double_chance.get("1X", "—")}%
12 — {double_chance.get("12", "—")}%
X2 — {double_chance.get("X2", "—")}%

━━━━━━━━━━━━━━━━━━━━

📊 Predicted Score:
{score}

⚠️ Risk Level:
{risk_text}

📡 Data Source:
{data_source}

🧪 Data Quality:
{quality_icon} {data_quality}%

━━━━━━━━━━━━━━━━━━━━

{ai_comment}

━━━━━━━━━━━━━━━━━━━━

📢 Daily Top 3 predictions:
{CHANNEL_URL}

Important:
Predictions are informational and do not guarantee results.
"""

    return f"""🏆 FLUX AI PRO
━━━━━━━━━━━━━━━━━━━━

⚽ Матч
{team1} — {team2}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{team1}
{bar(team1_rating)} {team1_rating}/100

{team2}
{bar(team2_rating)} {team2_rating}/100

Преимущество:
{power_text}

━━━━━━━━━━━━━━━━━━━━

🔥 FLUX Rating

{team1}
{bar(team1_rating)} {team1_rating}/100

{team2}
{bar(team2_rating)} {team2_rating}/100

━━━━━━━━━━━━━━━━━━━━

📊 Исход

П1 {bar(probabilities["p1"])} {probabilities["p1"]}%
X  {bar(probabilities["draw"])} {probabilities["draw"]}%
П2 {bar(probabilities["p2"])} {probabilities["p2"]}%

━━━━━━━━━━━━━━━━━━━━

{prediction_title}
👉 {main_pick_text}

🎯 Вероятность:
{main_value}%

🧠 AI Confidence:
{bar(confidence)} {confidence}%
{warning_block}

━━━━━━━━━━━━━━━━━━━━

🏆 ТОП-3 прогноза
{top_3_text}

━━━━━━━━━━━━━━━━━━━━

⚽ Тоталы

ТБ 1.5 — {totals.get("over_1_5", "—")}%
ТБ 2.5 — {totals.get("over_2_5", "—")}%
ТБ 3.5 — {totals.get("over_3_5", "—")}%

🥅 Обе забьют:
Да — {totals.get("btts_yes", "—")}%
Нет — {totals.get("btts_no", "—")}%

━━━━━━━━━━━━━━━━━━━━

🔒 Двойной шанс

1X — {double_chance.get("1X", "—")}%
12 — {double_chance.get("12", "—")}%
X2 — {double_chance.get("X2", "—")}%

━━━━━━━━━━━━━━━━━━━━

📊 Вероятный счёт:
{score}

⚠️ Риск:
{risk_text}

📡 Источник данных:
{data_source}

🧪 Качество данных:
{quality_icon} {data_quality}%

━━━━━━━━━━━━━━━━━━━━

{ai_comment}

━━━━━━━━━━━━━━━━━━━━

📢 Ежедневные ТОП-3 прогнозы:
{CHANNEL_URL}

Важно:
Прогноз не является гарантией результата.
"""


def analyze_and_format(
    team1,
    team2,
    language="ru",
):
    result = analyze_match_v2(
        team1,
        team2,
    )

    return format_analysis(
        result,
        language,
    )


__all__ = [
    "analyze_match_v2",
    "format_analysis",
    "analyze_and_format",
]
