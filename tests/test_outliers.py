# tests/test_outliers.py
"""Detección IQR de outliers."""

from __future__ import annotations

import pandas as pd

from core.outliers import iqr_outlier_count


class TestIQROutliers:
    def test_no_outliers_in_uniform_distribution(self):
        s = pd.Series(range(1, 101))
        assert iqr_outlier_count(s) == 0

    def test_detects_extreme_high_value(self):
        s = pd.Series([1, 2, 3, 4, 5, 100])
        assert iqr_outlier_count(s) == 1

    def test_detects_extreme_low_value(self):
        s = pd.Series([-100, 10, 11, 12, 13, 14, 15])
        assert iqr_outlier_count(s) == 1

    def test_ignores_nan(self):
        s = pd.Series([1, 2, 3, None, 1000])
        assert iqr_outlier_count(s) == 1

    def test_empty_series_returns_zero(self):
        assert iqr_outlier_count(pd.Series([], dtype=float)) == 0

    def test_constant_series_returns_zero(self):
        assert iqr_outlier_count(pd.Series([5, 5, 5, 5])) == 0

    def test_string_series_returns_zero(self):
        # Series de objetos no numéricos → coerción a NaN → 0.
        assert iqr_outlier_count(pd.Series(["a", "b", "c"])) == 0

    def test_custom_k_factor(self):
        s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20])
        # Con k=3.0 el umbral es más permisivo; 20 podría no ser outlier.
        with_k15 = iqr_outlier_count(s, k=1.5)
        with_k3 = iqr_outlier_count(s, k=3.0)
        assert with_k15 >= with_k3
