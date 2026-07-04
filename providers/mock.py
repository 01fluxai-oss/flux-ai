def get_match_data(team1, team2):
    return {
        "source": "mock",
        "team1": team1,
        "team2": team2,
        "team1_form": {
            "matches": 10,
            "wins": 7,
            "draws": 2,
            "losses": 1,
            "goals_for": 23,
            "goals_against": 9,
        },
        "team2_form": {
            "matches": 10,
            "wins": 6,
            "draws": 2,
            "losses": 2,
            "goals_for": 20,
            "goals_against": 12,
        },
        "h2h": {
            "matches": 5,
            "team1_wins": 2,
            "draws": 2,
            "team2_wins": 1,
        }
    }
