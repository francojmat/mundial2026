"""
API-Football (api-sports.io) client — free tier: 100 req/día, 10 req/min.
Solo lo usamos para el DETALLE de eventos (goles, tarjetas, cambios) que
football-data.org no da en su plan gratuito. El marcador y el estado en vivo
siguen viniendo de football-data.org.

Plan free directo (NO RapidAPI):
  base = https://v3.football.api-sports.io
  header = x-apisports-key
"""

import requests

APIFOOTBALL_BASE = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1  # "World Cup" en API-Football


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
