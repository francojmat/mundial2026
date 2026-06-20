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

RANKINGS_REFRESH = 600  # segundos: los rankings se recalculan cada 10 min


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

    if dirty:
        _save(cache_path, cache)
