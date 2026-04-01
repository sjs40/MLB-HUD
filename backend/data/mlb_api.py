"""
MLB Stats API client — free, no API key required.
Base URL: https://statsapi.mlb.com/api/v1
"""

import requests
from datetime import date, timedelta
from typing import Optional

BASE_URL = "https://statsapi.mlb.com/api/v1"


def _get(path: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_schedule(query_date: Optional[str] = None) -> list[dict]:
    """
    Return games for the given date (YYYY-MM-DD).
    If no date is provided, returns today's games.
    """
    if query_date is None:
        query_date = date.today().isoformat()

    data = _get("/schedule", params={
        "sportId": 1,
        "date": query_date,
        "hydrate": "probablePitcher,team",
    })

    games = []
    for game_date in data.get("dates", []):
        for game in game_date.get("games", []):
            teams = game.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})

            home_pitcher = home.get("probablePitcher") or {}
            away_pitcher = away.get("probablePitcher") or {}

            games.append({
                "game_id": game["gamePk"],
                "game_date": game_date["date"],
                "game_time": game.get("gameDate"),
                "status": game.get("status", {}).get("abstractGameState", "Preview"),
                "home_team_id": home.get("team", {}).get("id"),
                "home_team": home.get("team", {}).get("name", "Unknown"),
                "away_team_id": away.get("team", {}).get("id"),
                "away_team": away.get("team", {}).get("name", "Unknown"),
                "home_probable_pitcher_id": home_pitcher.get("id"),
                "home_probable_pitcher": home_pitcher.get("fullName"),
                "away_probable_pitcher_id": away_pitcher.get("id"),
                "away_probable_pitcher": away_pitcher.get("fullName"),
            })
    return games


def get_schedule_two_days() -> list[dict]:
    """Return today's and tomorrow's games combined."""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    return get_schedule(today) + get_schedule(tomorrow)


def get_probable_pitchers(game_id: int) -> dict:
    """Return home/away probable pitcher IDs and names for a game."""
    data = _get(f"/game/{game_id}/boxscore")
    teams = data.get("teams", {})

    result = {}
    for side in ("home", "away"):
        team_data = teams.get(side, {})
        team_info = team_data.get("team", {})
        # probablePitcher may be in the game feed instead
        result[side] = {
            "team_id": team_info.get("id"),
            "team_name": team_info.get("name"),
        }

    # Also pull from schedule for probable pitchers
    schedule_data = _get("/schedule", params={
        "sportId": 1,
        "gamePk": game_id,
        "hydrate": "probablePitcher",
    })
    for game_date in schedule_data.get("dates", []):
        for game in game_date.get("games", []):
            for side in ("home", "away"):
                pitcher = game.get("teams", {}).get(side, {}).get("probablePitcher") or {}
                result[side]["probable_pitcher_id"] = pitcher.get("id")
                result[side]["probable_pitcher_name"] = pitcher.get("fullName")

    return result


def get_live_feed(game_id: int) -> dict:
    """Return raw live game feed data.
    Note: live feed requires the v1.1 endpoint, not v1.
    """
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
    import requests as _req
    resp = _req.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_lineup(game_id: int) -> Optional[dict]:
    """
    Return official lineup if posted, else None.
    Returns dict with keys 'home' and 'away', each a list of batter dicts.
    """
    data = _get(f"/game/{game_id}/boxscore")
    teams = data.get("teams", {})

    result = {}
    lineup_found = False
    for side in ("home", "away"):
        team_data = teams.get(side, {})
        batters = team_data.get("batters", [])
        players = team_data.get("players", {})

        if batters:
            lineup_found = True
            lineup = []
            for player_id in batters:
                key = f"ID{player_id}"
                player = players.get(key, {})
                person = player.get("person", {})
                batting_order = player.get("battingOrder")
                lineup.append({
                    "player_id": person.get("id"),
                    "name": person.get("fullName"),
                    "batting_order": int(batting_order) // 100 if batting_order else None,
                    "position": player.get("position", {}).get("abbreviation"),
                    "bat_side": player.get("person", {}).get("batSide", {}).get("code"),
                    "projected": False,
                })
            result[side] = sorted(lineup, key=lambda x: x["batting_order"] or 99)
        else:
            result[side] = []

    return result if lineup_found else None


def get_team_lineup_history(team_id: int, num_games: int = 10) -> list[dict]:
    """
    Return batting order history for the last N completed games for a team.
    Used for lineup projection when the official lineup isn't posted yet.
    """
    # Get recent schedule for the team
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=30)).isoformat()

    data = _get("/schedule", params={
        "sportId": 1,
        "teamId": team_id,
        "startDate": start_date,
        "endDate": end_date,
        "hydrate": "linescore",
    })

    # Extract game_id AND which side this team is directly from the schedule
    # response — no secondary API call needed.
    completed_games: list[tuple[int, str]] = []  # (game_id, "home"|"away")
    for game_date in reversed(data.get("dates", [])):
        for game in game_date.get("games", []):
            if game.get("status", {}).get("abstractGameState") == "Final":
                home_team_id = (
                    game.get("teams", {}).get("home", {}).get("team", {}).get("id")
                )
                side = "home" if home_team_id == team_id else "away"
                completed_games.append((game["gamePk"], side))
            if len(completed_games) >= num_games:
                break
        if len(completed_games) >= num_games:
            break

    history = []
    for game_id, side in completed_games:
        try:
            lineup = get_lineup(game_id)
            if lineup:
                history.append({
                    "game_id": game_id,
                    "lineup": lineup.get(side, []),
                })
        except Exception:
            continue

    return history



def search_players(name: str) -> list[dict]:
    """
    Search for players by name. Returns list of matching players with id, name,
    position, and active status. Used for ad hoc analyzer.

    Strategy:
    1. Try /people/search?names=<query> (MLB suggest endpoint)
    2. Fall back to /sports/1/players?season=2026 + client-side filter
    """
    def _normalize(players_raw: list) -> list[dict]:
        results = []
        for player in players_raw:
            results.append({
                "player_id": player.get("id"),
                "name": player.get("fullName"),
                "position": player.get("primaryPosition", {}).get("abbreviation"),
                "bat_side": player.get("batSide", {}).get("code"),
                "pitch_hand": player.get("pitchHand", {}).get("code"),
                "active": player.get("active", True),
                "team": player.get("currentTeam", {}).get("name"),
            })
        return results

    # Attempt 1: /people/search (name suggest endpoint)
    try:
        data = _get("/people/search", params={"names": name, "sportId": 1})
        people = data.get("people", [])
        if people:
            return _normalize(people)
    except Exception:
        pass

    # Attempt 2: fetch all active players for the season, filter client-side
    try:
        data = _get("/sports/1/players", params={"season": 2026, "active": "true"})
        name_lower = name.lower()
        matched = [
            p for p in data.get("people", [])
            if name_lower in (p.get("fullName") or "").lower()
        ]
        return _normalize(matched[:20])  # cap at 20 results
    except Exception:
        pass

    return []
