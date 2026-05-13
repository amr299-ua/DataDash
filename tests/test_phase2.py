# tests/test_phase2.py
"""Tests unitarios para las funcionalidades de la Fase 2:

    - core.correlation.correlation_matrix → matriz Pearson sanitizada
    - rutas /download/csv y /download/json → contenido y headers correctos

Todos los tests son locales y no requieren red ni Docker.
"""
from __future__ import annotations

import io
import json
from typing import Tuple
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from core.correlation import MAX_CORRELATION_COLS, correlation_matrix


# ----------------------- correlation -----------------------

class TestCorrelationMatrix:
    def test_returns_unavailable_when_fewer_than_two_numeric_cols(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        result = correlation_matrix(df, ["x"])
        assert result["available"] is False
        assert result["columns"] == []
        assert result["matrix"] == []

    def test_returns_unavailable_when_no_numeric_cols(self):
        df = pd.DataFrame({"label": ["a", "b", "c"]})
        result = correlation_matrix(df, [])
        assert result["available"] is False

    def test_perfect_positive_correlation(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
        result = correlation_matrix(df, ["x", "y"])
        assert result["available"] is True
        assert result["columns"] == ["x", "y"]
        # Diagonal = 1; off-diagonal = 1 (correlación perfecta).
        assert result["matrix"][0][0] == 1.0
        assert result["matrix"][1][1] == 1.0
        assert result["matrix"][0][1] == 1.0
        assert result["matrix"][1][0] == 1.0

    def test_perfect_negative_correlation(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [4.0, 3.0, 2.0, 1.0]})
        result = correlation_matrix(df, ["x", "y"])
        assert result["matrix"][0][1] == -1.0
        assert result["matrix"][1][0] == -1.0

    def test_uncorrelated_independent_columns(self):
        rng = np.random.default_rng(seed=42)
        df = pd.DataFrame({"x": rng.normal(size=500), "y": rng.normal(size=500)})
        result = correlation_matrix(df, ["x", "y"])
        # Para muestras independientes grandes, |corr| debe ser pequeña.
        assert abs(result["matrix"][0][1]) < 0.2

    def test_zero_variance_column_yields_none(self):
        # Una columna constante tiene varianza 0 → correlación indefinida → NaN → None.
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "k": [5.0, 5.0, 5.0]})
        result = correlation_matrix(df, ["x", "k"])
        # Diagonal de la constante también es NaN (pandas: corr de constante con sí misma es NaN).
        assert result["matrix"][0][1] is None
        assert result["matrix"][1][0] is None

    def test_nan_values_are_sanitized(self):
        df = pd.DataFrame({
            "x": [1.0, 2.0, 3.0, 4.0, np.nan],
            "y": [2.0, 4.0, 6.0, np.nan, 10.0],
        })
        result = correlation_matrix(df, ["x", "y"])
        # No debe haber NaN ni Inf en el JSON resultante.
        for row in result["matrix"]:
            for val in row:
                if val is not None:
                    assert not np.isnan(val)
                    assert not np.isinf(val)

    def test_truncates_when_too_many_columns(self):
        cols = [f"c{i}" for i in range(MAX_CORRELATION_COLS + 5)]
        data = {c: np.arange(10) for c in cols}
        df = pd.DataFrame(data)
        result = correlation_matrix(df, cols)
        assert result["available"] is True
        assert result["truncated"] is True
        assert len(result["columns"]) == MAX_CORRELATION_COLS
        assert result["total_numeric"] == MAX_CORRELATION_COLS + 5

    def test_diagonal_is_one_for_well_defined_columns(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0], "b": [5.0, 4.0, 3.0, 2.0, 1.0]})
        result = correlation_matrix(df, ["a", "b"])
        assert result["matrix"][0][0] == 1.0
        assert result["matrix"][1][1] == 1.0

    def test_values_clamped_to_unit_interval(self):
        # Comprueba que los valores siempre quedan en [-1, 1] tras sanitización.
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})
        result = correlation_matrix(df, ["x", "y"])
        for row in result["matrix"]:
            for v in row:
                if v is not None:
                    assert -1.0 <= v <= 1.0

    def test_unknown_columns_in_classification_are_ignored(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]})
        # "z" no existe — debe ignorarse sin error.
        result = correlation_matrix(df, ["x", "y", "z"])
        assert result["available"] is True
        assert result["columns"] == ["x", "y"]


# ----------------------- Flask end-to-end (download) -----------------------

@pytest.fixture
def app_client() -> Tuple[object, object]:
    """Crea una app Flask aislada con un dataset preinyectado en sesión."""
    from app import cache as flask_cache, create_app
    from core.cache import dataset_cache

    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    # Limpia caches por si otro test los dejó sucios.
    flask_cache.clear()

    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "precio": [10.5, 20.0, 30.5, np.nan, 21.0],
        "categoria": ["A", "B", "A", "C", "B"],
        "fecha": pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        ),
    })
    classification = {
        "numeric": ["id", "precio"],
        "categorical": ["categoria"],
        "temporal": ["fecha"],
        "other": [],
    }
    payload = {
        "df": df,
        "classification": classification,
        "overview": {"rows": 5, "columns": 4, "numeric_count": 2,
                     "categorical_count": 1, "temporal_count": 1, "other_count": 0,
                     "total_nulls": 1, "memory_mb": 0.001},
        "stats": [],
        "charts": [],
        "filter_options": {"categorical": [], "numeric": [], "temporal": []},
        "correlation": correlation_matrix(df, classification["numeric"]),
        "filename": "test_dataset.csv",
    }
    token = dataset_cache.put(payload)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["dataset_token"] = token
    yield app, client
    dataset_cache.discard(token)
    flask_cache.clear()


class TestDownloadEndpoints:
    def test_csv_download_returns_text_csv(self, app_client):
        _, client = app_client
        resp = client.get("/download/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["Content-Type"]
        assert "test_dataset_cleaned.csv" in resp.headers["Content-Disposition"]
        body = resp.get_data(as_text=True)
        # El primer carácter es BOM (﻿) para Excel; lo descartamos al parsear.
        body_clean = body.lstrip("﻿")
        first_line = body_clean.splitlines()[0]
        for col in ("id", "precio", "categoria", "fecha"):
            assert col in first_line

    def test_csv_round_trip_preserves_row_count(self, app_client):
        _, client = app_client
        resp = client.get("/download/csv")
        body = resp.get_data(as_text=True).lstrip("﻿")
        df_round = pd.read_csv(io.StringIO(body))
        assert len(df_round) == 5
        # Las nulas siguen siendo nulas tras el round-trip.
        assert df_round["precio"].isna().sum() == 1

    def test_json_download_structure(self, app_client):
        _, client = app_client
        resp = client.get("/download/json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["Content-Type"]
        assert "test_dataset_cleaned.json" in resp.headers["Content-Disposition"]
        body = json.loads(resp.get_data(as_text=True))
        assert "meta" in body and "data" in body
        assert body["meta"]["rows"] == 5
        assert body["meta"]["filename"] == "test_dataset.csv"
        assert len(body["data"]) == 5
        # La clasificación se incluye para que el consumidor sepa los tipos.
        assert body["meta"]["classification"]["numeric"] == ["id", "precio"]

    def test_download_404_without_active_dataset(self):
        from app import create_app
        app = create_app()
        client = app.test_client()
        resp = client.get("/download/csv")
        # No hay token en sesión → main_bp aborta con 404.
        assert resp.status_code == 404

    def test_correlation_endpoint(self, app_client):
        _, client = app_client
        resp = client.get("/api/correlation")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True
        assert set(data["columns"]) == {"id", "precio"}


class TestFlaskCaching:
    def test_filter_response_is_memoized(self, app_client):
        """Segunda llamada con mismos filtros debe golpear la caché Flask-Caching."""
        from app import cache as flask_cache

        app, client = app_client
        flask_cache.clear()

        # Espiamos build_charts: si la caché funciona, debe llamarse 1 sola vez.
        with patch("routes.api.build_charts", wraps=__import__("core.chart_builder", fromlist=["build_charts"]).build_charts) as spy:
            filters_body = {"filters": {}, "page": 1, "page_size": 25}
            r1 = client.post(
                "/api/filter",
                data=json.dumps(filters_body),
                content_type="application/json",
            )
            r2 = client.post(
                "/api/filter",
                data=json.dumps(filters_body),
                content_type="application/json",
            )
            assert r1.status_code == 200
            assert r2.status_code == 200
            # Mismo payload → caché golpeada en la segunda llamada.
            assert spy.call_count == 1, f"build_charts se llamó {spy.call_count} veces (esperado 1)"

    def test_different_filters_bypass_cache(self, app_client):
        """Filtros distintos producen claves distintas → recomputo."""
        from app import cache as flask_cache

        app, client = app_client
        flask_cache.clear()

        with patch("routes.api.build_charts", wraps=__import__("core.chart_builder", fromlist=["build_charts"]).build_charts) as spy:
            r1 = client.post(
                "/api/filter",
                data=json.dumps({"filters": {}, "page": 1, "page_size": 25}),
                content_type="application/json",
            )
            r2 = client.post(
                "/api/filter",
                data=json.dumps({
                    "filters": {"categorical": {"categoria": ["A"]}},
                    "page": 1, "page_size": 25,
                }),
                content_type="application/json",
            )
            assert r1.status_code == 200 and r2.status_code == 200
            assert spy.call_count == 2

    def test_cache_cleared_on_reset(self, app_client):
        from app import cache as flask_cache

        app, client = app_client

        # Pre-popular caché.
        client.post(
            "/api/filter",
            data=json.dumps({"filters": {}, "page": 1, "page_size": 25}),
            content_type="application/json",
        )
        # Ahora reset.
        resp = client.post("/reset")
        assert resp.status_code in (302, 303)
        # Después del reset, no debería haber entradas en SimpleCache.
        store = getattr(flask_cache.cache, "_cache", None)
        if store is not None:
            assert len(store) == 0
