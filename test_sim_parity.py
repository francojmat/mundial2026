# -*- coding: utf-8 -*-
"""Test de paridad: el motor JS (sim-engine.js) tiene que dar IGUAL que el Python
(standings + bracket) tanto en las tablas de grupo como en el R32 completo."""
import io
import json
import subprocess
import sys

from standings import MatchResult, compute_stats, rank_group, rank_third_place_teams
from bracket import build_round_of_32

NODE = "node"


def _matches(grp):
    return [MatchResult(home=m["h"], away=m["a"],
                        home_goals=m["hg"] or 0, away_goals=m["ag"] or 0,
                        played=m["played"], status=m["status"]) for m in grp["matches"]]


def py_rank(groups, order):
    out = {}
    for g, grp in groups.items():
        teams = order.get(g, grp["teams"])
        out[g] = rank_group(teams, compute_stats(teams, _matches(grp)), _matches(grp))
    return out


def py_r32(groups):
    gr, thirds = {}, []
    for g, grp in groups.items():
        ms = _matches(grp)
        stats = compute_stats(grp["teams"], ms)
        ranked = rank_group(grp["teams"], stats, ms)
        gr["GROUP_" + g] = {"teams": ranked, "stats": stats, "matches": ms}
        if len(ranked) >= 3:
            thirds.append({"team": ranked[2], "group": "GROUP_" + g, "stats": stats[ranked[2]]})
    mus = build_round_of_32(gr, rank_third_place_teams(thirds)[:8])
    return {m["partido"]: [m["equipo1"], m["equipo2"]] for m in mus}


def js_run(override):
    p = subprocess.run([NODE, "_sim_driver.js"], input=json.dumps(override),
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        print("node error:", p.stderr); sys.exit(1)
    return json.loads(p.stdout)


data = json.load(io.open("sim.json", encoding="utf-8"))
groups = data["groups"]
ok = True

# 1) tablas de grupo (orden normal + invertido)
for label, order in [("grupos normal", {}),
                     ("grupos invertido", {g: list(reversed(v["teams"])) for g, v in groups.items()})]:
    py = py_rank(groups, order)
    js = js_run(order)["ranks"]
    good = all(py[g] == js.get(g) for g in groups)
    ok = ok and good
    print(f"[{label}] {'OK' if good else 'DIVERGE'}")
    if not good:
        for g in groups:
            if py[g] != js.get(g):
                print(f"    {g}: py={py[g]} js={js.get(g)}")

# 2) R32 completo
pr = py_r32(groups)
jr = {m[0]: [m[1], m[2]] for m in js_run({})["r32"]}
good = all(pr[p] == jr.get(p) for p in pr)
ok = ok and good
print(f"[R32 completo] {'OK' if good else 'DIVERGE'} ({len(pr)} cruces)")
if not good:
    for p in sorted(pr):
        if pr[p] != jr.get(p):
            print(f"    P{p}: py={pr[p]} js={jr.get(p)}")

print("\n==> PARIDAD TOTAL OK" if ok else "\n==> HAY DIVERGENCIAS")
sys.exit(0 if ok else 1)
