def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def calculate_team_power(form):
    matches = max(form.get("matches", 1), 1)
    points = form.get("points", 0)
    wins = form.get("wins", 0)
    goals_for = form.get("goals_for", 0)
    goals_against = form.get("goals_against", 0)

    points_score = (points / (matches * 3)) * 40
    win_score = (wins / matches) * 25
    attack_score = min(goals_for / matches, 3) * 8
    defense_score = max(0, 20 - (goals_against / matches) * 8)

    return clamp(points_score + win_score + attack_score + defense_score, 1, 100)


def calculate_match(team1, team2, team1_form, team2_form, h2h=None):
    h2h = h2h or {}

    team1_power = calculate_team_power(team1_form)
    team2_power = calculate_team_power(team2_form)

    total_power = max(team1_power + team2_power, 1)

    raw_p1 = team1_power / total_power
    raw_p2 = team2_power / total_power

    diff = abs(team1_power - team2_power)
    draw = clamp(30 - diff * 0.18, 18, 34)

    p1 = round(raw_p1 * (100 - draw))
    p2 = 100 - draw - p1

    avg_goals = (
        team1_form.get("avg_goals_for", 0)
        + team2_form.get("avg_goals_for", 0)
        + team1_form.get("avg_goals_against", 0)
        + team2_form.get("avg_goals_against", 0)
    ) / 2

    over_25 = clamp(avg_goals * 24, 25, 80)
    under_25 = 100 - over_25

    btts_yes = clamp(avg_goals * 22, 25, 80)
    btts_no = 100 - btts_yes

    confidence = clamp(5 + diff / 18, 1, 10)
    flux_score = clamp((team1_power + team2_power) / 2 + diff * 0.25, 1, 100)

    if p1 >= p2 and p1 >= draw:
        best_pick = f"П1 — {team1}"
    elif p2 >= p1 and p2 >= draw:
        best_pick = f"П2 — {team2}"
    else:
        best_pick = "X — ничья"

    if over_25 >= 60:
        goals_pick = "Тотал больше 2.5"
    elif under_25 >= 60:
        goals_pick = "Тотал меньше 2.5"
    else:
        goals_pick = "Тотал лучше пропустить"

    if confidence >= 8:
        risk = "Низкий"
    elif confidence >= 6:
        risk = "Средний"
    else:
        risk = "Высокий"

    return {
        "team1": team1,
        "team2": team2,
        "team1_power": team1_power,
        "team2_power": team2_power,
        "flux_score": flux_score,
        "probabilities": {
            "p1": p1,
            "draw": draw,
            "p2": p2,
        },
        "totals": {
            "over_2_5": over_25,
            "under_2_5": under_25,
            "btts_yes": btts_yes,
            "btts_no": btts_no,
        },
        "best_pick": best_pick,
        "goals_pick": goals_pick,
        "risk": risk,
        "confidence": confidence,
        "h2h": h2h,
    }


def format_analysis(result, team1_form, team2_form):
    team1 = result["team1"]
    team2 = result["team2"]

    return f"""
⚽ FLUX AI Sports Analysis

Матч:
{team1} — {team2}

📊 FLUX Score:
{result["flux_score"]}/100

📈 FLUX Index:
{team1}: {result["team1_power"]}/100
{team2}: {result["team2_power"]}/100

🎯 Вероятности FLUX:
П1 — {result["probabilities"]["p1"]}%
X — {result["probabilities"]["draw"]}%
П2 — {result["probabilities"]["p2"]}%

⚽ Тотал 2.5:
Больше — {result["totals"]["over_2_5"]}%
Меньше — {result["totals"]["under_2_5"]}%

🥅 Обе забьют:
Да — {result["totals"]["btts_yes"]}%
Нет — {result["totals"]["btts_no"]}%

📌 Форма команд:
{team1}: {team1_form.get("wins", 0)} побед, {team1_form.get("draws", 0)} ничьих, {team1_form.get("losses", 0)} поражений
Голы: {team1_form.get("goals_for", 0)} забито / {team1_form.get("goals_against", 0)} пропущено

{team2}: {team2_form.get("wins", 0)} побед, {team2_form.get("draws", 0)} ничьих, {team2_form.get("losses", 0)} поражений
Голы: {team2_form.get("goals_for", 0)} забито / {team2_form.get("goals_against", 0)} пропущено

🔥 Лучший вариант:
{result["best_pick"]}

⚽ Голы:
{result["goals_pick"]}

⚠️ Риск:
{result["risk"]}

🎯 Уверенность:
{result["confidence"]}/10

Вывод:
FLUX AI оценивает матч на основе формы, результативности, защиты и баланса сил команд. Прогноз не является гарантией результата.
"""
