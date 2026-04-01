"""
Batter matchup engine — operates on blended Statcast DataFrames.

Computes per-batter analysis against a specific pitcher's profile:
- xwOBA by pitch type
- Swing and whiff rates by pitch type
- Zone vulnerability and overlap with pitcher's primary locations
- Count leverage (performance in pitcher-friendly vs. hitter-friendly counts)
- Composite edge score with component transparency
"""

import pandas as pd
import numpy as np
from typing import Optional

SMALL_SAMPLE_THRESHOLD = 50

HITTER_FRIENDLY_COUNTS = {"2-0", "3-0", "3-1"}
PITCHER_FRIENDLY_COUNTS = {"0-2", "1-2", "2-2"}

# Zone IDs where the batter is considered "weak" if xwOBA > threshold
WEAK_ZONE_XWOBA_THRESHOLD = 0.380  # higher than avg = vulnerability


def _count_str(row) -> str:
    try:
        return f"{int(row['balls'])}-{int(row['strikes'])}"
    except Exception:
        return ""


def get_xwoba_by_pitch_type(
    df: pd.DataFrame,
    pitcher_pitch_types: list[str],
) -> list[dict]:
    """
    Return batter's xwOBA against each of the pitcher's primary pitch types.

    Returns list of:
    {pitch_type, xwoba, sample_size, small_sample_flag}
    """
    if df.empty:
        return []

    results = []
    for pt in pitcher_pitch_types:
        subset = df[df["pitch_type"] == pt]
        xwoba_vals = subset["estimated_woba_using_speedangle"].dropna()
        sample_size = len(subset)
        results.append({
            "pitch_type": pt,
            "xwoba": round(float(xwoba_vals.mean()), 3) if not xwoba_vals.empty else None,
            "sample_size": sample_size,
            "small_sample_flag": sample_size < SMALL_SAMPLE_THRESHOLD,
        })

    return sorted(results, key=lambda x: x["sample_size"], reverse=True)


def get_swing_whiff_rates(df: pd.DataFrame) -> list[dict]:
    """
    Return swing rate and whiff rate per pitch type.

    Returns list of:
    {pitch_type, swing_rate, whiff_rate, count}
    """
    if df.empty or "pitch_type" not in df.columns:
        return []

    results = []
    swing_descs = {
        "swinging_strike", "swinging_strike_blocked",
        "foul", "foul_tip", "hit_into_play",
        "hit_into_play_no_out", "hit_into_play_score",
    }
    whiff_descs = {"swinging_strike", "swinging_strike_blocked"}

    for pt, group in df.groupby("pitch_type"):
        total = len(group)
        swings = group[group["description"].isin(swing_descs)]
        whiffs = group[group["description"].isin(whiff_descs)]

        swing_rate = len(swings) / total if total > 0 else None
        whiff_rate = len(whiffs) / len(swings) if len(swings) > 0 else None

        results.append({
            "pitch_type": str(pt),
            "swing_rate": round(swing_rate, 3) if swing_rate is not None else None,
            "whiff_rate": round(whiff_rate, 3) if whiff_rate is not None else None,
            "count": total,
        })

    return sorted(results, key=lambda x: x["count"], reverse=True)


def get_zone_vulnerability(
    df: pd.DataFrame,
    pitcher_locations: list[dict],
) -> dict:
    """
    Identify the batter's weak zones and check overlap with pitcher's
    primary locations.

    Args:
        df: blended batter DataFrame
        pitcher_locations: list of {zone_id, count, whiff_rate, xwoba}
                           from pitcher's get_location_heatmap output

    Returns:
    {
      batter_weak_zones: [zone_id, ...],
      pitcher_primary_zones: [zone_id, ...],
      overlap_zones: [zone_id, ...],
    }
    """
    if df.empty:
        return {"batter_weak_zones": [], "pitcher_primary_zones": [], "overlap_zones": []}

    # Batter weak zones: zones where they have high xwOBA allowed by pitchers
    # (i.e., pitchers do well against this batter in these zones)
    zone_stats = []
    for zone_id in range(1, 10):
        zone_df = df[df["zone"] == zone_id]
        if zone_df.empty:
            continue
        xwoba_vals = zone_df["estimated_woba_using_speedangle"].dropna()
        if xwoba_vals.empty:
            continue
        # For a batter, lower xwOBA = batter is worse (pitcher advantage)
        avg_xwoba = float(xwoba_vals.mean())
        zone_stats.append({"zone_id": zone_id, "xwoba": avg_xwoba, "count": len(zone_df)})

    # Weak zones: below-average xwOBA for the batter (pitchers have advantage)
    if zone_stats:
        median_xwoba = float(np.median([z["xwoba"] for z in zone_stats]))
        batter_weak_zones = [
            z["zone_id"] for z in zone_stats
            if z["xwoba"] < median_xwoba and z["count"] >= 5
        ]
    else:
        batter_weak_zones = []

    # Pitcher's primary zones: top zones by pitch count
    if pitcher_locations:
        sorted_pitcher = sorted(pitcher_locations, key=lambda x: x.get("count", 0), reverse=True)
        top_n = max(3, len(sorted_pitcher) // 3)
        pitcher_primary_zones = [z["zone_id"] for z in sorted_pitcher[:top_n]]
    else:
        pitcher_primary_zones = []

    overlap_zones = [z for z in batter_weak_zones if z in pitcher_primary_zones]

    return {
        "batter_weak_zones": batter_weak_zones,
        "pitcher_primary_zones": pitcher_primary_zones,
        "overlap_zones": overlap_zones,
    }


def get_count_leverage(df: pd.DataFrame) -> dict:
    """
    Return batter's xwOBA in hitter-friendly vs. pitcher-friendly counts.

    Returns:
    {
      hitter_friendly: {xwoba, sample_size},
      pitcher_friendly: {xwoba, sample_size},
      leverage_delta: float  (positive = batter benefits from hitter counts)
    }
    """
    if df.empty:
        return {"hitter_friendly": None, "pitcher_friendly": None, "leverage_delta": None}

    df = df.copy()
    df["count_str"] = df.apply(_count_str, axis=1)

    def _xwoba_in_counts(count_set: set) -> dict:
        subset = df[df["count_str"].isin(count_set)]
        xwoba_vals = subset["estimated_woba_using_speedangle"].dropna()
        if xwoba_vals.empty:
            return {"xwoba": None, "sample_size": len(subset)}
        return {"xwoba": round(float(xwoba_vals.mean()), 3), "sample_size": len(subset)}

    hf = _xwoba_in_counts(HITTER_FRIENDLY_COUNTS)
    pf = _xwoba_in_counts(PITCHER_FRIENDLY_COUNTS)

    delta = None
    if hf["xwoba"] is not None and pf["xwoba"] is not None:
        delta = round(hf["xwoba"] - pf["xwoba"], 3)

    return {
        "hitter_friendly": hf,
        "pitcher_friendly": pf,
        "leverage_delta": delta,
        "hitter_friendly_counts": sorted(HITTER_FRIENDLY_COUNTS),
        "pitcher_friendly_counts": sorted(PITCHER_FRIENDLY_COUNTS),
    }


def compute_edge_score(
    xwoba_by_pitch: list[dict],
    swing_whiff: list[dict],
    zone_overlap: dict,
    count_leverage: dict,
    blend_meta: dict,
    league_avg_xwoba: float = 0.320,
) -> dict:
    """
    Compute a composite pitcher edge score (0–100) for a batter matchup.

    Higher score = pitcher has more edge over this batter.
    All component inputs are returned for UI transparency.
    Small sample inputs are down-weighted, not excluded.

    Score components:
    1. xwOBA component (40%): pitcher's pitch types vs. batter's xwOBA vs. league avg
    2. Whiff rate component (25%): batter's whiff rate on pitcher's key pitches
    3. Zone overlap component (20%): overlap between pitcher's locations and batter's weak zones
    4. Count leverage component (15%): batter's performance in pitcher-friendly counts

    Returns:
    {
      score: float,
      components: {xwoba, whiff, zone, count_leverage},
      flags: [str, ...]   # small sample and other warnings
    }
    """
    flags = []
    components = {}

    # ── Component 1: xwOBA (40%) ──────────────────────────────────────────────
    xwoba_scores = []
    small_sample_pitches = []
    for entry in xwoba_by_pitch:
        if entry["xwoba"] is None:
            continue
        # Edge score: lower batter xwOBA = better for pitcher
        # Normalize: 0.200 xwOBA = 100, 0.400 xwOBA = 0, linear
        raw = max(0.0, min(1.0, (0.400 - entry["xwoba"]) / 0.200))
        weight = 0.5 if entry["small_sample_flag"] else 1.0
        xwoba_scores.append((raw * 100, weight))
        if entry["small_sample_flag"]:
            small_sample_pitches.append(entry["pitch_type"])

    if xwoba_scores:
        values, weights = zip(*xwoba_scores)
        xwoba_component = float(np.average(values, weights=weights))
    else:
        xwoba_component = 50.0  # neutral if no data

    components["xwoba"] = {
        "score": round(xwoba_component, 1),
        "weight": 0.40,
        "detail": xwoba_by_pitch,
    }

    if small_sample_pitches:
        flags.append(f"Small sample (<{SMALL_SAMPLE_THRESHOLD} pitches) for: {', '.join(small_sample_pitches)}")

    # ── Component 2: Whiff rate (25%) ─────────────────────────────────────────
    whiff_scores = []
    for entry in swing_whiff:
        if entry["whiff_rate"] is None:
            continue
        # Higher whiff rate = more edge for pitcher
        # 0.15 whiff rate ≈ league avg, 0.40 = elite
        raw = max(0.0, min(1.0, entry["whiff_rate"] / 0.40))
        whiff_scores.append(raw * 100)

    whiff_component = float(np.mean(whiff_scores)) if whiff_scores else 50.0
    components["whiff"] = {
        "score": round(whiff_component, 1),
        "weight": 0.25,
        "detail": swing_whiff,
    }

    # ── Component 3: Zone overlap (20%) ───────────────────────────────────────
    overlap_count = len(zone_overlap.get("overlap_zones", []))
    total_pitcher_zones = len(zone_overlap.get("pitcher_primary_zones", []))
    if total_pitcher_zones > 0:
        overlap_pct = overlap_count / total_pitcher_zones
    else:
        overlap_pct = 0.0
    # More overlap = more pitcher edge
    zone_component = overlap_pct * 100
    components["zone"] = {
        "score": round(zone_component, 1),
        "weight": 0.20,
        "detail": zone_overlap,
    }

    # ── Component 4: Count leverage (15%) ─────────────────────────────────────
    delta = count_leverage.get("leverage_delta")
    if delta is not None:
        # Large positive delta = batter benefits much more from hitter counts
        # Large negative delta = batter performs similarly regardless of count
        # For pitcher edge: lower delta is better
        # Normalize: delta of -0.100 = 100 (pitcher edge), +0.150 = 0
        raw = max(0.0, min(1.0, (0.150 - delta) / 0.250))
        count_component = raw * 100
    else:
        count_component = 50.0

    components["count_leverage"] = {
        "score": round(count_component, 1),
        "weight": 0.15,
        "detail": count_leverage,
    }

    # ── Final weighted score ───────────────────────────────────────────────────
    final_score = (
        xwoba_component * 0.40
        + whiff_component * 0.25
        + zone_component * 0.20
        + count_component * 0.15
    )

    # Blend metadata flag
    if blend_meta.get("weight_2025", 0) > 0:
        flags.append(blend_meta.get("label", ""))

    return {
        "score": round(final_score, 1),
        "components": components,
        "flags": [f for f in flags if f],
    }


def build_batter_matchup(
    batter_df: pd.DataFrame,
    pitcher_pitch_types: list[str],
    pitcher_locations: list[dict],
    blend_meta: dict,
) -> dict:
    """
    Build a complete batter matchup analysis against a pitcher's profile.
    """
    xwoba_by_pitch = get_xwoba_by_pitch_type(batter_df, pitcher_pitch_types)
    swing_whiff = get_swing_whiff_rates(batter_df)
    zone_vuln = get_zone_vulnerability(batter_df, pitcher_locations)
    count_lev = get_count_leverage(batter_df)
    edge = compute_edge_score(xwoba_by_pitch, swing_whiff, zone_vuln, count_lev, blend_meta)

    return {
        "xwoba_by_pitch_type": xwoba_by_pitch,
        "swing_whiff_rates": swing_whiff,
        "zone_vulnerability": zone_vuln,
        "count_leverage": count_lev,
        "edge_score": edge,
    }
