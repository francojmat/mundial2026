"""
Head-to-head curado a mano para cruces que la API-Football no indexa.
Datos reales verificados (Wikipedia, RSSSF, 11v11, ESPN, eu-football, thesoccerworldcups).
Cubre los enfrentamientos PREVIOS (pre-Mundial 2026) de los 72 cruces de fase de
grupos + algunos de eliminatorias. Últimos 5 por par, del más reciente al más viejo.

Clave: frozenset de los dos equipos en ESPAÑOL (nombre_es), igual que motm.py.
Valor: lista de partidos [{date, comp, round, home, away, gh, ga}] (home/away en español).
Si un partido no está cargado, no se muestra (degradación elegante).
"""


def _p(date, comp, rnd, home, away, gh, ga):
    return {"date": date, "comp": comp, "round": rnd,
            "home": home, "away": away, "gh": gh, "ga": ga}


_H2H = {
    # ── Grupo A/B/C/D... (todos los cruces de fase de grupos con historial previo) ──
    frozenset({"Alemania", "Costa de Marfil"}): [
        _p("2009-11-18", "Amistoso", "", "Alemania", "Costa de Marfil", 2, 2)],
    frozenset({"Alemania", "Ecuador"}): [
        _p("2013-05-29", "Amistoso", "", "Ecuador", "Alemania", 2, 4),
        _p("2006-06-20", "Mundial", "Fase de grupos", "Ecuador", "Alemania", 0, 3)],
    frozenset({"Arabia Saudita", "España"}): [
        _p("2012-09-07", "Amistoso", "", "España", "Arabia Saudita", 5, 0),
        _p("2010-05-29", "Amistoso", "", "España", "Arabia Saudita", 3, 2),
        _p("2006-06-23", "Mundial", "Fase de grupos", "Arabia Saudita", "España", 0, 1)],
    frozenset({"Arabia Saudita", "Uruguay"}): [
        _p("2018-06-20", "Mundial", "Fase de grupos", "Arabia Saudita", "Uruguay", 0, 1),
        _p("2014-10-10", "Amistoso", "", "Arabia Saudita", "Uruguay", 1, 1)],
    frozenset({"Argelia", "Argentina"}): [
        _p("2007-06-05", "Amistoso", "", "Argelia", "Argentina", 3, 4)],
    frozenset({"Argelia", "Austria"}): [
        _p("1982-06-21", "Mundial", "Fase de grupos", "Argelia", "Austria", 0, 2)],
    frozenset({"Argelia", "Jordania"}): [
        _p("2004-05-30", "Amistoso", "", "Argelia", "Jordania", 1, 1),
        _p("1988-07-14", "Copa Árabe", "Fase de grupos", "Jordania", "Argelia", 2, 1)],
    frozenset({"Argentina", "Austria"}): [
        _p("1990-05-03", "Amistoso", "", "Austria", "Argentina", 1, 1),
        _p("1980-05-05", "Amistoso", "", "Argentina", "Austria", 5, 1)],
    frozenset({"Australia", "Estados Unidos"}): [
        _p("2025-10-14", "Amistoso", "", "Estados Unidos", "Australia", 2, 1),
        _p("2010-06-05", "Amistoso", "", "Estados Unidos", "Australia", 3, 1),
        _p("1998-11-06", "Amistoso", "", "Estados Unidos", "Australia", 0, 0),
        _p("1992-06-13", "Amistoso", "", "Estados Unidos", "Australia", 0, 1)],
    frozenset({"Australia", "Paraguay"}): [
        _p("2010-10-09", "Amistoso", "", "Australia", "Paraguay", 1, 0),
        _p("2006-10-07", "Amistoso", "", "Australia", "Paraguay", 1, 1),
        _p("2000-06-15", "Amistoso", "", "Australia", "Paraguay", 2, 1),
        _p("2000-06-12", "Amistoso", "", "Australia", "Paraguay", 0, 0),
        _p("2000-06-09", "Amistoso", "", "Australia", "Paraguay", 0, 0)],
    frozenset({"Australia", "Turquía"}): [
        _p("2004-05-24", "Amistoso", "", "Australia", "Turquía", 0, 1),
        _p("2004-05-21", "Amistoso", "", "Australia", "Turquía", 1, 3)],
    frozenset({"Bosnia y Herz.", "Qatar"}): [
        _p("2010-08-11", "Amistoso", "", "Bosnia y Herz.", "Qatar", 1, 1),
        _p("2000-01-24", "Amistoso", "", "Qatar", "Bosnia y Herz.", 2, 0)],
    frozenset({"Bosnia y Herz.", "Suiza"}): [
        _p("2016-03-29", "Amistoso", "", "Suiza", "Bosnia y Herz.", 0, 2)],
    frozenset({"Brasil", "Escocia"}): [
        _p("1998-06-10", "Mundial", "Fase de grupos", "Brasil", "Escocia", 2, 1),
        _p("1990-06-20", "Mundial", "Fase de grupos", "Brasil", "Escocia", 1, 0),
        _p("1982-06-18", "Mundial", "Fase de grupos", "Brasil", "Escocia", 4, 1),
        _p("1974-06-18", "Mundial", "Fase de grupos", "Escocia", "Brasil", 0, 0)],
    frozenset({"Brasil", "Haití"}): [
        _p("2016-06-08", "Copa América", "Fase de grupos", "Brasil", "Haití", 7, 1),
        _p("2004-08-18", "Amistoso", "", "Haití", "Brasil", 0, 6)],
    frozenset({"Brasil", "Marruecos"}): [
        _p("1998-06-16", "Mundial", "Fase de grupos", "Brasil", "Marruecos", 3, 0),
        _p("1997-10-29", "Amistoso", "", "Brasil", "Marruecos", 2, 0)],
    frozenset({"Bélgica", "Egipto"}): [
        _p("2022-11-18", "Amistoso", "", "Bélgica", "Egipto", 1, 2),
        _p("2018-06-06", "Amistoso", "", "Bélgica", "Egipto", 3, 0),
        _p("2005-02-09", "Amistoso", "", "Egipto", "Bélgica", 4, 0),
        _p("1999-03-30", "Amistoso", "", "Bélgica", "Egipto", 0, 1)],
    frozenset({"Canadá", "Suiza"}): [
        _p("2002-05-15", "Amistoso", "", "Suiza", "Canadá", 1, 3)],
    frozenset({"Colombia", "Portugal"}): [
        _p("2014-06-06", "Amistoso", "", "Portugal", "Colombia", 1, 0)],
    frozenset({"Corea del Sur", "México"}): [
        _p("2020-11-14", "Amistoso", "", "México", "Corea del Sur", 3, 2),
        _p("2018-06-23", "Mundial", "Fase de grupos", "México", "Corea del Sur", 2, 1),
        _p("2014-01-29", "Amistoso", "", "México", "Corea del Sur", 4, 0),
        _p("1998-06-13", "Mundial", "Fase de grupos", "México", "Corea del Sur", 3, 1)],
    frozenset({"Corea del Sur", "Rep. Checa"}): [
        _p("2016-06-05", "Amistoso", "", "Rep. Checa", "Corea del Sur", 1, 2),
        _p("2001-08-14", "Amistoso", "", "Rep. Checa", "Corea del Sur", 5, 0),
        _p("1998-05-26", "Amistoso", "", "Corea del Sur", "Rep. Checa", 2, 2)],
    frozenset({"Croacia", "Inglaterra"}): [
        _p("2021-06-13", "Eurocopa", "Fase de grupos", "Inglaterra", "Croacia", 1, 0),
        _p("2018-11-18", "Liga de Naciones", "Fase de grupos", "Inglaterra", "Croacia", 2, 1),
        _p("2018-10-12", "Liga de Naciones", "Fase de grupos", "Croacia", "Inglaterra", 0, 0),
        _p("2018-07-11", "Mundial", "Semifinal", "Croacia", "Inglaterra", 2, 1),
        _p("2009-09-09", "Eliminatorias", "", "Inglaterra", "Croacia", 5, 1)],
    frozenset({"Egipto", "Irán"}): [
        _p("2000-06-07", "Amistoso", "", "Irán", "Egipto", 1, 1)],
    frozenset({"Egipto", "Nueva Zelanda"}): [
        _p("2024-03-22", "Amistoso", "", "Egipto", "Nueva Zelanda", 1, 0)],
    frozenset({"Escocia", "Marruecos"}): [
        _p("1998-06-23", "Mundial", "Fase de grupos", "Escocia", "Marruecos", 0, 3)],
    frozenset({"España", "Uruguay"}): [
        _p("2013-06-16", "Copa Confederaciones", "Fase de grupos", "España", "Uruguay", 2, 1),
        _p("2013-02-06", "Amistoso", "", "España", "Uruguay", 3, 1),
        _p("2005-08-17", "Amistoso", "", "España", "Uruguay", 2, 0),
        _p("1995-01-18", "Amistoso", "", "España", "Uruguay", 2, 2),
        _p("1991-09-04", "Amistoso", "", "España", "Uruguay", 2, 1)],
    frozenset({"Estados Unidos", "Paraguay"}): [
        _p("2025-11-15", "Amistoso", "", "Estados Unidos", "Paraguay", 2, 1),
        _p("2018-03-27", "Amistoso", "", "Estados Unidos", "Paraguay", 1, 0),
        _p("2016-06-11", "Copa América", "Fase de grupos", "Estados Unidos", "Paraguay", 1, 0),
        _p("2011-03-29", "Amistoso", "", "Estados Unidos", "Paraguay", 0, 1)],
    frozenset({"Estados Unidos", "Turquía"}): [
        _p("2025-06-07", "Amistoso", "", "Estados Unidos", "Turquía", 1, 2),
        _p("2014-06-01", "Amistoso", "", "Estados Unidos", "Turquía", 2, 1),
        _p("2010-05-29", "Amistoso", "", "Estados Unidos", "Turquía", 2, 1)],
    frozenset({"Francia", "Noruega"}): [
        _p("2014-05-27", "Amistoso", "", "Francia", "Noruega", 4, 0),
        _p("2010-08-11", "Amistoso", "", "Noruega", "Francia", 2, 1),
        _p("1998-02-25", "Amistoso", "", "Francia", "Noruega", 3, 3),
        _p("1995-07-22", "Amistoso", "", "Noruega", "Francia", 0, 0),
        _p("1988-09-28", "Eliminatorias", "", "Francia", "Noruega", 1, 0)],
    frozenset({"Francia", "Senegal"}): [
        _p("2002-05-31", "Mundial", "Fase de grupos", "Francia", "Senegal", 0, 1)],
    frozenset({"Ghana", "Inglaterra"}): [
        _p("2011-03-29", "Amistoso", "", "Inglaterra", "Ghana", 1, 1)],
    frozenset({"Inglaterra", "Panamá"}): [
        _p("2018-06-24", "Mundial", "Fase de grupos", "Inglaterra", "Panamá", 6, 1)],
    frozenset({"Irán", "Nueva Zelanda"}): [
        _p("2003-10-12", "Amistoso", "", "Irán", "Nueva Zelanda", 3, 0),
        _p("1973-08-12", "Amistoso", "", "Irán", "Nueva Zelanda", 0, 0)],
    frozenset({"Japón", "Países Bajos"}): [
        _p("2013-11-16", "Amistoso", "", "Países Bajos", "Japón", 2, 2),
        _p("2010-06-19", "Mundial", "Fase de grupos", "Países Bajos", "Japón", 1, 0)],
    frozenset({"Japón", "Suecia"}): [
        _p("2002-05-25", "Amistoso", "", "Japón", "Suecia", 1, 1),
        _p("1997-02-13", "Amistoso", "", "Japón", "Suecia", 0, 1),
        _p("1996-02-22", "Amistoso", "", "Suecia", "Japón", 1, 1),
        _p("1995-06-10", "Amistoso", "", "Japón", "Suecia", 2, 2)],
    frozenset({"Japón", "Túnez"}): [
        _p("2023-10-17", "Amistoso", "", "Japón", "Túnez", 2, 0),
        _p("2022-06-14", "Amistoso", "", "Japón", "Túnez", 0, 3),
        _p("2015-03-27", "Amistoso", "", "Japón", "Túnez", 2, 0),
        _p("2003-10-08", "Amistoso", "", "Japón", "Túnez", 1, 0),
        _p("2002-06-14", "Mundial", "Fase de grupos", "Japón", "Túnez", 2, 0)],
    frozenset({"México", "Rep. Checa"}): [
        _p("2000-02-08", "Amistoso", "", "México", "Rep. Checa", 1, 2)],
    frozenset({"México", "Sudáfrica"}): [
        _p("2010-06-11", "Mundial", "Fase de grupos", "Sudáfrica", "México", 1, 1),
        _p("2005-07-08", "Copa de Oro", "Fase de grupos", "Sudáfrica", "México", 2, 1),
        _p("2000-06-07", "Amistoso", "", "México", "Sudáfrica", 4, 2),
        _p("1993-10-06", "Amistoso", "", "México", "Sudáfrica", 4, 0)],
    frozenset({"Noruega", "Senegal"}): [
        _p("2006-03-01", "Amistoso", "", "Senegal", "Noruega", 2, 1)],
    frozenset({"Paraguay", "Turquía"}): [
        _p("1995-06-17", "Amistoso", "", "Paraguay", "Turquía", 0, 0)],
    frozenset({"Países Bajos", "Suecia"}): [
        _p("2017-10-11", "Eliminatorias", "", "Países Bajos", "Suecia", 2, 0),
        _p("2016-09-06", "Eliminatorias", "", "Suecia", "Países Bajos", 1, 1),
        _p("2010-10-12", "Eliminatorias", "", "Países Bajos", "Suecia", 4, 1),
        _p("2008-11-19", "Amistoso", "", "Países Bajos", "Suecia", 3, 1)],
    frozenset({"Países Bajos", "Túnez"}): [
        _p("2009-02-11", "Amistoso", "", "Túnez", "Países Bajos", 1, 1)],
    frozenset({"Portugal", "Uzbekistán"}): [
        _p("2012-09-18", "Amistoso", "", "Portugal", "Uzbekistán", 5, 2)],
    frozenset({"Qatar", "Suiza"}): [
        _p("2018-11-14", "Amistoso", "", "Suiza", "Qatar", 0, 1)],
    frozenset({"Suecia", "Túnez"}): [
        _p("2003-02-12", "Amistoso", "", "Túnez", "Suecia", 1, 0),
        _p("1999-02-10", "Amistoso", "", "Túnez", "Suecia", 0, 1),
        _p("1992-04-22", "Amistoso", "", "Túnez", "Suecia", 0, 1),
        _p("1976-02-28", "Amistoso", "", "Túnez", "Suecia", 1, 1)],
    # ── Cruces de bracket curados previamente ──
    frozenset({"Inglaterra", "Portugal"}): [
        _p("2000-06-12", "Eurocopa", "Fase de grupos", "Portugal", "Inglaterra", 3, 2)],
    frozenset({"Corea del Sur", "Suiza"}): [
        _p("2006-06-23", "Mundial", "Fase de grupos", "Suiza", "Corea del Sur", 2, 0)],
}


def h2h_curado(team1: str, team2: str) -> list:
    """Historial curado entre dos equipos (nombres en español), o lista vacía."""
    return _H2H.get(frozenset({team1, team2}), [])
