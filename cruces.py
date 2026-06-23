"""
Explorador de cruces — posibles rivales de 16avos (R32) para cada equipo según
la posición en la que puede terminar su grupo.

Reusa el motor que ya existe: enumera los resultados posibles de cada grupo,
invierte a "qué equipos pueden terminar en cada posición" y, para los slots que
enfrentan a un 3.º, resuelve el Anexo C EXACTO enumerando las combinaciones de
terceros que pueden clasificar. El cálculo pesado corre una vez por generación.
"""

from itertools import product
from typing import Dict, List, Optional

from standings import MatchResult, compute_stats, rank_group, rank_third_place_teams
from bracket import _BRACKET, _SCHEDULE, _city_of_partido, assign_thirds_to_slots

# Tope de combinaciones para el Anexo C exacto. Si se supera (torneo temprano, muchos
# grupos abiertos), se cae al superset (terceros de los grupos candidatos). El feature
# es útil tarde, cuando hay equipos con lugar fijo y la mayoría de grupos ya cerraron.
_MAX_COMBOS = 60000
_SCORE = {"H": (1, 0), "D": (0, 0), "A": (0, 1)}


def _pending(matches: List[MatchResult]) -> List[MatchResult]:
    return [m for m in matches if not m.played and m.status == "TIMED"]


def _enumerate_group(teams, matches, fifa_rankings=None):
    """Lista de (ranking, stats) para cada resultado posible del grupo."""
    pending = _pending(matches)
    played = [m for m in matches if m.played]
    if not pending:
        stats = compute_stats(teams, played)
        return [(rank_group(teams, stats, played, fifa_rankings), stats)]
    out = []
    for combo in product("HDA", repeat=len(pending)):
        sim = list(played)
        for m, res in zip(pending, combo):
            hg, ag = _SCORE[res]
            sim.append(MatchResult(home=m.home, away=m.away, home_goals=hg,
                                   away_goals=ag, played=True, status="FINISHED"))
        stats = compute_stats(teams, sim)
        out.append((rank_group(teams, stats, sim, fifa_rankings), stats))
    return out


def _group_outcomes(standings, fifa_rankings=None) -> Dict[str, list]:
    return {g: _enumerate_group(d.get("teams", []), d.get("matches", []), fifa_rankings)
            for g, d in standings.items()
            if isinstance(g, str) and g.startswith("GROUP_")}


def possible_finishers(group_outcomes) -> Dict[str, Dict[int, set]]:
    """{ 'GROUP_X': {1: {equipos}, 2: ..., 3: ..., 4: ...} }"""
    res = {}
    for g, outs in group_outcomes.items():
        pos = {1: set(), 2: set(), 3: set(), 4: set()}
        for ranked, _ in outs:
            for i, t in enumerate(ranked, 1):
                if i <= 4:
                    pos[i].add(t)
        res[g] = pos
    return res


def _thirds_options(group_outcomes):
    """Por grupo, las opciones DISTINTAS de 3.º: [{team, group, stats}] (dedup por
    equipo + puntos/dif/gf, que es lo que define el ranking de terceros)."""
    res = {}
    for g, outs in group_outcomes.items():
        seen = {}
        for ranked, stats in outs:
            if len(ranked) < 3:
                continue
            t = ranked[2]
            s = stats[t]
            seen[(t, s.points, s.goal_diff, s.goals_for)] = {"team": t, "group": g, "stats": s}
        res[g] = list(seen.values())
    return res


def possible_slot_thirds(group_outcomes, fifa_rankings=None) -> Optional[Dict[int, set]]:
    """{ partido_de_slot_3ro: {equipos posibles} } resolviendo Anexo C exacto.
    Devuelve None si la enumeración supera el tope (→ el caller usa el superset)."""
    opts = _thirds_options(group_outcomes)
    groups = sorted(opts.keys())
    total = 1
    for g in groups:
        total *= max(len(opts[g]), 1)
    slot_partidos = [num for num, _s1, s2 in _BRACKET if s2[0] == "3"]
    if total > _MAX_COMBOS:
        return None
    result = {p: set() for p in slot_partidos}
    for combo in product(*[opts[g] for g in groups]):
        thirds = [dict(x) for x in combo]  # 12 terceros [{team, group, stats}]
        ranked8 = rank_third_place_teams(thirds, fifa_rankings)[:8]
        for partido, (team, _grp) in assign_thirds_to_slots(ranked8).items():
            if partido in result:
                result[partido].add(team)
    return result


def _opp_label(spec) -> str:
    kind, groups = spec
    if kind == "1":
        return f"1.º del {groups}"
    if kind == "2":
        return f"2.º del {groups}"
    return "un 3.º"


def team_cruces(team, group, finishers, slot_thirds) -> dict:
    """Para un equipo: sus ramas por posición clasificable (1.º / 2.º), con el
    partido de 16avos (sede, fecha) y la lista de rivales posibles."""
    glet = group.replace("GROUP_", "")
    fin = finishers.get(group, {})
    positions = {p for p in (1, 2, 3, 4) if team in fin.get(p, set())}
    branches = []
    for pos in (1, 2):
        if team not in fin.get(pos, set()):
            continue
        for num, s1, s2 in _BRACKET:
            target = (str(pos), glet)
            opp = s2 if s1 == target else s1 if s2 == target else None
            if opp is None:
                continue
            utc, _venue = _SCHEDULE.get(num, ("", ""))
            if opp[0] in ("1", "2"):
                og = "GROUP_" + opp[1]
                opps = sorted(finishers.get(og, {}).get(int(opp[0]), set()))
            elif slot_thirds is not None:
                opps = sorted(slot_thirds.get(num, set()))
            else:  # superset: terceros de los grupos candidatos
                cands = opp[1].split("/")
                opps = sorted({t for c in cands
                               for t in finishers.get("GROUP_" + c, {}).get(3, set())})
            branches.append({
                "pos": pos, "partido": num, "city": _city_of_partido(num),
                "utc": utc, "opp_type": _opp_label(opp), "opponents": opps,
            })
            break
    qualifying = positions & {1, 2}
    return {
        "team": team, "group": glet,
        "classified": positions <= {1, 2},          # top-2 en todos los escenarios
        "locked_pos": (list(qualifying)[0] if len(qualifying) == 1 and positions <= {1, 2} else None),
        "branches": branches,
    }


# Variantes de margen por resultado, para detectar desempates por diferencia/goles.
_MARGINS = {"H": [(1, 0), (3, 0), (2, 1)], "D": [(0, 0), (1, 1)], "A": [(0, 1), (0, 3), (1, 2)]}


def opponent_matrix(team, group, finishers, standings, fifa_rankings=None):
    """Grilla tipo Excel: para un equipo cuyo rival sale de UN solo grupo (posición
    concreta), enumera las combinaciones de los partidos pendientes de ESE grupo y
    devuelve el rival por combinación, marcando los desempates por goles.

    Devuelve None si el rival es un 3.º (no sale de un solo grupo) o el equipo no
    tiene un puesto clasificable definido para armar la grilla."""
    glet = group.replace("GROUP_", "")
    fin = finishers.get(group, {})
    positions = {p for p in (1, 2, 3, 4) if team in fin.get(p, set())}
    qualifying = positions & {1, 2}
    if positions > {1, 2} or len(qualifying) != 1:
        return None  # el equipo todavía no tiene UN puesto clasificable fijo
    my_pos = list(qualifying)[0]

    # encontrar el cruce y el lado rival
    opp = None
    for num, s1, s2 in _BRACKET:
        target = (str(my_pos), glet)
        if s1 == target:
            opp = s2; partido = num; break
        if s2 == target:
            opp = s1; partido = num; break
    if opp is None or opp[0] not in ("1", "2"):
        return None  # rival es un 3.º → no es una grilla de un solo grupo

    opp_pos = int(opp[0])
    g2 = "GROUP_" + opp[1]
    data2 = standings.get(g2, {})
    teams2 = data2.get("teams", [])
    matches2 = data2.get("matches", [])
    pending = [m for m in matches2 if not m.played and m.status == "TIMED"]
    played = [m for m in matches2 if m.played]

    def _pos_team(sim):
        stats = compute_stats(teams2, sim)
        ranked = rank_group(teams2, stats, sim, fifa_rankings)
        return (ranked[opp_pos - 1], stats) if len(ranked) >= opp_pos else (None, stats)

    rows = []
    combos = list(product("HDA", repeat=len(pending))) if pending else [()]
    for combo in combos:
        cand, gd_set, gf_set = set(), {}, {}
        margin_variants = list(product(*[_MARGINS[r] for r in combo])) if combo else [()]
        for margins in margin_variants:
            sim = list(played)
            for m, (hg, ag) in zip(pending, margins):
                sim.append(MatchResult(home=m.home, away=m.away, home_goals=hg,
                                       away_goals=ag, played=True, status="FINISHED"))
            t_at, stats = _pos_team(sim)
            if t_at:
                cand.add(t_at)
                gd_set.setdefault(t_at, set()).add(stats[t_at].goal_diff)
        # etiqueta de desempate: si dos candidatos pueden empatar en DG → goles a favor
        note = ""
        if len(cand) > 1:
            gds = [next(iter(v)) if len(v) == 1 else None for v in gd_set.values()]
            note = "goles a favor" if (None in gds or len(set(gds)) < len(gds)) else "diferencia de gol"
        rows.append({"combo": list(combo), "opponents": sorted(cand), "note": note})

    return {
        "partido": partido, "city": _city_of_partido(partido), "my_pos": my_pos,
        "opp_pos": opp_pos, "opp_group": opp[1],
        "matches": [{"home": m.home, "away": m.away} for m in pending],
        "rows": rows,
    }


def build_cruces(standings, fifa_rankings=None) -> Dict[str, dict]:
    """{ equipo_api: team_cruces(...) } para todos los equipos. Calcula el motor
    una sola vez. `exact` indica si el Anexo C se resolvió exacto o por superset."""
    group_outcomes = _group_outcomes(standings, fifa_rankings)
    finishers = possible_finishers(group_outcomes)
    slot_thirds = possible_slot_thirds(group_outcomes, fifa_rankings)
    out = {"_exact": slot_thirds is not None}
    for g, data in standings.items():
        if not (isinstance(g, str) and g.startswith("GROUP_")):
            continue
        for team in data.get("teams", []):
            entry = team_cruces(team, g, finishers, slot_thirds)
            entry["matrix"] = opponent_matrix(team, g, finishers, standings, fifa_rankings)
            out[team] = entry
    return out
