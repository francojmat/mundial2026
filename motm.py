"""
Man of the Match (Player of the Match) OFICIAL de FIFA — curado a mano.
Es un dato que FIFA entrega a un jugador real por partido; NO es el de mejor rating.
No hay fuente automática limpia, así que se actualiza manualmente a medida que se
juegan los partidos (fuente: fifa.com / play.fifa.com/potm).

Clave: frozenset de los dos equipos NORMALIZADOS al español (nombre_es), para que
matchee venga el nombre como venga de la API. Valor: nombre del jugador.
Si un partido no está cargado, no se muestra nada (degradación elegante).
"""
from countries import nombre_es

# (equipos en español)  →  jugador
_MOTM = {
    frozenset({"México", "Sudáfrica"}):        "Julián Quiñones",
    frozenset({"Ghana", "Panamá"}):            "Antoine Semenyo",
    frozenset({"Inglaterra", "Croacia"}):      "Harry Kane",
    frozenset({"Portugal", "Congo RD"}):       "João Neves",
    frozenset({"Uzbekistán", "Colombia"}):     "Luis Díaz",
    frozenset({"Rep. Checa", "Sudáfrica"}):    "Ladislav Krejčí",
    frozenset({"Suiza", "Bosnia y Herz."}):    "Johan Manzambi",
    frozenset({"Canadá", "Qatar"}):            "Jonathan David",
    frozenset({"México", "Corea del Sur"}):    "Luis Romo",
}


def motm_for(home: str, away: str):
    """Devuelve el jugador del partido (oficial) o None si no está curado."""
    return _MOTM.get(frozenset({nombre_es(home), nombre_es(away)}))
