# -*- coding: utf-8 -*-
"""Motor de agregación de estadísticas del torneo. Recorre UNA vez los datos que ya
cacheamos (partidos, detalle por partido con stats crudas, eventos) y produce un dict
con todos los agregados por equipo + lista de partidos + resumen, listo para servir
como estadisticas.json. Sin llamadas a la API: solo CPU sobre datos en memoria.

Lo consume la página /estadisticas (tabla de confederaciones, comparadores, rankings)."""
from datetime import datetime, timezone
from typing import Dict, List

from countries import nombre_es, _PAISES, TEAM_CONFEDERATION, CONFEDERACIONES


def _num(v) -> float:
    """Parsea valores de la API que vienen como int, '44%', '1.12' o None → float."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace("%", ""))
    except ValueError:
        return 0.0


def _parse_min(s):
    """'6' → (6, 0); '45+2' → (45, 2); inparseable → (None, 0)."""
    s = str(s or "")
    if "+" in s:
        a, b = s.split("+", 1)
        try:
            return (int(a), int(b))
        except ValueError:
            return (None, 0)
    try:
        return (int(s), 0)
    except ValueError:
        return (None, 0)


def _minval(s) -> int:
    """Valor ordenable del minuto (base*100+descuento)."""
    base, extra = _parse_min(s)
    return (base if base is not None else 999) * 100 + extra


_GOAL_BANDS = ["1-15", "16-30", "31-45", "46-60", "61-75", "76-90+"]


_POS_ES = {"G": "Arquero", "D": "Defensor", "M": "Mediocampista", "F": "Delantero"}
# stats ampliadas por jugador (sumadas a lo largo del torneo) para el comparador
_PSTAT = ("shots", "shots_on", "passes", "key_passes", "dribbles", "tackles",
          "duels_won", "fouls_drawn", "fouls_committed", "saves")


def _agg_players(match_details: Dict, finished_ids, pid_league: Dict) -> list:
    """Agrega el rendimiento de cada jugador a lo largo del torneo (desde los datos
    por partido): goles, asistencias, minutos, rating promedio, posición, liga.
    Solo cuenta partidos terminados (un partido en vivo daría datos parciales)."""
    players = {}
    for mid, d in match_details.items():
        if mid not in finished_ids:
            continue
        for ts in d.get("players") or []:
            team = ts.get("team")
            for p in ts.get("players") or []:
                pid = p.get("id")
                key = str(pid) if pid else f'{p.get("name")}|{team}'
                pl = players.get(key)
                if pl is None:
                    pl = {"name": p.get("name"), "team": team, "pos": p.get("pos") or "",
                          "league": pid_league.get(pid, ""),
                          "goals": 0, "assists": 0, "minutes": 0, "matches": 0,
                          "_rs": 0.0, "_rn": 0}
                    for k in _PSTAT:
                        pl[k] = 0
                    players[key] = pl
                pl["goals"] += p.get("goals") or 0
                pl["assists"] += p.get("assists") or 0
                pl["minutes"] += p.get("minutes") or 0
                pl["matches"] += 1
                for k in _PSTAT:
                    pl[k] += p.get(k) or 0
                if p.get("pos"):
                    pl["pos"] = p.get("pos")
                try:
                    if p.get("rating"):
                        pl["_rs"] += float(p["rating"]); pl["_rn"] += 1
                except (TypeError, ValueError):
                    pass
    out = []
    for pl in players.values():
        pl["ga"] = pl["goals"] + pl["assists"]
        pl["rating"] = round(pl["_rs"] / pl["_rn"], 2) if pl["_rn"] else 0.0
        pl["posEs"] = _POS_ES.get(pl["pos"], pl["pos"])
        del pl["_rs"]; del pl["_rn"]
        out.append(pl)
    return out


def _player_leaderboards(plist: list) -> dict:
    """Top-N por cada métrica de jugador, listos para renderizar."""
    def top(key, n, filt=None):
        pool = [p for p in plist if (filt is None or filt(p))]
        pool.sort(key=lambda p: p[key], reverse=True)
        return pool[:n]
    by_pos = {pos: top("rating", 3, lambda p, q=pos: p["pos"] == q and p["matches"] >= 2 and p["rating"] > 0)
              for pos in ("G", "D", "M", "F")}
    # lista completa (los que jugaron) para el comparador jugador vs jugador.
    # Solo los campos que usa el comparador → JSON más liviano.
    _af = ("name", "team", "pos", "goals", "assists", "ga", "minutes", "rating", "matches") + _PSTAT
    all_players = [{k: p[k] for k in _af}
                   for p in sorted((q for q in plist if q["minutes"] > 0),
                                   key=lambda p: (-p["ga"], -p["minutes"]))]
    return {
        "ga": top("ga", 15, lambda p: p["ga"] > 0),
        "rating": top("rating", 10, lambda p: p["matches"] >= 2 and p["rating"] > 0),
        "minutes": top("minutes", 10, lambda p: p["minutes"] > 0),
        "byPos": by_pos,
        "all": all_players,
    }


def _league_perf(plist: list) -> list:
    """Rendimiento agregado de los jugadores agrupados por su liga (para liga vs liga)."""
    L = {}
    for p in plist:
        lg = p.get("league")
        if not lg:
            continue
        d = L.get(lg)
        if d is None:
            d = {"league": lg, "players": 0, "goals": 0, "assists": 0, "minutes": 0,
                 "_rs": 0.0, "_rn": 0}
            L[lg] = d
        d["players"] += 1; d["goals"] += p["goals"]; d["assists"] += p["assists"]
        d["minutes"] += p["minutes"]
        if p["rating"] > 0:
            d["_rs"] += p["rating"]; d["_rn"] += 1
    out = []
    for d in L.values():
        if d["players"] < 8:   # ligas con muy pocos jugadores no sirven para comparar
            continue
        d["ga"] = d["goals"] + d["assists"]
        d["rating"] = round(d["_rs"] / d["_rn"], 2) if d["_rn"] else 0.0
        del d["_rs"]; del d["_rn"]
        out.append(d)
    out.sort(key=lambda x: -x["players"])
    return out


def _agg_squads(squads: Dict) -> dict:
    """Demografía de los planteles: de qué ligas vienen, clubes más representados,
    edades por selección y por confederación, % de legionarios."""
    from collections import Counter
    from countries import pais_liga_es
    leagues, clubs = Counter(), Counter()
    team_age, legion = [], []
    foreign_total = foreign_abroad = g_sum = g_n = 0
    confed_sum, confed_n = {}, {}
    for team, sq in squads.items():
        es_team = nombre_es(team)
        confed = TEAM_CONFEDERATION.get(team, "")
        iso = _PAISES.get(team, (team, ""))[1]
        asum = an = t_abroad = t_total = 0
        for p in sq.get("players", []):
            cc, club, age = p.get("club_country"), p.get("club"), p.get("age")
            if cc:
                liga = pais_liga_es(cc)
                leagues[liga] += 1
                foreign_total += 1
                t_total += 1
                if liga != es_team:
                    foreign_abroad += 1
                    t_abroad += 1
            if club:
                clubs[club] += 1
            if age:
                asum += age; an += 1
                if confed:
                    confed_sum[confed] = confed_sum.get(confed, 0) + age
                    confed_n[confed] = confed_n.get(confed, 0) + 1
        if an:
            team_age.append({"es": es_team, "iso": iso, "age": round(asum / an, 1)})
            g_sum += asum; g_n += an
        if t_total:
            legion.append({"es": es_team, "iso": iso, "abroad": t_abroad, "total": t_total,
                           "pct": round(t_abroad / t_total * 100)})
    team_age.sort(key=lambda x: x["age"])
    confed_age = sorted(
        ({"confed": c, "age": round(confed_sum[c] / confed_n[c], 1)} for c in confed_sum),
        key=lambda x: x["age"])
    return {
        "total_players": foreign_total,
        "avg_age": round(g_sum / g_n, 1) if g_n else 0,
        "foreign_pct": round(foreign_abroad / foreign_total * 100) if foreign_total else 0,
        "league_count": len(leagues),
        "leagues": [{"country": k, "count": v} for k, v in leagues.most_common(12)],
        "clubs": [{"club": k, "count": v} for k, v in clubs.most_common(10)],
        "youngest": team_age[:6],
        "oldest": list(reversed(team_age[-6:])),
        "confed_age": confed_age,
        "legionarios": sorted(legion, key=lambda x: -x["pct"]),
    }


def _band(base: int) -> str:
    if base <= 15:
        return "1-15"
    if base <= 30:
        return "16-30"
    if base <= 45:
        return "31-45"
    if base <= 60:
        return "46-60"
    if base <= 75:
        return "61-75"
    return "76-90+"


# stat cruda de API-Football → clave interna. possession y passes_pct se PROMEDIAN
# (son %); el resto se SUMA. Las tarjetas las tomamos de los eventos (más confiables).
_SUM_KEYS = {
    "Total Shots": "shots", "Shots on Goal": "shots_on", "Shots off Goal": "shots_off",
    "Blocked Shots": "shots_blocked", "Shots insidebox": "shots_inbox",
    "Shots outsidebox": "shots_outbox", "Corner Kicks": "corners", "Fouls": "fouls",
    "Offsides": "offsides", "Goalkeeper Saves": "saves", "Total passes": "passes",
    "Passes accurate": "passes_acc", "expected_goals": "xg",
    "goals_prevented": "goals_prevented",
}
_SUM_FIELDS = list(_SUM_KEYS.values())


def _new_team(name: str) -> dict:
    t = {"name": name, "es": nombre_es(name), "iso": _PAISES.get(name, (name, ""))[1],
         "confed": TEAM_CONFEDERATION.get(name, ""), "group": "",
         "played": 0, "won": 0, "drawn": 0, "lost": 0,
         "gf": 0, "ga": 0, "gd": 0, "points": 0, "yc": 0, "rc": 0,
         "clean_sheets": 0, "stat_n": 0, "r16": 0,
         "possession_avg": 0.0, "passes_pct_avg": 0.0,
         "_pos_sum": 0.0, "_pp_sum": 0.0}
    for f in _SUM_FIELDS:
        t[f] = 0.0
    return t


def build_stats(standings: Dict, match_details: Dict, matchups=None) -> dict:
    teams: Dict[str, dict] = {}
    # equipos proyectados a octavos = los que hoy ocupan el R32 (top 2 + mejores terceros)
    qualified = set()
    for mu in matchups or []:
        for side in (mu.get("equipo1"), mu.get("equipo2")):
            if side in TEAM_CONFEDERATION:
                qualified.add(side)

    def T(name: str) -> dict:
        if name not in teams:
            teams[name] = _new_team(name)
        return teams[name]

    # ── 1) Partidos: resultados + eventos (goles/tarjetas van pegados al partido) ─
    matches_out: List[dict] = []
    seen = set()
    goals_total = most_goals = 0
    penalties = own_goals = yc_total = rc_total = 0
    most_goals_match = biggest_win = fastest = latest = None
    bands = {b: 0 for b in _GOAL_BANDS}
    first_half = second_half = stoppage_goals = 0
    comebacks = []
    duos = {}
    referees = {}
    finished_ids = set()
    for ms in standings.get("_matches_by_date", {}).values():
        for m in ms:
            mid = m.get("match_id")
            if mid in seen:
                continue
            seen.add(mid)
            home, away = m.get("home"), m.get("away")
            if not home or not away:
                continue
            status = m.get("status", "")
            hg, ag = m.get("home_goals"), m.get("away_goals")
            finished = status == "FINISHED" and hg is not None and ag is not None
            matches_out.append({
                "id": mid, "home": home, "away": away, "hg": hg, "ag": ag,
                "status": status, "group": m.get("group", ""), "utc": m.get("utc_date", ""),
                "venue": " · ".join(x for x in [m.get("venue_name", ""), m.get("venue_city", "")] if x),
                "hc": TEAM_CONFEDERATION.get(home, ""), "ac": TEAM_CONFEDERATION.get(away, ""),
            })
            H, A = T(home), T(away)  # asegura que TODO equipo del fixture exista
            grp = m.get("group", "")
            if grp:
                H["group"] = A["group"] = grp
            if finished:
                finished_ids.add(str(mid))
                H["played"] += 1; A["played"] += 1
                H["gf"] += hg; H["ga"] += ag; A["gf"] += ag; A["ga"] += hg
                if ag == 0:
                    H["clean_sheets"] += 1
                if hg == 0:
                    A["clean_sheets"] += 1
                if hg > ag:
                    H["won"] += 1; H["points"] += 3; A["lost"] += 1
                elif hg < ag:
                    A["won"] += 1; A["points"] += 3; H["lost"] += 1
                else:
                    H["drawn"] += 1; A["drawn"] += 1; H["points"] += 1; A["points"] += 1
                tot = hg + ag
                goals_total += tot
                if tot > most_goals:
                    most_goals, most_goals_match = tot, {"home": home, "away": away, "hg": hg, "ag": ag}
                marg = abs(hg - ag)
                if biggest_win is None or marg > biggest_win["margin"]:
                    biggest_win = {"home": home, "away": away, "hg": hg, "ag": ag, "margin": marg}

            # goles del partido: tipos, minutos (heatmap), tiempos y remontadas.
            # El 'team' del evento es siempre el beneficiario (incluye goles en contra),
            # así que el marcador corriendo suma directo a g['team'].
            if finished:
                gd = sorted(m.get("goals_detail") or [], key=lambda x: _minval(x.get("minute")))
                sh = sa = defH = defA = 0
                ok_seq = True
                for g in gd:
                    base, extra = _parse_min(g.get("minute"))
                    if base is not None:
                        # tipos y bandas se cuentan sobre el MISMO conjunto (goles con
                        # minuto) → el heatmap y el desglose por tipo siempre cuadran.
                        ty = g.get("type", "NORMAL")
                        if ty == "PENALTY":
                            penalties += 1
                        elif ty == "OWN":
                            own_goals += 1
                        bands[_band(base)] += 1
                        if base <= 45:
                            first_half += 1
                        else:
                            second_half += 1
                        if extra:
                            stoppage_goals += 1
                        sv = base * 100 + extra
                        disp = f"{base}+{extra}" if extra else str(base)
                        if fastest is None or sv < fastest["sv"]:
                            fastest = {"sv": sv, "minute": disp, "scorer": g.get("scorer"), "team": g.get("team")}
                        if latest is None or sv > latest["sv"]:
                            latest = {"sv": sv, "minute": disp, "scorer": g.get("scorer"), "team": g.get("team")}
                    if g.get("assist") and g.get("scorer"):
                        dk = (g.get("team"), g.get("assist"), g.get("scorer"))
                        duos[dk] = duos.get(dk, 0) + 1
                    gt = g.get("team")
                    if gt == home:
                        sh += 1
                    elif gt == away:
                        sa += 1
                    else:
                        ok_seq = False
                    if sh < sa:
                        defH = max(defH, sa - sh)
                    if sa < sh:
                        defA = max(defA, sh - sa)
                if ok_seq and sh == hg and sa == ag:
                    if defH > 0 and hg >= ag:
                        comebacks.append({"team": home, "opp": away, "deficit": defH,
                                          "gf": hg, "ga": ag, "win": hg > ag})
                    if defA > 0 and ag >= hg:
                        comebacks.append({"team": away, "opp": home, "deficit": defA,
                                          "gf": ag, "ga": hg, "win": ag > hg})
            # tarjetas: solo de partidos TERMINADOS (consistente con played/stats; un
            # partido en vivo daría tarjetas tentativas y sesgaría tarjetas-por-partido)
            if finished:
                m_yc = m_rc = 0
                for b in m.get("bookings") or []:
                    tm = b.get("team")
                    if b.get("card") == "RED":
                        rc_total += 1; m_rc += 1
                        if tm in teams:
                            teams[tm]["rc"] += 1
                    else:
                        yc_total += 1; m_yc += 1
                        if tm in teams:
                            teams[tm]["yc"] += 1
                ref = (m.get("referee") or "").strip()
                if ref:
                    rd = referees.setdefault(ref, {"name": ref, "matches": 0, "yc": 0, "rc": 0})
                    rd["matches"] += 1; rd["yc"] += m_yc; rd["rc"] += m_rc

    # ── 2) Stats crudas por partido (match_details) — solo partidos TERMINADOS ─
    # (un partido en vivo tiene stats pero su resultado no cuenta aún; mezclarlos
    # sesga la eficiencia y los promedios). Por eso gateamos a finished_ids.
    for mid, d in match_details.items():
        if mid not in finished_ids:
            continue
        for ts in d.get("statistics") or []:
            name = ts.get("team")
            st = ts.get("stats") or {}
            if not name:
                continue
            t = T(name)
            t["stat_n"] += 1
            t["_pos_sum"] += _num(st.get("Ball Possession"))
            t["_pp_sum"] += _num(st.get("Passes %"))
            for api_key, ik in _SUM_KEYS.items():
                if api_key in st:
                    t[ik] += _num(st[api_key])

    # ── 3) Finalizar promedios y derivados ────────────────────────────────────
    for name, t in teams.items():
        t["gd"] = t["gf"] - t["ga"]
        t["r16"] = 1 if name in qualified else 0
        n = t["stat_n"] or 1
        t["possession_avg"] = round(t["_pos_sum"] / n, 1) if t["stat_n"] else 0.0
        t["passes_pct_avg"] = round(t["_pp_sum"] / n, 1) if t["stat_n"] else 0.0
        t["xg"] = round(t["xg"], 2)
        t["goals_prevented"] = round(t["goals_prevented"], 2)
        for f in _SUM_FIELDS:
            if f not in ("xg", "goals_prevented"):
                t[f] = int(t[f])
        del t["_pos_sum"]; del t["_pp_sum"]

    for x in (fastest, latest):
        if x:
            x.pop("sv", None)
    comebacks.sort(key=lambda c: (c["win"], c["deficit"]), reverse=True)

    # jugadores (con su liga) + rendimiento por liga + árbitros
    from countries import pais_liga_es
    squads = standings.get("_squads", {})
    pid_league = {}
    for sq in squads.values():
        for p in sq.get("players", []):
            if p.get("id") and p.get("club_country"):
                pid_league[p["id"]] = pais_liga_es(p["club_country"])
    plist = _agg_players(match_details, finished_ids, pid_league)
    refs_out = []
    for r in referees.values():
        if r["matches"] >= 2:
            r["cards"] = r["yc"] + r["rc"]
            r["cpm"] = round(r["cards"] / r["matches"], 1)
            refs_out.append(r)
    refs_out.sort(key=lambda x: -x["cpm"])
    refs_out = refs_out[:10]

    played_matches = sum(1 for m in matches_out if m["status"] == "FINISHED")
    tournament = {
        "matches_played": played_matches,
        "goals_total": goals_total,
        "goals_per_match": round(goals_total / played_matches, 2) if played_matches else 0,
        "yellow_total": yc_total, "red_total": rc_total,
        "penalties": penalties, "own_goals": own_goals,
        "clean_sheets": sum(t["clean_sheets"] for t in teams.values()),
        "most_goals_match": most_goals_match, "biggest_win": biggest_win,
        "fastest_goal": fastest, "latest_goal": latest,
    }

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "tournament": tournament,
        "teams": teams,
        "matches": matches_out,
        "confedNames": CONFEDERACIONES,
        "goals": {
            "bands": bands, "band_order": _GOAL_BANDS,
            "first_half": first_half, "second_half": second_half,
            "stoppage": stoppage_goals,
            # de jugada = total de goles con minuto − penales − en contra (mismo origen
            # que las bandas, así heatmap y tipos suman lo mismo)
            "normal": max(first_half + second_half - penalties - own_goals, 0),
            "penalty": penalties, "own": own_goals,
        },
        "comebacks": comebacks,
        "players": _player_leaderboards(plist),
        "leaguePerf": _league_perf(plist),
        "referees": refs_out,
        "squads": _agg_squads(squads),
        "duos": sorted(
            [{"team": t, "assist": a, "scorer": s, "count": c}
             for (t, a, s), c in duos.items() if c >= 2],
            key=lambda x: -x["count"])[:8],
    }


def render_stats_json(standings: Dict, matchups=None) -> str:
    """Serializa el agregado a JSON (para estadisticas.json)."""
    import json
    data = build_stats(standings, standings.get("_match_details", {}), matchups)
    return json.dumps(data, ensure_ascii=False)
