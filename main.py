"""
Mundial 2026 — Standings & Bracket en vivo.
Genera HTML + data.json y los sirve por HTTP.

Uso local:
  python main.py --key TU_API_KEY
  Abre http://localhost:8080/mundial2026.html

En producción (Fly.io):
  La key viene de la variable de entorno FOOTBALL_API_KEY.
"""

import argparse
import functools
import os
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

from api_client import WorldCupClient, build_standings
from bracket import build_round_of_32
from data_renderer import render_data_json
from html_renderer import render_html


class _Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split("?")[0]
        if path.endswith(".json"):
            self.send_header("Cache-Control", "public, max-age=30")
        elif path.endswith(".html"):
            self.send_header("Cache-Control", "public, max-age=3600")
        elif path.endswith((".png", ".avif")):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # silenciar logs HTTP en la consola


def _start_server(directory: str, port: int = 8080):
    handler = functools.partial(_Handler, directory=directory)
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Servidor HTTP en http://0.0.0.0:{port}")


def run(api_key: str, output: str, interval: int, port: int, fifa_rankings: dict):
    client = WorldCupClient(api_key)
    directory = os.path.dirname(os.path.abspath(output))
    json_out  = os.path.join(directory, "data.json")

    _start_server(directory, port)
    print(f"Actualizando cada {interval}s → {output}")

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching datos...")
            standings = build_standings(client, fifa_rankings)
            matchups  = build_round_of_32(standings, standings.get("_thirds_advancing", []))
            html      = render_html(standings, matchups)
            data_json = render_data_json(standings, matchups)

            for path, content in [(output, html), (json_out, data_json)]:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp, path)

            print("  → OK. HTML y data.json actualizados.")
        except Exception as e:
            print(f"  → ERROR: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",      default=os.environ.get("FOOTBALL_API_KEY"), help="API key de football-data.org")
    parser.add_argument("--output",   default="mundial2026.html")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--port",     type=int, default=8080)
    args = parser.parse_args()

    if not args.key:
        raise SystemExit("Error: falta la API key. Pasala con --key o la variable FOOTBALL_API_KEY.")

    run(args.key, args.output, args.interval, args.port, fifa_rankings={})
