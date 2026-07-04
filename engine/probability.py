def clamp(value, minimum=1, maximum=99):
    return max(minimum, min(maximum, round(value)))


def calculate_match_probabilities(team1_power, team2_power):
    p1_power = team1_power.get("power", 50)
    p2_power = team2_power.get("power", 50)

    diff = abs(p1_power - p2_power)

    draw = clamp(31 - diff * 0.25, 18, 34)

    available = 100 - draw
    total_power = max(p1_power + p2_power, 1)

    p1 = round((p1_power / total_power) * available)
    p2 = 100 - draw - p1

    return {
        "p1": clamp(p1, 5, 85),
        "draw": clamp(draw, 10, 40),
        "p2": clamp(p2, 5, 85),
        "difference": round(diff, 1),
    }
