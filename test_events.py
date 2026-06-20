"""Test local de events.py con un cliente simulado (sin red)."""
import os, json
from datetime import datetime, timezone, timedelta
import events

# Cliente fake que devuelve fixtures y eventos simulados
class FakeClient:
    def __init__(self):
        self.fixture_calls = 0
        self.event_calls = 0
    def get_fixtures_by_date(self, date_iso):
        self.fixture_calls += 1
        # Devuelve un fixture cuyo kickoff coincide con el partido de prueba
        return [{
            "fixture": {"id": 999, "date": "2026-06-20T16:00:00+00:00"},
            "teams": {"home": {"id": 26, "name": "Argentina"},
                      "away": {"id": 28, "name": "Algeria"}},
        }]
    def get_fixture_events(self, fixture_id):
        self.event_calls += 1
        return [
            {"time": {"elapsed": 23}, "team": {"id": 26}, "player": {"name": "Messi"},
             "assist": {"name": "Di Maria"}, "type": "Goal", "detail": "Normal Goal"},
            {"time": {"elapsed": 45, "extra": 2}, "team": {"id": 28}, "player": {"name": "Mahrez"},
             "assist": {"name": None}, "type": "Goal", "detail": "Penalty"},
            {"time": {"elapsed": 60}, "team": {"id": 26}, "player": {"name": "De Paul"},
             "assist": {"name": None}, "type": "Card", "detail": "Yellow Card"},
            {"time": {"elapsed": 78}, "team": {"id": 28}, "player": {"name": "Bennacer"},
             "assist": {"name": None}, "type": "Card", "detail": "Red Card"},
            {"time": {"elapsed": 70}, "team": {"id": 26}, "player": {"name": "Lautaro"},
             "assist": {"name": "Alvarez"}, "type": "subst", "detail": "Substitution 1"},
            {"time": {"elapsed": 80}, "team": {"id": 26}, "player": {"name": "X"},
             "assist": {"name": "Y"}, "type": "Goal", "detail": "Missed Penalty"},  # debe ignorarse
        ]

CACHE = "test_cache.json"
if os.path.exists(CACHE): os.remove(CACHE)

now = datetime.now(timezone.utc)
# Partido en vivo hoy (kickoff hace 1h)
matches_by_date = {
    "2026-06-20": [{
        "match_id": 537397, "home": "Argentina", "away": "Algeria",
        "status": "IN_PLAY",
        "utc_date": "2026-06-20T16:00:00Z",
    }]
}

fc = FakeClient()
print("--- 1ra llamada (en vivo, debe pedir) ---")
events.enrich_with_events(matches_by_date, fc, CACHE)
m = matches_by_date["2026-06-20"][0]
print("goles:", json.dumps(m["goals_detail"], ensure_ascii=False))
print("tarjetas:", json.dumps(m["bookings"], ensure_ascii=False))
print("cambios:", json.dumps(m["substitutions"], ensure_ascii=False))
print(f"requests: fixtures={fc.fixture_calls} events={fc.event_calls}")
assert len(m["goals_detail"]) == 2, "deben ser 2 goles (penal errado ignorado)"
assert m["goals_detail"][0]["team"] == "Argentina"
assert m["goals_detail"][1]["type"] == "PENALTY"
assert m["goals_detail"][1]["minute"] == "45+2"
assert len(m["bookings"]) == 2
assert m["bookings"][1]["card"] == "RED"
assert m["substitutions"][0]["player_in"] == "Lautaro"
assert m["substitutions"][0]["player_out"] == "Alvarez"

print("\n--- 2da llamada inmediata (debe usar cache, NO pedir) ---")
events.enrich_with_events(matches_by_date, fc, CACHE)
print(f"requests: fixtures={fc.fixture_calls} events={fc.event_calls}")
assert fc.event_calls == 1, "no debe volver a pedir dentro del intervalo"

print("\n--- 3ra: partido pasa a FINISHED, cache no era FINISHED -> 1 pedido final ---")
matches_by_date["2026-06-20"][0]["status"] = "FINISHED"
events.enrich_with_events(matches_by_date, fc, CACHE)
print(f"requests: fixtures={fc.fixture_calls} events={fc.event_calls}")
assert fc.event_calls == 2, "debe pedir una vez al terminar"

print("\n--- 4ta: ya FINISHED y cacheado -> 0 pedidos ---")
events.enrich_with_events(matches_by_date, fc, CACHE)
print(f"requests: fixtures={fc.fixture_calls} events={fc.event_calls}")
assert fc.event_calls == 2, "no debe pedir mas"

# fixture_map debe haberse cacheado (1 sola resolucion de fecha)
assert fc.fixture_calls == 1, f"debe resolver la fecha 1 sola vez, fue {fc.fixture_calls}"

print("\n--- 5ta: sin partidos en vivo ni nuevos -> 0 pedidos ---")
fc2 = FakeClient()
events.enrich_with_events(matches_by_date, fc2, CACHE)
assert fc2.event_calls == 0 and fc2.fixture_calls == 0

print("\nTODOS LOS ASSERTS PASARON OK")
os.remove(CACHE)
