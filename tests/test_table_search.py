# tests/test_table_search.py
"""Búsqueda libre en la tabla paginada."""
from __future__ import annotations

import pandas as pd

from core.table_builder import page


class TestPageSearch:
    def test_search_matches_substring_case_insensitive(self):
        df = pd.DataFrame({"nombre": ["Ana", "Susana", "Beatriz"], "x": [1, 2, 3]})
        result = page(df, page_number=1, page_size=10, search="ANA")
        names = [row[0] for row in result["rows"]]
        # "Ana" y "Susana" contienen "ana" en minúsculas; "Beatriz" no.
        assert "Ana" in names
        assert "Susana" in names
        assert "Beatriz" not in names

    def test_search_returns_all_rows_when_empty(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = page(df, page_number=1, page_size=10, search="")
        assert result["total_rows"] == 3

    def test_search_returns_all_rows_when_none(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = page(df, page_number=1, page_size=10, search=None)
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
