def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, round(value, 1)))


def calculate_attack_index(form):
    matches = max(form.get("matches", 1), 1)
    avg_goals_for = form.get("avg_goals_for", form.get("goals_for", 0) / matches)

    return clamp(35 + avg_goals_for * 22, 25, 95)


def calculate_defense_index(form):
    matches = max(form.get("matches", 1), 1)
    avg_goals_against = form.get(
        "avg_goals_against",
        form.get("goals_against", 0) / matches,
    )

    return clamp(90 - avg_goals_against * 24, 20, 95)


def calculate_momentum_index(form):
    matches = max(form.get("matches", 1), 1)
    points = form.get("points", 0)
    wins = form.get("wins", 0)
    losses = form.get("losses", 0)

    points_rate = points / (matches * 3)
    win_rate = wins / matches
    loss_rate = losses / matches

    return clamp((points_rate * 55) + (win_rate * 35) + ((1 - loss_rate) * 10), 20, 95)


def calculate_stability_index(form):
    matches = max(form.get("matches", 1), 1)
    draws = form.get("draws", 0)
    losses = form.get("losses", 0)

    instability = ((draws * 0.5) + losses) / matches
    return clamp(90 - instability * 45, 25, 95)


def calculate_flux_power(form, home_advantage=False):
    attack = calculate_attack_index(form)
    defense = calculate_defense_index(form)
    momentum = calculate_momentum_index(form)
    stability = calculate_stability_index(form)
    home_bonus = 4 if home_advantage else 0

    rating = (
        attack * 0.28
        + defense * 0.27
        + momentum * 0.30
        + stability * 0.15
        + home_bonus
    )

    return {
        "attack": attack,
        "defense": defense,
        "momentum": momentum,
        "stability": stability,
        "power": clamp(rating, 20, 95),
    }
