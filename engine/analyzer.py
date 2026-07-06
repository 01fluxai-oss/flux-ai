from providers.thesportsdb import get_match_data
from engine.v3_engine import analyze_v3

CHANNEL_URL = "https://t.me/FluxAIDaily"


def bar(value):
    value = max(0, min(100, int(value)))
    blocks = round(value / 10)
    return "█" * blocks + "░" * (10 - blocks)


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


def format_top_3(best_pick):
    top_3 = best_pick.get("top_3", [])

    if not top_3:
        return f"🥇 {best_pick.get('pick', '—')} — {best_pick.get('value', '—')}%"

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for index, item in enumerate(top_3[:3]):
        name, value = item
        lines.append(f"{medals[index]} {name} — {value}% {strength_icon(value)}")

    return "\n".join(lines)


def build_ai_comment(result, main_pick, main_value):
    team1 = result["team1"]
    team2 = result["team2"]

    r1 = result["team1_rating"]
    r2 = result["team2_rating"]

    form1 = r1["form"]
    form2 = r2["form"]
    attack1 = r1["attack"]
    attack2 = r2["attack"]
    defense1 = r1["defense"]
    defense2 = r2["defense"]

    totals = result["totals"]
    over25 = totals["over_2_5"]
    btts = totals["btts_yes"]

    lines = []
    lines.append("🧠 FLUX AI Coach")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("📈 Последняя форма")
    lines.append("")
    lines.append(f"{team1}: {form_bar(form1)}")
    lines.append(f"{team2}: {form_bar(form2)}")
    lines.append("")
    lines.append("📊 Общая форма")

    if form1 > form2 + 5:
        lines.append(f"✅ {team1} находится в лучшей форме.")
    elif form2 > form1 + 5:
        lines.append(f"✅ {team2} находится в лучшей форме.")
    else:
        lines.append("⚖️ Команды находятся примерно в одинаковой форме.")

    lines.append("")
    lines.append("⚔️ Атака")

    if attack1 > attack2 + 5:
        lines.append(f"🔥 Атака {team1} выглядит опаснее.")
    elif attack2 > attack1 + 5:
        lines.append(f"🔥 Атака {team2} выглядит опаснее.")
    else:
        lines.append("⚖️ Атакующий потенциал примерно одинаковый.")

    lines.append("")
    lines.append("🛡 Защита")

    if defense1 > defense2 + 5:
        lines.append(f"🧱 Защита {team1} выглядит надежнее.")
    elif defense2 > defense1 + 5:
        lines.append(f"🧱 Защита {team2} выглядит надежнее.")
    else:
        lines.append("⚖️ Защита команд примерно одинаковая.")

    lines.append("")

    if over25 >= 70:
        lines.append("⚽ Модель ожидает большое количество голов.")
    elif over25 <= 40:
        lines.append("⚽ Ожидается осторожный матч.")
    else:
        lines.append("⚽ Возможен открытый футбол.")

    if btts >= 65:
        lines.append("🥅 Высока вероятность обмена голами.")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("⭐ Главная рекомендация")
    lines.append(f"👉 {main_pick}")
    lines.append(f"🎯 Вероятность: {main_value}%")

    return "\n".join(lines)


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


def format_analysis(result):
    team1 = result["team1"]
    team2 = result["team2"]

    probabilities = result["probabilities"]
    totals = result["totals"]
    double_chance = result.get("double_chance", {})

    score = result.get("predicted_score", {}).get("score", "—")
    top_3 = result["best_pick"].get("top_3", [])
    top_3_text = format_top_3(result["best_pick"])

    confidence = int(result["confidence"])
    if confidence <= 10:
        confidence = confidence * 10

    if top_3:
        main_pick = top_3[0][0]
        main_value = top_3[0][1]
    else:
        main_pick = result["best_pick"]["pick"]
        main_value = result["best_pick"]["value"]

    ai_comment = build_ai_comment(result, main_pick, main_value)

    team1_rating = result["team1_rating"]["rating"]
    team2_rating = result["team2_rating"]["rating"]

    power_diff = team1_rating - team2_rating

    if power_diff > 0:
        power_text = f"{team1} +{power_diff}"
    elif power_diff < 0:
        power_text = f"{team2} +{abs(power_diff)}"
    else:
        power_text = "Равный баланс"

    return f"""
🏆 FLUX AI PRO
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

⭐ Главный прогноз
👉 {main_pick}

🎯 Вероятность:
{main_value}%

🧠 AI Confidence:
{bar(confidence)} {confidence}%

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
{result["risk"]}

━━━━━━━━━━━━━━━━━━━━

{ai_comment}

━━━━━━━━━━━━━━━━━━━━

📢 Ежедневные ТОП-3 прогнозы:
{CHANNEL_URL}

Важно:
Прогноз не является гарантией результата.
"""


def build_message_text(result):
    return format_analysis(result)


def analyze_and_format(team1, team2):
    result = analyze_match_v2(team1, team2)
    return format_analysis(result)


__all__ = [
    "analyze_match_v2",
    "format_analysis",
    "build_message_text",
    "analyze_and_format",
]
