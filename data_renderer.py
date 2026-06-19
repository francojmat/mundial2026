"""Genera data.json con los fragmentos HTML actualizables en vivo."""

import json
from datetime import datetime
from typing import Dict, List, Set

from html_renderer import _render_groups, _render_thirds, _match_card, _render_today_matches


def _r32_inner(matches: List[Dict]) -> str:
    """Devuelve el contenido interno de una columna R32 (los divs .par)."""
    html = ""
    for i in range(0, len(matches), 2):
        m1 = _match_card(matches[i])
        m2 = _match_card(matches[i + 1]) if i + 1 < len(matches) else ""
        html += f'<div class="par">{m1}{m2}</div>'
    return html


def render_data_json(standings: Dict, matchups: List[Dict]) -> str:
    live_teams: Set[str] = standings.get("_live_teams", set())
    thirds_advancing_set = {e["team"] for e in standings.get("_thirds_advancing", [])}

    data = {
        "updated": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "today_html": _render_today_matches(standings.get("_today_matches", [])),
        "groups_html": _render_groups(standings, live_teams, thirds_advancing_set),
        "thirds_html": _render_thirds(standings),
        "r32_left_html": _r32_inner(matchups[:8]),
        "r32_right_html": _r32_inner(matchups[8:]),
    }
    return json.dumps(data, ensure_ascii=False)
