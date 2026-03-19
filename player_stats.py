"""
Leaderboard (Player Stats) module for Badminton Tournament Pro.
Provides standings by subgroup (Deciders / Chokers) and female-only standings.
Aligned with tournament standings: fixed 5 game slots, resolved clash keys, only recorded games.
Deciders table uses games 1,3,5 (indices 0,2,4); Chokers uses games 2,4 (indices 1,3).
Points: +2 per match win for the player who played; matches played; last 3 results (form).
"""
from typing import Any, Dict, List, Optional, Set

import pandas as pd

import fixtures as fx


DEFAULT_SUBGROUP_NAMES = {"subgroup1": "Deciders (0-5)", "subgroup2": "Chokers (6-15)"}

# Skill level ranges: Deciders = 0-5 only, Chokers = 6-15 only (must not overlap)
DECIDERS_SKILL_MIN, DECIDERS_SKILL_MAX = 0, 5
CHOKERS_SKILL_MIN, CHOKERS_SKILL_MAX = 6, 15

# Decider games vs Choker games in a 5-game meeting (same as Record a Clash)
DECIDER_GAME_INDICES = frozenset({0, 2, 4})
CHOKER_GAME_INDICES = frozenset({1, 3})

POINTS_PER_WIN = 2


def _get_player_skill(
    name: str,
    player_dict: Optional[Dict[str, Any]] = None,
    player_database: Optional[pd.DataFrame] = None,
) -> Optional[int]:
    """Resolve a player's skill_level from player dict or player_database."""
    if player_dict is not None:
        sl = player_dict.get("skill_level")
        if sl is not None:
            try:
                return int(sl)
            except (TypeError, ValueError):
                pass
    if player_database is not None and not player_database.empty and "name" in player_database.columns:
        try:
            row = player_database[player_database["name"].astype(str) == str(name)]
            if not row.empty and "skill_level" in row.columns:
                return int(row.iloc[0]["skill_level"])
        except (TypeError, ValueError):
            pass
    return None


def _is_decider(skill: Optional[int], lo: int = DECIDERS_SKILL_MIN, hi: int = DECIDERS_SKILL_MAX) -> bool:
    """True if skill is in Deciders range (0-5 by default)."""
    return skill is not None and lo <= skill <= hi


def _is_choker(skill: Optional[int], lo: int = CHOKERS_SKILL_MIN, hi: int = CHOKERS_SKILL_MAX) -> bool:
    """True if skill is in Chokers range (6-15 by default)."""
    return skill is not None and lo <= skill <= hi


def compute_player_stats_from_matches(
    tournament_data: Dict[str, List[Dict]],
    groups: Dict[str, List[str]],
    group_names: Optional[Dict[str, str]] = None,
    match_indices: Optional[Set[int]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Per-player stats from tournament_data. Every recorded game counts (live, same as Standings).
    Resolves clash_key to group keys like standings.
    match_indices: if set, only those game slots (e.g. Deciders 0,2,4 or Chokers 1,3).
    """
    group_names = group_names or {}
    gkeys = list(groups.keys())
    stats: Dict[str, Dict[str, Any]] = {}

    clash_keys = sorted(k for k in (tournament_data or {}).keys() if "_vs_" in k)
    for clash_key in clash_keys:
        ga, gb = fx.resolve_clash_group_keys(clash_key, gkeys, group_names)
        if not ga or not gb:
            parts = clash_key.split("_vs_", 1)
            if len(parts) != 2:
                continue
            ga, gb = parts[0].strip(), parts[1].strip()
        if ga not in groups or gb not in groups:
            continue

        five = fx.coerce_five_match_slots(tournament_data.get(clash_key))
        if fx.count_recorded_games(five) == 0:
            continue
        for mi, match in enumerate(five):
            if match_indices is not None and mi not in match_indices:
                continue
            winner = fx.normalize_match_winner(match)
            if winner is None:
                continue

            players_data = match.get("players") or {}
            g1_players = players_data.get("g1") or []
            g2_players = players_data.get("g2") or []
            if isinstance(g1_players, (list, tuple)):
                names_g1 = [str(n).strip() for n in g1_players if n]
            else:
                names_g1 = []
            if isinstance(g2_players, (list, tuple)):
                names_g2 = [str(n).strip() for n in g2_players if n]
            else:
                names_g2 = []

            if names_g1 and names_g2:
                for name in names_g1:
                    if name not in stats:
                        stats[name] = {"points": 0, "matches_played": 0, "last_3": []}
                    stats[name]["matches_played"] += 1
                    won = winner == "g1"
                    if won:
                        stats[name]["points"] += POINTS_PER_WIN
                    stats[name]["last_3"].append("W" if won else "L")
                for name in names_g2:
                    if name not in stats:
                        stats[name] = {"points": 0, "matches_played": 0, "last_3": []}
                    stats[name]["matches_played"] += 1
                    won = winner == "g2"
                    if won:
                        stats[name]["points"] += POINTS_PER_WIN
                    stats[name]["last_3"].append("W" if won else "L")
            else:
                roster_g1 = list(groups.get(ga, []))
                roster_g2 = list(groups.get(gb, []))
                for name in roster_g1:
                    if name not in stats:
                        stats[name] = {"points": 0, "matches_played": 0, "last_3": []}
                    stats[name]["matches_played"] += 1
                    if winner == "g1":
                        stats[name]["points"] += POINTS_PER_WIN
                        stats[name]["last_3"].append("W")
                    else:
                        stats[name]["last_3"].append("L")
                for name in roster_g2:
                    if name not in stats:
                        stats[name] = {"points": 0, "matches_played": 0, "last_3": []}
                    stats[name]["matches_played"] += 1
                    if winner == "g2":
                        stats[name]["points"] += POINTS_PER_WIN
                        stats[name]["last_3"].append("W")
                    else:
                        stats[name]["last_3"].append("L")

    for name in stats:
        stats[name]["last_3"] = stats[name]["last_3"][-3:]
    return stats


def _form_display(last_3: List[str]) -> str:
    """Convert last 3 W/L to green/red dots."""
    s = ""
    for r in last_3:
        s += "🟢" if r == "W" else "🔴"
    return s


def _player_row(
    p: Dict[str, Any],
    group_display: str,
    stats: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    name = p.get("name", "")
    s = stats.get(name, {"points": 0, "matches_played": 0, "last_3": []})
    return {
        "Team": group_display,
        "Name": name,
        "Points": s["points"],
        "Matches Played": s["matches_played"],
        "Recent form": _form_display(s["last_3"]),
    }


def get_deciders_standings(
    detailed_groups: Dict[str, Any],
    group_names: Dict[str, str],
    subgroup_names: Dict[str, str],
    tournament_data: Dict[str, List[Dict]],
    groups: Dict[str, List[str]],
    player_database: Optional[pd.DataFrame] = None,
    deciders_min: int = DECIDERS_SKILL_MIN,
    deciders_max: int = DECIDERS_SKILL_MAX,
) -> pd.DataFrame:
    """
    Leaderboard for Deciders (subgroup1) only. Only players with skill in [deciders_min, deciders_max] (default 0-5).
    Games 1, 3, 5 only. Males only.
    """
    stats = compute_player_stats_from_matches(
        tournament_data, groups, group_names, match_indices=set(DECIDER_GAME_INDICES)
    )
    rows: List[Dict[str, Any]] = []
    if detailed_groups:
        for group_key, subgroups in detailed_groups.items():
            group_display = group_names.get(group_key, group_key)
            for p in subgroups.get("subgroup1", {}).get("players", []):
                if p.get("gender") == "F":
                    continue
                skill = _get_player_skill(p.get("name", ""), p, player_database)
                if not _is_decider(skill, deciders_min, deciders_max):
                    continue
                rows.append(_player_row(p, group_display, stats))
    elif player_database is not None and not player_database.empty and groups is not None:
        for group_key, player_names in groups.items():
            if not player_names:
                continue
            group_display = group_names.get(group_key, group_key)
            subset = player_database[
                player_database["name"].isin(player_names)
                & (player_database["skill_level"] >= deciders_min)
                & (player_database["skill_level"] <= deciders_max)
                & (player_database["gender"] != "F")
            ]
            for _, row in subset.iterrows():
                p = {"name": row.get("name", row["name"])}
                rows.append(_player_row(p, group_display, stats))
    if not rows:
        return pd.DataFrame(
            columns=["Rank", "Team", "Name", "Points", "Matches Played", "Recent form"]
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["Points", "Name"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


def get_chokers_standings(
    detailed_groups: Dict[str, Any],
    group_names: Dict[str, str],
    subgroup_names: Dict[str, str],
    tournament_data: Dict[str, List[Dict]],
    groups: Dict[str, List[str]],
    player_database: Optional[pd.DataFrame] = None,
    chokers_min: int = CHOKERS_SKILL_MIN,
    chokers_max: int = CHOKERS_SKILL_MAX,
) -> pd.DataFrame:
    """
    Leaderboard for Chokers (subgroup2) only. Only players with skill in [chokers_min, chokers_max] (default 6-15).
    Games 2, 4 only.
    """
    stats = compute_player_stats_from_matches(
        tournament_data, groups, group_names, match_indices=set(CHOKER_GAME_INDICES)
    )
    rows = []
    if detailed_groups:
        for group_key, subgroups in detailed_groups.items():
            group_display = group_names.get(group_key, group_key)
            for p in subgroups.get("subgroup2", {}).get("players", []):
                skill = _get_player_skill(p.get("name", ""), p, player_database)
                if not _is_choker(skill, chokers_min, chokers_max):
                    continue
                rows.append(_player_row(p, group_display, stats))
    elif player_database is not None and not player_database.empty and groups is not None:
        for group_key, player_names in groups.items():
            if not player_names:
                continue
            group_display = group_names.get(group_key, group_key)
            subset = player_database[
                player_database["name"].isin(player_names)
                & (player_database["skill_level"] >= chokers_min)
                & (player_database["skill_level"] <= chokers_max)
            ]
            for _, row in subset.iterrows():
                p = {"name": row.get("name", row["name"])}
                rows.append(_player_row(p, group_display, stats))
    if not rows:
        return pd.DataFrame(
            columns=["Rank", "Team", "Name", "Points", "Matches Played", "Recent form"]
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["Points", "Name"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


def get_female_standings(
    detailed_groups: Optional[Dict[str, Any]],
    group_names: Dict[str, str],
    subgroup_names: Dict[str, str],
    tournament_data: Dict[str, List[Dict]],
    groups: Dict[str, List[str]],
    player_database: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Female-only leaderboard. Same columns; sorted by points descending.
    """
    stats = compute_player_stats_from_matches(
        tournament_data, groups, group_names, match_indices=None
    )
    rows: List[Dict[str, Any]] = []

    if detailed_groups:
        for group_key, subgroups in detailed_groups.items():
            group_display = group_names.get(group_key, group_key)
            for p in subgroups.get("subgroup1", {}).get("players", []):
                if p.get("gender") == "F":
                    rows.append(_player_row(p, group_display, stats))
            for p in subgroups.get("subgroup2", {}).get("players", []):
                if p.get("gender") == "F":
                    rows.append(_player_row(p, group_display, stats))
    elif player_database is not None and groups is not None:
        for group_key, player_names in groups.items():
            if not player_names:
                continue
            group_display = group_names.get(group_key, group_key)
            subset = player_database[
                player_database["name"].isin(player_names) & (player_database["gender"] == "F")
            ]
            for _, row in subset.iterrows():
                name = row.get("name", row["name"])
                p = {"name": name}
                rows.append(_player_row(p, group_display, stats))
    if not rows:
        return pd.DataFrame(
            columns=["Rank", "Team", "Name", "Points", "Matches Played", "Recent form"]
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["Points", "Name"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


def get_player_stats_summary(
    detailed_groups: Optional[Dict[str, Any]],
    group_names: Dict[str, str],
    subgroup_names: Dict[str, str],
    tournament_data: Dict[str, List[Dict]],
    groups: Dict[str, List[str]],
    player_database: Optional[pd.DataFrame] = None,
    deciders_min: int = DECIDERS_SKILL_MIN,
    deciders_max: int = DECIDERS_SKILL_MAX,
    chokers_min: int = CHOKERS_SKILL_MIN,
    chokers_max: int = CHOKERS_SKILL_MAX,
) -> Dict[str, Any]:
    """
    Return leaderboard summary: has_subgroups, deciders_df, chokers_df, female_df.
    Deciders tab shows only players with skill in [deciders_min, deciders_max] (0-5).
    Chokers tab shows only players with skill in [chokers_min, chokers_max] (6-15).
    """
    has_subgroups = bool(detailed_groups)
    female_df = get_female_standings(
        detailed_groups, group_names, subgroup_names, tournament_data, groups, player_database
    )

    deciders_df = get_deciders_standings(
        detailed_groups or {},
        group_names,
        subgroup_names,
        tournament_data,
        groups,
        player_database=player_database,
        deciders_min=deciders_min,
        deciders_max=deciders_max,
    )
    chokers_df = get_chokers_standings(
        detailed_groups or {},
        group_names,
        subgroup_names,
        tournament_data,
        groups,
        player_database=player_database,
        chokers_min=chokers_min,
        chokers_max=chokers_max,
    )

    return {
        "has_subgroups": has_subgroups,
        "deciders_df": deciders_df,
        "chokers_df": chokers_df,
        "female_df": female_df,
    }
