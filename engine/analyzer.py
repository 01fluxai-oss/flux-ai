from providers.thesportsdb import get_match_data
from engine.v3_engine import analyze_v3


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
        "source": data.get("source", "TheSportsDB"),
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

🧠 Вердикт FLUX AI

📊 После анализа формы, атаки, защиты и статистической модели FLUX AI сделал следующий вывод.

🏆 Основной прогноз:
👉 {main_pick}

🎯 Вероятность:
{main_value}%

💬 Почему именно этот прогноз?

• Модель сравнила текущую форму обеих команд.
• Проанализировала эффективность атаки и защиты.
• Учла статистические вероятности исходов и голов.
• Выбрала вариант с максимальной вероятностью.

⚠️ Помните:
Даже самый высокий процент не гарантирует исход матча. Используйте прогноз как аналитический инструмент.

