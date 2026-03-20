"""
Database layer for Badminton Tournament Manager.
Uses Supabase (PostgreSQL). Set SUPABASE_URL and SUPABASE_SERVICE_KEY in:
  - .env (local), and/or
  - .streamlit/secrets.toml, and/or
  - Streamlit Community Cloud → App Settings → Secrets
Run supabase_schema.sql in Supabase SQL Editor once to create tables.
Persists full match information per game in tournament_matches (data_json).
"""
import json
import os
import random
from typing import Any, Dict, List, Tuple

import pandas as pd


def _secret(name: str) -> str:
    """Read credential from env first, then Streamlit secrets (deploy / local secrets.toml)."""
    v = os.getenv(name, "").strip()
    if v:
        return v
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return ""


def get_supabase_credentials() -> Tuple[str, str]:
    """Return (url, service_role_key) for Supabase."""
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_SERVICE_KEY") or _secret("SUPABASE_KEY")
    return url, key


def _normalize_match_for_db(m: Any, match_index: int) -> Dict[str, Any]:
    """
    Return a JSON-serializable dict for one game slot so the DB stores complete clash information.
    Converts set_scores tuples to lists, adds match_type (Decider/Choker), keeps players and match_info.
    """
    if not m or not isinstance(m, dict):
        return {}
    w = m.get("winner")
    if w not in ("g1", "g2"):
        return {}
    out = {
        "winner": str(w),
        "winner_display": str(m.get("winner_display", "")),
        "points": int(m.get("points", 0)),
        "score_display": str(m.get("score_display", "")),
        "match_type": "Decider" if match_index in (0, 2, 4) else "Choker",
        "set_scores": {},
        "players": {"g1": [], "g2": []},
        "match_info": dict(m.get("match_info") or {}),
    }
    for sn in ("set1", "set2", "set3"):
        s = m.get("set_scores") or {}
        val = s.get(sn)
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            out["set_scores"][sn] = [int(val[0]) if val[0] is not None else 0, int(val[1]) if val[1] is not None else 0]
        else:
            out["set_scores"][sn] = [0, 0]
    pl = m.get("players") or {}
    for side in ("g1", "g2"):
        arr = pl.get(side) or []
        out["players"][side] = [
            (x.get("name", x) if isinstance(x, dict) else str(x)) for x in arr
        ]
    return out


def _normalize_planned_slot_for_db(m: Any, match_index: int) -> Dict[str, Any]:
    """Persist planned lineup + venue (no winner yet) for tournament_matches.data_json."""
    import fixtures as _fx

    if not m or not isinstance(m, dict):
        return {}
    if _fx.normalize_match_winner(m) is not None:
        return {}
    if not _fx.has_lineup(m):
        return {}
    pl = m.get("players") or {}
    out: Dict[str, Any] = {
        "planned": True,
        "match_type": "Decider" if match_index in (0, 2, 4) else "Choker",
        "players": {"g1": [], "g2": []},
        "fixture": dict(m.get("fixture") or {}),
    }
    for side in ("g1", "g2"):
        arr = pl.get(side) or []
        out["players"][side] = [
            (x.get("name", x) if isinstance(x, dict) else str(x)) for x in arr if x
        ]
    return out


def _normalize_slot_for_db(m: Any, match_index: int) -> Dict[str, Any]:
    """One DB row per game: full result, or planned lineup, or empty."""
    if not m or not isinstance(m, dict):
        return {}
    if m.get("winner") in ("g1", "g2"):
        return _normalize_match_for_db(m, match_index)
    return _normalize_planned_slot_for_db(m, match_index)

# Lazy init Supabase client
_supabase = None


def _get_supabase():
    """Get or create Supabase client. Requires SUPABASE_URL and SUPABASE_SERVICE_KEY."""
    global _supabase
    if _supabase is not None:
        return _supabase
    url, key = get_supabase_credentials()
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) must be set in .env and/or "
            "Streamlit secrets (.streamlit/secrets.toml or Cloud). "
            "Get values from Supabase Dashboard → Project Settings → API."
        )
    # Optional: disable SSL verification (e.g. for self-signed / corporate certificates)
    verify_raw = _secret("SUPABASE_VERIFY_SSL") or os.getenv("SUPABASE_VERIFY_SSL", "true")
    verify_ssl = verify_raw.strip().lower() not in ("false", "0", "no")
    from supabase import create_client
    if verify_ssl:
        _supabase = create_client(url, key)
    else:
        try:
            from supabase import ClientOptions
            _supabase = create_client(url, key, options=ClientOptions(httpx_options={"verify": False}))
        except (ImportError, TypeError, AttributeError):
            import httpx
            from supabase import ClientOptions
            _supabase = create_client(url, key, options=ClientOptions(httpx_client=httpx.Client(verify=False)))
    return _supabase


def init_db() -> None:
    """No-op: tables are created by running supabase_schema.sql in Supabase SQL Editor."""
    pass


def compute_standings_rows(
    groups: Dict[str, List],
    group_names: Dict[str, str],
    tournament_data: Dict[str, List[Dict]],
) -> List[Dict[str, Any]]:
    """
    One row per group key matching Standings & Qualifiers columns.
    Aligns with calculate_standings: +2 Points and +1 Clash won per game won;
    clash keys resolved via display names.
    """
    import fixtures as _fx

    gkeys = list(groups.keys())
    stats: Dict[str, Dict[str, int]] = {}
    for gk in groups.keys():
        stats[gk] = {
            "matches_played": 0,
            "clash_won": 0,
            "points": 0,
            "sets_won": 0,
            "sets_lost": 0,
            "rally_points_won": 0,
            "rally_points_lost": 0,
            "total_match_points": 0,
        }

    pair_best = {}
    for clash_key, matches in (tournament_data or {}).items():
        if "_vs_" not in clash_key:
            continue
        raw = _fx.coerce_five_match_slots(matches)
        if _fx.count_recorded_games(raw) == 0:
            continue
        g1_key, g2_key = _fx.resolve_clash_group_keys(clash_key, gkeys, group_names)
        if not g1_key or not g2_key or g1_key not in stats or g2_key not in stats:
            continue
        pair = frozenset({g1_key, g2_key})
        cand = (g1_key, g2_key, raw)
        if pair not in pair_best:
            pair_best[pair] = cand
        else:
            _o1, _o2, oldm = pair_best[pair]
            nf, of = _fx.is_clash_fully_recorded(raw), _fx.is_clash_fully_recorded(oldm)
            nc, oc = _fx.count_recorded_games(raw), _fx.count_recorded_games(oldm)
            if nf and not of:
                pair_best[pair] = cand
            elif of and not nf:
                pass
            elif nc > oc:
                pair_best[pair] = cand

    for _pair, (g1_key, g2_key, matches) in pair_best.items():
        # Live update: count every meeting that has at least one recorded game
        stats[g1_key]["matches_played"] += 1
        stats[g2_key]["matches_played"] += 1

        for m in matches:
            w = _fx.normalize_match_winner(m)
            if w is None:
                continue
            pts = int(m.get("points") or 0)
            if w == "g1":
                stats[g1_key]["points"] += 2
                stats[g1_key]["clash_won"] += 1
                stats[g1_key]["total_match_points"] += pts
            elif w == "g2":
                stats[g2_key]["points"] += 2
                stats[g2_key]["clash_won"] += 1
                stats[g2_key]["total_match_points"] += pts

            set_scores = m.get("set_scores") or {}
            for sn in ("set1", "set2", "set3"):
                s = set_scores.get(sn)
                if not s or not isinstance(s, (list, tuple)) or len(s) < 2:
                    continue
                try:
                    a = int(s[0]) if s[0] is not None else 0
                    b = int(s[1]) if s[1] is not None else 0
                except (TypeError, ValueError):
                    continue
                stats[g1_key]["sets_won"] += 1 if a > b else 0
                stats[g1_key]["sets_lost"] += 1 if b > a else 0
                stats[g1_key]["rally_points_won"] += a
                stats[g1_key]["rally_points_lost"] += b
                stats[g2_key]["sets_won"] += 1 if b > a else 0
                stats[g2_key]["sets_lost"] += 1 if a > b else 0
                stats[g2_key]["rally_points_won"] += b
                stats[g2_key]["rally_points_lost"] += a

    rows = []
    for gk in groups.keys():
        s = stats[gk]
        sw, sl = s["sets_won"], s["sets_lost"]
        rw, rl = s["rally_points_won"], s["rally_points_lost"]
        rows.append({
            "group_name": str(gk),
            "team_display_name": str(group_names.get(gk, gk)),
            "matches_played": int(s["matches_played"]),
            "clash_won": int(s["clash_won"]),
            "points": int(s["points"]),
            "sets_won": int(sw),
            "sets_lost": int(sl),
            "set_difference": int(sw - sl),
            "rally_points_won": int(rw),
            "rally_points_lost": int(rl),
            "rally_points_difference": int(rw - rl),
            "clash_wins": int(s["clash_won"]),
            "total_points": int(s["total_match_points"]),
        })
    return rows


def save_tournament_data(
    player_database: pd.DataFrame,
    group_names: Dict[str, str],
    subgroup_names: Dict[str, str],
    groups: Dict[str, List[str]],
    detailed_groups: Dict[str, Any],
    standings: pd.DataFrame,
    tournament_data: Dict[str, List[Dict]],
    users: Dict[str, Any],
    clash_edit_history: List[Dict],
) -> None:
    """Persist all tournament state to Supabase."""
    sb = _get_supabase()

    # Players: replace all
    sb.table("players").delete().gte("id", 0).execute()
    if not player_database.empty:
        rows = []
        for _, row in player_database.iterrows():
            rows.append({
                "name": str(row.get("name", "")),
                "gender": str(row.get("gender", "M")),
                "email": str(row.get("email", "")),
                "skill_level": int(row.get("skill_level", 5)),
                "group_name": str(row.get("group", "Group A")),
                "assigned": bool(row.get("assigned", True)),
            })
        if rows:
            sb.table("players").insert(rows).execute()

    # Config: upsert by key
    for key, obj in [
        ("group_names", group_names),
        ("subgroup_names", subgroup_names),
        ("groups", groups),
        ("detailed_groups", detailed_groups),
    ]:
        sb.table("config").upsert(
            [{"key": key, "value_json": obj}],
            on_conflict="key",
        ).execute()

    # Standings: full table from tournament results (single source of truth)
    sb.table("standings").delete().like("group_name", "%").execute()
    st_rows = compute_standings_rows(groups, group_names, tournament_data)
    if st_rows:
        sb.table("standings").insert(st_rows).execute()

    # Users: replace all
    sb.table("users").delete().like("username", "%").execute()
    for username, data in users.items():
        sb.table("users").insert({
            "username": username,
            "password_hash": data.get("password_hash", ""),
            "role": data.get("role", "admin"),
            "created_by": data.get("created_by", ""),
            "created_at": data.get("created_at", ""),
        }).execute()

    # Clash edit history: replace all
    sb.table("clash_edit_history").delete().gte("id", 0).execute()
    for entry in clash_edit_history:
        sb.table("clash_edit_history").insert({
            "timestamp": entry.get("timestamp", ""),
            "editor": entry.get("editor"),
            "clash_key": entry.get("clash_key", ""),
            "match_number": entry.get("match_number"),
            "action": entry.get("action", ""),
            "original_data_json": entry.get("original_data", {}),
            "new_data_json": entry.get("new_data", {}),
            "reason": entry.get("reason", ""),
        }).execute()

    # Tournament matches: full clash information per game (winner, score, players, match_type, set_scores, match_info)
    sb.table("tournament_matches").delete().like("clash_key", "%").execute()
    for clash_key, matches in tournament_data.items():
        if not matches:
            continue
        lst = list(matches)
        while len(lst) < 5:
            lst.append({})
        lst = lst[:5]
        rows = [
            {"clash_key": clash_key, "match_index": i, "data_json": _normalize_slot_for_db(m, i)}
            for i, m in enumerate(lst)
        ]
        sb.table("tournament_matches").insert(rows).execute()

    return None


def migrate_json_to_db_if_needed() -> None:
    """If legacy JSON files exist and Supabase is configured, migrate once (no-op if no JSON)."""
    if not os.path.exists("tournament_players.json") and not os.path.exists("tournament_data.json"):
        return
    try:
        _get_supabase()
    except ValueError:
        return
    try:
        players = pd.DataFrame()
        if os.path.exists("tournament_players.json"):
            players = pd.read_json("tournament_players.json", orient="records")
        td = {}
        if os.path.exists("tournament_data.json"):
            with open("tournament_data.json", "r") as f:
                td = json.load(f)
    except Exception:
        return
    group_names = td.get("group_names", _default_group_names())
    subgroup_names = td.get("subgroup_names", _default_subgroup_names())
    groups = td.get("groups", _default_groups())
    detailed_groups = td.get("detailed_groups", {})
    users = td.get("users", {})
    clash_edit_history = td.get("clash_edit_history", [])
    tournament_data = td.get("tournament_data", {})
    standings = _default_standings()
    stand_dict = td.get("standings", {})
    if stand_dict:
        try:
            standings = pd.DataFrame.from_dict(stand_dict)
            if "Group" in standings.columns:
                standings = standings.set_index("Group")
        except Exception:
            pass
    if players.empty:
        players = _default_player_database()
    save_tournament_data(
        player_database=players,
        group_names=group_names,
        subgroup_names=subgroup_names,
        groups=groups,
        detailed_groups=detailed_groups,
        standings=standings,
        tournament_data=tournament_data,
        users=users,
        clash_edit_history=clash_edit_history,
    )


def load_tournament_data() -> Dict[str, Any]:
    """
    Load all tournament state from Supabase.
    Returns a dict suitable for st.session_state updates.
    """
    migrate_json_to_db_if_needed()
    try:
        sb = _get_supabase()
    except ValueError:
        return _default_state()

    result = {}

    # Players
    r = sb.table("players").select("name, gender, email, skill_level, group_name, assigned").order("id").execute()
    rows = r.data or []
    if rows:
        result["player_database"] = pd.DataFrame(
            rows,
            columns=["name", "gender", "email", "skill_level", "group_name", "assigned"],
        )
        result["player_database"] = result["player_database"].rename(columns={"group_name": "group"})
        result["player_database"]["assigned"] = result["player_database"]["assigned"].astype(bool)
    else:
        result["player_database"] = _default_player_database()

    # Config
    r = sb.table("config").select("key, value_json").execute()
    config = {row["key"]: row["value_json"] for row in (r.data or [])}
    result["group_names"] = config.get("group_names", _default_group_names())
    result["subgroup_names"] = config.get("subgroup_names", _default_subgroup_names())
    result["groups"] = config.get("groups", _default_groups())
    result["detailed_groups"] = config.get("detailed_groups", {})

    # Standings: all columns (backward compatible if migration not applied)
    try:
        r = sb.table("standings").select("*").execute()
    except Exception:
        r = type("R", (), {"data": []})()
    stand_rows = r.data or []
    if stand_rows:
        result["standings"] = _standings_df_from_db_rows(stand_rows, list(config.get("groups", _default_groups()).keys()))
    else:
        result["standings"] = _default_standings_for_groups(list(config.get("groups", _default_groups()).keys()))

    # Users
    r = sb.table("users").select("username, password_hash, role, created_by, created_at").execute()
    result["users"] = {}
    for row in r.data or []:
        result["users"][row["username"]] = {
            "password_hash": row["password_hash"],
            "role": row["role"],
            "created_by": row.get("created_by") or "",
            "created_at": row.get("created_at") or "",
        }

    # Clash edit history
    r = sb.table("clash_edit_history").select(
        "timestamp, editor, clash_key, match_number, action, original_data_json, new_data_json, reason"
    ).order("id").execute()
    result["clash_edit_history"] = []
    for row in r.data or []:
        result["clash_edit_history"].append({
            "timestamp": row.get("timestamp", ""),
            "editor": row.get("editor"),
            "clash_key": row.get("clash_key", ""),
            "match_number": row.get("match_number"),
            "action": row.get("action", ""),
            "original_data": row.get("original_data_json") or {},
            "new_data": row.get("new_data_json") or {},
            "reason": row.get("reason") or "",
        })

    # Tournament matches (sort in Python for stable order)
    r = sb.table("tournament_matches").select("clash_key, match_index, data_json").execute()
    rows = sorted(r.data or [], key=lambda x: (x["clash_key"], x["match_index"]))
    result["tournament_data"] = {}
    for row in rows:
        ckey = row["clash_key"]
        idx = row["match_index"]
        data = row.get("data_json") or {}
        if ckey not in result["tournament_data"]:
            result["tournament_data"][ckey] = []
        while len(result["tournament_data"][ckey]) <= idx:
            result["tournament_data"][ckey].append({})
        result["tournament_data"][ckey][idx] = data
    # Keep partial clash slots (empty dicts) so games 1–5 stay aligned after reload
    for ckey in list(result["tournament_data"].keys()):
        lst = result["tournament_data"][ckey]
        while len(lst) < 5:
            lst.append({})
        result["tournament_data"][ckey] = lst[:5]

    result["clashes"] = []

    return result


def get_default_state() -> Dict[str, Any]:
    """Return default state (e.g. when load fails or DB not configured). Use to initialize session_state."""
    return _default_state()


def _default_state() -> Dict[str, Any]:
    """Return default state when Supabase is not configured or empty."""
    return {
        "player_database": _default_player_database(),
        "group_names": _default_group_names(),
        "subgroup_names": _default_subgroup_names(),
        "groups": _default_groups(),
        "detailed_groups": {},
        "standings": _default_standings(),
        "tournament_data": {},
        "users": {},
        "clash_edit_history": [],
        "clashes": [],
    }


def _default_player_database() -> pd.DataFrame:
    return pd.DataFrame({
        "name": [f"Player {i+1}" for i in range(60)],
        "gender": ["M" if i % 3 != 0 else "F" for i in range(60)],
        "email": [f"player{i+1}@example.com" for i in range(60)],
        "skill_level": [random.randint(0, 15) for _ in range(60)],
        "group": [f"Group {chr(65 + (i // 10))}" for i in range(60)],
        "assigned": [True] * 60,
    })


def _default_group_names() -> Dict[str, str]:
    return {
        "Group A": "Thunder Shuttles (A)",
        "Group B": "Phoenix Feathers (B)",
        "Group C": "Vortex Smashers (C)",
        "Group D": "Shadow Drops (D)",
        "Group E": "Lightning Rackets (E)",
        "Group F": "Cyclone Squad (F)",
    }


def _default_subgroup_names() -> Dict[str, str]:
    return {"subgroup1": "Deciders (0-5)", "subgroup2": "Chokers (6-15)"}


def _default_groups() -> Dict[str, List[str]]:
    return {f"Group {chr(65 + i)}": [] for i in range(6)}


def _default_standings() -> pd.DataFrame:
    keys = [f"Group {chr(65 + i)}" for i in range(6)]
    return _default_standings_for_groups(keys)


def _default_standings_for_groups(group_keys: List[str]) -> pd.DataFrame:
    if not group_keys:
        group_keys = [f"Group {chr(65 + i)}" for i in range(6)]
    return pd.DataFrame(
        {"Clash Wins": [0] * len(group_keys), "Total Points": [0] * len(group_keys)},
        index=list(group_keys),
    )


def _standings_df_from_db_rows(stand_rows: List[Dict], group_keys: List[str]) -> pd.DataFrame:
    """Session standings indexed by internal group key (for finalize)."""
    lookup = {str(r.get("group_name", "")): r for r in stand_rows if r.get("group_name") is not None}
    cw, tp = [], []
    for gk in group_keys:
        r = lookup.get(str(gk), {})
        cw.append(int(r.get("clash_wins") if r.get("clash_wins") is not None else r.get("clash_won") or 0))
        tp.append(int(r.get("total_points") or 0))
    return pd.DataFrame({"Clash Wins": cw, "Total Points": tp}, index=list(group_keys))
