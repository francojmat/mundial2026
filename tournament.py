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
CLUBS_PER_RUN  = 80       # tope de jugadores a resolver club por corrida (1 llamada c/u, cacheado)
MATCH_LIVE_REFRESH = 120  # segundos: detalle de partido en vivo cada 2 min
MATCH_DETAILS_PER_RUN = 5 # tope de partidos a enriquecer por corrida (3 llamadas c/u)
VENUE_DETAILS_REFRESH = 604800  # detalles de estadio (foto/superficie) 1 vez por semana
VENUE_IMG_MIN_BYTES = 35000     # debajo de esto la imagen es un placeholder de la API

from countries import (VENUE_CAPACITY as _VENUE_CAPACITY, VENUE_PHOTO as _VENUE_PHOTO,
                       VENUE_COORDS as _VENUE_COORDS)

WEATHER_REFRESH = 7200  # clima de cada sede cada 2 horas

# Códigos WMO de Open-Meteo → texto en español
_WMO = {0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
        45: "Niebla", 48: "Niebla", 51: "Llovizna", 53: "Llovizna", 55: "Llovizna",
        61: "Lluvia", 63: "Lluvia", 65: "Lluvia fuerte", 66: "Lluvia helada", 67: "Lluvia helada",
        71: "Nieve", 73: "Nieve", 75: "Nieve intensa", 77: "Nieve",
        80: "Chubascos", 81: "Chubascos", 82: "Chubascos fuertes",
        85: "Chubascos de nieve", 86: "Chubascos de nieve",
        95: "Tormenta", 96: "Tormenta", 99: "Tormenta"}


def enrich_venue_weather(venues: list, cache_path: str = "apifootball_cache.json") -> None:
    """6.1 — agrega v['weather'] = {temp, desc} con el clima actual (Open-Meteo, sin key)."""
    if not venues:
        return
    cache = _load(cache_path)
    wcache = cache.get("weather") or {}
    dirty = False
    for v in venues:
        name = v.get("name")
        coords = _VENUE_COORDS.get(name)
        if not coords:
            continue
        entry = wcache.get(name)
        if not entry or _stale(entry, WEATHER_REFRESH):
            try:
                r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=8, params={
                    "latitude": coords[0], "longitude": coords[1],
                    "current": "temperature_2m,weather_code",
                })
                cur = (r.json() or {}).get("current") or {}
                temp = cur.get("temperature_2m")
                if temp is not None:
                    entry = {"temp": round(temp), "desc": _WMO.get(cur.get("weather_code"), ""),
                             "last_fetch": _now().isoformat()}
                    wcache[name] = entry
                    dirty = True
            except Exception:
                entry = wcache.get(name)
        if entry:
            v["weather"] = {"temp": entry.get("temp"), "desc": entry.get("desc")}
    cache["weather"] = wcache
    if dirty:
        _save(cache_path, cache)


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
    # 7.1 — club de cada jugador (país del club), backfill throttleado y cacheado
    if _enrich_player_clubs(squads, client, cache):
        dirty = True
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


def _enrich_player_clubs(squads: dict, client, cache: dict) -> bool:
    """7.1 — resuelve el club (y país del club) de cada jugador. 1 llamada por jugador,
    cacheado para siempre. Throttleado (CLUBS_PER_RUN) → hace backfill en varias corridas.
    Aplica club/club_country a los dicts de jugador del plantel."""
    clubs = cache.get("player_clubs") or {}
    budget = CLUBS_PER_RUN
    dirty = False
    for entry in (squads or {}).values():
        for p in entry.get("players", []):
            pid = p.get("id")
            if pid is None:
                continue
            key = str(pid)
            if key not in clubs and budget > 0:
                try:
                    info = client.get_player_club(pid)
                except Exception:
                    continue                # error de red/rate-limit: no cachear, reintenta luego
                clubs[key] = info or {}     # {} marca "consultado, sin club"
                budget -= 1
                dirty = True
            info = clubs.get(key)
            if info:
                p["club"] = info.get("club")
                p["club_country"] = info.get("country")
    cache["player_clubs"] = clubs
    return dirty


def _detail_has_player_ids(cached: dict) -> bool:
    """True si el detalle cacheado ya trae IDs de jugador (fixtures/players con 'id')."""
    for side in (cached.get("players") or []):
        for p in (side.get("players") or []):
            return p.get("id") is not None
    return True  # sin players → no hace falta re-pedir


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
            # Auto-reparado: si el detalle cacheado no tiene IDs de jugador (caché viejo,
            # previo al fix de stats), se vuelve a pedir aunque esté terminado.
            if cached and _detail_has_player_ids(cached):
                if cached.get("status") == "FINISHED":
                    continue  # terminado y cacheado (con ids) → no cambia
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


# ── Head-to-head de los cruces del bracket (4.3) ──────────────────────────────
H2H_REFRESH = 604800   # el historial entre dos selecciones se refresca 1 vez por semana
H2H_PER_RUN = 24       # tope de pares nuevos a pedir por corrida


def enrich_h2h(matchups: list, client, cache_path: str = "apifootball_cache.json",
               k1: str = "equipo1", k2: str = "equipo2", budget: int = H2H_PER_RUN) -> None:
    """Agrega a cada cruce/partido su historial (item['h2h']). Cache por par de ids.
    k1/k2 = nombres de los campos de equipo (equipo1/equipo2 en bracket; home/away en partidos)."""
    if client is None or not matchups:
        return
    from h2h_curado import h2h_curado
    from countries import nombre_es
    cache = _load(cache_path)
    tid = cache.get("team_id_map") or {}
    h2h = cache.get("h2h") or {}
    dirty = False
    for m in matchups:
        e1, e2 = m.get(k1), m.get(k2)
        i1, i2 = tid.get(e1), tid.get(e2)
        data = None
        if i1 and i2:
            key = "-".join(str(x) for x in sorted([i1, i2]))
            entry = h2h.get(key)
            if (not entry or _stale(entry, H2H_REFRESH)) and budget > 0:
                try:
                    data = client.get_h2h(i1, i2)
                    h2h[key] = {"list": data, "last_fetch": _now().isoformat()}
                    entry = h2h[key]
                    budget -= 1
                    dirty = True
                except Exception:
                    pass
            if entry:
                data = entry.get("list", [])
        # Fallback curado a mano cuando la API no tiene historial del par (clave en español)
        if not data:
            data = h2h_curado(nombre_es(e1), nombre_es(e2))
        if data:
            m["h2h"] = data
    cache["h2h"] = h2h
    if dirty:
        _save(cache_path, cache)
