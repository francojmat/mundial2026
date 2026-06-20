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

## Datos de API-Football disponibles y NO usados (WC 2026, league=1, season=2026)
Hoy solo usamos `fixtures` (mapeo) y `fixtures/events` (goles/tarjetas/cambios). El plan Pro
da MUCHO más, todo verificado que devuelve datos para 2026 (por si se suman features):
- **fixtures/lineups** — formación, XI titular con posición, suplentes, DT
- **fixtures/statistics** — posesión, tiros, pases+precisión, córners, faltas, offsides, atajadas
- **fixtures/players** — stats por jugador: rating, minutos, pases, tackles, duelos, gambetas
- **predictions** — % de cada resultado, consejo, comparativa de forma
- **teams/statistics** — forma, promedios de goles, vallas invictas por selección
- **standings** (API-Football) — con forma reciente (WWDLW) y splits local/visitante
- **players/squads** — plantel completo (número, posición, edad, foto)
- **players** — perfil + stats (edad, nacionalidad, altura, peso, foto)
- **coachs** — DTs (carrera, edad, foto)
- **players/topassists**, **topyellowcards**, **topredcards** — rankings
- **fixtures/headtohead**, **fixtures/rounds**, **injuries**, **sidelined**, **trophies**
- **odds** / **odds/live** — cuotas de apuestas · **teams** / **venues** — info y estadios
- Multimedia: URLs de logos, fotos de jugadores/DTs, imágenes de estadios

## Favicon
Set completo (realfavicongenerator) en la raíz del repo: `favicon.ico`, `favicon-16/32/96/256`,
`apple-icon-*`, `android-icon-192x192`, `ms-icon-*`, `manifest.json`, `browserconfig.xml`.
Referenciado en el `<head>` de `html_renderer.py`. El `manifest.json` se reescribió para listar
solo iconos que existen (el del zip referenciaba android-icon 36-144 que no venían). Se sirven
en la raíz (Cloudflare Pages); el `_redirects` solo afecta `/` exacto, no los archivos.

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
API-Football por **timestamp de kickoff** (tolerancia 5 min). Se traen TODOS los fixtures
del torneo en UNA request (`/fixtures?league=1&season=2026`, ~104 partidos) y se arma el
mapa completo. El mapeo se cachea en `fixture_map` y no se vuelve a resolver (el calendario
no cambia). NO usar el filtro `?date=` de API-Football: es poco fiable por timezone
(devuelve 0 aunque el partido exista). World Cup = league id **1**.

**Nombres de equipos:** en los eventos se usa `m["home"]`/`m["away"]` (de football-data,
traducibles al español) según el `team.id` de API-Football, para que coincidan con el
encabezado del cuadro.

**Degradación elegante:** sin `APIFOOTBALL_KEY`, `apifootball=None` y no se llama a la API
→ el sitio funciona igual, solo muestra el árbitro en el detalle. No rompe nada.

## API-Football: plan Pro ACTIVO (2026-06-20)
El free tier NO daba acceso a season 2026 (error "Free plans do not have access to this
season"). Se contrató el **plan Pro de API-Football (USD 19/mes, 7.500 req/día)** que sí da
acceso a 2026. Verificado: trae los 72 partidos del Mundial con eventos reales (hat-trick de
Messi vs Algeria, Mbappé, Haaland, etc.). El detalle de eventos ya aparece en la web.
NOTA: al pasar a pago, API-Football cambia la API key (la del free queda muerta).

## Secrets (GitHub Actions → Settings → Secrets)
- `FOOTBALL_API_KEY` — football-data.org (cargado)
- `APIFOOTBALL_KEY` — API-Football, **key del plan Pro** (cargado y activo)

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
- ✅ Sistema de dos APIs implementado, testeado y deployado.
- ✅ **API-Football Pro ACTIVO**: detalle de eventos reales del 2026 funcionando en la web.
- ✅ Workflow a prueba de fallos (continue-on-error + push resiliente con exit 0) → no más
  mails de "Run failed". Ver sección "Gotcha operativo".
- 💡 Futuro posible: migrar a API-Football como ÚNICA fuente (reemplazar football-data.org)
  para simplificar el stack a una sola API. No urgente; el sistema de dos APIs anda bien.
- 💡 Nota de diseño: el detalle desplegable solo se renderiza para los partidos de HOY
  (`_render_today_matches`). Partidos de días previos no muestran el detalle en la web aunque
  estén cacheados. Si se quiere mostrar historial con detalle, hay que extender el render.

## Gotcha operativo
El cron pushea a `main` cada ~60s. Al trabajar local, los push chocan seguido. Patrón:
`git pull origin main --no-rebase` → `git checkout --theirs data.json mundial2026.html` →
`git add .` → `git push`. (`events_cache.json` también lo toca el bot ahora.)
No disparar el workflow muchas veces seguidas: football-data.org corta con 429 (rate limit).
