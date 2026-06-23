const KO_SCHED = {"r16-L-0": ["2026-07-04T21:00:00Z", "Lincoln Financial Field, Filadelfia"], "r16-L-1": ["2026-07-04T17:00:00Z", "NRG Stadium, Houston"], "r16-L-2": ["2026-07-06T19:00:00Z", "AT&T Stadium, Dallas"], "r16-L-3": ["2026-07-07T00:00:00Z", "Lumen Field, Seattle"], "r16-R-0": ["2026-07-05T20:00:00Z", "MetLife Stadium, New Jersey"], "r16-R-1": ["2026-07-06T00:00:00Z", "Estadio Azteca, CDMX"], "r16-R-2": ["2026-07-07T16:00:00Z", "Mercedes-Benz Stadium, Atlanta"], "r16-R-3": ["2026-07-07T20:00:00Z", "BC Place, Vancouver"], "qf-L-0": ["2026-07-09T20:00:00Z", "Gillette Stadium, Boston"], "qf-L-1": ["2026-07-10T19:00:00Z", "SoFi Stadium, Los \u00c1ngeles"], "qf-R-0": ["2026-07-11T21:00:00Z", "Hard Rock Stadium, Miami"], "qf-R-1": ["2026-07-12T01:00:00Z", "Arrowhead Stadium, Kansas City"], "sf-L-0": ["2026-07-14T19:00:00Z", "AT&T Stadium, Dallas"], "sf-R-0": ["2026-07-15T19:00:00Z", "Mercedes-Benz Stadium, Atlanta"]};
function fmtDate(utcStr) {
  if (!utcStr) return 'Por confirmar';
  const d = new Date(utcStr);
  try {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      weekday:'short', day:'numeric', month:'short',
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(d);
  } catch(e) {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: 'America/Argentina/Buenos_Aires',
      weekday:'short', day:'numeric', month:'short',
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(d);
  }
}
function fmtTime(utcStr) {
  if (!utcStr) return '';
  const d = new Date(utcStr);
  try {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(d);
  } catch(e) {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: 'America/Argentina/Buenos_Aires',
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(d);
  }
}
function fmtShortDate(utcStr) {
  if (!utcStr) return '';
  const d = new Date(utcStr);
  const o = { day:'2-digit', month:'2-digit' };
  try {
    return new Intl.DateTimeFormat('es-AR', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, ...o }).format(d);
  } catch(e) {
    return new Intl.DateTimeFormat('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', ...o }).format(d);
  }
}

// ── State ──────────────────────────────────────────────────────────────────
let S = {};
function load() { try { S = JSON.parse(localStorage.getItem('wc26sim') || '{}'); } catch(e) { S={}; } }
function save() { localStorage.setItem('wc26sim', JSON.stringify(S)); }

// ── Feed map (src → {next_slot, position}) ───────────────────────────────
const FEED = {
  "74":{next:"r16-L-0",pos:0}, "77":{next:"r16-L-0",pos:1},  // → P89
  "73":{next:"r16-L-1",pos:0}, "75":{next:"r16-L-1",pos:1},  // → P90
  "83":{next:"r16-L-2",pos:0}, "84":{next:"r16-L-2",pos:1},  // → P93
  "81":{next:"r16-L-3",pos:0}, "82":{next:"r16-L-3",pos:1},  // → P94
  "76":{next:"r16-R-0",pos:0}, "78":{next:"r16-R-0",pos:1},  // → P91
  "79":{next:"r16-R-1",pos:0}, "80":{next:"r16-R-1",pos:1},  // → P92
  "86":{next:"r16-R-2",pos:0}, "88":{next:"r16-R-2",pos:1},  // → P95
  "85":{next:"r16-R-3",pos:0}, "87":{next:"r16-R-3",pos:1},  // → P96
  "r16-L-0":{next:"qf-L-0",pos:0}, "r16-L-1":{next:"qf-L-0",pos:1},
  "r16-L-2":{next:"qf-L-1",pos:0}, "r16-L-3":{next:"qf-L-1",pos:1},
  "r16-R-0":{next:"qf-R-0",pos:0}, "r16-R-1":{next:"qf-R-0",pos:1},
  "r16-R-2":{next:"qf-R-1",pos:0}, "r16-R-3":{next:"qf-R-1",pos:1},
  "qf-L-0": {next:"sf-L-0",pos:0}, "qf-L-1": {next:"sf-L-0",pos:1},
  "qf-R-0": {next:"sf-R-0",pos:0}, "qf-R-1": {next:"sf-R-0",pos:1},
  "sf-L-0": {next:"slot-final",pos:0},
  "sf-R-0": {next:"slot-final",pos:1},
};

const SLOT_ORDER = [
  "r16-L-0","r16-L-1","r16-L-2","r16-L-3",
  "r16-R-0","r16-R-1","r16-R-2","r16-R-3",
  "qf-L-0","qf-L-1","qf-R-0","qf-R-1",
  "sf-L-0","sf-R-0","slot-final","slot-tercer"
];

const SLOT_LABEL = {
  "r16-L-0":"P89","r16-L-1":"P90","r16-L-2":"P93","r16-L-3":"P94",
  "r16-R-0":"P91","r16-R-1":"P92","r16-R-2":"P95","r16-R-3":"P96",
  "qf-L-0":"P97","qf-L-1":"P98","qf-R-0":"P99","qf-R-1":"P100",
  "sf-L-0":"P101","sf-R-0":"P102",
};

function feedersOf(slotId) {
  return Object.entries(FEED)
    .filter(([,v]) => v.next === slotId)
    .sort((a,b) => a[1].pos - b[1].pos)
    .map(([k]) => k);
}
function getWinner(srcId) { return S[srcId]?.winner || null; }

// ── Render de un slot de ronda posterior ──────────────────────────────────
function renderSlot(slotId) {
  if (slotId === "slot-final") { renderFinal(); return; }
  if (slotId === "slot-tercer") { renderTercer(); return; }
  const el = document.getElementById(slotId);
  if (!el) return;

  const [src0, src1] = feedersOf(slotId);
  const t0 = getWinner(src0);
  const t1 = getWinner(src1);
  const myW = S[slotId]?.winner;
  const lbl = SLOT_LABEL[slotId] || "";
  const ks = KO_SCHED[slotId];
  const dateHtml = ks ? `<span>${fmtDate(ks[0])}</span>` : '<span>Por confirmar</span>';
  const venueHtml = ks ? `<span class="venue">${ks[1]}</span>` : '';

  const mkRow = (t, idx) => {
    if (!t) return `<div class="team-row ph">— Por definir</div>`;
    const src = idx===0 ? src0 : src1;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner" : isL ? "loser" : "";
    return `<div class="team-row ${cls} fade-in"
      data-slot="${slotId}" data-src="${src}" data-name="${t.name}"
      data-html="${encodeURIComponent(t.html)}"
      onclick="pickSlotWinner(this)">${t.html}</div>`;
  };

  el.innerHTML = `
    <div class="mc-label"><span>${lbl}</span></div>
    ${mkRow(t0,0)}${mkRow(t1,1)}
    <div class="mc-meta">${dateHtml}${venueHtml}</div>`;
  el.className = "mc";

  // Si es SF y ya hay ganador pero ahora llegó el 2do equipo → calcular loser automáticamente
  if ((slotId === "sf-L-0" || slotId === "sf-R-0") && S[slotId]?.winner && t0 && t1) {
    const winName = S[slotId].winner.name;
    const loserT  = t0.name === winName ? t1 : t0;
    if (!S[slotId].loser || S[slotId].loser.name !== loserT.name) {
      S[slotId].loser = loserT;
      save();
      renderTercer();
    }
  }
}

// ── Final ─────────────────────────────────────────────────────────────────
function renderFinal() {
  const el = document.getElementById("slot-final");
  if (!el) return;
  const [src0, src1] = feedersOf("slot-final");
  const t0 = getWinner(src0), t1 = getWinner(src1);
  const myW = S["slot-final"]?.winner;

  const mkRow = (t, idx) => {
    if (!t) return `<div class="team-row ph" style="justify-content:center">— Por definir</div>`;
    const src = idx===0 ? src0 : src1;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner champion" : isL ? "loser" : "";
    return `<div class="team-row ${cls} fade-in" style="justify-content:center"
      data-slot="slot-final" data-src="${src}" data-name="${t.name}"
      data-html="${encodeURIComponent(t.html)}"
      onclick="pickSlotWinner(this)">${t.html}</div>`;
  };

  // Team rows
  el.innerHTML = mkRow(t0,0) + mkRow(t1,1);

  // Cuadro campeón separado (champ-card)
  const champCard = document.getElementById('champ-card');
  if (champCard) {
    if (myW) {
      const tmp = document.createElement('div');
      tmp.innerHTML = myW.html;
      const origImg = tmp.querySelector('img');
      const translatedName = tmp.textContent.trim();
      const flagEl = document.getElementById('champ-flag');
      flagEl.innerHTML = '';
      if (origImg) {
        const newImg = new Image(48, 36);
        newImg.src = origImg.src.replace('/20x15/','/48x36/');
        newImg.setAttribute('style','display:block;margin:0 auto;image-rendering:crisp-edges');
        flagEl.appendChild(newImg);
      }
      document.getElementById('champ-country').textContent = translatedName || myW.name;
      champCard.style.display = '';
      champCard.classList.remove('fade-in');
      void champCard.offsetWidth;
      champCard.classList.add('fade-in');
    } else {
      champCard.style.display = 'none';
    }
  }
}

// ── 3er puesto ────────────────────────────────────────────────────────────
function renderTercer() {
  const el = document.getElementById("slot-tercer");
  if (!el) return;
  const t0 = S["sf-L-0"]?.loser || null;
  const t1 = S["sf-R-0"]?.loser || null;
  const myW = S["slot-tercer"]?.winner;

  const mkRow = (t, sfSrc) => {
    if (!t) return `<div class="team-row ph" style="justify-content:center">— Por definir</div>`;
    const isW = myW?.name === t.name;
    const isL = myW && !isW;
    const cls = isW ? "winner" : isL ? "loser" : "";
    return `<div class="team-row ${cls} fade-in" style="justify-content:center"
      data-slot="slot-tercer" data-name="${t.name}"
      data-html="${encodeURIComponent(t.html)}"
      onclick="pickTercerWinner(this)">${t.html}</div>`;
  };

  // el IS the .tercer-teams div directly
  el.innerHTML = mkRow(t0,"sf-L-0") + mkRow(t1,"sf-R-0");
}

// ── Seleccionar ganador en R32 ────────────────────────────────────────────
function pickWinner(el) {
  const card = el.closest(".mc");
  const mid = card.dataset.mid;
  const name = el.dataset.name;
  const html = decodeURIComponent(el.dataset.html);

  // Update all cards with same mid (desktop + mobile)
  document.querySelectorAll('[data-mid="' + mid + '"]').forEach(function(c) {
    c.querySelectorAll(".team-row").forEach(function(r) {
      r.classList.remove("winner","loser");
      r.classList.add(r.dataset.name === name ? "winner" : "loser");
    });
  });

  S[mid] = { winner: {name, html} };
  save();
  propagate(mid);
  syncMobile();
}

// ── Seleccionar ganador en slots R16/QF/SF/Final ──────────────────────────
function pickSlotWinner(el) {
  const slotId = el.dataset.slot;
  const name   = el.dataset.name;
  const html   = decodeURIComponent(el.dataset.html);

  const slotEl = document.getElementById(slotId);
  slotEl.querySelectorAll(".team-row").forEach(r => {
    if (!r.dataset.name) return;
    r.classList.remove("winner","loser","champion");
    r.classList.add(r.dataset.name === name ? "winner" : "loser");
  });

  // Si es una SF, guardar también el perdedor para el 3er puesto
  if (slotId === "sf-L-0" || slotId === "sf-R-0") {
    const rows = [...slotEl.querySelectorAll(".team-row[data-name]")];
    const loserRow = rows.find(r => r.dataset.name !== name);
    const loserName = loserRow?.dataset.name;
    const loserHtml = loserRow ? decodeURIComponent(loserRow.dataset.html) : null;
    // Si el loserRow no existe aún (2do equipo no llegó), usar el valor ya guardado si hay
    const prevLoser = !loserName ? (S[slotId]?.loser || null) : null;
    S[slotId] = { winner: {name, html}, loser: loserName ? {name: loserName, html: loserHtml} : prevLoser };
  } else {
    S[slotId] = { winner: {name, html} };
  }

  save();
  if (slotId !== "slot-final") propagate(slotId);
  renderFinal();
  renderTercer();
  syncMobile();
}

function pickTercerWinner(el) {
  const name = el.dataset.name;
  const html = decodeURIComponent(el.dataset.html);
  const slotEl = document.getElementById("slot-tercer");
  slotEl.querySelectorAll(".team-row[data-name]").forEach(r => {
    r.classList.remove("winner","loser");
    r.classList.add(r.dataset.name === name ? "winner" : "loser");
  });
  S["slot-tercer"] = { winner: {name, html} };
  save();
  syncMobile();
}

// ── Propagación ───────────────────────────────────────────────────────────
function propagate(srcId) {
  const next = FEED[srcId]?.next;
  if (!next) return;
  if (S[next]?.winner) {
    const [s0,s1] = feedersOf(next);
    const w0 = getWinner(s0), w1 = getWinner(s1);
    if (S[next].winner.name !== w0?.name && S[next].winner.name !== w1?.name) {
      delete S[next].winner;
      if (next === "sf-L-0" || next === "sf-R-0") delete S[next].loser;
      save();
      propagate(next);
    }
  }
  renderSlot(next);
}

// ── Restaurar al cargar ───────────────────────────────────────────────────
function restore() {
  document.querySelectorAll("[data-mid]").forEach(card => {
    const mid = card.dataset.mid;
    const w = S[mid]?.winner;
    if (!w) return;
    card.querySelectorAll(".team-row[data-name]").forEach(r => {
      r.classList.remove("winner","loser");
      r.classList.add(r.dataset.name === w.name ? "winner" : "loser");
    });
  });
  SLOT_ORDER.forEach(id => renderSlot(id));
  syncMobile();
}

function resetBracket() {
  S = {};
  save();
  document.querySelectorAll("[data-mid] .team-row").forEach(r =>
    r.classList.remove("winner","loser"));
  SLOT_ORDER.forEach(id => renderSlot(id));
  syncMobile();
}

// ── Sincronizar mobile bracket con estado desktop ─────────────────────────
function syncMobile() {
  ["r16-L-0","r16-L-1","r16-L-2","r16-L-3",
   "r16-R-0","r16-R-1","r16-R-2","r16-R-3",
   "qf-L-0","qf-L-1","qf-R-0","qf-R-1",
   "sf-L-0","sf-R-0"].forEach(function(id) {
    var d = document.getElementById(id);
    var m = document.getElementById('m-' + id);
    if (d && m) { m.innerHTML = d.innerHTML; m.className = d.className; }
  });
  var df = document.getElementById('slot-final');
  var mfr = document.getElementById('m-final-rows');
  if (df && mfr) { mfr.innerHTML = df.innerHTML; }
  var dt = document.getElementById('slot-tercer');
  var mtr = document.getElementById('m-tercer-rows');
  if (dt && mtr) { mtr.innerHTML = dt.innerHTML; }
}

// ── Tabs del bracket mobile ───────────────────────────────────────────────
function mbSetRound(btn, round) {
  document.querySelectorAll('.mb-tab').forEach(function(t) { t.classList.remove('mb-active'); });
  btn.classList.add('mb-active');
  document.querySelectorAll('.mb-panel').forEach(function(p) { p.style.display = 'none'; });
  var panel = document.getElementById('mb-' + round);
  if (panel) { panel.style.display = 'block'; }
}
function applyDataUtc(root) {
  (root || document).querySelectorAll('[data-utc]').forEach(function(el) {
    el.innerHTML = el.dataset.format === 'time' ? fmtTime(el.dataset.utc)
                 : el.dataset.format === 'shortdate' ? fmtShortDate(el.dataset.utc)
                 : fmtDate(el.dataset.utc);
  });
}
function scaleBracket() {
  var wrap = document.querySelector('.llaves-wrap');
  var ll   = document.querySelector('.llaves');
  if (!wrap || !ll) return;
  ll.style.transform = '';
  wrap.style.height  = '';
  var avail = wrap.clientWidth;
  var nat   = ll.scrollWidth;
  if (nat > avail && avail > 0) {
    var s = avail / nat;
    ll.style.transform       = 'scale(' + s + ')';
    ll.style.transformOrigin = 'top left';
    wrap.style.height        = Math.ceil(ll.scrollHeight * s) + 'px';
  }
}
// ── 4.1 · Camino al título: ilumina la recorrida de un cruce hasta la final ──
function pathFrom(id) {
  const path = [id]; let cur = id;
  while (FEED[cur]) { cur = FEED[cur].next; path.push(cur); }
  return path;
}
function clearPath() {
  document.querySelectorAll('.mc.on-path').forEach(e => e.classList.remove('on-path'));
}
function highlightPath(id) {
  clearPath();
  pathFrom(id).forEach(n => {
    document.querySelectorAll('.mc[data-mid="' + n + '"]').forEach(c => c.classList.add('on-path'));
    const el = document.getElementById(n);
    if (el && el.classList.contains('mc')) el.classList.add('on-path');
  });
}
function initPath() {
  document.querySelectorAll('.llaves-wrap .mc').forEach(card => {
    const id = card.dataset.mid || card.id;
    if (!id || !FEED[id]) return;
    card.onmouseenter = function() { highlightPath(id); };
    card.onmouseleave = clearPath;
  });
}
