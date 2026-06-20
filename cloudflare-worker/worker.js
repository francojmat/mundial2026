/**
 * API de sugerencias + Admin
 * Rutas:
 *   POST /api/suggest            → guarda sugerencia en KV (público)
 *   GET  /api/suggestions?token= → lista sugerencias (solo admin)
 *   POST /api/mark-read          → marca como leídas (solo admin)
 */

const CORS_ORIGIN = "https://mejortercero.online";

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
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }

    if (path === "/api/suggest" && request.method === "POST") {
      return handleSuggest(request, env);
    }
    if (path === "/api/suggestions" && request.method === "GET") {
      return handleList(request, env);
    }
    if (path === "/api/mark-read" && request.method === "POST") {
      return handleMarkRead(request, env);
    }

    return new Response("Not found", { status: 404 });
  },
};

// ── POST /api/suggest ────────────────────────────────────────────────────────

async function handleSuggest(request, env) {
  let body;
  try { body = await request.json(); }
  catch { return json({ error: "JSON inválido" }, 400); }

  const msg  = String(body.msg  || "").trim().slice(0, 600);
  const name = String(body.name || "").trim().slice(0, 80) || "Anónimo";
  const page = String(body.page || "").trim().slice(0, 100);

  if (!msg) return json({ error: "El mensaje no puede estar vacío" }, 400);

  // Rate limit: 3 por IP cada 30 min
  const ip  = request.headers.get("CF-Connecting-IP") || "unknown";
  const rlKey = `rl:${ip}`;
  const rlData = JSON.parse(await env.SUGGESTIONS.get(rlKey) || "[]");
  const since = Date.now() - 30 * 60 * 1000;
  const recent = rlData.filter(ts => ts > since);

  if (recent.length >= 3) {
    return json({ error: "Límite alcanzado. Intentá en 30 minutos." }, 429);
  }

  const id  = `sug:${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const sug = {
    id, name, msg, page,
    ts:   new Date().toISOString(),
    read: false,
  };

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

  const list = await env.SUGGESTIONS.list({ prefix: "sug:" });
  const items = await Promise.all(
    list.keys.map(async k => {
      const v = await env.SUGGESTIONS.get(k.name);
      return v ? JSON.parse(v) : null;
    })
  );

  return json(
    items.filter(Boolean).sort((a, b) => new Date(b.ts) - new Date(a.ts))
  );
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

// ── helpers ──────────────────────────────────────────────────────────────────

function validToken(token, env) {
  if (!token || !env.ADMIN_TOKEN_HASH) return false;
  const stored = env.ADMIN_TOKEN_HASH.replace(/^﻿/, '').trim();
  return token === stored;
}
