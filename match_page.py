"""
Página de detalle de partido ("Ver Partido"): alineaciones, estadísticas del
partido, rendimiento por jugador y posiciones del grupo. Mismo patrón shell+JSON
que el plantel. Identidad visual de marca.
"""

from datetime import datetime

from html_renderer import T, TEL, BG, WHT, BDR, BDR2, TXT, MUT, DIM, GRY
from countries import traducir, nombre_es

_POS_ORDER = {"G": 0, "D": 1, "M": 2, "F": 3}
_STAT_ROWS = [
    ("Ball Possession", "Posesión"),
    ("Total Shots",     "Tiros"),
    ("Shots on Goal",   "Tiros al arco"),
    ("Corner Kicks",    "Córners"),
    ("Fouls",           "Faltas"),
    ("Offsides",        "Offsides"),
    ("Yellow Cards",    "Amarillas"),
    ("Passes %",        "Precisión pases"),
]


def _num(v):
    if v is None:
        return 0.0
    try:
        return float(str(v).replace("%", "").strip() or 0)
    except Exception:
        return 0.0


def _split_home_away(entries, home_name, away_name):
    h, a = nombre_es(home_name), nombre_es(away_name)
    he = ae = None
    for e in entries:
        en = nombre_es(e.get("team", ""))
        if en == h and he is None:
            he = e
        elif en == a and ae is None:
            ae = e
    return he, ae


def _mt_lineup_team(entry, side_label):
    if not entry:
        return ""
    xi_sorted = sorted(entry.get("startXI", []), key=lambda p: _POS_ORDER.get(p.get("pos", ""), 9))

    def _pl(p):
        num = p.get("number")
        num_s = str(num) if num else "—"
        return (f'<div class="mt-pl"><span class="mt-pl-n">{num_s}</span>'
                f'<span class="mt-pl-name">{p.get("name", "")}</span>'
                f'<span class="mt-pl-pos">{p.get("pos", "")}</span></div>')

    xi_html = "".join(_pl(p) for p in xi_sorted)
    subs_html = "".join(_pl(p) for p in entry.get("subs", []))
    coach = entry.get("coach", "")
    coach_html = f'<div class="mt-coach">DT: {coach}</div>' if coach else ""
    return (
        f'<div class="mt-ln-team">'
        f'<div class="mt-ln-h">{side_label} <span class="mt-form">{entry.get("formation", "")}</span></div>'
        f'<div class="mt-ln-list">{xi_html}</div>'
        f'<div class="mt-subt">Suplentes</div>'
        f'<div class="mt-ln-list mt-subs">{subs_html}</div>'
        f'{coach_html}</div>'
    )


def _mt_lineups(detail, home_name, away_name):
    lineups = detail.get("lineups", [])
    if not lineups:
        return ""
    he, ae = _split_home_away(lineups, home_name, away_name)
    if not he and not ae:
        return ""
    return (
        f'<div class="mt-sec"><h3 class="mt-st">Alineaciones</h3>'
        f'<div class="mt-ln-grid">'
        f'{_mt_lineup_team(he, nombre_es(home_name))}'
        f'{_mt_lineup_team(ae, nombre_es(away_name))}'
        f'</div></div>'
    )


def _mt_statistics(detail, home_name, away_name):
    stats = detail.get("statistics", [])
    if not stats:
        return ""
    he, ae = _split_home_away(stats, home_name, away_name)
    if not he or not ae:
        return ""
    hs, as_ = he.get("stats", {}), ae.get("stats", {})
    rows = ""
    for key, label in _STAT_ROWS:
        if key not in hs and key not in as_:
            continue
        hv, av = hs.get(key), as_.get(key)
        total = _num(hv) + _num(av)
        hp = (_num(hv) / total * 100) if total else 50
        hd = hv if hv is not None else "0"
        ad = av if av is not None else "0"
        rows += (
            f'<div class="mt-strow">'
            f'<div class="mt-stvals"><span>{hd}</span><span class="mt-stlbl">{label}</span><span>{ad}</span></div>'
            f'<div class="mt-bar"><div class="mt-bar-h" style="width:{hp:.0f}%"></div>'
            f'<div class="mt-bar-a" style="width:{100 - hp:.0f}%"></div></div></div>'
        )
    if not rows:
        return ""
    return f'<div class="mt-sec"><h3 class="mt-st">Estadísticas del partido</h3>{rows}</div>'


def _mt_players_team(entry, side_label):
    if not entry:
        return ""
    players = [p for p in entry.get("players", []) if (p.get("minutes") or 0) > 0]
    players.sort(key=lambda p: _num(p.get("rating")), reverse=True)
    rows = ""
    for p in players:
        rating = p.get("rating")
        rating_s = f"{float(rating):.1f}" if rating else "—"
        ga = []
        if p.get("goals"):
            ga.append(f'{p["goals"]}&#9917;')
        if p.get("assists"):
            ga.append(f'{p["assists"]}<span style="color:{TEL}">A</span>')
        cap = ' <span class="mt-cap">C</span>' if p.get("captain") else ""
        rows += (
            f'<tr><td class="mt-p-name">{p.get("name", "")}{cap}</td>'
            f'<td>{p.get("minutes")}\'</td><td>{" ".join(ga)}</td>'
            f'<td><span class="mt-rating">{rating_s}</span></td></tr>'
        )
    return (
        f'<div class="mt-pl-team"><div class="mt-ln-h">{side_label}</div>'
        f'<table class="mt-ptable"><thead><tr><th>Jugador</th><th>Min</th><th>G/A</th><th>Pts</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def _mt_players(detail, home_name, away_name):
    players = detail.get("players", [])
    if not players:
        return ""
    he, ae = _split_home_away(players, home_name, away_name)
    if not he and not ae:
        return ""
    return (
        f'<div class="mt-sec"><h3 class="mt-st">Rendimiento por jugador</h3>'
        f'<div class="mt-pl-grid">'
        f'{_mt_players_team(he, nombre_es(home_name))}'
        f'{_mt_players_team(ae, nombre_es(away_name))}'
        f'</div></div>'
    )


def _mt_standings(group_data, label):
    if not group_data:
        return ""
    teams = group_data.get("teams", [])
    stats = group_data.get("stats", {})
    rows = ""
    for pos, team in enumerate(teams, 1):
        s = stats.get(team)
        if not s:
            continue
        cls = "mt-cls" if pos <= 2 else ""
        rows += (
            f'<tr class="{cls}"><td>{pos}</td><td class="mt-p-name">{traducir(team)}</td>'
            f'<td>{s.played}</td><td>{s.goal_diff:+d}</td><td><span class="mt-rating">{s.points}</span></td></tr>'
        )
    if not rows:
        return ""
    return (
        f'<div class="mt-sec"><h3 class="mt-st">Posiciones — Grupo {label}</h3>'
        f'<table class="mt-ptable mt-stand"><thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>DG</th><th>Pts</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def _mt_date(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return ""


def render_match_fragment(match, detail, group_data, stage_label):
    """Fragmento del detalle de partido. Va en partidos.json."""
    home, away = match.get("home", ""), match.get("away", "")
    hg, ag = match.get("home_goals"), match.get("away_goals")
    status = match.get("status", "")
    played = status in ("FINISHED", "IN_PLAY", "PAUSED")
    if played and hg is not None:
        centro = f'<span class="mt-sc">{hg}</span><span class="mt-sep">-</span><span class="mt-sc">{ag}</span>'
    else:
        centro = '<span class="mt-vs">vs</span>'
    if status == "FINISHED":
        badge = '<span class="mt-badge mt-fin">Finalizado</span>'
    elif status == "PAUSED":
        badge = '<span class="mt-badge mt-live"><span class="mt-dot"></span>Entretiempo</span>'
    elif status in ("IN_PLAY",):
        el = match.get("elapsed")
        min_html = f"{el}'" if el is not None else ""
        badge = (f'<span class="mt-badge mt-live"><span class="mt-dot"></span>EN VIVO '
                 f'<span class="mt-min">{min_html}</span></span>')
    else:
        badge = ''

    # Estadio
    from countries import capacidad_fmt
    vbits = [b for b in [match.get("venue_name", ""), match.get("venue_city", ""),
                         (capacidad_fmt(match.get("venue_name", "")) or "")] if b]
    venue_html = f'<div class="mt-venue">{" · ".join(vbits)}</div>' if vbits else ""

    header = (
        f'<div class="mt-meta">{stage_label} · {_mt_date(match.get("utc_date", ""))}</div>'
        f'<div class="mt-scoreline">'
        f'<div class="mt-team mt-th">{traducir(home)}</div>'
        f'<div class="mt-center" id="mt-center">{centro}</div>'
        f'<div class="mt-team mt-ta">{traducir(away)}</div></div>'
        f'<div class="mt-badge-wrap" id="mt-badge">{badge}</div>'
    )
    ref = match.get("referee", "")
    ref_html = f'<div class="mt-ref">Árbitro: {ref}</div>' if ref else ""
    header += venue_html

    detail = detail or {}
    detail_body = (
        _mt_lineups(detail, home, away)
        + _mt_statistics(detail, home, away)
        + _mt_players(detail, home, away)
    )
    if not detail_body:
        if status == "TIMED" or not status:
            msg = "Alineaciones y estadísticas todavía no disponibles. Aparecen cuando arranca el partido."
        else:
            msg = "Detalle del partido todavía no disponible. Actualizá en unos minutos."
        detail_body = f'<div class="mt-sec"><p class="mt-nodata">{msg}</p></div>'

    standings_html = _mt_standings(group_data, (match.get("group") or "").replace("GROUP_", ""))
    return f'<div class="mt-head">{header}{ref_html}</div>{detail_body}{standings_html}'


def render_partido_shell():
    """Página shell de partido. Lee ?id= e inyecta el fragmento de partidos.json."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Partido · Mundial 2026</title>
  <link rel="icon" href="/favicon.ico">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:24px 18px 48px}}
    .wrap{{max-width:680px;margin:0 auto}}
    .topbar{{display:flex;align-items:center;gap:12px;margin-bottom:22px}}
    .back{{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:600;color:{T};text-decoration:none;border:1px solid {BDR};border-radius:8px;padding:6px 12px;background:{WHT}}}
    .back:hover{{background:{GRY}}}
    .brand{{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{DIM}}}
    .mt-head{{background:{WHT};border:1px solid {BDR};border-radius:12px;padding:18px 16px;text-align:center;margin-bottom:22px}}
    .mt-meta{{font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM};margin-bottom:12px}}
    .mt-scoreline{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px}}
    .mt-team{{font-size:1rem;font-weight:700;display:flex;align-items:center;gap:8px}}
    .mt-th{{justify-content:flex-end;flex-direction:row-reverse}}
    .mt-ta{{justify-content:flex-start}}
    .mt-team img{{width:26px;height:20px;border-radius:2px;margin-right:0}}
    .mt-center{{display:flex;align-items:center;gap:7px}}
    .mt-sc{{font-size:1.7rem;font-weight:800;color:{TXT}}}
    .mt-sep{{color:{DIM};font-weight:700}}
    .mt-vs{{font-size:.85rem;color:{DIM};font-weight:700}}
    .mt-badge-wrap{{margin-top:10px}}
    .mt-badge{{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:4px 11px;border-radius:999px;display:inline-flex;align-items:center;gap:5px}}
    .mt-fin{{background:{GRY};color:{MUT}}}
    .mt-live{{background:rgba(194,65,12,.12);color:{T}}}
    .mt-dot{{width:6px;height:6px;border-radius:50%;background:{T};animation:mtblink 1.4s ease-in-out infinite}}
    @keyframes mtblink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
    .mt-venue{{font-size:.72rem;color:{MUT};margin-top:9px}}
    .mt-ref{{font-size:.72rem;color:{MUT};margin-top:10px}}
    .mt-sec{{margin-bottom:26px}}
    .mt-st{{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{T};margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid {BDR}}}
    .mt-ln-grid,.mt-pl-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
    .mt-ln-team,.mt-pl-team{{background:{WHT};border:1px solid {BDR};border-radius:10px;padding:12px}}
    .mt-ln-h{{font-size:.82rem;font-weight:700;margin-bottom:9px;display:flex;align-items:center;justify-content:space-between;gap:6px}}
    .mt-form{{font-size:.64rem;font-weight:700;color:{T};background:{GRY};border-radius:8px;padding:2px 7px}}
    .mt-ln-list{{display:flex;flex-direction:column;gap:3px}}
    .mt-pl{{display:flex;align-items:center;gap:8px;font-size:.78rem;padding:2px 0}}
    .mt-pl-n{{color:{T};font-weight:700;min-width:18px;text-align:center;font-size:.72rem}}
    .mt-pl-name{{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .mt-pl-pos{{font-size:.6rem;color:{DIM};font-weight:700}}
    .mt-subt{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM};margin:10px 0 5px}}
    .mt-subs{{opacity:.78}}
    .mt-coach{{font-size:.68rem;color:{MUT};margin-top:9px;padding-top:7px;border-top:1px solid {GRY}}}
    .mt-strow{{margin-bottom:11px}}
    .mt-stvals{{display:flex;justify-content:space-between;align-items:center;font-size:.82rem;font-weight:700;margin-bottom:3px}}
    .mt-stlbl{{font-size:.66rem;font-weight:600;color:{MUT};text-transform:uppercase;letter-spacing:.04em}}
    .mt-bar{{display:flex;height:6px;border-radius:3px;overflow:hidden;background:{GRY}}}
    .mt-bar-h{{background:{T}}}
    .mt-bar-a{{background:{TEL}}}
    .mt-ptable{{width:100%;border-collapse:collapse;font-size:.76rem}}
    .mt-ptable th{{font-size:.6rem;text-transform:uppercase;letter-spacing:.05em;color:{DIM};text-align:center;padding:4px 3px;border-bottom:1px solid {BDR}}}
    .mt-ptable td{{text-align:center;padding:5px 3px;border-bottom:1px solid {GRY}}}
    .mt-ptable .mt-p-name{{text-align:left;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:130px}}
    .mt-rating{{background:{T};color:{WHT};border-radius:6px;padding:1px 6px;font-weight:700;font-size:.72rem}}
    .mt-cap{{font-size:.55rem;background:{MUT};color:{WHT};border-radius:3px;padding:0 3px;font-weight:700;vertical-align:middle}}
    .mt-stand .mt-cls{{background:rgba(13,148,136,.08)}}
    .mt-nodata{{text-align:center;color:{MUT};font-size:.8rem;background:{WHT};border:1px dashed {BDR2};border-radius:10px;padding:20px 16px}}
    .loading{{text-align:center;color:{MUT};font-size:.85rem;margin-top:40px}}
    @media(max-width:560px){{
      .mt-ln-grid,.mt-pl-grid{{grid-template-columns:1fr}}
      .mt-team{{font-size:.85rem}}
      .mt-sc{{font-size:1.4rem}}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <a class="back" href="/">&#8592; Volver al inicio</a>
      <span class="brand">Mundial 2026</span>
    </div>
    <div id="match"><p class="loading">Cargando partido…</p></div>
  </div>
  <script>
    var MID = new URLSearchParams(location.search).get('id') || '';

    function loadMatch() {{
      var box = document.getElementById('match');
      fetch('/api/partidos')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var html = d[MID];
          if (html) {{ box.innerHTML = html; pollMatchLive(); }}
          else {{ box.innerHTML = '<p class="loading">Detalle no disponible todavía. Probá cuando arranque el partido.</p>'; }}
        }})
        .catch(function() {{ box.innerHTML = '<p class="loading">No se pudo cargar el partido.</p>'; }});
    }}

    // Actualiza marcador, minuto y badge EN VIVO sin recargar (cada 8s)
    function pollMatchLive() {{
      fetch('/api/live')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var m = (d.matches || []).filter(function(x) {{ return String(x.id) === String(MID); }})[0];
          if (!m) return;
          var center = document.getElementById('mt-center');
          if (center && m.h != null) {{
            center.innerHTML = '<span class="mt-sc">' + m.h + '</span><span class="mt-sep">-</span><span class="mt-sc">' + m.a + '</span>';
          }}
          var badge = document.getElementById('mt-badge');
          if (badge) {{
            badge.innerHTML = (m.status === 'HT')
              ? '<span class="mt-badge mt-live"><span class="mt-dot"></span>Entretiempo</span>'
              : '<span class="mt-badge mt-live"><span class="mt-dot"></span>EN VIVO <span class="mt-min">' + (m.elapsed != null ? m.elapsed + "'" : '') + '</span></span>';
          }}
        }})
        .catch(function() {{}});
    }}

    loadMatch();
    setInterval(pollMatchLive, 8000);
  </script>
</body>
</html>"""
