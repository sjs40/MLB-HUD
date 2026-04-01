"""GET /game/{game_id}/postgame — pitcher/hitter post-game analysis vs prior norms."""

from fastapi import APIRouter, HTTPException

from ..analysis.postgame import (
    extract_game_pitch_events,
    build_pitcher_postgame,
    build_hitter_postgame,
    split_events_by_player,
)
from ..data.mlb_api import get_live_feed
from ..data.statcast import get_pitcher_statcast, get_batter_statcast
from ..data.data_blending import blend_dataframes

router = APIRouter(tags=["postgame"])


@router.get("/game/{game_id}/postgame")
def postgame(game_id: int):
    try:
        feed = get_live_feed(game_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch game feed: {e}")

    status = feed.get("gameData", {}).get("status", {}).get("abstractGameState")

    events = extract_game_pitch_events(feed)
    by_pitcher = split_events_by_player(events, "pitcher_id")
    by_batter = split_events_by_player(events, "batter_id")

    pitcher_reports = []
    for pitcher_id, game_events in by_pitcher.items():
        pitcher_name = game_events[0].get("pitcher_name", "Unknown")
        try:
            df_2025 = get_pitcher_statcast(pitcher_id, 2025)
            df_2026 = get_pitcher_statcast(pitcher_id, 2026)
            norm_df = blend_dataframes(df_2026, df_2025, len(df_2026), 0)
        except Exception:
            norm_df = None

        report = build_pitcher_postgame(game_events, norm_df if norm_df is not None else None)
        pitcher_reports.append({
            "pitcher_id": pitcher_id,
            "pitcher_name": pitcher_name,
            **report,
        })

    hitter_reports = []
    for batter_id, game_events in by_batter.items():
        batter_name = game_events[0].get("batter_name", "Unknown")
        try:
            df_2025 = get_batter_statcast(batter_id, 2025)
            df_2026 = get_batter_statcast(batter_id, 2026)
            n_pa_2026 = df_2026["at_bat_number"].nunique() if not df_2026.empty and "at_bat_number" in df_2026.columns else len(df_2026) // 4
            norm_df = blend_dataframes(df_2026, df_2025, len(df_2026), n_pa_2026)
        except Exception:
            norm_df = None

        report = build_hitter_postgame(game_events, norm_df if norm_df is not None else None)
        hitter_reports.append({
            "batter_id": batter_id,
            "batter_name": batter_name,
            **report,
        })

    return {
        "game_id": game_id,
        "status": status,
        "total_pitches": len(events),
        "pitchers": sorted(pitcher_reports, key=lambda x: len(x.get("progression", [])), reverse=True),
        "hitters": sorted(hitter_reports, key=lambda x: sum(b.get("sample", 0) for b in x.get("velo_bands", [])), reverse=True),
    }
