"""
API-Football (api-sports.io) client — plan Pro: 7.500 req/día.
Provee el detalle de eventos (goles, tarjetas, cambios), rankings del torneo,
planteles, cuerpo técnico, lesionados, y detalle de partido (alineaciones,
estadísticas). El marcador y el estado en vivo siguen viniendo de football-data.org.

Endpoint directo (NO RapidAPI):
  base = https://v3.football.api-sports.io
  header = x-apisports-key
"""

from datetime import datetime

import requests

from countries import nombre_es

APIFOOTBALL_BASE = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1  # "World Cup" en API-Football


def _parse_iso(s: str):
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:
        return None


def resolve_fixture(match: dict, fixtures: list, tolerance: int = 300) -> dict:
    """
    Matchea un partido de football-data con su fixture de API-Football por
    timestamp de kickoff Y nombres de equipo (normalizados con nombre_es), para
    NO cruzar partidos simultáneos. Devuelve {fixture_id, home_id, away_id}
    alineado al home/away de football-data, o None si no se puede mapear.
    """
    utc = _parse_iso(match.get("utc_date", ""))
    if not utc:
        return None
    fd_home = nombre_es(match.get("home", ""))
    fd_away = nombre_es(match.get("away", ""))

    in_window = []
    for fx in fixtures:
        fxd = _parse_iso((fx.get("fixture") or {}).get("date", ""))
        if fxd and abs((fxd - utc).total_seconds()) <= tolerance:
            in_window.append(fx)

    chosen = None
    for fx in in_window:
        teams = fx.get("teams") or {}
        names = {
            nombre_es((teams.get("home") or {}).get("name", "")),
            nombre_es((teams.get("away") or {}).get("name", "")),
        }
        if names == {fd_home, fd_away}:
            chosen = fx
            break
    if chosen is None and len(in_window) == 1:
        chosen = in_window[0]  # único en la ventana → timestamp inequívoco
    if chosen is None:
        return None

    teams = chosen.get("teams") or {}
    by_name = {
        nombre_es((teams.get("home") or {}).get("name", "")): (teams.get("home") or {}).get("id"),
        nombre_es((teams.get("away") or {}).get("name", "")): (teams.get("away") or {}).get("id"),
    }
    home_id = by_name.get(fd_home)
    away_id = by_name.get(fd_away)
    if home_id is None or away_id is None:  # fallback posicional (nombres no normalizaron)
        home_id = (teams.get("home") or {}).get("id")
        away_id = (teams.get("away") or {}).get("id")
    return {
        "fixture_id": (chosen.get("fixture") or {}).get("id"),
        "home_id":    home_id,
        "away_id":    away_id,
    }


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

    # ── Detalle de partido ────────────────────────────────────────────────
    @staticmethod
    def _lineup_player(p: dict) -> dict:
        pl = p.get("player") or {}
        return {"name": pl.get("name", ""), "number": pl.get("number"), "pos": pl.get("pos", "")}

    def get_fixture_lineups(self, fixture_id: int) -> list:
        """[{team, formation, coach, startXI:[{name,number,pos}], subs:[...]}] (2 equipos)."""
        try:
            raw = self._get("/fixtures/lineups", {"fixture": fixture_id})
        except Exception:
            return []
        out = []
        for t in raw.get("response", []):
            out.append({
                "team":      (t.get("team") or {}).get("name", ""),
                "formation": t.get("formation", ""),
                "coach":     (t.get("coach") or {}).get("name", ""),
                "startXI":   [self._lineup_player(p) for p in (t.get("startXI") or [])],
                "subs":      [self._lineup_player(p) for p in (t.get("substitutes") or [])],
            })
        return out

    def get_fixture_statistics(self, fixture_id: int) -> list:
        """[{team, stats:{tipo: valor}}] (2 equipos)."""
        try:
            raw = self._get("/fixtures/statistics", {"fixture": fixture_id})
        except Exception:
            return []
        out = []
        for t in raw.get("response", []):
            stats = {s.get("type", ""): s.get("value") for s in (t.get("statistics") or [])}
            out.append({"team": (t.get("team") or {}).get("name", ""), "stats": stats})
        return out

    def get_fixture_players(self, fixture_id: int) -> list:
        """[{team, players:[{name,number,pos,rating,minutes,goals,assists,captain,sub}]}] (2 equipos)."""
        try:
            raw = self._get("/fixtures/players", {"fixture": fixture_id})
        except Exception:
            return []
        out = []
        for t in raw.get("response", []):
            players = []
            for p in (t.get("players") or []):
                pl = p.get("player") or {}
                st = (p.get("statistics") or [{}])[0]
                g  = st.get("games") or {}
                go = st.get("goals") or {}
                players.append({
                    "name":    pl.get("name", ""),
                    "number":  g.get("number"),
                    "pos":     g.get("position", ""),
                    "rating":  g.get("rating"),
                    "minutes": g.get("minutes"),
                    "goals":   go.get("total") or 0,
                    "assists": go.get("assists") or 0,
                    "captain": g.get("captain"),
                    "sub":     g.get("substitute"),
                })
            out.append({"team": (t.get("team") or {}).get("name", ""), "players": players})
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
