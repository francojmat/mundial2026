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

    def get_raw_standings(self) -> dict:
        return self._get(f"/competitions/{COMPETITION}/standings")

    def get_matches(self, stage: str = None) -> dict:
        params = {"stage": stage} if stage else {}
        return self._get(f"/competitions/{COMPETITION}/matches", params=params)

    def get_teams(self) -> dict:
        return self._get(f"/competitions/{COMPETITION}/teams")

    def get_today_matches(self) -> list:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        raw = self._get(f"/competitions/{COMPETITION}/matches",
                        params={"dateFrom": today, "dateTo": today})
        result = []
        for m in raw.get("matches", []):
            home = m["homeTeam"].get("shortName") or m["homeTeam"].get("name", "TBD")
            away = m["awayTeam"].get("shortName") or m["awayTeam"].get("name", "TBD")
            score = m.get("score", {})
            full = score.get("fullTime", {}) or {}
            status = m.get("status", "TIMED")
            result.append({
                "home": home,
                "away": away,
                "home_goals": full.get("home"),
                "away_goals": full.get("away"),
                "status": status,
                "utc_date": m.get("utcDate", ""),
                "stage": m.get("stage", ""),
                "group": m.get("group") or "",
                "matchday": m.get("matchday") or 0,
            })
        return result


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
    result["_today_matches"] = client.get_today_matches()

    return result
