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
from pages import render_plantel_shell, render_squad_fragment
from match_page import render_partido_shell, render_match_fragment


def main(api_key: str, html_out: str, json_out: str, apifootball_key: str = None) -> None:
    apifootball = APIFootballClient(apifootball_key)  # proveedor principal de datos
    scorers_client = WorldCupClient(api_key) if api_key else None  # solo goleadores
    print(f"Proveedor: API-Football. Goleadores: {'football-data' if scorers_client else 'sin lista'}.")
    print("Fetching datos...")
    standings = build_standings(scorers_client, apifootball)
    matchups = build_round_of_32(standings, standings.get("_thirds_advancing", []))

    html = render_html(standings, matchups)
    data_json = render_data_json(standings, matchups)

    outputs = [(html_out, html), (json_out, data_json)]

    # Páginas de plantel (solo si API-Football está activo y hay planteles cacheados)
    squads = standings.get("_squads", {})
    if squads:
        planteles = {name: render_squad_fragment(name, sq) for name, sq in squads.items()}
        outputs.append(("planteles.json", json.dumps(planteles, ensure_ascii=False)))
        outputs.append(("plantel.html", render_plantel_shell()))

    # Páginas de partido — TODOS los partidos tienen su página (con detalle si está disponible,
    # header + posiciones siempre; "sin datos aún" cuando todavía no hay alineaciones/stats)
    details = standings.get("_match_details", {})
    all_matches = [m for ms in standings.get("_matches_by_date", {}).values() for m in ms]
    if all_matches:
        thirds_adv = {e["team"] for e in standings.get("_thirds_advancing", [])}
        partidos = {}
        for m in all_matches:
            mid = str(m.get("match_id") or "")
            if not mid or mid == "None":
                continue
            grp = (m.get("group") or "").replace("GROUP_", "")
            stage_label = f"Grupo {grp}" if grp else (m.get("stage", "") or "").replace("_", " ").title()
            group_data = standings.get(m.get("group")) if m.get("group") else None
            partidos[mid] = render_match_fragment(m, details.get(mid), group_data, stage_label, thirds_adv)
        outputs.append(("partidos.json", json.dumps(partidos, ensure_ascii=False)))
        outputs.append(("partido.html", render_partido_shell()))

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
