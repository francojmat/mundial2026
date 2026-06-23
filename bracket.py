"""
FIFA World Cup 2026 — Round of 32 bracket builder.

Cruces oficiales R32:
  P74:  1E  vs  3(A/B/C/D/F)    P77:  1I  vs  3(C/D/F/G/H)
  P73:  2A  vs  2B              P75:  1F  vs  2C
  P83:  2K  vs  2L              P84:  1H  vs  2J
  P81:  1D  vs  3(B/E/F/I/J)   P82:  1G  vs  3(A/E/H/I/J)
  P76:  1C  vs  2F              P78:  2E  vs  2I
  P79:  1A  vs  3(C/E/F/H/I)   P80:  1L  vs  3(E/H/I/J/K)
  P86:  1J  vs  2H              P88:  2D  vs  2G
  P85:  1B  vs  3(E/F/G/I/J)   P87:  1K  vs  3(D/E/I/J/L)

Terceros: asignados por Anexo C del Reglamento FIFA 2026 (495 combinaciones posibles).
"""

from typing import Dict, List, Optional


def _group_key(letter: str) -> str:
    return f"GROUP_{letter}"


def _get_pos(group_results: Dict, letter: str, pos: int):
    """Devuelve (equipo, es_provisional). pos: 0=1ro, 1=2do."""
    data = group_results.get(_group_key(letter), {})
    teams = data.get("teams", [])
    matches = data.get("matches", [])
    played = sum(1 for m in matches if m.played)
    provisional = played < 6  # 4 equipos → 6 partidos totales
    fallback = f"{'1°' if pos == 0 else '2°'} Grp {letter}"
    if pos < len(teams):
        return teams[pos], provisional
    return fallback, True


def _is_group_complete(group_results: Dict, letter: str) -> bool:
    """True si el grupo terminó todos sus partidos (6/6 jugados)."""
    data = group_results.get(_group_key(letter), {})
    matches = data.get("matches", [])
    return sum(1 for m in matches if m.played) >= 6


# Calendario oficial FIFA 2026 (R32, partidos 73-88) — sede + horario.
# Verificado contra Wikipedia "2026 FIFA World Cup knockout stage" (jun 2026).
# Horarios convertidos a UTC desde la hora local de cada sede.
_SCHEDULE = {
    73: ("2026-06-28T19:00:00Z", "SoFi Stadium, Los Ángeles"),
    74: ("2026-06-29T20:30:00Z", "Gillette Stadium, Boston"),
    76: ("2026-06-29T17:00:00Z", "NRG Stadium, Houston"),
    75: ("2026-06-30T01:00:00Z", "Estadio BBVA, Monterrey"),
    78: ("2026-06-30T17:00:00Z", "AT&T Stadium, Dallas"),
    77: ("2026-06-30T21:00:00Z", "MetLife Stadium, New Jersey"),
    79: ("2026-07-01T01:00:00Z", "Estadio Azteca, CDMX"),
    80: ("2026-07-01T16:00:00Z", "Mercedes-Benz Stadium, Atlanta"),
    82: ("2026-07-01T20:00:00Z", "Lumen Field, Seattle"),
    81: ("2026-07-02T00:00:00Z", "Levi's Stadium, San Francisco"),
    84: ("2026-07-02T19:00:00Z", "SoFi Stadium, Los Ángeles"),
    83: ("2026-07-02T23:00:00Z", "BMO Field, Toronto"),
    85: ("2026-07-03T03:00:00Z", "BC Place, Vancouver"),
    88: ("2026-07-03T18:00:00Z", "AT&T Stadium, Dallas"),
    86: ("2026-07-03T22:00:00Z", "Hard Rock Stadium, Miami"),
    87: ("2026-07-04T01:30:00Z", "Arrowhead Stadium, Kansas City"),
}

# Estructura oficial del bracket FIFA 2026
# ('1','X') = 1ro del Grupo X
# ('2','X') = 2do del Grupo X
# ('3','X/Y/Z') = 3ro de alguno de esos grupos (tabla Anexo C post fase de grupos)
_BRACKET = [
    # ── Mitad izquierda (→ SF P101) ───────────────────────────────────────────
    (74, ('1', 'E'), ('3', 'A/B/C/D/F')),  # } → P89 → P97
    (77, ('1', 'I'), ('3', 'C/D/F/G/H')),  # }
    (73, ('2', 'A'), ('2', 'B')),           # } → P90 → P97
    (75, ('1', 'F'), ('2', 'C')),           # }
    (83, ('2', 'K'), ('2', 'L')),           # } → P93 → P98
    (84, ('1', 'H'), ('2', 'J')),           # }
    (81, ('1', 'D'), ('3', 'B/E/F/I/J')), # } → P94 → P98
    (82, ('1', 'G'), ('3', 'A/E/H/I/J')), # }
    # ── Mitad derecha (→ SF P102) ─────────────────────────────────────────────
    (76, ('1', 'C'), ('2', 'F')),           # } → P91 → P99
    (78, ('2', 'E'), ('2', 'I')),           # }
    (79, ('1', 'A'), ('3', 'C/E/F/H/I')), # } → P92 → P99
    (80, ('1', 'L'), ('3', 'E/H/I/J/K')), # }
    (86, ('1', 'J'), ('2', 'H')),           # } → P95 → P100
    (88, ('2', 'D'), ('2', 'G')),           # }
    (85, ('1', 'B'), ('3', 'E/F/G/I/J')), # } → P96 → P100
    (87, ('1', 'K'), ('3', 'D/E/I/J/L')), # }
]

# ── Anexo C: tabla oficial FIFA 2026 (495 combinaciones) ──────────────────────
#
# Columnas: 1A  1B  1D  1E  1G  1I  1K  1L
# Cada valor "X" indica que el 3ro del Grupo X va a ese slot.
# Slot 1A → P79 (1°A vs 3ro),  1B → P85,  1D → P81,  1E → P74
# Slot 1G → P82,              1I → P77,   1K → P87,  1L → P80
#
# La clave de búsqueda es el frozenset de las 8 letras de grupos cuyos terceros
# clasificaron (= las 8 letras que aparecen en la fila).
_ANNEX_C_RAW = """\
E J I F H G L K
H G I D J F L K
E J I D H G L K
E J I D H F L K
E G I D J F L K
E G J D H F L K
E G I D H F L K
E G J D H F L I
E G J D H F I K
H G I C J F L K
E J I C H G L K
E J I C H F L K
E G I C J F L K
E G J C H F L K
E G I C H F L K
E G J C H F L I
E G J C H F I K
H G I C J D L K
C J I D H F L K
C G I D J F L K
C G J D H F L K
C G I D H F L K
C G J D H F L I
C G J D H F I K
E J I C H D L K
E G I C J D L K
E G J C H D L K
E G I C H D L K
E G J C H D L I
E G J C H D I K
C J E D I F L K
C J E D H F L K
C E I D H F L K
C J E D H F L I
C J E D H F I K
C G E D J F L K
C G E D I F L K
C G E D J F L I
C G E D J F I K
C G E D H F L K
C G J D H F L E
C G J D H F E K
C G E D H F L I
C G E D H F I K
C G J D H F E I
H J B F I G L K
E J I B H G L K
E J B F I H L K
E J B F I G L K
E J B F H G L K
E G B F I H L K
E J B F H G L I
E J B F H G I K
H J B D I G L K
H J B D I F L K
I G B D J F L K
H G B D J F L K
H G B D I F L K
H G B D J F L I
H G B D J F I K
E J B D I H L K
E J B D I G L K
E J B D H G L K
E G B D I H L K
E J B D H G L I
E J B D H G I K
E J B D I F L K
E J B D H F L K
E I B D H F L K
E J B D H F L I
E J B D H F I K
E G B D J F L K
E G B D I F L K
E G B D J F L I
E G B D J F I K
E G B D H F L K
H G B D J F L E
H G B D J F E K
E G B D H F L I
E G B D H F I K
H G B D J F E I
H J B C I G L K
H J B C I F L K
I G B C J F L K
H G B C J F L K
H G B C I F L K
H G B C J F L I
H G B C J F I K
E J B C I H L K
E J B C I G L K
E J B C H G L K
E G B C I H L K
E J B C H G L I
E J B C H G I K
E J B C I F L K
E J B C H F L K
E I B C H F L K
E J B C H F L I
E J B C H F I K
E G B C J F L K
E G B C I F L K
E G B C J F L I
E G B C J F I K
E G B C H F L K
H G B C J F L E
H G B C J F E K
E G B C H F L I
E G B C H F I K
H G B C J F E I
H J B C I D L K
I G B C J D L K
H G B C J D L K
H G B C I D L K
H G B C J D L I
H G B C J D I K
C J B D I F L K
C J B D H F L K
C I B D H F L K
C J B D H F L I
C J B D H F I K
C G B D J F L K
C G B D I F L K
C G B D J F L I
C G B D J F I K
C G B D H F L K
C G B D H F L J
H G B C J F D K
C G B D H F L I
C G B D H F I K
H G B C J F D I
E J B C I D L K
E J B C H D L K
E I B C H D L K
E J B C H D L I
E J B C H D I K
E G B C J D L K
E G B C I D L K
E G B C J D L I
E G B C J D I K
E G B C H D L K
H G B C J D L E
H G B C J D E K
E G B C H D L I
E G B C H D I K
H G B C J D E I
C J B D E F L K
C E B D I F L K
C J B D E F L I
C J B D E F I K
C E B D H F L K
C J B D H F L E
C J B D H F E K
C E B D H F L I
C E B D H F I K
C J B D H F E I
C G B D E F L K
C G B D J F L E
C G B D J F E K
C G B D E F L I
C G B D E F I K
C G B D J F E I
C G B D H F L E
C G B D H F E K
H G B C J F D E
C G B D H F E I
H J I F A G L K
E J I A H G L K
E J I F A H L K
E J I F A G L K
E G J F A H L K
E G I F A H L K
E G J F A H L I
E G J F A H I K
H J I D A G L K
H J I D A F L K
I G J D A F L K
H G J D A F L K
H G I D A F L K
H G J D A F L I
H G J D A F I K
E J I D A H L K
E J I D A G L K
E G J D A H L K
E G I D A H L K
E G J D A H L I
E G J D A H I K
E J I D A F L K
H J E D A F L K
H E I D A F L K
H J E D A F L I
H J E D A F I K
E G J D A F L K
E G I D A F L K
E G J D A F L I
E G J D A F I K
H G E D A F L K
H G J D A F L E
H G J D A F E K
H G E D A F L I
H G E D A F I K
H G J D A F E I
H J I C A G L K
H J I C A F L K
I G J C A F L K
H G J C A F L K
H G I C A F L K
H G J C A F L I
H G J C A F I K
E J I C A H L K
E J I C A G L K
E G J C A H L K
E G I C A H L K
E G J C A H L I
E G J C A H I K
E J I C A F L K
H J E C A F L K
H E I C A F L K
H J E C A F L I
H J E C A F I K
E G J C A F L K
E G I C A F L K
E G J C A F L I
E G J C A F I K
H G E C A F L K
H G J C A F L E
H G J C A F E K
H G E C A F L I
H G E C A F I K
H G J C A F E I
H J I C A D L K
I G J C A D L K
H G J C A D L K
H G I C A D L K
H G J C A D L I
H G J C A D I K
C J I D A F L K
H J F C A D L K
H F I C A D L K
H J F C A D L I
H J F C A D I K
C G J D A F L K
C G I D A F L K
C G J D A F L I
C G J D A F I K
H G F C A D L K
C G J D A F L H
H G J C A F D K
H G F C A D L I
H G F C A D I K
H G J C A F D I
E J I C A D L K
H J E C A D L K
H E I C A D L K
H J E C A D L I
H J E C A D I K
E G J C A D L K
E G I C A D L K
E G J C A D L I
E G J C A D I K
H G E C A D L K
H G J C A D L E
H G J C A D E K
H G E C A D L I
H G E C A D I K
H G J C A D E I
C J E D A F L K
C E I D A F L K
C J E D A F L I
C J E D A F I K
H E F C A D L K
H J F C A D L E
H J E C A F D K
H E F C A D L I
H E F C A D I K
H J E C A F D I
C G E D A F L K
C G J D A F L E
C G J D A F E K
C G E D A F L I
C G E D A F I K
C G J D A F E I
H G F C A D L E
H G E C A F D K
H G J C A F D E
H G E C A F D I
H J B A I G L K
H J B A I F L K
I J B F A G L K
H J B F A G L K
H G B A I F L K
H J B F A G L I
H J B F A G I K
E J B A I H L K
E J B A I G L K
E J B A H G L K
E G B A I H L K
E J B A H G L I
E J B A H G I K
E J B A I F L K
E J B F A H L K
E I B F A H L K
E J B F A H L I
E J B F A H I K
E J B F A G L K
E G B A I F L K
E J B F A G L I
E J B F A G I K
E G B F A H L K
H J B F A G L E
H J B F A G E K
E G B F A H L I
E G B F A H I K
H J B F A G E I
I J B D A H L K
I J B D A G L K
H J B D A G L K
I G B D A H L K
H J B D A G L I
H J B D A G I K
I J B D A F L K
H J B D A F L K
H I B D A F L K
H J B D A F L I
H J B D A F I K
F J B D A G L K
I G B D A F L K
F J B D A G L I
F J B D A G I K
H G B D A F L K
H G B D A F L J
H G B D A F J K
H G B D A F L I
H G B D A F I K
H G B D A F I J
E J B A I D L K
E J B D A H L K
E I B D A H L K
E J B D A H L I
E J B D A H I K
E J B D A G L K
E G B A I D L K
E J B D A G L I
E J B D A G I K
E G B D A H L K
H J B D A G L E
H J B D A G E K
E G B D A H L I
E G B D A H I K
H J B D A G E I
E J B D A F L K
E I B D A F L K
E J B D A F L I
E J B D A F I K
H E B D A F L K
H J B D A F L E
H J B D A F E K
H E B D A F L I
H E B D A F I K
H J B D A F E I
E G B D A F L K
E G B D A F L J
E G B D A F J K
E G B D A F L I
E G B D A F I K
E G B D A F I J
H G B D A F L E
H G B D A F E K
H G B D A F E J
H G B D A F E I
I J B C A H L K
I J B C A G L K
H J B C A G L K
I G B C A H L K
H J B C A G L I
H J B C A G I K
I J B C A F L K
H J B C A F L K
H I B C A F L K
H J B C A F L I
H J B C A F I K
C J B F A G L K
I G B C A F L K
C J B F A G L I
C J B F A G I K
H G B C A F L K
H G B C A F L J
H G B C A F J K
H G B C A F L I
H G B C A F I K
H G B C A F I J
E J B A I C L K
E J B C A H L K
E I B C A H L K
E J B C A H L I
E J B C A H I K
E J B C A G L K
E G B A I C L K
E J B C A G L I
E J B C A G I K
E G B C A H L K
H J B C A G L E
H J B C A G E K
E G B C A H L I
E G B C A H I K
H J B C A G E I
E J B C A F L K
E I B C A F L K
E J B C A F L I
E J B C A F I K
H E B C A F L K
H J B C A F L E
H J B C A F E K
H E B C A F L I
H E B C A F I K
H J B C A F E I
E G B C A F L K
E G B C A F L J
E G B C A F J K
E G B C A F L I
E G B C A F I K
E G B C A F I J
H G B C A F L E
H G B C A F E K
H G B C A F E J
H G B C A F E I
I J B C A D L K
H J B C A D L K
H I B C A D L K
H J B C A D L I
H J B C A D I K
C J B D A G L K
I G B C A D L K
C J B D A G L I
C J B D A G I K
H G B C A D L K
H G B C A D L J
H G B C A D J K
H G B C A D L I
H G B C A D I K
H G B C A D I J
C J B D A F L K
C I B D A F L K
C J B D A F L I
C J B D A F I K
H F B C A D L K
C J B D A F L H
H J B C A F D K
H F B C A D L I
H F B C A D I K
H J B C A F D I
C G B D A F L K
C G B D A F L J
C G B D A F J K
C G B D A F L I
C G B D A F I K
C G B D A F I J
C G B D A F L H
H G B C A F D K
H G B C A F D J
H G B C A F D I
E J B C A D L K
E I B C A D L K
E J B C A D L I
E J B C A D I K
H E B C A D L K
H J B C A D L E
H J B C A D E K
H E B C A D L I
H E B C A D I K
H J B C A D E I
E G B C A D L K
E G B C A D L J
E G B C A D J K
E G B C A D L I
E G B C A D I K
E G B C A D I J
H G B C A D L E
H G B C A D E K
H G B C A D E J
H G B C A D E I
C E B D A F L K
C J B D A F L E
C J B D A F E K
C E B D A F L I
C E B D A F I K
C J B D A F E I
H F B C A D L E
H E B C A F D K
H J B C A F D E
H E B C A F D I
C G B D A F L E
C G B D A F E K
C G B D A F E J
C G B D A F E I
H G B C A F D E"""

# Columnas en orden (Anexo C): slot 1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L
_SLOT_COLS = ('A', 'B', 'D', 'E', 'G', 'I', 'K', 'L')

# Slot 1X → partido donde juega el 3ro contra el 1ro del Grupo X
_SLOT_TO_PARTIDO = {
    'A': 79,   # P79: 1°A vs 3ro
    'B': 85,   # P85: 1°B vs 3ro
    'D': 81,   # P81: 1°D vs 3ro
    'E': 74,   # P74: 1°E vs 3ro
    'G': 82,   # P82: 1°G vs 3ro
    'I': 77,   # P77: 1°I vs 3ro
    'K': 87,   # P87: 1°K vs 3ro
    'L': 80,   # P80: 1°L vs 3ro
}


def _build_annex_c() -> Dict:
    """Parsea _ANNEX_C_RAW y devuelve {frozenset(8 letras): {slot_col: third_group}}."""
    table = {}
    for line in _ANNEX_C_RAW.strip().splitlines():
        parts = line.split()
        if len(parts) != 8:
            continue
        key = frozenset(parts)
        assignment = dict(zip(_SLOT_COLS, parts))
        table[key] = assignment
    return table


_ANNEX_C = _build_annex_c()


def assign_thirds_to_slots(thirds_advancing: List[Dict]) -> Dict[int, str]:
    """
    Dado el ranking de los 8 mejores terceros, devuelve {partido_num: equipo}.

    Consulta el Anexo C del Reglamento FIFA 2026 para determinar a qué slot
    de los dieciseisavos va el 3ro de cada grupo.

    thirds_advancing: lista de dicts con 'team' y 'group' (ej: 'GROUP_A').
    """
    if len(thirds_advancing) < 8:
        return {}

    groups = [t['group'].replace('GROUP_', '') for t in thirds_advancing[:8]]
    key = frozenset(groups)
    assignment = _ANNEX_C.get(key)
    if not assignment:
        return {}

    group_to_team = {
        t['group'].replace('GROUP_', ''): t['team']
        for t in thirds_advancing[:8]
    }

    result = {}
    for slot_col, third_grp in assignment.items():
        partido = _SLOT_TO_PARTIDO.get(slot_col)
        team = group_to_team.get(third_grp)
        if partido and team:
            result[partido] = (team, third_grp)  # (equipo, letra del grupo)
    return result


def _resolve(spec, group_results, partido_num, thirds_slot_map):
    kind, groups = spec
    if kind == '1':
        team, prov = _get_pos(group_results, groups, 0)
        return team, prov, f"1° Grp {groups}"
    if kind == '2':
        team, prov = _get_pos(group_results, groups, 1)
        return team, prov, f"2° Grp {groups}"
    # kind == '3': proyección por Anexo C (provisional hasta que el grupo cierre)
    if thirds_slot_map and partido_num in thirds_slot_map:
        team, group_letter = thirds_slot_map[partido_num]
        prov = not _is_group_complete(group_results, group_letter)
        return team, prov, team
    placeholder = f"3° ({groups})"
    return placeholder, True, placeholder


def build_round_of_32(
    group_results: Dict,
    thirds_advancing: List[Dict],
    thirds_slot_map: Optional[Dict] = None,
) -> List[Dict]:
    if thirds_slot_map is None:
        thirds_slot_map = assign_thirds_to_slots(thirds_advancing)

    matchups = []
    for num, spec1, spec2 in _BRACKET:
        utc, venue = _SCHEDULE.get(num, ("", ""))
        team1, prov1, lbl1 = _resolve(spec1, group_results, num, thirds_slot_map)
        team2, prov2, lbl2 = _resolve(spec2, group_results, num, thirds_slot_map)
        matchups.append({
            "partido": num,
            "etiqueta": f"{lbl1} vs {lbl2}",
            "equipo1": team1,
            "equipo2": team2,
            "provisional": prov1 or prov2,
            "prov1": prov1,
            "prov2": prov2,
            "tipo": f"{spec1[0]}_vs_{spec2[0]}",
            "utc_date": utc,
            "venue": venue,
        })
    return matchups
