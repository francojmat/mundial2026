# -*- coding: utf-8 -*-
"""Página del simulador de llaves (Fase 3). Reusa EL MISMO bracket que el home en vivo
(_render_llaves + _render_mobile_bracket + bracket.css + bracket.js) para respetar el
diseño, y le agrega editores de resultado exacto por grupo que recalculan el R32 en vivo
con el motor JS (sim-engine.js, verificado contra el Python en test_sim_parity.py)."""
from typing import Dict, List

from html_renderer import (_render_llaves, _render_mobile_bracket,
                           T, BG, WHT, BDR, BDR2, TXT, MUT, DIM, GRY)


def render_simulador_shell(matchups: List[Dict]) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Simulá las llaves · Mundial 2026</title>
  <meta name="description" content="Simulador del Mundial 2026: cargá los resultados pendientes de los grupos y armá el bracket completo hasta la final.">
  <meta name="theme-color" content="#c2410c">
  <link rel="icon" href="/favicon.ico">
  <link rel="stylesheet" href="/bracket.css">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:{BG};color:{TXT};padding:20px 16px 60px}}
    .wrap{{max-width:1240px;margin:0 auto}}
    .topbar{{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}}
    .back{{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:700;color:{T};text-decoration:none;border:1px solid {BDR};border-radius:8px;padding:7px 13px;background:{WHT}}}
    h1{{font-size:1.45rem;font-weight:800;letter-spacing:-.02em}}
    .reset{{font-size:.74rem;font-weight:700;color:{T};border:1px solid {T};border-radius:8px;padding:7px 13px;background:{WHT};cursor:pointer;margin-left:auto}}
    .reset:hover{{background:{T};color:#fff}}
    .intro{{font-size:.82rem;color:{MUT};margin:4px 0 18px;line-height:1.5;max-width:760px}}
    .sec-t{{font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:{T};margin:26px 0 12px;padding-bottom:7px;border-bottom:1px solid {BDR}}}
    .sec-tog{{display:flex;align-items:center;justify-content:space-between;cursor:pointer;user-select:none}}
    .sec-tog:hover .tog-btn{{color:{T}}}
    .tog-btn{{font-size:.62rem;font-weight:700;color:{DIM};letter-spacing:.04em}}
    #groups-wrap.collapsed{{display:none}}
    /* editores de grupo */
    .sgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}}
    .sg{{background:{WHT};border:1px solid {BDR};border-radius:12px;padding:12px 14px}}
    .sg-h{{font-size:.78rem;font-weight:800;margin-bottom:8px}}
    .sg-r{{display:flex;align-items:center;gap:6px;font-size:.76rem;padding:3px 0}}
    .sg-p{{color:{DIM};width:15px;flex-shrink:0}}
    .sg-t{{flex:1;display:flex;align-items:center;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .sg-dg{{color:{MUT};width:30px;text-align:right}}
    .sg-pts{{font-weight:800;width:24px;text-align:right}}
    .sg-m{{margin-top:10px;padding-top:9px;border-top:1px solid {GRY};display:flex;flex-direction:column;gap:7px}}
    .sg-mr{{display:flex;align-items:center;gap:5px;font-size:.72rem}}
    .sg-mt{{flex:1;display:flex;align-items:center;justify-content:flex-end;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right}}
    .sg-mt.a{{justify-content:flex-start;text-align:left}}
    .sg-mt img{{margin:0 0 0 5px!important}}
    .sg-mt.a img{{margin:0 5px 0 0!important}}
    .sg-in{{width:34px;height:30px;border:1px solid {BDR2};border-radius:7px;text-align:center;font-size:.82rem;font-weight:700;color:{TXT};font-family:inherit;background:{BG};-moz-appearance:textfield;flex-shrink:0}}
    .sg-in::-webkit-outer-spin-button,.sg-in::-webkit-inner-spin-button{{-webkit-appearance:none;margin:0}}
    .sg-in:focus{{outline:none;border-color:{T};background:{WHT}}}
    .sg-x{{color:{DIM};font-weight:700;flex-shrink:0}}
    .bracket-leyenda{{font-size:.72rem;color:{MUT};margin:0 0 14px;padding:8px 12px;background:{GRY};border-radius:6px;line-height:1.45;max-width:760px}}
    .bracket-leyenda b{{color:{T}}}
    @media(max-width:640px){{ body{{padding:14px 10px}} h1{{font-size:1.2rem}} }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <a class="back" href="/">&#8592; Volver</a>
    <h1>Simulá las llaves</h1>
    <button class="reset" onclick="resetSim()">&#8635; Resetear</button>
  </div>
  <p class="intro">Primero cargá los resultados que faltan en cada grupo (los ya jugados quedan fijos). El bracket de abajo se arma solo con la lógica oficial de FIFA. Después hacé clic en el ganador de cada llave para avanzar hasta la final. Se guarda solo.</p>

  <div class="sec-t sec-tog" onclick="toggleGroups()">
    <span>1 · Resultados de los grupos</span>
    <span class="tog-btn" id="grp-tog">&#9650; CERRAR</span>
  </div>
  <div id="groups-wrap"><div id="groups" class="sgrid"></div></div>

  <div class="sec-t">2 · Tu bracket</div>
  <p class="bracket-leyenda"><b>Tu simulación.</b> El R32 se recalcula al toque con cada resultado que cargás (puntos, diferencia de gol, goles a favor y Anexo C, igual que el real). Hacé clic en un equipo para elegir quién pasa de ronda.</p>
  <div class="llaves-wrap">
    {_render_llaves(matchups)}
  </div>
  {_render_mobile_bracket(matchups)}
</div>

<script src="/sim-engine.js"></script>
<script src="/bracket.js"></script>
<script>
var SIM = null;
var RES = loadRes();   // resultados pendientes que carga el usuario: {{clave:{{h,a}}}}

function loadRes(){{ try {{ return JSON.parse(localStorage.getItem('sim_res')) || {{}}; }} catch(e){{ return {{}}; }} }}
function saveRes(){{ localStorage.setItem('sim_res', JSON.stringify(RES)); }}
function mkey(m){{ return m.h + '|' + m.a; }}
function pad2(n){{ return n < 10 ? '0' + n : '' + n; }}

// HTML bandera+nombre, idéntico a traducir() del server (mismo data-html que propaga el bracket)
function teamHtml(api){{
  var iso = SIM.iso[api], es = SIM.name[api] || api;
  var img = iso ? '<img src="/flags/20x15/' + iso + '.png" alt="' + es + '" width="20" height="15" loading="lazy" style="vertical-align:middle;margin-right:6px;flex-shrink:0">' : '';
  return img + es;
}}

// clona los grupos y aplica los resultados cargados (jugado solo si tiene los DOS goles)
function appliedGroups(){{
  var g = JSON.parse(JSON.stringify(SIM.groups));
  Object.keys(g).forEach(function(L){{
    g[L].matches.forEach(function(m){{
      if(!m.played){{
        var r = RES[mkey(m)];
        if(r && r.h !== undefined && r.h !== '' && r.a !== undefined && r.a !== ''){{
          m.played = true; m.hg = parseInt(r.h,10)||0; m.ag = parseInt(r.a,10)||0;
        }}
      }}
    }});
  }});
  return g;
}}

// ── R32: regenerar las cards igual que _match_card/_team_row del server ──────
function teamRow(api, mid){{
  var h = teamHtml(api), safe = h.replace(/"/g,'&quot;');
  return '<div class="team-row" data-mid="' + mid + '" data-name="' + api + '" data-html="' + safe + '" onclick="pickWinner(this)">' + h + '</div>';
}}
function matchCard(m){{
  var num = m.partido, mid = '' + num, ks = SIM.schedule['' + num] || ['',''];
  return '<div class="mc" data-mid="' + mid + '">' +
    '<div class="mc-label"><span>Partido ' + pad2(num) + '</span><span class="mc-label-r"></span></div>' +
    teamRow(m.e1, mid) + teamRow(m.e2, mid) +
    '<div class="mc-meta"><span class="r32-dt" data-utc="' + ks[0] + '"></span>' +
    (ks[1] ? '<span class="venue">' + ks[1] + '</span>' : '') + '</div></div>';
}}
function r32Inner(ms){{
  var h = '';
  for(var i=0;i<ms.length;i+=2){{ h += '<div class="par">' + matchCard(ms[i]) + (ms[i+1]?matchCard(ms[i+1]):'') + '</div>'; }}
  return h;
}}
function r32Names(mid){{
  var c = document.querySelector('.mc[data-mid="' + mid + '"]');
  return c ? [].slice.call(c.querySelectorAll('.team-row[data-name]')).map(function(r){{return r.dataset.name;}}) : [];
}}

// al cambiar el R32, descartar las elecciones de eliminatoria que dejaron de ser válidas
function revalidate(){{
  for(var n=73;n<=88;n++){{
    var k=''+n, nm=r32Names(k);
    if(S[k] && S[k].winner && nm.indexOf(S[k].winner.name)<0) delete S[k];
  }}
  SLOT_ORDER.forEach(function(slot){{
    if(slot==='slot-tercer') return;
    var fw = feedersOf(slot).map(getWinner).filter(Boolean).map(function(w){{return w.name;}});
    if(S[slot] && S[slot].winner && fw.indexOf(S[slot].winner.name)<0){{
      delete S[slot].winner; if(S[slot].loser) delete S[slot].loser;
    }}
  }});
  save();
}}

function updateBracket(){{
  var sim = {{groups:appliedGroups(), annexC:SIM.annexC, bracket:SIM.bracket, slotToPartido:SIM.slotToPartido}};
  var r32 = SimEngine.buildR32(sim), left = r32.slice(0,8), right = r32.slice(8);
  var rl = document.getElementById('r32-left'), rr = document.getElementById('r32-right');
  if(rl) rl.innerHTML = r32Inner(left);
  if(rr) rr.innerHTML = r32Inner(right);
  var mb = document.getElementById('mb-r32');
  if(mb) mb.innerHTML = r32Inner(left) + r32Inner(right);
  applyDataUtc();
  revalidate();
  restore();          // re-aplica las elecciones válidas y repinta los slots
  scaleBracket();
}}

// ── Editores de grupo ───────────────────────────────────────────────────────
function standHtml(L, g){{
  var grp = g[L], st = SimEngine.computeStats(grp.teams, grp.matches);
  var rk = SimEngine.rankGroup(grp.teams, st, grp.matches);
  return rk.map(function(t,i){{
    var s = st[t];
    return '<div class="sg-r"><span class="sg-p">' + (i+1) + '</span>' +
      '<span class="sg-t">' + teamHtml(t) + '</span>' +
      '<span class="sg-dg">' + (s.gd>0?'+':'') + s.gd + '</span>' +
      '<span class="sg-pts">' + s.pts + '</span></div>';
  }}).join('');
}}
function matchesHtml(L){{
  return SIM.groups[L].matches.map(function(m){{
    if(m.played) return '';                 // jugado real → fijo
    var k = mkey(m), r = RES[k] || {{}};
    var inp = function(side){{
      var v = (r[side]!==undefined?r[side]:'');
      return '<input class="sg-in" type="number" min="0" inputmode="numeric" value="' + v +
             '" oninput="setScore(\\'' + k + '\\',\\'' + side + '\\',this.value)">';
    }};
    return '<div class="sg-mr"><span class="sg-mt">' + teamHtml(m.h) + '</span>' +
      inp('h') + '<span class="sg-x">-</span>' + inp('a') +
      '<span class="sg-mt a">' + teamHtml(m.a) + '</span></div>';
  }}).join('');
}}
function renderGroups(){{
  var g = appliedGroups(), html = '';
  Object.keys(g).sort().forEach(function(L){{
    var mh = matchesHtml(L);
    html += '<div class="sg"><div class="sg-h">Grupo ' + L + '</div>' +
      '<div id="stand-' + L + '">' + standHtml(L,g) + '</div>' +
      (mh ? '<div class="sg-m">' + mh + '</div>' : '') + '</div>';
  }});
  document.getElementById('groups').innerHTML = html;
}}
function refreshStandings(){{
  var g = appliedGroups();
  Object.keys(SIM.groups).forEach(function(L){{
    var el = document.getElementById('stand-' + L);
    if(el) el.innerHTML = standHtml(L,g);
  }});
}}
function setScore(k, side, val){{
  RES[k] = RES[k] || {{}};
  if(val === '') delete RES[k][side]; else RES[k][side] = val;
  if(RES[k].h === undefined && RES[k].a === undefined) delete RES[k];
  saveRes();
  refreshStandings();   // tablas sin re-render de inputs (no se pierde el foco)
  updateBracket();
}}
function toggleGroups(){{
  var w = document.getElementById('groups-wrap'), t = document.getElementById('grp-tog');
  var closed = w.classList.toggle('collapsed');
  t.innerHTML = closed ? '&#9660; ABRIR' : '&#9650; CERRAR';
  localStorage.setItem('sim_grp_closed', closed ? '1' : '0');
}}
function resetSim(){{
  RES = {{}}; saveRes();
  resetBracket();       // limpia las elecciones de eliminatoria (bracket.js)
  renderGroups();
  updateBracket();
}}

fetch('/api/sim').then(function(r){{return r.json();}}).then(function(d){{
  SIM = d;
  load();               // estado del bracket (bracket.js, key 'wc26sim')
  renderGroups();
  if(localStorage.getItem('sim_grp_closed') === '1'){{
    document.getElementById('groups-wrap').classList.add('collapsed');
    document.getElementById('grp-tog').innerHTML = '&#9660; ABRIR';
  }}
  updateBracket();
  window.addEventListener('resize', scaleBracket);
}}).catch(function(e){{
  document.getElementById('groups').innerHTML = '<p style="color:#999">No se pudo cargar el simulador.</p>';
}});
</script>
</body>
</html>"""
