"""
Render de páginas internas (plantel, y a futuro detalle de partido) con la
identidad visual de marca. Patrón: una página "shell" estática (header + Volver +
contenedor + JS) que inyecta un fragmento pre-renderizado desde un JSON.
"""

from html_renderer import T, TEL, BG, WHT, BDR, BDR2, TXT, MUT, DIM, GRY
from countries import traducir, nombre_es

# Posición API-Football → grupo en español
_POS_GROUPS = [
    ("Goalkeeper", "Arqueros"),
    ("Defender",   "Defensores"),
    ("Midfielder", "Mediocampistas"),
    ("Attacker",   "Delanteros"),
]
_POS_SINGULAR = {
    "Goalkeeper": "Arquero",
    "Defender":   "Defensor",
    "Midfielder": "Mediocampista",
    "Attacker":   "Delantero",
}

# Silueta gris de fallback si la foto no carga
_FALLBACK = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'"
             "%3E%3Ccircle cx='20' cy='20' r='20' fill='%23f0ebe4'/%3E%3Ccircle cx='20' cy='15'"
             " r='6' fill='%23c8b8a8'/%3E%3Cpath d='M8 34c0-7 5-11 12-11s12 4 12 11' fill='%23c8b8a8'/%3E%3C/svg%3E")


def _player_card(p: dict) -> str:
    photo  = p.get("photo") or _FALLBACK
    num    = p.get("number")
    num_s  = str(num) if num else "—"
    name   = p.get("name", "")
    pos    = _POS_SINGULAR.get(p.get("position", ""), p.get("position", ""))
    age    = p.get("age")
    age_s  = f"{age} años" if age else "—"
    return (
        f'<div class="pl-card" onclick="this.classList.toggle(\'open\')">'
        f'<div class="pl-row">'
        f'<img class="pl-photo" src="{photo}" loading="lazy" alt="" '
        f'onerror="this.onerror=null;this.src=\'{_FALLBACK}\'">'
        f'<span class="pl-num">{num_s}</span>'
        f'<span class="pl-name">{name}</span>'
        f'<span class="pl-chev">&#9662;</span>'
        f'</div>'
        f'<div class="pl-detail">'
        f'<div class="pl-info">'
        f'<div class="pl-kv"><span class="pl-k">Posición</span><span>{pos}</span></div>'
        f'<div class="pl-kv"><span class="pl-k">Dorsal</span><span>{num_s}</span></div>'
        f'<div class="pl-kv"><span class="pl-k">Edad</span><span>{age_s}</span></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _coach_card(coach: dict) -> str:
    if not coach.get("name"):
        return ""
    photo = coach.get("photo") or _FALLBACK
    age   = coach.get("age")
    age_s = f"{age} años" if age else ""
    nat   = coach.get("nationality", "")
    meta  = " · ".join(x for x in [nat, age_s] if x)
    return (
        f'<div class="pl-group">'
        f'<h3 class="pl-gt">Director Técnico</h3>'
        f'<div class="coach-card">'
        f'<img class="coach-photo" src="{photo}" loading="lazy" alt="" '
        f'onerror="this.onerror=null;this.src=\'{_FALLBACK}\'">'
        f'<div>'
        f'<div class="coach-name">{coach.get("name", "")}</div>'
        f'<div class="coach-meta">{meta}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def render_squad_fragment(team_name: str, squad: dict) -> str:
    """Fragmento HTML del plantel (título + grupos por posición + DT). Va en planteles.json."""
    players = squad.get("players", [])
    if not players:
        return ('<p style="font-size:.8rem;color:#7c6a58;text-align:center;margin-top:20px">'
                'Plantel no disponible todavía.</p>')

    title = f'<h2 class="pl-title">{traducir(team_name)}</h2>'

    groups_html = ""
    for pos_key, pos_label in _POS_GROUPS:
        ps = [p for p in players if p.get("position") == pos_key]
        if not ps:
            continue
        ps.sort(key=lambda p: (p.get("number") or 999))
        cards = "".join(_player_card(p) for p in ps)
        groups_html += (f'<div class="pl-group"><h3 class="pl-gt">{pos_label} '
                        f'<span class="pl-gc">{len(ps)}</span></h3>'
                        f'<div class="pl-list">{cards}</div></div>')

    return title + groups_html + _coach_card(squad.get("coach", {}))


def render_plantel_shell() -> str:
    """Página shell estática de plantel. Lee ?t= e inyecta el fragmento de planteles.json."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Plantel · Mundial 2026</title>
  <link rel="icon" href="/favicon.ico">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:24px 18px 48px}}
    .wrap{{max-width:640px;margin:0 auto}}
    .topbar{{display:flex;align-items:center;gap:12px;margin-bottom:22px}}
    .back{{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:600;color:{T};text-decoration:none;border:1px solid {BDR};border-radius:8px;padding:6px 12px;background:{WHT}}}
    .back:hover{{background:{GRY}}}
    .brand{{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{DIM}}}
    .pl-title{{font-size:1.5rem;font-weight:700;letter-spacing:-.02em;margin-bottom:20px;display:flex;align-items:center;gap:10px}}
    .pl-title img{{width:32px;height:24px;border-radius:2px}}
    .pl-group{{margin-bottom:24px}}
    .pl-gt{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{T};margin-bottom:10px;display:flex;align-items:center;gap:8px}}
    .pl-gc{{background:{GRY};color:{MUT};border-radius:10px;padding:1px 8px;font-size:.62rem}}
    .pl-list{{display:flex;flex-direction:column;gap:7px}}
    .pl-card{{background:{WHT};border:1px solid {BDR};border-radius:10px;cursor:pointer;user-select:none;overflow:hidden}}
    .pl-card:hover{{border-color:{BDR2}}}
    .pl-row{{display:flex;align-items:center;gap:11px;padding:9px 13px}}
    .pl-photo{{width:38px;height:38px;border-radius:50%;object-fit:cover;background:{GRY};flex-shrink:0}}
    .pl-num{{font-size:.82rem;font-weight:700;color:{T};min-width:24px;text-align:center}}
    .pl-name{{font-size:.9rem;font-weight:600;flex:1}}
    .pl-chev{{color:{BDR2};font-size:.7rem;transition:transform .2s}}
    .pl-card.open .pl-chev{{transform:rotate(180deg)}}
    .pl-detail{{display:none;border-top:1px solid {GRY};padding:11px 13px;background:{BG}}}
    .pl-card.open .pl-detail{{display:block}}
    .pl-info{{display:flex;flex-wrap:wrap;gap:8px 22px}}
    .pl-kv{{display:flex;flex-direction:column;gap:1px}}
    .pl-k{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM}}}
    .pl-kv span:last-child{{font-size:.85rem;font-weight:600}}
    .coach-card{{display:flex;align-items:center;gap:14px;background:{WHT};border:1px solid {BDR};border-radius:10px;padding:13px 15px}}
    .coach-photo{{width:52px;height:52px;border-radius:50%;object-fit:cover;background:{GRY};flex-shrink:0}}
    .coach-name{{font-size:1rem;font-weight:700}}
    .coach-meta{{font-size:.78rem;color:{MUT};margin-top:2px}}
    .loading{{text-align:center;color:{MUT};font-size:.85rem;margin-top:40px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <a class="back" href="/">&#8592; Volver al inicio</a>
      <span class="brand">Mundial 2026</span>
    </div>
    <div id="squad"><p class="loading">Cargando plantel…</p></div>
  </div>
  <script>
    (function() {{
      var t = new URLSearchParams(location.search).get('t') || '';
      var box = document.getElementById('squad');
      fetch('/api/planteles')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var html = d[t];
          if (html) {{ box.innerHTML = html; document.title = t + ' · Plantel · Mundial 2026'; }}
          else {{ box.innerHTML = '<p class="loading">Plantel no disponible todavía. Probá en unos minutos.</p>'; }}
        }})
        .catch(function() {{ box.innerHTML = '<p class="loading">No se pudo cargar el plantel.</p>'; }});
    }})();
  </script>
</body>
</html>"""
