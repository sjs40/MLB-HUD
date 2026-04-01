# MLB-HUD — Implementation Plan

## Overview

A baseball analytics web app providing deep pitcher vs. batter matchup breakdowns using pitch-level Statcast data. Covers pitch mix, location tendencies, platoon/count patterns, game progression, and per-batter edge scoring — for today's slate, any ad hoc matchup, and live games in progress.

**Pitch sequencing analysis is explicitly out of scope for v1.** The codebase must be structured to allow it to be added later without major refactoring (stub out `pitch_sequencing.py`).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React + Tailwind CSS |
| Data | pybaseball + MLB Stats API (no paid APIs) |
| Charts | Recharts (line/bar), SVG (strike zone heatmaps) |
| Caching | Local file cache — CSV keyed by player ID + season + date |

All visualizations must be browser-native. No matplotlib, no server-side image generation.

---

## Data Sources

- **pybaseball** — Statcast pitch-level data for pitchers and batters
- **MLB Stats API** (free, no key required) — schedules, probable pitchers, lineups, live game feed
- **Projected lineups** — when official lineup not yet posted, derive from last 10-game lineup history via MLB Stats API. Display with explicit `PROJECTED` label

---

## 2025 / 2026 Data Blending

It is early in the 2026 MLB season. Small 2026 samples make pitch-level analysis unreliable on their own. Blend 2025 full-season data as a prior using the following rules:

### Blending Weights

| 2026 Pitcher Pitches | 2026 Batter PA | 2026 Weight | 2025 Weight |
|---|---|---|---|
| < 300 | < 100 | 40% | 60% |
| 300 – 600 | 100 – 250 | 60% | 40% |
| 600 – 900 | 250 – 400 | 80% | 20% |
| 900+ | 400+ | 100% | 0% (optional) |

### Blending Rules

- Always display data source prominently in the UI: e.g., *"Analysis based on 203 2026 pitches + 2025 full season (blended 40/60)"*
- Flag **Profile Change Alert** if a pitcher's 2026 pitch mix deviates from 2025 by more than **8 percentage points** on any pitch type — may indicate offseason adjustment, new pitch, or injury
- **2025 data is static** — cache once per player ID, never re-fetch
- **2026 data** — refresh once daily maximum
- Cache 2025 and 2026 separately

---

## App Modes

### Mode 1: Game Slate View
- Display today's and tomorrow's scheduled games
- Show per game: teams, probable pitchers, game time
- Click any game to drill into the pre-game analysis

---

### Mode 2: Pre-Game Deep Dive

Full matchup breakdown for a selected game.

#### Pitcher Profile *(blended Statcast)*

| Feature | Detail |
|---|---|
| Pitch mix | % usage, avg velo, spin rate, horizontal + vertical break per pitch type |
| Location heatmaps | SVG strike zone grids, separate views vs. LHH and RHH per pitch type |
| Count tendencies | Primary pitch in hitter-friendly counts (2-0, 3-1) vs. pitcher-friendly counts (0-2, 1-2); what he uses to get ahead vs. put batters away |
| Platoon splits | xwOBA allowed vs. LHH and RHH per pitch type (flag if sample < 50 pitches) |
| Game progression | Velo, pitch mix, whiff rate across innings 1–3 / 4–6 / 7+; visualized as line chart; flag meaningful drops |
| Weapons | Pitches with best run value / whiff rate |
| Vulnerabilities | Pitches with high xwOBA allowed / low whiff rate |

#### Lineup Matchup Matrix

For each batter (official if posted, projected if not — labeled clearly):

| Feature | Detail |
|---|---|
| xwOBA by pitch type | Blended career + current season vs. each of pitcher's primary pitch types |
| Swing + whiff rate | Per pitch type |
| Zone vulnerability | Where in zone is batter weak? Does it overlap with pitcher's primary locations? |
| Count leverage | Performance in hitter's counts vs. pitcher's counts |
| Matchup edge score | Composite signal — must show component inputs, not just a number |
| Small sample gate | If < 50 pitches seen for any split: display the data, flag it clearly, do not let it dominate the edge score |

#### Pre-Game Narrative

3–5 auto-generated key storylines grounded in actual data. Examples:
- *"Pitcher's slider holds a .198 xwOBA vs. RHH but lives down-and-away — three RHH in this lineup have elite chase rates on that location"*
- *"Pitcher shows meaningful velo decline after inning 5 — watch if this game goes deep"*

---

### Mode 3: Live Game Tracker

- Poll MLB Stats API live game feed every **60 seconds** during active games
- Track actual pitch mix, velocity, and location vs. blended season norms
- After each plate appearance: show actual outcome vs. pre-game xwOBA expectation
- Deviation flags: e.g., *"Pitcher has thrown fastball 65% tonight vs. 48% blended norm"*, *"Velo down 1.8 mph through 4 innings"*
- Running assumptions check: which pre-game matchup calls are proving correct or incorrect, and why

---

### Mode 4: Ad Hoc Batter vs. Pitcher Analyzer

- Standalone tool accessible from the nav, independent of any scheduled game
- User searches any pitcher and any batter by name
- Runs the full matchup analysis: pitch mix, location, platoon splits, zone vulnerability, edge score, narrative
- Same 2025/2026 blending logic applies
- Use cases: non-today matchups, reliever analysis, prop research, historical curiosity

---

## Build Order

Build sequentially. Do not skip ahead.

### Phase 1 — Data Layer
- Build and test all data fetching functions:
  - MLB Stats API: today's schedule, probable pitchers, lineup endpoints
  - pybaseball: Statcast pitcher and batter pulls for both 2025 and 2026
- Implement local CSV caching:
  - Key: `player_id + season + date`
  - 2025: cache permanently, never re-fetch
  - 2026: refresh once daily
- Print sample data shapes and confirm data quality before proceeding
- **Do not proceed to Phase 2 until caching is verified working correctly**

### Phase 2 — Blending Engine
- Implement 2025/2026 weighted blend logic as a standalone module (`data_blending.py`)
- Implement Profile Change Alert (>8pp deviation on any pitch type)
- Unit test blend weights across sample threshold boundaries

### Phase 3 — Pitcher Analysis Engine
- Pitch mix aggregation and run value calculation
- Location heatmap data (zone grid aggregation by pitch type and handedness)
- Count tendency analysis (hitter-friendly vs. pitcher-friendly counts)
- Game progression patterns (velo, whiff rate, mix by inning band)
- Weapons and vulnerability identification

### Phase 4 — Batter Matchup Engine
- xwOBA by pitch type (blended)
- Swing rate and whiff rate by pitch type
- Zone vulnerability mapping and overlap detection
- Count leverage calculation
- Matchup edge score with component transparency
- Small sample flagging (< 50 pitch threshold)

### Phase 5 — FastAPI Endpoints
- `GET /schedule` — today's and tomorrow's games
- `GET /game/{game_id}/pregame` — full pre-game analysis
- `GET /game/{game_id}/live` — live game state and deviation flags
- `GET /adhoc` — ad hoc pitcher vs. batter analysis
- `GET /players/search` — player name search for ad hoc mode

### Phase 6 — React Frontend
Build in this order:
1. Slate view (game cards)
2. Game drill-down navigation
3. Pitcher profile components (pitch mix, location SVG heatmaps, progression chart)
4. Lineup matchup matrix and edge score display
5. Pre-game narrative section
6. Ad hoc analyzer UI (search + results)

### Phase 7 — Live Polling Layer
- Implement 60-second polling against MLB Stats API live feed
- Pitch mix and velo deviation tracking
- PA-by-PA outcome vs. expectation display
- Running assumptions check panel

---

## Hard Constraints

| Constraint | Rule |
|---|---|
| Caching | pybaseball pulls are slow — local CSV cache is mandatory. Never re-fetch 2025 data. 2026 refreshes once daily max |
| Lineup state | "Lineup not posted" must be handled gracefully — show projected lineup with explicit PROJECTED label |
| Visualizations | All browser-native (SVG + Recharts). No matplotlib, no server-side PNG generation |
| Edge score transparency | Every edge score must display its component inputs. A batter cannot score high or low without the UI explaining why |
| Small samples | Splits with < 50 pitches: display with flag, do not hide, do not allow to dominate edge score |
| Pitch sequencing | Out of scope for v1. Stub out `pitch_sequencing.py` with docstrings describing what it will eventually do |

---

## Caching Architecture

```
cache/
  statcast/
    pitcher/
      {pitcher_id}_2025.csv        ← static, never re-fetch
      {pitcher_id}_2026_{date}.csv ← refresh daily
    batter/
      {batter_id}_2025.csv
      {batter_id}_2026_{date}.csv
  lineups/
    {team_id}_{date}.json          ← recent lineup history for projections
```

---

## Project File Structure (Target)

```
MLB-HUD/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── routers/
│   │   ├── schedule.py
│   │   ├── pregame.py
│   │   ├── live.py
│   │   └── adhoc.py
│   ├── data/
│   │   ├── mlb_api.py             ← MLB Stats API fetching
│   │   ├── statcast.py            ← pybaseball fetching + caching
│   │   └── data_blending.py       ← 2025/2026 blend logic
│   ├── analysis/
│   │   ├── pitcher_profile.py     ← pitch mix, location, progression
│   │   ├── batter_matchup.py      ← xwOBA, edge score, vulnerability
│   │   ├── narrative.py           ← auto-generated storylines
│   │   └── pitch_sequencing.py    ← STUB — v2 feature
│   └── cache/                     ← local CSV/JSON cache
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SlateView.jsx
│   │   │   ├── PitcherProfile.jsx
│   │   │   ├── StrikeZoneHeatmap.jsx  ← SVG
│   │   │   ├── LineupMatrix.jsx
│   │   │   ├── EdgeScore.jsx
│   │   │   ├── LiveTracker.jsx
│   │   │   └── AdHocAnalyzer.jsx
│   │   └── App.jsx
│   └── package.json
└── README.md
```

---

## Key Risks and Watch-Outs

| Risk | Mitigation |
|---|---|
| pybaseball full-season pull is slow (2–5 min per pitcher first run) | Cache in Phase 1 before any analysis; do not re-pull |
| 2026 sample is tiny early in season | Blending engine handles this; always surface sample size in UI |
| Pitcher changed profile from 2025 (new pitch, new team, injury) | Profile Change Alert flag surfaces this explicitly |
| MLB Stats API lineup endpoint empty until ~1–2 hrs before first pitch | Graceful fallback to projected lineup with PROJECTED label |
| SVG strike zone heatmaps are complex to build precisely | Use zone grid approximation (9-zone or 25-zone) in v1; refine later |
| Live polling reliability | Wrap in error handling; show "last updated" timestamp; fail gracefully |

---

## Out of Scope (v1)

- Pitch sequencing analysis (count-to-count transitions, pitch-to-pitch chains) — stubbed for v2
- Paid data APIs (e.g., Baseball Savant premium, MarineTraffic equivalent)
- User accounts or saved analyses
- Mobile-optimized layout (design for desktop first)
- Historical game replay

---

*Last updated: April 2026*