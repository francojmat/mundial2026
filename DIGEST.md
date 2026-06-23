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

### Hosting / deploy — DATOS SEPARADOS DEL CÓDIGO (clave, 2026-06-21)
- **main = solo código** (shells `mundial2026.html`/`plantel.html`/`partido.html`, .py, CSS/JS).
  Cloudflare Pages deploya `main` SOLO cuando cambia el código → casi nunca → **no más 522**.
  Los archivos de datos están gitignorados en main.
- **rama `data` = datos** (data.json, planteles.json, partidos.json, events_cache.json,
  apifootball_cache.json). El cron (`update.yml`) genera y **force-pushea a `data`** (orphan,
  1 commit). Pages NO deploya producción por esto. (Pages igual crea PREVIEW deploys de `data`
  —Cloudflare los hace pese a excluirlos por API— pero son inofensivos: no tocan producción
  ni cuota real, ya que sin build-command no cuentan.)
- **El Worker sirve los datos**: `/api/data`, `/api/planteles`, `/api/partidos` → fetch de
  `raw.githubusercontent.com/.../data/<file>`, cache 20s. El front pollea `/api/data`.
- Flujo de update: cron → genera → push a `data` → raw GitHub → Worker (cache 20s) → front.
  Para deployar CÓDIGO: commit a `main` (regenerar shells local con `python generate.py` y
  commitearlos). Pages deploya esa vez.
- Setting de Pages cambiado por API: `preview_deployment_setting` (token wrangler en
  `%APPDATA%/xdg.config/.wrangler/config/default.toml`, scope pages:write).
- Panel admin: `admin.html` (métricas PostHog vía Cloudflare Worker en `cloudflare-worker/worker.js`).
- El cron sigue disparándose por cron-job.org (~60s) + schedule cada 5 min. workflow_dispatch.

## Fuentes de datos — API-Football es el proveedor PRINCIPAL (migración 2026-06-21)

| Dato | Fuente |
|---|---|
| Partidos, scores, status, grupos, posiciones, fixtures, árbitro, eventos, planteles, detalle, estadios, rankings | **API-Football** (Pro, 7.500 req/día) |
| Goleadores (lista completa) | **football-data.org** (free) — único uso que le queda |

**Por qué football-data quedó solo para goleadores:** API-Football `topscorers` da solo top 20;
football-data da ~80. Decisión del usuario: mantener football-data SOLO para esa lista.

**Grupos:** API-Football NO da la letra del grupo en el fixture (`round` = "Group Stage - N").
El grupo se saca de `/standings` (`get_team_groups` → {equipo: GROUP_X}) y se asigna a cada partido.

**match_id = fixture_id de API-Football.** Por eso events.py y tournament.py ya NO necesitan
`resolve_fixture` (quedó muerto en apifootball_client.py) ni mapeo entre APIs. El bug de partidos
simultáneos desapareció de raíz. `_af_to_match` (api_client.py) convierte fixture→formato interno.

## Marcadores en vivo — endpoint /api/live (Worker)
Para no esperar el ciclo de git (~60s), el marcador en vivo va por el Cloudflare Worker:
`GET /api/live` pide a API-Football `?live=all`, cachea 10s (Cache API → respeta rate limit sin
importar el tráfico), devuelve `[{id, status, elapsed, h, a}]`. El front (`pollLive`, cada 8s)
busca la tarjeta por `data-mid` y actualiza el `.hoy-score`. Latencia ~8-10s. El Worker necesita
el secret `APIFOOTBALL_KEY` (cargado vía `wrangler secret put`). Deploy del Worker: `wrangler deploy`
desde `cloudflare-worker/` (wrangler está autenticado con la cuenta del usuario).

## Blindaje de cuota API-Football (2026-06-22) — POR QUÉ
Incidente: se agotó la cuota diaria (7500/día) y el cron publicaba datos VACÍOS encima de los
buenos → home en blanco. Protecciones, en orden:
- **Guarda anti-blanco** (`generate.py`): si `build_standings` devuelve 0 grupos (`GROUP_*`),
  `main()` aborta SIN escribir nada → el workflow re-publica la última versión buena. Una caída
  de la API NUNCA deja el sitio en blanco; congela lo último bueno.
- **`/api/live` consciente del horario**: `generate.py` emite `live_windows.json` (ventanas
  epoch-ms de partidos no terminados: inicio−15min a +210min). El Worker (`getLiveWindows`,
  cache 5min) solo consulta API-Football si `now` cae en una ventana; fuera de horario, 0
  llamadas. **Fail-open** si no hay ventanas (404/error) → consulta igual.
- **Tope diario duro** en `/api/live`: `DAILY_LIVE_BUDGET=4000`, contado en `caches.default`
  con clave por fecha UTC (NO en KV, que tiene 1000 escrituras/día). Al tope, sirve último bueno.
- **Cache de `/api/live` 8s→15s.** **cron-job.org bajado de 1min a 5min** (en la cuenta de Franco).
- **Nota de capacidad:** los visitantes NO consumen cuota (el Worker cachea). El límite de escala
  es el plan del Worker (Free 100k req/día ≈ ~50 concurrentes en un partido). Palanca gratis no
  implementada: Cache Rule delante del Worker.

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

## Páginas internas (pages.py + tournament.py)
Patrón para páginas nuevas: **shell estática + fragmento pre-renderizado en JSON** (evita
generar 1 archivo por entidad). `generate.py` escribe la shell y el JSON cada corrida.
- **Plantel** (`plantel.html` + `planteles.json`): la shell lee `?t=<pais>` e inyecta el
  fragmento. `pages.render_squad_fragment()` arma el plantel (jugadores con foto agrupados por
  posición, expandibles, + DT aparte). Link desde cada país en Posiciones (`_render_groups`).
  Datos: `players/squads` + `coachs` por equipo. `planteles.json` keyed por nombre football-data.
- **Ver Partido** (`partido.html` + `partidos.json`, en `match_page.py`): la shell lee `?id=<match_id>`
  e inyecta el detalle: alineaciones (formación + XI + suplentes + DT), estadísticas del partido
  (barras comparativas home/away), rendimiento por jugador (rating/min/G/A) y posiciones del grupo.
  Botón "VER PARTIDO" arriba del detalle expandible (`_hoy_detail_html`) en TODOS los partidos.
  `generate.py` arma un fragmento por CADA partido; si no hay alineaciones/stats todavía, muestra
  header + posiciones + "sin datos aún". Datos: `fixtures/lineups`+`statistics`+`players`.
  El detalle se enriquece priorizando partidos EN VIVO y los más recientes (no los más viejos).
- **Sidebar de navegación**: botón flotante ☰ (abajo-izq) que despliega un drawer con las 9 secciones.
  `navGo(secId)` cierra el drawer, expande la sección si está colapsada y hace scroll suave.
  Cada `<div class="sec">` tiene `id="sec-<secId>"`.
- **Rankings** (asistencias/amarillas/rojas): top 10 + "Ver todos" (`toggleList`), filtran value>0
  (no rellenan con ceros). Goleadores: football-data, `limit=200` (da más que las 20 de API-Football).
- **Estadios**: capacidad oficial WC2026 de los 16 (dict curado `_VENUE_CAPACITY` en tournament.py,
  fuente Wikipedia/FIFA — la API solo tiene 8 y con capacidad general). Superficie + foto desde la API
  (solo 8 con id). Las fotos placeholder se filtran por tamaño (`_image_is_real`, <35KB = placeholder).
  En la lista de partidos por estadio: resultado si jugado, si no el horario (hora argentina).
  **El bloque de estadios (`_render_venues`) se publica en `data2.json` (`venues_html`) y se
  refresca vía `loadExtra` (sin pisar tarjeta abierta `.hoy-fila.open`).** Vivía solo en el shell
  estático → resultados congelados hasta un redeploy; el cron no regenera el shell, solo la rama data.
- **Worker `handleData`** (`/api/data*`) se apoya solo en el edge cache de Cloudflare sobre el
  fetch a raw (`cf:{cacheTtl:15}`), NO en `caches.default` (cuyas entradas quedaban pegadas sin
  expirar al `max-age`, obligando a bumpear la cacheKey a mano). El bracket R32 (sedes/fechas) está
  en `bracket.py` `_SCHEDULE` — verificado vs calendario oficial FIFA.
- `tournament.py` cachea en `apifootball_cache.json`: rankings (asist/amar/rojas, refresh 10min),
  estadios (refresh 30min), `team_id_map` + `fixture_id_map`, `squads` (semanal, 10 equipos/corrida),
  y `match_details` (por partido; FINISHED se cachea para siempre, en vivo refresca cada 2min, tope
  5 partidos/corrida).
- **CRÍTICO — mapeo de fixtures:** `apifootball_client.resolve_fixture()` matchea football-data ↔
  API-Football por **timestamp de kickoff Y nombres de equipo** (vía nombre_es). NO matchear solo
  por timestamp: dos partidos simultáneos se cruzan (bug real: Argentina mostraba plantel de Austria).
  Lo usan events.py y tournament.py.
- Identidad visual de marca obligatoria en TODO lo nuevo (tokens en html_renderer.py: T=#c2410c…).
- Toda página nueva debe tener retorno a la principal (botón "← Volver al inicio").

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
- ✅ Features agregadas (jun 2026): rankings (asistencias/amarillas/rojas), Estadios, páginas de
  Plantel por país (con foto) y Ver Partido. Feature "Lesionados/Sancionados" NO se hizo: el
  endpoint `injuries` devuelve 0 para selecciones en el Mundial (sin datos).

## Sesión 2026-06-22 — 30 features + Perfil de selección (TODO LIVE)
Se implementaron 30 features de un plan (1.3, 1.6, 1.7, 2.1, 2.5, 3.1-3.3, 4.1, 4.3, 5.1-5.5,
6.1-6.4, 7.1-7.4, 8.3-8.6, 9.1, 10.6). Trabajado en local (`_dev_server.py`, puerto 8765,
gitignored) y deployado. Todo verificado E2E en producción.

**Archivos nuevos:**
- `pages.py` → ahora también arma el **Perfil de selección** (`seleccion.html` + `selecciones.json`,
  ruta `/api/selecciones` en el Worker): ficha (rank FIFA + palmarés) + tabla del grupo + partidos
  expandibles + acceso al plantel. `render_seleccion_fragment` / `render_seleccion_shell`.
- `seleccion_data.py` → ranking FIFA (ed. 11/06/2026) + palmarés por selección, curado a mano.
  Keyed por nombre football-data. **Refrescar ranking ~20/07/2026 (próxima edición FIFA).**
- `motm.py` → figura del partido (MOTM oficial FIFA) curada a mano, keyed por `frozenset` en español.
  **Franco lo actualiza cada día.**
- `h2h_curado.py` → historial de los 72 cruces de grupo (últimos 5: fecha/torneo/instancia, PRE-2026),
  keyed por `frozenset` de nombres en español. Fallback cuando la API no tiene el par.
- `scenarios.py` → escenarios de clasificación de grupo (qué se juega cada equipo).

**Plantel (`pages.py`):** perfil de jugador expandible · **stats del torneo por ID de jugador**
(antes por apellido → homónimos colapsaban, los 3 Martínez compartían stats; FIX por id, y
`get_fixture_players` ahora guarda `id`) · ficha de selección · **club (país del club) en gris**
bajo el nombre (de `/players?id=&season`; OJO: ligas europeas 2025-26 están bajo **season 2025**,
no 2026 → se consulta 2025 y 2026; backfill throttleado `CLUBS_PER_RUN=80`, cache `player_clubs`).

**Ver Partido (`match_page.py`):** cancha sin solape · cronología estilo home · figura del partido
(`_mt_h2h` muestra "Historial reciente" o "Primer enfrentamiento" hasta que arranca) · bloque
**"Partidos del grupo"** (jugados+próximos, actual resaltado) · **foto del estadio** (`VENUE_PHOTO`
o imagen de la API, misma que Estadios) · posiciones del grupo clickeables al perfil · posiciones
en español (Arquero/Defensor/Mediocampista/Delantero) · botón **"Volver a [selección]"** (link con `&t=&tn=`).

**Home:** nav "Ir a sección" DINÁMICO (`buildNav` se arma de `<div class="sec" data-nav="...">`;
sección nueva con `data-nav` aparece sola) · Sugerencias + "Seguinos en redes" (IG @mejortercero.online,
X @mejortercero) en la **sidebar** (antes flotantes) · grupos con "Detalles" plegable + qué se juega 4 equipos.

**Fixes técnicos clave:** `RECENT_DAYS` 4→45 (eventos de TODO el Mundial, no solo 4 días → arregla
detalle de partidos viejos). Auto-reparado de caché: `_detail_has_player_ids` re-pide detalles
cacheados sin `id` (para que prod se cure sola tras el fix de stats). Foto de estadio: `VENUE_PHOTO`
en countries.py (11 curadas) + imagen de la API (resto).

## SSR para bots — Cloudflare Pages Functions (2026-06-22)
Las páginas internas (Ver Partido/Plantel/Perfil) son shells que rellena el JS → invisibles
para bots sin JS. Solución: **Pages Functions** en `functions/` (NO el Worker — Cloudflare Pages
tiene precedencia sobre las rutas del Worker para las páginas que sirve; probado y descartado).
- `functions/{partido,plantel,seleccion}.js` rutean las URLs limpias (`/partido`, etc.; Pages
  redirige `/partido.html` → `/partido` con 308). `functions/_ssr.js` tiene la lógica.
- **Humanos:** `context.next()` → Pages sirve el shell estático normal (cero riesgo, sin overhead).
- **Bots** (regex de UA: google/claude/gpt/perplexity/social previews): toma el shell vía `next()`,
  busca el fragmento en `/data` branch JSON, y lo inyecta en el `<div id>` + reemplaza title/description/
  og + agrega canonical y JSON-LD (`SportsEvent` por partido, `SportsTeam` por selección). Fail-safe:
  cualquier error → `context.next()` (shell normal). Se deploya con `git push` (Pages detecta functions/).

## Gotcha operativo (corregido 2026-06-22)
**main = solo código; rama `data` = datos** (el cron force-pushea a `data`, NO a `main`). Para
deployar: commit a `main` (Pages redeploya) → `gh workflow run update.yml` (regenera la rama data) →
si tocaste rutas del Worker, `cd cloudflare-worker && npx wrangler deploy`. `/api/*` propaga en ~5 min
(CDN de GitHub raw). `wrangler` está autenticado con la cuenta de Franco. NUNCA commitear `.env`,
los data JSON, ni `_dev_server.py` (todos en `.gitignore`). No tipear la API key — la pega Franco.
