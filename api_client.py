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

    def get_match_details(self, match_id: int) -> dict:
        """Fetch detailed single-match data (goals, bookings, substitutions)."""
        try:
            return self._get(f"/matches/{match_id}")
        except Exception:
            return {}

    def enrich_matches_with_events(self, matches_by_date: dict, days_back: int = 4) -> None:
        """
        Para partidos terminados o en vivo de los últimos `days_back` días,
        obtiene goles, tarjetas y cambios desde el endpoint individual.
        Modifica matches_by_date in-place. Respeta el rate limit de 10 req/min.
        """
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        for matches in matches_by_date.values():
            for m in matches:
                status = m.get("status", "")
                if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
                    continue

                utc_str = m.get("utc_date", "")
                if not utc_str:
                    continue

                try:
                    utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
                    if status == "FINISHED" and utc_dt < cutoff:
                        continue
                except Exception:
                    continue

                match_id = m.get("match_id")
                if not match_id:
                    continue

                time.sleep(6.2)  # 10 req/min → 1 cada 6s
                detail = self.get_match_details(match_id)
                if not detail:
                    continue

                goals_detail = []
                for g in (detail.get("goals") or []):
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
                for b in (detail.get("bookings") or []):
                    minute = str(b.get("minute") or "")
                    if b.get("injuryTime"):
                        minute += f'+{b["injuryTime"]}'
                    bookings.append({
                        "minute": minute,
                        "player": (b.get("player") or {}).get("name", ""),
                        "team":   (b.get("team") or {}).get("shortName") or (b.get("team") or {}).get("name", ""),
                        "card":   b.get("card", "YELLOW"),
                    })

                subs = []
                for s in (detail.get("substitutions") or []):
                    subs.append({
                        "minute":     str(s.get("minute") or ""),
                        "player_out": (s.get("playerOut") or {}).get("name", ""),
                        "player_in":  (s.get("playerIn") or {}).get("name", ""),
                        "team":       (s.get("team") or {}).get("shortName") or (s.get("team") or {}).get("name", ""),
                    })

                m["goals_detail"]  = goals_detail
                m["bookings"]      = bookings
                m["substitutions"] = subs

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


def parse_matches(raw_matches: dict) -> Dict[str, List[MatchResult]]:
    """Convert API match data → {group_name: [MatchResult, ...]}"""
    groups: Dict[str, List[MatchResult]] = {}

    for m in raw_matches.get("matches", []):
        if m.get("stage") != "GROUP_STAGE":
            continue
        group = m.get("group", "UNKNOWN")
        status = m.get("status", "")
        played = status in ("FINISHED", "IN_PLAY", "PAUSED")

        home = m["homeTeam"]["shortName"] or m["homeTeam"]["name"]
        away = m["awayTeam"]["shortName"] or m["awayTeam"]["name"]
        score = m.get("score", {})
        full = score.get("fullTime", {}) or {}

        match = MatchResult(
            home=home,
            away=away,
            home_goals=full.get("home") or 0,
            away_goals=full.get("away") or 0,
            played=played,
            status=status,
        )

        groups.setdefault(group, []).append(match)

    return groups


def build_standings(client: WorldCupClient, fifa_rankings: Dict[str, int] = None) -> Dict:
    """
    Fetch all group matches and compute standings with FIFA 2026 tiebreakers.
    Returns dict with groups + third-place ranking.
    """
    raw = client.get_matches(stage="GROUP_STAGE")
    group_matches = parse_matches(raw)

    result = {}
    all_thirds = []

    for group_name, matches in sorted(group_matches.items()):
        # Collect all teams in this group
        teams_set = set()
        for m in matches:
            teams_set.add(m.home)
            teams_set.add(m.away)
        teams = list(teams_set)

        stats = compute_stats(teams, matches)
        ranked = rank_group(teams, stats, matches, fifa_rankings)

        result[group_name] = {
            "teams": ranked,
            "stats": stats,
            "matches": matches,
        }

        if len(ranked) >= 3:
            third_team = ranked[2]
            all_thirds.append({
                "team": third_team,
                "group": group_name,
                "stats": stats[third_team],
            })

    # Rank the third-place teams
    best_thirds = rank_third_place_teams(all_thirds, fifa_rankings)
    result["_thirds_ranked"] = best_thirds
    result["_thirds_advancing"] = best_thirds[:8]

    # Teams currently in a live match
    live_teams = set()
    for matches in group_matches.values():
        for m in matches:
            if m.status in ("IN_PLAY", "PAUSED"):
                live_teams.add(m.home)
                live_teams.add(m.away)
    result["_live_teams"] = live_teams
    display = client.get_matches_for_display()
    client.enrich_matches_with_events(display["dates"])
    result["_matches_by_date"] = display["dates"]
    result["_today_date"]      = display["today"]
    result["_today_matches"]   = display["dates"].get(display["today"], [])
    try:
        result["_scorers"] = client.get_scorers(limit=50)
    except Exception:
        result["_scorers"] = []

    return result
