"""Genera data.json con los fragmentos HTML actualizables en vivo."""

import json
from datetime import datetime
from typing import Dict, List, Set

from html_renderer import (_render_groups, _render_thirds, _render_scorers, _match_card,
                           _render_today_matches, _render_assists, _render_yellows, _render_reds,
                           _render_rating)


def _r32_inner(matches: List[Dict]) -> str:
    html = ""
    for i in range(0, len(matches), 2):
        m1 = _match_card(matches[i])
        m2 = _match_card(matches[i + 1]) if i + 1 < len(matches) else ""
        html += f'<div class="par">{m1}{m2}</div>'
    return html


def render_data_json(standings: Dict, matchups: List[Dict]) -> str:
    live_teams: Set[str] = standings.get("_live_teams", set())
    thirds_advancing_set = {e["team"] for e in standings.get("_thirds_advancing", [])}

    matches_by_date: Dict[str, list] = standings.get("_matches_by_date", {})
    today_date: str = standings.get("_today_date", "")

    dates_html = {
        date_str: _render_today_matches(matches, standings)
        for date_str, matches in matches_by_date.items()
    }

    data = {
        "updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "today_date": today_date,
        "dates_html": dates_html,
        "today_html": dates_html.get(today_date, _render_today_matches([], standings)),
        "groups_html": _render_groups(standings, live_teams, thirds_advancing_set),
        "thirds_html": _render_thirds(standings),
        "r32_left_html": _r32_inner(matchups[:8]),
        "r32_right_html": _r32_inner(matchups[8:]),
        "scorers_html": _render_scorers(standings),
        "rating_html":  _render_rating(standings),
        "assists_html": _render_assists(standings),
        "yellows_html": _render_yellows(standings),
        "reds_html":    _render_reds(standings),
    }
    return json.dumps(data, ensure_ascii=False)
