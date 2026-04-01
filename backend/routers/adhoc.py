"""
GET /adhoc — ad hoc pitcher vs. batter matchup analysis.

Same analysis pipeline as pregame but for any arbitrary pitcher/batter pair,
not tied to a specific scheduled game.
"""

from fastapi import APIRouter, HTTPException, Query

from ..data.statcast import get_pitcher_statcast, get_batter_statcast
from ..data.data_blending import (
    blend_dataframes,
    build_blend_metadata,
    check_profile_change_alert,
)
from ..analysis.pitcher_profile import build_pitcher_profile, get_location_heatmap
from ..analysis.batter_matchup import build_batter_matchup
from ..analysis.narrative import generate_narratives

router = APIRouter(tags=["adhoc"])


@router.get("/adhoc")
def adhoc(
    pitcher_id: int = Query(..., description="MLB player ID for the pitcher"),
    batter_id: int = Query(..., description="MLB player ID for the batter"),
    pitcher_name: str = Query("Pitcher", description="Display name for the pitcher"),
    batter_name: str = Query("Batter", description="Display name for the batter"),
    batter_hand: str = Query("R", description="Batter's handedness: L or R"),
):
    """
    Full matchup analysis for any pitcher vs. any batter.

    Uses the same 2025/2026 blending logic as the pre-game endpoint.
    Useful for: reliever analysis, non-today matchups, prop research.
    """
    # ── Pitcher data ──────────────────────────────────────────────────────────
    try:
        df_p_2025 = get_pitcher_statcast(pitcher_id, 2025)
        df_p_2026 = get_pitcher_statcast(pitcher_id, 2026)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch pitcher Statcast: {e}")

    n_p_2026 = len(df_p_2026)
    pitcher_blend_meta = build_blend_metadata(df_p_2026, df_p_2025, n_p_2026, 0)
    blended_pitcher = blend_dataframes(df_p_2026, df_p_2025, n_p_2026, 0)
    profile_alerts = check_profile_change_alert(df_p_2026, df_p_2025)

    profile = build_pitcher_profile(blended_pitcher)
    profile["profile_change_alerts"] = profile_alerts

    # Heatmaps for the batter's handedness
    pitcher_pts = [p["pitch_type"] for p in profile.get("pitch_mix", [])]
    hand_key = "vs_LHH" if batter_hand == "L" else "vs_RHH"
    heatmaps = {}
    for pt in pitcher_pts:
        heatmaps[pt] = get_location_heatmap(blended_pitcher, pt, batter_hand)
    profile["location_heatmaps_for_batter"] = heatmaps

    # ── Batter data ───────────────────────────────────────────────────────────
    try:
        df_b_2025 = get_batter_statcast(batter_id, 2025)
        df_b_2026 = get_batter_statcast(batter_id, 2026)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch batter Statcast: {e}")

    n_pa_2026 = (
        df_b_2026["at_bat_number"].nunique()
        if not df_b_2026.empty and "at_bat_number" in df_b_2026.columns
        else len(df_b_2026) // 4
    )
    batter_blend_meta = build_blend_metadata(df_b_2026, df_b_2025, n_p_2026, n_pa_2026)
    blended_batter = blend_dataframes(df_b_2026, df_b_2025, n_p_2026, n_pa_2026)

    # Pitcher's primary locations for this batter's hand
    pitcher_locations = heatmaps.get(pitcher_pts[0], []) if pitcher_pts else []

    matchup = build_batter_matchup(
        blended_batter, pitcher_pts, pitcher_locations, batter_blend_meta
    )

    # ── Narratives ────────────────────────────────────────────────────────────
    lineup_matchups = [{
        "name": batter_name,
        "bat_side": batter_hand,
        **matchup,
    }]
    narratives = generate_narratives(pitcher_name, profile, lineup_matchups, pitcher_blend_meta)

    return {
        "pitcher": {
            "pitcher_id": pitcher_id,
            "pitcher_name": pitcher_name,
            "blend_meta": pitcher_blend_meta,
            "profile_change_alerts": profile_alerts,
            "profile": profile,
        },
        "batter": {
            "batter_id": batter_id,
            "batter_name": batter_name,
            "bat_side": batter_hand,
            "blend_meta": batter_blend_meta,
            "matchup": matchup,
        },
        "narratives": narratives,
    }
