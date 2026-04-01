"""
Pre-game narrative engine — generates 3–5 data-grounded storylines.

Template-based in v1 (no LLM). Matches pitcher weapons/vulnerabilities
against lineup matchup data to surface the most relevant angles.
"""

from typing import Optional


def generate_narratives(
    pitcher_name: str,
    pitcher_profile: dict,
    lineup_matchups: list[dict],
    blend_meta: Optional[dict] = None,
) -> list[str]:
    """
    Generate 3–5 key pre-game storylines.

    Args:
        pitcher_name: Display name of the starting pitcher
        pitcher_profile: Output of pitcher_profile.build_pitcher_profile()
        lineup_matchups: List of per-batter matchup dicts, each containing
                         batter name, handedness, and build_batter_matchup() output
        blend_meta: BlendMetadata dict (used for data quality disclaimers)

    Returns:
        List of narrative strings (3–5 items)
    """
    stories = []

    # ── Weapon vs. lineup storyline ───────────────────────────────────────────
    weapons = pitcher_profile.get("weapons_vulnerabilities", {}).get("weapons", [])
    if weapons:
        best_weapon = weapons[0]
        pt = best_weapon["pitch_type"]
        whiff = best_weapon.get("whiff_rate")
        xwoba = best_weapon.get("xwoba")

        # Find batters with high whiff rates on this pitch
        high_whiff_batters = []
        for bm in lineup_matchups:
            batter_name = bm.get("name", "Unknown")
            for entry in bm.get("swing_whiff_rates", []):
                if entry["pitch_type"] == pt and entry.get("whiff_rate") is not None:
                    if entry["whiff_rate"] >= 0.28:
                        high_whiff_batters.append((batter_name, entry["whiff_rate"]))

        if whiff and xwoba:
            base = (
                f"{pitcher_name}'s {pt} generates a {whiff:.0%} whiff rate "
                f"with a {xwoba:.3f} xwOBA allowed"
            )
            if high_whiff_batters:
                n = len(high_whiff_batters)
                stories.append(
                    f"{base} — {n} batter{'s' if n > 1 else ''} in this lineup "
                    f"have chase/whiff tendencies against that pitch type."
                )
            else:
                stories.append(f"{base} — key weapon for today.")
        elif whiff:
            stories.append(
                f"{pitcher_name}'s {pt} is the primary strikeout pitch "
                f"at a {whiff:.0%} whiff rate."
            )

    # ── Vulnerability storyline ───────────────────────────────────────────────
    vulns = pitcher_profile.get("weapons_vulnerabilities", {}).get("vulnerabilities", [])
    if vulns:
        worst = vulns[0]
        pt = worst["pitch_type"]
        xwoba = worst.get("xwoba")
        if xwoba and xwoba > 0.350:
            # Find batters who could exploit it
            strong_batters = []
            for bm in lineup_matchups:
                batter_name = bm.get("name", "Unknown")
                for entry in bm.get("xwoba_by_pitch_type", []):
                    if entry["pitch_type"] == pt and entry.get("xwoba") is not None:
                        if entry["xwoba"] > 0.340 and not entry.get("small_sample_flag"):
                            strong_batters.append(batter_name)

            if strong_batters:
                batter_list = ", ".join(strong_batters[:3])
                stories.append(
                    f"{pitcher_name}'s {pt} is a vulnerability at {xwoba:.3f} xwOBA — "
                    f"{batter_list} have strong numbers against that pitch type."
                )
            else:
                stories.append(
                    f"{pitcher_name}'s {pt} carries a {xwoba:.3f} xwOBA allowed — "
                    f"watch for batters to target it."
                )

    # ── Velo progression storyline ────────────────────────────────────────────
    progression = pitcher_profile.get("game_progression", [])
    velo_flags = [p for p in progression if p.get("velo_flag")]
    if velo_flags:
        flag = velo_flags[0]
        drop = flag.get("velo_drop", 0)
        band = flag.get("inning_band")
        stories.append(
            f"{pitcher_name} shows a {drop:.1f} mph velocity decline entering "
            f"innings {band} — performance may change if the game goes deep."
        )

    # ── Profile change alert storyline ───────────────────────────────────────
    # Profile change alerts are passed through pitcher_profile if the calling
    # layer adds them; check for the key
    profile_alerts = pitcher_profile.get("profile_change_alerts", [])
    if profile_alerts:
        top_alert = profile_alerts[0]
        pt = top_alert["pitch_type"]
        delta = top_alert["delta"]
        direction = top_alert["direction"]
        stories.append(
            f"Profile Change Alert: {pitcher_name}'s {pt} usage is "
            f"{abs(delta):.1f}pp {direction} from 2025 — may indicate an "
            f"offseason adjustment, new pitch, or changed approach."
        )

    # ── Platoon split storyline ───────────────────────────────────────────────
    platoon = pitcher_profile.get("platoon_splits", {})
    vs_lhh = platoon.get("vs_LHH", [])
    vs_rhh = platoon.get("vs_RHH", [])

    lhh_xwoba_vals = [e["xwoba"] for e in vs_lhh if e.get("xwoba") and not e.get("small_sample")]
    rhh_xwoba_vals = [e["xwoba"] for e in vs_rhh if e.get("xwoba") and not e.get("small_sample")]

    if lhh_xwoba_vals and rhh_xwoba_vals:
        avg_lhh = sum(lhh_xwoba_vals) / len(lhh_xwoba_vals)
        avg_rhh = sum(rhh_xwoba_vals) / len(rhh_xwoba_vals)
        diff = abs(avg_lhh - avg_rhh)
        if diff > 0.040:
            stronger_side = "LHH" if avg_lhh > avg_rhh else "RHH"
            weaker_xwoba = max(avg_lhh, avg_rhh)
            stories.append(
                f"{pitcher_name} has a meaningful platoon split — "
                f"more vulnerable to {stronger_side} ({weaker_xwoba:.3f} xwOBA). "
                f"Check the lineup for handedness matchups."
            )

    # ── Zone overlap storyline ────────────────────────────────────────────────
    high_overlap_batters = []
    for bm in lineup_matchups:
        zone_vuln = bm.get("zone_vulnerability", {})
        overlap = zone_vuln.get("overlap_zones", [])
        if len(overlap) >= 2:
            high_overlap_batters.append((bm.get("name", "Unknown"), len(overlap)))

    if high_overlap_batters:
        high_overlap_batters.sort(key=lambda x: x[1], reverse=True)
        names = ", ".join(b[0] for b in high_overlap_batters[:3])
        n = len(high_overlap_batters)
        stories.append(
            f"{n} batter{'s' if n > 1 else ''} in this lineup have weak zones "
            f"that overlap with {pitcher_name}'s primary locations: {names}."
        )

    # ── Data quality disclaimer (if heavily 2025-weighted) ───────────────────
    if blend_meta and blend_meta.get("weight_2025", 0) >= 0.60:
        n_2026 = blend_meta.get("n_2026_pitches", 0)
        stories.append(
            f"Note: 2026 sample is small ({n_2026} pitches). "
            f"Analysis is heavily weighted toward 2025 full-season data."
        )

    # Return 3–5 stories; cap at 5, ensure at least 1
    return stories[:5] if stories else [
        f"Insufficient data to generate pre-game storylines for {pitcher_name}."
    ]
