"""
2025/2026 Statcast data blending engine.

Blending weights by sample size:
  Pitcher pitches 2026 | Batter PA 2026 | 2026 weight | 2025 weight
  < 300                | < 100          | 40%         | 60%
  300–600              | 100–250        | 60%         | 40%
  600–900              | 250–400        | 80%         | 20%
  900+                 | 400+           | 100%        | 0%

Profile Change Alert: flag if any pitch type's usage % shifts >8pp between seasons.
"""

import pandas as pd
import numpy as np
from typing import TypedDict


class BlendMetadata(TypedDict):
    n_2026_pitches: int
    n_2025_pitches: int
    weight_2026: float
    weight_2025: float
    label: str


# ── Weight lookup ─────────────────────────────────────────────────────────────

_PITCHER_THRESHOLDS = [(300, 0.40, 0.60), (600, 0.60, 0.40), (900, 0.80, 0.20)]
_BATTER_THRESHOLDS  = [(100, 0.40, 0.60), (250, 0.60, 0.40), (400, 0.80, 0.20)]


def get_blend_weights(
    n_pitcher_pitches_2026: int,
    n_batter_pa_2026: int,
) -> tuple[float, float]:
    """
    Return (weight_2026, weight_2025) based on sample sizes.
    Uses the more conservative weight (lower 2026 weight) of the two inputs.
    """
    def _pitcher_weight(n: int) -> tuple[float, float]:
        for threshold, w26, w25 in _PITCHER_THRESHOLDS:
            if n < threshold:
                return w26, w25
        return 1.0, 0.0

    def _batter_weight(n: int) -> tuple[float, float]:
        for threshold, w26, w25 in _BATTER_THRESHOLDS:
            if n < threshold:
                return w26, w25
        return 1.0, 0.0

    p26, p25 = _pitcher_weight(n_pitcher_pitches_2026)
    b26, b25 = _batter_weight(n_batter_pa_2026)

    # Use the more conservative (lower 2026) weight
    if p26 <= b26:
        return p26, p25
    return b26, b25


def blend_metric(val_2026: float, val_2025: float, w26: float, w25: float) -> float:
    """Blend two scalar metric values using the given weights."""
    return val_2026 * w26 + val_2025 * w25


def build_blend_metadata(
    df_2026: pd.DataFrame,
    df_2025: pd.DataFrame,
    n_pitcher_pitches_2026: int,
    n_batter_pa_2026: int,
) -> BlendMetadata:
    """Build a BlendMetadata dict for display in the UI."""
    w26, w25 = get_blend_weights(n_pitcher_pitches_2026, n_batter_pa_2026)
    n_2025 = len(df_2025) if df_2025 is not None else 0
    pct_26 = int(w26 * 100)
    pct_25 = int(w25 * 100)

    if w25 == 0:
        label = f"Analysis based on {n_pitcher_pitches_2026} 2026 pitches (2026 only)"
    else:
        label = (
            f"Analysis based on {n_pitcher_pitches_2026} 2026 pitches "
            f"+ 2025 full season (blended {pct_26}/{pct_25})"
        )

    return BlendMetadata(
        n_2026_pitches=n_pitcher_pitches_2026,
        n_2025_pitches=n_2025,
        weight_2026=w26,
        weight_2025=w25,
        label=label,
    )


def blend_dataframes(
    df_2026: pd.DataFrame,
    df_2025: pd.DataFrame,
    n_pitcher_pitches_2026: int,
    n_batter_pa_2026: int,
) -> pd.DataFrame:
    """
    Concatenate 2025 and 2026 DataFrames with row-level weighting via a
    'blend_weight' column. Analysis functions use this column to compute
    weighted statistics.

    If 2026 weight is 100%, only 2026 rows are returned.
    """
    w26, w25 = get_blend_weights(n_pitcher_pitches_2026, n_batter_pa_2026)

    parts = []

    if df_2026 is not None and not df_2026.empty:
        df26 = df_2026.copy()
        df26["season"] = 2026
        df26["blend_weight"] = w26
        parts.append(df26)

    if w25 > 0 and df_2025 is not None and not df_2025.empty:
        df25 = df_2025.copy()
        df25["season"] = 2025
        df25["blend_weight"] = w25
        parts.append(df25)

    if not parts:
        return pd.DataFrame()

    return pd.concat(parts, ignore_index=True)


# ── Profile Change Alert ──────────────────────────────────────────────────────

PROFILE_CHANGE_THRESHOLD_PP = 8.0  # percentage points


def check_profile_change_alert(
    df_2026: pd.DataFrame,
    df_2025: pd.DataFrame,
    min_pitches: int = 50,
) -> list[dict]:
    """
    Detect meaningful pitch mix changes between 2025 and 2026.

    Returns a list of dicts for pitch types where usage shifted >8pp:
        [{pitch_type, pct_2026, pct_2025, delta, direction}]

    Only runs the check if 2026 has at least `min_pitches` pitches.
    """
    if df_2026 is None or df_2026.empty or len(df_2026) < min_pitches:
        return []
    if df_2025 is None or df_2025.empty:
        return []

    def _pitch_mix(df: pd.DataFrame) -> dict[str, float]:
        counts = df["pitch_type"].value_counts(normalize=True)
        return (counts * 100).to_dict()

    mix_2026 = _pitch_mix(df_2026)
    mix_2025 = _pitch_mix(df_2025)

    all_pitch_types = set(mix_2026.keys()) | set(mix_2025.keys())
    alerts = []

    for pt in all_pitch_types:
        pct_26 = mix_2026.get(pt, 0.0)
        pct_25 = mix_2025.get(pt, 0.0)
        delta = pct_26 - pct_25

        if abs(delta) > PROFILE_CHANGE_THRESHOLD_PP:
            alerts.append({
                "pitch_type": pt,
                "pct_2026": round(pct_26, 1),
                "pct_2025": round(pct_25, 1),
                "delta": round(delta, 1),
                "direction": "up" if delta > 0 else "down",
            })

    return sorted(alerts, key=lambda x: abs(x["delta"]), reverse=True)
