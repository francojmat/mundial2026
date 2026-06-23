"""
Render de páginas internas (plantel, y a futuro detalle de partido) con la
identidad visual de marca. Patrón: una página "shell" estática (header + Volver +
contenedor + JS) que inyecta un fragmento pre-renderizado desde un JSON.
"""

from html_renderer import T, TEL, BG, WHT, BDR, BDR2, TXT, MUT, DIM, GRY, CRUCES_CSS
from countries import traducir, nombre_es, pais_liga_es
from seleccion_data import ficha_seleccion

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


def _pl_last(name: str) -> str:
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", name.lower()) if unicodedata.category(c) != "Mn")
    parts = s.replace(".", "").split()
    return parts[-1] if parts else ""


def compute_player_stats(match_details: dict) -> dict:
    """7.2 — stats del torneo por jugador, keyeadas por ID de jugador (único).
    Antes se keyeaba por (equipo, apellido) y colapsaba homónimos (los 3 Martínez
    de Argentina compartían stats). El ID evita ese merge."""
    acc = {}
    for det in (match_details or {}).values():
        for side in det.get("players", []):
            for p in side.get("players", []):
                pid = p.get("id")
                if pid is None or (p.get("minutes") or 0) <= 0:
                    continue
                a = acc.setdefault(pid, {"g": 0, "a": 0, "r": [], "pj": 0, "min": 0})
                a["g"] += p.get("goals") or 0
                a["a"] += p.get("assists") or 0
                a["pj"] += 1
                a["min"] += p.get("minutes") or 0
                try:
                    a["r"].append(float(p.get("rating")))
                except (TypeError, ValueError):
                    pass
    out = {}
    for pid, a in acc.items():
        out[pid] = {"g": a["g"], "a": a["a"], "pj": a["pj"], "min": a["min"],
                    "rating": round(sum(a["r"]) / len(a["r"]), 2) if a["r"] else None}
    return out


def _player_card(p: dict, pstats: dict = None, team: str = "") -> str:
    photo  = p.get("photo") or _FALLBACK
    num    = p.get("number")
    num_s  = str(num) if num else "—"
    name   = p.get("name", "")
    pos    = _POS_SINGULAR.get(p.get("position", ""), p.get("position", ""))
    age    = p.get("age")
    age_s  = f"{age} años" if age else "—"
    # 7.2 — números del jugador en el Mundial (si jugó), por ID de jugador
    st = (pstats or {}).get(p.get("id"))
    stats_html = ""
    if st and st.get("pj"):
        kvs = [("Partidos", st["pj"])]
        if st["g"]:
            kvs.append(("Goles", st["g"]))
        if st["a"]:
            kvs.append(("Asist.", st["a"]))
        if st.get("rating") is not None:
            kvs.append(("Valoración", st["rating"]))
        kvs.append(("Minutos", st["min"]))
        stats_html = (
            '<div class="pl-stats"><div class="pl-stats-t">En el Mundial</div>'
            + "".join(f'<div class="pl-kv"><span class="pl-k">{k}</span><span>{v}</span></div>' for k, v in kvs)
            + "</div>")
    # 7.1 — club del jugador (país del club) en gris clarito al lado del nombre
    club = p.get("club")
    club_html = ""
    if club:
        cc = pais_liga_es(p.get("club_country") or "")
        club_html = f'<span class="pl-club">{club}{f" ({cc})" if cc else ""}</span>'
    return (
        f'<div class="pl-card" onclick="this.classList.toggle(\'open\')">'
        f'<div class="pl-row">'
        f'<img class="pl-photo" src="{photo}" loading="lazy" alt="" '
        f'onerror="this.onerror=null;this.src=\'{_FALLBACK}\'">'
        f'<span class="pl-num">{num_s}</span>'
        f'<span class="pl-name">{name}{club_html}</span>'
        f'<span class="pl-chev">&#9662;</span>'
        f'</div>'
        f'<div class="pl-detail">'
        f'<div class="pl-info">'
        f'<div class="pl-kv"><span class="pl-k">Posición</span><span>{pos}</span></div>'
        f'<div class="pl-kv"><span class="pl-k">Dorsal</span><span>{num_s}</span></div>'
        f'<div class="pl-kv"><span class="pl-k">Edad</span><span>{age_s}</span></div>'
        f'</div>'
        f'{stats_html}'
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


def _ficha_block(team_name: str) -> str:
    """7.3 + 7.4 — ficha de la selección: ranking FIFA, títulos y mejor en Mundiales."""
    f = ficha_seleccion(team_name)
    if not f:
        return ""
    items = [("Ranking FIFA", f'#{f["rank"]}', "rk")]
    if f["titulos"]:
        copa = "título" if f["titulos"] == 1 else "títulos"
        items.append(("Copas del Mundo", f'&#127942; {f["titulos"]} {copa}', "rk"))
    items.append(("Mejor en Mundiales", f["mejor"], "wide"))
    cells = ""
    for k, v, cls in items:
        wide = " pl-fi-wide" if cls == "wide" else ""
        vcls = " rk" if cls == "rk" else ""
        cells += (f'<div class="pl-fi{wide}"><span class="pl-fi-k">{k}</span>'
                  f'<span class="pl-fi-v{vcls}">{v}</span></div>')
    return f'<div class="pl-ficha">{cells}</div>'


def render_squad_fragment(team_name: str, squad: dict, pstats: dict = None) -> str:
    """Fragmento HTML del plantel (título + ficha + grupos por posición + DT). Va en planteles.json."""
    players = squad.get("players", [])
    if not players:
        return ('<p style="font-size:.8rem;color:#7c6a58;text-align:center;margin-top:20px">'
                'Plantel no disponible todavía.</p>')

    title = f'<h2 class="pl-title">{traducir(team_name)}</h2>' + _ficha_block(team_name)

    groups_html = ""
    for pos_key, pos_label in _POS_GROUPS:
        ps = [p for p in players if p.get("position") == pos_key]
        if not ps:
            continue
        ps.sort(key=lambda p: (p.get("number") or 999))
        cards = "".join(_player_card(p, pstats, team_name) for p in ps)
        groups_html += (f'<div class="pl-group"><h3 class="pl-gt">{pos_label} '
                        f'<span class="pl-gc">{len(ps)}</span></h3>'
                        f'<div class="pl-list">{cards}</div></div>')

    return title + groups_html + _coach_card(squad.get("coach", {}))


def _sl_team_link(api_name: str) -> str:
    """Nombre + bandera enlazado al perfil de esa selección (9.1)."""
    import urllib.parse
    return f'<a class="sl-tlink" href="/seleccion.html?t={urllib.parse.quote(api_name)}">{traducir(api_name)}</a>'


def _rank_of(api: str) -> int:
    f = ficha_seleccion(api)
    return f["rank"] if f else 999


def _wrap_cz(inner: str) -> str:
    return (f'<div class="sl-sec cz"><h3 class="pl-gt">¿Contra quién en 16avos?</h3>'
            + inner + '</div>')


# Rellenos por equipo (claros, legibles con texto oscuro). Empate = neutro.
_CELL_BG = ["#e3effb", "#e6f4e6", "#fbf0d9", "#ece9fb", "#fbe3e6", "#def0ee"]
_DRAW_BG = "#f0efe9"


def _render_matrix(mx: dict, head: str) -> str:
    """Grilla tipo Excel: combinaciones de los partidos del grupo rival → rival.
    Cada equipo-resultado tiene su color de relleno (mismo color = mismo resultado)."""
    order = []
    for m in mx["matches"]:
        for t in (m["home"], m["away"]):
            if t not in order:
                order.append(t)
    color = {t: _CELL_BG[i % len(_CELL_BG)] for i, t in enumerate(order)}

    def cell(letter, m):
        if letter == "H":
            txt, bg = "Gana " + nombre_es(m["home"]), color[m["home"]]
        elif letter == "A":
            txt, bg = "Gana " + nombre_es(m["away"]), color[m["away"]]
        else:
            txt, bg = "Empate", _DRAW_BG
        return f'<td style="background:{bg}">{txt}</td>'

    def riv_html(o):
        rk = _rank_of(o)
        return traducir(o) + (f' <span class="cz-rk">#{rk}</span>' if rk != 999 else '')

    cols = "".join(f'<th>{nombre_es(m["home"])} <span class="cz-vs">vs</span> '
                   f'{nombre_es(m["away"])}</th>' for m in mx["matches"])
    body = ""
    all_opps = set()
    for r in mx["rows"]:
        cells = "".join(cell(c, mx["matches"][i]) for i, c in enumerate(r["combo"]))
        all_opps.update(r["opponents"])
        opps = " o ".join(riv_html(o) for o in r["opponents"])
        note = f' <span class="cz-note">· por {r["note"]}</span>' if r.get("note") else ""
        body += f'<tr>{cells}<td class="cz-riv">{opps}{note}</td></tr>'

    # mejor / peor caso entre todos los rivales posibles de la grilla
    bw = ""
    ranked = sorted(all_opps, key=_rank_of)
    if len(ranked) >= 2:
        hard, easy = ranked[0], ranked[-1]
        rh, re = _rank_of(hard), _rank_of(easy)
        if rh != 999 and re != 999 and hard != easy:
            bw = (f'<div class="cz-bw">'
                  f'<span><span class="cz-bw-k">Más difícil</span> {traducir(hard)} · #{rh}</span>'
                  f'<span><span class="cz-bw-k">Más fácil</span> {traducir(easy)} · #{re}</span></div>')

    return (f'<div class="cz-block"><div class="cz-head">{head}</div>'
            f'<div class="cz-sub">Tu rival según los partidos del Grupo {mx["opp_group"]}:</div>'
            f'<div class="cz-mwrap"><table class="cz-matrix"><thead><tr>{cols}'
            f'<th class="cz-riv-h">Tu rival</th></tr></thead><tbody>{body}</tbody></table></div>'
            f'{bw}</div>')


def _render_set_branch(b: dict, exact: bool, head: str) -> str:
    opps = sorted(b.get("opponents", []), key=_rank_of)
    if not opps:
        return ""
    chips = "".join(f'<span class="cz-opp">{traducir(o)}</span>' for o in opps)
    bw = ""
    if len(opps) >= 2:
        hard, easy = opps[0], opps[-1]
        rh, re = _rank_of(hard), _rank_of(easy)
        if rh != 999 and re != 999 and hard != easy:
            bw = (f'<div class="cz-bw">'
                  f'<span><span class="cz-bw-k">Más difícil</span> {traducir(hard)} · #{rh}</span>'
                  f'<span><span class="cz-bw-k">Más fácil</span> {traducir(easy)} · #{re}</span></div>')
    n = len(opps)
    tag = ('rival posible' if n == 1 else f'{n} rivales posibles')
    tag += '' if exact else ' · se define al cerrar los grupos'
    return (f'<div class="cz-block"><div class="cz-branch"><div class="cz-head">{head}</div>'
            f'<div class="cz-tag">{tag}</div>'
            f'<div class="cz-opps">{chips}</div>{bw}</div></div>')


def render_cruces_block(entry: dict, exact: bool) -> str:
    """Bloque '¿Contra quién?'. Se arma POR RAMA (cada posición clasificable): si esa
    rama enfrenta una posición concreta → GRILLA tipo Excel; si enfrenta un 3.º → lista."""
    if not entry:
        return ""
    branches = entry.get("branches", [])
    if not branches:
        return ""
    group = entry.get("group", "")
    locked = entry.get("locked_pos") is not None
    parts = []
    for b in branches:
        prefix = "Termina" if locked else "Si sale"
        mx = b.get("matrix")
        if mx and 1 <= len(mx.get("matches", [])) <= 2:
            head = (f'{prefix} {b["pos"]}.º del {group} → 16avos en {mx["city"]} · '
                    f'contra el {mx["opp_pos"]}.º del Grupo {mx["opp_group"]}')
            parts.append(_render_matrix(mx, head))
        elif mx and len(mx.get("matches", [])) == 0 and mx.get("rows"):
            opps = " o ".join(traducir(o) for o in mx["rows"][0].get("opponents", []))
            head = f'{prefix} {b["pos"]}.º del {group} → 16avos en {mx["city"]}'
            parts.append(f'<div class="cz-block"><div class="cz-head">{head}</div>'
                         f'<div class="cz-confirm">Rival confirmado: {opps}</div></div>')
        else:
            head = (f'{prefix} {b["pos"]}.º del {group} → 16avos en {b["city"]} · '
                    f'contra {b["opp_type"]}')
            parts.append(_render_set_branch(b, exact, head))
    parts = [p for p in parts if p]
    return _wrap_cz("".join(parts)) if parts else ""


def render_seleccion_fragment(team: str, group_label: str, rows: list, matches: list,
                              cruces: dict = None, cruces_exact: bool = False) -> str:
    """9.1 — perfil de selección: ficha + tabla de su grupo + sus partidos + acceso al plantel.
    `matches` = lista de dicts de partido completos (con goles/cambios para el detalle)."""
    import urllib.parse
    from html_renderer import _hoy_detail_html
    title = f'<h2 class="pl-title">{traducir(team)}</h2>' + _ficha_block(team)

    grp_rows = ""
    for r in rows:
        dg = f'+{r["dg"]}' if r["dg"] > 0 else str(r["dg"])
        me = " sl-me" if r["me"] else ""
        grp_rows += (f'<tr class="{me.strip()}"><td>{r["pos"]}</td>'
                     f'<td class="sl-tn">{_sl_team_link(r["team"])}</td>'
                     f'<td>{r["pj"]}</td><td>{r["dg"] and dg or "0"}</td>'
                     f'<td><b>{r["pts"]}</b></td></tr>')
    grp_html = (f'<div class="sl-sec"><h3 class="pl-gt">{group_label}</h3>'
                f'<table class="sl-grp"><thead><tr><th>#</th><th>Equipo</th>'
                f'<th>PJ</th><th>DG</th><th>Pts</th></tr></thead>'
                f'<tbody>{grp_rows}</tbody></table></div>') if rows else ""

    m_html = ""
    for m in matches:
        h, a = m.get("home", ""), m.get("away", "")
        status = m.get("status", "")
        played = status in ("FINISHED", "IN_PLAY", "PAUSED")
        live = status in ("IN_PLAY", "PAUSED")
        hg, ag = m.get("home_goals"), m.get("away_goals")
        mid = str(m.get("match_id") or "")
        hh = f'<b>{traducir(h)}</b>' if h == team else traducir(h)
        aa = f'<b>{traducir(a)}</b>' if a == team else traducir(a)
        if played and hg is not None and ag is not None:
            center = f'<span class="sl-sc">{hg} - {ag}</span>'
        else:
            center = f'<span class="sl-dt" data-utc="{m.get("utc_date","")}">—</span>'
        live_b = '<span class="sl-live">EN VIVO</span>' if live else ""
        # ?t=/&tn= → la página de partido muestra "Volver a <selección>" (no se pierde el flujo)
        tq = urllib.parse.quote(team)
        tnq = urllib.parse.quote(nombre_es(team))
        full_link = (f'<a class="sl-full" href="/partido.html?id={mid}&t={tq}&tn={tnq}" '
                     f'onclick="event.stopPropagation()">Ver partido completo &#8594;</a>')
        # 9.1 / detalle al estilo del inicio. show_vermatch=False: el badge de abajo cubre el acceso.
        detail = _hoy_detail_html(m, None, show_vermatch=False) if played else ""
        # Todos los partidos son expandibles (jugados y próximos); el "Ver completo" vive
        # dentro del detalle (no se ve hasta abrir). Toggle con ABRIR/CERRAR + flecha.
        toggle = ('<span class="sl-toggle"><span class="sl-toggle-t"></span>'
                  '<span class="sl-chev">&#9662;</span></span>')
        inner = detail + f'<div class="sl-full-wrap">{full_link}</div>'
        m_html += (f'<div class="sl-m sl-exp" onclick="this.classList.toggle(\'open\')">'
                   f'<div class="sl-m-top"><span class="sl-mh">{hh}</span>{center}'
                   f'<span class="sl-ma">{aa}</span>{live_b}{toggle}</div>'
                   f'<div class="sl-m-detail">{inner}</div></div>')
    matches_html = (f'<div class="sl-sec"><h3 class="pl-gt">Partidos</h3>'
                    f'<div class="sl-matches">{m_html}</div></div>') if matches else ""

    cruces_html = render_cruces_block(cruces, cruces_exact)

    team_q = urllib.parse.quote(team)
    cta = (f'<a class="sl-cta" href="/plantel.html?t={team_q}">'
           f'Ver plantel completo &#8594;</a>')

    return title + grp_html + cruces_html + matches_html + cta


def render_seleccion_shell() -> str:
    """Página shell de perfil de selección. Lee ?t= e inyecta el fragmento de selecciones.json."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Perfil de selección · Mundial 2026</title>
  <meta name="description" content="Perfil de la selección en el Mundial 2026: ranking FIFA, palmarés mundialista, su grupo, partidos y acceso al plantel completo.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Mejor Tercero">
  <meta property="og:title" content="Perfil de selección · Mundial 2026">
  <meta property="og:description" content="Ranking FIFA, palmarés, grupo y partidos de la selección en el Mundial 2026.">
  <meta property="og:image" content="https://mejortercero.online/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://mejortercero.online/og.png">
  <meta name="theme-color" content="#c2410c">
  <link rel="icon" href="/favicon.ico">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:24px 18px 48px}}
    .wrap{{max-width:640px;margin:0 auto}}
    .topbar{{display:flex;align-items:center;gap:12px;margin-bottom:22px}}
    .back{{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:600;color:{T};text-decoration:none;border:1px solid {BDR};border-radius:8px;padding:6px 12px;background:{WHT}}}
    .back:hover{{background:{GRY}}}
    .brand{{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{DIM}}}
    .pl-title{{font-size:1.5rem;font-weight:700;letter-spacing:-.02em;margin-bottom:14px;display:flex;align-items:center;gap:10px}}
    .pl-title img{{width:32px;height:24px;border-radius:2px}}
    .pl-ficha{{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:26px}}
    .pl-fi{{background:{WHT};border:1px solid {BDR};border-radius:10px;padding:8px 13px;display:flex;flex-direction:column;gap:2px;flex:1;min-width:118px}}
    .pl-fi-wide{{flex:2;min-width:170px}}
    .pl-fi-k{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM}}}
    .pl-fi-v{{font-size:.9rem;font-weight:700;color:{TXT}}}
    .pl-fi-v.rk{{color:{T}}}
    .sl-sec{{margin-bottom:26px}}
    .pl-gt{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{T};margin-bottom:11px}}
    {CRUCES_CSS}
    .sl-grp{{width:100%;border-collapse:collapse;background:{WHT};border:1px solid {BDR};border-radius:10px;overflow:hidden}}
    .sl-grp th{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:{DIM};text-align:center;padding:8px 4px;border-bottom:1px solid {BDR}}}
    .sl-grp th:nth-child(2){{text-align:left;padding-left:12px}}
    .sl-grp td{{font-size:.82rem;text-align:center;padding:9px 4px;border-bottom:1px solid {GRY}}}
    .sl-grp td.sl-tn{{text-align:left;padding-left:12px;font-weight:600;display:flex;align-items:center}}
    .sl-grp tr:last-child td{{border-bottom:none}}
    .sl-grp tr.sl-me{{background:{GRY}}}
    .sl-grp tr.sl-me td.sl-tn{{color:{T}}}
    .sl-tn .sl-tlink{{color:inherit;text-decoration:none;display:flex;align-items:center}}
    .sl-tn .sl-tlink:hover{{color:{T};text-decoration:underline}}
    .sl-matches{{display:flex;flex-direction:column;gap:7px}}
    .sl-m{{background:{WHT};border:1px solid {BDR};border-radius:10px;overflow:hidden}}
    .sl-m:hover{{border-color:{BDR2}}}
    .sl-m-top{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;padding:11px 64px 11px 14px;position:relative;cursor:pointer;user-select:none}}
    .sl-mh{{justify-self:end;text-align:right;font-size:.85rem;display:flex;align-items:center}}
    .sl-ma{{justify-self:start;text-align:left;font-size:.85rem;display:flex;align-items:center}}
    .sl-sc{{font-size:.95rem;font-weight:700;color:{T};min-width:48px;text-align:center}}
    .sl-dt{{font-size:.72rem;font-weight:600;color:{MUT};min-width:74px;text-align:center}}
    .sl-live{{position:absolute;top:-7px;left:50%;transform:translateX(-50%);font-size:.52rem;font-weight:700;letter-spacing:.05em;background:{T};color:#fff;padding:1px 7px;border-radius:6px}}
    .sl-toggle{{position:absolute;right:13px;top:50%;transform:translateY(-50%);display:flex;align-items:center;gap:5px}}
    .sl-toggle-t{{font-size:.54rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:{MUT}}}
    .sl-toggle-t::after{{content:"Abrir"}}
    .sl-m.open .sl-toggle-t::after{{content:"Cerrar"}}
    .sl-m.open .sl-toggle-t{{color:{T}}}
    .sl-chev{{color:{BDR2};font-size:.7rem;transition:transform .2s}}
    .sl-m.open .sl-chev{{transform:rotate(180deg);color:{T}}}
    .sl-m-detail{{display:none;border-top:1px solid {GRY};padding:11px 14px;background:{BG}}}
    .sl-m.open .sl-m-detail{{display:block}}
    .sl-full-wrap{{text-align:center;margin-top:11px}}
    .sl-full{{display:inline-flex;align-items:center;gap:6px;font-size:.72rem;font-weight:700;
             letter-spacing:.02em;color:{T};text-decoration:none;border:1px solid {T};border-radius:999px;
             padding:6px 14px;background:rgba(194,65,12,.05);transition:background .15s,color .15s}}
    .sl-full:hover{{background:{T};color:#fff}}
    .hoy-dsec{{margin-bottom:9px}}
    .hoy-dsec:last-child{{margin-bottom:0}}
    .hoy-dsec-t{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{DIM};margin:0 0 4px}}
    .hoy-ev{{display:flex;align-items:flex-start;gap:6px;padding:2px 0;font-size:.75rem;color:{TXT}}}
    .hoy-ev-min{{color:{DIM};font-size:.68rem;min-width:26px;flex-shrink:0;padding-top:1px}}
    .hoy-ev-dot{{width:7px;height:7px;border-radius:50%;background:{T};flex-shrink:0;margin-top:3px}}
    .hoy-ev-yc{{width:7px;height:10px;background:#d97706;flex-shrink:0;margin-top:2px;border-radius:1px}}
    .hoy-ev-rc{{width:7px;height:10px;background:#dc2626;flex-shrink:0;margin-top:2px;border-radius:1px}}
    .hoy-ev-sw{{font-size:.75rem;color:{TEL};flex-shrink:0;line-height:1.4}}
    .hoy-ev-s{{color:{MUT};font-size:.68rem}}
    .hoy-ev-txt{{flex:1;line-height:1.45}}
    .gf-row{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;font-size:.78rem}}
    .gf-tm{{display:inline-flex;align-items:center;flex-shrink:0}}
    .gf-ph{{color:{T};font-weight:700;font-size:.66rem;text-align:right;white-space:nowrap}}
    .sl-cta{{display:inline-flex;align-items:center;gap:6px;font-size:.85rem;font-weight:700;color:#fff;background:{T};border-radius:9px;padding:11px 18px;text-decoration:none}}
    .sl-cta:hover{{opacity:.92}}
    .loading{{text-align:center;color:{MUT};font-size:.85rem;margin-top:40px}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <a class="back" href="/">&#8592; Volver al inicio</a>
      <span class="brand">Mundial 2026</span>
    </div>
    <div id="sel"><p class="loading">Cargando selección…</p></div>
  </div>
  <script>
    function fmtDT(utc) {{
      var d = new Date(utc);
      if (isNaN(d)) return '';
      var f = d.toLocaleDateString('es', {{day:'2-digit', month:'2-digit'}});
      var h = d.toLocaleTimeString('es', {{hour:'2-digit', minute:'2-digit'}});
      return f + ' · ' + h;
    }}
    (function() {{
      var t = new URLSearchParams(location.search).get('t') || '';
      var box = document.getElementById('sel');
      fetch('/api/selecciones')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
          var html = d[t];
          if (html) {{
            box.innerHTML = html;
            document.title = t + ' · Mundial 2026';
            box.querySelectorAll('.sl-dt[data-utc]').forEach(function(e) {{
              var s = fmtDT(e.dataset.utc); if (s) e.textContent = s;
            }});
          }} else {{
            box.innerHTML = '<p class="loading">Selección no disponible todavía.</p>';
          }}
        }})
        .catch(function() {{ box.innerHTML = '<p class="loading">No se pudo cargar la selección.</p>'; }});
    }})();
  </script>
</body>
</html>"""


def render_plantel_shell() -> str:
    """Página shell estática de plantel. Lee ?t= e inyecta el fragmento de planteles.json."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Plantel · Mundial 2026</title>
  <meta name="description" content="Plantel completo de la selección en el Mundial 2026: jugadores con club y país, posiciones, números del torneo y director técnico.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Mejor Tercero">
  <meta property="og:title" content="Plantel · Mundial 2026">
  <meta property="og:description" content="Jugadores, posiciones, club y DT de la selección en el Mundial 2026.">
  <meta property="og:image" content="https://mejortercero.online/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://mejortercero.online/og.png">
  <meta name="theme-color" content="#c2410c">
  <link rel="icon" href="/favicon.ico">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:24px 18px 48px}}
    .wrap{{max-width:640px;margin:0 auto}}
    .topbar{{display:flex;align-items:center;gap:12px;margin-bottom:22px}}
    .back{{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:600;color:{T};text-decoration:none;border:1px solid {BDR};border-radius:8px;padding:6px 12px;background:{WHT}}}
    .back:hover{{background:{GRY}}}
    .brand{{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{DIM}}}
    .pl-title{{font-size:1.5rem;font-weight:700;letter-spacing:-.02em;margin-bottom:14px;display:flex;align-items:center;gap:10px}}
    .pl-title img{{width:32px;height:24px;border-radius:2px}}
    .pl-ficha{{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:24px}}
    .pl-fi{{background:{WHT};border:1px solid {BDR};border-radius:10px;padding:8px 13px;display:flex;flex-direction:column;gap:2px;flex:1;min-width:118px}}
    .pl-fi-wide{{flex:2;min-width:170px}}
    .pl-fi-k{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM}}}
    .pl-fi-v{{font-size:.9rem;font-weight:700;color:{TXT}}}
    .pl-fi-v.rk{{color:{T}}}
    .pl-group{{margin-bottom:24px}}
    .pl-gt{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{T};margin-bottom:10px;display:flex;align-items:center;gap:8px}}
    .pl-gc{{background:{GRY};color:{MUT};border-radius:10px;padding:1px 8px;font-size:.62rem}}
    .pl-list{{display:flex;flex-direction:column;gap:7px}}
    .pl-card{{background:{WHT};border:1px solid {BDR};border-radius:10px;cursor:pointer;user-select:none;overflow:hidden}}
    .pl-card:hover{{border-color:{BDR2}}}
    .pl-row{{display:flex;align-items:center;gap:11px;padding:9px 13px}}
    .pl-photo{{width:38px;height:38px;border-radius:50%;object-fit:cover;background:{GRY};flex-shrink:0}}
    .pl-num{{font-size:.82rem;font-weight:700;color:{T};min-width:24px;text-align:center}}
    .pl-name{{font-size:.9rem;font-weight:600;flex:1;display:flex;flex-direction:column;gap:1px;min-width:0}}
    .pl-club{{font-size:.66rem;font-weight:500;color:{DIM};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .pl-chev{{color:{BDR2};font-size:.7rem;transition:transform .2s}}
    .pl-card.open .pl-chev{{transform:rotate(180deg)}}
    .pl-detail{{display:none;border-top:1px solid {GRY};padding:11px 13px;background:{BG}}}
    .pl-card.open .pl-detail{{display:block}}
    .pl-info{{display:flex;flex-wrap:wrap;gap:8px 22px}}
    .pl-kv{{display:flex;flex-direction:column;gap:1px}}
    .pl-k{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:{DIM}}}
    .pl-stats{{border-top:1px solid {BDR};margin-top:9px;padding-top:9px;display:flex;flex-wrap:wrap;gap:8px 22px;align-items:flex-start}}
    .pl-stats-t{{width:100%;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{T};margin-bottom:2px}}
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
