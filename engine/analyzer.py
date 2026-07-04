from providers.mock import get_match_data
from flux_engine import calculate_match, format_analysis


def analyze_match_v2(team1, team2):
    data = get_match_data(team1, team2)

    team1_form = data["team1_form"]
    team2_form = data["team2_form"]
    h2h = data.get("h2h", {})

    result = calculate_match(
        team1=team1,
        team2=team2,
        team1_form=team1_form,
        team2_form=team2_form,
        h2h=h2h,
    )

    return format_analysis(result, team1_form, team2_form)
