"""
API-Football (api-sports.io) client — plan Pro: 7.500 req/día.
Provee el detalle de eventos (goles, tarjetas, cambios), rankings del torneo,
planteles, cuerpo técnico, lesionados, y detalle de partido (alineaciones,
estadísticas). El marcador y el estado en vivo siguen viniendo de football-data.org.

Endpoint directo (NO RapidAPI):
  base = https://v3.football.api-sports.io
  header = x-apisports-key
"""

import requests

APIFOOTBALL_BASE = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1  # "World Cup" en API-Football


def _player_ranking(raw: dict, value_fn) -> list:
    """Normaliza la respuesta de un endpoint players/top* a [{name, team, value}]."""
    out = []
    for p in raw.get("response", []):
        st = (p.get("statistics") or [{}])[0]
        out.append({
            "name":  (p.get("player") or {}).get("name", ""),
            "team":  (st.get("team") or {}).get("name", ""),
            "value": value_fn(st) or 0,
        })
    return out


class APIFootballClient:
    def __init__(self, api_key: str, season: int = 2026):
        self.season = season
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})

    def _get(self, path: str, params: dict = None) -> dict:
        resp = self.session.get(f"{APIFOOTBALL_BASE}{path}", params=params or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_all_fixtures(self) -> list:
        """
        Devuelve TODOS los partidos del Mundial de la temporada en una sola request.
        (El filtro ?date= de API-Football es poco fiable por timezone, así que
        traemos todo y matcheamos por timestamp del lado nuestro.)
        """
        try:
            data = self._get("/fixtures", {
                "league": WORLD_CUP_LEAGUE_ID,
                "season": self.season,
            })
            return data.get("response") or []
        except Exception:
            return []

    def get_fixture_events(self, fixture_id: int) -> list:
        """Devuelve la lista cruda de eventos de un partido."""
        try:
            data = self._get("/fixtures/events", {"fixture": fixture_id})
            return data.get("response") or []
        except Exception:
            return []

    # ── Rankings del torneo ───────────────────────────────────────────────
    def _league_params(self) -> dict:
        return {"league": WORLD_CUP_LEAGUE_ID, "season": self.season}

    def get_top_assists(self) -> list:
        raw = self._get("/players/topassists", self._league_params())
        return _player_ranking(raw, lambda st: (st.get("goals") or {}).get("assists"))

    def get_top_yellow_cards(self) -> list:
        raw = self._get("/players/topyellowcards", self._league_params())
        return _player_ranking(raw, lambda st: (st.get("cards") or {}).get("yellow"))

    def get_top_red_cards(self) -> list:
        raw = self._get("/players/topredcards", self._league_params())
        return _player_ranking(
            raw,
            lambda st: ((st.get("cards") or {}).get("red") or 0)
                       + ((st.get("cards") or {}).get("yellowred") or 0),
        )

    # ── Plantel y cuerpo técnico ──────────────────────────────────────────
    def get_squad(self, team_id: int) -> list:
        """Plantel completo de un equipo: [{id, name, number, age, position, photo}]."""
        try:
            raw = self._get("/players/squads", {"team": team_id})
        except Exception:
            return []
        resp = raw.get("response") or []
        if not resp:
            return []
        out = []
        for p in resp[0].get("players", []):
            out.append({
                "id":       p.get("id"),
                "name":     p.get("name", ""),
                "number":   p.get("number"),
                "age":      p.get("age"),
                "position": p.get("position", ""),
                "photo":    p.get("photo", ""),
            })
        return out

    def get_coach(self, team_id: int) -> dict:
        """DT actual de un equipo: {name, age, nationality, photo}."""
        try:
            raw = self._get("/coachs", {"team": team_id})
        except Exception:
            return {}
        resp = raw.get("response") or []
        # El DT actual es el que tiene a este equipo con career.end == null.
        current = None
        for c in resp:
            for car in (c.get("career") or []):
                if (car.get("team") or {}).get("id") == team_id and not car.get("end"):
                    current = c
                    break
            if current:
                break
        c = current or (resp[0] if resp else None)
        if not c:
            return {}
        return {
            "name":        c.get("name", ""),
            "age":         c.get("age"),
            "nationality": c.get("nationality", ""),
            "photo":       c.get("photo", ""),
        }
