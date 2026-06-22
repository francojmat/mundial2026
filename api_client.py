"""
football-data.org API client for World Cup 2026.
Free tier: 10 req/min. We poll every 60s.
"""

import time
import requests
from typing import Dict, List, Optional
from standings import MatchResult, TeamStanding, compute_stats, rank_group, rank_third_place_teams

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"


class WorldCupClient:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": api_key})

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self.session.get(f"{API_BASE}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_matches(self, stage: str = None) -> dict:
        params = {"stage": stage} if stage else {}
        return self._get(f"/competitions/{COMPETITION}/matches", params=params)

    def get_scorers(self, limit: int = 10) -> list:
        raw = self._get(f"/competitions/{COMPETITION}/scorers", params={"limit": limit})
        result = []
        for s in raw.get("scorers", []):
            player = s.get("player", {})
            team   = s.get("team", {})
            result.append({
                "name":      player.get("name", ""),
                "team":      team.get("shortName") or team.get("name", ""),
                "goals":     s.get("goals") or 0,
                "assists":   s.get("assists") or 0,
                "penalties": s.get("penalties") or 0,
                "played":    s.get("playedMatches") or 0,
            })
        return result

    def get_matches_for_display(self) -> dict:
        """
        Returns all World Cup matches grouped by local date (Argentine time, UTC-3).
        Returns {"dates": {"2026-06-11": [match, ...]}, "today": "2026-06-20"}.
        """
        from datetime import datetime, timezone, timedelta

        ARGENTINA = timezone(timedelta(hours=-3))
        now_arg = datetime.now(ARGENTINA)
        today_local = now_arg.date()

        raw = self._get(f"/competitions/{COMPETITION}/matches", params={})

        by_date: dict = {}

        for m in raw.get("matches", []):
            utc_str = m.get("utcDate", "")
            if not utc_str:
                continue
            utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            local_date = utc_dt.astimezone(ARGENTINA).date()

            home = m["homeTeam"].get("shortName") or m["homeTeam"].get("name", "TBD")
            away = m["awayTeam"].get("shortName") or m["awayTeam"].get("name", "TBD")
            score = m.get("score", {})
            full  = score.get("fullTime", {}) or {}
            status = m.get("status", "TIMED")

            referees = m.get("referees") or []
            referee  = referees[0].get("name", "") if referees else ""

            goals_detail = []
            for g in (m.get("goals") or []):
                minute = str(g.get("minute") or "")
                if g.get("injuryTime"):
                    minute += f'+{g["injuryTime"]}'
                goals_detail.append({
                    "minute": minute,
                    "scorer": (g.get("scorer") or {}).get("name", ""),
                    "team":   (g.get("team") or {}).get("shortName") or (g.get("team") or {}).get("name", ""),
                    "assist": (g.get("assist") or {}).get("name", ""),
                    "type":   g.get("type", "NORMAL"),
                })

            bookings = []
            for b in (m.get("bookings") or []):
                minute = str(b.get("minute") or "")
                if b.get("injuryTime"):
                    minute += f'+{b["injuryTime"]}'
                bookings.append({
                    "minute": minute,
                    "player": (b.get("player") or {}).get("name", ""),
                    "team":   (b.get("team") or {}).get("shortName") or (b.get("team") or {}).get("name", ""),
                    "card":   b.get("card", "YELLOW"),
                })

            substitutions = []
            for s in (m.get("substitutions") or []):
                substitutions.append({
                    "minute":     str(s.get("minute") or ""),
                    "player_out": (s.get("playerOut") or {}).get("name", ""),
                    "player_in":  (s.get("playerIn") or {}).get("name", ""),
                    "team":       (s.get("team") or {}).get("shortName") or (s.get("team") or {}).get("name", ""),
                })

            by_date.setdefault(local_date.isoformat(), []).append({
                "match_id": m.get("id"),
                "home": home,
                "away": away,
                "home_goals": full.get("home"),
                "away_goals": full.get("away"),
                "status": status,
                "utc_date": utc_str,
                "stage": m.get("stage", ""),
                "group": m.get("group") or "",
                "matchday": m.get("matchday") or 0,
                "referee": referee,
                "goals_detail":  goals_detail,
                "bookings":      bookings,
                "substitutions": substitutions,
            })

        return {"dates": by_date, "today": today_local.isoformat()}


def _af_to_match(fx: dict, team_groups: dict) -> dict:
    """Convierte un fixture de API-Football al formato interno de partido."""
    from apifootball_client import STATUS_MAP, ROUND_TO_STAGE
    f = fx.get("fixture") or {}
    teams = fx.get("teams") or {}
    goals = fx.get("goals") or {}
    league = fx.get("league") or {}
    home = (teams.get("home") or {}).get("name", "")
    away = (teams.get("away") or {}).get("name", "")
    status = STATUS_MAP.get((f.get("status") or {}).get("short", ""), "TIMED")
    rnd = league.get("round", "") or ""
    if rnd.startswith("Group Stage"):
        stage = "GROUP_STAGE"
        try:
            matchday = int(rnd.rsplit("-", 1)[-1].strip())
        except Exception:
            matchday = 0
        group = team_groups.get(home, "") or team_groups.get(away, "")
    else:
        stage = ROUND_TO_STAGE.get(rnd, "")
        matchday = 0
        group = ""
    referee = ((f.get("referee") or "").split(",")[0]).strip()
    venue = f.get("venue") or {}
    return {
        "match_id":   f.get("id"),
        "home": home, "away": away,
        "home_id":    (teams.get("home") or {}).get("id"),
        "away_id":    (teams.get("away") or {}).get("id"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "status":     status,
        "elapsed":    (f.get("status") or {}).get("elapsed"),
        "utc_date":   f.get("date", ""),
        "stage":      stage,
        "group":      group,
        "matchday":   matchday,
        "referee":    referee,
        "venue_name": venue.get("name", ""),
        "venue_city": venue.get("city", ""),
        "goals_detail":  [],
        "bookings":      [],
        "substitutions": [],
    }


def _build_display(matches: List[dict]) -> dict:
    """Agrupa los partidos por fecha local (hora argentina, UTC-3)."""
    from datetime import datetime, timezone, timedelta
    ARG = timezone(timedelta(hours=-3))
    today = datetime.now(ARG).date().isoformat()
    by_date: Dict[str, list] = {}
    for m in matches:
        try:
            dt = datetime.fromisoformat((m.get("utc_date") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        local = dt.astimezone(ARG).date().isoformat()
        by_date.setdefault(local, []).append(m)
    return {"dates": by_date, "today": today}


def build_standings(scorers_client, apifootball, fifa_rankings: Dict[str, int] = None,
                    events_cache_path: str = "events_cache.json") -> Dict:
    """
    Arma posiciones + display desde API-Football (único proveedor de partidos).
    `scorers_client` (football-data) se usa solo para la lista completa de goleadores.
    """
    fixtures = apifootball.get_all_fixtures()
    team_groups = apifootball.get_team_groups()
    matches = [_af_to_match(fx, team_groups) for fx in fixtures]

    # MatchResult por grupo (solo fase de grupos con grupo asignado)
    group_matches: Dict[str, List[MatchResult]] = {}
    for m in matches:
        if m["stage"] != "GROUP_STAGE" or not m["group"]:
            continue
        played = m["status"] in ("FINISHED", "IN_PLAY", "PAUSED")
        group_matches.setdefault(m["group"], []).append(MatchResult(
            home=m["home"], away=m["away"],
            home_goals=m["home_goals"] or 0, away_goals=m["away_goals"] or 0,
            played=played, status=m["status"],
        ))

    result: Dict = {}
    all_thirds = []
    for group_name, gmatches in sorted(group_matches.items()):
        teams = list({t for mm in gmatches for t in (mm.home, mm.away)})
        stats = compute_stats(teams, gmatches)
        ranked = rank_group(teams, stats, gmatches, fifa_rankings)
        result[group_name] = {"teams": ranked, "stats": stats, "matches": gmatches}
        if len(ranked) >= 3:
            all_thirds.append({"team": ranked[2], "group": group_name, "stats": stats[ranked[2]]})

    best_thirds = rank_third_place_teams(all_thirds, fifa_rankings)
    result["_thirds_ranked"] = best_thirds
    result["_thirds_advancing"] = best_thirds[:8]

    live_teams = set()
    for m in matches:
        if m["status"] in ("IN_PLAY", "PAUSED"):
            live_teams.add(m["home"])
            live_teams.add(m["away"])
    result["_live_teams"] = live_teams

    display = _build_display(matches)
    # Detalle de eventos (goles/tarjetas/cambios) — match_id YA es el fixture_id de API-Football
    from events import enrich_with_events
    enrich_with_events(display["dates"], apifootball, events_cache_path)
    result["_matches_by_date"] = display["dates"]
    result["_today_date"]      = display["today"]
    result["_today_matches"]   = display["dates"].get(display["today"], [])

    # Goleadores: football-data (da más jugadores que las 20 de API-Football)
    try:
        result["_scorers"] = scorers_client.get_scorers(limit=200) if scorers_client else []
    except Exception:
        result["_scorers"] = []

    # Resto de datos del torneo (rankings, estadios, planteles, detalle de partido)
    from tournament import enrich_tournament_data
    enrich_tournament_data(result, apifootball)

    return result
