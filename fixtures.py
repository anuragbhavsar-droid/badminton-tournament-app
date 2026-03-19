"""
Fixtures & results domain: completed clashes and upcoming fixtures from tournament_data + optional schedule.
"""
from __future__ import annotations

import copy
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _display(group_names: Dict[str, str], key: str) -> str:
    return str(group_names.get(key, key))


def canonical_clash_key(g1: Any, g2: Any) -> str:
    """Stable storage key for a pair (order of Group 1 / Group 2 does not matter)."""
    a, b = sorted([str(g1).strip(), str(g2).strip()], key=str)
    return f"{a}_vs_{b}"


def _all_td_keys_for_pair(tournament_data: Dict[str, Any], g1: Any, g2: Any) -> List[str]:
    s1, s2 = str(g1).strip(), str(g2).strip()
    out: List[str] = []
    for k in list((tournament_data or {}).keys()):
        if "_vs_" not in k:
            continue
        parts = k.split("_vs_", 1)
        if len(parts) != 2:
            continue
        if {parts[0].strip(), parts[1].strip()} == {s1, s2}:
            out.append(k)
    return out


def flip_match_row_g1_g2(m: dict) -> dict:
    """Swap g1/g2 orientation (same game, other team listed first in clash key)."""
    if not m:
        return m
    out = copy.deepcopy(m)
    w = normalize_match_winner(m)
    if w == "g1":
        out["winner"] = "g2"
    elif w == "g2":
        out["winner"] = "g1"
    pl = m.get("players") or {}
    out["players"] = {
        "g1": list(pl.get("g2") or []),
        "g2": list(pl.get("g1") or []),
    }
    ss = m.get("set_scores") or {}

    def sw(t: Any) -> Any:
        if isinstance(t, (list, tuple)) and len(t) >= 2:
            return (t[1], t[0])
        return t

    out["set_scores"] = {sn: sw(ss.get(sn)) for sn in ("set1", "set2", "set3")}
    return out


def migrate_clash_pair_to_canonical(tournament_data: Dict[str, Any], g1: Any, g2: Any) -> str:
    """
    Merge any legacy keys (A_vs_B and B_vs_A) into one canonical key; flip rows when needed.
    """
    td = tournament_data
    canon = canonical_clash_key(g1, g2)
    left = canon.split("_vs_", 1)[0]
    keys = _all_td_keys_for_pair(td, g1, g2)
    if not keys:
        return canon
    merged = coerce_five_match_slots(td.get(canon) if canon in keys else None)
    for k in keys:
        slots = coerce_five_match_slots(td.get(k))
        sk_left = k.split("_vs_", 1)[0]
        need_flip = sk_left != left
        for i in range(5):
            m = slots[i]
            if normalize_match_winner(m) is None:
                continue
            row = flip_match_row_g1_g2(m) if need_flip else copy.deepcopy(m)
            if normalize_match_winner(merged[i]) is None:
                merged[i] = row
            else:
                t_old = (merged[i].get("match_info") or {}).get("timestamp") or ""
                t_new = (row.get("match_info") or {}).get("timestamp") or ""
                if t_new > t_old:
                    merged[i] = row
    for k in keys:
        td.pop(k, None)
    td[canon] = merged
    return canon


def find_clash_key(g1: str, g2: str, tournament_data: Dict[str, Any]) -> Optional[str]:
    if not tournament_data:
        return None
    canon = canonical_clash_key(g1, g2)
    if canon in tournament_data and tournament_data[canon]:
        return canon
    for a, b in ((g1, g2), (g2, g1)):
        k = f"{a}_vs_{b}"
        if k in tournament_data and tournament_data[k]:
            return k
    return None


def normalize_match_winner(m: Optional[dict]) -> Optional[str]:
    """Return 'g1' or 'g2' from stored match row."""
    if not m:
        return None
    w = m.get("winner")
    if w in ("g1", "g2"):
        return w
    if w is None:
        return None
    s = str(w).strip().lower()
    if s in ("g1", "1", "team1", "home"):
        return "g1"
    if s in ("g2", "2", "team2", "away"):
        return "g2"
    return None


def is_clash_fully_recorded(matches: List[dict]) -> bool:
    """All 5 games recorded with a valid winner (clash result is final)."""
    if not matches:
        return False
    for i in range(5):
        if i >= len(matches):
            return False
        if normalize_match_winner(matches[i]) is None:
            return False
    return True


def resolve_clash_group_keys(
    clash_key: str,
    group_keys: List[str],
    group_names: Dict[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Map a tournament clash_key to internal group keys (handles display names in key).
    """
    if "_vs_" not in clash_key:
        return None, None
    left, right = clash_key.split("_vs_", 1)

    def resolve_segment(segment: str) -> Optional[str]:
        s = (segment or "").strip()
        for k in group_keys:
            if str(k) == s:
                return k
        for k in group_keys:
            if _display(group_names, k) == s:
                return k
        return None

    a = resolve_segment(left)
    b = resolve_segment(right)
    if a and b:
        return a, b
    return None, None


def coerce_five_match_slots(matches: Optional[List]) -> List[dict]:
    """Fixed 5 slots for one group-vs-group clash (empty dict = not played)."""
    m = list(matches or [])
    while len(m) < 5:
        m.append({})
    out = []
    for i in range(5):
        x = m[i] if i < len(m) else {}
        out.append(dict(x) if isinstance(x, dict) else {})
    return out


def count_recorded_games(five_slots: List[dict]) -> int:
    return sum(1 for x in five_slots if normalize_match_winner(x) is not None)


def _lineup_name_count(side_list: Any) -> int:
    if not side_list:
        return 0
    n = 0
    for x in side_list:
        s = (x.get("name", x) if isinstance(x, dict) else str(x) or "").strip()
        if s:
            n += 1
    return n


def has_lineup(m: dict) -> bool:
    """True if canonical players has 2 names per side (planned or recorded)."""
    if not m or not isinstance(m, dict):
        return False
    pl = m.get("players") or {}
    return _lineup_name_count(pl.get("g1")) >= 2 and _lineup_name_count(pl.get("g2")) >= 2


def is_planned_only(m: dict) -> bool:
    """Lineup saved ahead of time; no result yet — reuse in Record a Clash for scores only."""
    return has_lineup(m) and normalize_match_winner(m) is None


def clash_winner_group_key(
    matches: List[dict], g1_key: str, g2_key: str
) -> Optional[str]:
    """Which group key won the clash (must be fully recorded)."""
    if not is_clash_fully_recorded(matches):
        return None
    g1w = sum(1 for m in matches[:5] if normalize_match_winner(m) == "g1")
    g2w = sum(1 for m in matches[:5] if normalize_match_winner(m) == "g2")
    if g1w > g2w:
        return g1_key
    if g2w > g1w:
        return g2_key
    return None


def _pair_slot_in_schedule(
    g1: str,
    g2: str,
    schedule: List[dict],
    group_keys: List[str],
    group_names: Dict[str, str],
) -> Optional[Tuple[str, str, int]]:
    """Earliest schedule row for this pair: (date, start_time, round_number)."""

    def label_to_key(label: Any) -> Optional[str]:
        s = str(label).strip()
        for k in group_keys:
            if _display(group_names, k) == s or str(k) == s:
                return k
        return None

    best: Optional[Tuple[str, str, int, str]] = None
    for row in schedule:
        k1 = label_to_key(row.get("group1"))
        k2 = label_to_key(row.get("group2"))
        if k1 is None or k2 is None:
            continue
        if {k1, k2} != {g1, g2}:
            continue
        d = str(row.get("date") or "")
        t = str(row.get("start_time") or "")
        r = int(row.get("round_number") or 0)
        sort_key = f"{d} {t}"
        if best is None or sort_key < best[3]:
            best = (d, t, r, sort_key)
    if best is None:
        return None
    return (best[0], best[1], best[2])


def _last_game_timestamp(matches: List[dict]) -> str:
    ts: List[str] = []
    for m in matches[:5]:
        info = m.get("match_info") or {}
        t = info.get("timestamp")
        if t:
            ts.append(str(t))
    return max(ts) if ts else "—"


def build_completed_and_upcoming(
    groups: Dict[str, List],
    group_names: Dict[str, str],
    tournament_data: Dict[str, List[dict]],
    tournament_schedule: Optional[List[dict]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (completed_df, upcoming_df) for Standings-style display."""
    group_keys = sorted([k for k in groups.keys() if groups.get(k)])
    pairs = list(combinations(group_keys, 2))
    sched = tournament_schedule or []

    completed_rows: List[dict] = []
    upcoming_rows: List[dict] = []

    for g1, g2 in pairs:
        ck = canonical_clash_key(g1, g2)
        alt = find_clash_key(g1, g2, tournament_data or {})
        if alt and alt != ck:
            ck = alt
        matches = coerce_five_match_slots((tournament_data or {}).get(ck, []))
        n1, n2 = _display(group_names, g1), _display(group_names, g2)
        slot = _pair_slot_in_schedule(g1, g2, sched, group_keys, group_names)
        sched_label = f"{slot[0]} · {slot[1]}" if slot else "—"
        rnd = slot[2] if slot else None

        if is_clash_fully_recorded(matches):
            g1w = sum(1 for m in matches[:5] if m.get("winner") == "g1")
            g2w = sum(1 for m in matches[:5] if m.get("winner") == "g2")
            winner_name = n1 if g1w > g2w else n2
            games = f"{max(g1w, g2w)}–{min(g1w, g2w)}"
            completed_rows.append(
                {
                    "Last recorded": _last_game_timestamp(matches[:5]),
                    "Team A": n1,
                    "Team B": n2,
                    "Winner": winner_name,
                    "Games (wins)": games,
                    "Round": rnd if rnd else "—",
                    "Scheduled window": sched_label,
                    "_g1": g1,
                    "_g2": g2,
                    "_ck": ck,
                }
            )
        else:
            partial = count_recorded_games(matches)
            if partial > 0:
                status = f"In progress ({partial}/5 games)"
            else:
                status = "Scheduled"
            upcoming_rows.append(
                {
                    "Scheduled": sched_label,
                    "Round": rnd if rnd else "—",
                    "Team A": n1,
                    "Team B": n2,
                    "Status": status,
                    "_g1": g1,
                    "_g2": g2,
                    "_ck": ck,
                }
            )

    cdf = pd.DataFrame(completed_rows)
    if not cdf.empty:
        cdf = cdf.sort_values("Last recorded", ascending=False).reset_index(drop=True)

    udf = pd.DataFrame(upcoming_rows)
    if not udf.empty:
        udf["_sort"] = udf["Scheduled"].apply(
            lambda x: x if x and str(x) != "—" else "9999-12-31 99:99"
        )
        udf = udf.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    return cdf, udf


def clash_games_detail_df(
    matches: List[dict],
    g1_key: str,
    g2_key: str,
    group_names: Dict[str, str],
    subgroup_names: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Per-game breakdown for one clash."""
    subgroup_names = subgroup_names or {}
    dec = subgroup_names.get("subgroup1", "Deciders")
    chok = subgroup_names.get("subgroup2", "Chokers")
    pool = [dec, chok, dec, chok, dec]
    n1, n2 = _display(group_names, g1_key), _display(group_names, g2_key)
    def _player_names(pl_list: list) -> str:
        if not pl_list:
            return "—"
        return ", ".join(
            (p.get("name", p) if isinstance(p, dict) else str(p)) for p in pl_list
        )

    rows = []
    for i, m in enumerate(matches[:5]):
        w = m.get("winner")
        wd = n1 if w == "g1" else n2 if w == "g2" else "—"
        pl = m.get("players") or {}
        g1_pl = _player_names(pl.get("g1") or [])
        g2_pl = _player_names(pl.get("g2") or [])
        rows.append(
            {
                "Game": i + 1,
                "Pool": pool[i] if i < 5 else "—",
                "Winner": wd,
                "Score": m.get("score_display", "—"),
                "Match pts": m.get("points", "—"),
                f"Players ({n1})": g1_pl,
                f"Players ({n2})": g2_pl,
            }
        )
    return pd.DataFrame(rows)
