def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, round(value, 1)))


def calculate_attack_index(form):
    matches = max(form.get("matches", 1), 1)
    goals_for = form.get("goals_for", 0)
    avg_goals_for = goals_for / matches

    return clamp(avg_goals_for * 35)


def calculate_defense_index(form):
    matches = max(form.get("matches", 1), 1)
    goals_against = form.get("goals_against", 0)
    avg_goals_against = goals_against / matches

    return clamp(100 - avg_goals_against * 30)


def calculate_momentum_index(form):
    matches = max(form.get("matches", 1), 1)
    points = form.get("points", 0)
    wins = form.get("wins", 0)

    points_rate = points / (matches * 3)
    win_rate = wins / matches

    return clamp((points_rate * 60) + (win_rate * 40))


def calculate_stability_index(form):
    matches = max(form.get("matches", 1), 1)
    losses = form.get("losses", 0)

    loss_rate = losses / matches
    return clamp(100 - loss_rate * 100)


def calculate_flux_power(form, home_advantage=False):
    attack = calculate_attack_index(form)
    defense = calculate_defense_index(form)
    momentum = calculate_momentum_index(form)
    stability = calculate_stability_index(form)
    home_bonus = 8 if home_advantage else 0

    rating = (
        attack * 0.25
        + defense * 0.25
        + momentum * 0.30
        + stability * 0.15
        + home_bonus
    )

    return {
        "attack": attack,
        "defense": defense,
        "momentum": momentum,
        "stability": stability,
        "power": clamp(rating),
    }
