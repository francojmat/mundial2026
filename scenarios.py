"""
Escenarios de clasificación calculados sobre las tablas de grupo.

Enumera todos los resultados posibles de los partidos pendientes de un grupo
(3^n: gana local / empate / gana visitante) y, para cada equipo, determina qué
tiene asegurado y qué necesita. Respeta los desempates oficiales reusando
rank_group de standings.py.

Conservador a propósito: si algo depende de desempates finos (goles), preferimos
"puede clasificar" antes que afirmar de más. El idioma de salida es español.
"""

from itertools import product
from typing import Dict, List

from standings import MatchResult, compute_stats, rank_group

# Tope de partidos pendientes para enumerar (3^7 = 2187; por encima no aporta:
# son grupos casi sin jugar, donde no hay escenario útil que mostrar).
_MAX_PENDING = 7
# Goles representativos por resultado (margen mínimo). El clinch de los 2 primeros
# por puntos no depende del margen; los bordes de desempate quedan como "puede".
_SCORE = {"H": (1, 0), "D": (0, 0), "A": (0, 1)}


def _pending(matches: List[MatchResult]) -> List[MatchResult]:
    return [m for m in matches if not m.played and m.status == "TIMED"]


def _next_match_for(team: str, pending: List[MatchResult]):
    for m in pending:
        if m.home == team or m.away == team:
            return m
    return None


def compute_group_scenarios(teams: List[str], matches: List[MatchResult],
                            fifa_rankings: Dict[str, int] = None) -> Dict:
    """
    Devuelve por equipo:
      status: 'classified' (top-2 en todos los escenarios) | 'eliminated'
              (4º en todos) | 'alive'
      positions: set de posiciones finales posibles (1..4)
      if_win/if_draw/if_lose (solo 'alive' con próximo partido):
              'in' (top-2 asegurado) | 'third' (3º, depende de otros grupos)
              | 'alive' | 'out' según el mejor desenlace posible tras ese resultado.
    Devuelve {} si no hay nada que calcular (sin pendientes o demasiados).
    """
    pending = _pending(matches)
    if not pending or len(pending) > _MAX_PENDING:
        return {}

    played = [m for m in matches if m.played]

    # posiciones posibles por equipo (global), y condicionadas al resultado del
    # próximo partido de cada equipo.
    positions = {t: set() for t in teams}
    cond = {t: {"H": set(), "D": set(), "A": set()} for t in teams}
    nexts = {t: _next_match_for(t, pending) for t in teams}

    for combo in product("HDA", repeat=len(pending)):
        sim = list(played)
        outcome_of = {}
        for m, res in zip(pending, combo):
            hg, ag = _SCORE[res]
            sim.append(MatchResult(home=m.home, away=m.away, home_goals=hg,
                                   away_goals=ag, played=True, status="FINISHED"))
            outcome_of[id(m)] = res
        stats = compute_stats(teams, sim)
        ranked = rank_group(teams, stats, sim, fifa_rankings)
        pos = {t: ranked.index(t) + 1 for t in teams}
        for t in teams:
            positions[t].add(pos[t])
            nm = nexts[t]
            if nm is not None:
                res = outcome_of[id(nm)]
                # el resultado es desde el punto de vista del equipo t
                if nm.home == t:
                    side = res
                else:  # t es visitante: invertir H<->A
                    side = {"H": "A", "D": "D", "A": "H"}[res]
                cond[t][side].add(pos[t])

    out = {}
    for t in teams:
        ps = positions[t]
        if ps <= {1, 2}:
            status = "classified"          # top-2 en todos los escenarios
        elif ps == {4}:
            status = "eliminated"          # 4º siempre (ni siquiera mejor tercero)
        else:
            status = "alive"
        entry = {"status": status, "positions": sorted(ps)}
        nm = nexts[t]
        if status == "classified":
            # ¿asegura/pelea el 1.º puesto? (para mostrar algo aunque ya esté clasificado)
            if ps == {1}:
                entry["first"] = "clinched1"
            elif ps == {2}:
                entry["first"] = "clinched2"
            elif nm is not None:
                entry["first"] = "fight1"
                for side, key in (("H", "f_win"), ("D", "f_draw"), ("A", "f_lose")):
                    pset = cond[t][side]
                    if pset:
                        entry[key] = bool(pset <= {1})   # True si ese resultado lo deja 1.º
            else:
                entry["first"] = "fight1"
        if status == "alive" and nm is not None:
            for side, key in (("H", "if_win"), ("D", "if_draw"), ("A", "if_lose")):
                pset = cond[t][side]
                if not pset:
                    continue
                if pset <= {1, 2}:
                    entry[key] = "in"          # asegura top-2
                elif pset <= {4}:
                    entry[key] = "out"         # queda 4º seguro
                elif 3 in pset and pset <= {3, 4}:
                    entry[key] = "third"       # como mucho 3º (depende de terceros)
                else:
                    entry[key] = "alive"       # sigue dependiendo
        # próximo rival (para frases concretas), sin importar el status
        if nm is not None:
            entry["next"] = {"home": nm.home, "away": nm.away, "is_home": nm.home == t}
        out[t] = entry
    return out


# ── Frases en español ────────────────────────────────────────────────────────

def _opp_name(entry: Dict) -> str:
    """Nombre (API, sin traducir) del próximo rival, o '' si no hay próximo partido."""
    nx = entry.get("next")
    if not nx:
        return ""
    return nx["away"] if nx.get("is_home") else nx["home"]


def team_phrase(entry: Dict, opponent: str = None) -> str:
    """Frase corta de qué se juega el equipo. `opponent` = nombre del próximo rival
    ya traducido (lo pasa el caller); si es None se usa 'su rival'."""
    st = entry.get("status")
    opp = opponent or "su rival"
    has_next = bool(entry.get("next"))
    if st == "classified":
        f = entry.get("first")
        if f == "clinched1":
            return "Clasificado, termina 1.º"
        if f == "clinched2":
            return "Clasificado, termina 2.º"
        if f == "fight1":
            fw, fd = entry.get("f_win"), entry.get("f_draw")
            if not has_next:
                return "Clasificado, pelea el 1.º"
            if fd and fw:
                return f"Clasificado · no pierde con {opp} y es 1.º"
            if fd:
                return f"Clasificado · empata con {opp} y es 1.º"
            if fw:
                return f"Clasificado · le gana a {opp} y es 1.º"
            return "Clasificado, pelea el 1.º"
        return "Clasificado a octavos"
    if st == "eliminated":
        return "Sin chances de avanzar"
    win, draw, lose = entry.get("if_win"), entry.get("if_draw"), entry.get("if_lose")
    if not has_next:
        return "Depende de la última fecha"
    # Del mejor desenlace al peor. Distingue lo que ASEGURA de lo que solo deja con chances.
    if draw == "in":
        return f"Le alcanza con empatar a {opp}"
    if win == "in":
        # "gana o queda afuera" SOLO si no ganar lo ELIMINA (4.º). Si empatar/perder lo deja
        # 3.º, sigue con chances como mejor tercero → NO es "afuera".
        if draw == "out" and lose == "out":
            return f"Le gana a {opp} o queda afuera"
        if draw == "third" or lose == "third":
            return f"Ganándole a {opp} clasifica directo; si no, pelea como mejor 3.º"
        return f"Ganándole a {opp} clasifica"
    if win == "third":
        return f"Si le gana a {opp}, pelea como mejor 3.º"
    if win == "alive":
        return f"Le gana a {opp} y sigue dependiendo"
    # ni ganando asegura algo bueno
    return f"Necesita ganarle a {opp} y esperar"
