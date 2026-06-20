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
                "name":  player.get("name", ""),
                "team":  team.get("shortName") or team.get("name", ""),
                "goals": s.get("goals") or 0,
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

            by_date.setdefault(local_date.isoformat(), []).append({
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
    result["_matches_by_date"] = display["dates"]
    result["_today_date"]      = display["today"]
    result["_today_matches"]   = display["dates"].get(display["today"], [])
    try:
        result["_scorers"] = client.get_scorers(limit=50)
    except Exception:
        result["_scorers"] = []

    return result
