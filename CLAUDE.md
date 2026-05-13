# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

DataDash is a Flask web app for analyzing arbitrary user-uploaded CSVs and Excel files. The user-facing language is Spanish — keep UI strings, flash messages, and chart titles in Spanish when editing them.

## Commands

```bash
# First-time setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the dev server (http://localhost:5000)
python app.py

# Or, equivalent via Flask CLI
FLASK_APP=app:create_app flask run --port 5000

# Run tests
pytest tests/ -v
```

There is intentionally **no database** — adding one violates the project constraint.

## Architecture

The flow is `upload → parse → classify → derive → cache → render`. Each stage is one module, kept independent so they can be unit-tested or swapped without touching the others.

### Request lifecycle

1. **`POST /upload`** (`routes/main.py`) — saves the file under `uploads/__tmp_<name>`, runs the pipeline, then **immediately deletes** the temp file in a `finally` block. Storage is ephemeral by design.
2. **Pipeline** runs in this strict order — reorder at your peril:
   - `data_loader.load_dataset` — dispatcher that routes to `load_csv` or `load_excel` based on file extension. CSV: encoding probe (utf-8 → utf-8-sig → latin-1 → cp1252), then `csv.Sniffer` for delimiter (`,;\t|`) with a heuristic fallback. Excel: reads first sheet via `openpyxl`.
   - `data_cleaner.clean` — normalizes null tokens (`""`, `NULL`, `N/A`, `-`, …) to `np.nan`, drops fully-empty rows/columns, strips whitespace. Vectorized; never iterates rows.
   - `column_classifier.classify` — **mutates the DataFrame** by parsing detected datetime columns. Returns `{numeric, categorical, temporal, other}`. Categorical heuristic: `nunique <= 50` OR `nunique/n_rows <= 0.5`. Datetime detection requires ≥80% of a sample to parse AND fails fast for purely-numeric strings (to avoid misclassifying IDs like "12345").
   - `data_loader.optimize_dtypes` — runs *after* classification so it can downcast cleanly.
3. **Derivations**: `stats.numeric_summary`, `stats.dataset_overview`, `chart_builder.build_charts` (capped at `MAX_CHARTS = 12`), `filter_engine.available_filters` (metadata for the frontend filter UI).
4. **Cache**: `core/cache.py:DatasetCache` is a process-local, thread-safe, TTL-expiring dict. The session cookie stores only an opaque UUID token — the DataFrame itself stays in memory keyed by that token. **Sessions don't survive a process restart** by design.
5. **Dashboard render**: chart specs are inlined as `<script type="application/json">` and parsed client-side; the table is fetched lazily via `GET /api/table?page=…&page_size=…`.

### Why the pipeline order is load-bearing

- `clean` runs *before* `classify` because the null-token replacement only works on `object` dtype — once columns become datetime or downcast numeric, `replace({"-": np.nan})` becomes a no-op or raises.
- `classify` runs *before* `optimize_dtypes` because datetime parsing needs the original `object` strings; downcasting changes column dtypes irreversibly.
- `clean` operates on a `df.copy()` so the in-memory cached `df` is independent of whatever was on disk.

### Frontend contract

`chart_builder` emits Chart.js v4 config dicts (`{id, title, type, data, options}`) that the frontend renders verbatim — **no transformation happens in JS**. If a chart looks wrong, the bug is in `chart_builder.py`, not the JS layer.

Values fed into the JSON payload are always Python-native (`int`, `float`, `None`, `str`). NaN/Infinity are sanitized via the `_round` helper because `json.dumps(allow_nan=True)` produces invalid JSON that Chart.js would reject. The smoke test asserts `json.dumps(payload, allow_nan=False)` succeeds.

### Routing surface

- `GET /` — upload form
- `POST /upload` — process + redirect to `/dashboard`
- `GET /dashboard` — KPI cards, numeric summary table, charts grid, filters panel, data table shell
- `POST /reset` — discard current dataset
- `GET /api/charts` · `GET /api/stats` · `GET /api/classification` — JSON for the active dataset
- `GET /api/table?page=<n>&page_size=<n>` (alias `/api/data`) — paginated rows
- `GET /api/filter_options` — metadata for filter UI (unique values, min/max ranges)
- `POST /api/filter` — applies filters, returns recalculated overview/stats/charts/table

API routes return `404` when no dataset is in session, `410` when the cached entry expired (TTL = 1 h, configurable via `Config.DATASET_TTL_SECONDS`).

### Filtering system

`core/filter_engine.py` provides two functions:
- `available_filters(df, classification)` — produces JSON metadata for the frontend filter controls (multi-select for categoricals, min/max for numerics, date range for temporals). Truncates categorical options at 50 (sorted by frequency).
- `apply_filters(df, filters)` — vectorized boolean mask accumulation. Never mutates the original DataFrame. Returns a filtered copy.

The `POST /api/filter` endpoint accepts a JSON body with `filters`, `page`, and `page_size`, and returns a full recalculated payload (overview, stats, charts, table).

## Constraints to respect

- **No database, no ORM.** State lives in `DatasetCache` (memory) and ephemeral temp files only.
- **Bootstrap 5, Chart.js, and jsPDF come from CDNs.** Don't vendor them locally.
- **All pandas work is vectorized.** Don't introduce `for row in df.iterrows()` loops; the upstream spec forbids it.
- **Uploads must be deleted after processing** (the `finally` block in `routes/main.py:upload` handles this). Don't add code paths that bypass it.
- **`MAX_CONTENT_LENGTH = 50 MB`** — bumping it requires also bumping the client-side `MAX_BYTES` in `static/js/upload.js`.
