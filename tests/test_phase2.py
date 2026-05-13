# tests/test_phase2.py
"""Tests unitarios para las funcionalidades de la Fase 2:

    - core.correlation.correlation_matrix → matriz Pearson sanitizada

Todos los tests son locales y no requieren red ni Docker.
"""
from __future__ import annotations

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
