"""
Enriquecimiento de partidos con eventos (goles, tarjetas, cambios) desde
API-Football, con caché en disco, polling adaptativo y presupuesto diario.

Estrategia:
- Sin partidos en vivo y todo cacheado -> 0 requests.
- Partido terminado y ya cacheado -> 0 requests (los eventos no cambian).
- Partido en vivo -> 1 request cada `interval` segundos (adaptativo según
  cuántos partidos haya en vivo a la vez).
- Partido recién terminado -> 1 request final para congelar sus eventos.
- Tope duro diario para no pasarnos de las 100 requests del free tier.
"""

import json
import os
from datetime import datetime, timezone, timedelta

DAILY_BUDGET = 95          # margen sobre las 100 del free tier
RECENT_DAYS = 4            # solo enriquecemos partidos de los últimos N días


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _adaptive_interval(live_count: int) -> int:
    """Segundos entre refrescos del detalle, según partidos en vivo simultáneos."""
    if live_count <= 1:
        return 90
    if live_count == 2:
        return 180
    return 300


def _load_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"day": "", "requests_today": 0, "fixture_map": {}, "events": {}}


def _save_cache(path: str, cache: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def _parse_events(raw_events: list, home_id, away_id, home_name: str, away_name: str) -> dict:
    """Convierte los eventos crudos de API-Football a la forma que espera el HTML."""
    goals, bookings, subs = [], [], []

    for ev in raw_events:
        ev_type = (ev.get("type") or "").lower()
        detail  = (ev.get("detail") or "")
        t       = ev.get("time") or {}
        elapsed = t.get("elapsed")
        extra   = t.get("extra")
        minute  = str(elapsed) if elapsed is not None else ""
        if extra:
            minute += f"+{extra}"

        team_obj = ev.get("team") or {}
        team_id  = team_obj.get("id")
        team_name = home_name if team_id == home_id else (away_name if team_id == away_id else team_obj.get("name", ""))

        player = (ev.get("player") or {}).get("name") or ""
        assist = (ev.get("assist") or {}).get("name") or ""

        if ev_type == "goal":
            if "missed" in detail.lower():
                continue  # penal errado no es gol
            g_type = "NORMAL"
            d_low = detail.lower()
            if "penalty" in d_low:
                g_type = "PENALTY"
            elif "own" in d_low:
                g_type = "OWN"
            goals.append({
                "minute": minute,
                "scorer": player,
                "team":   team_name,
                "assist": assist,
                "type":   g_type,
            })

        elif ev_type == "card":
            card = "RED" if "red" in detail.lower() else "YELLOW"
            bookings.append({
                "minute": minute,
                "player": player,
                "team":   team_name,
                "card":   card,
            })

        elif ev_type == "subst":
            # En API-Football: player = entra, assist = sale
            subs.append({
                "minute":     minute,
                "player_in":  player,
                "player_out": assist,
                "team":       team_name,
            })

    return {"goals_detail": goals, "bookings": bookings, "substitutions": subs}


def _ensure_fixture_map(cache: dict, client, matches: list, state: dict) -> None:
    """
    Asegura que todos los partidos candidatos tengan su fixture_id de API-Football.
    Si falta alguno, trae TODOS los fixtures del torneo en una sola request y
    matchea por timestamp de kickoff (tolerancia 5 min). Cachea el mapeo (no cambia).
    `state` evita pedir la lista más de una vez por corrida.
    """
    pending = [m for m in matches if str(m.get("match_id")) not in cache["fixture_map"]]
    if not pending or state.get("fixtures_fetched"):
        return
    if cache["requests_today"] >= DAILY_BUDGET:
        return

    fixtures = client.get_all_fixtures()
    cache["requests_today"] += 1
    state["fixtures_fetched"] = True
    if not fixtures:
        return

    for m in pending:
        utc_dt = _parse_iso(m.get("utc_date", ""))
        if not utc_dt:
            continue
        for fx in fixtures:
            fx_dt = _parse_iso((fx.get("fixture") or {}).get("date", ""))
            if not fx_dt:
                continue
            if abs((fx_dt - utc_dt).total_seconds()) <= 300:
                teams = fx.get("teams") or {}
                cache["fixture_map"][str(m.get("match_id"))] = {
                    "fixture_id": (fx.get("fixture") or {}).get("id"),
                    "home_id":    (teams.get("home") or {}).get("id"),
                    "away_id":    (teams.get("away") or {}).get("id"),
                }
                break


def enrich_with_events(matches_by_date: dict, client, cache_path: str = "events_cache.json") -> None:
    """
    Enriquece in-place los partidos con goles/tarjetas/cambios desde API-Football.
    `client` es un APIFootballClient. Si es None, no hace nada (degradación elegante).
    """
    if client is None:
        return

    cache = _load_cache(cache_path)
    today = _now_utc().date().isoformat()
    day_changed = cache.get("day") != today
    if day_changed:
        cache["day"] = today
        cache["requests_today"] = 0  # el presupuesto se resetea cada día

    now = _now_utc()
    cutoff = now - timedelta(days=RECENT_DAYS)

    # Partidos candidatos (terminados/en vivo recientes)
    candidates = []
    live_count = 0
    for matches in matches_by_date.values():
        for m in matches:
            status = m.get("status", "")
            if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
                continue
            utc_dt = _parse_iso(m.get("utc_date", ""))
            if not utc_dt:
                continue
            if status == "FINISHED" and utc_dt < cutoff:
                continue
            candidates.append(m)
            if status in ("IN_PLAY", "PAUSED"):
                live_count += 1

    interval = _adaptive_interval(live_count)
    state = {}  # evita pedir la lista de fixtures más de una vez por corrida
    dirty = False

    for m in candidates:
        status = m.get("status", "")
        key = str(m.get("match_id"))
        cached = cache["events"].get(key)

        def apply(ev: dict):
            m["goals_detail"]  = ev.get("goals_detail", [])
            m["bookings"]      = ev.get("bookings", [])
            m["substitutions"] = ev.get("substitutions", [])

        # ¿Hace falta pedir a la API?
        need_fetch = False
        if status == "FINISHED":
            if not (cached and cached.get("status") == "FINISHED"):
                need_fetch = True  # recién terminado o nunca cacheado
        else:  # IN_PLAY / PAUSED
            if not cached:
                need_fetch = True
            else:
                last = _parse_iso(cached.get("last_fetch", ""))
                if not last or (now - last).total_seconds() >= interval:
                    need_fetch = True

        # Tope de presupuesto: si no queda, usamos lo cacheado y seguimos.
        if need_fetch and cache["requests_today"] >= DAILY_BUDGET:
            need_fetch = False

        if need_fetch:
            _ensure_fixture_map(cache, client, candidates, state)
            mapping = cache["fixture_map"].get(key)
            if mapping and mapping.get("fixture_id") and cache["requests_today"] < DAILY_BUDGET:
                raw = client.get_fixture_events(mapping["fixture_id"])
                cache["requests_today"] += 1
                parsed = _parse_events(
                    raw,
                    mapping.get("home_id"), mapping.get("away_id"),
                    m.get("home", ""), m.get("away", ""),
                )
                parsed["status"] = status
                parsed["last_fetch"] = now.isoformat()
                cache["events"][key] = parsed
                cached = parsed
                dirty = True

        if cached:
            apply(cached)

    if dirty or day_changed:
        _save_cache(cache_path, cache)
