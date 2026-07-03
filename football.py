from football_api import search_team, get_last_matches, get_h2h
from statistics import simplify_match, team_form_score, h2h_summary
from prediction import calculate_probabilities, calculate_totals, flux_index


def analyze_match(team1_name, team2_name):
    team1 = search_team(team1_name)
    team2 = search_team(team2_name)

    if not team1:
        return {"success": False, "error": f"Команда не найдена: {team1_name}"}

    if not team2:
        return {"success": False, "error": f"Команда не найдена: {team2_name}"}

    team1_matches = get_last_matches(team1["id"], 10)
    team2_matches = get_last_matches(team2["id"], 10)
    h2h_matches = get_h2h(team1["id"], team2["id"], 5)

    form1 = team_form_score(team1_matches, team1["name"])
    form2 = team_form_score(team2_matches, team2["name"])
    h2h = h2h_summary(h2h_matches, team1["name"], team2["name"])

    probabilities = calculate_probabilities(form1, form2, h2h)
    totals = calculate_totals(form1, form2)

    return {
        "success": True,
        "team1": team1,
        "team2": team2,
        "team1_form": form1,
        "team2_form": form2,
        "h2h": h2h,
        "probabilities": probabilities,
        "totals": totals,
        "flux_index": {
            team1["name"]: flux_index(form1, totals),
            team2["name"]: flux_index(form2, totals),
        },
        "team1_last_matches": [simplify_match(m) for m in team1_matches],
        "team2_last_matches": [simplify_match(m) for m in team2_matches],
        "head_to_head": [simplify_match(m) for m in h2h_matches],
    }
