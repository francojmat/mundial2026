"""
Genera mundial2026.html + data.json.
Se usa localmente (con --key) y en GitHub Actions (con FOOTBALL_API_KEY).

Uso local:
  python generate.py --key TU_API_KEY
"""
import argparse
import os
import sys

sys.path.insert(0, ".")

import json

from api_client import WorldCupClient, build_standings
from apifootball_client import APIFootballClient
from bracket import build_round_of_32
from data_renderer import render_data_json
from html_renderer import render_html
from pages import (render_plantel_shell, render_squad_fragment,
                   render_seleccion_fragment, render_seleccion_shell, render_cruces_block)
from countries import nombre_es
from match_page import render_partido_shell, render_match_fragment


def main(api_key: str, html_out: str, json_out: str, apifootball_key: str = None) -> None:
    apifootball = APIFootballClient(apifootball_key)  # proveedor principal de datos
    scorers_client = WorldCupClient(api_key) if api_key else None  # solo goleadores
    print(f"Proveedor: API-Football. Goleadores: {'football-data' if scorers_client else 'sin lista'}.")
    print("Fetching datos...")
    standings = build_standings(scorers_client, apifootball)

    # GUARDA DE RESILIENCIA: si API-Football no devolvió fixtures (rate limit del día,
    # outage, key vencida), los grupos quedan vacíos. Regenerar y publicar eso TIRA el
    # sitio en vivo (home en blanco). Mejor congelar la última versión buena: abortamos
    # sin escribir NINGÚN archivo, así el cron re-publica lo que ya estaba (bueno).
    _real_groups = [k for k in standings if isinstance(k, str) and k.startswith("GROUP_")]
    if not _real_groups:
        print("ABORT: API-Football devolvió 0 grupos (rate limit / outage). "
              "No se sobrescribe ningún archivo; se mantiene la última versión buena.")
        return

    matchups = build_round_of_32(standings, standings.get("_thirds_advancing", []))

    from tournament import enrich_h2h, enrich_venue_weather
    enrich_h2h(matchups, apifootball)
    enrich_venue_weather(standings.get("_venues", []))
    # 8.5 — pasar el clima de cada sede a sus partidos (para Ver Partido)
    _wmap = {v.get("name"): v.get("weather") for v in standings.get("_venues", []) if v.get("weather")}
    for _ms in standings.get("_matches_by_date", {}).values():
        for _m in _ms:
            _w = _wmap.get(_m.get("venue_name"))
            if _w:
                _m["weather"] = _w

    html = render_html(standings, matchups)
    data_json = render_data_json(standings, matchups)
    from data_renderer import render_data_extra_json
    data2_json = render_data_extra_json(standings, matchups)

    # live_windows.json — ventanas horarias de los partidos NO terminados. El Worker
    # lo lee (barato, desde la rama data) y solo le pega a API-Football en /api/live
    # cuando hay un partido dentro de su ventana. Fuera de horario: 0 llamadas.
    from datetime import datetime as _dt
    _windows = []
    for _ms in standings.get("_matches_by_date", {}).values():
        for _m in _ms:
            if _m.get("status") == "FINISHED":
                continue
            _u = (_m.get("utc_date") or "").replace("Z", "+00:00")
            try:
                _start = _dt.fromisoformat(_u).timestamp() * 1000
            except (ValueError, TypeError):
                continue
            # ventana generosa: 15 min antes del inicio hasta 3h30 después
            # (cubre demoras de kickoff + prórroga + penales + colchón).
            _windows.append([int(_start - 15 * 60 * 1000), int(_start + 210 * 60 * 1000)])
    live_windows_json = json.dumps({"windows": _windows}, ensure_ascii=False)

    # sim.json — datos de grupos estructurados para el simulador (motor en JS).
    # Los jugados van con su resultado; los pendientes con played=False (los fija el usuario).
    sim_groups = {}
    for gkey, gval in standings.items():
        if not (isinstance(gkey, str) and gkey.startswith("GROUP_")):
            continue
        sim_groups[gkey.replace("GROUP_", "")] = {
            "teams": gval.get("teams", []),
            "matches": [{"h": m.home, "a": m.away, "hg": m.home_goals, "ag": m.away_goals,
                         "played": m.played, "status": m.status} for m in gval.get("matches", [])],
        }
    # Estructura estática del bracket + Anexo C, serializadas DESDE el Python (misma fuente
    # que el server) para que el motor JS arme el R32 igual. Clave Anexo C = 8 letras ordenadas.
    from bracket import _ANNEX_C, _BRACKET, _SLOT_TO_PARTIDO, _SCHEDULE
    sim_annexc = {"".join(sorted(k)): v for k, v in _ANNEX_C.items()}
    sim_bracket = [[num, list(s1), list(s2)] for num, s1, s2 in _BRACKET]
    from countries import _PAISES, nombre_es
    _sim_teams = sorted({t for g in sim_groups.values() for t in g["teams"]})
    sim_json = json.dumps({
        "groups": sim_groups,
        "annexC": sim_annexc,
        "bracket": sim_bracket,
        "slotToPartido": _SLOT_TO_PARTIDO,
        "schedule": {str(n): list(v) for n, v in _SCHEDULE.items()},
        "iso": {t: _PAISES.get(t, (t, ""))[1] for t in _sim_teams},
        "name": {t: nombre_es(t) for t in _sim_teams},
    }, ensure_ascii=False)
    from simulador import render_simulador_shell
    from bracket_widget import BRACKET_CSS, BRACKET_JS  # bracket compartido con el home

    outputs = [(html_out, html), (json_out, data_json), ("data2.json", data2_json),
               ("live_windows.json", live_windows_json), ("sim.json", sim_json),
               ("simulador.html", render_simulador_shell(matchups)),
               ("bracket.css", BRACKET_CSS), ("bracket.js", BRACKET_JS)]

    # Sección de estadísticas (OPCIONAL: solo si los módulos están en el deploy).
    # Permite publicar el resto (incluido posts.json) sin commitear ese trabajo aún.
    try:
        from stats import render_stats_json
        from estadisticas import render_estadisticas_shell
        outputs.append(("estadisticas.json", render_stats_json(standings, matchups)))
        outputs.append(("estadisticas.html", render_estadisticas_shell()))
    except ImportError:
        pass

    # Páginas de plantel (solo si API-Football está activo y hay planteles cacheados)
    squads = standings.get("_squads", {})
    if squads:
        from pages import compute_player_stats
        pstats = compute_player_stats(standings.get("_match_details", {}))
        planteles = {name: render_squad_fragment(name, sq, pstats) for name, sq in squads.items()}
        outputs.append(("planteles.json", json.dumps(planteles, ensure_ascii=False)))
        outputs.append(("plantel.html", render_plantel_shell()))

        # 9.1 — perfil de selección: ficha + su grupo + sus partidos + acceso al plantel
        team_group, group_data = {}, {}
        for gkey, gval in standings.items():
            if not isinstance(gkey, str) or not gkey.startswith("GROUP_"):
                continue
            ranked = gval.get("teams", [])
            group_data[gkey] = (ranked, gval.get("stats", {}))
            for rt in ranked:
                team_group[rt] = gkey
        team_matches = {}
        for _ms in standings.get("_matches_by_date", {}).values():
            for _m in _ms:
                for _side in (_m.get("home"), _m.get("away")):
                    if _side:
                        team_matches.setdefault(_side, []).append(_m)
        # ¿Contra quién? — posibles rivales de 16avos (motor de cruces, una vez)
        from cruces import build_cruces
        cruces_data = build_cruces(standings)
        cruces_exact = cruces_data.get("_exact", False)
        selecciones = {}
        for t in squads.keys():
            gname = team_group.get(t)
            rows = []
            label = ""
            if gname:
                ranked, gstats = group_data[gname]
                label = "Grupo " + gname.replace("GROUP_", "")
                for i, rt in enumerate(ranked):
                    s = gstats.get(rt)
                    rows.append({"team": rt, "pos": i + 1,
                                 "pj": s.played if s else 0,
                                 "pts": s.points if s else 0,
                                 "dg": s.goal_diff if s else 0,
                                 "me": rt == t})
            mlist = sorted(team_matches.get(t, []), key=lambda x: x.get("utc_date") or "")
            selecciones[t] = render_seleccion_fragment(
                t, label, rows, mlist,
                cruces=cruces_data.get(t), cruces_exact=cruces_exact)
        outputs.append(("selecciones.json", json.dumps(selecciones, ensure_ascii=False)))
        outputs.append(("seleccion.html", render_seleccion_shell()))

        # cruces.json — bloques "¿Contra quién?" por equipo + estructura por grupo para
        # el selector segmentado. Se carga bajo demanda. Clave = nombre en español.
        #   {"_groups": [["Grupo A", ["México", ...]], ...], "México": "<bloque>", ...}
        cruces_blocks = {}
        cruces_groups = []
        for gkey in sorted(group_data.keys()):  # GROUP_A .. GROUP_L
            ranked, _gstats = group_data[gkey]
            label = "Grupo " + gkey.replace("GROUP_", "")
            gteams = []
            for rt in ranked:
                if rt not in squads:
                    continue
                blk = render_cruces_block(cruces_data.get(rt), cruces_exact)
                if blk:
                    es = nombre_es(rt)
                    cruces_blocks[es] = blk
                    gteams.append(es)
            if gteams:
                cruces_groups.append([label, gteams])
        cruces_out = {"_groups": cruces_groups}
        cruces_out.update(cruces_blocks)
        outputs.append(("cruces.json", json.dumps(cruces_out, ensure_ascii=False)))

    # Páginas de partido — TODOS los partidos tienen su página (con detalle si está disponible,
    # header + posiciones siempre; "sin datos aún" cuando todavía no hay alineaciones/stats)
    details = standings.get("_match_details", {})
    all_matches = [m for ms in standings.get("_matches_by_date", {}).values() for m in ms]
    if all_matches:
        # H2H para los partidos aún no jugados (reemplaza el "sin datos" hasta que arranque)
        _upcoming = [m for m in all_matches if m.get("status") in ("TIMED", "", None)]
        enrich_h2h(_upcoming, apifootball, k1="home", k2="away", budget=40)
        thirds_adv = {e["team"] for e in standings.get("_thirds_advancing", [])}
        # Imagen de cada sede (la misma que la sección Estadios: API o foto curada)
        venue_img_map = {v.get("name"): v.get("image_url")
                         for v in standings.get("_venues", []) if v.get("image_url")}
        # Partidos de cada grupo (jugados + próximos) para el bloque "Partidos del grupo"
        group_fixtures = {}
        for m in all_matches:
            g = m.get("group")
            if g and m.get("match_id"):
                group_fixtures.setdefault(g, []).append(m)
        partidos = {}
        for m in all_matches:
            mid = str(m.get("match_id") or "")
            if not mid or mid == "None":
                continue
            grp = (m.get("group") or "").replace("GROUP_", "")
            stage_label = f"Grupo {grp}" if grp else (m.get("stage", "") or "").replace("_", " ").title()
            group_data = standings.get(m.get("group")) if m.get("group") else None
            gfix = group_fixtures.get(m.get("group"))
            vimg = venue_img_map.get(m.get("venue_name"))
            partidos[mid] = render_match_fragment(m, details.get(mid), group_data, stage_label,
                                                  thirds_adv, group_fixtures=gfix, venue_img=vimg)
        outputs.append(("partidos.json", json.dumps(partidos, ensure_ascii=False)))
        outputs.append(("partido.html", render_partido_shell()))

        # Datos estructurados para el armador de posts de Instagram (panel admin)
        from posts_data import build_posts, build_team_statuses
        _posts = build_posts(all_matches, details)
        _posts["teams"] = build_team_statuses(standings)   # estados de clasificación
        outputs.append(("posts.json", json.dumps(_posts, ensure_ascii=False)))

    # SEO/GEO — sitemap.xml con todas las URLs (home + partidos + selecciones + planteles)
    import urllib.parse as _up
    _base = "https://mejortercero.online"
    _urls = [f"{_base}/", f"{_base}/simulador.html"]
    for _m in all_matches:
        _mid = _m.get("match_id")
        if _mid:
            _urls.append(f"{_base}/partido.html?id={_mid}")
    for _t in standings.get("_squads", {}).keys():
        _q = _up.quote(_t)
        _urls.append(f"{_base}/seleccion.html?t={_q}")
        _urls.append(f"{_base}/plantel.html?t={_q}")
    _smap = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             + "".join(f"<url><loc>{u}</loc></url>" for u in _urls)
             + "</urlset>")
    outputs.append(("sitemap.xml", _smap))

    for path, content in outputs:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)

    extra = f" + {len(squads)} planteles" if squads else ""
    print(f"Generado: {html_out} + {json_out}{extra}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default=os.environ.get("FOOTBALL_API_KEY"))
    parser.add_argument("--apifootball-key", default=os.environ.get("APIFOOTBALL_KEY"))
    parser.add_argument("--html", default="mundial2026.html")
    parser.add_argument("--json", default="data.json")
    args = parser.parse_args()

    if not args.apifootball_key:
        sys.exit("Error: falta APIFOOTBALL_KEY (proveedor principal). Pasala con --apifootball-key.")

    main(args.key, args.html, args.json, apifootball_key=args.apifootball_key)
