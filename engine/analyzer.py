from providers.thesportsdb import get_match_data
from engine.v3_engine import analyze_v3


CHANNEL_URL = "https://t.me/FluxAIDaily"


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]

    v3 = analyze_v3(
        team1=data.get("team1", team1),
        team2=data.get("team2", team2),
        team1_form=team1_form,
        team2_form=team2_form,
    )

    return {
        "team1": v3["team1"],
        "team2": v3["team2"],
        "source": data.get("source", "TheSportsDB + FLUX fallback"),
        "team1_form": team1_form,
        "team2_form": team2_form,
        "team1_rating": v3["team1_rating"],
        "team2_rating": v3["team2_rating"],
        "probabilities": v3["probabilities"],
        "totals": v3["totals"],
        "double_chance": v3.get("double_chance", {}),
        "predicted_score": v3.get("predicted_score", {}),
        "best_pick": v3["best_pick"],
        "risk": v3["risk"],
        "confidence": v3["confidence"],
        "data_quality": v3["data_quality"],
    }


def strength_icon(value):
    if value >= 80:
        return "🟢"
    if value >= 65:
        return "🟡"
    return "🔴"


def confidence_stars(confidence):
    filled = max(1, min(10, int(confidence)))
    return "★" * filled + "☆" * (10 - filled)


def format_top_3(best_pick):
    top_3 = best_pick.get("top_3", [])

    if not top_3:
        return f"🥇 {best_pick['pick']} — {best_pick['value']}% {strength_icon(best_pick['value'])}"

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for index, item in enumerate(top_3[:3]):
        name, value = item
        lines.append(f"{medals[index]} {name} — {value}% {strength_icon(value)}")

    return "\n".join(lines)


def build_ai_comment(result, main_pick, main_value):
    team1 = result["team1"]
    team2 = result["team2"]

    rating1 = result["team1_rating"]["rating"]
    rating2 = result["team2_rating"]["rating"]

    form1 = result["team1_rating"]["form"]
    form2 = result["team2_rating"]["form"]

    attack1 = result["team1_rating"]["attack"]
    attack2 = result["team2_rating"]["attack"]

    defense1 = result["team1_rating"]["defense"]
    defense2 = result["team2_rating"]["defense"]

    probs = result["probabilities"]

    if probs["p1"] > probs["p2"]:
        favorite = team1
    elif probs["p2"] > probs["p1"]:
        favorite = team2
    else:
        favorite = "ни одна из команд"

    lines = []
    lines.append("🧠 FLUX AI Coach")
    lines.append("")
    lines.append(f"Модель считает фаворитом матча: {favorite}.")
    lines.append("")

    if abs(rating1 - rating2) >= 10:
        better = team1 if rating1 > rating2 else team2
        lines.append(f"⭐ Общий рейтинг выше у {better}.")
    else:
        lines.append("⭐ По общему рейтингу команды близки.")

    if abs(form1 - form2) >= 12:
        better = team1 if form1 > form2 else team2
        lines.append(f"📈 Лучшую текущую форму показывает {better}.")
    else:
        lines.append("📈 По текущей форме сильного преимущества нет.")

    if attack1 > attack2 + 10:
        lines.append(f"⚔️ Атака {team1} выглядит опаснее.")
    elif attack2 > attack1 + 10:
        lines.append(f"⚔️ Атака {team2} выглядит опаснее.")

    if defense1 > defense2 + 10:
        lines.append(f"🛡 Защита {team1} выглядит надежнее.")
    elif defense2 > defense1 + 10:
        lines.append(f"🛡 Защита {team2} выглядит надежнее.")

    over25 = result["totals"].get("over_2_5", 0)

    if over25 >= 70:
        lines.append("⚽ Модель ожидает результативную игру.")
    elif over25 <= 40:
        lines.append("⚽ Вероятнее осторожный матч с небольшим количеством голов.")

    if main_value >= 80:
        level = "очень высокая"
    elif main_value >= 70:
        level = "высокая"
    elif main_value >= 60:
        level = "средняя"
    else:
        level = "умеренная"

    lines.append("")
    lines.append(f"🎯 Главная рекомендация: {main_pick}.")
    lines.append(f"Вероятность оценивается как {level} ({main_value}%).")
    lines.append("")
    lines.append("💡 FLUX AI рекомендует рассматривать этот прогноз как основной вариант.")

    return "\n".join(lines)


def format_analysis(result):
    team1 = result["team1"]
    team2 = result["team2"]

    probabilities = result["probabilities"]
    totals = result["totals"]

    score = result.get("predicted_score", {}).get("score", "—")
    top_3 = result["best_pick"].get("top_3", [])
    top_3_text = format_top_3(result["best_pick"])

    confidence = result["confidence"]
    stars = confidence_stars(confidence)

    if top_3:
        main_pick = top_3[0][0]
        main_value = top_3[0][1]
    else:
        main_pick = result["best_pick"]["pick"]
        main_value = result["best_pick"]["value"]

    ai_comment = build_ai_comment(result, main_pick, main_value)

    return f"""
🏆 FLUX AI PRO

⚽ Матч
{team1} — {team2}

━━━━━━━━━━━━━━━━━━

⭐ Сила команд
{team1}: {result["team1_rating"]["rating"]}/100
{team2}: {result["team2_rating"]["rating"]}/100

📈 Форма
{team1}: {result["team1_rating"]["form"]}/100
{team2}: {result["team2_rating"]["form"]}/100

⚔️ Атака
{team1}: {result["team1_rating"]["attack"]}/100
{team2}: {result["team2_rating"]["attack"]}/100

🛡 Защита
{team1}: {result["team1_rating"]["defense"]}/100
{team2}: {result["team2_rating"]["defense"]}/100

━━━━━━━━━━━━━━━━━━

🎯 Исход
П1 — {probabilities["p1"]}%
X — {probabilities["draw"]}%
П2 — {probabilities["p2"]}%

━━━━━━━━━━━━━━━━━━

🏆 ТОП-3 рекомендации
{top_3_text}

━━━━━━━━━━━━━━━━━━

⚽ Голы
ТБ 1.5 — {totals.get("over_1_5", "—")}%
ТБ 2.5 — {totals.get("over_2_5", "—")}%
ТБ 3.5 — {totals.get("over_3_5", "—")}%

🥅 Обе забьют
Да — {totals["btts_yes"]}%
Нет — {totals["btts_no"]}%

🎱 Возможный счет
{score}

━━━━━━━━━━━━━━━━━━

⭐ Индекс уверенности
{stars}
{confidence}/10

⚠️ Риск
{result["risk"]}

📊 Качество данных
{result["data_quality"]}/100

━━━━━━━━━━━━━━━━━━

{ai_comment}

🏆 Основной прогноз:
👉 {main_pick}

🎯 Вероятность:
{main_value}%

━━━━━━━━━━━━━━━━━━

Источник:
{result["source"]}

━━━━━━━━━━━━━━━━━━

🏆 Ежедневные ТОП-3 прогнозы FLUX AI:
{CHANNEL_URL}

📢 Подпишись на канал, чтобы не пропускать лучшие прогнозы.

Важно:
Прогноз не является гарантией результата.
"""


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)
