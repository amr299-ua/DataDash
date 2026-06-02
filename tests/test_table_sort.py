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
        assert xs[0] == 1.0
        assert xs[1] == 3.0
        assert xs[2] is None
