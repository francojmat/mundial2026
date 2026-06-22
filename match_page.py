"""
Página de detalle de partido ("Ver Partido"): alineaciones, estadísticas del
partido, rendimiento por jugador y posiciones del grupo. Mismo patrón shell+JSON
que el plantel. Identidad visual de marca.
"""

from datetime import datetime

from html_renderer import T, TEL, BG, WHT, BDR, BDR2, TXT, MUT, DIM, GRY, WRN
from countries import traducir, nombre_es, bandera_img, VENUE_PHOTO
from motm import motm_for

_POS_ORDER = {"G": 0, "D": 1, "M": 2, "F": 3}
_POS_ES = {"G": "Arquero", "D": "Defensor", "M": "Mediocampista", "F": "Delantero"}
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
        pos_raw = p.get("pos") or ""
        pos_es = _POS_ES.get(pos_raw, pos_raw)
        return (f'<div class="mt-pl"><span class="mt-pl-n">{num_s}</span>'
                f'<span class="mt-pl-name">{p.get("name", "")}</span>'
                f'<span class="mt-pl-pos">{pos_es}</span></div>')

    xi_html = "".join(_pl(p) for p in xi_sorted)
    subs_html = "".join(_pl(p) for p in entry.get("subs", []))
    coach = entry.get("coach", "")
    coach_html = f'<div class="mt-coach">DT: {coach}</div>' if coach else ""
    form = entry.get("formation") or ""
    form_html = f' <span class="mt-form">{form}</span>' if form else ""
    return (
        f'<div class="mt-ln-team">'
        f'<div class="mt-ln-h">{side_label}{form_html}</div>'
        f'<div class="mt-ln-list">{xi_html}</div>'
        f'<div class="mt-subt">Suplentes</div>'
        f'<div class="mt-ln-list mt-subs">{subs_html}</div>'
        f'{coach_html}</div>'
    )


def _formation_lines(entry):
    """Reparte el XI en líneas: [arquero], [defensas], [medios], ... según la formación."""
    xi = entry.get("startXI", [])
    gk = [p for p in xi if p.get("pos") == "G"]
    rest = [p for p in xi if p.get("pos") != "G"]
    try:
        nums = [int(x) for x in (entry.get("formation") or "").split("-")]
    except Exception:
        nums = []
    lines = []
    if gk:
        lines.append(gk[:1])
    if nums:
        i = 0
        for n in nums:
            lines.append(rest[i:i + n]); i += n
        if i < len(rest):
            lines.append(rest[i:])
    else:
        lines.append(rest)
    return [ln for ln in lines if ln]


def _pitch_side(entry, home=True):
    """Ubica los 11 de un equipo en su mitad del campo (% top/left)."""
    lines = _formation_lines(entry)
    L = len(lines)
    if L < 2:
        return ""
    cls = "mt-pp mt-pp-h" if home else "mt-pp mt-pp-a"
    out = ""
    for i, line in enumerate(lines):
        # cada mitad ocupa su zona dejando una franja libre en el centro (sin solaparse)
        y = (95 - i * (38 / (L - 1))) if home else (5 + i * (38 / (L - 1)))
        n = len(line)
        for j, p in enumerate(line):
            x = 50 if n == 1 else 15 + j * (70 / (n - 1))
            num = p.get("number") or ""
            nm = p.get("name", "")
            short = nm.split()[-1] if nm else ""
            out += (f'<div class="{cls}" style="left:{x:.1f}%;top:{y:.1f}%">'
                    f'<span class="mt-pp-n">{num}</span>'
                    f'<span class="mt-pp-name">{short}</span></div>')
    return out


def _mt_pitch(he, ae):
    """8.3 — campo con las dos alineaciones dibujadas."""
    home_html = _pitch_side(he, True) if he else ""
    away_html = _pitch_side(ae, False) if ae else ""
    if not (home_html or away_html):
        return ""
    return f'<div class="mt-pitch">{home_html}{away_html}</div>'


def _mt_lineups(detail, home_name, away_name):
    lineups = detail.get("lineups", [])
    if not lineups:
        return ""
    he, ae = _split_home_away(lineups, home_name, away_name)
    if not he and not ae:
        return ""
    return (
        f'<div class="mt-sec"><h3 class="mt-st">Alineaciones</h3>'
        f'{_mt_pitch(he, ae)}'
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


def _mt_group_matches(fixtures, current_mid, label):
    """Todos los partidos del grupo (jugados + próximos). El actual queda resaltado."""
    if not fixtures:
        return ""
    rows = ""
    for m in sorted(fixtures, key=lambda x: x.get("utc_date") or ""):
        mid = str(m.get("match_id") or "")
        h, a = m.get("home", ""), m.get("away", "")
        st = m.get("status", "")
        played = st in ("FINISHED", "IN_PLAY", "PAUSED")
        live = st in ("IN_PLAY", "PAUSED")
        hg, ag = m.get("home_goals"), m.get("away_goals")
        if played and hg is not None and ag is not None:
            center = f'<span class="mt-gm-sc">{hg} - {ag}</span>'
        else:
            center = f'<span class="mt-gm-dt" data-utc="{m.get("utc_date","")}">—</span>'
        live_b = '<span class="mt-gm-live">EN VIVO</span>' if live else ""
        inner = (f'<span class="mt-gm-h">{nombre_es(h)}{bandera_img(h, "mt-gm-fl", 18, 13)}</span>'
                 f'{center}'
                 f'<span class="mt-gm-a">{bandera_img(a, "mt-gm-fl", 18, 13)}{nombre_es(a)}</span>'
                 f'{live_b}')
        if mid == current_mid:
            rows += f'<div class="mt-gm-row mt-gm-cur">{inner}</div>'
        else:
            rows += f'<a class="mt-gm-row" href="/partido.html?id={mid}">{inner}</a>'
    return (f'<div class="mt-sec"><h3 class="mt-st">Partidos del grupo {label}</h3>'
            f'<div class="mt-gm">{rows}</div></div>')


def _mt_standings(group_data, label, thirds_advancing=None):
    if not group_data:
        return ""
    thirds_advancing = thirds_advancing or set()
    teams = group_data.get("teams", [])
    stats = group_data.get("stats", {})
    rows = ""
    for pos, team in enumerate(teams, 1):
        s = stats.get(team)
        if not s:
            continue
        if pos <= 2:
            cls = "mt-cls"
        elif pos == 3 and team in thirds_advancing:
            cls = "mt-third"
        else:
            cls = ""
        import urllib.parse
        tq = urllib.parse.quote(team)
        name_html = f'<a class="mt-tlink" href="/seleccion.html?t={tq}">{traducir(team)}</a>'
        rows += (
            f'<tr class="{cls}"><td>{pos}</td><td class="mt-p-name">{name_html}</td>'
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


def _tl_minkey(m):
    m = str(m).replace("'", "").strip()
    if "+" in m:
        a, b = (m.split("+") + ["0"])[:2]
        return (int(a) if a.isdigit() else 999) + (int(b) if b.isdigit() else 0) * 0.01
    return int(m) if m.isdigit() else 999


def _mt_timeline(match):
    """8.4 — cronología del partido: goles, tarjetas y cambios ordenados por minuto."""
    evs = ([(g.get("minute", ""), "goal", g) for g in (match.get("goals_detail") or [])]
           + [(b.get("minute", ""), "card", b) for b in (match.get("bookings") or [])]
           + [(s.get("minute", ""), "sub", s) for s in (match.get("substitutions") or [])])
    if not evs:
        return ""
    evs.sort(key=lambda e: _tl_minkey(e[0]))
    rows = ""
    for minute, kind, ev in evs:
        team = nombre_es(ev.get("team", "")) if ev.get("team") else ""
        team_s = f'<span class="tl-s"> · {team}</span>' if team else ""
        if kind == "goal":
            t = ev.get("type", "")
            sfx = " (PP)" if t == "PENALTY" else " (PC)" if t == "OWN" else ""
            asn = ev.get("assist", "")
            ass = f'<span class="tl-s"> · asist: {asn}</span>' if asn else ""
            icon = '<span class="tl-dot"></span>'
            txt = f'<b>{ev.get("scorer","")}</b>{sfx}{team_s}{ass}'
        elif kind == "card":
            icon = '<span class="tl-rc"></span>' if ev.get("card") == "RED" else '<span class="tl-yc"></span>'
            txt = f'{ev.get("player","")}{team_s}'
        else:
            icon = '<span class="tl-sw">&#x21C4;</span>'
            txt = f'{ev.get("player_in","")} &#8594; {ev.get("player_out","")}{team_s}'
        rows += (f'<div class="tl-row"><span class="tl-min">{minute}\'</span>'
                 f'{icon}<span class="tl-txt">{txt}</span></div>')
    return f'<div class="mt-sec"><h3 class="mt-st">Cronología</h3><div class="mt-timeline">{rows}</div></div>'


def _mt_h2h(match):
    """Bloque de historial entre los dos equipos (para partidos que aún no arrancaron).
    Si no hay antecedentes, muestra el bloque 'primer enfrentamiento'."""
    home = nombre_es(match.get("home", ""))
    away = nombre_es(match.get("away", ""))
    h2h = match.get("h2h") or []
    if not h2h:
        return (
            '<div class="mt-sec"><div class="mt-h2h-box mt-h2h-first">'
            '<div class="mt-h2h-ico">&#9876;</div>'
            '<div class="mt-h2h-first-t">Primer enfrentamiento</div>'
            f'<div class="mt-h2h-first-s">{home} y {away} nunca se enfrentaron. '
            'Será su primer partido en la historia.</div>'
            '</div></div>')
    rows = ""
    for x in h2h[:5]:
        d = x.get("date", "")
        fecha = f'{d[8:10]}/{d[5:7]}/{d[2:4]}' if len(d) >= 10 else d
        comp, rnd = x.get("comp", ""), x.get("round", "")
        meta = f'{comp} · {rnd}' if (comp and rnd) else (comp or rnd)
        rows += (f'<div class="mt-h2h-row">'
                 f'<span class="mt-h2h-d">{fecha}</span>'
                 f'<span class="mt-h2h-c">{meta}</span>'
                 f'<span class="mt-h2h-r">{nombre_es(x.get("home",""))} '
                 f'<b>{x.get("gh")}-{x.get("ga")}</b> {nombre_es(x.get("away",""))}</span></div>')
    return (f'<div class="mt-sec"><div class="mt-h2h-box">'
            f'<div class="mt-h2h-hd"><span class="mt-h2h-badge">Historial reciente</span></div>'
            f'<div class="mt-h2h">{rows}</div></div></div>')


def _mt_motm(match):
    """5.4 — Figura del partido (Man of the Match oficial de FIFA, curado a mano)."""
    p = motm_for(match.get("home", ""), match.get("away", ""))
    if not p:
        return ""
    return (f'<div class="mt-sec mt-motm">'
            f'<span class="motm-ico">★</span>'
            f'<div class="motm-txt"><div class="motm-lbl">Figura del partido</div>'
            f'<div class="motm-name">{p}</div></div></div>')


def _mt_highlights(match):
    """8.6 — acceso al resumen del partido en YouTube (búsqueda; no depende de catálogo)."""
    if match.get("status") != "FINISHED":
        return ""
    import urllib.parse
    q = urllib.parse.quote(
        f'{nombre_es(match.get("home",""))} vs {nombre_es(match.get("away",""))} Mundial 2026 resumen highlights')
    url = f"https://www.youtube.com/results?search_query={q}"
    return (f'<div class="mt-sec" style="text-align:center"><a class="mt-hl" href="{url}" target="_blank" rel="noopener">'
            f'<span class="mt-hl-ico">▶</span> Ver resumen en YouTube</a></div>')


def render_match_fragment(match, detail, group_data, stage_label, thirds_advancing=None,
                          group_fixtures=None, venue_img=None):
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
    w = match.get("weather") or {}
    if w.get("temp") is not None:
        vbits.append(f'{w["temp"]}° {w.get("desc", "")}'.strip())
    venue_html = f'<div class="mt-venue">{" · ".join(vbits)}</div>' if vbits else ""
    # Foto del estadio (la misma que en la sección Estadios), debajo del estadio
    vphoto = venue_img or VENUE_PHOTO.get(match.get("venue_name", ""))
    venue_img = (f'<img class="mt-venue-img" src="{vphoto}" loading="lazy" alt="" '
                 f'onerror="this.style.display=\'none\'">') if vphoto else ""

    # home: nombre + bandera (bandera pegada al "vs"); away: bandera (pegada al "vs") + nombre
    home_t = f'<span class="mt-tn">{nombre_es(home)}</span>{bandera_img(home, "mt-fl", 26, 20)}'
    away_t = f'{bandera_img(away, "mt-fl", 26, 20)}<span class="mt-tn">{nombre_es(away)}</span>'
    header = (
        f'<div class="mt-meta">{stage_label} · {_mt_date(match.get("utc_date", ""))}</div>'
        f'<div class="mt-scoreline">'
        f'<div class="mt-team mt-th">{home_t}</div>'
        f'<div class="mt-center" id="mt-center">{centro}</div>'
        f'<div class="mt-team mt-ta">{away_t}</div></div>'
        f'<div class="mt-badge-wrap" id="mt-badge">{badge}</div>'
    )
    ref = match.get("referee", "")
    ref_html = f'<div class="mt-ref">Árbitro: {ref}</div>' if ref else ""
    header += venue_html

    detail = detail or {}
    detail_body = (
        _mt_motm(match)
        + _mt_lineups(detail, home, away)
        + _mt_timeline(match)
        + _mt_statistics(detail, home, away)
        + _mt_players(detail, home, away)
        + _mt_highlights(match)
    )
    if not detail_body:
        # Hasta que arranque el partido mostramos el bloque de historial (o "primer enfrentamiento")
        if status == "TIMED" or not status:
            detail_body = _mt_h2h(match)
        else:
            msg = "Detalle del partido todavía no disponible. Actualizá en unos minutos."
            detail_body = f'<div class="mt-sec"><p class="mt-nodata">{msg}</p></div>'

    grp_label = (match.get("group") or "").replace("GROUP_", "")
    standings_html = _mt_standings(group_data, grp_label, thirds_advancing)
    fixtures_html = _mt_group_matches(group_fixtures, str(match.get("match_id") or ""), grp_label)
    return (f'<div class="mt-head">{header}{ref_html}{venue_img}</div>'
            f'{detail_body}{standings_html}{fixtures_html}')


def render_partido_shell():
    """Página shell de partido. Lee ?id= e inyecta el fragmento de partidos.json."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Ver Partido · Mundial 2026</title>
  <meta name="description" content="Detalle del partido del Mundial 2026: alineaciones, cronología minuto a minuto, estadísticas, historial entre las selecciones y posiciones del grupo.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Mejor Tercero">
  <meta property="og:title" content="Ver Partido · Mundial 2026">
  <meta property="og:description" content="Alineaciones, cronología, estadísticas e historial del partido en el Mundial 2026.">
  <meta property="og:image" content="https://mejortercero.online/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://mejortercero.online/og.png">
  <meta name="theme-color" content="#c2410c">
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
    .mt-scoreline{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:9px}}
    .mt-team{{font-size:1rem;font-weight:700;display:flex;align-items:center;gap:7px}}
    .mt-th{{justify-content:flex-end}}
    .mt-ta{{justify-content:flex-start}}
    .mt-fl{{width:26px;height:20px;border-radius:2px}}
    .mt-center{{display:flex;align-items:center;gap:7px}}
    .mt-sc{{font-size:1.7rem;font-weight:800;color:{TXT}}}
    .mt-sep{{color:{DIM};font-weight:700}}
    .mt-vs{{font-size:.85rem;color:{DIM};font-weight:700}}
    .mt-badge-wrap{{margin-top:10px}}
    .mt-badge{{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:4px 11px;border-radius:999px;display:inline-flex;align-items:center;gap:5px;background:transparent;border:1.5px solid transparent}}
    .mt-fin{{color:{MUT};border-color:{BDR2}}}
    .mt-live{{color:{T};border-color:{T}}}
    .mt-dot{{width:6px;height:6px;border-radius:50%;background:{T};animation:mtblink 1.4s ease-in-out infinite}}
    @keyframes mtblink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
    .mt-venue{{font-size:.72rem;color:{MUT};margin-top:9px}}
    .mt-ref{{font-size:.72rem;color:{MUT};margin-top:10px}}
    .mt-venue-img{{width:100%;max-height:150px;object-fit:cover;border-radius:8px;margin-top:14px;display:block}}
    .mt-gm{{display:flex;flex-direction:column;gap:6px}}
    .mt-gm-row{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;padding:9px 13px;background:{WHT};border:1px solid {BDR};border-radius:9px;text-decoration:none;color:{TXT};position:relative}}
    a.mt-gm-row:hover{{border-color:{BDR2}}}
    .mt-gm-cur{{background:rgba(194,65,12,.06);border-color:{T}}}
    .mt-gm-h{{justify-self:end;text-align:right;font-size:.8rem;display:flex;align-items:center;gap:6px}}
    .mt-gm-a{{justify-self:start;text-align:left;font-size:.8rem;display:flex;align-items:center;gap:6px}}
    .mt-gm-fl{{width:18px;height:13px;border-radius:2px}}
    .mt-gm-sc{{font-size:.9rem;font-weight:700;color:{T};min-width:46px;text-align:center}}
    .mt-gm-dt{{font-size:.7rem;font-weight:600;color:{MUT};min-width:72px;text-align:center}}
    .mt-gm-live{{position:absolute;top:-7px;left:50%;transform:translateX(-50%);font-size:.5rem;font-weight:700;letter-spacing:.05em;background:{T};color:#fff;padding:1px 7px;border-radius:6px}}
    .mt-sec{{margin-bottom:26px}}
    .mt-st{{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{T};margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid {BDR}}}
    .mt-ln-grid,.mt-pl-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
    .mt-ln-team,.mt-pl-team{{background:{WHT};border:1px solid {BDR};border-radius:10px;padding:12px}}
    .mt-ln-h{{font-size:.82rem;font-weight:700;margin-bottom:9px;display:flex;align-items:center;justify-content:space-between;gap:6px}}
    .mt-form{{font-size:.64rem;font-weight:700;color:{T};background:transparent;border:1.5px solid {T};border-radius:8px;padding:2px 7px}}
    .mt-pitch{{position:relative;width:100%;max-width:360px;margin:0 auto 16px;aspect-ratio:3/4;background:repeating-linear-gradient(0deg,#3c7d3c 0,#3c7d3c 12.5%,#367536 12.5%,#367536 25%);border:2px solid rgba(255,255,255,.45);border-radius:8px;overflow:hidden}}
    .mt-pitch::before{{content:'';position:absolute;top:50%;left:0;right:0;height:2px;background:rgba(255,255,255,.4)}}
    .mt-pitch::after{{content:'';position:absolute;top:50%;left:50%;width:72px;height:72px;border:2px solid rgba(255,255,255,.4);border-radius:50%;transform:translate(-50%,-50%)}}
    .mt-pp{{position:absolute;transform:translate(-50%,-50%);width:46px;text-align:center;z-index:2}}
    .mt-pp-n{{display:flex;align-items:center;justify-content:center;width:23px;height:23px;border-radius:50%;font-size:.6rem;font-weight:700;margin:0 auto;color:#fff;border:1.5px solid rgba(255,255,255,.75)}}
    .mt-pp-h .mt-pp-n{{background:{T}}}
    .mt-pp-a .mt-pp-n{{background:{TEL}}}
    .mt-pp-name{{display:block;font-size:.5rem;color:#fff;font-weight:700;margin-top:1px;text-shadow:0 1px 2px rgba(0,0,0,.7);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .mt-timeline{{display:flex;flex-direction:column}}
    .tl-row{{display:flex;align-items:flex-start;gap:9px;padding:7px 2px;border-bottom:1px solid {GRY};font-size:.82rem}}
    .tl-row:last-child{{border-bottom:none}}
    .tl-min{{color:{DIM};font-size:.7rem;font-weight:700;min-width:30px;flex-shrink:0;padding-top:2px}}
    .tl-dot{{width:7px;height:7px;border-radius:50%;background:{T};flex-shrink:0;margin-top:5px}}
    .tl-yc{{width:7px;height:10px;background:{WRN};flex-shrink:0;margin-top:3px;border-radius:1px}}
    .tl-rc{{width:7px;height:10px;background:#dc2626;flex-shrink:0;margin-top:3px;border-radius:1px}}
    .tl-sw{{font-size:.8rem;color:{TEL};flex-shrink:0;line-height:1.3}}
    .tl-txt{{flex:1;line-height:1.5;color:{TXT}}}
    .tl-s{{color:{MUT};font-size:.72rem}}
    .mt-h2h-box{{background:{WHT};border:1px solid {BDR};border-radius:12px;padding:6px 16px 10px}}
    .mt-h2h-hd{{text-align:center;margin:10px 0 6px}}
    .mt-h2h-badge{{display:inline-block;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{T};border:1px solid {T};border-radius:999px;padding:4px 13px;background:rgba(194,65,12,.05)}}
    .mt-h2h{{display:flex;flex-direction:column}}
    .mt-h2h-row{{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:6px 12px;padding:8px 2px;border-bottom:1px solid {GRY};font-size:.78rem}}
    .mt-h2h-row:last-child{{border-bottom:none}}
    .mt-h2h-d{{color:{DIM};font-size:.7rem;font-weight:700;white-space:nowrap}}
    .mt-h2h-c{{color:{MUT};font-size:.68rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .mt-h2h-r{{text-align:right;white-space:nowrap;color:{TXT}}}
    .mt-h2h-first{{text-align:center;padding:24px 18px}}
    .mt-h2h-ico{{font-size:1.5rem;color:{T};margin-bottom:8px;opacity:.85}}
    .mt-h2h-first-t{{font-size:.95rem;font-weight:700;color:{T};margin-bottom:5px}}
    .mt-h2h-first-s{{font-size:.8rem;color:{MUT};line-height:1.5;max-width:340px;margin:0 auto}}
    .mt-motm{{display:flex;align-items:center;gap:13px;background:linear-gradient(135deg,#fff7f3,#fff);border:1.5px solid {T}}}
    .motm-ico{{color:{T};font-size:1.6rem;line-height:1;flex-shrink:0}}
    .motm-lbl{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:{DIM};margin-bottom:1px}}
    .motm-name{{font-weight:700;color:{TXT};font-size:1.02rem}}
    .mt-hl{{display:inline-flex;align-items:center;gap:8px;font-size:.82rem;font-weight:700;color:{T};border:1.5px solid {T};border-radius:8px;padding:9px 16px;text-decoration:none;background:transparent}}
    .mt-hl:hover{{background:rgba(194,65,12,.08)}}
    .mt-hl-ico{{font-size:.65rem}}
    .mt-ln-list{{display:flex;flex-direction:column;gap:3px}}
    .mt-pl{{display:flex;align-items:center;gap:8px;font-size:.78rem;padding:2px 0}}
    .mt-pl-n{{color:{T};font-weight:700;min-width:18px;text-align:center;font-size:.72rem}}
    .mt-pl-name{{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .mt-pl-pos{{font-size:.58rem;color:{DIM};font-weight:700;white-space:nowrap;text-transform:uppercase;letter-spacing:.02em;flex-shrink:0}}
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
    .mt-tlink{{color:inherit;text-decoration:none}}
    .mt-tlink:hover{{color:{T};text-decoration:underline}}
    .mt-rating{{background:{T};color:{WHT};border-radius:6px;padding:1px 6px;font-weight:700;font-size:.72rem}}
    .mt-cap{{font-size:.55rem;background:{MUT};color:{WHT};border-radius:3px;padding:0 3px;font-weight:700;vertical-align:middle}}
    .mt-stand .mt-cls{{background:rgba(13,148,136,.08)}}
    .mt-stand .mt-third{{background:rgba(194,65,12,.08)}}
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
      <a class="back" id="mt-back" href="/">&#8592; Volver al inicio</a>
      <a class="back" id="mt-home" href="/" style="display:none">Inicio</a>
      <span class="brand">Mundial 2026</span>
    </div>
    <div id="match"><p class="loading">Cargando partido…</p></div>
  </div>
  <script>
    var _q = new URLSearchParams(location.search);
    var MID = _q.get('id') || '';
    // Si venís del perfil de una selección, el "Volver" te devuelve a esa selección
    (function() {{
      var from = _q.get('t'), fromName = _q.get('tn') || from;
      if (from) {{
        var b = document.getElementById('mt-back');
        b.href = '/seleccion.html?t=' + encodeURIComponent(from);
        b.innerHTML = '&#8592; Volver a ' + fromName;
        document.getElementById('mt-home').style.display = '';
      }}
    }})();

    // Formatea los horarios de los partidos próximos del grupo a la zona del usuario
    function fmtMatchTimes() {{
      document.querySelectorAll('.mt-gm-dt[data-utc]').forEach(function(e) {{
        var d = new Date(e.getAttribute('data-utc'));
        if (isNaN(d)) return;
        e.textContent = d.toLocaleDateString('es', {{day:'2-digit', month:'2-digit'}})
          + ' ' + d.toLocaleTimeString('es', {{hour:'2-digit', minute:'2-digit'}});
      }});
    }}

    function loadMatch() {{
      var box = document.getElementById('match');
      fetch('/api/partidos')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var html = d[MID];
          if (html) {{ box.innerHTML = html; fmtMatchTimes(); pollMatchLive(); }}
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
