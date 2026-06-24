/*
 * Aviso emergente para los visitantes de Mejor Tercero.
 * Trae /api/announcement; si está activo y no fue descartado, muestra un modal
 * de marca con la opción "No volver a mostrar" (recordada en localStorage por id).
 * Self-contained: estilos inline, sin dependencias del CSS del sitio.
 */
(function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function escAttr(s) { return esc(s).replace(/"/g, '&quot;'); }

  var KEY = 'mt_ann_dismissed';

  fetch('/api/announcement', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (a) {
      if (!a || !a.active || (!a.title && !a.body)) return;
      // Si el visitante eligió "no volver a mostrar" ESTE aviso, no lo mostramos.
      try {
        if (a.dismissible && localStorage.getItem(KEY) === String(a.id)) return;
      } catch (e) { /* sin localStorage: lo mostramos igual */ }
      show(a);
    })
    .catch(function () { /* silencioso: el aviso es opcional */ });

  function show(a) {
    var ACCENT = ({ info: '#c2410c', success: '#16a34a', warning: '#d97706' })[a.style] || '#c2410c';
    var SANS = '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif';

    var ov = document.createElement('div');
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-modal', 'true');
    ov.style.cssText = 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;' +
      'justify-content:center;padding:20px;background:rgba(33,28,20,.55);font-family:' + SANS;

    var card = document.createElement('div');
    card.style.cssText = 'background:#faf8f4;max-width:440px;width:100%;border-top:6px solid ' + ACCENT +
      ';box-shadow:0 18px 50px rgba(0,0,0,.32);padding:26px 24px 18px;position:relative;animation:mtAnnIn .22s ease';

    var h = '';
    h += '<button id="mtAnnX" aria-label="Cerrar" style="position:absolute;top:8px;right:12px;border:none;' +
         'background:none;font-size:24px;line-height:1;color:#b09880;cursor:pointer">×</button>';
    if (a.title) h += '<h3 style="font-size:1.18rem;font-weight:800;color:#211c14;margin:0 0 8px;padding-right:22px">' + esc(a.title) + '</h3>';
    if (a.body)  h += '<p style="font-size:.92rem;line-height:1.55;color:#4a4034;margin:0 0 16px;white-space:pre-wrap">' + esc(a.body) + '</p>';
    var ctaUrl = /^https?:\/\//i.test(a.cta_url || '') ? a.cta_url : '';  // solo http(s): bloquea javascript:/data:
    if (a.cta_text && ctaUrl) {
      h += '<a href="' + escAttr(ctaUrl) + '" target="_blank" rel="noopener" style="display:inline-block;' +
           'background:' + ACCENT + ';color:#fff;font-size:.82rem;font-weight:700;letter-spacing:.04em;' +
           'text-transform:uppercase;padding:10px 18px;text-decoration:none;margin-bottom:14px">' + esc(a.cta_text) + '</a>';
    }
    h += '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;' +
         'border-top:1px solid #e8ddd0;padding-top:12px;margin-top:4px">';
    h += a.dismissible
      ? '<label style="display:flex;align-items:center;gap:7px;font-size:.78rem;color:#7c6a58;cursor:pointer">' +
        '<input type="checkbox" id="mtAnnNo" style="accent-color:' + ACCENT + '">No volver a mostrar</label>'
      : '<span></span>';
    h += '<button id="mtAnnClose" style="border:none;background:' + ACCENT + ';color:#fff;font-size:.78rem;' +
         'font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding:9px 18px;cursor:pointer">Entendido</button>';
    h += '</div>';
    card.innerHTML = h;

    if (!document.getElementById('mtAnnStyle')) {
      var st = document.createElement('style');
      st.id = 'mtAnnStyle';
      st.textContent = '@keyframes mtAnnIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}';
      document.head.appendChild(st);
    }

    ov.appendChild(card);
    document.body.appendChild(ov);

    function close() {
      var no = document.getElementById('mtAnnNo');
      if (no && no.checked) { try { localStorage.setItem(KEY, String(a.id)); } catch (e) {} }
      ov.remove();
    }
    document.getElementById('mtAnnClose').onclick = close;
    document.getElementById('mtAnnX').onclick = close;
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    document.addEventListener('keydown', function onEsc(e) {
      if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onEsc); }
    });
  }
})();
