"""
Construye `posts.json`: datos estructurados de cada partido jugado para el
armador de publicaciones de Instagram del panel de admin. SOLO datos (sin HTML)
— el dibujo de la imagen lo hace el navegador con Canvas.

Lo consume admin.html (pestaña "Posts") vía /api/posts. Se regenera por el cron
junto con el resto de la rama `data`.
"""

from countries import nombre_es, iso_code
from motm import motm_for
from scenarios import compute_group_scenarios, team_phrase
from standings import compute_stats, rank_group


def _num(v):
    try:
        return float(str(v).replace("%", "").strip() or 0)
    except Exception:
        return 0.0


def _team_players(detail, team_name):
    """Jugadores de un equipo que jugaron, con rating, ordenados de mejor a peor."""
    if not detail:
        return []
    target = nombre_es(team_name)
    out = []
    for entry in detail.get("players", []):
        if nombre_es(entry.get("team", "")) != target:
            continue
        for p in entry.get("players", []):
            if (p.get("minutes") or 0) <= 0:
                continue
            out.append({
                "name": p.get("name", ""),
                "rating": round(_num(p.get("rating")), 1),
                "min": p.get("minutes") or 0,
                "g": p.get("goals") or 0,
                "a": p.get("assists") or 0,
                "cap": bool(p.get("captain")),
            })
    out.sort(key=lambda x: x["rating"], reverse=True)
    return out


def _team_obj(name, goals):
    return {"name": nombre_es(name), "iso": iso_code(name), "goals": goals}


# Mismas filas/orden que la sección "Estadísticas del partido" de Ver Partido.
_STAT_ROWS = [
    ("Ball Possession", "Posesión"),
    ("Total Shots",     "Tiros"),
    ("Shots on Goal",   "Tiros al arco"),
    ("Corner Kicks",    "Córners"),
    ("Fouls",           "Faltas"),
    ("Offsides",        "Offsides"),
    ("Yellow Cards",    "Amarillas"),
    ("Passes %",        "Precisión pases"),
]


def _match_stats(detail, home_name, away_name):
    """Estadísticas del partido (home vs away), en el mismo orden que Ver Partido."""
    sts = (detail or {}).get("statistics") or []
    he = ae = None
    for e in sts:
        en = nombre_es(e.get("team", ""))
        if en == nombre_es(home_name) and he is None:
            he = e
        elif en == nombre_es(away_name) and ae is None:
            ae = e
    if not he or not ae:
        return []
    hs, as_ = he.get("stats", {}) or {}, ae.get("stats", {}) or {}
    out = []
    for key, label in _STAT_ROWS:
        if key not in hs and key not in as_:
            continue
        out.append({
            "label": label,
            "home": hs.get(key) if hs.get(key) is not None else "0",
            "away": as_.get(key) if as_.get(key) is not None else "0",
        })
    return out


def build_team_statuses(standings):
    """
    Estado de clasificación por equipo, derivado de los escenarios de grupo (la
    misma fuente que "qué se juega" del home). Por equipo:
      status: 'classified' | 'eliminated' | 'alive'
      locked: posición asegurada (1..4) si solo puede terminar ahí, si no None
      positions: posiciones finales posibles
    Permite generar imágenes de "clasificado", "posición asegurada" y "eliminado".
    """
    thirds_adv = {e.get("team") for e in standings.get("_thirds_advancing", [])}
    # ¿Terminaron TODOS los grupos? Un 3.º solo está clasificado/eliminado como mejor
    # tercero cuando el cuadro de terceros está cerrado (Anexo C depende de los 12 grupos).
    # Antes de eso, _thirds_advancing es provisional y afirmar "Clasificado" miente.
    all_groups_done = True
    for _gk, _gv in standings.items():
        if isinstance(_gk, str) and _gk.startswith("GROUP_"):
            _ms = _gv.get("matches", [])
            if not (_ms and all(getattr(_m, "played", False) for _m in _ms)):
                all_groups_done = False
                break
    out = []
    for gkey, gval in standings.items():
        if not (isinstance(gkey, str) and gkey.startswith("GROUP_")):
            continue
        glabel = gkey.replace("GROUP_", "")
        teams = gval.get("teams", [])
        matches = gval.get("matches", [])
        done = bool(matches) and all(getattr(m, "played", False) for m in matches)
        sc = compute_group_scenarios(teams, matches)
        # rankear acá (no depender del orden de entrada) para la posición actual
        ranked = rank_group(teams, compute_stats(teams, matches), matches)
        for i, t in enumerate(ranked):
            pos = i + 1
            if t in sc:
                positions = list(sc[t]["positions"])
                status = sc[t]["status"]
            else:                          # grupo terminado (o sin escenarios): posición fija
                positions = [pos]
                status = "classified" if pos <= 2 else ("eliminated" if pos == 4 else "alive")
            locked = positions[0] if len(positions) == 1 else None
            # ajustes por posición asegurada / mejor tercero
            if locked in (1, 2):
                status = "classified"
            elif locked == 4:
                status = "eliminated"
            elif locked == 3:
                # Solo afirmar clasificado/eliminado como mejor 3.º cuando TODOS los
                # grupos terminaron. Si todavía juegan otros grupos, el 3.º "depende".
                if all_groups_done:
                    status = "classified" if t in thirds_adv else "eliminated"
                else:
                    status = "alive"
            out.append({
                "name": nombre_es(t),
                "iso": iso_code(t),
                "group": glabel,
                "status": status,
                "locked": locked,
                "positions": positions,
            })
    return out


def build_upcoming(all_matches, standings):
    """
    Partidos POR VENIR (no jugados, con ambos equipos definidos) para el editor de
    "Previa": estadio, horario (utc) y qué se juega cada equipo. El stake sale del
    motor de escenarios (team_phrase), igual que "qué se juega" del home.
    """
    group_sc = {}
    for gkey, gval in standings.items():
        if isinstance(gkey, str) and gkey.startswith("GROUP_"):
            group_sc[gkey] = compute_group_scenarios(gval.get("teams", []), gval.get("matches", []))

    def stake(sc, team, opp):
        e = sc.get(team)
        return team_phrase(e, opponent=nombre_es(opp)) if e else ""

    out = []
    for m in all_matches:
        if m.get("status") not in ("TIMED", "", None):
            continue
        if m.get("home_goals") is not None or m.get("away_goals") is not None:
            continue
        mid = str(m.get("match_id") or "")
        home, away = m.get("home", ""), m.get("away", "")
        if not mid or mid == "None" or not home or not away:
            continue  # cruce aún sin definir (bracket TBD) → no se puede previsualizar
        grp = (m.get("group") or "").replace("GROUP_", "")
        stage = f"Grupo {grp}" if grp else (m.get("stage", "") or "").replace("_", " ").title()
        md = m.get("matchday")
        stage_label = f"{stage} · Fecha {md}" if (grp and md) else stage
        sc = group_sc.get(m.get("group"), {})
        out.append({
            "id": mid,
            "stage": stage_label,
            "utc": m.get("utc_date", ""),
            "venue": " · ".join(x for x in [m.get("venue_name", ""), m.get("venue_city", "")] if x),
            "home": {"name": nombre_es(home), "iso": iso_code(home), "stake": stake(sc, home, away)},
            "away": {"name": nombre_es(away), "iso": iso_code(away), "stake": stake(sc, away, home)},
        })
    out.sort(key=lambda x: x.get("utc", ""))
    return out


def build_posts(all_matches, details):
    """
    Devuelve {"matches": [...]} con los partidos que tienen marcador (jugados o
    en curso). `all_matches` son los partidos internos (con goals_detail ya
    mergeados) y `details` el dict {match_id: match_details} con los ratings.
    """
    out = []
    for m in all_matches:
        mid = str(m.get("match_id") or "")
        if not mid or mid == "None":
            continue
        hg, ag = m.get("home_goals"), m.get("away_goals")
        if hg is None and ag is None:
            continue  # todavía no se jugó: no hay nada que postear

        home, away = m.get("home", ""), m.get("away", "")
        grp = (m.get("group") or "").replace("GROUP_", "")
        stage = f"Grupo {grp}" if grp else (m.get("stage", "") or "").replace("_", " ").title()
        md = m.get("matchday")
        stage_label = f"{stage} · Fecha {md}" if (grp and md) else stage

        goals = [{
            "min": gd.get("minute", ""),
            "scorer": gd.get("scorer", ""),
            "team": nombre_es(gd.get("team", "")),
            "assist": gd.get("assist", ""),
            "type": gd.get("type", "NORMAL"),
        } for gd in (m.get("goals_detail") or [])]

        detail = details.get(mid)
        out.append({
            "id": mid,
            "stage": stage_label,
            "finished": m.get("status") == "FINISHED",
            "venue": " · ".join(x for x in [m.get("venue_name", ""), m.get("venue_city", "")] if x),
            "referee": m.get("referee", ""),
            "home": _team_obj(home, hg),
            "away": _team_obj(away, ag),
            "goals": goals,
            "stats": _match_stats(detail, home, away),
            "motm": motm_for(home, away),
            "players": {
                nombre_es(home): _team_players(detail, home),
                nombre_es(away): _team_players(detail, away),
            },
        })
    return {"matches": out}
