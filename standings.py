"""
FIFA World Cup 2026 — Group standings with official tiebreaker rules.

Tiebreaker order (Article 13, FIFA 2026 regulations):
  1. H2H points (among tied teams)
  2. H2H goal difference (among tied teams)
  3. H2H goals scored (among tied teams)
  4. Overall goal difference (all group matches)
  5. Overall goals scored (all group matches)
  6. Fair play score (yellow -1, red -3)
  7. FIFA World Ranking (lower number = better)
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TeamStanding:
    name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    fifa_ranking: int = 999

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def fair_play_score(self) -> int:
        return -(self.yellow_cards + self.red_cards * 3)


@dataclass
class MatchResult:
    home: str
    away: str
    home_goals: int
    away_goals: int
    home_yellow: int = 0
    away_yellow: int = 0
    home_red: int = 0
    away_red: int = 0
    played: bool = True
    status: str = "TIMED"  # TIMED | IN_PLAY | PAUSED | FINISHED


def compute_stats(teams: List[str], matches: List[MatchResult]) -> Dict[str, TeamStanding]:
    stats = {t: TeamStanding(name=t) for t in teams}
    team_set = set(teams)

    for m in matches:
        if not m.played:
            continue
        if m.home not in team_set or m.away not in team_set:
            continue

        h, a = m.home, m.away
        stats[h].played += 1
        stats[a].played += 1
        stats[h].goals_for += m.home_goals
        stats[h].goals_against += m.away_goals
        stats[a].goals_for += m.away_goals
        stats[a].goals_against += m.home_goals
        stats[h].yellow_cards += m.home_yellow
        stats[a].yellow_cards += m.away_yellow
        stats[h].red_cards += m.home_red
        stats[a].red_cards += m.away_red

        if m.home_goals > m.away_goals:
            stats[h].won += 1
            stats[h].points += 3
            stats[a].lost += 1
        elif m.home_goals == m.away_goals:
            stats[h].drawn += 1
            stats[h].points += 1
            stats[a].drawn += 1
            stats[a].points += 1
        else:
            stats[a].won += 1
            stats[a].points += 3
            stats[h].lost += 1

    return stats


def rank_group(
    teams: List[str],
    all_stats: Dict[str, TeamStanding],
    all_matches: List[MatchResult],
    fifa_rankings: Dict[str, int] = None,
) -> List[str]:
    """Return teams sorted 1st→4th using FIFA 2026 tiebreaker rules."""
    if fifa_rankings:
        for team, rank in fifa_rankings.items():
            if team in all_stats:
                all_stats[team].fifa_ranking = rank

    # Group by points
    by_points: Dict[int, List[str]] = {}
    for t in teams:
        pts = all_stats[t].points
        by_points.setdefault(pts, []).append(t)

    result = []
    for pts in sorted(by_points.keys(), reverse=True):
        group = by_points[pts]
        if len(group) == 1:
            result.extend(group)
        else:
            result.extend(_break_tie(group, all_stats, all_matches))

    return result


def _break_tie(
    tied: List[str],
    all_stats: Dict[str, TeamStanding],
    all_matches: List[MatchResult],
) -> List[str]:
    if len(tied) == 1:
        return tied

    # Compute H2H stats restricted to matches among tied teams only
    h2h = compute_stats(tied, all_matches)

    def sort_key(team: str) -> tuple:
        s = all_stats[team]
        h = h2h[team]
        return (
            h.points,           # 1. H2H points
            h.goal_diff,        # 2. H2H goal difference
            h.goals_for,        # 3. H2H goals scored
            s.goal_diff,        # 4. Overall goal difference
            s.goals_for,        # 5. Overall goals scored
            s.fair_play_score,  # 6. Fair play (higher = better, already negated)
            -s.fifa_ranking,    # 7. FIFA ranking (lower number = better)
        )

    sorted_teams = sorted(tied, key=sort_key, reverse=True)

    # Check for remaining ties after all criteria — group and recurse if needed
    result = []
    i = 0
    while i < len(sorted_teams):
        j = i + 1
        while j < len(sorted_teams) and sort_key(sorted_teams[j]) == sort_key(sorted_teams[i]):
            j += 1
        if j - i > 1:
            # Truly identical on all 7 criteria — leave in original order
            result.extend(sorted_teams[i:j])
        else:
            result.append(sorted_teams[i])
        i = j

    return result


def rank_third_place_teams(
    thirds: List[Dict],  # [{"team": name, "group": "A", "stats": TeamStanding}, ...]
    fifa_rankings: Dict[str, int] = None,
) -> List[Dict]:
    """
    Rank the 12 third-place teams to find the 8 best that advance.
    No H2H (they're from different groups) — use overall stats only.
    """
    if fifa_rankings:
        for entry in thirds:
            entry["stats"].fifa_ranking = fifa_rankings.get(entry["team"], 999)

    def third_key(entry: Dict) -> tuple:
        s = entry["stats"]
        return (
            s.points,
            s.goal_diff,
            s.goals_for,
            s.fair_play_score,
            -s.fifa_ranking,
        )

    return sorted(thirds, key=third_key, reverse=True)
