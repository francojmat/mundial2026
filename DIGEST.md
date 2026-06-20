# DIGEST — Mundial 2026 (web de seguimiento)

> Si no está en el DIGEST, no pasó. Actualizar en el mismo commit que el cambio de código.

## Qué es

Sitio estático que muestra el Mundial 2026 en vivo: partidos de hoy (cuadros
desplegables con detalle), tabla de posiciones por grupo con desempates FIFA,
ranking de terceros, bracket de 32avos, goleadores. Se regenera solo cada ~60s.

## Arquitectura de generación

`generate.py` corre en GitHub Actions y produce 2 archivos estáticos:
- `mundial2026.html` — la web completa (HTML+CSS+JS inline)
- `data.json` — fragmentos HTML pre-renderizados que el front consume para refrescar sin recargar

Pipeline: `generate.py` → `build_standings()` (api_client.py) → `render_html()` (html_renderer.py) + `render_data_json()` (data_renderer.py).

### Hosting / deploy
- Web servida por **Cloudflare Pages** desde la rama `main` del repo `francojmat/mundial2026`.
- **GitHub Actions** (`.github/workflows/update.yml`) regenera y commitea a `main`:
  - cron cada 5 min (mínimo de GitHub) + `workflow_dispatch` disparado por cron-job.org cada 60s.
  - El job hace `git add data.json mundial2026.html events_cache.json` y pushea.
- Panel admin: `admin.html` (métricas PostHog vía Cloudflare Worker en `cloudflare-worker/worker.js`).

## Fuentes de datos — DOS APIs (decisión clave)

| Dato | Fuente | Costo | Frecuencia |
|---|---|---|---|
| Marcador, estado (EN VIVO/FIN), posiciones, fixtures, árbitro, goleadores del torneo | **football-data.org** | free (10 req/min) | cada corrida (~60s) |
| Detalle de eventos por partido: goles (min + asistencia), tarjetas, cambios | **API-Football** (api-sports.io) | free (100 req/día) | adaptativo, solo en vivo |

**Por qué dos APIs:** el free tier de football-data.org NO devuelve goles/tarjetas/cambios
(devuelve `[]` en el endpoint individual `/v4/matches/{id}` — verificado con logs el 2026-06-20).
Solo trae el árbitro. Por eso el detalle de eventos viene de API-Football.

El **marcador** ya se actualiza en vivo gratis vía football-data.org, así que el usuario
ve los goles en el resultado en ~60s sin gastar API-Football. API-Football solo llena el
detalle del cuadro desplegable (quién, minuto, asistencia, tarjetas, cambios).

## Sistema de eventos (events.py + apifootball_client.py)

`build_standings(client, apifootball=...)` llama a `events.enrich_with_events()` que
enriquece in-place cada partido con `goals_detail`, `bookings`, `substitutions`
(la forma exacta que ya renderiza `_hoy_detail_html()` en html_renderer.py).

**Estrategia de ahorro (clave para no pasar las 100 req/día):**
- Sin partidos en vivo y todo cacheado → **0 requests**.
- Partido FINISHED ya cacheado → 0 requests (los eventos no cambian).
- Partido en vivo (IN_PLAY/PAUSED) → 1 request cada `interval` segundos.
- Partido recién terminado → 1 request final para congelar.
- Polling **adaptativo** según partidos en vivo simultáneos: 90s (1) · 180s (2) · 300s (3+).
- Tope duro `DAILY_BUDGET = 95` req/día; si se alcanza, usa solo caché.

**Caché:** `events_cache.json` (commiteado al repo para persistir entre corridas):
```
{ "day": "YYYY-MM-DD", "requests_today": N,
  "fixture_map": { "<match_id_fd>": {"fixture_id","home_id","away_id"} },
  "events": { "<match_id_fd>": {"status","last_fetch","goals_detail","bookings","substitutions"} } }
```
`requests_today` se resetea al cambiar el día (UTC).

**Mapeo de IDs entre APIs:** se matchea cada partido de football-data con el fixture de
API-Football por **timestamp de kickoff** (tolerancia 5 min). Una request de
`/fixtures?league=1&season=2026&date=...` resuelve todos los partidos de un día de una.
El mapeo se cachea en `fixture_map` (no se vuelve a resolver).

**Nombres de equipos:** en los eventos se usa `m["home"]`/`m["away"]` (de football-data,
traducibles al español) según el `team.id` de API-Football, para que coincidan con el
encabezado del cuadro.

**Degradación elegante:** sin `APIFOOTBALL_KEY`, `apifootball=None` y no se llama a la API
→ el sitio funciona igual, solo muestra el árbitro en el detalle. No rompe nada.

## Secrets (GitHub Actions → Settings → Secrets)
- `FOOTBALL_API_KEY` — football-data.org (ya cargado)
- `APIFOOTBALL_KEY` — API-Football (PENDIENTE de cargar por el usuario)

## Archivos principales
- `generate.py` — entrypoint; lee `FOOTBALL_API_KEY` y `APIFOOTBALL_KEY` del env.
- `api_client.py` — `WorldCupClient` (football-data.org), `build_standings()`, `parse_matches()`.
- `apifootball_client.py` — `APIFootballClient`: `get_fixtures_by_date()`, `get_fixture_events()`.
- `events.py` — `enrich_with_events()`: caché + adaptativo + presupuesto + parsing.
- `html_renderer.py` — render del sitio. `_hoy_detail_html()` arma el cuadro desplegable. `_render_today_matches()` los cuadros de hoy con `toggleMatch()` JS.
- `data_renderer.py` — arma `data.json`.
- `standings.py` / `bracket.py` — desempates FIFA y bracket.
- `test_events.py` — test de regresión de events.py (parsing, caché, adaptativo, presupuesto). Correr: `python test_events.py`.
- `debug_events.py` — diagnóstico manual de qué devuelve football-data.org (necesita `--key`).

## Estado actual (2026-06-20)
- ✅ Cuadros de partido desplegables (chevron, goles/tarjetas/cambios/árbitro).
- ✅ Métricas PostHog ampliadas en admin (países, dispositivos, referentes, horas pico, únicos).
- ✅ Sistema de dos APIs implementado, testeado y deployado en modo degradado.
- ⏳ PENDIENTE: el usuario crea cuenta en API-Football y carga `APIFOOTBALL_KEY`. Al cargarla,
  el detalle de eventos reales empieza a aparecer en la próxima corrida.
- 💡 Futuro: si el tráfico lo justifica, plan pago de API-Football (~USD 19/mes, 7.500 req/día)
  para detalle instantáneo en todos los partidos simultáneos.

## Gotcha operativo
El cron pushea a `main` cada ~60s. Al trabajar local, los push chocan seguido. Patrón:
`git pull origin main --no-rebase` → `git checkout --theirs data.json mundial2026.html` →
`git add .` → `git push`. (`events_cache.json` también lo toca el bot ahora.)
No disparar el workflow muchas veces seguidas: football-data.org corta con 429 (rate limit).
