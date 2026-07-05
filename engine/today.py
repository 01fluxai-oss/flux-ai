from engine.analyzer import analyze_match_v2


TODAY_MATCHES = [
    ("Liverpool", "Arsenal"),
    ("Inter", "Milan"),
    ("Barcelona", "Bayern"),
    ("Man City", "Real Madrid"),
    ("PSG", "Bayern"),
]


def get_pick_score(result):
    best_pick = result["best_pick"]
    value = best_pick.get("value", 0)
    confidence = result.get("confidence", 0)
    data_quality = result.get("data_quality", 0)

    return value + confidence * 2 + data_quality * 0.1


def format_today_item(index, result):
    medals = ["🥇", "🥈", "🥉"]
    medal = medals[index]

    team1 = result["team1"]
    team2 = result["team2"]

    best_pick = result["best_pick"]
    pick = best_pick["pick"]
    value = best_pick["value"]

    confidence = result["confidence"]
    risk = result["risk"]

    return (
        f"{medal} {team1} — {team2}\n"
        f"🔥 Прогноз: {pick} — {value}%\n"
        f"🎯 Уверенность: {confidence}/10\n"
        f"⚠️ Риск: {risk}"
    )


def today_top_3():
    results = []

    for team1, team2 in TODAY_MATCHES:
        try:
            result = analyze_match_v2(team1, team2)
            results.append(result)
        except Exception as e:
            print("TODAY_ANALYSIS_ERROR:", team1, team2, e, flush=True)

    if not results:
        return (
            "⚠️ Сегодня не удалось получить прогнозы.\n\n"
            "Попробуй отправить матч вручную:\n"
            "Real Madrid — PSG"
        )

    results = sorted(results, key=get_pick_score, reverse=True)[:3]

    items = []

    for index, result in enumerate(results):
        items.append(format_today_item(index, result))

    return (
        "🏆 FLUX AI DAILY\n\n"
        "ТОП-3 прогнозов на сегодня\n\n"
        + "\n\n".join(items)
        + "\n\nВажно: прогноз не является гарантией результата."
    )
