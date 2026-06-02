# Mejoras DataDash (Fases 3-7) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mejorar robustez, UX, capacidades de análisis, calidad de código y performance de DataDash en cinco fases independientes y mergeables por separado.

**Architecture:** Cada fase es un PR autónomo. El proyecto mantiene su arquitectura sin DB, pipeline `upload → parse → classify → derive → cache → render`, pandas vectorizado y blueprints Flask. Las mejoras se aplican respetando los invariantes existentes: `MAX_CONTENT_LENGTH = 50 MB`, Bootstrap/Chart.js/jsPDF desde CDN, uploads borrados tras procesar, sin base de datos, UI en español.

**Tech Stack:** Python 3 · Flask 3 · pandas 2 · NumPy · openpyxl · Flask-Caching · Bootstrap 5 · Chart.js 4 · jsPDF · pytest.

---

## Estructura de archivos (visión global)

Archivos nuevos por fase:

- Fase 3 — `core/_serde.py` (utils de serialización compartidos).
- Fase 4 — `tests/test_table_search_sort.py`, `tests/test_filter_status.py`.
- Fase 5 — `core/sheet_picker.py`, `core/outliers.py`, `routes/api_custom.py`, `tests/test_phase5.py`.
- Fase 6 — `pyproject.toml`, `requirements.in`, `routes/uploads.py`, `routes/downloads.py`, `routes/dashboard.py`, `routes/_helpers.py`, `tests/test_main_routes.py`, `tests/test_chart_builder.py`.
- Fase 7 — Modificaciones en `core/data_loader.py`, `app.py`, `config.py` (no archivos nuevos).

Archivos modificados según fase: ver cada tarea.

---

# FASE 3 — Robustez y corrección

**Objetivo:** corregir defectos detectados (mutación implícita, duplicación, colisiones, TTLs desalineados, llamadas redundantes) sin cambios visibles al usuario.

**Estimación:** 1 día.

**Branch sugerida:** `fase-3-robustez`.

---

### Task 3.1: Centralizar `_round` en `core/_serde.py`

**Files:**
- Create: `core/_serde.py`
- Modify: `core/stats.py:54-63`
- Modify: `core/correlation.py:58-72`
- Modify: `core/chart_builder.py:250-259`
- Test: `tests/test_serde.py`

- [ ] **Step 1: Crear test que falla**

Crea `tests/test_serde.py`:

```python
# tests/test_serde.py
"""Tests para utilidades de serialización JSON-safe."""
from __future__ import annotations

import math

import numpy as np

from core._serde import safe_round


class TestSafeRound:
    def test_returns_none_for_none(self):
        assert safe_round(None) is None

    def test_returns_none_for_nan(self):
        assert safe_round(float("nan")) is None

    def test_returns_none_for_inf(self):
        assert safe_round(math.inf) is None
        assert safe_round(-math.inf) is None

    def test_returns_none_for_numpy_nan(self):
        assert safe_round(np.nan) is None

    def test_rounds_to_4_decimals_by_default(self):
        assert safe_round(1.234567) == 1.2346

    def test_respects_custom_ndigits(self):
        assert safe_round(1.234567, ndigits=2) == 1.23

    def test_returns_none_for_unparseable(self):
        assert safe_round("not-a-number") is None

    def test_passes_through_integer(self):
        assert safe_round(5) == 5.0
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_serde.py -v
```

Esperado: `ImportError` o `ModuleNotFoundError: No module named 'core._serde'`.

- [ ] **Step 3: Implementar `core/_serde.py`**

```python
# core/_serde.py
"""Utilidades de serialización JSON-safe compartidas por el pipeline.

Cualquier valor numérico que pueda contener NaN/Inf debe pasar por `safe_round`
antes de ser incluido en un payload JSON, porque `json.dumps(allow_nan=True)`
produce JSON no estándar que Chart.js rechaza.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np


def safe_round(value: Any, ndigits: int = 4) -> Optional[float]:
    """Convierte a float redondeado o None si no es serializable.

    Reglas: NaN/Inf/None/unparseable → None. Resto → round(float, ndigits).
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return round(v, ndigits)
```

- [ ] **Step 4: Verificar que el test pasa**

```bash
pytest tests/test_serde.py -v
```

Esperado: 8 passed.

- [ ] **Step 5: Sustituir `_round` en `core/stats.py`**

Edita `core/stats.py`:

- Elimina las líneas 54-63 (función `_round`).
- Añade al inicio: `from core._serde import safe_round`.
- Reemplaza globalmente `_round(` por `safe_round(` en el archivo.

- [ ] **Step 6: Sustituir `_round` en `core/correlation.py`**

Edita `core/correlation.py`:

- Elimina las líneas 58-72 (función `_sanitize`).
- Añade al inicio: `from core._serde import safe_round`.
- Reemplaza `_sanitize(v)` en línea 46 por `_clamp_corr(v)`.
- Añade función local justo encima de `correlation_matrix`:

```python
def _clamp_corr(value: object) -> Optional[float]:
    """Clampa el valor de Pearson a [-1, 1] tras pasarlo por safe_round."""
    v = safe_round(value)
    if v is None:
        return None
    if v > 1.0:
        return 1.0
    if v < -1.0:
        return -1.0
    return v
```

- [ ] **Step 7: Sustituir `_round` en `core/chart_builder.py`**

Edita `core/chart_builder.py`:

- Elimina las líneas 250-259 (función `_round`).
- Añade al inicio: `from core._serde import safe_round`.
- Reemplaza globalmente `_round(` por `safe_round(`.

- [ ] **Step 8: Ejecutar suite completa**

```bash
pytest tests/ -v
```

Esperado: todos los tests previos (61) más los 8 nuevos = 69 passed.

- [ ] **Step 9: Commit**

```bash
git add core/_serde.py core/stats.py core/correlation.py core/chart_builder.py tests/test_serde.py
git commit -m "refactor: consolidate _round helpers into core/_serde.safe_round"
```

---

### Task 3.2: `classify()` deja de mutar el DataFrame

**Files:**
- Modify: `core/column_classifier.py:15-63`
- Modify: `routes/main.py:72-73`
- Test: `tests/test_pipeline.py` (añadir caso explícito)

- [ ] **Step 1: Añadir test que verifica no-mutación**

Añade al final de `tests/test_pipeline.py` (dentro de la sección de classify, antes del `if __name__`):

```python
class TestClassifyNoMutation:
    def test_classify_returns_tuple_and_does_not_mutate_input(self):
        from core.column_classifier import classify
        df = pd.DataFrame({
            "fecha": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "valor": [1, 2, 3],
        })
        original_dtype = df["fecha"].dtype  # object
        new_df, classification = classify(df)
        # El df original NO se mutó.
        assert df["fecha"].dtype == original_dtype
        # El nuevo df SÍ tiene "fecha" como datetime.
        assert pd.api.types.is_datetime64_any_dtype(new_df["fecha"])
        # La clasificación es correcta.
        assert "fecha" in classification["temporal"]
        assert "valor" in classification["numeric"]
```

- [ ] **Step 2: Ejecutar test y verificar fallo**

```bash
pytest tests/test_pipeline.py::TestClassifyNoMutation -v
```

Esperado: FAIL — `classify()` devuelve un dict, no tupla.

- [ ] **Step 3: Modificar `classify()` para devolver tupla `(df, classification)`**

Edita `core/column_classifier.py`. Reemplaza la firma y el cuerpo:

```python
def classify(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """Clasifica las columnas. Devuelve (df_con_fechas_parseadas, clasificacion).

    NO muta `df`. El DataFrame devuelto puede tener columnas temporales
    convertidas a dtype datetime; el original permanece intacto.
    """
    df = df.copy()
    numeric: List[str] = []
    categorical: List[str] = []
    temporal: List[str] = []
    other: List[str] = []
    n_rows = max(1, len(df))
    # ... (resto del cuerpo igual, pero al final:)
    return df, {
        "numeric": numeric,
        "categorical": categorical,
        "temporal": temporal,
        "other": other,
    }
```

Añade `Tuple` al import: `from typing import Dict, List, Optional, Tuple`.

- [ ] **Step 4: Actualizar la llamada en `routes/main.py`**

Edita `routes/main.py` líneas 72-73:

```python
        df = clean(df)
        if df.empty or df.shape[1] == 0:
            raise CSVLoadError("El archivo no contiene datos analizables tras la limpieza.")
        df, classification = classify(df)
        df = optimize_dtypes(df)
```

- [ ] **Step 5: Ejecutar suite completa**

```bash
pytest tests/ -v
```

Esperado: actualizar cualquier test existente en `test_pipeline.py` que use `classify(df)` con la forma antigua. Repasa los casos `TestClassify*` y ajústalos a desestructurar la tupla. Vuelve a ejecutar hasta verde.

- [ ] **Step 6: Commit**

```bash
git add core/column_classifier.py routes/main.py tests/test_pipeline.py
git commit -m "refactor: classify() returns (df, classification) instead of mutating input"
```

---

### Task 3.3: `SECRET_KEY` aborta si falta en producción

**Files:**
- Modify: `config.py:8-17`
- Modify: `app.py:23-46`
- Test: `tests/test_secret_key.py`

- [ ] **Step 1: Test que fuerza fallo en prod sin SECRET**

Crea `tests/test_secret_key.py`:

```python
# tests/test_secret_key.py
"""Garantiza que el SECRET_KEY no es el default en modo no-debug."""
from __future__ import annotations

import os
from unittest import mock

import pytest


def test_create_app_aborts_when_secret_missing_in_production():
    """Si DATADASH_ENV=production y no hay DATADASH_SECRET, debe fallar."""
    from app import create_app

    env = {"DATADASH_ENV": "production"}
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("DATADASH_SECRET", None)
        with pytest.raises(RuntimeError, match="DATADASH_SECRET"):
            create_app()


def test_create_app_works_with_explicit_secret_in_production():
    from app import create_app

    env = {"DATADASH_ENV": "production", "DATADASH_SECRET": "supersecret"}
    with mock.patch.dict(os.environ, env, clear=False):
        app = create_app()
        assert app.config["SECRET_KEY"] == "supersecret"


def test_create_app_works_in_dev_with_default_secret():
    """En modo dev se permite el default para no romper el flujo local."""
    from app import create_app

    env = {"DATADASH_ENV": "development"}
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("DATADASH_SECRET", None)
        app = create_app()
        assert app.config["SECRET_KEY"]  # cualquier valor no vacío
```

- [ ] **Step 2: Ejecutar y verificar fallo**

```bash
pytest tests/test_secret_key.py -v
```

Esperado: FAIL — no se lanza RuntimeError.

- [ ] **Step 3: Modificar `config.py`**

Reemplaza el contenido de `config.py`:

```python
# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEV_DEFAULT_SECRET = "dev-secret-change-me"


class Config:
    SECRET_KEY = os.environ.get("DATADASH_SECRET", DEV_DEFAULT_SECRET)
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}
    DATASET_TTL_SECONDS = 3600
    MAX_CHARTS = 12
    DEFAULT_PAGE_SIZE = 25
    JSON_SORT_KEYS = False
```

- [ ] **Step 4: Añadir la guardia en `app.py`**

Edita `app.py` justo después de `app.config.from_object(config_class)` (línea 25):

```python
    app.config.from_object(config_class)

    env = os.environ.get("DATADASH_ENV", "development").lower()
    if env == "production" and app.config["SECRET_KEY"] == "dev-secret-change-me":
        raise RuntimeError(
            "DATADASH_SECRET no está definido y DATADASH_ENV=production. "
            "Exporta DATADASH_SECRET con un valor aleatorio antes de arrancar."
        )
```

- [ ] **Step 5: Verificar que los tests pasan**

```bash
pytest tests/test_secret_key.py -v
```

Esperado: 3 passed. Después, suite completa para no romper nada:

```bash
pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add config.py app.py tests/test_secret_key.py
git commit -m "feat: refuse to boot in production when DATADASH_SECRET is missing"
```

---

### Task 3.4: Nombre temporal único con UUID

**Files:**
- Modify: `routes/main.py:62-65`
- Test: `tests/test_main_routes.py` (en Fase 6 se crea formalmente; aquí añadimos a `test_phase2.py`).

- [ ] **Step 1: Test de upload concurrente que falla con el código actual**

Añade a `tests/test_phase2.py` dentro de la clase `TestDownloadEndpoints` (o crea `TestUploadIsolation`):

```python
    def test_upload_uses_unique_temp_name(self, app_client, tmp_path):
        """Dos uploads simultáneos con el mismo nombre no deben colisionar.

        Comprobamos que ningún archivo `__tmp_<filename>` queda en disco
        tras procesar (se borra siempre en finally), y que el nombre de
        archivo temporal incluye un componente único (uuid) para evitar
        race conditions.
        """
        import re
        client, _ = app_client
        csv = b"a,b\n1,2\n3,4\n"
        # Subir dos veces el mismo "test.csv" en rápida sucesión.
        for _ in range(2):
            resp = client.post(
                "/upload",
                data={"file": (io.BytesIO(csv), "test.csv")},
                content_type="multipart/form-data",
                follow_redirects=False,
            )
            assert resp.status_code in (302, 303)
        # La carpeta uploads no debe contener residuos.
        upload_dir = Path("uploads")
        leftovers = list(upload_dir.glob("__tmp_*"))
        assert leftovers == [], f"Quedaron uploads sin borrar: {leftovers}"
```

Asegúrate de importar `io` y `Path` al principio del archivo si no lo están.

- [ ] **Step 2: Ejecutar el test**

```bash
pytest tests/test_phase2.py::TestDownloadEndpoints::test_upload_uses_unique_temp_name -v
```

Pasará incluso con el código actual (el `finally` borra el archivo). Esto valida el invariante pero no la colisión. Reforzamos:

- [ ] **Step 3: Test adicional verificando el patrón del nombre temporal**

Añade al mismo archivo:

```python
    def test_temp_filename_contains_uuid_component(self, app_client, tmp_path, monkeypatch):
        """Verifica que el nombre temporal incluye un sufijo único (uuid)."""
        import re
        captured = {}
        from routes import main as main_module
        real_save = main_module.Path

        # Monitor: capturamos el path que recibe `file.save`
        from werkzeug.datastructures import FileStorage
        original_save = FileStorage.save

        def spy_save(self, dst, *a, **kw):
            captured["path"] = str(dst)
            return original_save(self, dst, *a, **kw)

        monkeypatch.setattr(FileStorage, "save", spy_save)

        client, _ = app_client
        csv = b"a,b\n1,2\n"
        client.post(
            "/upload",
            data={"file": (io.BytesIO(csv), "test.csv")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        # Esperamos un patrón __tmp_<hex>_test.csv
        assert "path" in captured
        name = Path(captured["path"]).name
        assert re.match(r"__tmp_[0-9a-f]{8,}_test\.csv$", name), name
```

- [ ] **Step 4: Ejecutar y ver el fallo**

```bash
pytest tests/test_phase2.py::TestDownloadEndpoints::test_temp_filename_contains_uuid_component -v
```

Esperado: FAIL — el nombre actual es `__tmp_test.csv`.

- [ ] **Step 5: Modificar `routes/main.py`**

Edita la sección de creación del temp path (líneas 62-65):

```python
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    # uuid corto para evitar colisiones con uploads concurrentes del mismo nombre.
    unique = uuid.uuid4().hex[:8]
    temp_path = upload_dir / f"__tmp_{unique}_{filename}"
    file.save(temp_path)
```

Añade `import uuid` al principio del archivo.

- [ ] **Step 6: Verificar suite**

```bash
pytest tests/ -v
```

Esperado: todos pasan.

- [ ] **Step 7: Commit**

```bash
git add routes/main.py tests/test_phase2.py
git commit -m "fix: avoid temp-upload name collisions with uuid prefix"
```

---

### Task 3.5: Alinear TTLs de Flask-Caching con `DatasetCache`

**Files:**
- Modify: `config.py`
- Modify: `app.py:16-20`

- [ ] **Step 1: Test que verifica la consistencia**

Crea `tests/test_cache_alignment.py`:

```python
# tests/test_cache_alignment.py
"""El TTL de Flask-Caching debe coincidir con el del dataset principal."""
from __future__ import annotations


def test_flask_cache_ttl_matches_dataset_ttl():
    from app import create_app
    from config import Config

    app = create_app()
    cache = app.config["FLASK_CACHE_INSTANCE"]
    # SimpleCache guarda `default_timeout` directamente.
    assert cache.cache.default_timeout == Config.DATASET_TTL_SECONDS
```

- [ ] **Step 2: Ejecutar y ver fallo**

```bash
pytest tests/test_cache_alignment.py -v
```

Esperado: FAIL — 600 ≠ 3600.

- [ ] **Step 3: Mover el config del cache a `config.py`**

Edita `config.py`, añade dentro de `Config`:

```python
    FLASK_CACHE_CONFIG = {
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 500,
    }
```

- [ ] **Step 4: Consumir el config en `app.py`**

Reemplaza líneas 14-20 de `app.py`:

```python
# Cache global compartido entre blueprints. Configuración derivada de Config.
cache = Cache()
```

Y dentro de `create_app`, después de cargar la config:

```python
    cache.init_app(app, config=app.config["FLASK_CACHE_CONFIG"])
    app.config["FLASK_CACHE_INSTANCE"] = cache
```

- [ ] **Step 5: Ejecutar suite**

```bash
pytest tests/ -v
```

Esperado: el nuevo test pasa, resto sigue verde.

- [ ] **Step 6: Commit**

```bash
git add config.py app.py tests/test_cache_alignment.py
git commit -m "fix: align Flask-Caching TTL with DatasetCache (3600s)"
```

---

### Task 3.6: Eliminar doble cálculo de mediana en `numeric_summary`

**Files:**
- Modify: `core/stats.py:11-38`

- [ ] **Step 1: Test que verifica que la mediana viene de `describe`**

Añade a `tests/test_pipeline.py` (al final de `TestStats` o similar):

```python
    def test_numeric_summary_uses_describe_quantile_for_median(self):
        from core.stats import numeric_summary
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        rows = numeric_summary(df, ["x"])
        assert rows[0]["median"] == 3.0
```

- [ ] **Step 2: Verificar que pasa antes y después**

```bash
pytest tests/test_pipeline.py -k median -v
```

Pasa porque el resultado es el mismo. Pero refactorizamos para no duplicar la pasada por la columna.

- [ ] **Step 3: Refactor `numeric_summary`**

Reemplaza el cuerpo del bucle en `core/stats.py`:

```python
    summaries: List[Dict[str, Any]] = []
    for col in numeric_cols:
        if col not in desc.index:
            continue
        count = desc.at[col, "count"]
        if pd.isna(count) or count == 0:
            continue
        summaries.append(
            {
                "column": col,
                "count": int(count),
                "mean": safe_round(desc.at[col, "mean"]),
                "median": safe_round(desc.at[col, "50%"]),
                "std": safe_round(desc.at[col, "std"]),
                "min": safe_round(desc.at[col, "min"]),
                "max": safe_round(desc.at[col, "max"]),
                "nulls": int(df[col].isna().sum()),
            }
        )
    return summaries
```

- [ ] **Step 4: Ejecutar suite**

```bash
pytest tests/ -v
```

Esperado: verde.

- [ ] **Step 5: Commit**

```bash
git add core/stats.py tests/test_pipeline.py
git commit -m "refactor: read median from describe's 50% column instead of recomputing"
```

---

### Fase 3 — Cierre

- [ ] **PR Final de Fase 3**

```bash
git push -u origin fase-3-robustez
gh pr create --title "Fase 3: robustez y corrección de defectos" --body "$(cat <<'EOF'
## Summary
- SECRET_KEY: aborta si DATADASH_ENV=production y no hay DATADASH_SECRET.
- `classify()` devuelve `(df, classification)` en lugar de mutar.
- Centraliza `_round` → `core/_serde.safe_round`.
- Uploads temporales con sufijo uuid (evita colisiones).
- Alinea TTL Flask-Caching ↔ DatasetCache a 3600 s.
- `numeric_summary` lee mediana de `describe()['50%']`.

## Test plan
- [ ] pytest tests/ -v (todos verdes)
- [ ] Run app en dev sin DATADASH_SECRET (debe arrancar)
- [ ] DATADASH_ENV=production python app.py sin secret → RuntimeError
EOF
)"
```

---

# FASE 4 — UX visible

**Objetivo:** mejorar la experiencia del usuario en la interfaz: confirmación destructiva, búsqueda, sort, feedback de carga, responsividad móvil del heatmap.

**Estimación:** 2 días.

**Branch sugerida:** `fase-4-ux`.

---

### Task 4.1: Confirmación al pulsar "Subir otro archivo"

**Files:**
- Modify: `templates/dashboard.html:43-48`
- Create: `static/js/reset-confirm.js`
- Modify: `templates/dashboard.html` (bloque scripts).

- [ ] **Step 1: Sustituir el formulario inline por un trigger de modal**

En `templates/dashboard.html`, reemplaza el bloque del formulario `reset` (líneas 43-48) por:

```html
        <button id="reset-trigger-btn" class="btn btn-outline-secondary" type="button">
            <i class="bi bi-arrow-counterclockwise me-1"></i> Subir otro archivo
        </button>
        <form id="reset-form" action="{{ url_for('main.reset') }}" method="POST" class="d-none">
        </form>
```

Justo antes del `{% endblock %}` final del bloque content, añade el modal:

```html
<div class="modal fade" id="reset-modal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-exclamation-triangle me-2 text-warning"></i>¿Descartar análisis actual?</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
                <p class="mb-0" id="reset-modal-body">Vas a descartar el dataset actual y volver al inicio.</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-danger" id="reset-confirm-btn">
                    <i class="bi bi-trash me-1"></i> Sí, descartar
                </button>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Crear `static/js/reset-confirm.js`**

```javascript
// static/js/reset-confirm.js
// Intercepta el botón "Subir otro archivo" y abre un modal de confirmación.
// Si hay filtros activos, el modal lo menciona explícitamente.
(function () {
    'use strict';

    const trigger = document.getElementById('reset-trigger-btn');
    const form = document.getElementById('reset-form');
    const modal = document.getElementById('reset-modal');
    const body = document.getElementById('reset-modal-body');
    const confirmBtn = document.getElementById('reset-confirm-btn');
    if (!trigger || !form || !modal || !confirmBtn) return;

    function hasActiveFilters() {
        // filters.js mantiene #filter-status con clase 'text-primary' cuando hay filtros activos.
        const status = document.getElementById('filter-status');
        return status && status.classList.contains('text-primary');
    }

    trigger.addEventListener('click', function () {
        body.textContent = hasActiveFilters()
            ? 'Tienes filtros activos en el análisis. Si continúas, se perderán junto con el dataset.'
            : 'Vas a descartar el dataset actual y volver al inicio.';
        const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
        bsModal.show();
    });

    confirmBtn.addEventListener('click', function () {
        form.submit();
    });
})();
```

- [ ] **Step 3: Incluir el script en `dashboard.html`**

En el bloque `{% block scripts %}` de `templates/dashboard.html`, antes del cierre del bloque, añade:

```html
<script src="{{ url_for('static', filename='js/reset-confirm.js') }}"></script>
```

- [ ] **Step 4: Verificación manual**

Como es UI, ejecuta el servidor:

```bash
python app.py
```

1. Sube un CSV de prueba (`/tmp/sample.csv`).
2. Click "Subir otro archivo" → modal aparece con texto neutro.
3. Aplica un filtro → click "Subir otro archivo" → modal menciona los filtros.
4. Click "Cancelar" → modal se cierra, dataset intacto.
5. Click "Sí, descartar" → redirige al index.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html static/js/reset-confirm.js
git commit -m "feat: confirm before discarding dataset, warn about active filters"
```

---

### Task 4.2: Búsqueda libre en la tabla

**Files:**
- Modify: `core/table_builder.py`
- Modify: `routes/api.py:79-86`
- Modify: `static/js/table.js`
- Modify: `templates/dashboard.html` (tab table)
- Test: `tests/test_table_search.py`

- [ ] **Step 1: Test del filtro de búsqueda en `table_builder`**

Crea `tests/test_table_search.py`:

```python
# tests/test_table_search.py
"""Búsqueda libre en la tabla paginada."""
from __future__ import annotations

import pandas as pd

from core.table_builder import page


class TestPageSearch:
    def test_search_matches_substring_case_insensitive(self):
        df = pd.DataFrame({"nombre": ["Ana", "ANTONIO", "Beatriz"], "x": [1, 2, 3]})
        result = page(df, page_number=1, page_size=10, search="ana")
        # "Ana" y "ANTONIO" matchean (substring case-insensitive: "ANA" en "ANTONIO" no, pero "ana" en "Ana" sí; "ant" en "ANTONIO" no... vamos a ser claros)
        names = [row[0] for row in result["rows"]]
        assert "Ana" in names
        assert "Beatriz" not in names

    def test_search_returns_all_rows_when_empty(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = page(df, page_number=1, page_size=10, search="")
        assert result["total_rows"] == 3

    def test_search_matches_numeric_columns_as_string(self):
        df = pd.DataFrame({"id": [100, 200, 300], "tag": ["a", "b", "c"]})
        result = page(df, page_number=1, page_size=10, search="200")
        assert result["total_rows"] == 1
        assert result["rows"][0][1] == "b"

    def test_search_zero_matches(self):
        df = pd.DataFrame({"x": ["a", "b"]})
        result = page(df, page_number=1, page_size=10, search="zzz")
        assert result["total_rows"] == 0
        assert result["rows"] == []
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_table_search.py -v
```

Esperado: FAIL — `page()` no acepta el kwarg `search`.

- [ ] **Step 3: Extender `core/table_builder.py`**

Reemplaza la firma y añade el filtro al principio de `page`:

```python
def page(
    df: pd.DataFrame,
    page_number: int,
    page_size: int,
    search: str | None = None,
) -> Dict[str, Any]:
    """Devuelve un slice de `df` listo para serializar como JSON.

    Si `search` está presente, filtra primero las filas que contienen el
    substring (case-insensitive) en cualquier columna textual o numérica.
    """
    if search:
        q = str(search).strip().lower()
        if q:
            # Convertimos todo a string una vez y buscamos vectorizadamente.
            joined = df.astype(str).apply(lambda col: col.str.lower())
            mask = joined.apply(lambda col: col.str.contains(q, na=False, regex=False)).any(axis=1)
            df = df.loc[mask].reset_index(drop=True)

    page_size = max(1, min(100, int(page_size)))
    # ... (resto igual)
```

- [ ] **Step 4: Pasar `search` desde el endpoint `/api/table`**

Edita `routes/api.py` la función `table`:

```python
@api_bp.get("/data")
@api_bp.get("/table")
def table():
    payload = _current_payload()
    page_number = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", default=25, type=int) or 25
    search = request.args.get("q", default=None, type=str) or None
    return jsonify(build_page(payload["df"], page_number, page_size, search=search))
```

- [ ] **Step 5: Verificar tests**

```bash
pytest tests/test_table_search.py -v
pytest tests/ -v
```

Esperado: todo verde.

- [ ] **Step 6: Añadir el input de búsqueda al tab table**

Edita `templates/dashboard.html`, dentro de `#tab-table > .card-header`, justo después del `<h5>`:

```html
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <div class="input-group input-group-sm" style="width:auto">
                        <span class="input-group-text"><i class="bi bi-search"></i></span>
                        <input id="table-search" type="search"
                               class="form-control form-control-sm"
                               placeholder="Buscar..." style="width:200px">
                    </div>
                    <label for="page-size" class="small text-muted mb-0">Por página:</label>
                    <select id="page-size" class="form-select form-select-sm" style="width:auto">
                        <option value="10">10</option>
                        <option value="25" selected>25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </select>
                </div>
```

(Elimina el bloque antiguo del label y el select; los acabas de englobar.)

- [ ] **Step 7: Conectar el input en `static/js/table.js`**

Añade al inicio del IIFE (después de obtener los elementos):

```javascript
    const searchInput = document.getElementById('table-search');
    let currentSearch = '';
    let searchTimer = null;
```

Modifica la URL en `load`:

```javascript
        const url = '/api/table?page=' + encodeURIComponent(page) +
                    '&page_size=' + encodeURIComponent(pageSize) +
                    (currentSearch ? '&q=' + encodeURIComponent(currentSearch) : '');
```

Añade al final del IIFE, antes de `load(currentPage, currentPageSize)`:

```javascript
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function () {
                currentSearch = searchInput.value.trim();
                currentPage = 1;
                load(currentPage, currentPageSize);
            }, 250);
        });
    }
```

- [ ] **Step 8: Verificación manual**

```bash
python app.py
```

Sube un CSV, ve al tab "Explorador de Datos", escribe en la búsqueda — la tabla se filtra al cabo de ~250 ms.

- [ ] **Step 9: Commit**

```bash
git add core/table_builder.py routes/api.py static/js/table.js templates/dashboard.html tests/test_table_search.py
git commit -m "feat: free-text search in the data explorer table"
```

---

### Task 4.3: Ordenamiento por columna en la tabla

**Files:**
- Modify: `core/table_builder.py`
- Modify: `routes/api.py`
- Modify: `static/js/table.js`
- Modify: `static/css/styles.css`
- Test: `tests/test_table_sort.py`

- [ ] **Step 1: Test de sort**

Crea `tests/test_table_sort.py`:

```python
# tests/test_table_sort.py
"""Sort por columna en la tabla paginada."""
from __future__ import annotations

import pandas as pd

from core.table_builder import page


class TestPageSort:
    def test_sort_asc_by_existing_column(self):
        df = pd.DataFrame({"x": [3, 1, 2]})
        result = page(df, 1, 10, sort_by="x", sort_dir="asc")
        xs = [r[0] for r in result["rows"]]
        assert xs == [1, 2, 3]

    def test_sort_desc(self):
        df = pd.DataFrame({"x": [1, 3, 2]})
        result = page(df, 1, 10, sort_by="x", sort_dir="desc")
        xs = [r[0] for r in result["rows"]]
        assert xs == [3, 2, 1]

    def test_unknown_column_is_ignored(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = page(df, 1, 10, sort_by="zzz", sort_dir="asc")
        xs = [r[0] for r in result["rows"]]
        assert xs == [1, 2, 3]

    def test_nan_values_pushed_last_on_asc(self):
        df = pd.DataFrame({"x": [3.0, float("nan"), 1.0]})
        result = page(df, 1, 10, sort_by="x", sort_dir="asc")
        xs = [r[0] for r in result["rows"]]
        # nulls al final.
        assert xs[0] == 1.0
        assert xs[1] == 3.0
        assert xs[2] is None
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_table_sort.py -v
```

Esperado: FAIL — `page()` no acepta `sort_by`.

- [ ] **Step 3: Extender `core/table_builder.py`**

Añade tras la lógica de `search`:

```python
    if sort_by and sort_by in df.columns:
        ascending = (sort_dir or "asc").lower() != "desc"
        df = df.sort_values(by=sort_by, ascending=ascending, na_position="last").reset_index(drop=True)
```

Actualiza la firma:

```python
def page(
    df: pd.DataFrame,
    page_number: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> Dict[str, Any]:
```

- [ ] **Step 4: Verificar tests**

```bash
pytest tests/test_table_sort.py -v
```

Esperado: 4 passed.

- [ ] **Step 5: Pasar `sort_by` / `sort_dir` desde el endpoint**

En `routes/api.py` añade dentro de `table`:

```python
    sort_by = request.args.get("sort_by", default=None, type=str) or None
    sort_dir = request.args.get("sort_dir", default=None, type=str) or None
    return jsonify(build_page(payload["df"], page_number, page_size,
                              search=search, sort_by=sort_by, sort_dir=sort_dir))
```

- [ ] **Step 6: Hacer las cabeceras clicables en `table.js`**

En el render del thead, modifica:

```javascript
        thead.innerHTML =
            '<tr>' +
            data.columns
                .map(function (c) {
                    const isSorted = c === currentSort.col;
                    const arrow = isSorted
                        ? (currentSort.dir === 'asc' ? ' ▲' : ' ▼')
                        : '';
                    return '<th data-col="' + escapeHtml(c) + '" class="sortable">' +
                           escapeHtml(c) + '<span class="text-muted small">' + arrow + '</span></th>';
                })
                .join('') +
            '</tr>';
```

Declara estado de sort al inicio del IIFE:

```javascript
    let currentSort = { col: null, dir: null };
```

Modifica el URL builder:

```javascript
        const url = '/api/table?page=' + encodeURIComponent(page) +
                    '&page_size=' + encodeURIComponent(pageSize) +
                    (currentSearch ? '&q=' + encodeURIComponent(currentSearch) : '') +
                    (currentSort.col ? '&sort_by=' + encodeURIComponent(currentSort.col) +
                                       '&sort_dir=' + currentSort.dir : '');
```

Añade el delegate de click después de cargar la primera página:

```javascript
    thead.addEventListener('click', function (e) {
        const th = e.target.closest('th.sortable');
        if (!th) return;
        const col = th.dataset.col;
        if (currentSort.col === col) {
            currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort = { col: col, dir: 'asc' };
        }
        currentPage = 1;
        load(currentPage, currentPageSize);
    });
```

- [ ] **Step 7: CSS para indicar que es clicable**

Añade a `static/css/styles.css`:

```css
#data-table th.sortable {
    cursor: pointer;
    user-select: none;
}
#data-table th.sortable:hover {
    background-color: var(--surface-hover);
}
```

- [ ] **Step 8: Verificación manual**

```bash
python app.py
```

Click en una cabecera → orden asc; click otra vez → desc; click en otra → asc por la nueva.

- [ ] **Step 9: Commit**

```bash
git add core/table_builder.py routes/api.py static/js/table.js static/css/styles.css tests/test_table_sort.py
git commit -m "feat: click-to-sort column headers in the data explorer table"
```

---

### Task 4.4: Spinner cubriendo el dashboard durante recalc

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `static/js/filters.js`
- Modify: `static/css/styles.css`

- [ ] **Step 1: Añadir overlay HTML**

En `templates/dashboard.html`, dentro de `.tab-content` y como primer hijo (antes de los `tab-pane`), añade:

```html
<div id="dashboard-overlay" class="dashboard-overlay d-none" aria-live="polite">
    <div class="dashboard-overlay-inner">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Cargando…</span>
        </div>
        <div class="mt-2 small text-muted">Aplicando filtros…</div>
    </div>
</div>
```

- [ ] **Step 2: CSS para el overlay**

Añade a `static/css/styles.css`:

```css
.dashboard-overlay {
    position: fixed;
    inset: 0;
    background: color-mix(in srgb, var(--bg) 70%, transparent);
    z-index: 1050;
    display: flex;
    align-items: center;
    justify-content: center;
}
.dashboard-overlay-inner {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 1.25rem 1.5rem;
    text-align: center;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}
.d-none.dashboard-overlay { display: none !important; }
```

- [ ] **Step 3: Activar el overlay en `filters.js`**

En `static/js/filters.js`, modifica `applyFilters` para mostrar y ocultar el overlay:

```javascript
    async function applyFilters() {
        const { filters, count } = collectFilters();
        const overlay = document.getElementById('dashboard-overlay');
        if (overlay) overlay.classList.remove('d-none');
        setBusy(true);
        let res;
        try {
            // ... (resto igual)
        } catch (err) {
            // ...
        } finally {
            if (overlay) overlay.classList.add('d-none');
        }
        // ...
    }
```

Asegúrate de que el `finally` se ejecuta siempre — reordena las returns tempranas para que vayan a un único punto de salida o duplica el `overlay.classList.add('d-none')` en cada return.

Versión más segura:

```javascript
    async function applyFilters() {
        const { filters, count } = collectFilters();
        const overlay = document.getElementById('dashboard-overlay');
        const hideOverlay = function () { if (overlay) overlay.classList.add('d-none'); };
        if (overlay) overlay.classList.remove('d-none');
        setBusy(true);
        try {
            // ... cuerpo entero del try/await original
        } finally {
            setBusy(false);
            hideOverlay();
        }
    }
```

- [ ] **Step 4: Verificación manual**

Con un dataset grande (>100k filas), aplicar filtros muestra el overlay durante el cálculo. Probar también que se cierra al fallar la red (devtools → throttling offline).

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html static/js/filters.js static/css/styles.css
git commit -m "feat: loading overlay while filters recalc the dashboard"
```

---

### Task 4.5: Heatmap responsive en móvil (scroll horizontal)

**Files:**
- Modify: `static/css/styles.css`
- Modify: `static/js/heatmap.js`

- [ ] **Step 1: Envolver el grid en un scroll container**

En `static/js/heatmap.js`, dentro de `render`, justo antes del `container.innerHTML = ...`, envuelve el contenido:

```javascript
        container.innerHTML =
            '<div class="hm-scroll">' +
            '<div class="hm-grid" style="grid-template-columns:' + gridTemplate + '">' +
            cells.join('') +
            '</div>' +
            '</div>' +
            legend +
            note;
```

- [ ] **Step 2: CSS**

Añade a `static/css/styles.css`:

```css
.hm-scroll {
    overflow-x: auto;
    overflow-y: hidden;
    max-width: 100%;
}
@media (max-width: 576px) {
    .hm-grid {
        font-size: 0.65rem;
    }
}
```

- [ ] **Step 3: Verificación manual**

```bash
python app.py
```

DevTools → emular pantalla mobile (375 px), abrir un CSV con >10 columnas numéricas, ver que el heatmap tiene scroll horizontal y no rompe el layout.

- [ ] **Step 4: Commit**

```bash
git add static/js/heatmap.js static/css/styles.css
git commit -m "feat: horizontal scroll for correlation heatmap on small screens"
```

---

### Task 4.6: Estados vacíos granulares en el tab "Análisis Visual"

**Files:**
- Modify: `core/chart_builder.py`
- Modify: `static/js/dashboard.js`
- Modify: `templates/dashboard.html`

- [ ] **Step 1: Test que el builder reporta razón cuando no genera nada**

Añade a `tests/test_chart_builder.py` (se crea más completo en Fase 6, pero arrancamos):

```python
# tests/test_chart_builder.py
"""Tests rápidos para mensajes de estado vacío del chart_builder."""
from __future__ import annotations

import pandas as pd

from core.chart_builder import build_charts


class TestEmpty:
    def test_returns_empty_list_when_no_usable_columns(self):
        df = pd.DataFrame({"id_unico": [str(i) for i in range(1000)]})
        # Se clasificaría como "other" (alta cardinalidad).
        result = build_charts(df, {
            "numeric": [], "categorical": [], "temporal": [], "other": ["id_unico"]
        })
        assert result == []
```

- [ ] **Step 2: Mostrar mensajes específicos según composición**

Edita `templates/dashboard.html` el bloque del tab-charts:

```html
            <div id="charts-empty" class="alert alert-info d-none">
                <i class="bi bi-info-circle me-1"></i>
                <span id="charts-empty-text">No se pudieron generar gráficos automáticos para este conjunto de datos.</span>
            </div>
```

- [ ] **Step 3: Lógica en `dashboard.js`**

En `Dashboard.renderCharts`, antes del `if (!Array.isArray(specs) ...)`, añade una función que decide el mensaje:

```javascript
    function emptyMessage() {
        // Lee `window.Dashboard.classification` (lo seteamos desde el template).
        const cls = (window.Dashboard && window.Dashboard.classification) || {};
        const hasNum = (cls.numeric || []).length > 0;
        const hasCat = (cls.categorical || []).length > 0;
        const hasTmp = (cls.temporal || []).length > 0;
        if (!hasNum && !hasCat && !hasTmp) {
            return 'Las columnas detectadas son de alta cardinalidad o no contienen datos analizables. Prueba con otro archivo.';
        }
        return 'No se pudieron generar gráficos automáticos. Aplica filtros para reducir el dataset y vuelve a intentarlo.';
    }
```

Y en el bloque que activa `charts-empty`:

```javascript
        if (!Array.isArray(specs) || specs.length === 0) {
            if (empty) {
                const txt = document.getElementById('charts-empty-text');
                if (txt) txt.textContent = emptyMessage();
                empty.classList.remove('d-none');
            }
            return;
        }
```

- [ ] **Step 4: Exponer la clasificación desde el template**

En `templates/dashboard.html`, dentro del bloque de scripts, justo antes del primer `<script>` propio, añade:

```html
<script id="classification-payload" type="application/json">{{ classification | tojson }}</script>
```

Y en `static/js/dashboard.js` al inicio del IIFE:

```javascript
    const clsEl = document.getElementById('classification-payload');
    if (clsEl) {
        try {
            window.Dashboard = window.Dashboard || {};
            window.Dashboard.classification = JSON.parse(clsEl.textContent);
        } catch (_) { /* noop */ }
    }
```

- [ ] **Step 5: Verificación manual**

Sube un CSV donde todas las columnas sean texto único (e.g. UUIDs). El tab "Análisis Visual" debe mostrar "Las columnas detectadas son de alta cardinalidad...".

Sube un CSV con datos normales pero filtra hasta dejar 0 filas — el mensaje debe ser el otro.

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard.html static/js/dashboard.js tests/test_chart_builder.py
git commit -m "feat: granular empty-state messages in the visualization tab"
```

---

### Fase 4 — Cierre

- [ ] **PR Final de Fase 4**

```bash
git push -u origin fase-4-ux
gh pr create --title "Fase 4: mejoras de UX (búsqueda, sort, modal, overlay)" --body "$(cat <<'EOF'
## Summary
- Modal de confirmación al pulsar "Subir otro archivo" (avisa de filtros activos).
- Búsqueda libre en la tabla del Explorador de Datos.
- Click-to-sort en cabeceras de columna.
- Overlay con spinner mientras los filtros recalculan.
- Heatmap con scroll horizontal en pantallas pequeñas.
- Estados vacíos más informativos en el tab de gráficos.

## Test plan
- [ ] pytest tests/ -v
- [ ] Subir CSV, aplicar filtros, click "Subir otro archivo" — modal correcto.
- [ ] Buscar "x" en la tabla — filtra al instante.
- [ ] Click en cabecera de columna — ordena asc, click otra vez → desc.
- [ ] DevTools mobile 375px → heatmap con scroll horizontal.
EOF
)"
```

---

# FASE 5 — Capacidades de datos

**Objetivo:** ampliar el análisis con multi-hoja Excel, override de tipos, detección de outliers, filtros OR y gráficos personalizados.

**Estimación:** 2-3 días.

**Branch sugerida:** `fase-5-datos`.

---

### Task 5.1: Selector de hoja en Excel

**Files:**
- Create: `core/sheet_picker.py`
- Modify: `core/data_loader.py:101-130`
- Modify: `routes/main.py` (`upload`)
- Modify: `templates/index.html` (ver Step 5)
- Create: `templates/sheet_picker.html`
- Test: `tests/test_sheet_picker.py`

- [ ] **Step 1: Test que detecta hojas**

Crea `tests/test_sheet_picker.py`:

```python
# tests/test_sheet_picker.py
"""Detección y selección de hojas en archivos Excel."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.sheet_picker import list_sheets, load_sheet


def _make_workbook(tmp_path: Path) -> Path:
    p = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        pd.DataFrame({"a": [1, 2]}).to_excel(w, sheet_name="Ventas", index=False)
        pd.DataFrame({"b": [3, 4]}).to_excel(w, sheet_name="Clientes", index=False)
    return p


class TestSheetPicker:
    def test_list_sheets_returns_all(self, tmp_path):
        p = _make_workbook(tmp_path)
        assert list_sheets(p) == ["Ventas", "Clientes"]

    def test_load_sheet_by_name(self, tmp_path):
        p = _make_workbook(tmp_path)
        df = load_sheet(p, "Clientes")
        assert list(df.columns) == ["b"]

    def test_load_sheet_default_first(self, tmp_path):
        p = _make_workbook(tmp_path)
        df = load_sheet(p, None)
        assert list(df.columns) == ["a"]
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_sheet_picker.py -v
```

Esperado: ImportError.

- [ ] **Step 3: Implementar `core/sheet_picker.py`**

```python
# core/sheet_picker.py
"""Selección de hoja en archivos Excel."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd

from core.data_loader import CSVLoadError


def list_sheets(path: Path) -> List[str]:
    try:
        return list(pd.ExcelFile(path, engine="openpyxl").sheet_names)
    except Exception as exc:
        raise CSVLoadError(f"No se pudieron listar las hojas del Excel: {exc}") from exc


def load_sheet(path: Path, sheet: Optional[str]) -> pd.DataFrame:
    try:
        if sheet is None:
            return pd.read_excel(path, engine="openpyxl", sheet_name=0)
        return pd.read_excel(path, engine="openpyxl", sheet_name=sheet)
    except ValueError as exc:
        raise CSVLoadError(f"Hoja '{sheet}' no encontrada en el archivo.") from exc
```

- [ ] **Step 4: Integrar selector en el flujo de upload**

Modifica `routes/main.py:upload`. Si el archivo es `.xlsx` y tiene >1 hoja, en lugar de procesar directamente, redirige a una nueva vista `/upload/sheet`.

Implementación:

```python
# Justo antes de `df = load_dataset(temp_path)` añade:
if extension == "xlsx":
    from core.sheet_picker import list_sheets
    sheets = list_sheets(temp_path)
    if len(sheets) > 1 and request.form.get("sheet") is None:
        # Guardamos el temp file con un nombre estable para reusarlo en la confirmación.
        # Movemos el archivo a un nombre indexado por uuid en una zona "pending".
        pending_dir = upload_dir / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        pending_token = uuid.uuid4().hex
        pending_path = pending_dir / f"{pending_token}.xlsx"
        temp_path.rename(pending_path)
        # Limpiamos referencia para que el finally no borre lo que acabamos de mover.
        temp_path = pending_path
        session["pending_upload"] = {
            "path": str(pending_path),
            "filename": filename,
            "sheets": sheets,
        }
        return redirect(url_for("main.choose_sheet"))
```

Asegúrate de que el `finally` no borra el archivo movido — añade un flag:

```python
moved = False
try:
    # ... lógica anterior, si movemos, marcamos moved = True
finally:
    if not moved:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            ...
```

Añade nuevo route:

```python
@main_bp.get("/upload/sheet")
def choose_sheet():
    pending = session.get("pending_upload")
    if not pending:
        return redirect(url_for("main.index"))
    return render_template("sheet_picker.html",
                           filename=pending["filename"],
                           sheets=pending["sheets"])


@main_bp.post("/upload/sheet")
def process_sheet():
    pending = session.pop("pending_upload", None)
    if not pending:
        return redirect(url_for("main.index"))
    sheet = request.form.get("sheet")
    if not sheet or sheet not in pending["sheets"]:
        flash("Selecciona una hoja válida.", "danger")
        session["pending_upload"] = pending
        return redirect(url_for("main.choose_sheet"))

    from core.sheet_picker import load_sheet
    temp_path = Path(pending["path"])
    try:
        df = load_sheet(temp_path, sheet)
        df = clean(df)
        if df.empty or df.shape[1] == 0:
            raise CSVLoadError("La hoja seleccionada no contiene datos analizables.")
        df, classification = classify(df)
        df = optimize_dtypes(df)
    except CSVLoadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.index"))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    overview = dataset_overview(df, classification)
    stats = numeric_summary(df, classification["numeric"])
    charts = build_charts(df, classification)
    filter_options = available_filters(df, classification)
    correlation = correlation_matrix(df, classification["numeric"])
    # Resto del cache (igual que en upload).
    # ... (extrae el bloque común a una función `_store_payload`)
```

Para evitar duplicar tanta lógica, refactor: extrae a una función privada `_persist_dataset(df, classification, filename)` que devuelve el token, y úsala en ambos endpoints.

- [ ] **Step 5: Plantilla `templates/sheet_picker.html`**

```html
{% extends 'base.html' %}

{% block title %}Selecciona una hoja — {{ filename }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-6">
        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <h5 class="fw-bold mb-3"><i class="bi bi-file-earmark-spreadsheet me-2"></i>{{ filename }}</h5>
                <p class="text-muted small">Este archivo contiene varias hojas. Selecciona la que quieres analizar:</p>
                <form action="{{ url_for('main.process_sheet') }}" method="POST" class="d-flex gap-2">
                    <select name="sheet" class="form-select">
                        {% for s in sheets %}
                            <option value="{{ s }}">{{ s }}</option>
                        {% endfor %}
                    </select>
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-play-fill me-1"></i>Analizar
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Verificación**

```bash
pytest tests/test_sheet_picker.py -v
pytest tests/ -v
python app.py
```

Sube un Excel con 2 hojas → ver el selector → elegir → dashboard. Sube un Excel de 1 hoja → flujo directo (sin selector).

- [ ] **Step 7: Commit**

```bash
git add core/sheet_picker.py core/data_loader.py routes/main.py templates/sheet_picker.html tests/test_sheet_picker.py
git commit -m "feat: sheet picker for Excel files with multiple sheets"
```

---

### Task 5.2: Override manual del tipo de columna

**Files:**
- Modify: `core/column_classifier.py`
- Modify: `routes/api.py`
- Modify: `static/js/dashboard.js` o nuevo `static/js/reclassify.js`
- Modify: `templates/dashboard.html`
- Test: `tests/test_reclassify.py`

- [ ] **Step 1: Test de re-clasificación**

Crea `tests/test_reclassify.py`:

```python
# tests/test_reclassify.py
"""Override manual del tipo clasificado por columna."""
from __future__ import annotations

import io
import json

import pandas as pd
import pytest

from app import create_app
from core.cache import dataset_cache


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_reclassify_moves_column_between_buckets(client):
    df = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
    classification = {
        "numeric": ["x"], "categorical": ["y"], "temporal": [], "other": []
    }
    payload = {
        "df": df, "classification": classification,
        "overview": {}, "stats": [], "charts": [], "filter_options": {},
        "correlation": {}, "filename": "t.csv",
    }
    token = dataset_cache.put(payload)
    with client.session_transaction() as sess:
        sess["dataset_token"] = token

    resp = client.post("/api/reclassify", json={"x": "categorical"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "x" in data["classification"]["categorical"]
    assert "x" not in data["classification"]["numeric"]
```

- [ ] **Step 2: Endpoint `/api/reclassify`**

Añade a `routes/api.py`:

```python
@api_bp.post("/reclassify")
def reclassify():
    """Mueve columnas entre buckets de clasificación.

    Body: { "<col>": "numeric" | "categorical" | "temporal" | "other" }
    """
    token, payload = _current_token_and_payload()
    overrides = request.get_json(silent=True) or {}
    if not isinstance(overrides, dict):
        return jsonify({"error": "Body debe ser un dict {columna: tipo}."}), 400

    valid = {"numeric", "categorical", "temporal", "other"}
    classification = {k: list(v) for k, v in payload["classification"].items()}
    df = payload["df"]

    for col, target in overrides.items():
        if col not in df.columns or target not in valid:
            continue
        # Remueve la columna de su bucket actual.
        for bucket in classification.values():
            if col in bucket:
                bucket.remove(col)
        # Si el target es temporal, intenta parsear in-place.
        if target == "temporal":
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except (TypeError, ValueError):
                target = "other"
        elif target == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        classification[target].append(col)

    # Re-deriva todo lo que depende de classification.
    payload["classification"] = classification
    payload["overview"] = dataset_overview(df, classification)
    payload["stats"] = numeric_summary(df, classification["numeric"])
    payload["charts"] = build_charts(df, classification)
    payload["correlation"] = correlation_matrix(df, classification["numeric"])
    from core.filter_engine import available_filters
    payload["filter_options"] = available_filters(df, classification)

    # Invalida caché de filtros derivada para el token.
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE")
    if flask_cache is not None:
        flask_cache.clear()

    return jsonify({
        "classification": classification,
        "overview": payload["overview"],
        "stats": payload["stats"],
        "charts": payload["charts"],
        "correlation": payload["correlation"],
        "filter_options": payload["filter_options"],
    })
```

Importa `pd`, `dataset_overview`, `numeric_summary`, `build_charts`, `correlation_matrix` al principio del archivo.

- [ ] **Step 3: UI mínima**

En `templates/dashboard.html`, dentro del card de "Resumen de variables numéricas" (o en una nueva card adyacente), añade un control por columna que permita cambiar su tipo:

```html
<div class="card border-0 shadow-sm mb-4">
    <div class="card-header bg-white border-0">
        <h5 class="fw-semibold mb-0"><i class="bi bi-tools me-1"></i> Ajustar tipos de columna</h5>
    </div>
    <div class="card-body">
        <div id="reclassify-container" class="row g-2"></div>
        <div class="text-end mt-3">
            <button id="reclassify-apply-btn" class="btn btn-primary btn-sm">
                Aplicar cambios
            </button>
        </div>
    </div>
</div>
```

- [ ] **Step 4: Script `static/js/reclassify.js`**

```javascript
// static/js/reclassify.js
(function () {
    'use strict';
    const container = document.getElementById('reclassify-container');
    const btn = document.getElementById('reclassify-apply-btn');
    if (!container || !btn) return;

    const cls = (window.Dashboard && window.Dashboard.classification) || {};
    const allCols = []
        .concat((cls.numeric || []).map(c => ({ col: c, type: 'numeric' })))
        .concat((cls.categorical || []).map(c => ({ col: c, type: 'categorical' })))
        .concat((cls.temporal || []).map(c => ({ col: c, type: 'temporal' })))
        .concat((cls.other || []).map(c => ({ col: c, type: 'other' })));

    function escapeHtml(s) {
        const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML;
    }
    container.innerHTML = allCols.map(function (entry) {
        const sel = ['numeric', 'categorical', 'temporal', 'other']
            .map(t => '<option value="' + t + '"' + (t === entry.type ? ' selected' : '') + '>' + t + '</option>')
            .join('');
        return (
            '<div class="col-md-4">' +
            '<label class="form-label small">' + escapeHtml(entry.col) + '</label>' +
            '<select data-col="' + escapeHtml(entry.col) + '" class="form-select form-select-sm reclassify-sel">' +
            sel + '</select></div>'
        );
    }).join('');

    btn.addEventListener('click', async function () {
        const payload = {};
        container.querySelectorAll('.reclassify-sel').forEach(function (s) {
            payload[s.dataset.col] = s.value;
        });
        btn.disabled = true;
        try {
            const res = await fetch('/api/reclassify', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            // Forzamos recarga para reflejar todos los cambios derivados.
            window.location.reload();
        } catch (err) {
            alert('No se pudo aplicar la reclasificación: ' + err.message);
        } finally {
            btn.disabled = false;
        }
    });
})();
```

Incluye el script al final del `{% block scripts %}` en `dashboard.html`.

- [ ] **Step 5: Verificación**

```bash
pytest tests/test_reclassify.py -v
python app.py
```

Sube un CSV donde "12345" sea un ID numérico mal clasificado como numérico — cámbialo a categorical, aplica, los gráficos y filtros lo reflejan.

- [ ] **Step 6: Commit**

```bash
git add routes/api.py templates/dashboard.html static/js/reclassify.js tests/test_reclassify.py
git commit -m "feat: manual column type override via /api/reclassify"
```

---

### Task 5.3: Detección de outliers

**Files:**
- Create: `core/outliers.py`
- Modify: `core/stats.py:11-38` (incluir conteo de outliers)
- Modify: `templates/dashboard.html` (tabla numérica)
- Test: `tests/test_outliers.py`

- [ ] **Step 1: Test del detector**

Crea `tests/test_outliers.py`:

```python
# tests/test_outliers.py
from __future__ import annotations

import pandas as pd

from core.outliers import iqr_outlier_count


class TestIQROutliers:
    def test_no_outliers_in_uniform_distribution(self):
        s = pd.Series(range(1, 101))
        assert iqr_outlier_count(s) == 0

    def test_detects_extreme_values(self):
        s = pd.Series([1, 2, 3, 4, 5, 100])
        assert iqr_outlier_count(s) == 1

    def test_ignores_nan(self):
        s = pd.Series([1, 2, 3, None, 1000])
        assert iqr_outlier_count(s) == 1

    def test_empty_series_returns_zero(self):
        assert iqr_outlier_count(pd.Series([], dtype=float)) == 0

    def test_constant_series_returns_zero(self):
        assert iqr_outlier_count(pd.Series([5, 5, 5, 5])) == 0
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_outliers.py -v
```

Esperado: ImportError.

- [ ] **Step 3: Implementar `core/outliers.py`**

```python
# core/outliers.py
"""Detección simple de outliers con IQR (Tukey)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def iqr_outlier_count(series: pd.Series, k: float = 1.5) -> int:
    """Cuenta valores fuera de [Q1 - k*IQR, Q3 + k*IQR].

    Para series vacías, constantes o sin valor numérico válido devuelve 0.
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return 0
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0 or np.isnan(iqr):
        return 0
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return int(((s < lo) | (s > hi)).sum())
```

- [ ] **Step 4: Incluir outliers en `numeric_summary`**

En `core/stats.py`, importa `from core.outliers import iqr_outlier_count` y añade al dict:

```python
                "outliers": iqr_outlier_count(df[col]),
```

- [ ] **Step 5: Renderizar en la tabla**

Edita `templates/dashboard.html` el `<thead>` de stats:

```html
<th>Outliers</th>
```

Y el `<tbody>` (Jinja):

```html
<td>{{ row.outliers if row.outliers is defined else '—' }}</td>
```

Y en `static/js/filters.js` la función `renderStats`, añade la celda:

```javascript
                    '<td>' + Number(r.outliers || 0).toLocaleString() + '</td>' +
```

- [ ] **Step 6: Verificar suite**

```bash
pytest tests/ -v
```

- [ ] **Step 7: Commit**

```bash
git add core/outliers.py core/stats.py templates/dashboard.html static/js/filters.js tests/test_outliers.py
git commit -m "feat: IQR-based outlier count in the numeric summary table"
```

---

### Task 5.4: Filtros OR entre columnas

**Files:**
- Modify: `core/filter_engine.py:105-162`
- Modify: `routes/api.py:117-182`
- Modify: `static/js/filters.js`
- Modify: `templates/dashboard.html` (toggle global)
- Test: `tests/test_filter_or.py`

- [ ] **Step 1: Test del modo OR**

Crea `tests/test_filter_or.py`:

```python
# tests/test_filter_or.py
from __future__ import annotations

import pandas as pd

from core.filter_engine import apply_filters


class TestFilterOR:
    def test_or_combines_two_categorical_columns(self):
        df = pd.DataFrame({
            "color": ["red", "blue", "green", "red"],
            "size": ["S", "M", "L", "XL"],
        })
        filters = {
            "categorical": {"color": ["red"], "size": ["M"]},
            "combinator": "OR",
        }
        out = apply_filters(df, filters)
        # OR: rojos OR tamaño M → 3 filas (0, 1, 3).
        assert len(out) == 3

    def test_and_is_default(self):
        df = pd.DataFrame({
            "color": ["red", "blue", "red"],
            "size": ["S", "M", "L"],
        })
        filters = {"categorical": {"color": ["red"], "size": ["S"]}}
        out = apply_filters(df, filters)
        assert len(out) == 1
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_filter_or.py -v
```

Esperado: FAIL — el código actual hace AND siempre.

- [ ] **Step 3: Refactor `apply_filters`**

Reemplaza el cuerpo de `apply_filters`:

```python
def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if not filters or not isinstance(filters, dict):
        return df

    combinator = (filters.get("combinator") or "AND").upper()
    if combinator not in ("AND", "OR"):
        combinator = "AND"

    masks: List[pd.Series] = []

    for col, allowed in (filters.get("categorical") or {}).items():
        if col not in df.columns or not allowed:
            continue
        if not isinstance(allowed, (list, tuple, set)):
            continue
        allowed_str = {str(v) for v in allowed}
        col_str = df[col].astype("string")
        masks.append(col_str.isin(allowed_str))

    for col, bounds in (filters.get("numeric") or {}).items():
        if col not in df.columns or not isinstance(bounds, dict):
            continue
        col_num = pd.to_numeric(df[col], errors="coerce")
        lo = bounds.get("min")
        hi = bounds.get("max")
        m = pd.Series(True, index=df.index)
        if lo is not None:
            try:
                m &= col_num >= float(lo)
            except (TypeError, ValueError):
                pass
        if hi is not None:
            try:
                m &= col_num <= float(hi)
            except (TypeError, ValueError):
                pass
        masks.append(m)

    for col, bounds in (filters.get("temporal") or {}).items():
        if col not in df.columns or not isinstance(bounds, dict):
            continue
        col_dt = pd.to_datetime(df[col], errors="coerce")
        start = bounds.get("start")
        end = bounds.get("end")
        m = pd.Series(True, index=df.index)
        if start:
            try:
                m &= col_dt >= pd.Timestamp(start)
            except (TypeError, ValueError):
                pass
        if end:
            try:
                m &= col_dt <= pd.Timestamp(end)
            except (TypeError, ValueError):
                pass
        masks.append(m)

    if not masks:
        return df

    if combinator == "OR":
        final = masks[0]
        for m in masks[1:]:
            final |= m
    else:
        final = masks[0]
        for m in masks[1:]:
            final &= m

    return df.loc[final].reset_index(drop=True)
```

Asegúrate de añadir `from typing import List` si no está.

- [ ] **Step 4: Toggle UI**

En `templates/dashboard.html`, dentro del filters panel header, junto al status:

```html
<div class="form-check form-switch ms-auto">
    <input class="form-check-input" type="checkbox" role="switch" id="filter-or-toggle">
    <label class="form-check-label small" for="filter-or-toggle">Combinar con OR</label>
</div>
```

Y en `filters.js`, en `collectFilters`:

```javascript
        const orToggle = document.getElementById('filter-or-toggle');
        if (orToggle && orToggle.checked) {
            filters.combinator = "OR";
        }
```

- [ ] **Step 5: Verificación**

```bash
pytest tests/test_filter_or.py -v
python app.py
```

- [ ] **Step 6: Commit**

```bash
git add core/filter_engine.py static/js/filters.js templates/dashboard.html tests/test_filter_or.py
git commit -m "feat: OR combinator for cross-column filters"
```

---

### Task 5.5: Constructor de gráficos personalizado

**Files:**
- Create: `routes/api_custom.py`
- Modify: `app.py` (registrar blueprint)
- Modify: `templates/dashboard.html` (botón + modal)
- Create: `static/js/custom-chart.js`
- Test: `tests/test_custom_chart.py`

- [ ] **Step 1: Test del endpoint custom**

Crea `tests/test_custom_chart.py`:

```python
# tests/test_custom_chart.py
from __future__ import annotations

import pandas as pd
import pytest

from app import create_app
from core.cache import dataset_cache


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _seed_dataset(client) -> str:
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 20, 15, 25], "cat": ["a", "b", "a", "b"]})
    payload = {
        "df": df,
        "classification": {"numeric": ["x", "y"], "categorical": ["cat"], "temporal": [], "other": []},
        "overview": {}, "stats": [], "charts": [], "filter_options": {},
        "correlation": {}, "filename": "t.csv",
    }
    token = dataset_cache.put(payload)
    with client.session_transaction() as sess:
        sess["dataset_token"] = token
    return token


def test_custom_scatter(client):
    _seed_dataset(client)
    resp = client.post("/api/chart/custom", json={
        "type": "scatter", "x": "x", "y": "y"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "scatter"
    assert data["data"]["datasets"][0]["data"][0] == {"x": 1, "y": 10}


def test_invalid_columns_returns_400(client):
    _seed_dataset(client)
    resp = client.post("/api/chart/custom", json={
        "type": "scatter", "x": "x", "y": "no-existe"
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Verificar fallo**

```bash
pytest tests/test_custom_chart.py -v
```

Esperado: 404 — no existe `/api/chart/custom`.

- [ ] **Step 3: Implementar el blueprint**

Crea `routes/api_custom.py`:

```python
# routes/api_custom.py
"""Constructor de gráficos personalizados por usuario."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
from flask import Blueprint, abort, jsonify, request, session

from core.cache import dataset_cache

api_custom_bp = Blueprint("api_custom", __name__)

ALLOWED_TYPES = {"scatter", "bar", "line"}


def _payload() -> Dict[str, Any]:
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="Dataset expirado.")
    return payload


@api_custom_bp.post("/chart/custom")
def custom_chart():
    body = request.get_json(silent=True) or {}
    chart_type = body.get("type")
    x = body.get("x")
    y = body.get("y")

    if chart_type not in ALLOWED_TYPES:
        return jsonify({"error": f"Tipo no soportado. Usa: {sorted(ALLOWED_TYPES)}"}), 400
    payload = _payload()
    df: pd.DataFrame = payload["df"]
    if x not in df.columns or y not in df.columns:
        return jsonify({"error": "Columna X o Y no existe en el dataset."}), 400

    pair = df[[x, y]].dropna()
    if pair.empty:
        return jsonify({"error": "No hay datos válidos para esa combinación."}), 400

    if chart_type == "scatter":
        if not (pd.api.types.is_numeric_dtype(pair[x]) and pd.api.types.is_numeric_dtype(pair[y])):
            return jsonify({"error": "Scatter requiere dos columnas numéricas."}), 400
        if len(pair) > 2000:
            pair = pair.sample(2000, random_state=42)
        points = [{"x": float(a), "y": float(b)} for a, b in pair.itertuples(index=False, name=None)]
        return jsonify({
            "id": f"custom-scatter-{x}-{y}",
            "title": f"{y} vs {x}",
            "type": "scatter",
            "data": {"datasets": [{"label": f"{y} vs {x}", "data": points,
                                   "pointRadius": 3}]},
            "options": {"responsive": True, "maintainAspectRatio": False,
                        "scales": {"x": {"type": "linear", "title": {"display": True, "text": x}},
                                   "y": {"title": {"display": True, "text": y}}}},
        })

    if chart_type == "bar":
        grouped = pair.groupby(x)[y].mean().sort_index()
        return jsonify({
            "id": f"custom-bar-{x}-{y}",
            "title": f"{y} medio por {x}",
            "type": "bar",
            "data": {"labels": [str(v) for v in grouped.index],
                     "datasets": [{"label": f"{y} medio", "data": [float(v) for v in grouped.values]}]},
            "options": {"responsive": True, "maintainAspectRatio": False},
        })

    if chart_type == "line":
        sorted_pair = pair.sort_values(x)
        return jsonify({
            "id": f"custom-line-{x}-{y}",
            "title": f"{y} a lo largo de {x}",
            "type": "line",
            "data": {"labels": [str(v) for v in sorted_pair[x]],
                     "datasets": [{"label": y, "data": [float(v) for v in sorted_pair[y]],
                                   "fill": False, "tension": 0.25}]},
            "options": {"responsive": True, "maintainAspectRatio": False},
        })

    return jsonify({"error": "Tipo no implementado."}), 500
```

- [ ] **Step 4: Registrar el blueprint en `app.py`**

```python
    from routes.api_custom import api_custom_bp
    app.register_blueprint(api_custom_bp, url_prefix="/api")
```

- [ ] **Step 5: UI — botón + modal**

En `templates/dashboard.html`, dentro de `#tab-charts`, antes del `<div id="charts-grid">`:

```html
<div class="d-flex justify-content-end mb-2">
    <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#custom-chart-modal">
        <i class="bi bi-plus-circle me-1"></i> Nuevo gráfico
    </button>
</div>
```

Y al final del bloque content, el modal:

```html
<div class="modal fade" id="custom-chart-modal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Nuevo gráfico personalizado</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body row g-2">
                <div class="col-12">
                    <label class="form-label small">Tipo</label>
                    <select id="cc-type" class="form-select form-select-sm">
                        <option value="scatter">Scatter</option>
                        <option value="bar">Barras (promedio por X)</option>
                        <option value="line">Línea</option>
                    </select>
                </div>
                <div class="col-6">
                    <label class="form-label small">Eje X</label>
                    <select id="cc-x" class="form-select form-select-sm"></select>
                </div>
                <div class="col-6">
                    <label class="form-label small">Eje Y</label>
                    <select id="cc-y" class="form-select form-select-sm"></select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button class="btn btn-primary" id="cc-create-btn">Crear</button>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 6: `static/js/custom-chart.js`**

```javascript
// static/js/custom-chart.js
(function () {
    'use strict';
    const typeEl = document.getElementById('cc-type');
    const xEl = document.getElementById('cc-x');
    const yEl = document.getElementById('cc-y');
    const btn = document.getElementById('cc-create-btn');
    const modalEl = document.getElementById('custom-chart-modal');
    if (!typeEl || !xEl || !yEl || !btn || !modalEl) return;

    function populate() {
        const cls = (window.Dashboard && window.Dashboard.classification) || {};
        const cols = []
            .concat(cls.numeric || [])
            .concat(cls.categorical || [])
            .concat(cls.temporal || []);
        const opts = cols.map(c => '<option value="' + c + '">' + c + '</option>').join('');
        xEl.innerHTML = opts;
        yEl.innerHTML = opts;
    }
    populate();

    btn.addEventListener('click', async function () {
        btn.disabled = true;
        try {
            const res = await fetch('/api/chart/custom', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: typeEl.value, x: xEl.value, y: yEl.value }),
            });
            if (!res.ok) {
                const err = await res.json();
                alert(err.error || 'No se pudo crear el gráfico.');
                return;
            }
            const spec = await res.json();
            // Inyectamos el nuevo spec en el grid.
            const grid = document.getElementById('charts-grid');
            if (!grid || !window.Dashboard || !window.Dashboard.renderCharts) return;
            const current = Object.values(window.Dashboard.lastSpecs || {});
            window.Dashboard.renderCharts(current.concat([spec]));
            bootstrap.Modal.getInstance(modalEl).hide();
        } finally {
            btn.disabled = false;
        }
    });
})();
```

Inclúyelo en `dashboard.html` `{% block scripts %}`.

- [ ] **Step 7: Verificar**

```bash
pytest tests/test_custom_chart.py -v
python app.py
```

Click en "Nuevo gráfico", elegir tipo y columnas → aparece en la grid.

- [ ] **Step 8: Commit**

```bash
git add routes/api_custom.py app.py templates/dashboard.html static/js/custom-chart.js tests/test_custom_chart.py
git commit -m "feat: user-built custom charts via /api/chart/custom"
```

---

### Fase 5 — Cierre

```bash
git push -u origin fase-5-datos
gh pr create --title "Fase 5: ampliar capacidades de análisis" --body "$(cat <<'EOF'
## Summary
- Selector de hoja para archivos Excel multi-sheet.
- Override manual del tipo clasificado de cada columna.
- Detección IQR de outliers en el resumen numérico.
- Filtros combinables con AND/OR (toggle global).
- Constructor de gráficos personalizado (scatter / bar / line) desde la UI.

## Test plan
- [ ] pytest tests/ -v (todos verdes)
- [ ] Sube un Excel con 2 hojas → ver selector → elegir → dashboard correcto.
- [ ] Reclasificar columna "id" como categorical → gráficos se ajustan.
- [ ] Outliers visibles en la tabla numérica.
- [ ] Toggle OR funciona con filtros de varias columnas.
- [ ] Modal "Nuevo gráfico" inyecta un scatter custom.
EOF
)"
```

---

# FASE 6 — Calidad de código

**Objetivo:** introducir linter/formatter, medición de cobertura, tests de los módulos sin cobertura propia, lockfile reproducible, y refactor del routing.

**Estimación:** 1 día.

**Branch sugerida:** `fase-6-calidad`.

---

### Task 6.1: `pyproject.toml` + ruff + black

**Files:**
- Create: `pyproject.toml`
- Modify: `requirements.txt` (añadir bloque de dev)

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = ["venv", ".venv", "uploads"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = ["E501"]  # delegamos longitud a formatter

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401"]  # imports defensivos en tests

[tool.black]
line-length = 100
target-version = ["py311"]
exclude = "venv|.venv|uploads"
```

- [ ] **Step 2: Añadir dev deps a `requirements.txt`**

Al final del bloque "Solo para tests locales":

```
ruff>=0.5.0,<1.0.0
black>=24.0.0,<25.0.0
pytest-cov>=5.0.0,<6.0.0
```

- [ ] **Step 3: Instalar y ejecutar**

```bash
source venv/bin/activate
pip install -r requirements.txt
ruff check .
black --check .
```

- [ ] **Step 4: Aplicar formato y corregir warnings**

```bash
ruff check . --fix
black .
ruff check .
```

Esperado: sin errores. Si quedan, ajustar el código (no las reglas).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "chore: add ruff + black + pytest-cov dev tooling"
git add -u  # capturar cambios de formato
git commit -m "style: apply ruff/black to existing codebase"
```

---

### Task 6.2: Cobertura con `pytest-cov` ≥ 80%

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Config de coverage**

Añade a `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=core --cov=routes --cov-report=term-missing --cov-fail-under=80"
testpaths = ["tests"]
```

- [ ] **Step 2: Ejecutar y observar**

```bash
pytest
```

Si la cobertura está por debajo de 80%, el comando falla. Identifica los archivos con menos cobertura — serán target de tareas 6.3 y 6.4.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: enforce 80% test coverage via pytest-cov"
```

---

### Task 6.3: Tests para `core/chart_builder.py`

**Files:**
- Modify/Extend: `tests/test_chart_builder.py`

- [ ] **Step 1: Casos a cubrir**

Extiende `tests/test_chart_builder.py`:

```python
import pandas as pd
import pytest

from core.chart_builder import (
    MAX_CATEGORIES,
    MAX_CHARTS,
    MAX_HISTOGRAM_BINS,
    SCATTER_MAX_POINTS,
    build_charts,
)


class TestCategoricalDistribution:
    def test_pie_when_few_categories(self):
        df = pd.DataFrame({"c": ["a", "b", "c", "a"]})
        out = build_charts(df, {"numeric": [], "categorical": ["c"], "temporal": [], "other": []})
        assert out[0]["type"] == "pie"

    def test_bar_when_many_categories(self):
        df = pd.DataFrame({"c": [f"cat-{i}" for i in range(20)]})
        out = build_charts(df, {"numeric": [], "categorical": ["c"], "temporal": [], "other": []})
        assert out[0]["type"] == "bar"

    def test_groups_excess_categories_into_other(self):
        df = pd.DataFrame({"c": [f"cat-{i % 30}" for i in range(60)]})
        out = build_charts(df, {"numeric": [], "categorical": ["c"], "temporal": [], "other": []})
        labels = out[0]["data"]["labels"]
        assert "Otros" in labels
        assert len(labels) == MAX_CATEGORIES


class TestHistogram:
    def test_histogram_for_numeric(self):
        df = pd.DataFrame({"x": list(range(100))})
        out = build_charts(df, {"numeric": ["x"], "categorical": [], "temporal": [], "other": []})
        assert out[0]["type"] == "bar"
        assert len(out[0]["data"]["labels"]) <= MAX_HISTOGRAM_BINS

    def test_skip_constant_column(self):
        df = pd.DataFrame({"x": [5] * 20})
        out = build_charts(df, {"numeric": ["x"], "categorical": [], "temporal": [], "other": []})
        assert out == []


class TestTimeSeries:
    def test_time_series_generates_line(self):
        df = pd.DataFrame({
            "t": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "v": [1.0, 2.0, 3.0],
        })
        out = build_charts(df, {"numeric": ["v"], "categorical": [], "temporal": ["t"], "other": []})
        assert any(c["type"] == "line" for c in out)


class TestScatterAndCaps:
    def test_scatter_when_two_numerics(self):
        df = pd.DataFrame({"x": range(10), "y": range(10)})
        out = build_charts(df, {"numeric": ["x", "y"], "categorical": [], "temporal": [], "other": []})
        assert any(c["type"] == "scatter" for c in out)

    def test_max_charts_cap(self):
        cats = {f"c{i}": ["a", "b"] * 50 for i in range(20)}
        df = pd.DataFrame(cats)
        out = build_charts(df, {"numeric": [], "categorical": list(cats.keys()), "temporal": [], "other": []})
        assert len(out) <= MAX_CHARTS


class TestJSONSafety:
    def test_payload_is_json_serializable_without_allow_nan(self):
        import json
        df = pd.DataFrame({
            "x": [1.0, 2.0, float("nan"), 4.0],
            "cat": ["a", "b", "a", None],
        })
        out = build_charts(df, {"numeric": ["x"], "categorical": ["cat"], "temporal": [], "other": []})
        json.dumps(out, allow_nan=False)  # No debe lanzar.
```

- [ ] **Step 2: Ejecutar**

```bash
pytest tests/test_chart_builder.py -v
```

Esperado: verde.

- [ ] **Step 3: Commit**

```bash
git add tests/test_chart_builder.py
git commit -m "test: cover chart_builder edge cases and JSON safety"
```

---

### Task 6.4: Tests para `routes/main.py`

**Files:**
- Create: `tests/test_main_routes.py`

- [ ] **Step 1: Cubrir upload / dashboard / reset / downloads end-to-end**

```python
# tests/test_main_routes.py
"""Tests de integración para los endpoints en routes/main.py."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    with app.test_client() as c:
        yield c


class TestUpload:
    CSV = b"col1,col2\nx,1\ny,2\nz,3\n"

    def test_happy_path_redirects_to_dashboard(self, client):
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(self.CSV), "data.csv")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "/dashboard" in resp.location

    def test_no_file_flashes_and_redirects(self, client):
        resp = client.post("/upload", data={}, follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_corrupted_excel_returns_to_index(self, client):
        garbage = b"not actually an xlsx"
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(garbage), "broken.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/")

    def test_upload_deletes_temp_file(self, client, tmp_path):
        client.post(
            "/upload",
            data={"file": (io.BytesIO(self.CSV), "data.csv")},
            content_type="multipart/form-data",
        )
        residuals = list(Path(tmp_path / "uploads").glob("__tmp_*"))
        assert residuals == []


class TestDashboard:
    def test_dashboard_redirects_when_no_dataset(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestReset:
    def test_reset_clears_session(self, client):
        with client.session_transaction() as sess:
            sess["dataset_token"] = "abc"
        resp = client.post("/reset", follow_redirects=False)
        assert resp.status_code in (302, 303)
        with client.session_transaction() as sess:
            assert "dataset_token" not in sess
```

- [ ] **Step 2: Ejecutar**

```bash
pytest tests/test_main_routes.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_main_routes.py
git commit -m "test: integration coverage for upload, dashboard, reset endpoints"
```

---

### Task 6.5: Lockfile reproducible con `pip-compile`

**Files:**
- Create: `requirements.in`
- Modify: `requirements.txt` (regenerado)
- Modify: `README.md` (instrucciones)

- [ ] **Step 1: Crear `requirements.in`** con los rangos actuales

```
Flask>=3.0.0,<4.0.0
Werkzeug>=3.0.0,<4.0.0
pandas>=2.1.0,<3.0.0
numpy>=1.24.0,<3.0.0
python-dateutil>=2.8.2
openpyxl>=3.1.0,<4.0.0
Flask-Caching>=2.1.0,<3.0.0

# Dev
pytest>=8.0.0,<9.0.0
pytest-cov>=5.0.0,<6.0.0
ruff>=0.5.0,<1.0.0
black>=24.0.0,<25.0.0
```

- [ ] **Step 2: Generar `requirements.txt` pinneado**

```bash
pip install pip-tools
pip-compile requirements.in -o requirements.txt
```

- [ ] **Step 3: Documentar en README**

Añade una sección "Reproducibilidad":

```markdown
### Bloqueo de versiones

`requirements.txt` es generado a partir de `requirements.in` con `pip-compile` (pip-tools).
Para actualizar las versiones pinneadas:

\`\`\`bash
pip install pip-tools
pip-compile requirements.in -o requirements.txt
\`\`\`
```

- [ ] **Step 4: Verificar instalación limpia**

```bash
deactivate || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add requirements.in requirements.txt README.md
git commit -m "build: pin transitive deps via pip-compile lockfile"
```

---

### Task 6.6: Refactor — partir `routes/main.py` en módulos

**Files:**
- Create: `routes/_helpers.py`
- Create: `routes/uploads.py`
- Create: `routes/downloads.py`
- Create: `routes/dashboard.py`
- Delete: `routes/main.py`
- Modify: `app.py` (registrar nuevos blueprints)

- [ ] **Step 1: Extraer helpers comunes**

`routes/_helpers.py`:

```python
# routes/_helpers.py
"""Helpers compartidos por los blueprints de cara al usuario."""
from __future__ import annotations

from typing import Any, Dict

from flask import abort, current_app, session
from werkzeug.utils import secure_filename

from core.cache import dataset_cache


def active_payload_or_404() -> Dict[str, Any]:
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="El dataset ha expirado.")
    return payload


def processed_stem(original: str) -> str:
    base = secure_filename(original or "dataset") or "dataset"
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return f"{stem}_cleaned"


def clear_derived_cache() -> None:
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE")
    if flask_cache is None:
        return
    try:
        flask_cache.clear()
    except Exception:
        current_app.logger.warning("No se pudo limpiar Flask-Caching.")
```

- [ ] **Step 2: Crear `routes/uploads.py`**

Mueve aquí los endpoints `/upload`, `/reset`, y los helpers `_persist_dataset` (extracción del cuerpo común del upload):

```python
# routes/uploads.py
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from core.cache import dataset_cache
from core.chart_builder import build_charts
from core.column_classifier import classify
from core.correlation import correlation_matrix
from core.data_cleaner import clean
from core.data_loader import CSVLoadError, load_dataset, optimize_dtypes
from core.filter_engine import available_filters
from core.stats import dataset_overview, numeric_summary
from routes._helpers import clear_derived_cache

uploads_bp = Blueprint("uploads", __name__)
logger = logging.getLogger(__name__)


def _persist_dataset(df, classification, filename: str) -> str:
    overview = dataset_overview(df, classification)
    stats = numeric_summary(df, classification["numeric"])
    charts = build_charts(df, classification)
    filter_options = available_filters(df, classification)
    correlation = correlation_matrix(df, classification["numeric"])

    previous_token = session.get("dataset_token")
    if previous_token:
        dataset_cache.discard(previous_token)
    clear_derived_cache()

    token = dataset_cache.put({
        "df": df, "classification": classification,
        "overview": overview, "stats": stats,
        "charts": charts, "filter_options": filter_options,
        "correlation": correlation, "filename": filename,
    })
    session["dataset_token"] = token
    return token


@uploads_bp.post("/upload")
def upload():
    # ... (mover aquí el cuerpo actual de routes.main.upload, ajustando llamadas)
```

- [ ] **Step 3: Crear `routes/downloads.py`** con `/download/csv` y `/download/json`

Mueve el contenido equivalente de `routes/main.py:166-223`, importando `active_payload_or_404` y `processed_stem` de `_helpers`.

- [ ] **Step 4: Crear `routes/dashboard.py`** con `/` y `/dashboard`

Mueve los dos endpoints, usando `active_payload_or_404`.

- [ ] **Step 5: Borrar `routes/main.py`**

```bash
git rm routes/main.py
```

- [ ] **Step 6: Actualizar `app.py`**

```python
    from routes.api import api_bp
    from routes.api_custom import api_custom_bp
    from routes.dashboard import dashboard_bp
    from routes.downloads import downloads_bp
    from routes.uploads import uploads_bp

    app.register_blueprint(uploads_bp)
    app.register_blueprint(downloads_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(api_custom_bp, url_prefix="/api")
```

- [ ] **Step 7: Actualizar `url_for(...)`** en templates

`templates/dashboard.html`:
- `main.reset` → `uploads.reset`
- `main.download_csv` → `downloads.download_csv`
- `main.download_json` → `downloads.download_json`
- `main.index` → `dashboard.index`

`templates/index.html`:
- `main.upload` → `uploads.upload`

Y cualquier otro `url_for` que use el blueprint `main`.

- [ ] **Step 8: Ajustar tests**

`tests/test_main_routes.py` referencia rutas (`/upload`, `/dashboard`, `/reset`) que siguen siendo las mismas, así que no debería romper. Pero el `app.errorhandler` y los `redirect(url_for("main.*"))` sí — barre todo el repo con `grep -rn 'main\.' routes/ tests/` y ajusta.

- [ ] **Step 9: Verificar suite + manual**

```bash
pytest tests/ -v
python app.py
```

Navega por toda la app (upload → dashboard → downloads → reset).

- [ ] **Step 10: Commit**

```bash
git add routes/ app.py templates/ tests/
git commit -m "refactor: split routes/main.py into uploads/downloads/dashboard blueprints"
```

---

### Fase 6 — Cierre

```bash
git push -u origin fase-6-calidad
gh pr create --title "Fase 6: calidad de código y lockfile" --body "$(cat <<'EOF'
## Summary
- ruff + black como linters; pyproject.toml configurado.
- pytest-cov con umbral 80%.
- Tests para chart_builder y routes (uploads, dashboard, reset, downloads).
- requirements.txt regenerado con pip-compile a partir de requirements.in.
- routes/main.py partido en 3 blueprints + helpers compartidos.

## Test plan
- [ ] ruff check . (sin errores)
- [ ] black --check . (formato consistente)
- [ ] pytest (cobertura >= 80%)
- [ ] Re-instalación limpia desde requirements.txt
- [ ] Navegación end-to-end manual.
EOF
)"
```

---

# FASE 7 — Performance y escalabilidad (opcional)

**Objetivo:** opciones de configuración para deploy multi-worker, sniff de tipos en muestra para CSV grandes y soporte opcional de pyarrow.

**Estimación:** 1 día.

**Branch sugerida:** `fase-7-performance`.

---

### Task 7.1: Sniff de tipos en muestra para CSV grandes

**Files:**
- Modify: `core/data_loader.py:66-98`
- Test: `tests/test_data_loader.py` (existente) o nuevo `tests/test_load_csv_typed.py`

- [ ] **Step 1: Test con CSV grande sintético**

```python
# tests/test_load_csv_typed.py
from __future__ import annotations

import pandas as pd

from core.data_loader import load_csv


def test_large_csv_uses_sample_for_dtype_inference(tmp_path):
    rows = 50_000
    p = tmp_path / "big.csv"
    df = pd.DataFrame({"a": range(rows), "b": [f"row-{i}" for i in range(rows)]})
    df.to_csv(p, index=False)
    out = load_csv(p)
    assert len(out) == rows
    assert out["a"].dtype.kind in ("i", "u")  # entero, no object
```

- [ ] **Step 2: Modificar `load_csv` para usar `nrows` en sniff**

Reemplaza la lógica de `pd.read_csv`:

```python
    # Lectura en dos pasos: una muestra para inferir dtypes, luego lectura completa
    # con esos dtypes para evitar el coste de re-inferir en 50 MB.
    try:
        sample_df = pd.read_csv(
            path, sep=delimiter, encoding=encoding, engine="c",
            nrows=5000, low_memory=False, skip_blank_lines=True, on_bad_lines="skip",
        )
        dtype_map = {c: sample_df[c].dtype for c in sample_df.columns}
        df = pd.read_csv(
            path, sep=delimiter, encoding=encoding, engine="c",
            dtype=dtype_map, low_memory=False, skip_blank_lines=True, on_bad_lines="skip",
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        # Fallback al modo simple si la pre-inferencia rompió.
        try:
            df = pd.read_csv(
                path, sep=delimiter, encoding=encoding, engine="c",
                low_memory=False, skip_blank_lines=True, on_bad_lines="skip",
            )
        except pd.errors.EmptyDataError as e2:
            raise CSVLoadError("El archivo no contiene columnas analizables.") from e2
        except pd.errors.ParserError as e2:
            raise CSVLoadError(f"Error de parseo del CSV: {e2}") from e2
        except UnicodeDecodeError as e2:
            raise CSVLoadError("Error de codificación al leer el archivo.") from e2
```

- [ ] **Step 3: Ejecutar tests**

```bash
pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add core/data_loader.py tests/test_load_csv_typed.py
git commit -m "perf: infer dtypes from 5k-row sample before full CSV read"
```

---

### Task 7.2: `CACHE_TYPE` configurable por env

**Files:**
- Modify: `config.py`
- Modify: `README.md` (documentar)

- [ ] **Step 1: Permitir override desde env**

Edita `config.py`:

```python
    FLASK_CACHE_CONFIG = {
        "CACHE_TYPE": os.environ.get("DATADASH_CACHE_TYPE", "SimpleCache"),
        "CACHE_DEFAULT_TIMEOUT": 3600,
        "CACHE_THRESHOLD": 500,
        "CACHE_DIR": os.environ.get("DATADASH_CACHE_DIR", str(BASE_DIR / "cache")),
    }
```

- [ ] **Step 2: README — sección "Deploy multi-worker"**

```markdown
### Deploy en producción con varios workers

`SimpleCache` (default) es process-local. Si despliegas con `gunicorn -w N`, cada
worker tiene su propio dataset cacheado. Para sortear esto sin DB, usa
`FileSystemCache` exportando:

\`\`\`bash
export DATADASH_CACHE_TYPE=FileSystemCache
export DATADASH_CACHE_DIR=/var/lib/datadash/cache
\`\`\`

El `DatasetCache` interno sigue siendo process-local — para un setup verdaderamente
multi-worker hay que reescribirlo como wrapper de Flask-Caching, fuera del alcance
de esta fase.
```

- [ ] **Step 3: Verificar arranque con `FileSystemCache`**

```bash
DATADASH_CACHE_TYPE=FileSystemCache DATADASH_CACHE_DIR=/tmp/dd_cache python app.py
```

Comprobar que arranca y `/tmp/dd_cache` se crea.

- [ ] **Step 4: Commit**

```bash
git add config.py README.md
git commit -m "feat: allow FileSystemCache backend via DATADASH_CACHE_TYPE env"
```

---

### Task 7.3: pyarrow opcional para CSV/JSON de salida

**Files:**
- Modify: `requirements.in`
- Modify: `routes/downloads.py` (creado en Fase 6) o `routes/main.py` (si Fase 6 no se ejecutó)

- [ ] **Step 1: Añadir pyarrow como dep opcional con marker**

En `requirements.in`:

```
pyarrow>=14.0.0,<20.0.0 ; python_version >= "3.10"
```

Regenerar lockfile:

```bash
pip-compile requirements.in -o requirements.txt
```

- [ ] **Step 2: Usar pyarrow en `download_csv` si disponible**

En `routes/downloads.py`, dentro de `download_csv`:

```python
    try:
        import pyarrow  # noqa
        # to_csv ya usa C, pero pyarrow puede acelerar to_string serializations.
        # Para datasets pequeños la diferencia es mínima; documentamos como toggle.
        df.to_csv(buf, index=False, encoding="utf-8")
    except ImportError:
        df.to_csv(buf, index=False, encoding="utf-8")
```

(Mantenemos el código equivalente — la mejora real viene cuando se usa `engine="pyarrow"` en operaciones aguas arriba. Esta tarea es honesto: el speedup principal viene del sniff de la 7.1.)

- [ ] **Step 3: Commit**

```bash
git add requirements.in requirements.txt routes/downloads.py
git commit -m "build: pin pyarrow as optional dep for future fast paths"
```

---

### Fase 7 — Cierre

```bash
git push -u origin fase-7-performance
gh pr create --title "Fase 7: opciones de performance y escalabilidad" --body "$(cat <<'EOF'
## Summary
- CSV: inferencia de tipos sobre muestra de 5k filas antes de la lectura completa.
- Flask-Caching backend configurable (SimpleCache | FileSystemCache) por env.
- pyarrow pinneado como dep opcional.

## Test plan
- [ ] pytest tests/ -v
- [ ] Cargar CSV de ~50 MB: tiempo de upload < a la versión anterior.
- [ ] DATADASH_CACHE_TYPE=FileSystemCache python app.py → arranca, crea cache dir.
EOF
)"
```

---

## Notas finales

- **Orden recomendado de ejecución:** 3 → 4 → 6 → 5 → 7. Razón: 6 introduce herramientas que mejoran 5 (linter, refactor); 7 es opcional y dependiente del uso real.
- **Cada fase es un PR independiente.** El plan está pensado para revisión por etapas.
- **No introducir Docker, CI/CD ni dependencias de terceros más allá de las listadas.** Respeta los invariantes del proyecto (no DB, vectorizado, uploads efímeros, UI español).
- **El idioma de los commits y comentarios mezcla español (para mensajes y docstrings de dominio) e inglés (para mensajes de commit convencionales).** Es el patrón actual del repo — mantenlo.
