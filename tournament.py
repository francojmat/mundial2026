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

import requests

RANKINGS_REFRESH = 600    # segundos: los rankings se recalculan cada 10 min
VENUES_REFRESH = 1800     # segundos: estadios cada 30 min (la estructura es fija, refresca scores)
SQUADS_REFRESH = 604800   # segundos: planteles 1 vez por semana (los rosters no cambian)
SQUADS_PER_RUN = 10       # tope de equipos a refrescar por corrida (evita ráfaga de llamadas)
MATCH_LIVE_REFRESH = 120  # segundos: detalle de partido en vivo cada 2 min
MATCH_DETAILS_PER_RUN = 5 # tope de partidos a enriquecer por corrida (3 llamadas c/u)
VENUE_DETAILS_REFRESH = 604800  # detalles de estadio (foto/superficie) 1 vez por semana
VENUE_IMG_MIN_BYTES = 35000     # debajo de esto la imagen es un placeholder de la API

from countries import VENUE_CAPACITY as _VENUE_CAPACITY, VENUE_PHOTO as _VENUE_PHOTO


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
    vlist = vn.get("list", [])
    if vlist:
        if _enrich_venue_details(vlist, client, cache):
            dirty = True
        vdetails = cache.get("venue_details") or {}
        for v in vlist:
            d = vdetails.get(v.get("name")) or {}
            # Capacidad oficial WC para los 16 (curada); superficie solo donde la API la tiene.
            # Foto: la de la API si existe; si no, la curada local (Wikimedia) para completar.
            v["capacity"] = _VENUE_CAPACITY.get(v.get("name"))
            v["surface"]  = d.get("surface")
            v["image_url"] = d.get("image") or _VENUE_PHOTO.get(v.get("name"))
    standings["_venues"] = vlist

    # Mapa nombre→team_id (directo de los fixtures; el match_id ya es el fixture_id)
    tid_map = cache.get("team_id_map") or {}
    if fixtures:
        new_tid = _team_ids_from_fixtures(fixtures)
        if new_tid:
            tid_map = {**tid_map, **new_tid}
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

    # Detalle de partido (alineaciones, stats de equipo, stats por jugador)
    details = cache.get("match_details") or {}
    if matches_by_date:
        if _enrich_match_details(matches_by_date, details, client):
            cache["match_details"] = details
            dirty = True
    # Marcar qué partidos tienen detalle (para mostrar el botón VER PARTIDO)
    for matches in matches_by_date.values():
        for m in matches:
            if str(m.get("match_id")) in details:
                m["has_detail"] = True
    standings["_match_details"] = details

    if dirty:
        _save(cache_path, cache)


def _enrich_match_details(matches_by_date: dict, details: dict, client) -> bool:
    """Trae alineaciones/stats/jugadores de partidos jugados o en vivo. Cache por partido.
    Prioriza partidos en vivo y los más recientes (que son los que la gente mira).
    El match_id ES el fixture_id de API-Football."""
    candidates = []
    for matches in matches_by_date.values():
        for m in matches:
            status = m.get("status", "")
            if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
                continue
            if not m.get("match_id"):
                continue
            cached = details.get(str(m.get("match_id")))
            if cached:
                if cached.get("status") == "FINISHED":
                    continue  # terminado y cacheado → no cambia
                if not _stale(cached, MATCH_LIVE_REFRESH):
                    continue  # en vivo pero refrescado hace poco
            candidates.append(m)

    # Prioridad: en vivo primero, luego los más recientes (dos sorts estables)
    candidates.sort(key=lambda m: m.get("utc_date", ""), reverse=True)
    candidates.sort(key=lambda m: 0 if m.get("status") in ("IN_PLAY", "PAUSED") else 1)

    dirty = False
    for m in candidates[:MATCH_DETAILS_PER_RUN]:
        key = str(m.get("match_id"))
        fixture_id = m.get("match_id")
        lineups = client.get_fixture_lineups(fixture_id)
        if not lineups:
            continue  # todavía sin alineaciones (no arrancó)
        details[key] = {
            "lineups":    lineups,
            "statistics": client.get_fixture_statistics(fixture_id),
            "players":    client.get_fixture_players(fixture_id),
            "status":     m.get("status", ""),
            "last_fetch": _now().isoformat(),
        }
        dirty = True
    return dirty


def _team_ids_from_fixtures(fixtures: list) -> dict:
    """{nombre_equipo: team_id} directo de los fixtures de API-Football."""
    out = {}
    for fx in fixtures:
        teams = fx.get("teams") or {}
        for side in ("home", "away"):
            t = teams.get(side) or {}
            if t.get("name") and t.get("id"):
                out[t["name"]] = t["id"]
    return out


def _image_is_real(url: str) -> bool:
    """True si la imagen es real (no un placeholder de la API). Los placeholders pesan poco."""
    if not url:
        return False
    try:
        r = requests.get(url, timeout=8)
        return r.ok and len(r.content) >= VENUE_IMG_MIN_BYTES
    except Exception:
        return False


def _enrich_venue_details(vlist: list, client, cache: dict) -> bool:
    """Trae capacidad/superficie/foto de cada estadio con id. Cache semanal. Valida la foto."""
    details = cache.get("venue_details") or {}
    dirty = False
    for v in vlist:
        name, vid = v.get("name"), v.get("id")
        if not name or not vid:
            continue
        entry = details.get(name)
        if entry and not _stale(entry, VENUE_DETAILS_REFRESH):
            continue
        data = client.get_venue(id=vid)
        if not data:
            continue
        img = data.get("image")
        if not _image_is_real(img):
            img = None
        details[name] = {
            "capacity":   data.get("capacity"),
            "surface":    data.get("surface"),
            "image":      img,
            "last_fetch": _now().isoformat(),
        }
        dirty = True
    if dirty:
        cache["venue_details"] = details
    return dirty


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
        slot = venues.setdefault(name, {"name": name, "city": v.get("city", ""),
                                        "id": v.get("id"), "matches": []})
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
