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

from api_client import WorldCupClient, build_standings
from bracket import build_round_of_32
from data_renderer import render_data_json
from html_renderer import render_html


def main(api_key: str, html_out: str, json_out: str) -> None:
    client = WorldCupClient(api_key)
    print("Fetching datos...")
    standings = build_standings(client)
    matchups = build_round_of_32(standings, standings.get("_thirds_advancing", []))

    html = render_html(standings, matchups)
    data_json = render_data_json(standings, matchups)

    for path, content in [(html_out, html), (json_out, data_json)]:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)

    print(f"Generado: {html_out} + {json_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", default=os.environ.get("FOOTBALL_API_KEY"))
    parser.add_argument("--html", default="mundial2026.html")
    parser.add_argument("--json", default="data.json")
    args = parser.parse_args()

    if not args.key:
        sys.exit("Error: falta la API key. Pasala con --key o la variable FOOTBALL_API_KEY.")

    main(args.key, args.html, args.json)
