"""
Lineup projection — used when the official lineup hasn't been posted yet.
Derives a projected batting order from the last 10 games of lineup history.
"""

from collections import Counter
from .mlb_api import get_team_lineup_history


def project_lineup(team_id: int, handedness_of_sp: str = None) -> list[dict]:
    """
    Project a batting order for a team based on recent lineup history.

    Args:
        team_id: MLB team ID
        handedness_of_sp: 'L' or 'R' — opposing starting pitcher's hand.
                          Not used in v1 projection logic (roster splits are
                          too complex without full roster data), but accepted
                          for forward-compatibility.

    Returns:
        List of player dicts with projected=True flag, sorted by most common
        batting slot. Up to 9 players.
    """
    history = get_team_lineup_history(team_id, num_games=10)

    if not history:
        return []

    # Tally each player's appearances at each batting slot
    # slot_votes[player_id][slot] = count
    slot_votes: dict[int, Counter] = {}
    player_info: dict[int, dict] = {}

    for game in history:
        for batter in game.get("lineup", []):
            pid = batter.get("player_id")
            slot = batter.get("batting_order")
            if pid is None or slot is None:
                continue
            if pid not in slot_votes:
                slot_votes[pid] = Counter()
                player_info[pid] = {
                    "player_id": pid,
                    "name": batter.get("name"),
                    "position": batter.get("position"),
                    "bat_side": batter.get("bat_side"),
                }
            slot_votes[pid][slot] += 1

    # Assign each player to their most common slot, then fill slots 1–9
    # greedily by most frequent appearance count
    player_scores = []
    for pid, counter in slot_votes.items():
        most_common_slot, appearances = counter.most_common(1)[0]
        player_scores.append((pid, most_common_slot, appearances))

    # Sort by slot first, then break ties by appearance frequency (desc)
    player_scores.sort(key=lambda x: (x[1], -x[2]))

    # Deduplicate slots — take the most-appeared player per slot
    slot_assignments: dict[int, tuple] = {}
    for pid, slot, appearances in player_scores:
        if slot not in slot_assignments:
            slot_assignments[slot] = (pid, appearances)
        else:
            existing_appearances = slot_assignments[slot][1]
            if appearances > existing_appearances:
                slot_assignments[slot] = (pid, appearances)

    # Build projected lineup for slots 1–9
    projected = []
    for slot in range(1, 10):
        entry = slot_assignments.get(slot)
        if entry:
            pid = entry[0]
            info = player_info[pid].copy()
            info["batting_order"] = slot
            info["projected"] = True
            projected.append(info)

    return projected
