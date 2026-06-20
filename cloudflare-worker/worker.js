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
const PREVIEW_URL  = "https://preview.mundial2026.pages.dev";
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
  async fetch(request, env) {
    const url  = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }

    if (path === "/api/metrics"     && request.method === "GET")  return handleMetrics(request, env);
    if (path === "/api/suggest"     && request.method === "POST") return handleSuggest(request, env);
    if (path === "/api/suggestions" && request.method === "GET")  return handleList(request, env);
    if (path === "/api/mark-read"   && request.method === "POST") return handleMarkRead(request, env);
    if (path === "/api/chat"        && request.method === "POST") return handleChat(request, env);
    if (path === "/api/apply"       && request.method === "POST") return handleApply(request, env);
    if (path === "/api/discard"     && request.method === "POST") return handleDiscard(request, env);

    return new Response("Not found", { status: 404 });
  },
};

// ── GET /api/metrics ─────────────────────────────────────────────────────────

async function handleMetrics(request, env) {
  const url = new URL(request.url);
  if (!validToken(url.searchParams.get("token") || "", env)) {
    return json({ error: "No autorizado" }, 401);
  }

  const phKey = (env.POSTHOG_KEY || '').replace(/^﻿/, '').trim();
  const res = await fetch("https://us.posthog.com/api/projects/478313/query", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${phKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: {
        kind: "HogQLQuery",
        query: `SELECT toDate(timestamp) AS day,
                       count() AS pageviews,
                       count(distinct person_id) AS users
                FROM events
                WHERE event = '$pageview'
                  AND timestamp >= now() - interval 30 day
                GROUP BY day
                ORDER BY day`,
      },
    }),
  });

  if (!res.ok) {
    return json({ error: "Error PostHog", status: res.status }, 502);
  }

  const data = await res.json();
  const rows = (data.results || []).map(r => ({
    day: r[0],
    views: Number(r[1]),
    users: Number(r[2]),
  }));

  const today  = new Date().toISOString().split("T")[0];
  const weekAgo = new Date(Date.now() - 6 * 86400000).toISOString().split("T")[0];

  return json({
    daily:       rows,
    today_views: rows.find(r => r.day === today)?.views ?? 0,
    today_users: rows.find(r => r.day === today)?.users ?? 0,
    week_views:  rows.filter(r => r.day >= weekAgo).reduce((s, r) => s + r.views, 0),
    month_views: rows.reduce((s, r) => s + r.views, 0),
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

// ── POST /api/chat ────────────────────────────────────────────────────────────

async function handleChat(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  if (!validToken(body.token || "", env)) return json({ error: "No autorizado" }, 401);

  const userMessage = String(body.message || "").trim().slice(0, 3000);
  if (!userMessage) return json({ error: "Mensaje vacío" }, 400);

  const history = Array.isArray(body.history) ? body.history.slice(-12) : [];

  // Fetch current html_renderer.py and persistent change log
  const rendererContent = await fetchGitHubFile(env, "html_renderer.py", "main");
  const changeLog       = await loadChangeLog(env);

  const messages = [
    ...history,
    { role: "user", content: userMessage },
  ];

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
    return json({ error: `Error Claude: ${err}` }, 502);
  }

  const claudeData = await claudeResp.json();
  const rawReply   = claudeData.content?.[0]?.text || "";

  // Claude should respond with raw JSON (no markdown fences)
  let parsed;
  try {
    const cleaned = rawReply.replace(/^```json\s*/i, "").replace(/\s*```$/, "").trim();
    parsed = JSON.parse(cleaned);
  } catch {
    parsed = { type: "message", text: rawReply };
  }

  if (parsed.type === "change" && parsed.file && parsed.content) {
    const committed = await commitToPreview(env, parsed.file, parsed.content, parsed.description || "cambio AI");
    if (committed) {
      return json({
        reply:           `✅ Listo. ${parsed.description || "Cambio aplicado al preview."}`,
        previewUrl:      PREVIEW_URL,
        hasPendingChange: true,
        changeFile:      parsed.file,
        changeDescription: parsed.description || "",
      });
    } else {
      return json({ reply: "⚠️ No se pudo escribir el preview. Revisá los logs del Worker.", previewUrl: null, hasPendingChange: false });
    }
  }

  return json({
    reply:            parsed.text || rawReply,
    previewUrl:       null,
    hasPendingChange: false,
  });
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
  const updateBody = {
    message: `AI apply: ${body.description || filename}`,
    content: previewFile.content.replace(/\n/g, ""),
    branch:  "main",
  };
  if (mainSha) updateBody.sha = mainSha;

  const updateResp = await fetch(`https://api.github.com/repos/${REPO}/contents/${filename}`, {
    method:  "PUT",
    headers: { ...ghHeaders, "Content-Type": "application/json" },
    body:    JSON.stringify(updateBody),
  });

  if (!updateResp.ok) {
    const err = await updateResp.text();
    return json({ error: `GitHub error: ${err}` }, 502);
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

El sitio es estático: generate.py produce mundial2026.html y data.json a partir de html_renderer.py.

ARCHIVOS QUE PODÉS MODIFICAR:
- html_renderer.py : CSS, HTML, funciones Python de renderizado. ES EL ARCHIVO PRINCIPAL.
- api_client.py    : fetching de datos de la API de fútbol.
- countries.py     : traducciones al español + códigos de banderas.

FORMATO DE RESPUESTA — CRÍTICO:
Respondé SIEMPRE con JSON puro, sin bloques markdown, sin texto antes ni después.

Si el usuario pide un cambio visual o de comportamiento:
{"type":"change","description":"descripción breve del cambio","file":"html_renderer.py","content":"...contenido COMPLETO del archivo modificado..."}

Si es una pregunta o conversación:
{"type":"message","text":"tu respuesta en español, sin markdown"}

REGLAS:
- El campo "content" debe tener el ARCHIVO COMPLETO, no solo el fragmento modificado.
- Hablale al usuario en español simple, sin jerga técnica.
- Si el pedido no es claro, pedí clarificación con {"type":"message","text":"..."}.
- No sugieras cambios que no te pidieron.
- Solo podés tocar los 3 archivos listados arriba.

HISTORIAL DE CAMBIOS YA APLICADOS A PRODUCCIÓN:
${changeLog.length
  ? changeLog.map(c => `- [${c.date}] ${c.file} — ${c.description}`).join("\n")
  : "(ninguno todavía — primera sesión)"}

Usá este historial para entender el contexto de lo que ya se hizo. No repitas cambios ya aplicados a menos que te lo pidan explícitamente.

CONTENIDO ACTUAL DE html_renderer.py:
${rendererContent || "(no disponible — respondé con type:message indicando el problema)"}`;
}
