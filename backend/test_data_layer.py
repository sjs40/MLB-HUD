"""
Data layer verification script — run before proceeding to Phase 3.

Usage:
    cd backend
    python test_data_layer.py

Checks:
1. MLB Stats API schedule fetch for today
2. Statcast pitcher pull (2025 + 2026) with cache verification
3. Cache files exist on disk after pull
"""

import sys
import os
from pathlib import Path
from datetime import date

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data.mlb_api import get_schedule, get_schedule_two_days, search_players
from backend.data.statcast import get_pitcher_statcast, get_batter_statcast, PITCHER_CACHE

# ── Test 1: Schedule ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 1: Today's schedule")
print("="*60)
today = date.today().isoformat()
games = get_schedule(today)
print(f"  Games found for {today}: {len(games)}")
for g in games[:3]:
    print(f"  {g['away_team']} @ {g['home_team']}  —  game_id={g['game_id']}")
    print(f"    Away SP: {g['away_probable_pitcher']}  |  Home SP: {g['home_probable_pitcher']}")

# ── Test 2: Two-day schedule ──────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 2: Two-day schedule (today + tomorrow)")
print("="*60)
two_day = get_schedule_two_days()
print(f"  Total games: {len(two_day)}")

# ── Test 3: Player search ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 3: Player search ('Gerrit Cole')")
print("="*60)
results = search_players("Gerrit Cole")
for p in results[:3]:
    print(f"  {p['name']}  id={p['player_id']}  pos={p['position']}  hand={p['pitch_hand']}")

# ── Test 4: Statcast pitcher cache ────────────────────────────────────────────
# Using Gerrit Cole (player_id=543037) as a known stable test subject
PITCHER_ID = 543037
PITCHER_NAME = "Gerrit Cole"

print("\n" + "="*60)
print(f"TEST 4: Statcast pitcher pull — {PITCHER_NAME} (id={PITCHER_ID})")
print("="*60)

print("\n  [2025 pull]")
df_2025 = get_pitcher_statcast(PITCHER_ID, 2025)
print(f"  Rows: {len(df_2025)}  |  Columns: {len(df_2025.columns)}")
if not df_2025.empty:
    pitch_mix = df_2025["pitch_type"].value_counts(normalize=True).head(5)
    print("  Pitch mix:")
    for pt, pct in pitch_mix.items():
        print(f"    {pt}: {pct:.1%}")

print("\n  [2026 pull]")
df_2026 = get_pitcher_statcast(PITCHER_ID, 2026)
print(f"  Rows: {len(df_2026)}  |  Columns: {len(df_2026.columns)}")

# ── Test 5: Cache files on disk ───────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 5: Cache files on disk")
print("="*60)
cache_files = list(PITCHER_CACHE.glob(f"{PITCHER_ID}_*.csv"))
if cache_files:
    for f in cache_files:
        size_kb = f.stat().st_size / 1024
        print(f"  FOUND: {f.name}  ({size_kb:.1f} KB)")
else:
    print("  ERROR: No cache files found!")
    sys.exit(1)

print("\n" + "="*60)
print("ALL CHECKS PASSED — data layer is ready")
print("="*60 + "\n")
