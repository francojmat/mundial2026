// SSR de páginas internas vía Cloudflare Pages Functions.
// Humanos: context.next() → Pages sirve el shell estático normal (cero riesgo).
// Bots (Google/IA/preview social): se inyecta el contenido + title/description/JSON-LD.

const SITE = "https://mejortercero.online";
const BOT_RE = /bot|crawl|spider|slurp|claude|gpt|openai|perplexity|googlebot|bingbot|applebot|ccbot|bytespider|facebookexternalhit|meta-external|linkedin|slack|whatsapp|telegram|discord|embedly|quora|pinterest|reddit|baidu|yandex|duckduck|petal|amazonbot|twitterbot/i;

function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function firstMatch(re, s) { const m = re.exec(s); return m ? m[1].trim() : ""; }

// JSON de la rama 'data' parseado (cacheado 20s en el edge).
async function getDataJson(file, waitUntil) {
  const cache = caches.default;
  const ck = new Request("https://data.internal/" + file);
  let txt = null;
  const hit = await cache.match(ck);
  if (hit) txt = await hit.text();
  else {
    const r = await fetch("https://raw.githubusercontent.com/francojmat/mundial2026/data/" + file,
                          { cf: { cacheTtl: 10 } });
    if (r.ok) {
      txt = await r.text();
      waitUntil(cache.put(ck, new Response(txt,
        { headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=20" } })));
    }
  }
  if (!txt) return null;
  try { return JSON.parse(txt); } catch (e) { return null; }
}

// Construye title/description/JSON-LD por entidad a partir del fragmento HTML.
function buildMeta(cfg, frag, key, url) {
  const pageUrl = SITE + url.pathname + url.search;
  let title, desc, jsonld = "";
  if (cfg.type === "partido") {
    const re = /class="mt-tn">([^<]+)</g; const tn = []; let m;
    while ((m = re.exec(frag)) && tn.length < 2) tn.push(m[1].trim());
    const t1 = tn[0] || "Partido", t2 = tn[1] || "";
    const meta = firstMatch(/class="mt-meta">([^<]+)</, frag);
    const venue = firstMatch(/class="mt-venue">([^<]+)</, frag);
    const scs = [...frag.matchAll(/class="mt-sc">(\d+)</g)].map((x) => x[1]);
    const res = scs.length >= 2 ? ` Resultado: ${t1} ${scs[0]}-${scs[1]} ${t2}.` : "";
    title = t2 ? `${t1} vs ${t2} · Mundial 2026` : "Ver Partido · Mundial 2026";
    desc = `${meta ? meta + ". " : ""}${venue ? venue + ". " : ""}Alineaciones, cronología, estadísticas e historial.${res}`;
    const ld = {
      "@context": "https://schema.org", "@type": "SportsEvent",
      name: t2 ? `${t1} vs ${t2}` : title, sport: "Fútbol",
      eventStatus: scs.length >= 2 ? "https://schema.org/EventCompleted" : "https://schema.org/EventScheduled",
      superEvent: { "@type": "SportsEvent", name: "Copa Mundial de la FIFA 2026" }, url: pageUrl,
    };
    const dm = /(\d{2})\/(\d{2})\/(\d{4})/.exec(meta);
    if (dm) ld.startDate = `${dm[3]}-${dm[2]}-${dm[1]}`;
    if (venue) ld.location = { "@type": "Place", name: venue };
    if (t2) ld.competitor = [{ "@type": "SportsTeam", name: t1 }, { "@type": "SportsTeam", name: t2 }];
    jsonld = `<script type="application/ld+json">${JSON.stringify(ld)}</script>`;
  } else {
    const team = firstMatch(/class="pl-title">(?:<img[^>]*>)?\s*([^<]+)</, frag) || decodeURIComponent(key);
    if (cfg.type === "plantel") {
      title = `Plantel de ${team} · Mundial 2026`;
      desc = `Plantel completo de ${team} en el Mundial 2026: jugadores con club y país, posiciones y director técnico.`;
    } else {
      title = `${team} en el Mundial 2026`;
      desc = `${team} en el Mundial 2026: ranking FIFA, palmarés, su grupo y sus partidos.`;
    }
    const ld = { "@context": "https://schema.org", "@type": "SportsTeam", name: team, sport: "Fútbol", url: pageUrl };
    jsonld = `<script type="application/ld+json">${JSON.stringify(ld)}</script>`;
  }
  return { title, desc, jsonld, pageUrl };
}

function injectSSR(shell, frag, cfg, key, url) {
  const meta = buildMeta(cfg, frag, key, url);
  shell = shell.replace(new RegExp('<div id="' + cfg.div + '">[\\s\\S]*?</div>'),
                        '<div id="' + cfg.div + '">' + frag + '</div>');
  shell = shell.replace(/<title>[\s\S]*?<\/title>/, '<title>' + esc(meta.title) + '</title>');
  shell = shell.replace(/<meta name="description"[^>]*>/, '<meta name="description" content="' + esc(meta.desc) + '">');
  shell = shell.replace(/<meta property="og:title"[^>]*>/, '<meta property="og:title" content="' + esc(meta.title) + '">');
  shell = shell.replace(/<meta property="og:description"[^>]*>/, '<meta property="og:description" content="' + esc(meta.desc) + '">');
  const extra = '<link rel="canonical" href="' + esc(meta.pageUrl) + '"><meta property="og:url" content="'
    + esc(meta.pageUrl) + '">' + meta.jsonld;
  shell = shell.replace('</head>', extra + '</head>');
  return shell;
}

// Handler genérico. Humanos → next() (shell estático). Bots → inyecta SSR.
export async function ssrPage(context, cfg) {
  const { request } = context;
  const url = new URL(request.url);
  const ua = request.headers.get("user-agent") || "";
  const key = url.searchParams.get(cfg.param);
  if (!(BOT_RE.test(ua) && key)) return context.next();
  try {
    const shellResp = await context.next();
    let shell = await shellResp.text();
    const data = await getDataJson(cfg.json, context.waitUntil.bind(context));
    const frag = data && data[decodeURIComponent(key)];
    if (frag) shell = injectSSR(shell, frag, cfg, key, url);
    return new Response(shell, {
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=60" },
    });
  } catch (e) {
    return context.next();   // fail-safe: shell normal
  }
}
