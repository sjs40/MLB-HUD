"""
GET /game/{game_id}/pregame — full pre-game analysis for a scheduled game.

Orchestrates: lineup resolution → Statcast pulls → blending →
pitcher profile → batter matchups → narratives.
"""

from fastapi import APIRouter, HTTPException
import traceback

from ..data.mlb_api import get_probable_pitchers, get_lineup
from ..data.statcast import get_pitcher_statcast, get_batter_statcast
from ..data.data_blending import (
    blend_dataframes,
    build_blend_metadata,
    check_profile_change_alert,
)
from ..data.lineup_projection import project_lineup
from ..analysis.pitcher_profile import build_pitcher_profile, get_location_heatmap
from ..analysis.batter_matchup import build_batter_matchup
from ..analysis.narrative import generate_narratives

router = APIRouter(tags=["pregame"])


def _resolve_lineup(
    game_id: int,
    team_id: int,
    pitcher_hand: str,
    team_side: str,  # "home" or "away" — known from the schedule, no extra API call
) -> tuple[list[dict], bool]:
    """
    Return (lineup, is_projected).
    Uses official lineup if posted; falls back to projection if not.
    team_side must be passed by the caller (derived from schedule data).
    """
    lineup_data = get_lineup(game_id)
    if lineup_data:
        lineup = lineup_data.get(team_side, [])
        if lineup:
            return lineup, False

    # Fall back to projection
    projected = project_lineup(team_id, pitcher_hand)
    return projected, True


@router.get("/game/{game_id}/pregame")
def pregame(game_id: int):
    """
    Full pre-game analysis for a game.

    Returns:
    - home_pitcher: pitcher profile, blend metadata, profile alerts
    - away_pitcher: same
    - home_lineup: per-batter matchup analysis vs. away pitcher
    - away_lineup: per-batter matchup analysis vs. home pitcher
    - narratives: {home_pitcher: [...], away_pitcher: [...]}
    """
    try:
        probable = get_probable_pitchers(game_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch probable pitchers: {e}")

    result = {}

    for side in ("home", "away"):
        opp_side = "away" if side == "home" else "home"
        pitcher_info = probable.get(side, {})
        pitcher_id = pitcher_info.get("probable_pitcher_id")
        pitcher_name = pitcher_info.get("probable_pitcher_name", "TBD")
        pitcher_hand = pitcher_info.get("pitch_hand", "R")
        opp_team_id = probable.get(opp_side, {}).get("team_id")

        # ── Pitcher profile ───────────────────────────────────────────────────
        if pitcher_id:
            try:
                df_p_2025 = get_pitcher_statcast(pitcher_id, 2025)
                df_p_2026 = get_pitcher_statcast(pitcher_id, 2026)
            except Exception as e:
                result[f"{side}_pitcher"] = {"error": str(e), "pitcher_name": pitcher_name}
                continue

            n_2026 = len(df_p_2026)
            blend_meta = build_blend_metadata(df_p_2026, df_p_2025, n_2026, 0)
            blended_pitcher = blend_dataframes(df_p_2026, df_p_2025, n_2026, 0)
            profile_alerts = check_profile_change_alert(df_p_2026, df_p_2025)

            profile = build_pitcher_profile(blended_pitcher)
            profile["profile_change_alerts"] = profile_alerts

            # Compute location heatmaps for each pitch type vs. each hand
            heatmaps = {}
            pitch_types = [p["pitch_type"] for p in profile.get("pitch_mix", [])]
            for pt in pitch_types:
                heatmaps[pt] = {
                    "vs_LHH": get_location_heatmap(blended_pitcher, pt, "L"),
                    "vs_RHH": get_location_heatmap(blended_pitcher, pt, "R"),
                }
            profile["location_heatmaps"] = heatmaps

            result[f"{side}_pitcher"] = {
                "pitcher_id": pitcher_id,
                "pitcher_name": pitcher_name,
                "blend_meta": blend_meta,
                "profile_change_alerts": profile_alerts,
                "profile": profile,
            }
        else:
            result[f"{side}_pitcher"] = {
                "pitcher_id": None,
                "pitcher_name": "TBD",
                "blend_meta": None,
                "profile": None,
            }

        # ── Lineup matchup analysis ───────────────────────────────────────────
        if opp_team_id and pitcher_id:
            lineup, is_projected = _resolve_lineup(game_id, opp_team_id, pitcher_hand, opp_side)
            batter_matchups = []

            for batter in lineup:
                batter_id = batter.get("player_id")
                if not batter_id:
                    continue
                try:
                    df_b_2025 = get_batter_statcast(batter_id, 2025)
                    df_b_2026 = get_batter_statcast(batter_id, 2026)
                except Exception:
                    batter_matchups.append({
                        **batter,
                        "error": "Failed to fetch batter data",
                    })
                    continue

                n_pa_2026 = df_b_2026["at_bat_number"].nunique() if not df_b_2026.empty and "at_bat_number" in df_b_2026.columns else len(df_b_2026) // 4
                batter_blend_meta = build_blend_metadata(df_b_2026, df_b_2025, n_2026, n_pa_2026)
                blended_batter = blend_dataframes(df_b_2026, df_b_2025, n_2026, n_pa_2026)

                # Use all pitch types as pitcher's primary types for matchup
                pitcher_pts = [p["pitch_type"] for p in profile.get("pitch_mix", [])]
                # Use first pitch type's LHH heatmap as location reference (simplified)
                pitcher_locations = []
                if pitcher_pts and "location_heatmaps" in profile:
                    hand_key = "vs_LHH" if batter.get("bat_side") == "L" else "vs_RHH"
                    pitcher_locations = profile["location_heatmaps"].get(pitcher_pts[0], {}).get(hand_key, [])

                matchup = build_batter_matchup(
                    blended_batter, pitcher_pts, pitcher_locations, batter_blend_meta
                )
                batter_matchups.append({
                    **batter,
                    "blend_meta": batter_blend_meta,
                    "matchup": matchup,
                })

            result[f"{opp_side}_lineup"] = {
                "batters": batter_matchups,
                "is_projected": is_projected,
            }

    # ── Narratives ────────────────────────────────────────────────────────────
    narratives = {}
    for side in ("home", "away"):
        opp_side = "away" if side == "home" else "home"
        pitcher_data = result.get(f"{side}_pitcher", {})
        profile = pitcher_data.get("profile")
        blend_meta = pitcher_data.get("blend_meta")
        pitcher_name = pitcher_data.get("pitcher_name", "TBD")
        lineup_data = result.get(f"{opp_side}_lineup", {})
        lineup_matchups = lineup_data.get("batters", [])

        if profile:
            narratives[side] = generate_narratives(
                pitcher_name, profile, lineup_matchups, blend_meta
            )
        else:
            narratives[side] = []

    result["narratives"] = narratives
    return result
