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

# Status de API-Football → status interno (el que usa el resto del código)
STATUS_MAP = {
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
    "1H": "IN_PLAY", "2H": "IN_PLAY", "ET": "IN_PLAY", "BT": "IN_PLAY",
    "P": "IN_PLAY", "LIVE": "IN_PLAY", "INT": "IN_PLAY",
    "HT": "PAUSED",
    "NS": "TIMED", "TBD": "TIMED",
}

# Round de API-Football → stage interno (el que espera _stage_label)
ROUND_TO_STAGE = {
    "Round of 32":     "ROUND_OF_32",
    "Round of 16":     "ROUND_OF_16",
    "Quarter-finals":  "QUARTER_FINALS",
    "Semi-finals":     "SEMI_FINALS",
    "3rd Place Final": "THIRD_PLACE",
    "Final":           "FINAL",
}

# Instancia (round) de un partido histórico → texto corto en español (para el H2H)
_ROUND_ES = {
    "Final":           "Final",
    "Semi-finals":     "Semifinal",
    "Quarter-finals":  "Cuartos",
    "Round of 16":     "Octavos",
    "Round of 32":     "16avos",
    "3rd Place Final": "3.º puesto",
    "Friendlies":      "Amistoso",
}


def _round_es(rnd: str) -> str:
    """Normaliza la instancia de un partido a una etiqueta corta en español."""
    if not rnd:
        return ""
    if rnd in _ROUND_ES:
        return _ROUND_ES[rnd]
    low = rnd.lower()
    if "group" in low:
        return "Fase de grupos"
    if "qualif" in low:
        return "Eliminatorias"
    if "friendl" in low:
        return "Amistoso"
    if "final" in low and "semi" not in low and "quarter" not in low:
        return "Final"
    return rnd


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
            "photo": (p.get("player") or {}).get("photo", ""),
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

    def get_team_groups(self) -> dict:
        """{nombre_equipo: 'GROUP_X'} desde /standings (API-Football no da el grupo en el fixture)."""
        try:
            raw = self._get("/standings", self._league_params())
        except Exception:
            return {}
        out = {}
        resp = raw.get("response") or []
        if not resp:
            return out
        for grp in (resp[0].get("league") or {}).get("standings") or []:
            for row in grp:
                g = row.get("group", "") or ""
                if not g.startswith("Group "):
                    continue
                suffix = g[len("Group "):].strip()
                # Solo grupos reales de una letra (A-L). Ignora el agregado "Group Stage".
                if len(suffix) != 1 or not suffix.isalpha():
                    continue
                name = (row.get("team") or {}).get("name", "")
                if name:
                    out[name] = "GROUP_" + suffix
        return out

    def get_fixture_events(self, fixture_id: int) -> list:
        """Devuelve la lista cruda de eventos de un partido."""
        try:
            data = self._get("/fixtures/events", {"fixture": fixture_id})
            return data.get("response") or []
        except Exception:
            return []

    def get_h2h(self, id1: int, id2: int, last: int = 6) -> list:
        """Últimos enfrentamientos entre dos equipos (más nuevo primero):
        [{date, comp, season, home, away, gh, ga}]. Solo partidos ya jugados."""
        try:
            raw = self._get("/fixtures/headtohead", {"h2h": f"{id1}-{id2}", "last": last})
        except Exception:
            return []
        out = []
        for fx in raw.get("response", []):
            t = fx.get("teams") or {}
            g = fx.get("goals") or {}
            lg = fx.get("league") or {}
            f = fx.get("fixture") or {}
            gh, ga = g.get("home"), g.get("away")
            if gh is None or ga is None:
                continue
            out.append({
                "date":   (f.get("date") or "")[:10],
                "comp":   lg.get("name", ""),
                "round":  _round_es(lg.get("round", "")),
                "season": lg.get("season"),
                "home":   (t.get("home") or {}).get("name", ""),
                "away":   (t.get("away") or {}).get("name", ""),
                "gh":     gh,
                "ga":     ga,
            })
        out.sort(key=lambda m: m.get("date", ""), reverse=True)
        return out

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

    def get_player_club(self, player_id: int, seasons=(2025, 2026)):
        """Club actual del jugador (7.1): {'club', 'country'} desde sus estadísticas.
        Las ligas europeas 2025-26 están bajo temporada 2025; las de año calendario
        bajo 2026 → probamos 2025 primero y, si no hay, 2026. None si no se encuentra.
        Puede lanzar (red/rate-limit): el caller decide si cachear o reintentar."""
        for season in seasons:
            raw = self._get("/players", {"id": player_id, "season": season})
            resp = raw.get("response") or []
            if not resp:
                continue
            best = None  # (partidos, club, país)
            for s in resp[0].get("statistics", []):
                lg = s.get("league") or {}
                tm = s.get("team") or {}
                country = lg.get("country")
                if not country or country == "World":   # descartar selección nacional
                    continue
                apps = ((s.get("games") or {}).get("appearences")) or 0
                if best is None or apps > best[0]:
                    best = (apps, tm.get("name"), country)
            if best and best[1]:
                return {"club": best[1], "country": best[2]}
        return None

    # ── Detalle de partido ────────────────────────────────────────────────
    @staticmethod
    def _lineup_player(p: dict) -> dict:
        pl = p.get("player") or {}
        return {"name": pl.get("name", ""), "number": pl.get("number"), "pos": pl.get("pos", "")}

    def get_venue(self, **params) -> dict:
        """Detalle de un estadio (capacity, surface, image, address). Por id o search."""
        try:
            raw = self._get("/venues", params)
        except Exception:
            return {}
        resp = raw.get("response") or []
        return resp[0] if resp else {}

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
                    "id":      pl.get("id"),
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
