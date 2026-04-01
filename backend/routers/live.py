"""
GET /game/{game_id}/live — live game state with deviation flags vs. blended norms.
"""

from datetime import date
from fastapi import APIRouter, HTTPException

from ..data.mlb_api import get_live_feed, get_probable_pitchers
from ..data.statcast import get_pitcher_statcast
from ..data.data_blending import blend_dataframes, build_blend_metadata
from ..analysis.pitcher_profile import get_pitch_mix

router = APIRouter(tags=["live"])

# Thresholds for deviation flags
PITCH_MIX_DEVIATION_THRESHOLD = 10.0  # percentage points
VELO_DEVIATION_THRESHOLD = 1.5         # mph


def _extract_live_pitches(live_feed: dict, pitcher_id: int) -> list[dict]:
    """
    Extract pitch-level data from the live feed for a specific pitcher.
    Returns list of {pitch_type, release_speed, inning, description}.
    """
    pitches = []
    plays = (
        live_feed.get("liveData", {})
        .get("plays", {})
        .get("allPlays", [])
    )
    for play in plays:
        events = play.get("playEvents", [])
        for event in events:
            if event.get("type") != "pitch":
                continue
            pitcher = (
                play.get("matchup", {}).get("pitcher", {}).get("id")
            )
            if pitcher != pitcher_id:
                continue
            details = event.get("pitchData", {})
            pitch_type = event.get("details", {}).get("type", {}).get("code")
            inning = play.get("about", {}).get("inning")
            pitches.append({
                "pitch_type": pitch_type,
                "release_speed": details.get("startSpeed"),
                "inning": inning,
                "description": event.get("details", {}).get("description", ""),
            })
    return pitches


def _compute_deviations(live_pitches: list[dict], norm_mix: list[dict]) -> list[dict]:
    """
    Compare tonight's pitch mix against blended season norms.
    Returns list of deviation flags for pitches deviating >10pp.
    """
    if not live_pitches:
        return []

    total = len(live_pitches)
    live_counts: dict[str, int] = {}
    for p in live_pitches:
        pt = p.get("pitch_type") or "UN"
        live_counts[pt] = live_counts.get(pt, 0) + 1

    norm_dict = {n["pitch_type"]: n["pct"] for n in norm_mix}

    flags = []
    for pt, count in live_counts.items():
        live_pct = (count / total) * 100
        norm_pct = norm_dict.get(pt, 0.0)
        delta = live_pct - norm_pct
        if abs(delta) >= PITCH_MIX_DEVIATION_THRESHOLD:
            flags.append({
                "pitch_type": pt,
                "live_pct": round(live_pct, 1),
                "norm_pct": round(norm_pct, 1),
                "delta": round(delta, 1),
                "direction": "up" if delta > 0 else "down",
            })

    return sorted(flags, key=lambda x: abs(x["delta"]), reverse=True)


def _compute_velo_deviation(live_pitches: list[dict], norm_mix: list[dict]) -> dict | None:
    """
    Compare tonight's average fastball velocity against blended norm.
    Returns a flag if deviation exceeds threshold.
    """
    fb_types = {"FF", "SI", "FC"}
    live_velos = [
        p["release_speed"] for p in live_pitches
        if p.get("pitch_type") in fb_types and p.get("release_speed") is not None
    ]
    if not live_velos:
        return None

    live_avg = sum(live_velos) / len(live_velos)

    norm_fb = next(
        (n for n in norm_mix if n["pitch_type"] in fb_types and n.get("avg_velo")), None
    )
    if not norm_fb:
        return None

    norm_velo = norm_fb["avg_velo"]
    delta = live_avg - norm_velo

    if abs(delta) >= VELO_DEVIATION_THRESHOLD:
        return {
            "live_avg_velo": round(live_avg, 1),
            "norm_avg_velo": round(norm_velo, 1),
            "delta": round(delta, 1),
            "direction": "up" if delta > 0 else "down",
            "pitch_count": len(live_velos),
        }
    return None


@router.get("/game/{game_id}/live")
def live_game(game_id: int):
    """
    Live game state with deviation flags against blended season norms.

    Returns:
    - game_status: current inning, outs, score, etc.
    - current_pitcher: who's pitching
    - pitch_mix_deviations: list of pitch types deviating >10pp from norm
    - velo_deviation: fastball velocity deviation if >1.5 mph
    - live_pitch_counts: tonight's pitch type breakdown
    - inning_progression: per-inning velo trend tonight
    """
    import requests as _requests

    try:
        feed = get_live_feed(game_id)
    except _requests.HTTPError as e:
        # MLB API returns 4xx/5xx for games that aren't live yet or have no feed.
        # Return a friendly "not live" payload rather than crashing.
        status_code = e.response.status_code if e.response is not None else 0
        return {
            "game_id": game_id,
            "status": "Preview",
            "detailed_status": f"Live feed unavailable (MLB API returned {status_code}). "
                               f"Game may not have started yet.",
            "inning": None,
            "inning_half": None,
            "outs": None,
            "home_score": None,
            "away_score": None,
            "current_pitcher_id": None,
            "current_pitcher_name": None,
            "total_pitches_tonight": 0,
            "live_pitch_mix": [],
            "norm_pitch_mix": [],
            "pitch_mix_deviations": [],
            "velo_deviation": None,
            "inning_progression": [],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch live feed: {e}")

    game_data = feed.get("gameData", {})
    live_data = feed.get("liveData", {})
    status = game_data.get("status", {})
    linescore = live_data.get("linescore", {})

    # Current pitcher on the mound
    current_pitcher = (
        linescore.get("offense", {}).get("pitcher")
        or live_data.get("plays", {}).get("currentPlay", {})
        .get("matchup", {}).get("pitcher", {})
    )
    current_pitcher_id = current_pitcher.get("id") if isinstance(current_pitcher, dict) else None
    current_pitcher_name = current_pitcher.get("fullName") if isinstance(current_pitcher, dict) else "Unknown"

    # Extract tonight's pitches for the current pitcher
    live_pitches = []
    norm_mix = []
    pitch_mix_deviations = []
    velo_deviation = None

    if current_pitcher_id:
        live_pitches = _extract_live_pitches(feed, current_pitcher_id)

        try:
            df_2025 = get_pitcher_statcast(current_pitcher_id, 2025)
            df_2026 = get_pitcher_statcast(current_pitcher_id, 2026)
            n_2026 = len(df_2026)
            blended = blend_dataframes(df_2026, df_2025, n_2026, 0)
            norm_mix = get_pitch_mix(blended)
            pitch_mix_deviations = _compute_deviations(live_pitches, norm_mix)
            velo_deviation = _compute_velo_deviation(live_pitches, norm_mix)
        except Exception:
            pass  # Non-fatal — show live data without deviation context

    # Tonight's pitch type breakdown
    live_counts: dict[str, int] = {}
    for p in live_pitches:
        pt = p.get("pitch_type") or "UN"
        live_counts[pt] = live_counts.get(pt, 0) + 1
    total_pitches = len(live_pitches)
    live_pitch_mix = [
        {"pitch_type": pt, "count": count, "pct": round(count / total_pitches * 100, 1)}
        for pt, count in sorted(live_counts.items(), key=lambda x: x[1], reverse=True)
    ] if total_pitches > 0 else []

    # Per-inning velo trend tonight
    inning_velos: dict[int, list[float]] = {}
    for p in live_pitches:
        inning = p.get("inning")
        velo = p.get("release_speed")
        if inning and velo:
            inning_velos.setdefault(inning, []).append(velo)
    inning_progression = [
        {"inning": inn, "avg_velo": round(sum(velos) / len(velos), 1), "pitch_count": len(velos)}
        for inn, velos in sorted(inning_velos.items())
    ]

    return {
        "game_id": game_id,
        "status": status.get("abstractGameState"),
        "detailed_status": status.get("detailedState"),
        "inning": linescore.get("currentInning"),
        "inning_half": linescore.get("inningHalf"),
        "outs": linescore.get("outs"),
        "home_score": linescore.get("teams", {}).get("home", {}).get("runs"),
        "away_score": linescore.get("teams", {}).get("away", {}).get("runs"),
        "current_pitcher_id": current_pitcher_id,
        "current_pitcher_name": current_pitcher_name,
        "total_pitches_tonight": total_pitches,
        "live_pitch_mix": live_pitch_mix,
        "norm_pitch_mix": norm_mix,
        "pitch_mix_deviations": pitch_mix_deviations,
        "velo_deviation": velo_deviation,
        "inning_progression": inning_progression,
    }
