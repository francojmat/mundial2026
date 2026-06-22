/**
 * API de sugerencias + Admin + Chat IA
 * Rutas:
 *   POST /api/suggest            → guarda sugerencia en KV (público)
 *   GET  /api/suggestions?token= → lista sugerencias (solo admin)
 *   POST /api/mark-read          → marca como leídas (solo admin)
 *   POST /api/chat               → chat con Claude, genera preview (solo admin)
 *   POST /api/apply              → aplica cambio de preview a main (solo admin)
 *   POST /api/discard            → descarta preview (solo admin)
 */

const CORS_ORIGIN  = "https://mejortercero.online";
const REPO         = "francojmat/mundial2026";
const PREVIEW_URL  = "https://preview.mundial2026-d40.pages.dev/mundial2026";
const MEMORY_KEY   = "memory:changes";

function cors() {
  return {
    "Access-Control-Allow-Origin": CORS_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...cors() },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url  = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }

    if (path === "/api/live"        && request.method === "GET")  return handleLive(request, env, ctx);
    if (path === "/api/data"        && request.method === "GET")  return handleData("data.json", ctx);
    if (path === "/api/data2"       && request.method === "GET")  return handleData("data2.json", ctx);
    if (path === "/api/planteles"   && request.method === "GET")  return handleData("planteles.json", ctx);
    if (path === "/api/partidos"    && request.method === "GET")  return handleData("partidos.json", ctx);
    if (path === "/api/selecciones" && request.method === "GET")  return handleData("selecciones.json", ctx);
    if (path === "/api/metrics"     && request.method === "GET")  return handleMetrics(request, env);
    if (path === "/api/suggest"     && request.method === "POST") return handleSuggest(request, env);
    if (path === "/api/suggestions" && request.method === "GET")  return handleList(request, env);
    if (path === "/api/mark-read"   && request.method === "POST") return handleMarkRead(request, env);
    if (path === "/api/chat"        && request.method === "POST") return handleChat(request, env, ctx);
    if (path === "/api/chat-poll"   && request.method === "GET")  return handleChatPoll(request, env);
    if (path === "/api/apply"       && request.method === "POST") return handleApply(request, env);
    if (path === "/api/discard"     && request.method === "POST") return handleDiscard(request, env);

    return new Response("Not found", { status: 404 });
  },
};

// ── GET /api/data | /api/planteles | /api/partidos ────────────────────────────
// Sirve los datos desde la rama 'data' del repo (que Cloudflare Pages NO deploya).
// Cachea ~20s → el sitio se actualiza sin redeployar Pages (se acaban los 522).
async function handleData(file, ctx) {
  const cache = caches.default;
  // v2: se versiona la clave para invalidar entradas viejas pegadas en el edge cache.
  const cacheKey = new Request("https://data.internal/v2/" + file);
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  let body = "{}";
  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/francojmat/mundial2026/data/" + file,
      { cf: { cacheTtl: 10 } }
    );
    if (r.ok) body = await r.text();
  } catch (e) { /* devolvemos {} */ }

  const resp = new Response(body, {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=20",
      ...cors(),
    },
  });
  ctx.waitUntil(cache.put(cacheKey, resp.clone()));
  return resp;
}

// ── GET /api/live ────────────────────────────────────────────────────────────
// Marcadores en vivo desde API-Football, cacheados 10s (sin importar el tráfico,
// la API se pide como mucho 1 vez cada 10s → respeta el rate limit).
async function handleLive(request, env, ctx) {
  const KEY = (env.APIFOOTBALL_KEY || "").trim();
  const cache = caches.default;
  const fresh = new Request("https://live.internal/wc2026");       // respuesta servida (8s)
  const good  = new Request("https://live.internal/wc2026-good");  // último resultado NO vacío (60s)

  const hit = await cache.match(fresh);
  if (hit) return hit;

  // Estados "en vivo" (incluye entretiempo y prórroga)
  const LIVE = new Set(["1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT"]);

  let matches = null;  // null = el fetch falló; [] = no hay en vivo de verdad
  if (KEY) {
    try {
      const r = await fetch(
        "https://v3.football.api-sports.io/fixtures?league=1&season=2026",
        { headers: { "x-apisports-key": KEY }, cf: { cacheTtl: 0 } }
      );
      const data = await r.json();
      if (Array.isArray(data.response)) {
        matches = data.response
          .filter(fx => LIVE.has((fx.fixture.status || {}).short))
          .map(fx => ({
            id:      fx.fixture.id,
            status:  fx.fixture.status.short,
            elapsed: fx.fixture.status.elapsed,
            h:       fx.goals.home,
            a:       fx.goals.away,
          }));
      }
    } catch (e) { matches = null; }
  } else {
    matches = [];
  }

  if (matches && matches.length > 0) {
    // Resultado bueno → guardarlo como "último bueno" (60s)
    ctx.waitUntil(cache.put(good, new Response(JSON.stringify(matches),
      { headers: { "Cache-Control": "max-age=60" } })));
  } else {
    // Vacío o error: si hay un "último bueno" reciente, servirlo (mata el flapeo en vivo).
    // Si genuinamente no hay en vivo, el último bueno ya expiró → []
    const lg = await cache.match(good);
    matches = lg ? await lg.json() : [];
  }

  const resp = new Response(JSON.stringify({ updated: Date.now(), matches }), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=8",
      ...cors(),
    },
  });
  ctx.waitUntil(cache.put(fresh, resp.clone()));
  return resp;
}

// ── GET /api/metrics ─────────────────────────────────────────────────────────

async function handleMetrics(request, env) {
  const url = new URL(request.url);
  if (!validToken(url.searchParams.get("token") || "", env)) {
    return json({ error: "No autorizado" }, 401);
  }

  const phKey  = (env.POSTHOG_KEY || '').replace(/^﻿/, '').trim();
  const phUrl  = "https://us.posthog.com/api/projects/478313/query";
  const phHdrs = { "Authorization": `Bearer ${phKey}`, "Content-Type": "application/json" };

  const phQuery = (q) => fetch(phUrl, {
    method: "POST",
    headers: phHdrs,
    body: JSON.stringify({ query: { kind: "HogQLQuery", query: q } }),
  }).then(r => r.ok ? r.json() : null).catch(() => null);

  const [dailyRes, countriesRes, devicesRes, referrersRes, hoursRes] = await Promise.all([
    phQuery(`SELECT toDate(timestamp) AS day, count() AS pageviews, count(distinct person_id) AS users
             FROM events WHERE event = '$pageview' AND timestamp >= now() - interval 30 day
             GROUP BY day ORDER BY day`),
    phQuery(`SELECT properties.$geoip_country_name AS country, count() AS views
             FROM events WHERE event = '$pageview' AND timestamp >= now() - interval 30 day
               AND properties.$geoip_country_name IS NOT NULL AND properties.$geoip_country_name != ''
             GROUP BY country ORDER BY views DESC LIMIT 8`),
    phQuery(`SELECT properties.$device_type AS device, count() AS views
             FROM events WHERE event = '$pageview' AND timestamp >= now() - interval 30 day
               AND properties.$device_type IS NOT NULL AND properties.$device_type != ''
             GROUP BY device ORDER BY views DESC`),
    phQuery(`SELECT properties.$referring_domain AS ref, count() AS views
             FROM events WHERE event = '$pageview' AND timestamp >= now() - interval 7 day
               AND properties.$referring_domain IS NOT NULL
               AND properties.$referring_domain != '' AND properties.$referring_domain != '$direct'
             GROUP BY ref ORDER BY views DESC LIMIT 6`),
    phQuery(`SELECT toHour(toTimezone(timestamp, 'America/Argentina/Buenos_Aires')) AS hour, count() AS views
             FROM events WHERE event = '$pageview' AND timestamp >= now() - interval 7 day
             GROUP BY hour ORDER BY hour`),
  ]);

  const rows    = (dailyRes?.results || []).map(r => ({ day: r[0], views: Number(r[1]), users: Number(r[2]) }));
  const today   = new Date().toISOString().split("T")[0];
  const weekAgo = new Date(Date.now() - 6 * 86400000).toISOString().split("T")[0];

  return json({
    daily:       rows,
    today_views: rows.find(r => r.day === today)?.views ?? 0,
    today_users: rows.find(r => r.day === today)?.users ?? 0,
    week_views:  rows.filter(r => r.day >= weekAgo).reduce((s, r) => s + r.views, 0),
    month_views: rows.reduce((s, r) => s + r.views, 0),
    countries:   (countriesRes?.results  || []).map(r => ({ country: r[0], views: Number(r[1]) })),
    devices:     (devicesRes?.results    || []).map(r => ({ device:  r[0], views: Number(r[1]) })),
    referrers:   (referrersRes?.results  || []).map(r => ({ ref:     r[0], views: Number(r[1]) })),
    hours:       (hoursRes?.results      || []).map(r => ({ hour: Number(r[0]), views: Number(r[1]) })),
  });
}

// ── POST /api/suggest ────────────────────────────────────────────────────────

async function handleSuggest(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  const msg  = String(body.msg  || "").trim().slice(0, 600);
  const name = String(body.name || "").trim().slice(0, 80) || "Anónimo";
  const page = String(body.page || "").trim().slice(0, 100);

  if (!msg) return json({ error: "El mensaje no puede estar vacío" }, 400);

  const ip     = request.headers.get("CF-Connecting-IP") || "unknown";
  const rlKey  = `rl:${ip}`;
  const rlData = JSON.parse(await env.SUGGESTIONS.get(rlKey) || "[]");
  const since  = Date.now() - 30 * 60 * 1000;
  const recent = rlData.filter(ts => ts > since);

  if (recent.length >= 3) {
    return json({ error: "Límite alcanzado. Intentá en 30 minutos." }, 429);
  }

  const id  = `sug:${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const sug = { id, name, msg, page, ts: new Date().toISOString(), read: false };

  await env.SUGGESTIONS.put(id, JSON.stringify(sug), { expirationTtl: 86400 * 90 });
  await env.SUGGESTIONS.put(rlKey, JSON.stringify([...recent, Date.now()]), { expirationTtl: 3600 });

  return json({ ok: true }, 201);
}

// ── GET /api/suggestions?token= ──────────────────────────────────────────────

async function handleList(request, env) {
  const url = new URL(request.url);
  if (!await validToken(url.searchParams.get("token") || "", env)) {
    return json({ error: "No autorizado" }, 401);
  }

  const list  = await env.SUGGESTIONS.list({ prefix: "sug:" });
  const items = await Promise.all(
    list.keys.map(async k => {
      const v = await env.SUGGESTIONS.get(k.name);
      return v ? JSON.parse(v) : null;
    })
  );

  return json(items.filter(Boolean).sort((a, b) => new Date(b.ts) - new Date(a.ts)));
}

// ── POST /api/mark-read ──────────────────────────────────────────────────────

async function handleMarkRead(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  if (!await validToken(body.token || "", env)) {
    return json({ error: "No autorizado" }, 401);
  }

  const ids = Array.isArray(body.ids) ? body.ids : [];
  await Promise.all(ids.map(async id => {
    const v = await env.SUGGESTIONS.get(id);
    if (!v) return;
    const sug = JSON.parse(v);
    sug.read = true;
    await env.SUGGESTIONS.put(id, JSON.stringify(sug), { expirationTtl: 86400 * 90 });
  }));

  return json({ ok: true });
}

// ── POST /api/chat ─────────────────────────────────────────────────────────────
// Responde inmediatamente con un jobId y procesa en background para evitar timeout 524.

async function handleChat(request, env, ctx) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  if (!validToken(body.token || "", env)) return json({ error: "No autorizado" }, 401);

  const userMessage = String(body.message || "").trim().slice(0, 3000);
  if (!userMessage) return json({ error: "Mensaje vacío" }, 400);

  const jobId = `job:${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  await env.SUGGESTIONS.put(jobId, JSON.stringify({ status: "pending" }), { expirationTtl: 600 });

  ctx.waitUntil(processChatJob(jobId, body, env));

  return json({ jobId, status: "pending" });
}

// ── GET /api/chat-poll?jobId=&token= ──────────────────────────────────────────

async function handleChatPoll(request, env) {
  const url   = new URL(request.url);
  const jobId = url.searchParams.get("jobId") || "";
  const token = url.searchParams.get("token") || "";

  if (!validToken(token, env))  return json({ error: "No autorizado" }, 401);
  if (!jobId)                   return json({ error: "Falta jobId" }, 400);

  const raw = await env.SUGGESTIONS.get(jobId);
  if (!raw) return json({ status: "not_found" }, 404);

  return json(JSON.parse(raw));
}

// ── processChatJob (background) ───────────────────────────────────────────────

async function processChatJob(jobId, body, env) {
  const saveResult = (data) =>
    env.SUGGESTIONS.put(jobId, JSON.stringify(data), { expirationTtl: 600 });

  try {
    const history         = Array.isArray(body.history) ? body.history.slice(-12) : [];
    const rendererContent = await fetchGitHubFile(env, "html_renderer.py", "main");
    const changeLog       = await loadChangeLog(env);

    const messages = [...history, { role: "user", content: body.message }];

    const claudeResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key":         env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
      },
      body: JSON.stringify({
        model:      "claude-sonnet-4-6",
        max_tokens: 16000,
        system:     buildSystemPrompt(rendererContent, changeLog),
        messages,
      }),
    });

    if (!claudeResp.ok) {
      const err = await claudeResp.text();
      return saveResult({ status: "done", result: { reply: `⚠️ Error Claude: ${err}`, previewUrl: null, hasPendingChange: false } });
    }

    const claudeData = await claudeResp.json();
    const rawReply   = claudeData.content?.[0]?.text || "";

    let parsed;
    try {
      const cleaned = rawReply.replace(/^```json\s*/i, "").replace(/\s*```$/, "").trim();
      parsed = JSON.parse(cleaned);
    } catch {
      parsed = { type: "message", text: rawReply };
    }

    // Single patch
    if (parsed.type === "patch" && parsed.file && parsed.old != null && parsed.new != null) {
      const result = await applyAndCommit(env, [{ file: parsed.file, old: parsed.old, new: parsed.new }], parsed.description || "cambio AI");
      return saveResult({ status: "done", result });
    }

    // Multi-file patches
    if (parsed.type === "patches" && Array.isArray(parsed.patches) && parsed.patches.length) {
      const result = await applyAndCommit(env, parsed.patches, parsed.description || "cambio AI");
      return saveResult({ status: "done", result });
    }

    // Conversation
    return saveResult({ status: "done", result: { reply: parsed.text || rawReply, previewUrl: null, hasPendingChange: false } });

  } catch (e) {
    return saveResult({ status: "done", result: { reply: `⚠️ Error interno: ${e.message}`, previewUrl: null, hasPendingChange: false } });
  }
}

// ── POST /api/apply ───────────────────────────────────────────────────────────

async function handleApply(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  if (!validToken(body.token || "", env)) return json({ error: "No autorizado" }, 401);

  const filename = String(body.file || "").trim();
  if (!filename) return json({ error: "Falta el nombre del archivo" }, 400);

  const ghHeaders = ghAuthHeaders(env);

  // Get file content from preview branch
  const previewResp = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${filename}?ref=preview`,
    { headers: ghHeaders }
  );
  if (!previewResp.ok) return json({ error: "No se encontró el archivo en preview" }, 502);
  const previewFile = await previewResp.json();

  // Get SHA from main branch (needed for update)
  const mainResp = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${filename}?ref=main`,
    { headers: ghHeaders }
  );
  let mainSha = null;
  if (mainResp.ok) {
    const mainFile = await mainResp.json();
    mainSha = mainFile.sha;
  }

  // The content from GitHub is already base64; we just pass it through
  const content = previewFile.content.replace(/\n/g, "");

  // Retry up to 3 times — cron jobs can push to main between our GET and PUT
  let updateResp;
  let currentSha = mainSha;
  for (let attempt = 0; attempt < 3; attempt++) {
    const updateBody = {
      message: `AI apply: ${body.description || filename}`,
      content,
      branch: "main",
    };
    if (currentSha) updateBody.sha = currentSha;

    updateResp = await fetch(`https://api.github.com/repos/${REPO}/contents/${filename}`, {
      method:  "PUT",
      headers: { ...ghHeaders, "Content-Type": "application/json" },
      body:    JSON.stringify(updateBody),
    });

    if (updateResp.ok) break;

    if (updateResp.status === 409 && attempt < 2) {
      // SHA stale — refetch and retry
      const fresh = await fetch(
        `https://api.github.com/repos/${REPO}/contents/${filename}?ref=main`,
        { headers: ghHeaders }
      );
      if (fresh.ok) currentSha = (await fresh.json()).sha;
      continue;
    }

    const err = await updateResp.text();
    return json({ error: `GitHub error: ${err}` }, 502);
  }

  if (!updateResp.ok) {
    const err = await updateResp.text();
    return json({ error: `GitHub error tras reintentos: ${err}` }, 502);
  }

  // Persist this change to memory
  await appendChangeLog(env, {
    file:        filename,
    description: body.description || filename,
  });

  return json({ ok: true });
}

// ── POST /api/discard ─────────────────────────────────────────────────────────

async function handleDiscard(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  if (!validToken(body.token || "", env)) return json({ error: "No autorizado" }, 401);

  const ghHeaders = ghAuthHeaders(env);

  await fetch(`https://api.github.com/repos/${REPO}/git/refs/heads/preview`, {
    method:  "DELETE",
    headers: ghHeaders,
  });

  return json({ ok: true });
}

// ── helpers ──────────────────────────────────────────────────────────────────

function validToken(token, env) {
  if (!token || !env.ADMIN_TOKEN_HASH) return false;
  const stored = env.ADMIN_TOKEN_HASH.replace(/^﻿/, "").trim();
  return token === stored;
}

function ghAuthHeaders(env) {
  return {
    "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
    "User-Agent":    "mundial2026-bot",
    "Accept":        "application/vnd.github+json",
  };
}

async function fetchGitHubFile(env, path, branch = "main") {
  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${path}?ref=${branch}`,
    { headers: ghAuthHeaders(env) }
  );
  if (!resp.ok) return null;
  const data = await resp.json();
  // Decode base64 → string (unicode-safe)
  const b64 = data.content.replace(/\n/g, "");
  return b64ToUtf8(b64);
}

async function commitToPreview(env, filename, content, message) {
  const BRANCH    = "preview";
  const ghHeaders = ghAuthHeaders(env);
  const jsonHdr   = { ...ghHeaders, "Content-Type": "application/json" };

  // Ensure preview branch exists
  const branchResp = await fetch(
    `https://api.github.com/repos/${REPO}/git/refs/heads/${BRANCH}`,
    { headers: ghHeaders }
  );

  if (!branchResp.ok) {
    // Create preview from main
    const mainRef = await fetch(
      `https://api.github.com/repos/${REPO}/git/refs/heads/main`,
      { headers: ghHeaders }
    );
    if (!mainRef.ok) return false;
    const mainData = await mainRef.json();
    const createResp = await fetch(`https://api.github.com/repos/${REPO}/git/refs`, {
      method:  "POST",
      headers: jsonHdr,
      body:    JSON.stringify({ ref: `refs/heads/${BRANCH}`, sha: mainData.object.sha }),
    });
    if (!createResp.ok) return false;
  }

  // Get current file SHA on preview (for update)
  const fileResp = await fetch(
    `https://api.github.com/repos/${REPO}/contents/${filename}?ref=${BRANCH}`,
    { headers: ghHeaders }
  );
  let fileSha = null;
  if (fileResp.ok) {
    const fileData = await fileResp.json();
    fileSha = fileData.sha;
  }

  // Commit
  const putBody = {
    message: `AI: ${message}`,
    content: utf8ToB64(content),
    branch:  BRANCH,
  };
  if (fileSha) putBody.sha = fileSha;

  const putResp = await fetch(`https://api.github.com/repos/${REPO}/contents/${filename}`, {
    method:  "PUT",
    headers: jsonHdr,
    body:    JSON.stringify(putBody),
  });

  return putResp.ok;
}

// Aplica una lista de {file, old, new} y commitea cada archivo modificado al preview
async function applyAndCommit(env, patches, description) {
  // Group patches by file
  const byFile = {};
  for (const p of patches) {
    if (!byFile[p.file]) byFile[p.file] = await fetchGitHubFile(env, p.file, "main");
    if (!byFile[p.file]) return { reply: `⚠️ No se pudo leer ${p.file} de GitHub.`, previewUrl: null, hasPendingChange: false };
    const patched = applyPatch(byFile[p.file], p.old, p.new);
    if (patched === null) return { reply: `⚠️ No encontré el texto a reemplazar en ${p.file}. Puede que el archivo haya cambiado. Intentá de nuevo.`, previewUrl: null, hasPendingChange: false };
    byFile[p.file] = patched;
  }

  for (const [file, content] of Object.entries(byFile)) {
    const ok = await commitToPreview(env, file, content, description);
    if (!ok) return { reply: `⚠️ No se pudo escribir ${file} al preview.`, previewUrl: null, hasPendingChange: false };
  }

  const fileList = Object.keys(byFile).join(", ");
  return {
    reply: `✅ Listo. ${description}`,
    previewUrl: PREVIEW_URL,
    hasPendingChange: true,
    changeFile: fileList,
    changeDescription: description,
  };
}

function applyPatch(content, oldText, newText) {
  const idx = content.indexOf(oldText);
  if (idx === -1) return null;
  return content.slice(0, idx) + newText + content.slice(idx + oldText.length);
}

function utf8ToB64(str) {
  const bytes = new TextEncoder().encode(str);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function b64ToUtf8(b64) {
  const binary = atob(b64);
  const bytes  = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

async function loadChangeLog(env) {
  try {
    const raw = await env.SUGGESTIONS.get(MEMORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

async function appendChangeLog(env, { file, description }) {
  const log = await loadChangeLog(env);
  const now = new Date().toLocaleDateString("es-AR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    timeZone: "America/Argentina/Buenos_Aires",
  });
  log.push({ date: now, file, description });
  // Keep last 50 entries
  const trimmed = log.slice(-50);
  await env.SUGGESTIONS.put(MEMORY_KEY, JSON.stringify(trimmed), {
    expirationTtl: 86400 * 365,
  });
}

function buildSystemPrompt(rendererContent, changeLog = []) {
  return `Sos el asistente de desarrollo de mejortercero.online, un sitio de seguimiento del Mundial 2026.

═══ ARQUITECTURA ═══════════════════════════════════════════════════════════════

generate.py invoca dos pipelines:
  1. build_standings() [api_client.py] → html_renderer.py  → mundial2026.html (HTML estático completo)
  2. build_standings() [api_client.py] → data_renderer.py  → data.json (fragmentos actualizables)

El frontend JavaScript llama a pollData() cada 30 segundos y actualiza estas secciones sin recargar la página:

  div id="groups-inner"  ← data.json["groups_html"]   ← _render_groups()   en html_renderer.py
  div id="thirds-inner"  ← data.json["thirds_html"]   ← _render_thirds()   en html_renderer.py
  div id="scorers-inner" ← data.json["scorers_html"]  ← _render_scorers()  en html_renderer.py
  div id="today-body"    ← data.json["dates_html"][fecha] ← _render_today_matches() en html_renderer.py

REGLA CRÍTICA: Si modificás o agregás una sección dinámica en html_renderer.py, TAMBIÉN debés
actualizar data_renderer.py para que el JSON incluya ese contenido. Son dos archivos acoplados.

═══ ARCHIVOS EDITABLES ═════════════════════════════════════════════════════════

- html_renderer.py  → CSS, HTML, funciones de renderizado. ARCHIVO PRINCIPAL.
- data_renderer.py  → genera data.json. Tocar cuando agregues/modificás secciones dinámicas.
- api_client.py     → fetch de datos de la API de fútbol y construcción del objeto standings.
- countries.py      → traducciones al español + códigos ISO de banderas.

═══ DATOS DISPONIBLES EN standings ═════════════════════════════════════════════

standings["GROUP_A"] … ["GROUP_L"]  → {teams: [], stats: {equipo: {PJ,PG,PE,PP,GF,GC,DG,Pts}}, matches: []}
standings["_scorers"]               → [{name, team, goals}, ...]  (top 50 goleadores)
standings["_thirds_ranked"]         → [{team, group, stats}, ...]  (todos los terceros, rankeados)
standings["_thirds_advancing"]      → top 8 de _thirds_ranked
standings["_live_teams"]            → set() de nombres de equipos jugando en este momento
standings["_matches_by_date"]       → {"2026-06-14": [{home, away, home_goals, away_goals, status, utc_date, stage, group, matchday, referee}], ...}
standings["_today_date"]            → "2026-06-20"
standings["_today_matches"]         → lista de partidos del día actual

No uses claves que no estén en esta lista — no existen y causarán un error.

═══ NOMBRES DE EQUIPOS ═════════════════════════════════════════════════════════

SIEMPRE usá traducir(nombre_api) de countries.py para obtener bandera HTML + nombre en español.
  ✅ traducir("Argentina")  →  '<img src="/flags/20x15/ar.png" ...>Argentina'
  ❌ "Argentina"  o  "🇦🇷 Argentina"  — nunca hardcodees nombres ni emojis de banderas.

═══ VARIABLES CSS (OBLIGATORIO) ════════════════════════════════════════════════

El HTML se genera con f-strings de Python. Las variables CSS son constantes Python que se
interpolan automáticamente. En el código CSS siempre escribí {T}, {BG}, etc. — NUNCA colores hex directos.

  T    = #c2410c  → terracota (color principal, botones, acentos)
  TEL  = #0d9488  → teal (equipos clasificados directamente)
  OK   = #16a34a  → verde (resultados positivos)
  WRN  = #d97706  → naranja (advertencias)
  BG   = #faf8f4  → fondo de página
  WHT  = #ffffff  → fondo de cards y tablas
  BDR  = #e8ddd0  → borde suave (el más usado)
  BDR2 = #c8b8a8  → borde marcado
  TXT  = #211c14  → texto principal
  MUT  = #7c6a58  → texto secundario
  DIM  = #b09880  → texto atenuado / labels
  GRY  = #f0ebe4  → fondo gris cálido (filas alternas, fondos secundarios)

═══ PATRÓN DE SECCIONES COLAPSABLES ════════════════════════════════════════════

Toda sección nueva DEBE seguir exactamente este patrón. El ID debe ser único y en minúsculas.

  <div class="sec">
    <div class="sec-hdr" onclick="toggleSec('ID')">
      <p class="sec-t" style="margin:0;border:none;padding-bottom:0">TÍTULO DE LA SECCIÓN</p>
      <button class="sec-toggle" id="st-ID">▲ CERRAR</button>
    </div>
    <div class="sec-body" id="sb-ID">
      <!-- Si es estática: contenido directo -->
      <!-- Si es dinámica: <div id="ID-inner">contenido inicial</div> -->
    </div>
  </div>

El estado abierto/cerrado se guarda en localStorage (clave "sec_states") y se restaura al cargar.
No modifiques las funciones toggleSec(), loadSecs(), saveSecs(), restoreSecs() salvo que sea específicamente necesario.

═══ FORMATO DE RESPUESTA — CRÍTICO ═════════════════════════════════════════════

Respondé SIEMPRE con JSON puro. Sin bloques markdown, sin texto antes ni después.

Cambio en UN archivo (la mayoría de los casos):
{
  "type": "patch",
  "description": "frase específica de qué cambió",
  "file": "html_renderer.py",
  "old": "texto EXACTO del archivo que reemplazás — mínimo 3 líneas para que sea único",
  "new": "texto nuevo que lo reemplaza"
}

Cambio en MÚLTIPLES archivos:
{
  "type": "patches",
  "description": "frase específica",
  "patches": [
    {"file": "html_renderer.py", "old": "texto exacto", "new": "texto nuevo"},
    {"file": "data_renderer.py", "old": "texto exacto", "new": "texto nuevo"}
  ]
}

Pregunta o conversación:
{"type": "message", "text": "respuesta en español, sin markdown"}

REGLAS DEL PATCH:
- "old" debe ser el texto EXACTO tal como aparece en el archivo (respetá espacios e indentación).
- "old" debe incluir suficiente contexto (al menos 3 líneas) para ser único en el archivo.
- Si necesitás varios cambios en el mismo archivo, incluí todos en un único par old/new.
- NO devuelvas el archivo completo. Solo el fragmento que cambia.
- "description" debe ser específico: "Saqué el emoji ✉ del botón de sugerencias", no "Actualicé el botón".
  Esta descripción va al historial de memoria y al commit de GitHub.
- Hablá en español simple, sin jerga técnica.
- Si el pedido no es claro, pedí clarificación antes de generar código.

═══ HISTORIAL DE CAMBIOS APLICADOS A PRODUCCIÓN ════════════════════════════════

${changeLog.length
  ? changeLog.map(c => `[${c.date}] ${c.file} — ${c.description}`).join("\n")
  : "(ninguno todavía — primera sesión)"}

Usá este historial para entender el contexto. No repitas cambios ya aplicados a menos que te lo pidan.

═══ CONTENIDO ACTUAL DE html_renderer.py ═══════════════════════════════════════

${rendererContent || "(no disponible — respondé con type:message indicando el problema)"}`;
}
