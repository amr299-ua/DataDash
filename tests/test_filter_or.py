# tests/test_filter_or.py
"""Combinador AND (default) vs OR entre múltiples filtros."""

from __future__ import annotations

import pandas as pd

from core.filter_engine import apply_filters


class TestFilterCombinator:
    def test_or_combines_two_categorical_columns(self):
        df = pd.DataFrame(
            {
                "color": ["red", "blue", "green", "red"],
                "size": ["S", "M", "L", "XL"],
            }
        )
        filters = {
            "categorical": {"color": ["red"], "size": ["M"]},
            "combinator": "OR",
        }
        out = apply_filters(df, filters)
        # OR: rojos OR tamaño M → filas 0, 1, 3.
        assert len(out) == 3
        assert set(out["color"]) == {"red", "blue"}

    def test_and_is_default(self):
        df = pd.DataFrame(
            {
                "color": ["red", "blue", "red"],
                "size": ["S", "M", "L"],
            }
        )
        filters = {"categorical": {"color": ["red"], "size": ["S"]}}
        out = apply_filters(df, filters)
        assert len(out) == 1
        assert out.iloc[0]["color"] == "red"
        assert out.iloc[0]["size"] == "S"

    def test_or_with_numeric_and_categorical(self):
        df = pd.DataFrame({"price": [1, 100, 50, 200], "tag": ["a", "b", "a", "c"]})
        filters = {
            "numeric": {"price": {"min": 90, "max": None}},
            "categorical": {"tag": ["a"]},
            "combinator": "OR",
        }
        out = apply_filters(df, filters)
        # OR: price >= 90 OR tag == a → filas 0 (a), 1 (b, 100), 2 (a), 3 (c, 200).
        assert len(out) == 4

    def test_invalid_combinator_falls_back_to_and(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        filters = {
            "numeric": {"x": {"min": 2, "max": 2}},
            "combinator": "XOR",  # inválido
        }
        out = apply_filters(df, filters)
        assert len(out) == 1
        assert out.iloc[0]["x"] == 2

    def test_no_filters_returns_full_df(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        out = apply_filters(df, {"combinator": "OR"})
        assert len(out) == 3
