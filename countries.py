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


# País de la liga (API-Football) → español, para mostrar el club del jugador (7.1)
_LIGA_PAIS_ES = {
    "Spain": "España", "England": "Inglaterra", "Italy": "Italia", "Germany": "Alemania",
    "France": "Francia", "Portugal": "Portugal", "Netherlands": "Países Bajos",
    "Belgium": "Bélgica", "Turkey": "Turquía", "Türkiye": "Turquía", "Greece": "Grecia",
    "Scotland": "Escocia", "Austria": "Austria", "Switzerland": "Suiza", "Croatia": "Croacia",
    "Denmark": "Dinamarca", "Norway": "Noruega", "Sweden": "Suecia", "Russia": "Rusia",
    "Ukraine": "Ucrania", "Poland": "Polonia", "Czech-Republic": "Rep. Checa", "Czechia": "Rep. Checa",
    "Serbia": "Serbia", "USA": "Estados Unidos", "Mexico": "México", "Brazil": "Brasil",
    "Argentina": "Argentina", "Colombia": "Colombia", "Ecuador": "Ecuador", "Uruguay": "Uruguay",
    "Chile": "Chile", "Paraguay": "Paraguay", "Peru": "Perú", "Japan": "Japón",
    "South-Korea": "Corea del Sur", "Korea-Republic": "Corea del Sur", "China": "China",
    "Saudi-Arabia": "Arabia Saudita", "Qatar": "Catar", "United-Arab-Emirates": "Emiratos Árabes",
    "Egypt": "Egipto", "Morocco": "Marruecos", "Algeria": "Argelia", "Tunisia": "Túnez",
    "Nigeria": "Nigeria", "Ghana": "Ghana", "South-Africa": "Sudáfrica", "Australia": "Australia",
    "Iran": "Irán", "Iraq": "Irak", "Jordan": "Jordania", "Uzbekistan": "Uzbekistán",
    "Canada": "Canadá", "Romania": "Rumania", "Hungary": "Hungría", "Bulgaria": "Bulgaria",
    "Israel": "Israel", "Cyprus": "Chipre", "Slovakia": "Eslovaquia", "Slovenia": "Eslovenia",
    "Ireland": "Irlanda", "Wales": "Gales", "Finland": "Finlandia", "Bosnia": "Bosnia y Herz.",
    "India": "India", "Thailand": "Tailandia", "Costa-Rica": "Costa Rica", "Panama": "Panamá",
    "Venezuela": "Venezuela", "Bolivia": "Bolivia",
}


def pais_liga_es(country: str) -> str:
    """País de la liga en español (o el original si no está mapeado)."""
    if not country:
        return ""
    return _LIGA_PAIS_ES.get(country, country.replace("-", " "))


def bandera_img(nombre_api: str, cls: str = "", w: int = 20, h: int = 15) -> str:
    """Solo la bandera (img), sin margen, para armar layouts a medida."""
    iso = _PAISES.get(nombre_api, (nombre_api, ""))[1]
    if not iso:
        return ""
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="/flags/20x15/{iso}.png" alt="{nombre_es(nombre_api)}" '
            f'width="{w}" height="{h}" style="vertical-align:middle;flex-shrink:0">')


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


# Fotos curadas (Wikimedia Commons, licencia libre) para los estadios que la API
# de API-Football no trae o devuelve como placeholder. Se sirven desde /venues/.
# Clave = nombre del estadio como viene en los fixtures de API-Football.
VENUE_PHOTO = {
    "AT&T Stadium":            "/venues/att-stadium.jpg",
    "Levi's Stadium":          "/venues/levis-stadium.jpg",
    "Lincoln Financial Field": "/venues/lincoln-financial-field.jpg",
    "MetLife Stadium":         "/venues/metlife-stadium.jpg",
    "NRG Stadium":             "/venues/nrg-stadium.jpg",
    "SoFi Stadium":            "/venues/sofi-stadium.jpg",
    "Arrowhead Stadium":       "/venues/arrowhead-stadium.jpg",
    "Hard Rock Stadium":       "/venues/hard-rock-stadium.jpg",
    "Mercedes-Benz Stadium":   "/venues/mercedes-benz-stadium.jpg",
    "Lumen Field":             "/venues/lumen-field.jpg",
    "Estadio BBVA":            "/venues/estadio-bbva.jpg",
}


# Coordenadas (lat, lon) de las 16 sedes del Mundial 2026 — curadas.
# Para el clima (Open-Meteo) y el link al mapa. Clave = nombre del estadio en los fixtures.
VENUE_COORDS = {
    "Estadio Azteca":          (19.3029, -99.1505),
    "Estadio BBVA":            (25.6692, -100.2444),
    "Estadio Akron":           (20.6817, -103.4625),
    "MetLife Stadium":         (40.8135, -74.0745),
    "AT&T Stadium":            (32.7473, -97.0945),
    "SoFi Stadium":            (33.9535, -118.3392),
    "Arrowhead Stadium":       (39.0489, -94.4839),
    "NRG Stadium":             (29.6847, -95.4107),
    "Lincoln Financial Field": (39.9008, -75.1675),
    "Mercedes-Benz Stadium":   (33.7553, -84.4006),
    "Hard Rock Stadium":       (25.9580, -80.2389),
    "Lumen Field":             (47.5952, -122.3316),
    "Levi's Stadium":          (37.4030, -121.9700),
    "Gillette Stadium":        (42.0909, -71.2643),
    "BC Place":                (49.2768, -123.1120),
    "BMO Field":               (43.6332, -79.4185),
}


def venue_maps_url(name: str):
    """Link a Google Maps de la sede (por coordenadas), o None si no se conoce."""
    c = VENUE_COORDS.get(name)
    return f"https://www.google.com/maps/search/?api=1&query={c[0]},{c[1]}" if c else None


# Datos curados de las 16 sedes (Wikipedia): país, año de inauguración, equipo local. (6.2 / 6.3)
VENUE_INFO = {
    "Estadio Azteca":          {"country": "México",          "year": 1966, "home": "Club América"},
    "Estadio BBVA":            {"country": "México",          "year": 2015, "home": "Rayados de Monterrey"},
    "Estadio Akron":           {"country": "México",          "year": 2010, "home": "Chivas de Guadalajara"},
    "MetLife Stadium":         {"country": "Estados Unidos",  "year": 2010, "home": "Giants y Jets (NFL)"},
    "AT&T Stadium":            {"country": "Estados Unidos",  "year": 2009, "home": "Dallas Cowboys (NFL)"},
    "SoFi Stadium":            {"country": "Estados Unidos",  "year": 2020, "home": "Rams y Chargers (NFL)"},
    "Arrowhead Stadium":       {"country": "Estados Unidos",  "year": 1972, "home": "Kansas City Chiefs (NFL)"},
    "NRG Stadium":             {"country": "Estados Unidos",  "year": 2002, "home": "Houston Texans (NFL)"},
    "Lincoln Financial Field": {"country": "Estados Unidos",  "year": 2003, "home": "Philadelphia Eagles (NFL)"},
    "Mercedes-Benz Stadium":   {"country": "Estados Unidos",  "year": 2017, "home": "Atlanta United (MLS)"},
    "Hard Rock Stadium":       {"country": "Estados Unidos",  "year": 1987, "home": "Miami Dolphins (NFL)"},
    "Lumen Field":             {"country": "Estados Unidos",  "year": 2002, "home": "Seattle Sounders (MLS)"},
    "Levi's Stadium":          {"country": "Estados Unidos",  "year": 2014, "home": "San Francisco 49ers (NFL)"},
    "Gillette Stadium":        {"country": "Estados Unidos",  "year": 2002, "home": "New England Revolution (MLS)"},
    "BC Place":                {"country": "Canadá",          "year": 1983, "home": "Vancouver Whitecaps (MLS)"},
    "BMO Field":               {"country": "Canadá",          "year": 2007, "home": "Toronto FC (MLS)"},
}
