"""
Datos del torneo desde API-Football (rankings, y a futuro planteles, coaches,
lesionados, estadios, detalle de partido). Cache en disco con refresco temporizado
para no gastar requests al pedo.

Separado de events.py: events.py = eventos por partido; tournament.py = el resto.
Cache propio: apifootball_cache.json (commiteado al repo para persistir entre corridas).
"""

import json
import os
from datetime import datetime, timezone

RANKINGS_REFRESH = 600    # segundos: los rankings se recalculan cada 10 min
VENUES_REFRESH = 1800     # segundos: estadios cada 30 min (la estructura es fija, refresca scores)
SQUADS_REFRESH = 604800   # segundos: planteles 1 vez por semana (los rosters no cambian)
SQUADS_PER_RUN = 10       # tope de equipos a refrescar por corrida (evita ráfaga de llamadas)


def _now():
    return datetime.now(timezone.utc)


def _parse_iso(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _load(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(path: str, cache: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def _stale(section: dict, max_age: int) -> bool:
    last = _parse_iso((section or {}).get("last_fetch", ""))
    return (not last) or (_now() - last).total_seconds() >= max_age


def enrich_tournament_data(standings: dict, client, cache_path: str = "apifootball_cache.json") -> None:
    """
    Pone en standings las claves _assists, _yellows, _reds (rankings del torneo).
    Si client es None, no hace nada (degradación elegante).
    """
    if client is None:
        return

    cache = _load(cache_path)
    dirty = False

    # Rankings: asistencias, amarillas, rojas
    rk = cache.get("rankings") or {}
    if _stale(rk, RANKINGS_REFRESH):
        try:
            rk = {
                "assists": client.get_top_assists(),
                "yellows": client.get_top_yellow_cards(),
                "reds":    client.get_top_red_cards(),
                "last_fetch": _now().isoformat(),
            }
            cache["rankings"] = rk
            dirty = True
        except Exception:
            rk = cache.get("rankings") or {}

    standings["_assists"] = rk.get("assists", [])
    standings["_yellows"] = rk.get("yellows", [])
    standings["_reds"]    = rk.get("reds", [])

    # Fixtures: se usan para estadios y para mapear nombre football-data → team_id API-Football.
    matches_by_date = standings.get("_matches_by_date", {})
    need_fixtures = _stale(cache.get("venues") or {}, VENUES_REFRESH) or not cache.get("team_id_map")
    fixtures = None
    if need_fixtures:
        try:
            fixtures = client.get_all_fixtures()
        except Exception:
            fixtures = None

    # Estadios
    vn = cache.get("venues") or {}
    if fixtures and _stale(vn, VENUES_REFRESH):
        vn = {"list": _build_venues(fixtures), "last_fetch": _now().isoformat()}
        cache["venues"] = vn
        dirty = True
    standings["_venues"] = vn.get("list", [])

    # Mapa nombre → team_id (se arma una vez con los fixtures, después persiste)
    tid_map = cache.get("team_id_map") or {}
    if fixtures and matches_by_date:
        new_map = _build_team_id_map(matches_by_date, fixtures)
        if new_map:
            tid_map = {**tid_map, **new_map}
            cache["team_id_map"] = tid_map
            dirty = True

    # Planteles + coach (cache semanal, con tope por corrida)
    squads = cache.get("squads") or {}
    if tid_map:
        budget = SQUADS_PER_RUN
        for name, tid in tid_map.items():
            if budget <= 0:
                break
            entry = squads.get(name)
            if entry and not _stale(entry, SQUADS_REFRESH):
                continue
            try:
                players = client.get_squad(tid)
            except Exception:
                continue
            if players:
                squads[name] = {
                    "players": players,
                    "coach":   client.get_coach(tid),
                    "last_fetch": _now().isoformat(),
                }
                budget -= 1
                dirty = True
        cache["squads"] = squads
    standings["_squads"] = squads

    if dirty:
        _save(cache_path, cache)


def _build_team_id_map(matches_by_date: dict, fixtures: list) -> dict:
    """Mapea nombre de equipo (football-data) → team_id (API-Football) por timestamp de kickoff."""
    out = {}
    for matches in matches_by_date.values():
        for m in matches:
            utc = _parse_iso(m.get("utc_date", ""))
            if not utc:
                continue
            for fx in fixtures:
                fxd = _parse_iso((fx.get("fixture") or {}).get("date", ""))
                if fxd and abs((fxd - utc).total_seconds()) <= 300:
                    teams = fx.get("teams") or {}
                    h = (teams.get("home") or {}).get("id")
                    a = (teams.get("away") or {}).get("id")
                    if m.get("home") and h:
                        out[m["home"]] = h
                    if m.get("away") and a:
                        out[m["away"]] = a
                    break
    return out


def _build_venues(fixtures: list) -> list:
    """Agrupa los fixtures por estadio. Devuelve lista ordenada por cant. de partidos."""
    venues = {}
    for fx in fixtures:
        f = fx.get("fixture") or {}
        v = f.get("venue") or {}
        name = v.get("name")
        if not name:
            continue
        teams = fx.get("teams") or {}
        goals = fx.get("goals") or {}
        slot = venues.setdefault(name, {"name": name, "city": v.get("city", ""), "matches": []})
        slot["matches"].append({
            "date":   f.get("date", ""),
            "status": (f.get("status") or {}).get("short", ""),
            "home":   (teams.get("home") or {}).get("name", ""),
            "away":   (teams.get("away") or {}).get("name", ""),
            "gh":     goals.get("home"),
            "ga":     goals.get("away"),
        })
    out = list(venues.values())
    for v in out:
        v["matches"].sort(key=lambda m: m.get("date", ""))
        v["count"] = len(v["matches"])
    out.sort(key=lambda v: (-v["count"], v["name"]))
    return out
