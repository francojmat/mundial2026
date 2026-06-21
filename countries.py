"""
Mapeo de nombres de equipos → (nombre español, código ISO bandera).
Banderas vía flagcdn.com.
"""

# (nombre_es, iso_code para flagcdn.com)
_PAISES = {
    "Mexico":               ("México",           "mx"),
    "Korea Republic":       ("Corea del Sur",    "kr"),
    "South Korea":          ("Corea del Sur",    "kr"),
    "Czechia":              ("Rep. Checa",       "cz"),
    "Czech Republic":       ("Rep. Checa",       "cz"),
    "South Africa":         ("Sudáfrica",        "za"),
    "Canada":               ("Canadá",           "ca"),
    "Switzerland":          ("Suiza",            "ch"),
    "Bosnia-H.":            ("Bosnia y Herz.",   "ba"),
    "Bosnia Herzegovina":   ("Bosnia y Herz.",   "ba"),
    "Bosnia-Herzegovina":   ("Bosnia y Herz.",   "ba"),
    "Bosnia & Herzegovina": ("Bosnia y Herz.",   "ba"),
    "Qatar":                ("Qatar",            "qa"),
    "Scotland":             ("Escocia",          "gb-sct"),
    "Morocco":              ("Marruecos",        "ma"),
    "Brazil":               ("Brasil",           "br"),
    "Haiti":                ("Haití",            "ht"),
    "USA":                  ("Estados Unidos",   "us"),
    "United States":        ("Estados Unidos",   "us"),
    "Australia":            ("Australia",        "au"),
    "Turkey":               ("Turquía",          "tr"),
    "Türkiye":              ("Turquía",          "tr"),
    "Paraguay":             ("Paraguay",         "py"),
    "Germany":              ("Alemania",         "de"),
    "Ivory Coast":          ("Costa de Marfil",  "ci"),
    "Côte d'Ivoire":        ("Costa de Marfil",  "ci"),
    "Ecuador":              ("Ecuador",          "ec"),
    "Curaçao":              ("Curazao",          "cw"),
    "Curacao":              ("Curazao",          "cw"),
    "Sweden":               ("Suecia",           "se"),
    "Japan":                ("Japón",            "jp"),
    "Netherlands":          ("Países Bajos",     "nl"),
    "Tunisia":              ("Túnez",            "tn"),
    "Iran":                 ("Irán",             "ir"),
    "New Zealand":          ("Nueva Zelanda",    "nz"),
    "Belgium":              ("Bélgica",          "be"),
    "Egypt":                ("Egipto",           "eg"),
    "Saudi Arabia":         ("Arabia Saudita",   "sa"),
    "Uruguay":              ("Uruguay",          "uy"),
    "Cape Verde":           ("Cabo Verde",       "cv"),
    "Cape Verde Islands":   ("Cabo Verde",       "cv"),
    "Spain":                ("España",           "es"),
    "Norway":               ("Noruega",          "no"),
    "France":               ("Francia",          "fr"),
    "Senegal":              ("Senegal",          "sn"),
    "Iraq":                 ("Irak",             "iq"),
    "Argentina":            ("Argentina",        "ar"),
    "Austria":              ("Austria",          "at"),
    "Jordan":               ("Jordania",         "jo"),
    "Algeria":              ("Argelia",          "dz"),
    "Colombia":             ("Colombia",         "co"),
    "Portugal":             ("Portugal",         "pt"),
    "Congo DR":             ("Congo RD",         "cd"),
    "DR Congo":             ("Congo RD",         "cd"),
    "Uzbekistan":           ("Uzbekistán",       "uz"),
    "England":              ("Inglaterra",       "gb-eng"),
    "Ghana":                ("Ghana",            "gh"),
    "Panama":               ("Panamá",           "pa"),
    "Croatia":              ("Croacia",          "hr"),
}


def _flag_img(iso: str, nombre: str) -> str:
    url = f"/flags/20x15/{iso}.png"
    return f'<img src="{url}" alt="{nombre}" width="20" height="15" style="vertical-align:middle;margin-right:6px;flex-shrink:0">'


def traducir(nombre_api: str) -> str:
    """Devuelve HTML: bandera + nombre en español."""
    if nombre_api in _PAISES:
        nombre_es, iso = _PAISES[nombre_api]
        return f"{_flag_img(iso, nombre_es)}{nombre_es}"
    return nombre_api


def nombre_es(nombre_api: str) -> str:
    """Solo el nombre en español, sin HTML."""
    if nombre_api in _PAISES:
        return _PAISES[nombre_api][0]
    return nombre_api


# Capacidades oficiales de configuración Mundial 2026 (Wikipedia/FIFA).
# Clave = nombre del estadio como viene en los fixtures de API-Football.
VENUE_CAPACITY = {
    "Estadio Azteca":          80824,
    "MetLife Stadium":         80663,
    "AT&T Stadium":            70649,
    "SoFi Stadium":            70492,
    "Arrowhead Stadium":       69045,
    "Levi's Stadium":          68827,
    "NRG Stadium":             68777,
    "Lincoln Financial Field": 68324,
    "Mercedes-Benz Stadium":   68239,
    "Lumen Field":             66925,
    "Hard Rock Stadium":       64478,
    "Gillette Stadium":        64146,
    "BC Place":                52497,
    "Estadio BBVA":            51243,
    "Estadio Akron":           45664,
    "BMO Field":               43036,
}


def capacidad_fmt(name: str):
    """Capacidad formateada con puntos de miles, o None si no se conoce."""
    cap = VENUE_CAPACITY.get(name)
    return f"{cap:,}".replace(",", ".") if cap else None
