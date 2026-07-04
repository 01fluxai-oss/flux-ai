from providers.mock import get_match_data
from engine.flux_score import calculate_flux_score
from engine.prediction import calculate_probabilities, calculate_totals


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]
    h2h = data["h2h"]

    flux_score = calculate_flux_score(team1_form, team2_form, h2h)
    probabilities = calculate_probabilities(flux_score)
    totals = calculate_totals(team1_form, team2_form)

    return {
        "team1": team1,
        "team2": team2,
        "source": data["source"],
        "team1_form": team1_form,
        "team2_form": team2_form,
        "h2h": h2h,
        "flux_score": flux_score,
        "probabilities": probabilities,
        "totals": totals,
    }
