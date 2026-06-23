/* Motor de tablas portado de standings.py / bracket.py — para el simulador.
   DEBE dar idéntico al Python (hay un test de paridad: test_sim_parity.py).
   Sin FIFA ranking ni tarjetas (el bracket en vivo usa fifa=None y cards=0). */
(function (global) {
  "use strict";

  // m = {h, a, hg, ag, played}  (tarjetas hy/ay/hr/ar opcionales, default 0)
  function computeStats(teams, matches) {
    var st = {}, set = {};
    teams.forEach(function (t) {
      st[t] = { name: t, pj: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0, yc: 0, rc: 0, fifa: 999 };
      set[t] = 1;
    });
    matches.forEach(function (m) {
      if (!m.played) return;
      if (!set[m.h] || !set[m.a]) return;
      var H = st[m.h], A = st[m.a];
      H.pj++; A.pj++;
      H.gf += m.hg; H.ga += m.ag; A.gf += m.ag; A.ga += m.hg;
      H.yc += (m.hy || 0); A.yc += (m.ay || 0); H.rc += (m.hr || 0); A.rc += (m.ar || 0);
      if (m.hg > m.ag) { H.w++; H.pts += 3; A.l++; }
      else if (m.hg === m.ag) { H.d++; H.pts++; A.d++; A.pts++; }
      else { A.w++; A.pts += 3; H.l++; }
    });
    Object.keys(st).forEach(function (t) {
      st[t].gd = st[t].gf - st[t].ga;
      st[t].fp = -(st[t].yc + st[t].rc * 3);
    });
    return st;
  }

  function _key(team, stats, h2h) {
    var s = stats[team], h = h2h[team];
    // mismos 7 criterios y orden que _break_tie en standings.py
    return [h.pts, h.gd, h.gf, s.gd, s.gf, s.fp, -s.fifa];
  }
  function _cmpDesc(a, b) {  // lexicográfico descendente
    for (var i = 0; i < a.length; i++) { if (a[i] !== b[i]) return b[i] - a[i]; }
    return 0;
  }
  function _breakTie(tied, stats, matches) {
    if (tied.length === 1) return tied.slice();
    var h2h = computeStats(tied, matches);
    var keys = {};
    tied.forEach(function (t) { keys[t] = _key(t, stats, h2h); });
    var arr = tied.slice();
    // sort estable: empate total → orden original (igual que sorted(reverse=True) en Python)
    arr.sort(function (a, b) {
      var c = _cmpDesc(keys[a], keys[b]);
      return c !== 0 ? c : (tied.indexOf(a) - tied.indexOf(b));
    });
    return arr;
  }

  function rankGroup(teams, stats, matches) {
    var byPts = {};
    teams.forEach(function (t) { var p = stats[t].pts; (byPts[p] = byPts[p] || []).push(t); });
    var pts = Object.keys(byPts).map(Number).sort(function (a, b) { return b - a; });
    var out = [];
    pts.forEach(function (p) {
      var g = byPts[p];
      if (g.length === 1) out.push(g[0]);
      else _breakTie(g, stats, matches).forEach(function (t) { out.push(t); });
    });
    return out;
  }

  // rankear los 12 terceros (sin H2H, solo overall) y devolver los 8 mejores
  function rankThirds(thirds) {  // thirds = [{team, group, stats}]
    function key(e) {
      var s = e.stats;
      return [s.pts, s.gd, s.gf, s.fp, -s.fifa];
    }
    var arr = thirds.slice();
    arr.sort(function (a, b) {
      var c = _cmpDesc(key(a), key(b));
      return c !== 0 ? c : (thirds.indexOf(a) - thirds.indexOf(b));
    });
    return arr;
  }

  // { letra: {ranked:[teams], stats} } a partir de sim.groups
  function computeGroups(groups) {
    var out = {};
    Object.keys(groups).forEach(function (g) {
      var grp = groups[g];
      var stats = computeStats(grp.teams, grp.matches);
      out[g] = { ranked: rankGroup(grp.teams, stats, grp.matches), stats: stats };
    });
    return out;
  }

  // { partido: equipo } para los slots de 3.º, vía Anexo C (port de assign_thirds_to_slots)
  function assignThirds(gr, annexC, slotToPartido) {
    var thirds = [];
    Object.keys(gr).forEach(function (g) {
      var r = gr[g].ranked;
      if (r.length >= 3) thirds.push({ team: r[2], group: g, stats: gr[g].stats[r[2]] });
    });
    if (thirds.length < 8) return {};
    var top8 = rankThirds(thirds).slice(0, 8);
    var key = top8.map(function (t) { return t.group; }).sort().join("");
    var assignment = annexC[key];
    if (!assignment) return {};
    var g2t = {};
    top8.forEach(function (t) { g2t[t.group] = t.team; });
    var out = {};
    Object.keys(assignment).forEach(function (slot) {
      var p = slotToPartido[slot], team = g2t[assignment[slot]];
      if (p && team) out[p] = team;
    });
    return out;
  }

  // arma los 16 cruces de R32 (port de build_round_of_32)
  function buildR32(sim) {
    var gr = computeGroups(sim.groups);
    var slotThirds = assignThirds(gr, sim.annexC, sim.slotToPartido);
    function resolve(spec, partido) {
      var kind = spec[0], grp = spec[1];
      if (kind === "1" || kind === "2") {
        var r = (gr[grp] || {}).ranked || [];
        return r[kind === "1" ? 0 : 1] || (kind + "° Grp " + grp);
      }
      return slotThirds[partido] || ("3° (" + grp + ")");
    }
    return sim.bracket.map(function (b) {
      return { partido: b[0], e1: resolve(b[1], b[0]), e2: resolve(b[2], b[0]) };
    });
  }

  var API = {
    computeStats: computeStats, rankGroup: rankGroup, rankThirds: rankThirds,
    computeGroups: computeGroups, assignThirds: assignThirds, buildR32: buildR32,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  global.SimEngine = API;
})(typeof window !== "undefined" ? window : globalThis);
