# -*- coding: utf-8 -*-
"""Test de consistencia del motor de estadísticas (stats.py → estadisticas.json).
Verifica los invariantes que deben cumplirse siempre, así una regresión futura salta.
Correr después de generar: python test_stats.py"""
import io
import json
import sys

d = json.load(io.open("estadisticas.json", encoding="utf-8"))
T = d["teams"]
g = d["goals"]
t = d["tournament"]
played = [x for x in T.values() if x["played"] > 0]
fails = []


def check(cond, msg):
    print(("  OK  " if cond else "FAIL  ") + msg)
    if not cond:
        fails.append(msg)


# ── Resultados: sin fugas en el conteo de goles ───────────────────────────────
gf = sum(x["gf"] for x in T.values())
ga = sum(x["ga"] for x in T.values())
check(gf == ga == t["goals_total"], f"GF({gf})==GA({ga})==goles_torneo({t['goals_total']})")
check(sum(x["won"] for x in T.values()) == sum(x["lost"] for x in T.values()), "victorias == derrotas")
check(sum(x["drawn"] for x in T.values()) % 2 == 0, "empates (suma) es par")
check(sum(x["played"] for x in T.values()) == 2 * t["matches_played"], "partidos-equipo == 2 x partidos")

# ── Stats / tarjetas gateadas a TERMINADOS (stat_n debe == played) ─────────────
mism = [(x["es"], x["played"], x["stat_n"]) for x in played if x["stat_n"] != x["played"]]
check(not mism, f"stat_n == played para todos (mezcla en vivo: {mism[:3]})")

# ── Goles: heatmap y desglose por tipo suman lo MISMO ─────────────────────────
band_sum = sum(g["bands"].values())
type_sum = g["normal"] + g["penalty"] + g["own"]
check(band_sum == type_sum, f"suma bandas({band_sum}) == tipos({type_sum})")
check(g["first_half"] + g["second_half"] == band_sum, "1T + 2T == suma de bandas")

# ── Confederaciones: las 48 mapeadas ──────────────────────────────────────────
check(all(x["confed"] for x in T.values()), "todas las selecciones tienen confederación")

# ── Remontadas: coherentes (no perdió quien remontó) ──────────────────────────
cb_ok = all((c["gf"] > c["ga"]) == c["win"] and c["deficit"] >= 1 for c in d["comebacks"])
check(cb_ok, "remontadas coherentes (win <-> gf>ga, déficit>=1)")

# ── Árbitros: cpm == tarjetas/partidos ────────────────────────────────────────
ref_ok = all(abs(r["cpm"] - (r["yc"] + r["rc"]) / r["matches"]) < 0.06 and r["matches"] >= 2
             for r in d["referees"])
check(ref_ok, "árbitros: cpm coherente y min 2 partidos")

# ── Ligas / legionarios: rangos válidos ───────────────────────────────────────
check(all(l["players"] >= 8 for l in d["leaguePerf"]), "leaguePerf: solo ligas con >=8 jugadores")
check(all(0 <= x["pct"] <= 100 for x in d["squads"]["legionarios"]), "legionarios: pct en [0,100]")

# ── Jugadores: G+A == goles+asistencias ───────────────────────────────────────
pa = d["players"]["all"]
check(all(p["ga"] == p["goals"] + p["assists"] for p in pa), "jugadores: ga == goles + asistencias")

print(f"\n==> {'TODO OK' if not fails else str(len(fails)) + ' FALLAS'}")
sys.exit(0 if not fails else 1)
