# -*- coding: utf-8 -*-
"""GENERADO por _extract_bracket.py — NO editar a mano. CSS+JS del bracket
compartidos entre el home en vivo y el simulador (mismo diseño y lógica)."""
from html_renderer import (T, TEL, OK, WRN, BG, WHT, BDR, BDR2, TXT, MUT,
                           DIM, GRY, _ko_schedule_json)

BRACKET_CSS = f'''
    /* ── Bracket ── */
    .llaves-wrap{{overflow:hidden;width:100%}}
    .bracket-leyenda{{font-size:.72rem;color:{MUT};margin:0 0 14px;padding:8px 12px;background:{GRY};border-radius:6px;line-height:1.45;max-width:760px}}
    .bracket-leyenda b{{color:{T}}}
    .bl-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;background:{T};animation:blink 1.4s ease-in-out infinite;vertical-align:middle;margin-right:2px}}
    .llaves{{display:flex;align-items:stretch;min-height:960px;min-width:1200px;gap:0}}

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
    .tr-lock{{width:12px;height:12px;color:{T};margin-left:auto;flex-shrink:0;opacity:.85}}
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
'''

BRACKET_JS = f'''const KO_SCHED = {_ko_schedule_json()};
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
function load() {{ try {{ S = JSON.parse(localStorage.getItem('wc26sim') || '{{}}'); }} catch(e) {{ S={{}}; }} }}
function save() {{ localStorage.setItem('wc26sim', JSON.stringify(S)); }}

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
function applyDataUtc(root) {{
  (root || document).querySelectorAll('[data-utc]').forEach(function(el) {{
    el.innerHTML = el.dataset.format === 'time' ? fmtTime(el.dataset.utc)
                 : el.dataset.format === 'shortdate' ? fmtShortDate(el.dataset.utc)
                 : fmtDate(el.dataset.utc);
  }});
}}
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
'''
