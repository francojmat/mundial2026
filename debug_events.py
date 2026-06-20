"""
Diagnóstico: qué devuelve football-data.org para un partido terminado.
Uso: python debug_events.py --key TU_API_KEY
"""
import argparse
import json
import requests

API_BASE = "https://api.football-data.org/v4"

def main(key):
    session = requests.Session()
    session.headers.update({"X-Auth-Token": key})

    print("=== 1) Buscando partidos terminados (bulk endpoint) ===")
    r = session.get(f"{API_BASE}/competitions/WC/matches", params={"status": "FINISHED"}, timeout=10)
    r.raise_for_status()
    matches = r.json().get("matches", [])
    print(f"Total partidos terminados: {len(matches)}")

    if not matches:
        print("No hay partidos terminados aún.")
        return

    m = matches[-1]  # último partido terminado
    match_id = m.get("id")
    print(f"\nÚltimo partido terminado: {m.get('homeTeam',{}).get('name')} vs {m.get('awayTeam',{}).get('name')}")
    print(f"Match ID: {match_id}")
    print(f"\nCampos en bulk endpoint:")
    print(f"  goals ({len(m.get('goals') or [])} items): {json.dumps(m.get('goals'), ensure_ascii=False)[:300]}")
    print(f"  bookings ({len(m.get('bookings') or [])} items): {json.dumps(m.get('bookings'), ensure_ascii=False)[:300]}")
    print(f"  substitutions ({len(m.get('substitutions') or [])} items): {json.dumps(m.get('substitutions'), ensure_ascii=False)[:300]}")
    print(f"  referees: {json.dumps(m.get('referees'), ensure_ascii=False)[:200]}")

    print(f"\n=== 2) Endpoint individual /matches/{match_id} ===")
    r2 = session.get(f"{API_BASE}/matches/{match_id}", timeout=10)
    print(f"HTTP status: {r2.status_code}")
    if not r2.ok:
        print(f"Error: {r2.text[:400]}")
        return

    d = r2.json()
    print(f"\nCampos en endpoint individual:")
    print(f"  goals ({len(d.get('goals') or [])} items): {json.dumps(d.get('goals'), ensure_ascii=False)[:500]}")
    print(f"  bookings ({len(d.get('bookings') or [])} items): {json.dumps(d.get('bookings'), ensure_ascii=False)[:500]}")
    print(f"  substitutions ({len(d.get('substitutions') or [])} items): {json.dumps(d.get('substitutions'), ensure_ascii=False)[:500]}")

    print("\n=== RAW individual (primeros 2000 chars) ===")
    print(json.dumps(d, ensure_ascii=False, indent=2)[:2000])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--key", required=True)
    args = p.parse_args()
    main(args.key)
