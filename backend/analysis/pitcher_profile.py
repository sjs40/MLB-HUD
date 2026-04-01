"""
Pitcher analysis engine — operates on blended Statcast DataFrames.

All functions accept a DataFrame produced by data_blending.blend_dataframes(),
which includes a 'blend_weight' column for weighted statistics.
"""

import pandas as pd
import numpy as np

# Statcast zone IDs 1–9 map to a 3x3 grid (row-major, top-to-bottom, left-to-right
# from the catcher's perspective). Zones 11–14 are chase zones outside the strike zone.
STRIKE_ZONES = list(range(1, 10))
ALL_ZONES = list(range(1, 15))

HITTER_FRIENDLY_COUNTS = {"2-0", "3-0", "3-1"}
PITCHER_FRIENDLY_COUNTS = {"0-2", "1-2", "2-2"}

INNING_BANDS = [
    ("1-3", (1, 3)),
    ("4-6", (4, 6)),
    ("7+",  (7, 99)),
]

VELO_DROP_THRESHOLD = 1.5  # mph
SMALL_SAMPLE_THRESHOLD = 50


def _count_str(row) -> str:
    """Build 'balls-strikes' string from Statcast columns."""
    try:
        return f"{int(row['balls'])}-{int(row['strikes'])}"
    except Exception:
        return ""


def get_pitch_mix(df: pd.DataFrame) -> list[dict]:
    """
    Return pitch mix summary per pitch type.
    Each entry: {pitch_type, pct, avg_velo, spin_rate, h_break, v_break}
    """
    if df.empty or "pitch_type" not in df.columns:
        return []

    df = df.dropna(subset=["pitch_type"])
    total = len(df)
    results = []

    for pt, group in df.groupby("pitch_type"):
        w = group["blend_weight"].values if "blend_weight" in group.columns else None

        def wavg(col):
            vals = group[col].dropna()
            if vals.empty:
                return None
            if w is not None:
                weights = group.loc[vals.index, "blend_weight"]
                return float(np.average(vals, weights=weights))
            return float(vals.mean())

        results.append({
            "pitch_type": str(pt),
            "pct": round(len(group) / total * 100, 1),
            "count": len(group),
            "avg_velo": round(wavg("release_speed"), 1) if wavg("release_speed") is not None else None,
            "spin_rate": round(wavg("release_spin_rate"), 0) if wavg("release_spin_rate") is not None else None,
            "h_break": round(wavg("pfx_x"), 1) if wavg("pfx_x") is not None else None,
            "v_break": round(wavg("pfx_z"), 1) if wavg("pfx_z") is not None else None,
        })

    return sorted(results, key=lambda x: x["pct"], reverse=True)


def get_location_heatmap(
    df: pd.DataFrame,
    pitch_type: str,
    batter_hand: str,
) -> list[dict]:
    """
    Return 9-zone strike zone grid aggregations for a specific pitch type
    and batter handedness.

    Returns list of {zone_id, count, whiff_rate, xwoba} for zones 1–9.
    """
    subset = df.copy()
    if pitch_type and pitch_type != "ALL":
        subset = subset[subset["pitch_type"] == pitch_type]
    if batter_hand in ("L", "R"):
        subset = subset[subset["stand"] == batter_hand]

    subset = subset[subset["zone"].isin(STRIKE_ZONES)].copy()

    results = []
    for zone_id in STRIKE_ZONES:
        zone_df = subset[subset["zone"] == zone_id]
        if zone_df.empty:
            results.append({
                "zone_id": zone_id,
                "count": 0,
                "whiff_rate": None,
                "xwoba": None,
            })
            continue

        swings = zone_df[zone_df["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
            "foul", "foul_tip", "hit_into_play", "hit_into_play_no_out",
            "hit_into_play_score",
        ])]
        whiffs = zone_df[zone_df["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
        ])]
        whiff_rate = len(whiffs) / len(swings) if len(swings) > 0 else None

        xwoba_vals = zone_df["estimated_woba_using_speedangle"].dropna()
        xwoba = float(xwoba_vals.mean()) if not xwoba_vals.empty else None

        results.append({
            "zone_id": zone_id,
            "count": len(zone_df),
            "whiff_rate": round(whiff_rate, 3) if whiff_rate is not None else None,
            "xwoba": round(xwoba, 3) if xwoba is not None else None,
        })

    return results


def get_count_tendencies(df: pd.DataFrame) -> dict:
    """
    Return pitch type distribution in hitter-friendly vs. pitcher-friendly counts.

    Returns:
    {
      "hitter_friendly": {pitch_type: pct, ...},
      "pitcher_friendly": {pitch_type: pct, ...},
    }
    """
    if df.empty:
        return {"hitter_friendly": {}, "pitcher_friendly": {}}

    df = df.copy()
    df["count_str"] = df.apply(_count_str, axis=1)

    def _distribution(subset: pd.DataFrame) -> dict:
        if subset.empty:
            return {}
        counts = subset["pitch_type"].value_counts(normalize=True)
        return {str(k): round(v * 100, 1) for k, v in counts.items()}

    hitter_df = df[df["count_str"].isin(HITTER_FRIENDLY_COUNTS)]
    pitcher_df = df[df["count_str"].isin(PITCHER_FRIENDLY_COUNTS)]

    return {
        "hitter_friendly": _distribution(hitter_df),
        "pitcher_friendly": _distribution(pitcher_df),
        "hitter_friendly_counts": sorted(HITTER_FRIENDLY_COUNTS),
        "pitcher_friendly_counts": sorted(PITCHER_FRIENDLY_COUNTS),
    }


def get_platoon_splits(df: pd.DataFrame) -> dict:
    """
    Return xwOBA allowed vs. LHH and RHH per pitch type.
    Flags small_sample=True if a split has < 50 pitches.

    Returns:
    {
      "vs_LHH": [{pitch_type, xwoba, count, small_sample}],
      "vs_RHH": [{pitch_type, xwoba, count, small_sample}],
    }
    """
    results = {}
    for hand, label in [("L", "vs_LHH"), ("R", "vs_RHH")]:
        hand_df = df[df["stand"] == hand] if "stand" in df.columns else pd.DataFrame()
        splits = []
        if not hand_df.empty:
            for pt, group in hand_df.groupby("pitch_type"):
                xwoba_vals = group["estimated_woba_using_speedangle"].dropna()
                splits.append({
                    "pitch_type": str(pt),
                    "xwoba": round(float(xwoba_vals.mean()), 3) if not xwoba_vals.empty else None,
                    "count": len(group),
                    "small_sample": len(group) < SMALL_SAMPLE_THRESHOLD,
                })
        results[label] = sorted(splits, key=lambda x: x["count"], reverse=True)
    return results


def get_game_progression(df: pd.DataFrame) -> list[dict]:
    """
    Return per-inning-band velo, whiff rate, and pitch mix.
    Flags bands where velocity drops >1.5 mph from the previous band.

    Returns list of:
    {inning_band, avg_velo, whiff_rate, pitch_mix: {pitch_type: pct}, velo_flag}
    """
    if df.empty or "inning" not in df.columns:
        return []

    results = []
    prev_velo = None

    for band_label, (low, high) in INNING_BANDS:
        band_df = df[(df["inning"] >= low) & (df["inning"] <= high)]

        if band_df.empty:
            results.append({
                "inning_band": band_label,
                "avg_velo": None,
                "whiff_rate": None,
                "pitch_mix": {},
                "velo_flag": False,
                "pitch_count": 0,
            })
            continue

        velo_vals = band_df["release_speed"].dropna()
        avg_velo = float(velo_vals.mean()) if not velo_vals.empty else None

        swings = band_df[band_df["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
            "foul", "foul_tip", "hit_into_play", "hit_into_play_no_out",
            "hit_into_play_score",
        ])]
        whiffs = band_df[band_df["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
        ])]
        whiff_rate = len(whiffs) / len(swings) if len(swings) > 0 else None

        mix = band_df["pitch_type"].value_counts(normalize=True)
        pitch_mix = {str(k): round(v * 100, 1) for k, v in mix.items()}

        velo_flag = (
            avg_velo is not None
            and prev_velo is not None
            and (prev_velo - avg_velo) >= VELO_DROP_THRESHOLD
        )

        results.append({
            "inning_band": band_label,
            "avg_velo": round(avg_velo, 1) if avg_velo is not None else None,
            "whiff_rate": round(whiff_rate, 3) if whiff_rate is not None else None,
            "pitch_mix": pitch_mix,
            "velo_flag": velo_flag,
            "velo_drop": round(prev_velo - avg_velo, 1) if velo_flag else None,
            "pitch_count": len(band_df),
        })

        if avg_velo is not None:
            prev_velo = avg_velo

    return results


def get_weapons_and_vulnerabilities(df: pd.DataFrame) -> dict:
    """
    Identify the pitcher's best and worst pitches.

    Weapons: top 2 pitch types by whiff rate (minimum 20 pitches).
    Vulnerabilities: bottom 2 pitch types by xwOBA allowed (minimum 20 pitches).

    Returns: {weapons: [...], vulnerabilities: [...]}
    """
    if df.empty:
        return {"weapons": [], "vulnerabilities": []}

    MIN_PITCHES = 20
    pitch_stats = []

    for pt, group in df.groupby("pitch_type"):
        if len(group) < MIN_PITCHES:
            continue

        swings = group[group["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
            "foul", "foul_tip", "hit_into_play", "hit_into_play_no_out",
            "hit_into_play_score",
        ])]
        whiffs = group[group["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
        ])]
        whiff_rate = len(whiffs) / len(swings) if len(swings) > 0 else 0

        xwoba_vals = group["estimated_woba_using_speedangle"].dropna()
        xwoba = float(xwoba_vals.mean()) if not xwoba_vals.empty else None

        run_val_col = "delta_run_exp"
        run_value = None
        if run_val_col in group.columns:
            rv_vals = group[run_val_col].dropna()
            run_value = float(rv_vals.sum()) if not rv_vals.empty else None

        pitch_stats.append({
            "pitch_type": str(pt),
            "count": len(group),
            "whiff_rate": round(whiff_rate, 3),
            "xwoba": round(xwoba, 3) if xwoba is not None else None,
            "run_value": round(run_value, 2) if run_value is not None else None,
        })

    if not pitch_stats:
        return {"weapons": [], "vulnerabilities": []}

    # Weapons: highest whiff rate
    weapons = sorted(
        [p for p in pitch_stats if p["whiff_rate"] is not None],
        key=lambda x: x["whiff_rate"],
        reverse=True,
    )[:2]

    # Vulnerabilities: highest xwOBA allowed (worst for pitcher)
    vulnerabilities = sorted(
        [p for p in pitch_stats if p["xwoba"] is not None],
        key=lambda x: x["xwoba"],
        reverse=True,
    )[:2]

    return {"weapons": weapons, "vulnerabilities": vulnerabilities}


def build_pitcher_profile(df: pd.DataFrame) -> dict:
    """
    Top-level function: build a complete pitcher profile from a blended DataFrame.
    Returns all analysis sections as a single dict.
    """
    return {
        "pitch_mix": get_pitch_mix(df),
        "count_tendencies": get_count_tendencies(df),
        "platoon_splits": get_platoon_splits(df),
        "game_progression": get_game_progression(df),
        "weapons_vulnerabilities": get_weapons_and_vulnerabilities(df),
        "location_heatmaps": {
            # Populated on demand per pitch type / batter hand in the endpoint layer
            # to avoid computing all combinations upfront
        },
        "total_pitches": len(df),
    }
