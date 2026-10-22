# PPALMA Crime Mapping Tool

A spatio-temporal crime hotspot analysis tool for six municipalities in North
Cotabato — **P**ikit, **P**igcawayan, **A**lamada, **L**ibungan, **M**idsayap,
**A**leosan ("PPALMA"). Built with DBSCAN clustering and cross-year cluster
matching ("persistence") to surface where reported incidents recur.

## Data

The tool runs on the official PNP incident dataset, loaded through the Upload
page (`source='official'`). The synthetic demonstration dataset used before the
real data was released has been removed; it remains in git history if a
demonstration fixture is ever needed again.

The importer does the file cleanup so a PNP export can be loaded as-is — see
[What the importer organizes](#what-the-importer-organizes).

## Stack

- **Frontend:** React + Vite + TypeScript + Tailwind CSS + React-Leaflet
- **Map tiles:** OpenStreetMap (free, no API key, attribution shown on the map)
- **Backend:** FastAPI + Pandas + NumPy + scikit-learn + GeoPandas + Shapely
- **Database:** PostgreSQL + PostGIS (local dev) — a Supabase Postgres URL
  works as a drop-in alternative via `DATABASE_URL`; no code is Supabase-specific
- **Auth:** JWT (python-jose) + bcrypt, no external auth SaaS

All tooling above is free/open-source; no paid API keys or subscriptions are
required anywhere in the stack.

### Internet access

The backend, database, and API all run entirely on localhost and need no
internet access. **The one exception is the Leaflet basemap tiles**: by
default the map fetches OpenStreetMap tile images
(`tile.openstreetmap.org`) live over the internet on every pan/zoom, the same
way any Leaflet/Mapbox/Google-Maps-style web map does. If you need to demo or
develop fully offline, you would need to either self-host an OSM tile cache
(e.g. via `mbtiles`/`tileserver-gl`) or swap in a local raster tile source —
this is not currently wired up. The municipality boundary GeoJSON, incident
data, clustering, and persistence analysis are all computed locally and need
no internet access.

## Study area boundary data provenance

`data/boundaries/ppalma_municipalities.geojson` is **not hand-traced**. It was
filtered from the real, PSGC-sourced province file published in
[faeldon/philippines-json-maps](https://github.com/faeldon/philippines-json-maps)
(`2023/geojson/provdists/hires/municities-provdist-1204700000.0.1.json`,
Cotabato province), keeping only the 6 PPALMA `adm3_psgc` codes:

| Municipality | adm3_psgc |
|---|---|
| Alamada | 1204701000 |
| Libungan | 1204705000 |
| Midsayap | 1204709000 |
| Pigkawayan | 1204711000 |
| Pikit | 1204712000 |
| Aleosan | 1204717000 |

Barangay names (attribute text only, no barangay geometry) came from the same
source's per-municipality barangay files and are saved in
`data/boundaries/ppalma_barangays.json`. The importer resolves inbound barangay
spellings against this list.

`data/boundaries/ppalma_barangay_centroids.json` contains municipality-qualified
polygon centroids for all 146 listed PPALMA barangays. They were extracted from
the government-derived [PSGC 2026.4.13.0 data package](https://github.com/fish-and-bear/psgc)
(PSA PSGC Q1 2026 and the GeoRisk Philippines barangay boundary layer, WGS84).
The map uses these centroids to focus a barangay filter; it does not infer a
barangay's location from incident coordinates.

## Local setup

### 1. Database (local PostgreSQL + PostGIS)

```powershell
psql -U postgres -c "CREATE DATABASE ppalma_crime;"
psql -U postgres -d ppalma_crime -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

To use Supabase instead, just point `DATABASE_URL` at your Supabase Postgres
connection string (PostGIS is enabled by default on Supabase) — no other
changes are needed.

### 2. Backend

```powershell
cd backend
py -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # edit DATABASE_URL / JWT_SECRET as needed
.\venv\Scripts\python -m alembic upgrade head
.\venv\Scripts\python -m app.scripts.seed_municipalities
.\venv\Scripts\python -m app.scripts.seed_reference_data  # roles, barangays, configurable settings
.\venv\Scripts\python -m app.scripts.seed_user          # creates analyst@ppalma.local / ppalma-dev-2026 as an admin
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Incident data is then loaded through the Upload page. If a database still holds
synthetic records from an earlier run, clear them once with:

```powershell
.\venv\Scripts\python -m app.scripts.purge_synthetic
```

API docs: http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

App: http://localhost:5173 — log in with `analyst@ppalma.local` / `ppalma-dev-2026`
(this seeded account is granted the `admin` role — see [Roles](#roles-access-control) below).

## Vercel deployment

The root `vercel.json` deploys the Vite frontend and FastAPI backend as one
same-origin application. Set these environment variables in the Vercel project
before using database-backed features:

- `DATABASE_URL` — a reachable PostgreSQL/PostGIS connection string
- `JWT_SECRET_KEY` — a long, random production secret
- `DATA_SOURCE=official`

Optional analysis settings use the same names documented below and in
`backend/.env.example`. The frontend uses `/api` on the deployed origin, so a
separate public API URL or CORS configuration is not required.

Deploy from the repository root with `vercel --prod`, or import this GitHub
repository into Vercel. The deployment packages the boundary/reference data
needed by the API but excludes tests, migrations, and evaluation fixtures from
the serverless function bundle.

## Analysis parameters (configurable, not hardcoded)

Set in `backend/.env` (see `backend/app/core/config.py`):

- `DBSCAN_EPS_KM`, `DBSCAN_MIN_SAMPLES` — DBSCAN neighborhood radius (km) and
  minimum-samples density. DBSCAN is run using scikit-learn's `haversine`
  metric over radian-converted coordinates, so `eps` is a true great-circle
  distance in kilometers, not a raw coordinate-degree radius. Both values are
  shown to users in the map's Cluster-mode filter panel, with tooltips.
- `PERSISTENCE_MATCH_DISTANCE_KM` — max centroid distance used to match a
  cluster to the same recurring "chain" across consecutive years.
- `PERSISTENCE_SCORE_THRESHOLD` — the persistence-score cutoff (default
  `0.5`) that separates "intermittent" from "persistent" — see below.

These are deliberately left tunable — the values that make sense depend on the
loaded dataset's true spatial density and time span, so they are recalibrated
against the PNP data rather than fixed in code.

## Persistence score and categories

`persistence_score = periods_present / total_periods_analyzed` (0–1), where a
"period" is a distinct year and `total_periods_analyzed` is the number of
distinct years with any data in the current filter scope. Chains are
classified into four categories, compared against `PERSISTENCE_SCORE_THRESHOLD`:

| Category | Condition |
|---|---|
| **Temporary** | Appears in exactly 1 period. |
| **Intermittent** | Appears in 2+ periods, score below threshold. |
| **Historical persistent** | Score ≥ threshold, but **not** present in the most recent analyzed period — it recurred strongly, then stopped. |
| **Active persistent** | Score ≥ threshold **and** present in the most recent analyzed period — the strongest "still active" signal. |

"Historical persistent" is intentionally distinct from "temporary": a chain
present in 4 of 5 years and then absent is a materially different signal than
one that appeared exactly once, even though neither is present in the latest
period.

**Known limitation:** chain matching across years is centroid-distance only
(a greedy nearest-match within `PERSISTENCE_MATCH_DISTANCE_KM` of the chain's
most recent centroid). It does not consider cluster shape or overlap, so two
spatially adjacent but genuinely distinct hotspots that fall within the match
distance of each other in different years could be merged into one chain, and
a hotspot that drifts further than the match distance between consecutive
years will be split into two separate chains. A more precise future version
would match on convex-hull polygon overlap (IoU) instead of centroid
distance — this is deferred until the official PNP dataset's real spatial
density is known, since a polygon-overlap threshold needs real data to
calibrate against. See `backend/app/services/persistence_service.py` for the
full implementation and this same note in code.

Note also that a single-year DBSCAN cluster instance (Cluster View) and its
multi-year persistence chain (Persistence View) are reported through separate,
purpose-scoped detail panels rather than one merged view — full cluster-
instance-to-persistence-chain cross-linking in a single panel is listed under
[Deferred features](#deferred-features) below.

## Roles / access control

Every account has a `role` of either `pnp_personnel` or `admin`, enforced
server-side via a `require_role(...)` FastAPI dependency (not just hidden in
the UI):

- **PNP Personnel** (`pnp_personnel`): can log in, view the dashboard, map,
  and incident records, import crime records, generate reports, and log out.
- **Admin** (`admin`): all PNP Personnel functions, plus managing user
  accounts. Destructive record deletion also remains administrator-only.

The seeded demo account (`analyst@ppalma.local`) is granted `admin` so the
existing demo login can exercise every feature. The other seeded accounts are
PNP Personnel. JWTs expire after `JWT_EXPIRE_MINUTES` (default 12 hours).

## What the map does and does not claim

- DBSCAN clusters and persistence categories describe **where historical,
  already-reported incidents were spatially concentrated and recurred** — not
  a prediction of future crime.
- The heatmap layer is a smoothed visual-density aid (via `leaflet.heat`) and
  the low-zoom marker clustering on the Incident layer (via
  `leaflet.markercluster`) is a display/performance optimization only —
  neither is DBSCAN output, and both are labeled as such in the map legend.
- Victim/suspect identities are never stored or displayed; the incident schema
  has no such fields.
- Records placed at a barangay centroid (because exact coordinates were not
  released) are labeled `barangay_level` precision — their cluster placement is
  approximate to the barangay, not the exact incident location.

## What the importer organizes

A PNP export can be uploaded as it was received — the system performs the
cleanup that would otherwise be done by hand in Excel, and reports every change
in the import summary rather than applying it silently
(`backend/app/services/import_service.py`):

| Inbound problem | What the system does |
|---|---|
| Header names vary (`Blotter Entry No`, `City/Municipality`, `Nature of Offense`) | Auto-mapped to schema fields by synonym; the operator can override any mapping |
| Barangay spelled `BRGY. BALABAK`, `Brgy Balabak`, `Sitio Maligaya, Balabak` | Resolved to the official PSGC name (`Balabak`) |
| `Poblacion I` vs `Poblacion 1` | Roman and Arabic numerals resolve to the same barangay |
| `Pigkawayan` / `PIKIT` / `Physical Injuries` | Standardized to `Pigcawayan` / `Pikit` / `Physical Injury` |
| Latitude/longitude blank or unreadable | Placed at the barangay's official centroid, tagged `coordinate_source='barangay_centroid'`, `coordinate_precision='barangay_level'` |
| Coordinate transposed or outside the study area | Replaced with the barangay centroid where one resolves; rejected only when no usable location remains |
| Barangay blank | Recovered from the coordinate (nearest official barangay centroid in that municipality) |
| Reference number blank | Assigned a deterministic id (`B<batch>-000123`) so the row is not lost |
| Ambiguous numeric dates (`05/03/2024`) | Column read in the order the file itself proves — one `25/12` value makes the whole column day-first; if nothing settles it, those rows are flagged instead of quietly guessed |
| Offense outside the eight index crimes | Rejected, never bucketed into "Other", so the index-crime analysis stays intact |

Worksheets (`.xlsx`, `.xls`) are handled as first-class input alongside CSV:

| Worksheet quirk | What the system does |
|---|---|
| Real Excel date/time cells | Read as dates, not as epoch numbers (the naive path turns every date into 1970 and rejects the whole file) |
| Title block above the header (`Republic of the Philippines`, unit name, blank row) | Header row located automatically; the preamble is skipped |
| One tab per year or per municipality | Tabs sharing the same columns are combined into one dataset, and the combined tabs are named in the import summary |
| A cover sheet or legend tab | Left out — reported by name rather than mangled into the table |
| Trailing blank rows and unnamed columns | Dropped |

Coordinates are **optional**: the PNP data-sharing agreement allows releasing
barangay-level location when exact coordinates cannot be given, so a row with a
resolvable barangay is always placeable. Rows placed at a centroid are labeled
as such, and that label is visible in the records table and the map.

After loading real data, recalibrate `DBSCAN_EPS_KM` / `DBSCAN_MIN_SAMPLES` for
its actual spatial density, and confirm `PERSISTENCE_MATCH_DISTANCE_KM` /
`PERSISTENCE_SCORE_THRESHOLD` against the available study years.

## Deferred features

Intentionally not implemented in this pass (documented rather than silently
skipped):

- Fullscreen map mode
- Map north indicator
- Split year-over-year comparison view
- Dark mode
- A full WCAG/keyboard-navigation accessibility pass (current state has basic
  focus states only)
- Full cluster-instance-to-persistence-chain cross-linking in a single detail
  panel (see the note at the end of [Persistence score and categories](#persistence-score-and-categories))
- Offline/self-hosted basemap tiles (see [Internet access](#internet-access))

## Troubleshooting

**`connection refused` / `could not connect to server` on backend startup**
PostgreSQL isn't running, or `DATABASE_URL` in `backend/.env` points at the
wrong host/port. Confirm the service is running and the URL matches how you
created the database in [step 1](#1-database-local-postgresql--postgis).

**`extension "postgis" is not available` or geometry-column errors**
The `postgis` extension wasn't created in the target database. Run:
`psql -U postgres -d ppalma_crime -c "CREATE EXTENSION IF NOT EXISTS postgis;"`

**Alembic error about a revision it doesn't recognize, or "Target database is
not up to date"**
Your database's `alembic_version` table is out of sync with
`backend/migrations/versions/`. On a disposable dev database, the simplest
fix is to drop and recreate the database (step 1) and re-run
`alembic upgrade head` from a clean state.

**CORS errors in the browser console when the frontend calls the API**
`FRONTEND_ORIGIN` in `backend/.env` must exactly match the URL the frontend is
served from (default `http://localhost:5173`). Restart the backend after
changing it.

**Frontend can't reach the API / network errors on every page**
Check `VITE_API_URL` in `frontend/.env` points at the running backend
(default `http://localhost:8000`), and that the backend is actually running.

**The map area is blank, or markers/popups look unstyled**
Leaflet's CSS must be imported before your own styles. Confirm
`frontend/src/main.tsx` still imports `leaflet/dist/leaflet.css`,
`leaflet.markercluster/dist/MarkerCluster.css`, and
`leaflet.markercluster/dist/MarkerCluster.Default.css`.

**`address already in use` starting uvicorn or vite**
Another process is already bound to port 8000 or 5173. Stop it, or start
uvicorn/vite with a different `--port`, updating `VITE_API_URL`/
`FRONTEND_ORIGIN` to match if you change the backend port.

**403 Forbidden when deleting a record or committing an import**
That action requires the `admin` role — see [Roles / access control](#roles-access-control).
Log in with the seeded admin account, or promote your account via
`seed_user.py`.

## Project layout

```
backend/
  app/
    core/        settings, JWT/bcrypt auth helpers, RBAC dependency, shared constants
    db/          SQLAlchemy engine/session
    models/      SQLAlchemy + GeoAlchemy2 models
    api/routes/  auth, municipalities, incidents, upload, clusters, persistence, reports, dashboard
    services/    import_service (CSV/XLSX import + auto-organizing), clustering,
                 persistence_service, locality, evaluation_report, temporal_split_evaluation
    scripts/     seed_municipalities, seed_reference_data, seed_user, purge_synthetic
  migrations/    Alembic
frontend/
  src/
    pages/       LoginPage, DashboardPage, MapPage, UploadPage, RecordsPage, ReportsPage
    components/map/  PPALMAMap, BoundaryLayer, IncidentLayer, ClusterLayer, PersistenceLayer,
                      TimelineControl, LayerControl, HeatmapLayer, MapViewControls, DetailDrawer, ...
    components/ui/   ConfirmDialog, Skeleton, Tooltip, EmptyState, ErrorState
    api/         axios client + typed endpoint functions
data/
  boundaries/    ppalma_municipalities.geojson, ppalma_barangays.json,
                 ppalma_barangay_centroids.json
  evaluation_demo/  sample evaluation-export fixture
  templates/     crime_import_template.csv
```
