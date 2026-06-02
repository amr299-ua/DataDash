# tests/test_chart_builder.py
"""Tests para la generación de specs Chart.js a partir del DataFrame clasificado."""

from __future__ import annotations

import json

import pandas as pd

from core.chart_builder import (
    MAX_CATEGORIES,
    MAX_CHARTS,
    MAX_HISTOGRAM_BINS,
    build_charts,
)


def _cls(numeric=None, categorical=None, temporal=None, other=None):
    return {
        "numeric": numeric or [],
        "categorical": categorical or [],
        "temporal": temporal or [],
        "other": other or [],
    }


class TestCategoricalDistribution:
    def test_pie_when_few_categories(self):
        df = pd.DataFrame({"c": ["a", "b", "c", "a"]})
        out = build_charts(df, _cls(categorical=["c"]))
        assert len(out) == 1
        assert out[0]["type"] == "pie"
        assert "Distribución" in out[0]["title"]

    def test_bar_when_many_categories(self):
        df = pd.DataFrame({"c": [f"cat-{i}" for i in range(20)]})
        out = build_charts(df, _cls(categorical=["c"]))
        # >6 → bar.
        assert out[0]["type"] == "bar"

    def test_groups_excess_categories_into_other(self):
        df = pd.DataFrame({"c": [f"cat-{i % 30}" for i in range(60)]})
        out = build_charts(df, _cls(categorical=["c"]))
        labels = out[0]["data"]["labels"]
        assert "Otros" in labels
        assert len(labels) == MAX_CATEGORIES

    def test_skip_all_null_column(self):
        df = pd.DataFrame({"c": [None, None, None]})
        out = build_charts(df, _cls(categorical=["c"]))
        assert out == []


class TestHistogram:
    def test_histogram_for_numeric_column(self):
        df = pd.DataFrame({"x": list(range(100))})
        out = build_charts(df, _cls(numeric=["x"]))
        assert out[0]["type"] == "bar"
        assert "Histograma" in out[0]["title"]
        assert len(out[0]["data"]["labels"]) <= MAX_HISTOGRAM_BINS

    def test_skip_constant_column(self):
        df = pd.DataFrame({"x": [5] * 20})
        out = build_charts(df, _cls(numeric=["x"]))
        assert out == []

    def test_skip_empty_numeric(self):
        df = pd.DataFrame({"x": pd.Series([], dtype=float)})
        out = build_charts(df, _cls(numeric=["x"]))
        assert out == []


class TestTimeSeries:
    def test_generates_line_for_temporal_numeric_pair(self):
        df = pd.DataFrame(
            {
                "t": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "v": [1.0, 2.0, 3.0],
            }
        )
        out = build_charts(df, _cls(numeric=["v"], temporal=["t"]))
        assert any(c["type"] == "line" for c in out)

    def test_skip_when_no_numeric_columns(self):
        df = pd.DataFrame({"t": pd.to_datetime(["2024-01-01", "2024-01-02"])})
        out = build_charts(df, _cls(temporal=["t"]))
        assert out == []


class TestScatterAndCaps:
    def test_scatter_when_two_numerics(self):
        df = pd.DataFrame({"x": range(10), "y": range(10)})
        out = build_charts(df, _cls(numeric=["x", "y"]))
        # debe incluir scatter al final.
        types = [c["type"] for c in out]
        assert "scatter" in types

    def test_no_scatter_with_only_one_numeric(self):
        df = pd.DataFrame({"x": range(10)})
        out = build_charts(df, _cls(numeric=["x"]))
        types = [c["type"] for c in out]
        assert "scatter" not in types

    def test_max_charts_cap_respected(self):
        cats = {f"c{i}": ["a", "b"] * 50 for i in range(20)}
        df = pd.DataFrame(cats)
        out = build_charts(df, _cls(categorical=list(cats.keys())))
        assert len(out) <= MAX_CHARTS


class TestJSONSafety:
    def test_payload_is_json_serializable_without_allow_nan(self):
        df = pd.DataFrame(
            {
                "x": [1.0, 2.0, float("nan"), 4.0],
                "cat": ["a", "b", "a", None],
            }
        )
        out = build_charts(df, _cls(numeric=["x"], categorical=["cat"]))
        # Si hubiera NaN/Inf el dump fallaría.
        json.dumps(out, allow_nan=False)

    def test_scatter_payload_has_x_and_y_dicts(self):
        df = pd.DataFrame({"x": range(5), "y": [2, 4, 6, 8, 10]})
        out = build_charts(df, _cls(numeric=["x", "y"]))
        scatter = next(c for c in out if c["type"] == "scatter")
        first_point = scatter["data"]["datasets"][0]["data"][0]
        assert "x" in first_point and "y" in first_point


class TestSlug:
    def test_chart_ids_are_slug_safe(self):
        df = pd.DataFrame({"con espacios": ["a", "b", "a"]})
        out = build_charts(df, _cls(categorical=["con espacios"]))
        # No debe haber espacios en el id.
        assert " " not in out[0]["id"]
        assert out[0]["id"].startswith("cat-")
