"""Post-game analysis helpers for pitcher and hitter performance vs prior norms."""

from __future__ import annotations

from collections import defaultdict
import pandas as pd

from .pitcher_profile import get_pitch_mix


SWING_EVENTS = {
    "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
    "hit_into_play", "hit_into_play_no_out", "hit_into_play_score",
}
WHIFF_EVENTS = {"swinging_strike", "swinging_strike_blocked"}


def extract_game_pitch_events(feed: dict) -> list[dict]:
    """Extract pitch-level events from MLB live feed for both teams."""
    events_out: list[dict] = []
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])

    for play in plays:
        about = play.get("about", {})
        matchup = play.get("matchup", {})
        pitcher = matchup.get("pitcher", {})
        batter = matchup.get("batter", {})

        for event in play.get("playEvents", []):
            if event.get("type") != "pitch":
                continue

            details = event.get("details", {})
            pitch_data = event.get("pitchData", {})
            coordinates = pitch_data.get("coordinates", {})
            hit_data = event.get("hitData", {}) or {}

            events_out.append({
                "inning": about.get("inning"),
                "is_top_inning": about.get("isTopInning"),
                "pitcher_id": pitcher.get("id"),
                "pitcher_name": pitcher.get("fullName"),
                "batter_id": batter.get("id"),
                "batter_name": batter.get("fullName"),
                "pitch_type": details.get("type", {}).get("code"),
                "description": details.get("description", ""),
                "release_speed": pitch_data.get("startSpeed"),
                "zone": pitch_data.get("zone"),
                "plate_x": coordinates.get("pX"),
                "plate_z": coordinates.get("pZ"),
                "estimated_woba_using_speedangle": hit_data.get("launchSpeedAngle") and hit_data.get("launchSpeed"),
                "launch_speed": hit_data.get("launchSpeed"),
            })

    return events_out


def _pitcher_progression(game_df: pd.DataFrame) -> list[dict]:
    results = []
    if game_df.empty:
        return results

    for inn, grp in game_df.groupby("inning"):
        velo = grp["release_speed"].dropna()
        mix = grp["pitch_type"].value_counts(normalize=True)
        swings = grp[grp["description"].isin(SWING_EVENTS)]
        whiffs = grp[grp["description"].isin(WHIFF_EVENTS)]

        results.append({
            "inning": int(inn),
            "pitch_count": len(grp),
            "avg_velo": round(float(velo.mean()), 1) if not velo.empty else None,
            "whiff_rate": round(len(whiffs) / len(swings), 3) if len(swings) else None,
            "pitch_mix": {str(k): round(v * 100, 1) for k, v in mix.items()},
        })

    return sorted(results, key=lambda x: x["inning"])


def build_pitcher_postgame(game_events: list[dict], norm_df: pd.DataFrame | None) -> dict:
    """Build post-game pitcher view: progression + deviations vs blended norm."""
    game_df = pd.DataFrame(game_events)
    norm_df = norm_df if norm_df is not None else pd.DataFrame()
    if game_df.empty:
        return {
            "progression": [],
            "deviations": {"pitch_mix": [], "velo_delta": None, "whiff_delta": None},
        }

    progression = _pitcher_progression(game_df)

    game_mix = get_pitch_mix(game_df)
    norm_mix = get_pitch_mix(norm_df)
    norm_lookup = {x["pitch_type"]: x for x in norm_mix}

    mix_deviations = []
    for gm in game_mix:
        nm = norm_lookup.get(gm["pitch_type"])
        norm_pct = nm["pct"] if nm else 0.0
        delta = round(gm["pct"] - norm_pct, 1)
        mix_deviations.append({
            "pitch_type": gm["pitch_type"],
            "game_pct": gm["pct"],
            "norm_pct": norm_pct,
            "delta": delta,
            "flag": abs(delta) >= 8,
        })

    game_velo = game_df["release_speed"].dropna()
    norm_velo = norm_df["release_speed"].dropna() if not norm_df.empty else pd.Series(dtype=float)
    velo_delta = None
    if not game_velo.empty and not norm_velo.empty:
        velo_delta = round(float(game_velo.mean() - norm_velo.mean()), 1)

    game_swings = game_df[game_df["description"].isin(SWING_EVENTS)]
    game_whiffs = game_df[game_df["description"].isin(WHIFF_EVENTS)]
    norm_swings = norm_df[norm_df["description"].isin(SWING_EVENTS)] if not norm_df.empty else pd.DataFrame()
    norm_whiffs = norm_df[norm_df["description"].isin(WHIFF_EVENTS)] if not norm_df.empty else pd.DataFrame()
    whiff_delta = None
    if len(game_swings) and len(norm_swings):
        whiff_delta = round((len(game_whiffs) / len(game_swings)) - (len(norm_whiffs) / len(norm_swings)), 3)

    return {
        "progression": progression,
        "deviations": {
            "pitch_mix": sorted(mix_deviations, key=lambda x: abs(x["delta"]), reverse=True),
            "velo_delta": velo_delta,
            "whiff_delta": whiff_delta,
        },
    }


def build_hitter_postgame(game_events: list[dict], norm_df: pd.DataFrame | None) -> dict:
    """Build per-hitter success/failure vs prior norms by pitch, velo, and zone."""
    game_df = pd.DataFrame(game_events)
    norm_df = norm_df if norm_df is not None else pd.DataFrame()
    if game_df.empty:
        return {"by_pitch_type": [], "velo_bands": [], "zones": [], "summary": []}

    insights = []

    by_pitch = []
    for pt, grp in game_df.groupby("pitch_type"):
        if not pt:
            continue
        g_x = grp["estimated_woba_using_speedangle"].dropna()
        n_grp = norm_df[norm_df["pitch_type"] == pt] if not norm_df.empty else pd.DataFrame()
        n_x = n_grp["estimated_woba_using_speedangle"].dropna() if not n_grp.empty else pd.Series(dtype=float)
        g_val = float(g_x.mean()) if not g_x.empty else None
        n_val = float(n_x.mean()) if not n_x.empty else None
        delta = round(g_val - n_val, 3) if g_val is not None and n_val is not None else None
        by_pitch.append({
            "pitch_type": str(pt),
            "game_xwoba": round(g_val, 3) if g_val is not None else None,
            "norm_xwoba": round(n_val, 3) if n_val is not None else None,
            "delta": delta,
            "pitches_seen": len(grp),
        })

    if by_pitch:
        top = max(by_pitch, key=lambda x: x["delta"] if x["delta"] is not None else -999)
        low = min(by_pitch, key=lambda x: x["delta"] if x["delta"] is not None else 999)
        if top.get("delta") is not None:
            insights.append(f"Best against {top['pitch_type']} ({top['delta']:+.3f} xwOBA vs norm)")
        if low.get("delta") is not None:
            insights.append(f"Struggled most vs {low['pitch_type']} ({low['delta']:+.3f} xwOBA vs norm)")

    bands = [(0, 90, "<90"), (90, 95, "90-95"), (95, 120, "95+")]
    velo_bands = []
    for low, high, label in bands:
        g = game_df[(game_df["release_speed"] >= low) & (game_df["release_speed"] < high)]
        n = norm_df[(norm_df["release_speed"] >= low) & (norm_df["release_speed"] < high)] if not norm_df.empty else pd.DataFrame()
        g_x = g["estimated_woba_using_speedangle"].dropna()
        n_x = n["estimated_woba_using_speedangle"].dropna() if not n.empty else pd.Series(dtype=float)
        g_val = float(g_x.mean()) if not g_x.empty else None
        n_val = float(n_x.mean()) if not n_x.empty else None
        velo_bands.append({
            "band": label,
            "game_xwoba": round(g_val, 3) if g_val is not None else None,
            "norm_xwoba": round(n_val, 3) if n_val is not None else None,
            "delta": round(g_val - n_val, 3) if g_val is not None and n_val is not None else None,
            "sample": len(g),
        })

    zones = []
    for zone_id in range(1, 10):
        g = game_df[game_df["zone"] == zone_id]
        if g.empty:
            continue
        n = norm_df[norm_df["zone"] == zone_id] if not norm_df.empty else pd.DataFrame()
        g_x = g["estimated_woba_using_speedangle"].dropna()
        n_x = n["estimated_woba_using_speedangle"].dropna() if not n.empty else pd.Series(dtype=float)
        g_val = float(g_x.mean()) if not g_x.empty else None
        n_val = float(n_x.mean()) if not n_x.empty else None
        zones.append({
            "zone_id": zone_id,
            "game_xwoba": round(g_val, 3) if g_val is not None else None,
            "norm_xwoba": round(n_val, 3) if n_val is not None else None,
            "delta": round(g_val - n_val, 3) if g_val is not None and n_val is not None else None,
            "sample": len(g),
        })

    return {
        "by_pitch_type": sorted(by_pitch, key=lambda x: x["pitches_seen"], reverse=True),
        "velo_bands": velo_bands,
        "zones": sorted(zones, key=lambda x: x["sample"], reverse=True),
        "summary": insights,
    }


def split_events_by_player(events: list[dict], key: str) -> dict[int, list[dict]]:
    """Group events by pitcher_id or batter_id."""
    grouped: dict[int, list[dict]] = defaultdict(list)
    for ev in events:
        pid = ev.get(key)
        if pid:
            grouped[pid].append(ev)
    return grouped
