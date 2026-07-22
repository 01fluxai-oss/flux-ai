from providers.nba_provider import (
    get_nba_match_data,
)

from engine.nba_engine import (
    analyze_nba_match,
)


PICK_LABELS = {
    "ru": {
        "home_win": "Победа первой команды",
        "away_win": "Победа второй команды",
        "over_total": "Тотал больше",
        "under_total": "Тотал меньше",
        "team1_form": "Сильная форма первой команды",
        "team2_form": "Сильная форма второй команды",
        "close_game": "Равная игра",
    },
    "en": {
        "home_win": "Home Team Win",
        "away_win": "Away Team Win",
        "over_total": "Over Total",
        "under_total": "Under Total",
        "team1_form": "Strong Home Team Form",
        "team2_form": "Strong Away Team Form",
        "close_game": "Close Game",
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


PACE_LABELS = {
    "ru": {
        "high": "Высокий темп",
        "medium": "Средний темп",
        "low": "Низкий темп",
    },
    "en": {
        "high": "High Pace",
        "medium": "Medium Pace",
        "low": "Low Pace",
    },
}


def progress_bar(value, length=10):
    value = max(
        0,
        min(
            100,
            int(value),
        ),
    )

    filled = round(
        value / 100 * length
    )

    return (
        "█" * filled
        + "░" * (
            length - filled
        )
    )


def probability_icon(value):
    value = int(value)

    if value >= 75:
        return "🟢"

    if value >= 58:
        return "🟡"

    return "🔴"


def quality_icon(value):
    value = int(value)

    if value >= 80:
        return "🟢"

    if value >= 50:
        return "🟡"

    return "🔴"


def recent_form_icons(form):
    recent = form.get(
        "recent",
        [],
    )

    if not recent:
        return "—"

    icons = []

    for game in recent[:5]:
        if game.get(
            "result"
        ) == "win":
            icons.append("🟢")
        else:
            icons.append("🔴")

    return "".join(icons)


def format_pick(
    code,
    value,
    language,
    team1_name,
    team2_name,
    total_line,
):
    labels = PICK_LABELS.get(
        language,
        PICK_LABELS["en"],
    )

    if code == "home_win":
        return (
            f"{team1_name} — "
            f"{int(value)}%"
        )

    if code == "away_win":
        return (
            f"{team2_name} — "
            f"{int(value)}%"
        )

    if code == "over_total":
        if language == "ru":
            return (
                f"Тотал больше "
                f"{total_line} — "
                f"{int(value)}%"
            )

        return (
            f"Over "
            f"{total_line} — "
            f"{int(value)}%"
        )

    if code == "under_total":
        if language == "ru":
            return (
                f"Тотал меньше "
                f"{total_line} — "
                f"{int(value)}%"
            )

        return (
            f"Under "
            f"{total_line} — "
            f"{int(value)}%"
        )

    if code == "team1_form":
        return (
            f"{team1_name}: "
            f"{labels[code]} — "
            f"{int(value)}%"
        )

    if code == "team2_form":
        return (
            f"{team2_name}: "
            f"{labels[code]} — "
            f"{int(value)}%"
        )

    return (
        f"{labels.get(code, code)} — "
        f"{int(value)}%"
    )


def build_nba_comment(
    result,
    language="en",
):
    team1 = result["team1"]
    team2 = result["team2"]

    team1_name = team1["name"]
    team2_name = team2["name"]

    team1_rating = result[
        "team1_rating"
    ]

    team2_rating = result[
        "team2_rating"
    ]

    recent_form1 = result[
        "recent_form1"
    ]

    recent_form2 = result[
        "recent_form2"
    ]

    pace_level = result[
        "pace_signal"
    ]["level"]

    pace_text = PACE_LABELS[
        language
    ][pace_level]

    lines = []

    if language == "ru":
        lines.append(
            "🧠 FLUX AI NBA Coach"
        )
        lines.append(
            "━━━━━━━━━━━━━━━━━━━━"
        )
        lines.append("")
        lines.append(
            "📈 Текущая форма"
        )
        lines.append("")

        if recent_form1 > recent_form2:
            lines.append(
                f"✅ {team1_name} находится "
                f"в лучшей форме."
            )

        elif recent_form2 > recent_form1:
            lines.append(
                f"✅ {team2_name} находится "
                f"в лучшей форме."
            )

        else:
            lines.append(
                "⚖️ Форма команд примерно равна."
            )

        lines.append("")
        lines.append(
            "⚔️ Атака"
        )

        offense_difference = (
            team1_rating["offense"]
            - team2_rating["offense"]
        )

        if offense_difference >= 8:
            lines.append(
                f"🔥 Атака {team1_name} "
                f"выглядит сильнее."
            )

        elif offense_difference <= -8:
            lines.append(
                f"🔥 Атака {team2_name} "
                f"выглядит сильнее."
            )

        else:
            lines.append(
                "⚖️ Атакующий потенциал "
                "примерно равен."
            )

        lines.append("")
        lines.append(
            "🛡 Защита"
        )

        defense_difference = (
            team1_rating["defense"]
            - team2_rating["defense"]
        )

        if defense_difference >= 8:
            lines.append(
                f"🧱 Защита {team1_name} "
                f"выглядит надёжнее."
            )

        elif defense_difference <= -8:
            lines.append(
                f"🧱 Защита {team2_name} "
                f"выглядит надёжнее."
            )

        else:
            lines.append(
                "⚖️ Защитные показатели "
                "примерно равны."
            )

        lines.append("")
        lines.append(
            f"🏃 Темп матча: {pace_text}."
        )

        return "\n".join(lines)

    lines.append(
        "🧠 FLUX AI NBA Coach"
    )
    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )
    lines.append("")
    lines.append(
        "📈 Current Form"
    )
    lines.append("")

    if recent_form1 > recent_form2:
        lines.append(
            f"✅ {team1_name} is in "
            f"better form."
        )

    elif recent_form2 > recent_form1:
        lines.append(
            f"✅ {team2_name} is in "
            f"better form."
        )

    else:
        lines.append(
            "⚖️ The teams are in "
            "similar form."
        )

    lines.append("")
    lines.append(
        "⚔️ Offense"
    )

    offense_difference = (
        team1_rating["offense"]
        - team2_rating["offense"]
    )

    if offense_difference >= 8:
        lines.append(
            f"🔥 {team1_name} has the "
            f"stronger offense."
        )

    elif offense_difference <= -8:
        lines.append(
            f"🔥 {team2_name} has the "
            f"stronger offense."
        )

    else:
        lines.append(
            "⚖️ Offensive potential "
            "is similar."
        )

    lines.append("")
    lines.append(
        "🛡 Defense"
    )

    defense_difference = (
        team1_rating["defense"]
        - team2_rating["defense"]
    )

    if defense_difference >= 8:
        lines.append(
            f"🧱 {team1_name} has the "
            f"stronger defense."
        )

    elif defense_difference <= -8:
        lines.append(
            f"🧱 {team2_name} has the "
            f"stronger defense."
        )

    else:
        lines.append(
            "⚖️ Defensive performance "
            "is similar."
        )

    lines.append("")
    lines.append(
        f"🏃 Expected pace: {pace_text}."
    )

    return "\n".join(lines)


def analyze_nba_match_v2(
    team1_name,
    team2_name,
):
    match_data = get_nba_match_data(
        team1_name,
        team2_name,
    )

    result = analyze_nba_match(
        match_data["team1"],
        match_data["team2"],
        match_data["team1_form"],
        match_data["team2_form"],
    )

    result["team1_form"] = (
        match_data["team1_form"]
    )

    result["team2_form"] = (
        match_data["team2_form"]
    )

    result["source"] = (
        match_data.get(
            "source",
            "BALLDONTLIE",
        )
    )

    result["data_warning"] = (
        match_data.get(
            "data_warning"
        )
    )

    provider_quality = int(
        match_data.get(
            "data_quality",
            0,
        )
    )

    engine_quality = int(
        result.get(
            "data_quality",
            0,
        )
    )

    result["data_quality"] = min(
        provider_quality,
        engine_quality,
    )

    return result


def format_nba_analysis(
    result,
    language="en",
):
    if language not in (
        "ru",
        "en",
    ):
        language = "en"

    team1 = result["team1"]
    team2 = result["team2"]

    team1_name = team1["name"]
    team2_name = team2["name"]

    team1_rating = result[
        "team1_rating"
    ]["rating"]

    team2_rating = result[
        "team2_rating"
    ]["rating"]

    probabilities = result[
        "probabilities"
    ]

    expected_points = result[
        "expected_points"
    ]

    total_market = result[
        "total_market"
    ]

    main_pick = result[
        "main_pick"
    ]

    top_insights = result[
        "top_insights"
    ]

    confidence = int(
        result.get(
            "confidence",
            0,
        )
    )

    data_quality = int(
        result.get(
            "data_quality",
            0,
        )
    )

    source = result.get(
        "source",
        "BALLDONTLIE",
    )

    risk_code = result.get(
        "risk",
        "high",
    )

    risk_text = RISK_LABELS[
        language
    ].get(
        risk_code,
        risk_code,
    )

    pace_code = result[
        "pace_signal"
    ]["level"]

    pace_text = PACE_LABELS[
        language
    ].get(
        pace_code,
        pace_code,
    )

    total_line = total_market[
        "reference_line"
    ]

    main_pick_text = format_pick(
        main_pick["pick"],
        main_pick["value"],
        language,
        team1_name,
        team2_name,
        total_line,
    )

    top_lines = []

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    for index, item in enumerate(
        top_insights[:3]
    ):
        code, value = item

        formatted = format_pick(
            code,
            value,
            language,
            team1_name,
            team2_name,
            total_line,
        )

        top_lines.append(
            f"{medals[index]} "
            f"{formatted} "
            f"{probability_icon(value)}"
        )

    while len(top_lines) < 3:
        top_lines.append(
            f"{medals[len(top_lines)]} —"
        )

    team1_form_icons = (
        recent_form_icons(
            result["team1_form"]
        )
    )

    team2_form_icons = (
        recent_form_icons(
            result["team2_form"]
        )
    )

    coach_comment = build_nba_comment(
        result,
        language=language,
    )

    quality_status = (
        f"{quality_icon(data_quality)} "
        f"{data_quality}%"
    )

    if language == "ru":
        return f"""🏀 FLUX AI NBA PRO
━━━━━━━━━━━━━━━━━━━━

🏟 Матч
{team1_name} — {team2_name}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{team1_name}
{progress_bar(team1_rating)} {team1_rating}/100

{team2_name}
{progress_bar(team2_rating)} {team2_rating}/100

Преимущество:
{team1_name if team1_rating >= team2_rating else team2_name} +{abs(team1_rating - team2_rating)}

━━━━━━━━━━━━━━━━━━━━

📊 Вероятность победы

{team1_name}
{progress_bar(probabilities["home"])} {probabilities["home"]}%

{team2_name}
{progress_bar(probabilities["away"])} {probabilities["away"]}%

━━━━━━━━━━━━━━━━━━━━

⭐ Главный прогноз
👉 {main_pick_text}

🧠 Уверенность модели:
{progress_bar(confidence)} {confidence}%

━━━━━━━━━━━━━━━━━━━━

🏆 TOP-3 прогноза
{top_lines[0]}
{top_lines[1]}
{top_lines[2]}

━━━━━━━━━━━━━━━━━━━━

🏀 Ожидаемый счёт

{team1_name} — {expected_points["team1_points"]}
{team2_name} — {expected_points["team2_points"]}

📊 Прогнозируемый тотал:
{total_market["model_total"]}

📈 Линия модели:
{total_line}

Тотал больше — {total_market["over_probability"]}%
Тотал меньше — {total_market["under_probability"]}%

━━━━━━━━━━━━━━━━━━━━

🏃 Темп матча:
{pace_text}

📈 Последняя форма

{team1_name}: {team1_form_icons}
{team2_name}: {team2_form_icons}

⚠️ Уровень риска:
{risk_text}

📡 Источник данных:
{source}

🧪 Качество данных:
{quality_status}

━━━━━━━━━━━━━━━━━━━━

{coach_comment}

━━━━━━━━━━━━━━━━━━━━

📢 Ежедневные TOP-3 прогнозы:
https://t.me/FluxAIDaily

Важно:
Прогнозы носят информационный характер и не гарантируют результат."""

    return f"""🏀 FLUX AI NBA PRO
━━━━━━━━━━━━━━━━━━━━

🏟 Match
{team1_name} — {team2_name}

━━━━━━━━━━━━━━━━━━━━

⚡ FLUX Power Index

{team1_name}
{progress_bar(team1_rating)} {team1_rating}/100

{team2_name}
{progress_bar(team2_rating)} {team2_rating}/100

Advantage:
{team1_name if team1_rating >= team2_rating else team2_name} +{abs(team1_rating - team2_rating)}

━━━━━━━━━━━━━━━━━━━━

📊 Win Probability

{team1_name}
{progress_bar(probabilities["home"])} {probabilities["home"]}%

{team2_name}
{progress_bar(probabilities["away"])} {probabilities["away"]}%

━━━━━━━━━━━━━━━━━━━━

⭐ Main Prediction
👉 {main_pick_text}

🧠 Model Confidence:
{progress_bar(confidence)} {confidence}%

━━━━━━━━━━━━━━━━━━━━

🏆 TOP-3 Predictions
{top_lines[0]}
{top_lines[1]}
{top_lines[2]}

━━━━━━━━━━━━━━━━━━━━

🏀 Expected Score

{team1_name} — {expected_points["team1_points"]}
{team2_name} — {expected_points["team2_points"]}

📊 Projected Total:
{total_market["model_total"]}

📈 Model Line:
{total_line}

Over — {total_market["over_probability"]}%
Under — {total_market["under_probability"]}%

━━━━━━━━━━━━━━━━━━━━

🏃 Expected Pace:
{pace_text}

📈 Recent Form

{team1_name}: {team1_form_icons}
{team2_name}: {team2_form_icons}

⚠️ Risk Level:
{risk_text}

📡 Data Source:
{source}

🧪 Data Quality:
{quality_status}

━━━━━━━━━━━━━━━━━━━━

{coach_comment}

━━━━━━━━━━━━━━━━━━━━

📢 Daily Top 3 predictions:
https://t.me/FluxAIDaily

Important:
Predictions are informational and do not guarantee results."""


def analyze_and_format_nba(
    team1_name,
    team2_name,
    language="en",
):
    result = analyze_nba_match_v2(
        team1_name,
        team2_name,
    )

    return format_nba_analysis(
        result,
        language=language,
    )


__all__ = [
    "analyze_nba_match_v2",
    "format_nba_analysis",
    "analyze_and_format_nba",
]
