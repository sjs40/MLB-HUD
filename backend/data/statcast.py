"""
Statcast data fetching via pybaseball + local CSV caching.

Cache structure:
  cache/statcast/pitcher/{pitcher_id}_2025.csv       — static, never re-fetch
  cache/statcast/pitcher/{pitcher_id}_2026_{date}.csv — refresh daily
  cache/statcast/batter/{batter_id}_2025.csv
  cache/statcast/batter/{batter_id}_2026_{date}.csv
"""

import os
import pandas as pd
from datetime import date
from pathlib import Path

import pybaseball

# Silence pybaseball progress output in production; keep for dev visibility
pybaseball.cache.enable()

CACHE_DIR = Path(__file__).parent.parent / "cache" / "statcast"
PITCHER_CACHE = CACHE_DIR / "pitcher"
BATTER_CACHE = CACHE_DIR / "batter"

# Season date ranges
SEASON_RANGES = {
    2025: ("2025-03-20", "2025-11-01"),
    2026: ("2026-03-26", None),  # None = today
}


def _pitcher_cache_path(pitcher_id: int, season: int) -> Path:
    if season == 2025:
        return PITCHER_CACHE / f"{pitcher_id}_2025.csv"
    else:
        today = date.today().isoformat()
        return PITCHER_CACHE / f"{pitcher_id}_2026_{today}.csv"


def _batter_cache_path(batter_id: int, season: int) -> Path:
    if season == 2025:
        return BATTER_CACHE / f"{batter_id}_2025.csv"
    else:
        today = date.today().isoformat()
        return BATTER_CACHE / f"{batter_id}_2026_{today}.csv"


def _is_cached_2025(path: Path) -> bool:
    """2025 data is valid if the file exists at all."""
    return path.exists()


def _is_cached_2026(pitcher_or_batter_id: int, role: str) -> tuple[bool, Path]:
    """
    2026 data is valid if today's file exists.
    Returns (is_cached, path).
    """
    today = date.today().isoformat()
    if role == "pitcher":
        path = PITCHER_CACHE / f"{pitcher_or_batter_id}_2026_{today}.csv"
    else:
        path = BATTER_CACHE / f"{pitcher_or_batter_id}_2026_{today}.csv"
    return path.exists(), path


def get_pitcher_statcast(pitcher_id: int, season: int) -> pd.DataFrame:
    """
    Return Statcast pitch-level data for a pitcher.
    Uses local CSV cache — never re-fetches 2025, refreshes 2026 once daily.
    """
    if season == 2025:
        path = _pitcher_cache_path(pitcher_id, 2025)
        if _is_cached_2025(path):
            print(f"[cache HIT] pitcher {pitcher_id} 2025")
            return pd.read_csv(path)
        print(f"[cache MISS] pitcher {pitcher_id} 2025 — pulling from pybaseball...")
        start, end = SEASON_RANGES[2025]
        df = pybaseball.statcast_pitcher(start, end, player_id=pitcher_id)
        _save(df, path)
        print(f"  Saved {len(df)} rows to {path}")

    elif season == 2026:
        is_cached, path = _is_cached_2026(pitcher_id, "pitcher")
        if is_cached:
            print(f"[cache HIT] pitcher {pitcher_id} 2026")
            return pd.read_csv(path)
        print(f"[cache MISS] pitcher {pitcher_id} 2026 — pulling from pybaseball...")
        start, _ = SEASON_RANGES[2026]
        end = date.today().isoformat()
        df = pybaseball.statcast_pitcher(start, end, player_id=pitcher_id)
        _save(df, path)
        print(f"  Saved {len(df)} rows to {path}")

    else:
        raise ValueError(f"Unsupported season: {season}. Use 2025 or 2026.")

    print(f"  Shape: {df.shape}")
    if not df.empty:
        print(df[["game_date", "pitch_type", "release_speed", "player_name"]].head(3).to_string(index=False))
    return df


def get_batter_statcast(batter_id: int, season: int) -> pd.DataFrame:
    """
    Return Statcast pitch-level data for a batter (pitches seen, not thrown).
    Uses local CSV cache — never re-fetches 2025, refreshes 2026 once daily.
    """
    if season == 2025:
        path = _batter_cache_path(batter_id, 2025)
        if _is_cached_2025(path):
            print(f"[cache HIT] batter {batter_id} 2025")
            return pd.read_csv(path)
        print(f"[cache MISS] batter {batter_id} 2025 — pulling from pybaseball...")
        start, end = SEASON_RANGES[2025]
        df = pybaseball.statcast_batter(start, end, player_id=batter_id)
        _save(df, path)
        print(f"  Saved {len(df)} rows to {path}")

    elif season == 2026:
        is_cached, path = _is_cached_2026(batter_id, "batter")
        if is_cached:
            print(f"[cache HIT] batter {batter_id} 2026")
            return pd.read_csv(path)
        print(f"[cache MISS] batter {batter_id} 2026 — pulling from pybaseball...")
        start, _ = SEASON_RANGES[2026]
        end = date.today().isoformat()
        df = pybaseball.statcast_batter(start, end, player_id=batter_id)
        _save(df, path)
        print(f"  Saved {len(df)} rows to {path}")

    else:
        raise ValueError(f"Unsupported season: {season}. Use 2025 or 2026.")

    print(f"  Shape: {df.shape}")
    if not df.empty:
        print(df[["game_date", "pitch_type", "release_speed"]].head(3).to_string(index=False))
    return df


def _save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
