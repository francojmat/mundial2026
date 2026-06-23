"""Renderer HTML — identidad Zevra + bracket interactivo."""

import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set
from countries import traducir, nombre_es, bandera_img, venue_maps_url, VENUE_INFO
from scenarios import compute_group_scenarios, team_phrase, _opp_name
from bracket import r32_destination

_ARG_TZ = timezone(timedelta(hours=-3))

T   = "#c2410c"
TEL = "#0d9488"
OK  = "#16a34a"
WRN = "#d97706"
BG  = "#faf8f4"
WHT = "#ffffff"
BDR = "#e8ddd0"
BDR2= "#c8b8a8"
TXT = "#211c14"
MUT = "#7c6a58"
DIM = "#b09880"
GRY = "#f0ebe4"

# CSS del bloque "¿Contra quién?" (cruces) — compartido por el shell del home y el de
# selección. Es un f-string ya interpolado (con llaves literales) → se inserta tal cual
# en otros f-strings vía {CRUCES_CSS} sin reinterpretarse.
CRUCES_CSS = (
    f".cz-block{{margin-bottom:18px}}.cz-block:last-child{{margin-bottom:0}}"
    f".cz-head{{font-size:.8rem;font-weight:700;color:{TXT};margin-bottom:5px;line-height:1.3}}"
    f".cz-sub{{font-size:.68rem;color:{MUT};margin-bottom:10px}}"
    f".cz-mwrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}"
    f".cz-matrix{{width:100%;border-collapse:collapse;font-size:.72rem;background:{WHT};border:1px solid {BDR};border-radius:10px;overflow:hidden}}"
    f".cz-matrix th{{font-size:.56rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:{DIM};text-align:left;padding:7px 10px;border-bottom:1px solid {BDR};white-space:nowrap}}"
    f".cz-matrix th.cz-riv-h{{color:{T}}}"
    f".cz-matrix td{{padding:6px 10px;border-bottom:1px solid {GRY};white-space:nowrap;color:{TXT}}}"
    f".cz-matrix tr:last-child td{{border-bottom:none}}"
    f".cz-matrix td.cz-riv{{color:{TXT};font-weight:700}}"
    f".cz-matrix td.cz-riv img{{height:1em;width:auto;border-radius:1px;margin:0 3px 0 0;vertical-align:-.1em}}"
    f".cz-vs{{color:{DIM};font-weight:400;font-size:.85em}}"
    f".cz-note{{font-weight:400;color:{MUT};font-size:.64rem}}.cz-rk{{font-weight:400;color:{MUT};font-size:.88em}}"
    f".cz-confirm{{font-size:.92rem;font-weight:700;color:{T};display:flex;align-items:center;gap:6px}}"
    f".cz-confirm img{{height:1em;width:auto;border-radius:1px}}"
    f".cz-branch{{background:{WHT};border:1px solid {BDR};border-radius:10px;padding:11px 13px;margin-bottom:9px}}"
    f".cz-tag{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:{DIM};margin:5px 0 9px}}"
    f".cz-opps{{display:flex;flex-wrap:wrap;gap:6px}}"
    f".cz-opp{{display:inline-flex;align-items:center;gap:5px;font-size:.74rem;background:{GRY};border-radius:6px;padding:4px 9px}}"
    f".cz-opp img{{height:1em;width:auto;border-radius:1px}}"
    f".cz-bw{{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:10px;padding-top:9px;border-top:1px solid {GRY};font-size:.72rem}}"
    f".cz-bw img{{height:1em;width:auto;border-radius:1px;vertical-align:-.1em;margin:0 3px}}"
    f".cz-bw-k{{font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:{T};margin-right:5px}}"
    # propios de la sección del home
    f".cz-sel{{width:100%;max-width:360px;padding:9px 12px;font-size:.85rem;border:1px solid {BDR2};border-radius:8px;background:{WHT};color:{TXT};margin-bottom:16px}}"
)

# Horarios aproximados R16/QF/SF/Final (UTC)
# Calendario oficial FIFA 2026 (octavos→final) — sede + horario, verificado contra
# Wikipedia "knockout stage". Horarios convertidos a UTC. Slots → partido:
# r16-L-0=P89, r16-L-1=P90, r16-L-2=P93, r16-L-3=P94, r16-R-0=P91, r16-R-1=P92,
# r16-R-2=P95, r16-R-3=P96, qf-L-0=P97, qf-L-1=P98, qf-R-0=P99, qf-R-1=P100,
# sf-L-0=P101, sf-R-0=P102.
_KO_SCHEDULE = {
    "r16-L-0": ("2026-07-04T21:00:00Z", "Lincoln Financial Field, Filadelfia"),  # P89
    "r16-L-1": ("2026-07-04T17:00:00Z", "NRG Stadium, Houston"),                  # P90
    "r16-L-2": ("2026-07-06T19:00:00Z", "AT&T Stadium, Dallas"),                  # P93
    "r16-L-3": ("2026-07-07T00:00:00Z", "Lumen Field, Seattle"),                  # P94
    "r16-R-0": ("2026-07-05T20:00:00Z", "MetLife Stadium, New Jersey"),           # P91
    "r16-R-1": ("2026-07-06T00:00:00Z", "Estadio Azteca, CDMX"),                  # P92
    "r16-R-2": ("2026-07-07T16:00:00Z", "Mercedes-Benz Stadium, Atlanta"),        # P95
    "r16-R-3": ("2026-07-07T20:00:00Z", "BC Place, Vancouver"),                   # P96
    "qf-L-0":  ("2026-07-09T20:00:00Z", "Gillette Stadium, Boston"),              # P97
    "qf-L-1":  ("2026-07-10T19:00:00Z", "SoFi Stadium, Los Ángeles"),             # P98
    "qf-R-0":  ("2026-07-11T21:00:00Z", "Hard Rock Stadium, Miami"),              # P99
    "qf-R-1":  ("2026-07-12T01:00:00Z", "Arrowhead Stadium, Kansas City"),        # P100
    "sf-L-0":  ("2026-07-14T19:00:00Z", "AT&T Stadium, Dallas"),                  # P101
    "sf-R-0":  ("2026-07-15T19:00:00Z", "Mercedes-Benz Stadium, Atlanta"),        # P102
}
_3RD_PLACE = ("2026-07-18T21:00:00Z", "Hard Rock Stadium, Miami")                 # P103
_FINAL     = ("2026-07-19T19:00:00Z", "MetLife Stadium, New Jersey")              # P104


def _done(matches) -> bool:
    return sum(1 for m in matches if m.played) >= 6

def _live(matches) -> bool:
    return any(m.status in ("IN_PLAY", "PAUSED") for m in matches)


def render_html(standings: Dict, matchups: List[Dict]) -> str:
    live_teams: Set[str] = standings.get("_live_teams", set())
    thirds_advancing_set = {e["team"] for e in standings.get("_thirds_advancing", [])}
    updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ko_json = _ko_schedule_json()

    # SEO/GEO — datos estructurados (Schema.org): sitio + el Mundial como SportsEvent
    import json as _json
    _jsonld = _json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": "Mejor Tercero",
             "url": "https://mejortercero.online/", "inLanguage": "es",
             "description": "Mundial 2026 en vivo: posiciones por grupo, mejores terceros, "
                            "bracket, goleadores y estadios, actualizados al instante."},
            {"@type": "SportsEvent", "name": "Copa Mundial de la FIFA 2026",
             "alternateName": "Mundial 2026", "sport": "Fútbol",
             "startDate": "2026-06-11", "endDate": "2026-07-19",
             "eventStatus": "https://schema.org/EventScheduled",
             "location": {"@type": "Place", "name": "Estados Unidos, México y Canadá"},
             "url": "https://mejortercero.online/"},
        ],
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Mejor Tercero · Mundial 2026 en vivo: posiciones, terceros, bracket y goleadores</title>
  <meta name="description" content="Seguí el Mundial 2026 en vivo: posiciones por grupo con desempates FIFA, los mejores terceros, bracket de 32avos, goleadores, valoraciones y estadios. Resultados y escenarios de clasificación al instante.">
  <link rel="canonical" href="https://mejortercero.online/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Mejor Tercero">
  <meta property="og:title" content="Mejor Tercero · Mundial 2026 en vivo">
  <meta property="og:description" content="Posiciones, mejores terceros, bracket, goleadores y estadios del Mundial 2026, actualizados al instante.">
  <meta property="og:image" content="https://mejortercero.online/og.png">
  <meta property="og:url" content="https://mejortercero.online/">
  <meta property="og:locale" content="es_AR">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Mejor Tercero · Mundial 2026 en vivo">
  <meta name="twitter:description" content="Posiciones, mejores terceros, bracket, goleadores y estadios del Mundial 2026, al instante.">
  <meta name="twitter:image" content="https://mejortercero.online/og.png">
  <meta name="theme-color" content="#c2410c">
  <script type="application/ld+json">{_jsonld}</script>
  <link rel="apple-touch-icon" sizes="57x57" href="/apple-icon-57x57.png">
  <link rel="apple-touch-icon" sizes="60x60" href="/apple-icon-60x60.png">
  <link rel="apple-touch-icon" sizes="72x72" href="/apple-icon-72x72.png">
  <link rel="apple-touch-icon" sizes="76x76" href="/apple-icon-76x76.png">
  <link rel="apple-touch-icon" sizes="114x114" href="/apple-icon-114x114.png">
  <link rel="apple-touch-icon" sizes="120x120" href="/apple-icon-120x120.png">
  <link rel="apple-touch-icon" sizes="144x144" href="/apple-icon-144x144.png">
  <link rel="apple-touch-icon" sizes="152x152" href="/apple-icon-152x152.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-icon-180x180.png">
  <link rel="icon" type="image/png" sizes="192x192" href="/android-icon-192x192.png">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
  <link rel="icon" href="/favicon.ico">
  <link rel="manifest" href="/manifest.json">
  <meta name="msapplication-TileColor" content="#ffffff">
  <meta name="msapplication-TileImage" content="/ms-icon-144x144.png">
  <meta name="theme-color" content="#ffffff">
  <script>!function(t,e){{var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){{function g(t,e){{var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){{var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}},u.people.toString=function(){{return u.toString(1)+" (stub)"}},n="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys getNextSurveyStep".split(" "),o=0;o<n.length;o++)g(u,n[o]);e._i.push([i,s,a])}},(e.__SV=1))}}(document,window.posthog||[]);posthog.init('phc_oJ2GTZXyfDHXr3dmKGnEww3n3bNSQ4SRAvbQa43eVZZ5',{{api_host:'https://us.i.posthog.com',person_profiles:'identified_only'}})</script>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    {CRUCES_CSS}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:28px 24px}}

    .hdr{{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:18px;text-align:center}}
    .hdr-logo{{height:68px;width:auto;display:block}}
    @media(max-width:480px){{.hdr-logo{{height:54px}}}}
    h1{{font-size:1.55rem;font-weight:700;letter-spacing:-.02em}}
    .pill{{display:inline-flex;align-items:center;gap:5px;background:rgba(194,65,12,.1);border:1px solid rgba(194,65,12,.35);color:{T};font-size:.68rem;font-weight:700;padding:3px 10px;letter-spacing:.08em;text-transform:uppercase}}
    .dot{{width:6px;height:6px;border-radius:50%;background:{T};animation:blink 1.4s ease-in-out infinite}}
    @keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
    .upd{{font-size:.75rem;color:{DIM};margin-bottom:28px}}

    .sec{{margin-bottom:36px}}
    .sec-t{{font-size:.63rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:{DIM};margin-bottom:12px;padding-bottom:7px;border-bottom:1px solid {BDR}}}
    .divider{{height:1px;background:{BDR};margin:32px 0}}

    .leyenda{{display:flex;gap:18px;margin-bottom:12px;flex-wrap:wrap}}
    .ley-item{{display:flex;align-items:center;gap:6px;font-size:.71rem;color:{MUT}}}
    .ley-dot{{width:12px;height:12px;flex-shrink:0}}

    /* ── Grupos ── */
    .grupos{{display:grid;grid-template-columns:repeat(auto-fill,minmax(450px,1fr));gap:12px}}
    .grupo{{background:{WHT};border:1px solid {BDR};overflow:hidden}}
    .grupo-h{{display:flex;align-items:center;justify-content:space-between;padding:9px 14px 8px;border-bottom:1px solid {BDR}}}
    .grupo-t{{font-size:.76rem;font-weight:700;color:{T};letter-spacing:.08em;text-transform:uppercase}}
    .grupo-foot{{border-top:1px solid {GRY}}}
    .gf-toggle{{display:flex;align-items:center;justify-content:space-between;padding:8px 14px;cursor:pointer;user-select:none}}
    .gf-toggle-t{{display:inline-block;font-size:.57rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{MUT};border:1px solid {BDR};border-radius:999px;padding:3px 11px;background:{GRY};transition:all .15s}}
    .grupo-foot.open .gf-toggle-t{{color:{T};border-color:{T};background:rgba(194,65,12,.06)}}
    .gf-chev{{font-size:.6rem;color:{MUT};transition:transform .2s}}
    .grupo-foot.open .gf-chev{{transform:rotate(180deg);color:{T}}}
    .gf-body{{display:none;padding:2px 14px 11px}}
    .grupo-foot.open .gf-body{{display:block}}
    .gf-stats{{font-size:.68rem;color:{MUT};font-weight:700;letter-spacing:.02em}}
    .gf-esc{{margin-top:9px}}
    .gf-cap{{display:inline-block;font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{T};border:1px solid {T};border-radius:999px;padding:3px 10px;background:rgba(194,65,12,.05);margin-bottom:9px}}
    .gf-row{{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;font-size:.78rem;color:{TXT}}}
    .gf-tm{{display:inline-flex;align-items:center;flex-shrink:0}}
    .gf-tm img{{height:1em;width:auto;border-radius:1px}}
    .gf-ph{{color:{T};font-weight:700;font-size:.66rem;text-align:right;white-space:normal;line-height:1.35}}
    .gf-ph img{{height:.95em;width:auto;border-radius:1px;vertical-align:-.05em}}
    .gd-row{{display:flex;align-items:baseline;justify-content:space-between;gap:10px;padding:3px 0;font-size:.72rem}}
    .gd-k{{flex-shrink:0;font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:{MUT}}}
    .gd-v{{color:{TXT};text-align:right;line-height:1.35}}
    .gd-v img{{height:.85em;width:auto;border-radius:1px}}
    .gd-hl{{color:{T};font-weight:700}}
    .corte-row td{{text-align:center;font-size:.57rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{T};background:rgba(194,65,12,.07);border-top:2px solid {T};border-bottom:2px solid {T};padding:5px}}
    .terc-prov{{font-size:.54rem;color:{DIM};font-weight:700;margin-left:5px;text-transform:uppercase;letter-spacing:.03em}}
    .terc-exp{{font-size:.8rem;color:{TXT};line-height:1.55;margin:0}}
    .terc-exp-box{{margin-bottom:12px}}
    .pl-cell{{display:inline-flex;align-items:center}}
    .pl-av{{width:22px;height:22px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:7px;background:{GRY};flex-shrink:0}}
    .rank-filter{{margin-bottom:10px;text-align:center}}
    .rank-filter select{{font-size:.74rem;font-family:inherit;color:{TXT};background:{WHT};border:1px solid {BDR};border-radius:6px;padding:5px 12px;cursor:pointer;max-width:100%}}
    .badge{{font-size:.6rem;font-weight:700;padding:2px 9px;border-radius:999px;letter-spacing:.05em;text-transform:uppercase;background:transparent;border:1.5px solid transparent}}
    .b-ok  {{color:{MUT};border-color:{BDR2}}}
    .b-vivo{{color:{T};border-color:{T}}}
    .b-live{{color:{T};border-color:{T};display:inline-flex;align-items:center;gap:4px}}

    table{{width:100%;border-collapse:collapse}}
    th{{font-size:.61rem;font-weight:600;color:{DIM};letter-spacing:.08em;text-transform:uppercase;padding:5px 10px;text-align:center;border-bottom:1px solid {BDR}}}
    th:first-child,th:nth-child(2){{text-align:left}}
    td{{font-size:.81rem;padding:7px 10px;text-align:center;border-bottom:1px solid {BG}}}
    td:first-child{{text-align:center;color:{DIM};width:26px;font-size:.72rem}}
    td:nth-child(2){{text-align:left;white-space:nowrap}}
    tr:last-child td{{border-bottom:none}}

    tr.clasifica td{{background:{WHT}}}
    tr.clasifica td:first-child{{border-left:3px solid {TEL}}}
    tr.clasifica td:nth-child(2){{font-weight:600}}
    tr.tercero td{{background:{WHT}}}
    tr.tercero td:first-child{{border-left:3px solid {T}}}
    tr.eliminado td{{background:{GRY};color:{DIM}}}
    tr.eliminado td:first-child{{border-left:3px solid {BDR}}}

    .pts{{color:{T};font-weight:700;font-size:.87rem}}
    .dg-p{{color:{OK}}}.dg-n{{color:#dc2626}}
    .live-row{{background:rgba(194,65,12,.05)!important}}
    .live-name::after{{content:" ●";color:{T};font-size:.6rem;animation:blink 1.4s ease-in-out infinite}}

    /* ── Bracket ── */
    .llaves-wrap{{overflow:hidden;width:100%}}
    .bracket-leyenda{{font-size:.72rem;color:{MUT};margin:0 0 14px;padding:8px 12px;background:{GRY};border-radius:6px;line-height:1.45;max-width:760px}}
    .bracket-leyenda b{{color:{T}}}
    .bl-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;background:{T};animation:blink 1.4s ease-in-out infinite;vertical-align:middle;margin-right:2px}}
    .llaves{{display:flex;align-items:stretch;min-height:960px;min-width:1200px;gap:0}}

    /* ── Responsive ── */
    @media(max-width:900px){{
      body{{padding:20px 16px}}
      .grupos{{grid-template-columns:repeat(auto-fill,minmax(min(450px,100%),1fr))}}
    }}
    @media(max-width:640px){{
      body{{padding:14px 10px}}
      h1{{font-size:1.2rem}}
      .upd{{font-size:.68rem;margin-bottom:20px}}
      .grupos{{grid-template-columns:1fr}}
      td{{font-size:.74rem;padding:5px 6px}}
      th{{font-size:.55rem;padding:4px 6px}}
      .reset-btn{{font-size:.68rem}}
    }}

    .mitad{{display:flex;flex:1}}

    /* Columnas de ronda */
    .col{{display:flex;flex-direction:column;justify-content:space-around}}
    .col.r32{{width:200px;flex-shrink:0}}
    .col.r16,.col.qf,.col.sf{{width:200px;flex-shrink:0}}

    /* Conectores: vertical limitado entre centros de cards (sin sobrantes arriba/abajo) */
    .conn{{width:24px;flex-shrink:0;display:flex;flex-direction:column;overflow:visible}}
    .arm{{flex:1;display:flex;flex-direction:column;overflow:visible}}
    .arm-t{{flex:1;position:relative;overflow:visible}}
    .arm-t::after{{content:'';position:absolute;top:50%;left:0;right:0;border-top:1px solid {BDR2}}}
    .arm-t::before{{content:'';position:absolute;top:50%;bottom:0;right:0;width:1px;background:{BDR2}}}
    .arm-b{{flex:1;position:relative;overflow:visible}}
    .arm-b::after{{content:'';position:absolute;top:50%;left:0;right:0;border-top:1px solid {BDR2}}}
    .arm-b::before{{content:'';position:absolute;top:0;bottom:50%;right:0;width:1px;background:{BDR2}}}
    .mitad.der .arm-t::before{{right:auto;left:0}}
    .mitad.der .arm-b::before{{right:auto;left:0}}

    /* ── Match card ── */
    .par{{display:flex;flex-direction:column;flex:1;justify-content:space-around}}
    .mc{{background:{WHT};border:1px solid {BDR};margin:2px 0;display:flex;flex-direction:column}}
    .mc.on-path{{border-color:{T};box-shadow:0 0 0 2px rgba(194,65,12,.22);position:relative;z-index:3}}
    .mc-label-r{{display:flex;align-items:center;gap:5px}}
    .h2h-btn{{font-size:.5rem;font-weight:700;letter-spacing:.04em;color:{T};background:transparent;border:1px solid {T};border-radius:4px;padding:0 4px;cursor:pointer;line-height:1.5}}
    .h2h-btn:hover{{background:rgba(194,65,12,.12)}}
    .h2h-overlay{{display:none;position:fixed;inset:0;background:rgba(33,28,20,.45);z-index:100;align-items:center;justify-content:center;padding:20px}}
    .h2h-overlay.open{{display:flex}}
    .h2h-modal{{background:{WHT};border-radius:12px;max-width:420px;width:100%;padding:18px 20px;box-shadow:0 12px 44px rgba(0,0,0,.22)}}
    .h2h-head{{display:flex;align-items:center;justify-content:space-between;font-weight:700;font-size:.95rem;color:{TXT}}}
    .h2h-x{{background:none;border:none;font-size:1.35rem;color:{MUT};cursor:pointer;line-height:1}}
    .h2h-sub{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{DIM};margin:1px 0 10px}}
    .h2h-row{{padding:7px 0;border-top:1px solid {GRY}}}
    .h2h-row:first-child{{border-top:none}}
    .h2h-d{{font-size:.6rem;color:{DIM};font-weight:700;margin-right:8px}}
    .h2h-c{{font-size:.58rem;color:{MUT}}}
    .h2h-r{{display:block;font-size:.84rem;color:{TXT};margin-top:1px}}
    .h2h-r b{{color:{T}}}
    .mc-label{{font-size:.58rem;font-weight:700;color:{DIM};letter-spacing:.07em;text-transform:uppercase;padding:4px 8px 3px;border-bottom:1px solid {BG};display:flex;justify-content:space-between;align-items:center;flex-shrink:0}}
    .mc-meta{{font-size:.6rem;color:{DIM};padding:3px 8px 4px;border-top:1px solid {BG};display:flex;flex-direction:column;gap:1px;flex-shrink:0}}
    .mc-meta .venue{{color:{MUT};font-size:.57rem}}

    .badge-live-sm{{color:{T};background:transparent;border:1.5px solid {T};font-size:.55rem;font-weight:700;padding:1px 7px;border-radius:999px;text-transform:uppercase;display:inline-flex;align-items:center;gap:3px}}
    .badge-live-sm .dot{{width:4px;height:4px}}

    /* Filas de equipo — clicables */
    .team-row{{display:flex;align-items:center;padding:6px 8px;font-size:.79rem;cursor:pointer;transition:background .15s;user-select:none;border-bottom:1px solid {BG};min-height:30px}}
    .team-row:last-of-type{{border-bottom:none}}
    .team-row:hover{{background:rgba(194,65,12,.06)}}
    .team-row.winner{{background:rgba(194,65,12,.08);font-weight:700;color:{T};border-left:2px solid {T}}}
    .team-row.loser{{opacity:.28;text-decoration:line-through;cursor:default}}
    .team-row.ph{{color:{DIM};font-style:italic;cursor:default;font-size:.73rem}}
    .team-row.ph:hover{{background:none}}
    .team-row.prov{{color:{MUT};font-style:italic}}
    .team-row img{{flex-shrink:0}}

    /* ── Columna central ── */
    .final-col{{width:200px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:0 6px}}

    /* Final */
    .final-box{{background:linear-gradient(135deg,#fff9f7 0%,#fff 100%);border:2px solid {T};width:100%;position:relative;overflow:hidden}}
    .final-box::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,{T},{WRN},{T})}}
    .final-inner{{padding:14px 10px 12px;text-align:center}}
    .final-title{{font-size:.65rem;font-weight:700;color:{T};letter-spacing:.12em;text-transform:uppercase;margin-bottom:2px}}
    .final-date{{font-size:.6rem;color:{DIM};margin-bottom:8px}}
    .final-venue{{font-size:.57rem;color:{DIM};margin-bottom:8px}}
    .final-teams{{border-top:1px solid {BDR};padding-top:6px}}
    .final-teams .team-row{{font-size:.72rem;justify-content:center;padding:5px 6px}}
    .final-teams .team-row.champion{{color:{T};font-weight:700;font-size:.77rem;background:rgba(194,65,12,.06)}}
    .champ-card{{background:linear-gradient(135deg,#fff9f7 0%,#fff 100%);border:2px solid {T};width:100%;position:relative;overflow:hidden;text-align:center;padding:10px 8px 12px}}
    .champ-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,{T},{WRN},{T})}}
    .champ-trophy-img{{display:block;margin:6px auto 8px;width:68px;height:auto}}
    .champ-card-flag{{margin-bottom:5px}}
    .champ-card-flag img{{display:block;margin:0 auto;width:48px;height:36px;image-rendering:crisp-edges}}
    .champ-card-country{{font-size:.88rem;font-weight:700;color:{TXT};margin-bottom:3px;line-height:1.2}}
    .champ-card-subtitle{{font-size:.54rem;font-weight:700;color:{T};letter-spacing:.1em;text-transform:uppercase}}

    /* 3er puesto */
    .tercer-box{{background:{WHT};border:1px solid {BDR};width:100%;border-top:2px solid {TEL}}}
    .tercer-inner{{padding:10px 8px 8px;text-align:center}}
    .tercer-title{{font-size:.6rem;font-weight:700;color:{TEL};letter-spacing:.1em;text-transform:uppercase;margin-bottom:2px}}
    .tercer-date{{font-size:.57rem;color:{DIM};margin-bottom:6px}}
    .tercer-venue{{font-size:.54rem;color:{DIM}}}
    .tercer-teams{{border-top:1px solid {BDR};padding-top:4px}}
    .tercer-teams .team-row{{font-size:.7rem;justify-content:center;padding:4px 6px}}
    .tercer-teams .team-row.winner{{border-left:none}}
    .final-teams .team-row.winner{{border-left:none}}

    .reset-btn{{margin-top:14px;font-size:.72rem;color:{MUT};background:none;border:1px solid {BDR};padding:5px 12px;cursor:pointer;font-family:inherit}}
    .reset-btn:hover{{border-color:{T};color:{T}}}
    @keyframes fadeIn{{from{{opacity:0;transform:translateY(3px)}}to{{opacity:1;transform:none}}}}
    .fade-in{{animation:fadeIn .22s ease}}

    /* ── Partidos de hoy ── */
    .hoy-nav{{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:10px}}
    .hoy-nav-btn{{background:none;border:1px solid {BDR};border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:1.1rem;line-height:1;display:flex;align-items:center;justify-content:center;color:{DIM};padding:0;flex-shrink:0}}
    .hoy-nav-btn:hover{{background:{GRY}}}
    .hoy-nav-btn:disabled{{opacity:.3;cursor:default}}
    .hoy-lista{{display:flex;flex-direction:column;gap:6px;max-width:600px;margin:0 auto}}
    .hoy-fila{{background:{WHT};border:1px solid {BDR};padding:7px 12px;cursor:pointer;user-select:none}}
    .hoy-fila:hover{{border-color:{BDR2}}}
    .hoy-head{{position:relative;text-align:center;margin-bottom:5px;min-height:14px}}
    .hoy-etiqueta{{font-size:.6rem;font-weight:700;color:{DIM};letter-spacing:.08em;text-transform:uppercase;vertical-align:middle}}
    .hoy-chev{{position:absolute;right:0;top:50%;transform:translateY(-50%);color:{BDR2};font-size:.65rem;transition:transform .2s;line-height:1}}
    .hoy-fila.open .hoy-chev{{transform:translateY(-50%) rotate(180deg)}}
    .hoy-fila .hoy-head{{padding:0 58px}}
    .hoy-fila .hoy-head::after{{content:"Abrir";position:absolute;right:14px;top:50%;transform:translateY(-50%);font-size:.55rem;font-weight:700;text-transform:uppercase;letter-spacing:.02em;color:{MUT};white-space:nowrap;pointer-events:none}}
    .hoy-fila.open .hoy-head::after{{content:"Cerrar";color:{T}}}
    @media(max-width:480px){{.hoy-fila .hoy-head{{padding:0 48px}}.hoy-fila .hoy-head::after{{font-size:.5rem;right:12px}}}}
    .hoy-detail{{display:none;border-top:1px solid {GRY};padding:8px 2px 4px;margin-top:8px}}
    .hoy-fila.open .hoy-detail{{display:block}}
    .hoy-vermatch{{display:flex;width:fit-content;align-items:center;gap:7px;margin:2px auto 12px;background:{T};color:{WHT};font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:8px 20px;border-radius:999px;text-decoration:none;transition:opacity .15s,transform .1s}}
    .hoy-vermatch:hover{{opacity:.92}}
    .hoy-vermatch:active{{transform:scale(.98)}}
    .hoy-dsec{{margin-bottom:8px}}
    .hoy-dsec:last-child{{margin-bottom:0}}
    .hoy-dsec-t{{font-size:.58rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{DIM};margin:0 0 4px}}
    .hoy-ev{{display:flex;align-items:flex-start;gap:6px;padding:2px 0;font-size:.75rem;color:{TXT}}}
    .hoy-ev-min{{color:{DIM};font-size:.68rem;min-width:26px;flex-shrink:0;padding-top:1px}}
    .hoy-ev-dot{{width:7px;height:7px;border-radius:50%;background:{T};flex-shrink:0;margin-top:3px}}
    .hoy-ev-yc{{width:7px;height:10px;background:{WRN};flex-shrink:0;margin-top:2px;border-radius:1px}}
    .hoy-ev-rc{{width:7px;height:10px;background:#dc2626;flex-shrink:0;margin-top:2px;border-radius:1px}}
    .hoy-ev-sw{{font-size:.75rem;color:{TEL};flex-shrink:0;line-height:1.4}}
    .hoy-ev-s{{color:{MUT};font-size:.68rem}}
    .hoy-ev-txt{{flex:1;line-height:1.45}}
    .hoy-match{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px;width:100%}}
    .hoy-home{{display:flex;align-items:center;justify-content:flex-start;flex-direction:row-reverse;gap:6px;font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden}}
    .hoy-away{{display:flex;align-items:center;justify-content:flex-start;gap:6px;font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden}}
    .hoy-home img,.hoy-away img{{margin-right:0;flex-shrink:0}}
    .hoy-centro{{display:flex;flex-direction:column;align-items:center;gap:2px;white-space:nowrap}}
    .hoy-score{{font-size:.85rem;font-weight:700;color:{TXT}}}
    .hoy-hora{{font-size:.78rem;font-weight:600;color:{MUT}}}
    .hoy-vs{{font-size:.65rem;color:{DIM};font-weight:600}}
    .hoy-badge-live{{color:{T};font-size:.6rem;font-weight:700;text-transform:uppercase;display:inline-flex;align-items:center;gap:3px;letter-spacing:.04em;vertical-align:middle;margin-left:7px}}
    .hoy-badge-live .dot{{width:5px;height:5px}}
    .hoy-badge-fin{{color:{MUT};font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;vertical-align:middle;margin-left:7px}}
    .team-link{{color:inherit;text-decoration:none;cursor:pointer;border-bottom:1px dotted {BDR2}}}
    .team-link:hover{{color:{T};border-bottom-color:{T}}}
    .ven-name{{font-size:.82rem;font-weight:700;color:{TXT}}}
    .ven-sub{{text-align:center;font-size:.68rem;color:{MUT};margin-top:3px;letter-spacing:.02em}}
    .ven-m{{display:grid;grid-template-columns:34px 1fr auto 1fr;align-items:center;gap:6px;padding:3px 0;font-size:.74rem}}
    .ven-m-date{{color:{DIM};font-size:.66rem}}
    .ven-m-team{{display:flex;align-items:center;gap:4px;white-space:nowrap;overflow:hidden}}
    .ven-m-h{{flex-direction:row-reverse;justify-content:flex-start}}
    .ven-m-a{{justify-content:flex-start}}
    .ven-m-h img,.ven-m-a img{{margin-right:0;flex-shrink:0}}
    .ven-m-mid{{font-weight:700;color:{MUT};font-size:.72rem;text-align:center;min-width:38px}}
    .ven-time{{color:{T};font-weight:700;font-size:.7rem}}
    .ven-m-ko{{border-top:1px dashed {BDR};padding:4px 0}}
    .ven-m-ko .ven-ko-label{{grid-column:2;text-align:right;color:{T};font-weight:700;font-size:.68rem;text-transform:uppercase;letter-spacing:.03em}}
    .ven-img{{width:100%;max-height:150px;object-fit:cover;border-radius:8px;margin-bottom:10px;display:block}}
    .ven-info{{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 18px;margin-bottom:10px;font-size:.78rem;color:{TXT}}}
    .ven-info .ven-k{{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:{DIM};margin-right:4px}}
    .ven-local{{font-size:.74rem;color:{MUT};margin-bottom:10px;text-align:center}}
    .ven-map{{display:flex;width:fit-content;align-items:center;gap:6px;font-size:.7rem;font-weight:700;color:{T};
             margin:0 auto 12px;text-decoration:none;border:1px solid {T};border-radius:999px;
             padding:6px 13px;background:rgba(194,65,12,.05);transition:background .15s,color .15s}}
    .ven-map:hover{{background:{T};color:#fff}}
    .ven-map-ico{{width:12px;height:12px;flex-shrink:0}}
    @media(max-width:480px){{
      .ven-m{{font-size:.68rem;grid-template-columns:28px 1fr auto 1fr}}
      .hoy-home,.hoy-away{{font-size:.72rem}}
      .hoy-score{{font-size:.9rem}}
      .hoy-match{{gap:6px}}
    }}

    /* ── Secciones colapsables ── */
    .sec-hdr{{display:flex;align-items:center;justify-content:space-between;padding-bottom:7px;border-bottom:1px solid {BDR};margin-bottom:12px;cursor:pointer;user-select:none}}
    .sec-hdr:hover .sec-toggle{{color:{T}}}
    .sec-body.sec-collapsed{{display:none}}
    .sec-toggle{{background:none;border:none;color:{DIM};font-size:.7rem;cursor:pointer;padding:0;line-height:1;font-family:inherit}}

    /* ── Sidebar de navegación ── */
    [id^="sec-"]{{scroll-margin-top:16px}}
    .navfab{{position:fixed;bottom:20px;left:20px;z-index:55;background:{T};color:{WHT};border:none;border-radius:12px;width:46px;height:46px;font-size:1.3rem;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.18);display:flex;align-items:center;justify-content:center;line-height:1}}
    .navfab:hover{{opacity:.92}}
    .nav-overlay{{position:fixed;inset:0;background:rgba(33,28,20,.42);z-index:60;opacity:0;pointer-events:none;transition:opacity .2s}}
    .nav-overlay.open{{opacity:1;pointer-events:auto}}
    .nav-drawer{{position:fixed;top:0;left:0;height:100%;width:262px;max-width:82%;background:{WHT};z-index:65;transform:translateX(-100%);transition:transform .25s ease;box-shadow:2px 0 20px rgba(0,0,0,.14);display:flex;flex-direction:column;padding:18px 0;overflow-y:auto}}
    .nav-drawer.open{{transform:translateX(0)}}
    .nav-dh{{display:flex;justify-content:space-between;align-items:center;font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{DIM};padding:0 20px 14px;margin-bottom:6px;border-bottom:1px solid {BDR}}}
    .nav-close{{background:none;border:none;font-size:1.1rem;color:{MUT};cursor:pointer;line-height:1;padding:0}}
    .nav-link{{display:flex;align-items:center;gap:11px;padding:11px 20px;font-size:.9rem;font-weight:600;color:{TXT};cursor:pointer;border:none;background:none;width:100%;text-align:left;font-family:inherit;border-left:3px solid transparent}}
    .nav-link:hover{{background:{GRY};color:{T};border-left-color:{T}}}
    .nav-dot{{width:7px;height:7px;border-radius:50%;background:{BDR2};flex-shrink:0}}
    .nav-link:hover .nav-dot{{background:{T}}}

    /* ── Mobile bracket ── */
    .mobile-bracket{{display:none}}
    @media(max-width:900px){{
      .llaves-wrap{{display:none!important}}
      .mobile-bracket{{display:block}}
      .mb-tabs{{display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch;margin-bottom:14px;padding-bottom:4px}}
      .mb-tab{{flex-shrink:0;border:1px solid {BDR};background:{WHT};color:{MUT};font-size:.75rem;font-weight:700;padding:7px 18px;cursor:pointer;letter-spacing:.05em;text-transform:uppercase;font-family:inherit;transition:background .12s,color .12s}}
      .mb-tab.mb-active{{background:{T};color:{WHT};border-color:{T}}}
      .mb-panel .mc{{margin-bottom:8px}}
      .mb-panel .par{{display:contents}}
    }}
  </style>
</head>
<body>

<button class="navfab" onclick="toggleNav()" aria-label="Ir a sección" title="Ir a sección">&#9776;</button>
<div class="nav-overlay" id="navOverlay" onclick="closeNav()"></div>
<nav class="nav-drawer" id="navDrawer">
  <div class="nav-dh"><span>Ir a sección</span><button class="nav-close" onclick="closeNav()" aria-label="Cerrar">&#10005;</button></div>
  <div id="navLinks"></div>
  <div class="nav-foot">
    <button class="nav-link" onclick="closeNav();openSug()"><span class="nav-dot"></span>Enviar sugerencia</button>
    <div class="nav-social">
      <span class="nav-social-t">Seguinos en redes</span>
      <a class="nav-social-i" href="https://www.instagram.com/mejortercero.online" target="_blank" rel="noopener" aria-label="Instagram">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.23-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38-.16-.42-.36-1.06-.41-2.23-.06-1.27-.07-1.65-.07-4.85s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41 1.27-.06 1.65-.07 4.85-.07M12 0C8.74 0 8.33.01 7.05.07 5.78.13 4.9.33 4.14.63c-.79.3-1.46.72-2.13 1.38C1.35 2.68.93 3.35.63 4.14.33 4.9.13 5.78.07 7.05.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.27.26 2.15.56 2.91.3.79.72 1.46 1.38 2.13.67.66 1.34 1.08 2.13 1.38.76.3 1.64.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 4.95-.07c1.27-.06 2.15-.26 2.91-.56.79-.3 1.46-.72 2.13-1.38.66-.67 1.08-1.34 1.38-2.13.3-.76.5-1.64.56-2.91.06-1.28.07-1.69.07-4.95s-.01-3.67-.07-4.95c-.06-1.27-.26-2.15-.56-2.91-.3-.79-.72-1.46-1.38-2.13C21.32 1.35 20.65.93 19.86.63 19.1.33 18.22.13 16.95.07 15.67.01 15.26 0 12 0m0 5.84A6.16 6.16 0 1 0 18.16 12 6.16 6.16 0 0 0 12 5.84M12 16a4 4 0 1 1 4-4 4 4 0 0 1-4 4m6.41-10.85a1.44 1.44 0 1 0 1.44 1.44 1.44 1.44 0 0 0-1.44-1.44"/></svg>
      </a>
      <a class="nav-social-i" href="https://x.com/mejortercero" target="_blank" rel="noopener" aria-label="X">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.66l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
      </a>
    </div>
  </div>
</nav>

<div class="hdr">
  <img src="/logo.png" alt="Mejor Tercero - Mundial 2026" class="hdr-logo">
</div>

<div id="today-container">
<div class="sec" id="sec-hoy" data-nav="Partidos">
  <div style="position:relative">
    <div class="hoy-nav">
      <button class="hoy-nav-btn" id="hoy-prev" onclick="navDay(-1)">&#8249;</button>
      <p class="sec-t" id="hoy-nav-label" style="margin:0;border:none;padding-bottom:0">Partidos de hoy</p>
      <button class="hoy-nav-btn" id="hoy-next" onclick="navDay(+1)">&#8250;</button>
    </div>
    <button class="sec-toggle" id="st-hoy" onclick="toggleSec('hoy')" style="position:absolute;right:0;top:50%;transform:translateY(-50%)">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-hoy">
    <div id="today-body">{_render_today_matches(standings.get("_today_matches", []), standings)}</div>
  </div>
</div>
<div class="divider"></div>
</div>

<div class="sec" id="sec-grupos" data-nav="Posiciones">
  <div class="sec-hdr" onclick="toggleSec('grupos')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Posiciones — Fase de grupos</p>
    <button class="sec-toggle" id="st-grupos">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-grupos">
    <div class="leyenda">
      <span class="ley-item"><span class="ley-dot" style="background:{WHT};border:1px solid {BDR};border-left:3px solid {TEL}"></span>Clasifica directo</span>
      <span class="ley-item"><span class="ley-dot" style="background:{WHT};border:1px solid {BDR};border-left:3px solid {T}"></span>Mejor 3ro (top 8)</span>
      <span class="ley-item"><span class="ley-dot" style="background:{GRY};border:1px solid {BDR}"></span>Eliminado / fuera del top 8</span>
    </div>
    <div class="grupos" id="groups-inner">{_render_groups(standings, live_teams, thirds_advancing_set)}</div>
  </div>
</div>

<div class="sec" id="sec-terceros" data-nav="Mejor Tercero">
  <div class="sec-hdr" onclick="toggleSec('terceros')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Mejor Tercero — Mundial 2026</p>
    <button class="sec-toggle" id="st-terceros">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-terceros">
    <div id="thirds-inner">{_render_thirds(standings)}</div>
  </div>
</div>
<div class="divider"></div>

<div class="sec" id="sec-bracket" data-nav="Bracket">
  <div class="sec-hdr" onclick="toggleSec('bracket')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Bracket — Hacé clic para simular el avance</p>
    <button class="sec-toggle" id="st-bracket">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-bracket">
    <p class="bracket-leyenda"><span class="bl-dot"></span> <b>Proyección en vivo.</b> Los cruces se recalculan a cada gol con la tabla oficial de FIFA (Anexo C). Los equipos <i>en gris</i> son provisionales: se confirman cuando termina su grupo.</p>
    <div class="llaves-wrap">
      {_render_llaves(matchups)}
    </div>
    {_render_mobile_bracket(matchups)}
    <button class="reset-btn" onclick="resetBracket()">↺ Resetear simulación</button>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-cruces" data-nav="¿Contra quién?">
  <div class="sec-hdr" onclick="toggleSec('cruces')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">¿Contra quién? — Rival posible en 16avos</p>
    <button class="sec-toggle" id="st-cruces">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-cruces">
    <select class="cz-sel" id="cruces-sel" onchange="showCruces(this.value)" aria-label="Elegí una selección">
      <option value="">Elegí una selección…</option>
    </select>
    <div id="cruces-out"></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-goleadores" data-nav="Goleadores">
  <div class="sec-hdr" onclick="toggleSec('goleadores')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Goleadores — Mundial 2026</p>
    <button class="sec-toggle" id="st-goleadores">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-goleadores">
    <div id="scorers-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-valoracion" data-nav="Valoración">
  <div class="sec-hdr" onclick="toggleSec('valoracion')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Mejor valoración — Mundial 2026</p>
    <button class="sec-toggle" id="st-valoracion">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-valoracion">
    <div id="rating-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-asistencias" data-nav="Asistencias">
  <div class="sec-hdr" onclick="toggleSec('asistencias')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Asistencias — Mundial 2026</p>
    <button class="sec-toggle" id="st-asistencias">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-asistencias">
    <div id="assists-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-amarillas" data-nav="Tarjetas amarillas">
  <div class="sec-hdr" onclick="toggleSec('amarillas')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Tarjetas amarillas — Mundial 2026</p>
    <button class="sec-toggle" id="st-amarillas">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-amarillas">
    <div id="yellows-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-rojas" data-nav="Tarjetas rojas">
  <div class="sec-hdr" onclick="toggleSec('rojas')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Tarjetas rojas — Mundial 2026</p>
    <button class="sec-toggle" id="st-rojas">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-rojas">
    <div id="reds-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<div class="divider"></div>
<div class="sec" id="sec-estadios" data-nav="Estadios">
  <div class="sec-hdr" onclick="toggleSec('estadios')">
    <p class="sec-t" style="margin:0;border:none;padding-bottom:0">Estadios — Mundial 2026</p>
    <button class="sec-toggle" id="st-estadios">▲ CERRAR</button>
  </div>
  <div class="sec-body" id="sb-estadios">
    <div id="venues-inner"><p style="text-align:center;color:{MUT};font-size:.85rem;padding:18px 0">Cargando…</p></div>
  </div>
</div>

<!-- Sugerencias y "seguinos en redes" viven en la sidebar (nav-drawer) -->

<!-- Modal sugerencias -->
<div class="sug-overlay" id="sugOverlay" onclick="if(event.target===this)closeSug()">
  <div class="sug-modal">
    <div class="sug-header">
      <span>Envianos una sugerencia</span>
      <button onclick="closeSug()" style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:{MUT}">✕</button>
    </div>
    <div class="sug-body">
      <label class="sug-label">Tu nombre <span style="color:{DIM}">(opcional)</span></label>
      <input id="sugName" class="sug-input" type="text" placeholder="Ej: Martín" maxlength="80" autocomplete="off">
      <label class="sug-label">Sugerencia *</label>
      <textarea id="sugMsg" class="sug-input" rows="4" placeholder="¿Qué mejorarías o agregarías?" maxlength="600"></textarea>
      <button class="sug-send" id="sugBtn" onclick="sendSug()">Enviar sugerencia</button>
      <p id="sugThanks" style="display:none;color:{TEL};font-size:.8rem;margin-top:8px;font-weight:600">¡Gracias! Tu sugerencia fue enviada.</p>
      <p id="sugErr" style="display:none;color:#dc2626;font-size:.78rem;margin-top:8px"></p>
    </div>
  </div>
</div>

<style>
  .nav-foot{{margin-top:auto;padding-top:10px;border-top:1px solid {BDR}}}
  .nav-social{{display:flex;align-items:center;gap:9px;padding:11px 20px 2px}}
  .nav-social-t{{font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:{DIM}}}
  .nav-social-i{{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:{T};color:#fff;text-decoration:none;transition:opacity .15s}}
  .nav-social-i:hover{{opacity:.9}}
  .nav-social-i svg{{width:16px;height:16px}}
  .sug-overlay{{display:none;position:fixed;inset:0;background:rgba(33,28,20,.5);z-index:1000;align-items:center;justify-content:center}}
  .sug-overlay.open{{display:flex}}
  .sug-modal{{background:{WHT};width:100%;max-width:420px;margin:20px}}
  .sug-header{{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid {BDR};font-size:.82rem;font-weight:700;color:{TXT}}}
  .sug-body{{padding:18px}}
  .sug-label{{display:block;font-size:.7rem;font-weight:700;color:{DIM};letter-spacing:.08em;text-transform:uppercase;margin-bottom:5px;margin-top:12px}}
  .sug-label:first-child{{margin-top:0}}
  .sug-input{{width:100%;border:1px solid {BDR};padding:8px 10px;font-size:.82rem;font-family:inherit;color:{TXT};background:{BG};resize:vertical}}
  .sug-input:focus{{outline:1px solid {T}}}
  .sug-send{{margin-top:14px;width:100%;background:{T};color:#fff;border:none;padding:10px;font-size:.78rem;font-weight:700;cursor:pointer;letter-spacing:.06em;text-transform:uppercase}}
  .sug-send:hover{{background:#a83509}}
  .sug-send:disabled{{background:{DIM};cursor:default}}
</style>

<script>
// ── Partidos expandibles ──────────────────────────────────────────────────
function toggleMatch(el) {{ el.classList.toggle('open'); }}

// Detalle de grupo: abrir/cerrar todos los grupos de la MISMA fila a la vez
function toggleGroupRow(el) {{
  var foot = el.parentNode;
  var grupo = foot.closest('.grupo');
  if (!grupo) return;
  var willOpen = !foot.classList.contains('open');
  var top = grupo.offsetTop;
  document.querySelectorAll('#groups-inner .grupo').forEach(function(g) {{
    if (Math.abs(g.offsetTop - top) < 4) {{
      var f = g.querySelector('.grupo-foot');
      if (f) f.classList.toggle('open', willOpen);
    }}
  }});
}}

// ── Goleadores expandibles ────────────────────────────────────────────────
function toggleScorers() {{
  var extra = document.getElementById('scorers-extra');
  var btn   = document.getElementById('scorers-btn');
  if (!extra) return;
  var hidden = extra.style.display === 'none';
  extra.style.display = hidden ? '' : 'none';
  if (btn) btn.textContent = hidden ? 'Ver menos' : 'Ver todos los goleadores';
}}
function toggleList(key) {{
  var extra = document.getElementById(key + '-extra');
  var btn   = document.getElementById(key + '-btn');
  if (!extra) return;
  var hidden = extra.style.display === 'none';
  extra.style.display = hidden ? '' : 'none';
  if (btn) btn.textContent = hidden ? 'Ver menos' : (btn.getAttribute('data-more') || 'Ver todos');
}}

// ── Sugerencias → Worker ──────────────────────────────────────────────────
const SUG_API = 'https://mejortercero.online/api/suggest';
function openSug(){{ document.getElementById('sugOverlay').classList.add('open'); }}
function closeSug(){{
  document.getElementById('sugOverlay').classList.remove('open');
  document.getElementById('sugThanks').style.display='none';
  document.getElementById('sugErr').style.display='none';
}}
async function sendSug(){{
  const btn   = document.getElementById('sugBtn');
  const errEl = document.getElementById('sugErr');
  errEl.style.display = 'none';
  const msg  = document.getElementById('sugMsg').value.trim().slice(0,600);
  const name = document.getElementById('sugName').value.trim().slice(0,80);
  if (!msg) {{ errEl.textContent='El campo sugerencia no puede estar vacío.'; errEl.style.display='block'; return; }}
  btn.disabled = true; btn.textContent = 'Enviando…';
  try {{
    const res = await fetch(SUG_API, {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{ msg, name, page: window.location.pathname }}),
    }});
    const data = await res.json();
    if (!res.ok) {{ throw new Error(data.error || 'Error al enviar'); }}
    document.getElementById('sugMsg').value = '';
    document.getElementById('sugName').value = '';
    document.getElementById('sugThanks').style.display = 'block';
    setTimeout(closeSug, 2000);
  }} catch(e) {{
    errEl.textContent = e.message || 'Error de red. Intentá de nuevo.';
    errEl.style.display = 'block';
  }} finally {{
    btn.disabled = false; btn.textContent = 'Enviar sugerencia';
  }}
}}
</script>

<script>
// ── Datos ──────────────────────────────────────────────────────────────────
const KO_SCHED = {ko_json};

// ── Formateo de fecha (hora local del usuario) ────────────────────────────
function fmtDate(utcStr) {{
  if (!utcStr) return 'Por confirmar';
  const d = new Date(utcStr);
  try {{
    return new Intl.DateTimeFormat('es-AR', {{
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      weekday:'short', day:'numeric', month:'short',
      hour:'2-digit', minute:'2-digit', hour12:false
    }}).format(d);
  }} catch(e) {{
    return new Intl.DateTimeFormat('es-AR', {{
      timeZone: 'America/Argentina/Buenos_Aires',
      weekday:'short', day:'numeric', month:'short',
      hour:'2-digit', minute:'2-digit', hour12:false
    }}).format(d);
  }}
}}
function fmtTime(utcStr) {{
  if (!utcStr) return '';
  const d = new Date(utcStr);
  try {{
    return new Intl.DateTimeFormat('es-AR', {{
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      hour:'2-digit', minute:'2-digit', hour12:false
    }}).format(d);
  }} catch(e) {{
    return new Intl.DateTimeFormat('es-AR', {{
      timeZone: 'America/Argentina/Buenos_Aires',
      hour:'2-digit', minute:'2-digit', hour12:false
    }}).format(d);
  }}
}}
function fmtShortDate(utcStr) {{
  if (!utcStr) return '';
  const d = new Date(utcStr);
  const o = {{ day:'2-digit', month:'2-digit' }};
  try {{
    return new Intl.DateTimeFormat('es-AR', {{ timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, ...o }}).format(d);
  }} catch(e) {{
    return new Intl.DateTimeFormat('es-AR', {{ timeZone: 'America/Argentina/Buenos_Aires', ...o }}).format(d);
  }}
}}

// ── State ──────────────────────────────────────────────────────────────────
let S = {{}};
function load() {{ try {{ S = JSON.parse(localStorage.getItem('wc26') || '{{}}'); }} catch(e) {{ S={{}}; }} }}
function save() {{ localStorage.setItem('wc26', JSON.stringify(S)); }}

// ── Feed map (src → {{next_slot, position}}) ───────────────────────────────
const FEED = {{
  "74":{{next:"r16-L-0",pos:0}}, "77":{{next:"r16-L-0",pos:1}},  // → P89
  "73":{{next:"r16-L-1",pos:0}}, "75":{{next:"r16-L-1",pos:1}},  // → P90
  "83":{{next:"r16-L-2",pos:0}}, "84":{{next:"r16-L-2",pos:1}},  // → P93
  "81":{{next:"r16-L-3",pos:0}}, "82":{{next:"r16-L-3",pos:1}},  // → P94
  "76":{{next:"r16-R-0",pos:0}}, "78":{{next:"r16-R-0",pos:1}},  // → P91
  "79":{{next:"r16-R-1",pos:0}}, "80":{{next:"r16-R-1",pos:1}},  // → P92
  "86":{{next:"r16-R-2",pos:0}}, "88":{{next:"r16-R-2",pos:1}},  // → P95
  "85":{{next:"r16-R-3",pos:0}}, "87":{{next:"r16-R-3",pos:1}},  // → P96
  "r16-L-0":{{next:"qf-L-0",pos:0}}, "r16-L-1":{{next:"qf-L-0",pos:1}},
  "r16-L-2":{{next:"qf-L-1",pos:0}}, "r16-L-3":{{next:"qf-L-1",pos:1}},
  "r16-R-0":{{next:"qf-R-0",pos:0}}, "r16-R-1":{{next:"qf-R-0",pos:1}},
  "r16-R-2":{{next:"qf-R-1",pos:0}}, "r16-R-3":{{next:"qf-R-1",pos:1}},
  "qf-L-0": {{next:"sf-L-0",pos:0}}, "qf-L-1": {{next:"sf-L-0",pos:1}},
  "qf-R-0": {{next:"sf-R-0",pos:0}}, "qf-R-1": {{next:"sf-R-0",pos:1}},
  "sf-L-0": {{next:"slot-final",pos:0}},
  "sf-R-0": {{next:"slot-final",pos:1}},
}};

const SLOT_ORDER = [
  "r16-L-0","r16-L-1","r16-L-2","r16-L-3",
  "r16-R-0","r16-R-1","r16-R-2","r16-R-3",
  "qf-L-0","qf-L-1","qf-R-0","qf-R-1",
  "sf-L-0","sf-R-0","slot-final","slot-tercer"
];

const SLOT_LABEL = {{
  "r16-L-0":"P89","r16-L-1":"P90","r16-L-2":"P93","r16-L-3":"P94",
  "r16-R-0":"P91","r16-R-1":"P92","r16-R-2":"P95","r16-R-3":"P96",
  "qf-L-0":"P97","qf-L-1":"P98","qf-R-0":"P99","qf-R-1":"P100",
  "sf-L-0":"P101","sf-R-0":"P102",
}};

function feedersOf(slotId) {{
  return Object.entries(FEED)
    .filter(([,v]) => v.next === slotId)
    .sort((a,b) => a[1].pos - b[1].pos)
    .map(([k]) => k);
}}
function getWinner(srcId) {{ return S[srcId]?.winner || null; }}

// ── Render de un slot de ronda posterior ──────────────────────────────────
function renderSlot(slotId) {{
  if (slotId === "slot-final") {{ renderFinal(); return; }}
  if (slotId === "slot-tercer") {{ renderTercer(); return; }}
  const el = document.getElementById(slotId);
  if (!el) return;

  const [src0, src1] = feedersOf(slotId);
  const t0 = getWinner(src0);
  const t1 = getWinner(src1);
  const myW = S[slotId]?.winner;
  const lbl = SLOT_LABEL[slotId] || "";
  const ks = KO_SCHED[slotId];
  const dateHtml = ks ? `<span>${{fmtDate(ks[0])}}</span>` : '<span>Por confirmar</span>';
  const venueHtml = ks ? `<span class="venue">${{ks[1]}}</span>` : '';

  const mkRow = (t, idx) => {{
    if (!t) return `<div class="team-row ph">— Por definir</div>`;
    const src = idx===0 ? src0 : src1;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner" : isL ? "loser" : "";
    return `<div class="team-row ${{cls}} fade-in"
      data-slot="${{slotId}}" data-src="${{src}}" data-name="${{t.name}}"
      data-html="${{encodeURIComponent(t.html)}}"
      onclick="pickSlotWinner(this)">${{t.html}}</div>`;
  }};

  el.innerHTML = `
    <div class="mc-label"><span>${{lbl}}</span></div>
    ${{mkRow(t0,0)}}${{mkRow(t1,1)}}
    <div class="mc-meta">${{dateHtml}}${{venueHtml}}</div>`;
  el.className = "mc";

  // Si es SF y ya hay ganador pero ahora llegó el 2do equipo → calcular loser automáticamente
  if ((slotId === "sf-L-0" || slotId === "sf-R-0") && S[slotId]?.winner && t0 && t1) {{
    const winName = S[slotId].winner.name;
    const loserT  = t0.name === winName ? t1 : t0;
    if (!S[slotId].loser || S[slotId].loser.name !== loserT.name) {{
      S[slotId].loser = loserT;
      save();
      renderTercer();
    }}
  }}
}}

// ── Final ─────────────────────────────────────────────────────────────────
function renderFinal() {{
  const el = document.getElementById("slot-final");
  if (!el) return;
  const [src0, src1] = feedersOf("slot-final");
  const t0 = getWinner(src0), t1 = getWinner(src1);
  const myW = S["slot-final"]?.winner;

  const mkRow = (t, idx) => {{
    if (!t) return `<div class="team-row ph" style="justify-content:center">— Por definir</div>`;
    const src = idx===0 ? src0 : src1;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner champion" : isL ? "loser" : "";
    return `<div class="team-row ${{cls}} fade-in" style="justify-content:center"
      data-slot="slot-final" data-src="${{src}}" data-name="${{t.name}}"
      data-html="${{encodeURIComponent(t.html)}}"
      onclick="pickSlotWinner(this)">${{t.html}}</div>`;
  }};

  // Team rows
  el.innerHTML = mkRow(t0,0) + mkRow(t1,1);

  // Cuadro campeón separado (champ-card)
  const champCard = document.getElementById('champ-card');
  if (champCard) {{
    if (myW) {{
      const tmp = document.createElement('div');
      tmp.innerHTML = myW.html;
      const origImg = tmp.querySelector('img');
      const translatedName = tmp.textContent.trim();
      const flagEl = document.getElementById('champ-flag');
      flagEl.innerHTML = '';
      if (origImg) {{
        const newImg = new Image(48, 36);
        newImg.src = origImg.src.replace('/20x15/','/48x36/');
        newImg.setAttribute('style','display:block;margin:0 auto;image-rendering:crisp-edges');
        flagEl.appendChild(newImg);
      }}
      document.getElementById('champ-country').textContent = translatedName || myW.name;
      champCard.style.display = '';
      champCard.classList.remove('fade-in');
      void champCard.offsetWidth;
      champCard.classList.add('fade-in');
    }} else {{
      champCard.style.display = 'none';
    }}
  }}
}}

// ── 3er puesto ────────────────────────────────────────────────────────────
function renderTercer() {{
  const el = document.getElementById("slot-tercer");
  if (!el) return;
  const t0 = S["sf-L-0"]?.loser || null;
  const t1 = S["sf-R-0"]?.loser || null;
  const myW = S["slot-tercer"]?.winner;

  const mkRow = (t, sfSrc) => {{
    if (!t) return `<div class="team-row ph" style="justify-content:center">— Por definir</div>`;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner" : isL ? "loser" : "";
    return `<div class="team-row ${{cls}} fade-in" style="justify-content:center"
      data-slot="slot-tercer" data-name="${{t.name}}"
      data-html="${{encodeURIComponent(t.html)}}"
      onclick="pickTercerWinner(this)">${{t.html}}</div>`;
  }};

  // el IS the .tercer-teams div directly
  el.innerHTML = mkRow(t0,"sf-L-0") + mkRow(t1,"sf-R-0");
}}

// ── Seleccionar ganador en R32 ────────────────────────────────────────────
function pickWinner(el) {{
  const card = el.closest(".mc");
  const mid = card.dataset.mid;
  const name = el.dataset.name;
  const html = decodeURIComponent(el.dataset.html);

  // Update all cards with same mid (desktop + mobile)
  document.querySelectorAll('[data-mid="' + mid + '"]').forEach(function(c) {{
    c.querySelectorAll(".team-row").forEach(function(r) {{
      r.classList.remove("winner","loser");
      r.classList.add(r.dataset.name === name ? "winner" : "loser");
    }});
  }});

  S[mid] = {{ winner: {{name, html}} }};
  save();
  propagate(mid);
  syncMobile();
}}

// ── Seleccionar ganador en slots R16/QF/SF/Final ──────────────────────────
function pickSlotWinner(el) {{
  const slotId = el.dataset.slot;
  const name   = el.dataset.name;
  const html   = decodeURIComponent(el.dataset.html);

  const slotEl = document.getElementById(slotId);
  slotEl.querySelectorAll(".team-row").forEach(r => {{
    if (!r.dataset.name) return;
    r.classList.remove("winner","loser","champion");
    r.classList.add(r.dataset.name === name ? "winner" : "loser");
  }});

  // Si es una SF, guardar también el perdedor para el 3er puesto
  if (slotId === "sf-L-0" || slotId === "sf-R-0") {{
    const rows = [...slotEl.querySelectorAll(".team-row[data-name]")];
    const loserRow = rows.find(r => r.dataset.name !== name);
    const loserName = loserRow?.dataset.name;
    const loserHtml = loserRow ? decodeURIComponent(loserRow.dataset.html) : null;
    // Si el loserRow no existe aún (2do equipo no llegó), usar el valor ya guardado si hay
    const prevLoser = !loserName ? (S[slotId]?.loser || null) : null;
    S[slotId] = {{ winner: {{name, html}}, loser: loserName ? {{name: loserName, html: loserHtml}} : prevLoser }};
  }} else {{
    S[slotId] = {{ winner: {{name, html}} }};
  }}

  save();
  if (slotId !== "slot-final") propagate(slotId);
  renderFinal();
  renderTercer();
  syncMobile();
}}

function pickTercerWinner(el) {{
  const name = el.dataset.name;
  const html = decodeURIComponent(el.dataset.html);
  const slotEl = document.getElementById("slot-tercer");
  slotEl.querySelectorAll(".team-row[data-name]").forEach(r => {{
    r.classList.remove("winner","loser");
    r.classList.add(r.dataset.name === name ? "winner" : "loser");
  }});
  S["slot-tercer"] = {{ winner: {{name, html}} }};
  save();
  syncMobile();
}}

// ── Propagación ───────────────────────────────────────────────────────────
function propagate(srcId) {{
  const next = FEED[srcId]?.next;
  if (!next) return;
  if (S[next]?.winner) {{
    const [s0,s1] = feedersOf(next);
    const w0 = getWinner(s0), w1 = getWinner(s1);
    if (S[next].winner.name !== w0?.name && S[next].winner.name !== w1?.name) {{
      delete S[next].winner;
      if (next === "sf-L-0" || next === "sf-R-0") delete S[next].loser;
      save();
      propagate(next);
    }}
  }}
  renderSlot(next);
}}

// ── Restaurar al cargar ───────────────────────────────────────────────────
function restore() {{
  document.querySelectorAll("[data-mid]").forEach(card => {{
    const mid = card.dataset.mid;
    const w = S[mid]?.winner;
    if (!w) return;
    card.querySelectorAll(".team-row[data-name]").forEach(r => {{
      r.classList.remove("winner","loser");
      r.classList.add(r.dataset.name === w.name ? "winner" : "loser");
    }});
  }});
  SLOT_ORDER.forEach(id => renderSlot(id));
  syncMobile();
}}

function resetBracket() {{
  S = {{}};
  save();
  document.querySelectorAll("[data-mid] .team-row").forEach(r =>
    r.classList.remove("winner","loser"));
  SLOT_ORDER.forEach(id => renderSlot(id));
  syncMobile();
}}

// ── Sincronizar mobile bracket con estado desktop ─────────────────────────
function syncMobile() {{
  ["r16-L-0","r16-L-1","r16-L-2","r16-L-3",
   "r16-R-0","r16-R-1","r16-R-2","r16-R-3",
   "qf-L-0","qf-L-1","qf-R-0","qf-R-1",
   "sf-L-0","sf-R-0"].forEach(function(id) {{
    var d = document.getElementById(id);
    var m = document.getElementById('m-' + id);
    if (d && m) {{ m.innerHTML = d.innerHTML; m.className = d.className; }}
  }});
  var df = document.getElementById('slot-final');
  var mfr = document.getElementById('m-final-rows');
  if (df && mfr) {{ mfr.innerHTML = df.innerHTML; }}
  var dt = document.getElementById('slot-tercer');
  var mtr = document.getElementById('m-tercer-rows');
  if (dt && mtr) {{ mtr.innerHTML = dt.innerHTML; }}
}}

// ── Tabs del bracket mobile ───────────────────────────────────────────────
function mbSetRound(btn, round) {{
  document.querySelectorAll('.mb-tab').forEach(function(t) {{ t.classList.remove('mb-active'); }});
  btn.classList.add('mb-active');
  document.querySelectorAll('.mb-panel').forEach(function(p) {{ p.style.display = 'none'; }});
  var panel = document.getElementById('mb-' + round);
  if (panel) {{ panel.style.display = 'block'; }}
}}

// ── Polling de datos en vivo (sin recarga de página) ─────────────────────
function applyDataUtc(root) {{
  (root || document).querySelectorAll('[data-utc]').forEach(function(el) {{
    el.innerHTML = el.dataset.format === 'time' ? fmtTime(el.dataset.utc)
                 : el.dataset.format === 'shortdate' ? fmtShortDate(el.dataset.utc)
                 : fmtDate(el.dataset.utc);
  }});
}}

// ── Navegación de días ────────────────────────────────────────────────────
var _navDatesHtml = {{}};
var _navDates = [];
var _navIdx = 0;
var _navTodayStr = '';

function navInit(todayStr, datesHtml) {{
  _navDatesHtml = datesHtml;
  _navDates = Object.keys(datesHtml).sort();
  var ti = _navDates.indexOf(todayStr);
  var prevTodayIdx = _navDates.indexOf(_navTodayStr);
  var wasOnToday = (_navTodayStr === '' || _navIdx === prevTodayIdx);
  _navTodayStr = todayStr;
  if (wasOnToday) _navIdx = ti >= 0 ? ti : 0;
  navRender();
}}

function navDay(delta) {{
  var next = _navIdx + delta;
  if (next < 0 || next >= _navDates.length) return;
  _navIdx = next;
  navRender();
}}

function navRender() {{
  if (!_navDates.length) return;
  var todayIdx = _navDates.indexOf(_navTodayStr);
  var diff = _navIdx - todayIdx;
  var label = diff === 0 ? 'Partidos de hoy'
            : diff === -1 ? 'Partidos de ayer'
            : diff === 1 ? 'Partidos de mañana'
            : 'Partidos del ' + _navDates[_navIdx];
  var labelEl = document.getElementById('hoy-nav-label');
  if (labelEl) labelEl.textContent = label;
  var body = document.getElementById('today-body');
  if (body) {{ body.innerHTML = _navDatesHtml[_navDates[_navIdx]] || ''; applyDataUtc(body); }}
  var prev = document.getElementById('hoy-prev');
  var next = document.getElementById('hoy-next');
  if (prev) prev.disabled = (_navIdx === 0);
  if (next) next.disabled = (_navIdx === _navDates.length - 1);
}}

// ── Secciones colapsables ─────────────────────────────────────────────────
var SEC = {{}};
function loadSecs() {{ try {{ SEC = JSON.parse(localStorage.getItem('sec_states') || '{{}}'); }} catch(e) {{ SEC={{}}; }} }}
function saveSecs() {{ localStorage.setItem('sec_states', JSON.stringify(SEC)); }}
function toggleSec(id) {{
  var body = document.getElementById('sb-' + id);
  var btn  = document.getElementById('st-' + id);
  if (!body) return;
  var collapsed = body.classList.toggle('sec-collapsed');
  if (btn) btn.textContent = collapsed ? '▼ ABRIR' : '▲ CERRAR';
  SEC[id] = collapsed;
  saveSecs();
}}
function restoreSecs() {{
  loadSecs();
  Object.keys(SEC).forEach(function(id) {{
    if (SEC[id]) {{
      var body = document.getElementById('sb-' + id);
      var btn  = document.getElementById('st-' + id);
      if (body) body.classList.add('sec-collapsed');
      if (btn) btn.textContent = '▼ ABRIR';
    }}
  }});
}}

// ── Sidebar de navegación ─────────────────────────────────────────────────
function toggleNav() {{
  document.getElementById('navDrawer').classList.toggle('open');
  document.getElementById('navOverlay').classList.toggle('open');
}}
function closeNav() {{
  document.getElementById('navDrawer').classList.remove('open');
  document.getElementById('navOverlay').classList.remove('open');
}}
// Arma el menú "Ir a sección" a partir de las secciones presentes en la página.
// Cualquier sección nueva con el atributo data-nav aparece sola, sin tocar el menú.
function buildNav() {{
  var box = document.getElementById('navLinks');
  if (!box) return;
  var secs = document.querySelectorAll('.sec[data-nav]');
  var html = '';
  secs.forEach(function(s) {{
    var key = s.id.replace(/^sec-/, '');
    var label = s.getAttribute('data-nav') || key;
    html += '<button class="nav-link" onclick="navGo(\\'' + key + '\\')">'
          + '<span class="nav-dot"></span>' + label + '</button>';
  }});
  box.innerHTML = html;
}}

function navGo(secId) {{
  closeNav();
  var body = document.getElementById('sb-' + secId);
  if (body && body.classList.contains('sec-collapsed')) {{
    body.classList.remove('sec-collapsed');
    var btn = document.getElementById('st-' + secId);
    if (btn) btn.textContent = '▲ CERRAR';
    SEC[secId] = false; saveSecs();
  }}
  var target = document.getElementById('sec-' + secId);
  if (target) setTimeout(function() {{ target.scrollIntoView({{behavior: 'smooth', block: 'start'}}); }}, 60);
}}

// ── Marcadores en vivo (cada 8s, vía el Worker — mucho más rápido que data.json) ──
function pollLive() {{
  fetch('/api/live')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      (d.matches || []).forEach(function(m) {{
        var card = document.querySelector('.hoy-fila[data-mid="' + m.id + '"]');
        if (!card) return;
        // Marcador: si la tarjeta ya está en vivo, actualizar; si estaba por jugarse, pasarla a vivo
        var sc = card.querySelector('.hoy-score');
        var centro = card.querySelector('.hoy-centro');
        if (sc && m.h != null) {{
          sc.textContent = m.h + ' - ' + m.a;
        }} else if (centro && m.h != null) {{
          centro.innerHTML = '<span class="hoy-score">' + m.h + ' - ' + m.a + '</span>';
        }}
        // Badge EN VIVO: crearlo si no existe (transición rápida sin esperar a /api/data)
        var head = card.querySelector('.hoy-head');
        var chev = head ? head.querySelector('.hoy-chev') : null;
        if (head && chev && !head.querySelector('.hoy-badge-live') && !head.querySelector('.hoy-badge-fin')) {{
          var b = document.createElement('span');
          b.className = 'hoy-badge-live';
          b.innerHTML = (m.status === 'HT')
            ? '<span class="dot"></span>ENT'
            : '<span class="dot"></span>EN VIVO <span class="hoy-min"></span>';
          head.insertBefore(b, chev);
        }}
        var mn = card.querySelector('.hoy-min');
        if (mn && m.elapsed != null && m.status !== 'HT') mn.textContent = m.elapsed + "'";
      }});
    }})
    .catch(function() {{}});
}}

function pollData() {{
  fetch('/api/data')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      var gi = document.getElementById('groups-inner');
      if (gi && d.groups_html !== undefined) gi.innerHTML = d.groups_html;

      var ti = document.getElementById('thirds-inner');
      if (ti && d.thirds_html !== undefined) ti.innerHTML = d.thirds_html;

      if (d.dates_html !== undefined && d.today_date !== undefined) {{
        navInit(d.today_date, d.dates_html);
      }}

      var r32Updated = false;
      var rl = document.getElementById('r32-left');
      if (rl && d.r32_left_html !== undefined) {{
        rl.innerHTML = d.r32_left_html; applyDataUtc(rl); r32Updated = true;
      }}
      var rr = document.getElementById('r32-right');
      if (rr && d.r32_right_html !== undefined) {{
        rr.innerHTML = d.r32_right_html; applyDataUtc(rr); r32Updated = true;
      }}
      var mbR32 = document.getElementById('mb-r32');
      if (mbR32 && d.r32_left_html !== undefined && d.r32_right_html !== undefined) {{
        mbR32.innerHTML = d.r32_left_html + d.r32_right_html;
        applyDataUtc(mbR32);
      }}
      if (r32Updated) {{ restore(); initPath(); }}

      var si = document.getElementById('scorers-inner');
      if (si && d.scorers_html !== undefined) si.innerHTML = d.scorers_html;

      var rti = document.getElementById('rating-inner');
      if (rti && d.rating_html !== undefined) rti.innerHTML = d.rating_html;

      var ai = document.getElementById('assists-inner');
      if (ai && d.assists_html !== undefined) ai.innerHTML = d.assists_html;

      var yi = document.getElementById('yellows-inner');
      if (yi && d.yellows_html !== undefined) yi.innerHTML = d.yellows_html;

      var rdi = document.getElementById('reds-inner');
      if (rdi && d.reds_html !== undefined) rdi.innerHTML = d.reds_html;

      var upd = document.getElementById('upd');
      if (upd && d.updated) upd.textContent = d.updated;
    }})
    .catch(function(e) {{ console.warn('[poll]', e); }});
}}

// Rankings (valoración/goleadores/asist/tarjetas) — carga diferida desde /api/data2
// para no pesar el primer pintado. No es data en vivo; refresca en un timer lento.
function loadExtra() {{
  fetch('/api/data2')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      // Rellenar UNA sección por frame (cediendo el hilo entre cada una) para que
      // aparezcan progresivas SIN bloquear la navegación con un innerHTML gigante.
      var jobs = [['scorers-inner','scorers_html'],['rating-inner','rating_html'],
                  ['assists-inner','assists_html'],['yellows-inner','yellows_html'],
                  ['reds-inner','reds_html'],['venues-inner','venues_html']];
      var i = 0;
      function step() {{
        if (i >= jobs.length) return;
        var id = jobs[i][0], key = jobs[i][1], el = document.getElementById(id);
        if (el && d[key] !== undefined) {{
          // Estadios: no pisar una tarjeta que el usuario tenga abierta.
          if (id !== 'venues-inner' || !el.querySelector('.hoy-fila.open')) {{
            el.innerHTML = d[key];
            if (id === 'venues-inner') applyDataUtc(el);
          }}
        }}
        i++;
        requestAnimationFrame(step);
      }}
      requestAnimationFrame(step);
    }})
    .catch(function() {{}});
}}

// ── ¿Contra quién? — sección del home con selector (carga bajo demanda) ─────
var _cruces = null, _crucesLoading = false;
function loadCruces() {{
  if (_cruces || _crucesLoading) return;
  _crucesLoading = true;
  fetch('/api/cruces')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      _cruces = d;
      var sel = document.getElementById('cruces-sel');
      if (sel) {{
        Object.keys(d).sort(function(a,b){{ return a.localeCompare(b,'es'); }}).forEach(function(name) {{
          var o = document.createElement('option');
          o.value = name; o.textContent = name; sel.appendChild(o);
        }});
      }}
    }})
    .catch(function() {{ _crucesLoading = false; }});
}}
function showCruces(name) {{
  var out = document.getElementById('cruces-out');
  if (out) out.innerHTML = (name && _cruces && _cruces[name]) ? _cruces[name] : '';
}}

// ── Bracket responsivo: escalar para caber en pantalla ────────────────────
function scaleBracket() {{
  var wrap = document.querySelector('.llaves-wrap');
  var ll   = document.querySelector('.llaves');
  if (!wrap || !ll) return;
  ll.style.transform = '';
  wrap.style.height  = '';
  var avail = wrap.clientWidth;
  var nat   = ll.scrollWidth;
  if (nat > avail && avail > 0) {{
    var s = avail / nat;
    ll.style.transform       = 'scale(' + s + ')';
    ll.style.transformOrigin = 'top left';
    wrap.style.height        = Math.ceil(ll.scrollHeight * s) + 'px';
  }}
}}

// ── 4.1 · Camino al título: ilumina la recorrida de un cruce hasta la final ──
function pathFrom(id) {{
  const path = [id]; let cur = id;
  while (FEED[cur]) {{ cur = FEED[cur].next; path.push(cur); }}
  return path;
}}
function clearPath() {{
  document.querySelectorAll('.mc.on-path').forEach(e => e.classList.remove('on-path'));
}}
function highlightPath(id) {{
  clearPath();
  pathFrom(id).forEach(n => {{
    document.querySelectorAll('.mc[data-mid="' + n + '"]').forEach(c => c.classList.add('on-path'));
    const el = document.getElementById(n);
    if (el && el.classList.contains('mc')) el.classList.add('on-path');
  }});
}}
function initPath() {{
  document.querySelectorAll('.llaves-wrap .mc').forEach(card => {{
    const id = card.dataset.mid || card.id;
    if (!id || !FEED[id]) return;
    card.onmouseenter = function() {{ highlightPath(id); }};
    card.onmouseleave = clearPath;
  }});
}}

// ── 5.5 · Filtro de ranking por selección ─────────────────────────────────
function filterRank(sel) {{
  var team = sel.value;
  var wrap = sel.closest('.rank-wrap');
  if (!wrap) return;
  var key = sel.dataset.key;
  var extra = document.getElementById(key + '-extra');
  var btn = document.getElementById(key + '-btn');
  if (team) {{                       // al filtrar, mostramos toda la lista
    if (extra) extra.style.display = '';
    if (btn) btn.style.display = 'none';
  }} else {{
    if (extra) extra.style.display = 'none';
    if (btn) btn.style.display = '';
  }}
  wrap.querySelectorAll('tr[data-team]').forEach(function(r) {{
    r.style.display = (!team || r.dataset.team === team) ? '' : 'none';
  }});
}}

document.addEventListener("DOMContentLoaded", function() {{
  load(); restore(); restoreSecs();
  buildNav();
  applyDataUtc();
  scaleBracket();
  initPath();
  window.addEventListener('resize', scaleBracket);
  pollData();
  setInterval(pollData, 30000);
  pollLive();
  setInterval(pollLive, 8000);
  // Rankings: diferidos tras el primer pintado + refresco lento (no son data en vivo)
  setTimeout(loadExtra, 60);
  setInterval(loadExtra, 120000);
  // ¿Contra quién?: cargar el selector cuando la sección se acerca al viewport
  var secCz = document.getElementById('sec-cruces');
  if (secCz && 'IntersectionObserver' in window) {{
    var obs = new IntersectionObserver(function(ents) {{
      if (ents[0].isIntersecting) {{ loadCruces(); obs.disconnect(); }}
    }}, {{ rootMargin: '400px' }});
    obs.observe(secCz);
  }} else {{
    setTimeout(loadCruces, 2000);
  }}
}});

// ── 4.3 · Modal head-to-head ──────────────────────────────────────────────
function showH2H(btn) {{
  var data = btn.closest('.mc').querySelector('.mc-h2h');
  if (!data) return;
  document.getElementById('h2hTitle').textContent = data.dataset.title;
  document.getElementById('h2hBody').innerHTML = data.innerHTML;
  document.getElementById('h2hModal').classList.add('open');
}}
function closeH2H() {{ document.getElementById('h2hModal').classList.remove('open'); }}
</script>
<div class="h2h-overlay" id="h2hModal" onclick="if(event.target===this)closeH2H()">
  <div class="h2h-modal">
    <div class="h2h-head"><span id="h2hTitle"></span><button class="h2h-x" onclick="closeH2H()">&times;</button></div>
    <div class="h2h-sub">Últimos enfrentamientos</div>
    <div id="h2hBody"></div>
  </div>
</div>
</body>
</html>"""


# ── Grupos ─────────────────────────────────────────────────────────────────

def _group_detalles_html(label: str, teams: list, stats: dict, matches: list,
                         standings: Dict, sc: dict, done: bool) -> str:
    """Filas de 'Detalles' del grupo: ritmo de gol, goleador, valla, partidazo,
    definición y a dónde van el 1.º y el 2.º en 16avos. Todo de data ya disponible."""
    bits = []  # (clave, valor_html)

    played = [m for m in matches if m.played]
    if played:
        gf_total = sum(m.home_goals + m.away_goals for m in played)
        bits.append(("Ritmo", f"{gf_total} goles · {gf_total / len(played):.1f} por partido"))

    # Goleador del grupo (los goleadores vienen de football-data → matchear por nombre_es;
    # la bandera sale del equipo del GRUPO que matchea, que es nombre API válido para bandera_img)
    es_to_team = {nombre_es(t): t for t in teams}
    best_sc, best_team = None, None
    for p in standings.get("_scorers", []):
        es = nombre_es(p.get("team", ""))
        if (p.get("goals") or 0) > 0 and es in es_to_team:
            if best_sc is None or p["goals"] > best_sc["goals"]:
                best_sc, best_team = p, es_to_team[es]
    if best_sc:
        flag = bandera_img(best_team)
        flag = f'{flag} ' if flag else ''
        bits.append(("Goleador del grupo",
                     f'{flag}{best_sc["name"]} <span class="gd-hl">{best_sc["goals"]}</span>'))

    # Valla menos vencida (entre los que ya jugaron)
    played_st = [(t, stats[t]) for t in teams if t in stats and stats[t].played > 0]
    if played_st:
        bt, bs = min(played_st, key=lambda x: (x[1].goals_against, -x[1].played))
        bits.append(("Valla menos vencida", f'{traducir(bt)} · {bs.goals_against} GC'))

    # El partidazo / goleada (partido jugado con más goles del grupo)
    if played:
        top = max(played, key=lambda m: (m.home_goals + m.away_goals, abs(m.home_goals - m.away_goals)))
        margin = abs(top.home_goals - top.away_goals)
        if (top.home_goals + top.away_goals) >= 4 or margin >= 3:
            k = "Goleada" if margin >= 3 else "El partidazo"
            bits.append((k, f'{traducir(top.home)} {top.home_goals}-{top.away_goals} {traducir(top.away)}'))

    # Definición del grupo
    if done:
        bits.append(("Definición", "Grupo cerrado"))
    elif sc:
        clinch1 = [t for t in teams if sc.get(t, {}).get("first") == "clinched1"]
        can_first = [t for t in teams if 1 in sc.get(t, {}).get("positions", [])]
        if clinch1:
            bits.append(("Definición", f'{traducir(clinch1[0])} ya es 1.º'))
        elif len(can_first) >= 2:
            bits.append(("Definición", f'<span class="gd-hl">{len(can_first)}</span> pelean el 1.º'))

    # A dónde van el 1.º y el 2.º en 16avos (sedes fijas del fixture)
    d1, d2 = r32_destination(label, 1), r32_destination(label, 2)
    if d1 and d2:
        bits.append(("En 16avos",
                     f'1.º → <span class="gd-hl">{d1["city"]}</span> (vs {d1["rival"]}) · '
                     f'2.º → <span class="gd-hl">{d2["city"]}</span>'))

    if not bits:
        return ""
    rows = "".join(f'<div class="gd-row"><span class="gd-k">{k}</span>'
                   f'<span class="gd-v">{v}</span></div>' for k, v in bits)
    return f'<div class="gd">{rows}</div>'


def _render_groups(standings: Dict, live_teams: Set[str], thirds_advancing_set: Set[str]) -> str:
    html = ""
    for gname, data in sorted(standings.items()):
        if gname.startswith("_"): continue
        teams   = data.get("teams", [])
        stats   = data.get("stats", {})
        matches = data.get("matches", [])
        done    = _done(matches)
        is_live = _live(matches)
        label   = gname.replace("GROUP_", "")

        if is_live:
            badge = '<span class="badge b-live"><span class="dot"></span>En vivo</span>'
        elif done:
            badge = '<span class="badge b-ok">Finalizado</span>'
        else:
            badge = '<span class="badge b-vivo">En curso</span>'

        filas = ""
        for pos, team in enumerate(teams, 1):
            s = stats.get(team)
            if not s: continue
            if pos <= 2:
                cls = "clasifica"
            elif pos == 3:
                cls = "tercero" if team in thirds_advancing_set else "eliminado"
            else:
                cls = "eliminado"

            is_live_team = team in live_teams
            if is_live_team: cls += " live-row"
            dg = (f'<span class="dg-p">{s.goal_diff:+d}</span>' if s.goal_diff > 0
                  else f'<span class="dg-n">{s.goal_diff:+d}</span>' if s.goal_diff < 0
                  else "0")
            name_inner = f'<span class="live-name">{traducir(team)}</span>' if is_live_team else traducir(team)
            team_q = urllib.parse.quote(team)
            name_html = f'<a class="team-link" href="/seleccion.html?t={team_q}">{name_inner}</a>'
            filas += f"""
        <tr class="{cls}">
          <td>{pos}</td><td>{name_html}</td>
          <td>{s.played}</td><td>{s.won}</td><td>{s.drawn}</td><td>{s.lost}</td>
          <td>{s.goals_for}</td><td>{s.goals_against}</td>
          <td>{dg}</td><td><span class="pts">{s.points}</span></td>
        </tr>"""
        # 2.5 / 2.1 / 3.1 — Detalles del grupo + qué se juega CADA equipo
        sc = compute_group_scenarios(teams, matches) if not done else {}
        detalles_html = _group_detalles_html(label, teams, stats, matches, standings, sc, done)
        esc_html = ""
        if sc:
            rows_e = "".join(
                f'<div class="gf-row"><span class="gf-tm">{traducir(t)}</span>'
                f'<span class="gf-ph">'
                f'{team_phrase(sc[t], opponent=(traducir(_opp_name(sc[t])) or None))}</span></div>'
                for t in teams if t in sc
            )
            if rows_e:
                esc_html = f'<div class="gf-esc"><div class="gf-cap">Qué se juega</div>{rows_e}</div>'
        # detalle del grupo plegable ("Detalles"), cerrado por defecto
        body_inner = detalles_html + esc_html
        foot = (f'<div class="grupo-foot">'
                f'<div class="gf-toggle" onclick="toggleGroupRow(this)">'
                f'<span class="gf-toggle-t">Detalles</span><span class="gf-chev">&#9662;</span></div>'
                f'<div class="gf-body">{body_inner}</div></div>') if body_inner else ""
        html += f"""
  <div class="grupo">
    <div class="grupo-h"><span class="grupo-t">Grupo {label}</span>{badge}</div>
    <table>
      <thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DG</th><th>Pts</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>{foot}
  </div>"""
    return html


# ── Mejores terceros ────────────────────────────────────────────────────────

def _render_thirds(standings: Dict) -> str:
    thirds = standings.get("_thirds_ranked", [])
    if not thirds:
        return f'<p style="font-size:.75rem;color:{MUT};margin-top:4px">Disponible al completarse la primera ronda de grupos.</p>'
    filas = ""
    for i, entry in enumerate(thirds, 1):
        s = entry["stats"]
        adv = i <= 8
        cls = "clasifica" if adv else "eliminado"
        dg  = (f'<span class="dg-p">{s.goal_diff:+d}</span>' if s.goal_diff > 0
               else f'<span class="dg-n">{s.goal_diff:+d}</span>' if s.goal_diff < 0 else "0")
        filas += f"""
    <tr class="{cls}">
      <td>{i}</td><td>{traducir(entry['team'])}</td>
      <td>{entry['group'].replace('GROUP_','')}</td>
      <td>{s.played}</td><td>{s.goals_for}</td><td>{s.goals_against}</td>
      <td>{dg}</td><td><span class="pts">{s.points}</span></td>
    </tr>"""
        if i == 8:  # línea de corte: los 8 de arriba avanzan
            filas += ('<tr class="corte-row"><td colspan="8">'
                      'Línea de clasificación — los 8 de arriba avanzan</td></tr>')
    return f"""
    <div style="max-width:660px;margin:0 auto">
      <div class="hoy-fila terc-exp-box" onclick="toggleMatch(this)">
        <div class="hoy-head"><span class="hoy-etiqueta">Cómo funcionan los mejores terceros</span><span class="hoy-chev">&#9662;</span></div>
        <div class="hoy-detail"><p class="terc-exp">El Mundial 2026 tiene 12 grupos de 4. Pasan a octavos los 2 primeros de cada grupo (24 equipos) más los <b>8 mejores terceros</b>, que se eligen comparando los 12 terceros entre sí: primero por puntos, después diferencia de gol, goles a favor, fair play y, al final, el ranking FIFA. Los 4 terceros que quedan más abajo se eliminan. Por eso esta tabla — y el nombre del sitio.</p></div>
      </div>
      <div class="grupo">
        <table>
          <thead><tr><th>#</th><th>Equipo</th><th>Grp</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th><th>Pts</th></tr></thead>
          <tbody>{filas}</tbody>
        </table>
      </div>
    </div>"""


# ── Match card R32 ─────────────────────────────────────────────────────────

def _team_row(api_name: str, mid: str, prov: bool = False) -> str:
    html_val = traducir(api_name)
    safe = html_val.replace('"', '&quot;')
    cls = "team-row prov" if prov else "team-row"
    title = ' title="Proyección — cambia según cómo terminen los grupos"' if prov else ''
    return (f'<div class="{cls}"{title} data-mid="{mid}" data-name="{api_name}" '
            f'data-html="{safe}" onclick="pickWinner(this)">{html_val}</div>')


def _match_card(m: Dict) -> str:
    num = m["partido"]
    e1  = m["equipo1"]
    e2  = m["equipo2"]
    mid = str(num)
    is_live = m.get("is_live", False)
    utc_date = m.get("utc_date") or ""
    venue    = m.get("venue", "")

    if is_live:
        status_badge = f'<span class="badge-live-sm"><span class="dot"></span>EN VIVO</span>'
    else:
        status_badge = ''

    is_tbd = "3ro" in e2 or "post" in e2.lower() or e2.startswith("3°")
    row1 = _team_row(e1, mid, m.get("prov1", False))
    row2 = (_team_row(e2, mid, m.get("prov2", False)) if not is_tbd
            else f'<div class="team-row ph">{e2}</div>')

    data_utc_attr = f' data-utc="{utc_date}"' if utc_date else ''

    # 4.3 — head-to-head: botón en el encabezado + historial embebido en la card
    h2h = m.get("h2h") or []
    h2h_btn, h2h_data = "", ""
    if h2h:
        def _h2h_comp(x):
            comp, rnd = x.get("comp", ""), x.get("round", "")
            return f'{comp} · {rnd}' if (comp and rnd) else (comp or rnd)
        rows_h = "".join(
            f'<div class="h2h-row"><span class="h2h-d">{x["date"][8:10]}/{x["date"][5:7]}/{x["date"][2:4]}</span>'
            f'<span class="h2h-c">{_h2h_comp(x)}</span>'
            f'<span class="h2h-r">{nombre_es(x["home"])} <b>{x["gh"]}-{x["ga"]}</b> {nombre_es(x["away"])}</span></div>'
            for x in h2h[:6]
        )
        title = f'{nombre_es(e1)} vs {nombre_es(e2)}'
        h2h_btn = '<button class="h2h-btn" onclick="showH2H(this)" title="Historial entre los dos">H2H</button>'
        h2h_data = f'<div class="mc-h2h" hidden data-title="{title}">{rows_h}</div>'

    return f"""
    <div class="mc" data-mid="{mid}">
      <div class="mc-label"><span>Partido {num:02d}</span><span class="mc-label-r">{h2h_btn}{status_badge}</span></div>
      {row1}{row2}{h2h_data}
      <div class="mc-meta">
        <span class="r32-dt"{data_utc_attr}></span>
        {'<span class="venue">' + venue + '</span>' if venue else ''}
      </div>
    </div>"""


# ── Bracket / Llaves ────────────────────────────────────────────────────────

def _conn(n_arms: int) -> str:
    arm = '<div class="arm"><div class="arm-t"></div><div class="arm-b"></div></div>'
    return f'<div class="conn">{"".join(arm for _ in range(n_arms))}</div>'


def _slots_col(n: int, prefix: str, cls: str) -> str:
    slots = ""
    for i in range(n):
        sid = f"{prefix}-{i}"
        ks = _KO_SCHEDULE.get(sid)
        date_attr = f' data-utc="{ks[0]}"' if ks else ''
        venue_html = f'<span class="venue">{ks[1]}</span>' if ks else ''
        lbl = {"r16": "Octavos", "qf": "Cuartos", "sf": "Semifinal"}.get(cls, "")
        slots += f"""
      <div class="mc" id="{sid}">
        <div class="mc-label"><span>{lbl}</span></div>
        <div class="team-row ph">— Por definir</div>
        <div class="team-row ph">— Por definir</div>
        <div class="mc-meta">
          <span id="dt-{sid}"{date_attr}></span>
          {venue_html}
        </div>
      </div>"""
    return f'<div class="col {cls}">{slots}</div>'


def _r32_col(matches: List[Dict], col_id: str = "") -> str:
    html = ""
    for i in range(0, len(matches), 2):
        m1 = _match_card(matches[i])
        m2 = _match_card(matches[i+1]) if i + 1 < len(matches) else ""
        html += f'<div class="par">{m1}{m2}</div>'
    id_attr = f' id="{col_id}"' if col_id else ""
    return f'<div class="col r32"{id_attr}>{html}</div>'


def _render_llaves(matchups: List[Dict]) -> str:
    left  = matchups[:8]
    right = matchups[8:]

    left_html = (
        _r32_col(left, "r32-left") +
        _conn(4) +
        _slots_col(4, "r16-L", "r16") +
        _conn(2) +
        _slots_col(2, "qf-L", "qf") +
        _conn(1) +
        _slots_col(1, "sf-L", "sf")
    )

    right_html = (
        _slots_col(1, "sf-R", "sf") +
        _conn(1) +
        _slots_col(2, "qf-R", "qf") +
        _conn(2) +
        _slots_col(4, "r16-R", "r16") +
        _conn(4) +
        _r32_col(right, "r32-right")
    )

    final_col = f"""
    <div class="final-col">
      <div class="champ-card" id="champ-card" style="display:none">
        <img src="./copa.avif" class="champ-trophy-img" alt="Copa Mundial">
        <div class="champ-card-flag" id="champ-flag"></div>
        <div class="champ-card-country" id="champ-country"></div>
        <div class="champ-card-subtitle">Campe&oacute;n Mundial 2026</div>
      </div>

      <div class="final-box">
        <div class="final-inner">
          <div class="final-title">Final</div>
          <div class="final-date" id="dt-final" data-utc="{_FINAL[0]}"></div>
          <div class="final-venue">{_FINAL[1]}</div>
        </div>
        <div class="final-teams" id="slot-final">
          <div class="team-row ph" style="justify-content:center">— Por definir</div>
          <div class="team-row ph" style="justify-content:center">— Por definir</div>
        </div>
      </div>

      <div class="tercer-box">
        <div class="tercer-inner">
          <div class="tercer-title">3er y 4to Puesto</div>
          <div class="tercer-date" id="dt-tercer" data-utc="{_3RD_PLACE[0]}"></div>
          <div class="tercer-venue">{_3RD_PLACE[1]}</div>
        </div>
        <div class="tercer-teams" id="slot-tercer">
          <div class="team-row ph" style="justify-content:center">— Por definir</div>
          <div class="team-row ph" style="justify-content:center">— Por definir</div>
        </div>
      </div>
    </div>"""

    return f"""
<div class="llaves">
  <div class="mitad izq">{left_html}</div>
  {final_col}
  <div class="mitad der">{right_html}</div>
</div>"""


def _render_mobile_bracket(matchups: List[Dict]) -> str:
    # R32: all 16 match cards flat
    r32 = "".join(_match_card(m) for m in matchups)

    def _mslot(sid: str, lbl: str) -> str:
        msid = f"m-{sid}"
        ks = _KO_SCHEDULE.get(sid)
        date_attr = f' data-utc="{ks[0]}"' if ks else ''
        venue_html = f'<span class="venue">{ks[1]}</span>' if ks else ''
        return (f'<div class="mc" id="{msid}">'
                f'<div class="mc-label"><span>{lbl}</span></div>'
                f'<div class="team-row ph">— Por definir</div>'
                f'<div class="team-row ph">— Por definir</div>'
                f'<div class="mc-meta"><span{date_attr}></span>{venue_html}</div>'
                f'</div>')

    r16 = "".join(_mslot(s, "Octavos") for s in [
        "r16-L-0","r16-L-1","r16-L-2","r16-L-3",
        "r16-R-0","r16-R-1","r16-R-2","r16-R-3"])
    qf  = "".join(_mslot(s, "Cuartos") for s in [
        "qf-L-0","qf-L-1","qf-R-0","qf-R-1"])
    sf  = "".join(_mslot(s, "Semifinal") for s in ["sf-L-0","sf-R-0"])

    final_card = (
        f'<div class="mc" style="border-top:2px solid {T};margin-bottom:8px">'
        f'<div class="mc-label" style="color:{T}"><span>Final</span></div>'
        f'<div id="m-final-rows">'
        f'<div class="team-row ph" style="justify-content:center">— Por definir</div>'
        f'<div class="team-row ph" style="justify-content:center">— Por definir</div>'
        f'</div>'
        f'<div class="mc-meta"><span data-utc="{_FINAL[0]}"></span>'
        f'<span class="venue">{_FINAL[1]}</span></div>'
        f'</div>'
    )
    tercer_card = (
        f'<div class="mc" style="border-top:2px solid {TEL}">'
        f'<div class="mc-label" style="color:{TEL}"><span>3er y 4to Puesto</span></div>'
        f'<div id="m-tercer-rows">'
        f'<div class="team-row ph" style="justify-content:center">— Por definir</div>'
        f'<div class="team-row ph" style="justify-content:center">— Por definir</div>'
        f'</div>'
        f'<div class="mc-meta"><span data-utc="{_3RD_PLACE[0]}"></span>'
        f'<span class="venue">{_3RD_PLACE[1]}</span></div>'
        f'</div>'
    )

    return (
        f'<div class="mobile-bracket">'
        f'<div class="mb-tabs">'
        f'<button class="mb-tab mb-active" onclick="mbSetRound(this,\'r32\')">R32</button>'
        f'<button class="mb-tab" onclick="mbSetRound(this,\'r16\')">R16</button>'
        f'<button class="mb-tab" onclick="mbSetRound(this,\'qf\')">QF</button>'
        f'<button class="mb-tab" onclick="mbSetRound(this,\'sf\')">SF</button>'
        f'<button class="mb-tab" onclick="mbSetRound(this,\'f\')">Final</button>'
        f'</div>'
        f'<div class="mb-panel" id="mb-r32">{r32}</div>'
        f'<div class="mb-panel" id="mb-r16" style="display:none">{r16}</div>'
        f'<div class="mb-panel" id="mb-qf" style="display:none">{qf}</div>'
        f'<div class="mb-panel" id="mb-sf" style="display:none">{sf}</div>'
        f'<div class="mb-panel" id="mb-f" style="display:none">{final_card}{tercer_card}</div>'
        f'</div>'
    )


def _ko_schedule_json() -> str:
    import json
    return json.dumps({k: list(v) for k, v in _KO_SCHEDULE.items()})


# ── Partidos de hoy ────────────────────────────────────────────────────────

def _stage_label(stage: str, group: str, matchday: int) -> str:
    if stage == "GROUP_STAGE":
        grp = group.replace("GROUP_", "")
        return f"Grupo {grp} · Fecha {matchday}"
    return {
        "ROUND_OF_32":    "16avos de Final",
        "ROUND_OF_16":    "Octavos de Final",
        "QUARTER_FINALS": "Cuartos de Final",
        "SEMI_FINALS":    "Semifinales",
        "THIRD_PLACE":    "3er y 4to Puesto",
        "FINAL":          "Final",
    }.get(stage, stage)


def _hoy_badge(m: dict) -> str:
    """Badge de estado inline para la cabecera de la fila."""
    status = m["status"]
    if status == "FINISHED":
        return '<span class="hoy-badge-fin">FIN</span>'
    if status == "PAUSED":
        return '<span class="hoy-badge-live"><span class="dot"></span>ENT</span>'
    if status == "IN_PLAY":
        el = m.get("elapsed")
        min_html = f"{el}'" if el is not None else ""
        return ('<span class="hoy-badge-live"><span class="dot"></span>EN VIVO '
                f'<span class="hoy-min">{min_html}</span></span>')
    return ''


def _hoy_centro(m: dict) -> str:
    """Solo el marcador / hora para el centro de la grilla, sin badge."""
    status = m["status"]
    hg = m.get("home_goals")
    ag = m.get("away_goals")
    if status == "FINISHED":
        score = f"{hg} - {ag}" if hg is not None else "- -"
        return f'<span class="hoy-score">{score}</span>'
    if status in ("IN_PLAY", "PAUSED"):
        score = f"{hg} - {ag}" if hg is not None else "0 - 0"
        return f'<span class="hoy-score">{score}</span>'
    utc = m.get("utc_date", "")
    if utc:
        return f'<span class="hoy-hora" data-utc="{utc}" data-format="time"></span>'
    return '<span class="hoy-vs">vs</span>'


def _attach_scorer_photos(scorers: list, squads: dict) -> None:
    """5.1 — cruza la foto de los planteles con cada goleador, por apellido + país."""
    import unicodedata

    def _norm(s):
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s.lower().replace(".", "").strip()

    def _last(name):
        parts = _norm(name).split()
        return parts[-1] if parts else ""

    idx = {}
    for team, entry in (squads or {}).items():
        tes = nombre_es(team)
        for p in entry.get("players", []):
            ln = _last(p.get("name", ""))
            if ln and p.get("photo"):
                idx[(tes, ln)] = p["photo"]

    for s in scorers:
        if s.get("photo"):
            continue
        photo = idx.get((nombre_es(s.get("team", "")), _last(s.get("name", ""))))
        if photo:
            s["photo"] = photo


def _render_rating(standings: Dict) -> str:
    """5.2 — ranking del mejor promedio de valoración del torneo (mín. 2 partidos)."""
    md = standings.get("_match_details", {})
    acc = {}
    for det in md.values():
        for side in det.get("players", []):
            team = side.get("team", "")
            for p in side.get("players", []):
                r = p.get("rating")
                if not r or (p.get("minutes") or 0) <= 0:
                    continue
                try:
                    rv = float(r)
                except (TypeError, ValueError):
                    continue
                acc.setdefault((p.get("name", ""), team), []).append(rv)
    items = []
    for (name, team), ratings in acc.items():
        if len(ratings) < 2:
            continue
        items.append({"name": name, "team": team,
                      "value": round(sum(ratings) / len(ratings), 2),
                      "played": len(ratings)})
    items.sort(key=lambda x: x["value"], reverse=True)
    _attach_scorer_photos(items, standings.get("_squads", {}))
    return _render_ranking(items, "Prom.", "rating",
                           "Disponible a medida que se jueguen los partidos.",
                           extra_col=("PJ", lambda it: it.get("played", 0)))


def _render_scorers(standings: Dict) -> str:
    scorers = standings.get("_scorers", [])
    if not scorers:
        return f'<p style="font-size:.75rem;color:{MUT};margin-top:4px">Disponible próximamente.</p>'
    _attach_scorer_photos(scorers, standings.get("_squads", {}))

    def _row(i: int, s: dict) -> str:
        bg      = f'style="background:{GRY}"' if i % 2 == 0 else ''
        assists = s.get("assists") or 0
        played  = s.get("played") or 0
        return (f'<tr {bg} data-team="{nombre_es(s["team"])}">'
                f'<td>{i}</td>'
                f'<td style="text-align:left;white-space:nowrap"><span class="pl-cell">{_player_avatar(s.get("photo", ""))}{s["name"]}</span></td>'
                f'<td style="text-align:left;white-space:nowrap">{traducir(s["team"])}</td>'
                f'<td><span class="pts">{s["goals"]}</span></td>'
                f'<td style="color:{MUT}">{assists if assists else "—"}</td>'
                f'<td style="color:{DIM}">{played if played else "—"}</td>'
                f'</tr>')

    top   = "".join(_row(i, s) for i, s in enumerate(scorers[:10], 1))
    rest  = scorers[10:]
    extra = ""
    btn   = ""
    if rest:
        extra_rows = "".join(_row(i, s) for i, s in enumerate(rest, 11))
        extra = f'<tbody id="scorers-extra" style="display:none">{extra_rows}</tbody>'
        btn   = (f'<div style="text-align:center;margin-top:8px">'
                 f'<button class="reset-btn" id="scorers-btn" onclick="toggleScorers()">'
                 f'Ver todos los goleadores</button></div>')

    return f"""
    <div class="rank-wrap" style="max-width:500px;margin:0 auto">
      <div class="grupo">
        <table>
          <thead><tr>
            <th>#</th>
            <th style="text-align:left">Jugador</th>
            <th style="text-align:left">País</th>
            <th>Goles</th>
            <th>Asist.</th>
            <th>PJ</th>
          </tr></thead>
          <tbody>{top}</tbody>
          {extra}
        </table>
      </div>
      {btn}
    </div>"""


def _player_avatar(photo: str) -> str:
    """Avatar redondo chico del jugador (5.1). Vacío si no hay foto."""
    if not photo:
        return ''
    return (f'<img class="pl-av" src="{photo}" alt="" width="22" height="22" '
            f'loading="lazy" decoding="async" fetchpriority="low" '
            f'onerror="this.style.display=\'none\'">')


def _rank_filter(teams: set, key: str) -> str:
    """5.5 — selector de país para filtrar un ranking en el cliente."""
    teams = {t for t in teams if t}
    if len(teams) < 2:
        return ''
    opts = "".join(f'<option value="{t}">{t}</option>' for t in sorted(teams))
    return (f'<div class="rank-filter"><select data-key="{key}" onchange="filterRank(this)">'
            f'<option value="">Todas las selecciones</option>{opts}</select></div>')


def _render_ranking(items: list, value_header: str, key: str,
                    empty: str = "Disponible próximamente.", extra_col=None) -> str:
    """Tabla de ranking de jugadores. Top 10 + ver todos. extra_col=(header, fn) opcional (5.3)."""
    # Solo jugadores con al menos 1 (no rellenar con ceros)
    items = [it for it in items if (it.get("value") or 0) > 0]
    if not items:
        return f'<p style="font-size:.75rem;color:{MUT};margin-top:4px">{empty}</p>'

    def _row(i: int, it: dict) -> str:
        bg = f'style="background:{GRY}"' if i % 2 == 0 else ''
        ec = f'<td style="color:{DIM}">{extra_col[1](it)}</td>' if extra_col else ''
        return (f'<tr {bg} data-team="{nombre_es(it.get("team", ""))}">'
                f'<td>{i}</td>'
                f'<td style="text-align:left;white-space:nowrap"><span class="pl-cell">{_player_avatar(it.get("photo", ""))}{it.get("name", "")}</span></td>'
                f'<td style="text-align:left;white-space:nowrap">{traducir(it.get("team", ""))}</td>'
                f'<td><span class="pts">{it.get("value", 0)}</span></td>'
                f'{ec}'
                f'</tr>')

    top = "".join(_row(i, it) for i, it in enumerate(items[:10], 1))
    rest = items[10:]
    extra = ""
    btn = ""
    if rest:
        extra_rows = "".join(_row(i, it) for i, it in enumerate(rest, 11))
        extra = f'<tbody id="{key}-extra" style="display:none">{extra_rows}</tbody>'
        btn = (f'<div style="text-align:center;margin-top:8px">'
               f'<button class="reset-btn" id="{key}-btn" data-more="Ver todos" '
               f'onclick="toggleList(\'{key}\')">Ver todos</button></div>')

    return f"""
    <div class="rank-wrap" style="max-width:500px;margin:0 auto">
      <div class="grupo">
        <table>
          <thead><tr>
            <th>#</th>
            <th style="text-align:left">Jugador</th>
            <th style="text-align:left">País</th>
            <th>{value_header}</th>
            {('<th>' + extra_col[0] + '</th>') if extra_col else ''}
          </tr></thead>
          <tbody>{top}</tbody>
          {extra}
        </table>
      </div>
      {btn}
    </div>"""


def _render_assists(standings: Dict) -> str:
    return _render_ranking(standings.get("_assists", []), "Asist.", "assists")


def _render_yellows(standings: Dict) -> str:
    return _render_ranking(standings.get("_yellows", []), "Amar.", "yellows")


def _render_reds(standings: Dict) -> str:
    return _render_ranking(standings.get("_reds", []), "Rojas", "reds")


def _venue_date(iso: str) -> str:
    """Fecha corta (día/mes), formateada en la zona del usuario (cliente)."""
    return f'<span class="ven-m-date" data-utc="{iso}" data-format="shortdate"></span>'


def _venue_time(iso: str) -> str:
    """Hora de inicio, formateada en la zona del usuario (cliente). Vacío si no hay hora."""
    try:
        datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return ""
    return f'<span class="ven-time" data-utc="{iso}" data-format="time"></span>'


# Calendario COMPLETO de eliminatorias — verificado contra el oficial FIFA 2026
# (Wikipedia knockout stage): (datetime UTC, estadio, ronda). Con HORA real para que
# el cliente la muestre bien en la zona del usuario (antes era solo fecha → se veía
# un día antes y 21:00 fijo). Nombres de estadio como en los fixtures de API-Football.
_VENUE_KO = [
    # 16avos de Final (P73-P88)
    ("2026-06-28T19:00:00Z", "SoFi Stadium",            "16avos de Final"),  # P73
    ("2026-06-29T17:00:00Z", "NRG Stadium",             "16avos de Final"),  # P76
    ("2026-06-29T20:30:00Z", "Gillette Stadium",        "16avos de Final"),  # P74
    ("2026-06-30T01:00:00Z", "Estadio BBVA",            "16avos de Final"),  # P75
    ("2026-06-30T17:00:00Z", "AT&T Stadium",            "16avos de Final"),  # P78
    ("2026-06-30T21:00:00Z", "MetLife Stadium",         "16avos de Final"),  # P77
    ("2026-07-01T01:00:00Z", "Estadio Azteca",          "16avos de Final"),  # P79
    ("2026-07-01T16:00:00Z", "Mercedes-Benz Stadium",   "16avos de Final"),  # P80
    ("2026-07-01T20:00:00Z", "Lumen Field",             "16avos de Final"),  # P82
    ("2026-07-02T00:00:00Z", "Levi's Stadium",          "16avos de Final"),  # P81
    ("2026-07-02T19:00:00Z", "SoFi Stadium",            "16avos de Final"),  # P84
    ("2026-07-02T23:00:00Z", "BMO Field",               "16avos de Final"),  # P83
    ("2026-07-03T03:00:00Z", "BC Place",                "16avos de Final"),  # P85
    ("2026-07-03T18:00:00Z", "AT&T Stadium",            "16avos de Final"),  # P88
    ("2026-07-03T22:00:00Z", "Hard Rock Stadium",       "16avos de Final"),  # P86
    ("2026-07-04T01:30:00Z", "Arrowhead Stadium",       "16avos de Final"),  # P87
    # Octavos de Final (P89-P96)
    ("2026-07-04T17:00:00Z", "NRG Stadium",             "Octavos de Final"), # P90
    ("2026-07-04T21:00:00Z", "Lincoln Financial Field", "Octavos de Final"), # P89
    ("2026-07-05T20:00:00Z", "MetLife Stadium",         "Octavos de Final"), # P91
    ("2026-07-06T00:00:00Z", "Estadio Azteca",          "Octavos de Final"), # P92
    ("2026-07-06T19:00:00Z", "AT&T Stadium",            "Octavos de Final"), # P93
    ("2026-07-07T00:00:00Z", "Lumen Field",             "Octavos de Final"), # P94
    ("2026-07-07T16:00:00Z", "Mercedes-Benz Stadium",   "Octavos de Final"), # P95
    ("2026-07-07T20:00:00Z", "BC Place",                "Octavos de Final"), # P96
    # Cuartos de Final (P97-P100)
    ("2026-07-09T20:00:00Z", "Gillette Stadium",        "Cuartos de Final"), # P97
    ("2026-07-10T19:00:00Z", "SoFi Stadium",            "Cuartos de Final"), # P98
    ("2026-07-11T21:00:00Z", "Hard Rock Stadium",       "Cuartos de Final"), # P99
    ("2026-07-12T01:00:00Z", "Arrowhead Stadium",       "Cuartos de Final"), # P100
    # Semifinales (P101, P102)
    ("2026-07-14T19:00:00Z", "AT&T Stadium",            "Semifinal"),        # P101
    ("2026-07-15T19:00:00Z", "Mercedes-Benz Stadium",   "Semifinal"),        # P102
    # 3er Puesto (P103) y Final (P104)
    ("2026-07-18T21:00:00Z", "Hard Rock Stadium",       "3er Puesto"),       # P103
    ("2026-07-19T19:00:00Z", "MetLife Stadium",         "Final"),            # P104
]


def _knockouts_for_venue(venue_name: str) -> list:
    """Eliminatorias (16avos → Final) programadas en este estadio. Calendario verificado."""
    if not venue_name:
        return []
    return [{"date": d, "ko": True, "label": lbl}
            for d, ven, lbl in _VENUE_KO if ven == venue_name]


def _render_venues(standings: Dict) -> str:
    """Módulo de estadios, cada uno expandible con foto y sus partidos (grupos + eliminatorias)."""
    venues = standings.get("_venues", [])
    if not venues:
        return f'<p style="font-size:.75rem;color:{MUT};margin-top:4px">Disponible próximamente.</p>'

    cards = ""
    for v in venues:
        all_m = list(v.get("matches", [])) + _knockouts_for_venue(v.get("name", ""))
        all_m.sort(key=lambda m: m.get("date", ""))
        count = len(all_m)
        rows = ""
        for m in all_m:
            iso = m.get("date", "")
            fecha = _venue_date(iso)
            if m.get("ko"):
                rows += (f'<div class="ven-m ven-m-ko">'
                         f'{fecha}'
                         f'<span class="ven-ko-label">{m.get("label", "")}</span>'
                         f'<span class="ven-m-mid">{_venue_time(iso)}</span>'
                         f'</div>')
                continue
            home = traducir(m.get("home", ""))
            away = traducir(m.get("away", ""))
            if m.get("status") == "FT" and m.get("gh") is not None:
                mid = f'<span class="pts">{m.get("gh")} - {m.get("ga")}</span>'
            else:
                mid = _venue_time(iso)
            rows += (f'<div class="ven-m">'
                     f'{fecha}'
                     f'<span class="ven-m-team ven-m-h">{home}</span>'
                     f'<span class="ven-m-mid">{mid}</span>'
                     f'<span class="ven-m-team ven-m-a">{away}</span>'
                     f'</div>')
        # Foto del estadio (solo la validada como real, no placeholder)
        img = ""
        if v.get("image_url"):
            img = (f'<img class="ven-img" loading="lazy" decoding="async" fetchpriority="low" '
                   f'alt="" src="{v["image_url"]}" onerror="this.style.display=\'none\'">')
        # Datos: capacidad + superficie
        vinfo = VENUE_INFO.get(v.get("name", "")) or {}
        bits = []
        cap = v.get("capacity")
        if cap:
            try:
                bits.append(f'<span class="ven-k">Capacidad</span> {int(cap):,}'.replace(",", "."))
            except Exception:
                pass
        if vinfo.get("country"):  # 6.2
            bits.append(f'<span class="ven-k">País</span> {vinfo["country"]}')
        if vinfo.get("year"):     # 6.3
            bits.append(f'<span class="ven-k">Inaugurado</span> {vinfo["year"]}')
        surf = v.get("surface")
        if surf:
            surf_es = {"grass": "Césped natural", "artificial turf": "Césped sintético"}.get(surf, surf)
            bits.append(f'<span class="ven-k">Superficie</span> {surf_es}')
        # 6.1 — clima actual de la ciudad sede
        w = v.get("weather") or {}
        if w.get("temp") is not None:
            desc = f' · {w.get("desc")}' if w.get("desc") else ""
            bits.append(f'<span class="ven-k">Clima</span> {w["temp"]}°{desc}')
        info = f'<div class="ven-info">{"".join(f"<span>{b}</span>" for b in bits)}</div>' if bits else ""
        # 6.4 — link a Google Maps de la sede
        murl = venue_maps_url(v.get("name", ""))
        _pin = ('<svg class="ven-map-ico" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
                '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 '
                '9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z"/></svg>')
        maplink = (f'<a class="ven-map" href="{murl}" target="_blank" rel="noopener" '
                   f'onclick="event.stopPropagation()">{_pin}Ver en el mapa</a>') if murl else ""
        local = (f'<div class="ven-local"><span class="ven-k">Equipo local</span> {vinfo["home"]}</div>'
                 if vinfo.get("home") else "")
        detail = f'<div class="hoy-detail">{img}{info}{local}{maplink}<div class="hoy-dsec">{rows}</div></div>'
        sub = " · ".join(b for b in [v.get("city", ""),
                                     f'{count} {"partido" if count == 1 else "partidos"}'] if b)
        cards += (f'<div class="hoy-fila" onclick="toggleMatch(this)">'
                  f'<div class="hoy-head">'
                  f'<span class="ven-name">{v.get("name", "")}</span>'
                  f'<span class="hoy-chev">&#9662;</span>'
                  f'</div>'
                  f'<div class="ven-sub">{sub}</div>'
                  f'{detail}'
                  f'</div>')
    return f'<div style="max-width:560px;margin:0 auto;display:flex;flex-direction:column;gap:8px">{cards}</div>'


def _hoy_detail_html(m: dict, standings: dict = None, show_vermatch: bool = True) -> str:
    """Bloque expandible con goles, tarjetas, cambios y árbitro."""
    sections = []

    # 1.7 — Qué se juega cada equipo (fase de grupos, partido aún no empezado)
    grp = m.get("group") or ""
    if standings and grp.startswith("GROUP_") and m.get("status") == "TIMED":
        gd = standings.get(grp)
        if gd:
            sc = compute_group_scenarios(gd.get("teams", []), gd.get("matches", []))
            rows_q = "".join(
                f'<div class="gf-row"><span class="gf-tm">{traducir(t)}</span>'
                f'<span class="gf-ph">'
                f'{team_phrase(sc[t], opponent=(traducir(_opp_name(sc[t])) or None))}</span></div>'
                for t in (m.get("home"), m.get("away")) if sc.get(t)
            )
            if rows_q:
                sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Qué se juega</p>{rows_q}</div>')

    goals = m.get("goals_detail") or []
    if goals:
        rows = ""
        for g in goals:
            minute = g.get("minute", "")
            scorer = g.get("scorer", "")
            team   = nombre_es(g.get("team", ""))
            assist = g.get("assist", "")
            g_type = g.get("type", "NORMAL")
            suffix = " (PP)" if g_type == "PENALTY" else (" (PC)" if g_type == "OWN" else "")
            assist_txt = f'<span class="hoy-ev-s"> · asist: {assist}</span>' if assist else ""
            rows += (f'<div class="hoy-ev">'
                     f'<span class="hoy-ev-min">{minute}\'</span>'
                     f'<span class="hoy-ev-dot"></span>'
                     f'<span class="hoy-ev-txt">{scorer}{suffix}'
                     f'<span class="hoy-ev-s"> · {team}</span>'
                     f'{assist_txt}</span>'
                     f'</div>')
        sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Goles</p>{rows}</div>')

    bookings = m.get("bookings") or []
    if bookings:
        rows = ""
        for b in bookings:
            card   = b.get("card", "YELLOW")
            player = b.get("player", "")
            team   = nombre_es(b.get("team", ""))
            minute = b.get("minute", "")
            icon   = "hoy-ev-yc" if card == "YELLOW" else "hoy-ev-rc"
            rows += (f'<div class="hoy-ev">'
                     f'<span class="hoy-ev-min">{minute}\'</span>'
                     f'<span class="{icon}"></span>'
                     f'<span class="hoy-ev-txt">{player}'
                     f'<span class="hoy-ev-s"> · {team}</span></span>'
                     f'</div>')
        sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Tarjetas</p>{rows}</div>')

    subs = m.get("substitutions") or []
    if subs:
        rows = ""
        for s in subs:
            minute     = s.get("minute", "")
            player_in  = s.get("player_in", "")
            player_out = s.get("player_out", "")
            team       = nombre_es(s.get("team", ""))
            rows += (f'<div class="hoy-ev">'
                     f'<span class="hoy-ev-min">{minute}\'</span>'
                     f'<span class="hoy-ev-sw">&#x21C4;</span>'
                     f'<span class="hoy-ev-txt">{player_in} → {player_out}'
                     f'<span class="hoy-ev-s"> · {team}</span></span>'
                     f'</div>')
        sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Cambios</p>{rows}</div>')

    ref = m.get("referee", "")
    if ref:
        sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Árbitro</p>'
                        f'<p style="font-size:.75rem;color:{MUT};margin:0">{ref}</p></div>')

    vname = m.get("venue_name", "")
    if vname:
        from countries import capacidad_fmt
        vbits = [b for b in [vname, m.get("venue_city", ""),
                             (capacidad_fmt(vname) + " espectadores") if capacidad_fmt(vname) else ""] if b]
        sections.append(f'<div class="hoy-dsec"><p class="hoy-dsec-t">Estadio</p>'
                        f'<p style="font-size:.75rem;color:{MUT};margin:0">{" · ".join(vbits)}</p></div>')

    # Botón VER PARTIDO arriba de todo — SIEMPRE (todos los partidos tienen su página).
    # En contextos que ya tienen su propio acceso (perfil de selección) se omite.
    mid = m.get("match_id")
    vermatch = (f'<a class="hoy-vermatch" href="/partido.html?id={mid}" '
                f'onclick="event.stopPropagation()">VER PARTIDO &#8594;</a>') if (mid and show_vermatch) else ""

    if not sections and not vermatch:
        return ""

    return f'<div class="hoy-detail">{vermatch}{"".join(sections)}</div>'


def _render_today_matches(matches: list, standings: dict = None) -> str:
    """Devuelve solo el cuerpo de partidos (sin wrapper sec ni título — los maneja el JS de navegación)."""
    if not matches:
        return f'<p style="font-size:.75rem;color:{MUT};padding:2px 0">No hay partidos programados.</p>'
    matches = sorted(matches, key=lambda m: m.get("utc_date", ""))
    rows = ""
    for m in matches:
        lbl       = _stage_label(m["stage"], m["group"], m.get("matchday", 0))
        home_html = traducir(m["home"])
        away_html = traducir(m["away"])
        badge     = _hoy_badge(m)
        centro    = _hoy_centro(m)
        detail    = _hoy_detail_html(m, standings)
        rows += (f'<div class="hoy-fila" data-mid="{m.get("match_id")}" onclick="toggleMatch(this)">'
                 f'<div class="hoy-head">'
                 f'<span class="hoy-etiqueta">{lbl}</span>'
                 f'{badge}'
                 f'<span class="hoy-chev">&#9662;</span>'
                 f'</div>'
                 f'<div class="hoy-match">'
                 f'<div class="hoy-home">{home_html}</div>'
                 f'<div class="hoy-centro">{centro}</div>'
                 f'<div class="hoy-away">{away_html}</div>'
                 f'</div>'
                 f'{detail}'
                 f'</div>')
    return f'<div class="hoy-lista">{rows}</div>'
