"""
Datos curados por selección — ranking FIFA y palmarés mundialista (7.3 + 7.4).
No hay API limpia para esto, así que se cura a mano (como motm.py). Son datos
objetivos y estables: el palmarés casi no cambia; el ranking FIFA se actualiza
cada ~mes (fuente: inside.fifa.com/fifa-world-ranking/men, edición 11/06/2026).

Clave: nombre del equipo TAL CUAL lo entrega API-Football (mismo key que los
planteles), para no depender de traducciones. Valor: (rank, títulos, mejor).
  rank    = posición en el ranking FIFA masculino
  titulos = Copas del Mundo ganadas
  mejor   = mejor resultado histórico en Mundiales (texto en español)
"""

# team (nombre API-Football) -> {"rank", "titulos", "mejor"}
_SEL = {
    "Argentina":              (1,  3, "Campeón (1978, 1986, 2022)"),
    "Spain":                  (2,  1, "Campeón (2010)"),
    "France":                 (3,  2, "Campeón (1998, 2018)"),
    "England":                (4,  1, "Campeón (1966)"),
    "Portugal":               (5,  0, "3.º puesto (1966)"),
    "Brazil":                 (6,  5, "Campeón (1958, 1962, 1970, 1994, 2002)"),
    "Morocco":                (7,  0, "4.º puesto (2022)"),
    "Netherlands":            (8,  0, "Subcampeón (1974, 1978, 2010)"),
    "Belgium":                (9,  0, "3.º puesto (2018)"),
    "Germany":                (10, 4, "Campeón (1954, 1974, 1990, 2014)"),
    "Croatia":                (11, 0, "Subcampeón (2018)"),
    "Colombia":               (13, 0, "Cuartos de final (2014)"),
    "Mexico":                 (14, 0, "Cuartos de final (1970, 1986)"),
    "Senegal":                (15, 0, "Cuartos de final (2002)"),
    "Uruguay":                (16, 2, "Campeón (1930, 1950)"),
    "USA":                    (17, 0, "3.º puesto (1930)"),
    "Japan":                  (18, 0, "Octavos de final"),
    "Switzerland":            (19, 0, "Cuartos de final (1934, 1938, 1954)"),
    "Iran":                   (20, 0, "Fase de grupos"),
    "Türkiye":                (22, 0, "3.º puesto (2002)"),
    "Ecuador":                (23, 0, "Octavos de final (2006)"),
    "Austria":                (24, 0, "3.º puesto (1954)"),
    "South Korea":            (25, 0, "4.º puesto (2002)"),
    "Australia":              (27, 0, "Octavos de final (2006, 2022)"),
    "Algeria":                (28, 0, "Octavos de final (2014)"),
    "Egypt":                  (29, 0, "Fase de grupos"),
    "Canada":                 (30, 0, "Fase de grupos"),
    "Norway":                 (31, 0, "Octavos de final (1998)"),
    "Ivory Coast":            (33, 0, "Fase de grupos"),
    "Panama":                 (34, 0, "Fase de grupos"),
    "Sweden":                 (38, 0, "Subcampeón (1958)"),
    "Czechia":                (40, 0, "Subcampeón (1934, 1962)"),
    "Paraguay":               (41, 0, "Cuartos de final (2010)"),
    "Scotland":               (42, 0, "Fase de grupos"),
    "Tunisia":                (45, 0, "Fase de grupos"),
    "Congo DR":               (46, 0, "Fase de grupos (1974)"),
    "Uzbekistan":             (50, 0, "Debuta en 2026"),
    "Qatar":                  (56, 0, "Fase de grupos (2022)"),
    "Iraq":                   (57, 0, "Fase de grupos (1986)"),
    "South Africa":           (60, 0, "Fase de grupos"),
    "Saudi Arabia":           (61, 0, "Octavos de final (1994)"),
    "Jordan":                 (63, 0, "Debuta en 2026"),
    "Bosnia & Herzegovina":   (64, 0, "Fase de grupos (2014)"),
    "Cape Verde Islands":     (67, 0, "Debuta en 2026"),
    "Ghana":                  (73, 0, "Cuartos de final (2010)"),
    "Curaçao":                (82, 0, "Debuta en 2026"),
    "Haiti":                  (83, 0, "Fase de grupos (1974)"),
    "New Zealand":            (85, 0, "Fase de grupos"),
}


def ficha_seleccion(team: str):
    """Devuelve {'rank', 'titulos', 'mejor'} o None si no está curado."""
    row = _SEL.get(team)
    if not row:
        return None
    return {"rank": row[0], "titulos": row[1], "mejor": row[2]}


def fifa_rankings() -> dict:
    """{nombre_API: posición_ranking_FIFA} para el desempate oficial #7
    (último criterio: puntos→dif gol→goles→fair play→ranking FIFA). Keys = nombres
    de API-Football, mismos que usa standings, así que se enchufa directo."""
    return {team: row[0] for team, row in _SEL.items()}
