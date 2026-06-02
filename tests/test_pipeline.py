# tests/test_pipeline.py
"""Tests unitarios del pipeline de datos.

Se enfocan en la lógica pura de pandas/Python:
    - data_cleaner.clean    → manejo de nulos y limpieza
    - column_classifier.classify → tipos de columna correctos
    - stats.numeric_summary → exactitud de media/mediana/std/min/max/nulos
    - stats.dataset_overview → conteos y memoria
    - data_loader.load_csv  → encoding/delimitador
    - data_loader.load_excel → lectura de .xlsx (openpyxl)
    - data_loader.load_dataset → dispatch agnóstico al formato
    - filter_engine.apply_filters / available_filters → filtrado vectorizado

Estos tests están pensados para correrse localmente con `pytest`. No requieren
ni servidor Flask ni infra externa.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.column_classifier import classify
from core.data_cleaner import clean
from core.data_loader import (
    CSVLoadError,
    load_csv,
    load_dataset,
    load_excel,
    optimize_dtypes,
)
from core.filter_engine import apply_filters, available_filters
from core.stats import dataset_overview, numeric_summary

# ----------------------- data_cleaner.clean -----------------------


class TestDataCleaner:
    def test_replaces_null_tokens_with_nan(self):
        df = pd.DataFrame({"a": ["x", "NULL", "N/A", "-", "ok"], "b": [1, 2, 3, 4, 5]})
        out = clean(df)
        # 3 valores en "a" deben quedar NaN; "x" y "ok" permanecen.
        assert out["a"].isna().sum() == 3
        assert set(out["a"].dropna()) == {"x", "ok"}

    def test_strips_whitespace_in_object_columns(self):
        df = pd.DataFrame({"a": ["  hola  ", "  mundo", "ok  "]})
        out = clean(df)
        assert list(out["a"]) == ["hola", "mundo", "ok"]

    def test_strips_column_names(self):
        df = pd.DataFrame({"  col1  ": [1, 2], " col2": [3, 4]})
        out = clean(df)
        assert list(out.columns) == ["col1", "col2"]

    def test_drops_fully_empty_columns_and_rows(self):
        df = pd.DataFrame(
            {
                "keep": [1, 2, 3, 4],
                "empty": [np.nan, np.nan, np.nan, np.nan],
                "also_empty": ["", "NULL", "-", "N/A"],
            }
        )
        df.loc[4] = [np.nan, np.nan, np.nan]
        out = clean(df)
        assert "empty" not in out.columns
        assert "also_empty" not in out.columns
        assert "keep" in out.columns
        # La fila completamente vacía se descartó.
        assert len(out) == 4

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"a": ["x", "NULL"]})
        original = df.copy()
        _ = clean(df)
        pd.testing.assert_frame_equal(df, original)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        out = clean(df)
        assert out.empty


# ------------------ column_classifier.classify ------------------


class TestColumnClassifier:
    def test_numeric_int_and_float(self):
        df = pd.DataFrame({"i": [1, 2, 3], "f": [1.0, 2.0, 3.5]})
        _, cls = classify(df)
        assert set(cls["numeric"]) == {"i", "f"}
        assert cls["categorical"] == []
        assert cls["temporal"] == []

    def test_categorical_low_cardinality_strings(self):
        df = pd.DataFrame({"cat": ["a", "b", "a", "c", "b"] * 10})
        _, cls = classify(df)
        assert cls["categorical"] == ["cat"]
        assert cls["numeric"] == []

    def test_temporal_iso_dates_detected_and_parsed(self):
        df = pd.DataFrame({"d": ["2024-01-01", "2024-02-15", "2024-03-30", "2024-04-12"]})
        parsed_df, cls = classify(df)
        assert cls["temporal"] == ["d"]
        assert pd.api.types.is_datetime64_any_dtype(parsed_df["d"])

    def test_numeric_id_strings_are_not_misclassified_as_temporal(self):
        # Caso de prueba crítico — IDs como "12345" no deben caer como fechas.
        df = pd.DataFrame({"id": [str(x) for x in range(10000, 10020)]})
        _, cls = classify(df)
        assert cls["temporal"] == []

    def test_boolean_column_is_categorical(self):
        df = pd.DataFrame({"b": [True, False, True, True]})
        _, cls = classify(df)
        assert cls["categorical"] == ["b"]

    def test_high_cardinality_strings_go_to_other(self):
        # 200 strings únicos, ratio = 1.0 — supera tanto MAX_UNIQUE como MAX_RATIO.
        df = pd.DataFrame({"s": [f"v_{i}" for i in range(200)]})
        _, cls = classify(df)
        assert cls["other"] == ["s"]


class TestClassifyNoMutation:
    def test_classify_returns_tuple_and_does_not_mutate_input(self):
        df = pd.DataFrame(
            {
                "fecha": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "valor": [1, 2, 3],
            }
        )
        original_dtype = df["fecha"].dtype  # object
        new_df, classification = classify(df)
        # El df original NO se mutó.
        assert df["fecha"].dtype == original_dtype
        # El nuevo df SÍ tiene "fecha" como datetime.
        assert pd.api.types.is_datetime64_any_dtype(new_df["fecha"])
        # La clasificación es correcta.
        assert "fecha" in classification["temporal"]
        assert "valor" in classification["numeric"]


# ------------------------- stats module -------------------------


class TestNumericSummary:
    def test_mean_median_min_max_exact(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        rows = numeric_summary(df, ["x"])
        assert len(rows) == 1
        r = rows[0]
        assert r["column"] == "x"
        assert r["count"] == 5
        assert r["mean"] == 3.0
        assert r["median"] == 3.0
        assert r["min"] == 1.0
        assert r["max"] == 5.0
        assert r["nulls"] == 0

    def test_std_matches_pandas(self):
        values = [10.0, 12.0, 23.0, 23.0, 16.0, 23.0, 21.0, 16.0]
        df = pd.DataFrame({"x": values})
        rows = numeric_summary(df, ["x"])
        expected_std = round(float(pd.Series(values).std()), 4)
        assert rows[0]["std"] == expected_std

    def test_nulls_are_counted(self):
        df = pd.DataFrame({"x": [1.0, np.nan, 2.0, np.nan, 3.0]})
        rows = numeric_summary(df, ["x"])
        assert rows[0]["count"] == 3
        assert rows[0]["nulls"] == 2
        assert rows[0]["mean"] == 2.0

    def test_all_nan_column_is_skipped(self):
        df = pd.DataFrame({"x": [np.nan, np.nan, np.nan]})
        rows = numeric_summary(df, ["x"])
        assert rows == []

    def test_inf_values_sanitized_to_none(self):
        df = pd.DataFrame({"x": [1.0, np.inf, 2.0]})
        rows = numeric_summary(df, ["x"])
        # mean con inf devuelve inf → debe sanitizarse a None.
        assert rows[0]["mean"] is None

    def test_empty_numeric_list_returns_empty(self):
        df = pd.DataFrame({"x": [1, 2, 3]})
        assert numeric_summary(df, []) == []


class TestDatasetOverview:
    def test_basic_counts(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        cls = {"numeric": ["a"], "categorical": ["b"], "temporal": [], "other": []}
        ov = dataset_overview(df, cls)
        assert ov["rows"] == 3
        assert ov["columns"] == 2
        assert ov["numeric_count"] == 1
        assert ov["categorical_count"] == 1
        assert ov["temporal_count"] == 0
        assert ov["total_nulls"] == 0
        assert ov["memory_mb"] >= 0

    def test_counts_nulls_across_dataframe(self):
        df = pd.DataFrame({"a": [1, np.nan, 3], "b": ["x", None, "z"]})
        cls = {"numeric": ["a"], "categorical": ["b"], "temporal": [], "other": []}
        ov = dataset_overview(df, cls)
        assert ov["total_nulls"] == 2


# ------------------- data_loader CSV / Excel -------------------


class TestCSVLoader:
    def test_basic_comma_csv(self, tmp_path: Path):
        p = tmp_path / "basic.csv"
        p.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")
        df = load_csv(p)
        assert list(df.columns) == ["a", "b", "c"]
        assert df.shape == (2, 3)

    def test_semicolon_delimiter_detected(self, tmp_path: Path):
        p = tmp_path / "semi.csv"
        p.write_text("a;b;c\n1;2;3\n4;5;6\n", encoding="utf-8")
        df = load_csv(p)
        assert df.shape == (2, 3)
        assert list(df.columns) == ["a", "b", "c"]

    def test_latin1_encoding(self, tmp_path: Path):
        p = tmp_path / "latin.csv"
        # Contenido con acentos en latin-1 — debe decodificar tras fallar utf-8.
        p.write_bytes("nombre,edad\nMaría,30\nJesús,25\n".encode("latin-1"))
        df = load_csv(p)
        assert df.shape == (2, 2)
        # El loader pudo leer con utf-8-sig/latin-1 según fallback; lo importante es
        # que no falle y conserve filas.
        assert "edad" in df.columns

    def test_empty_file_raises(self, tmp_path: Path):
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        with pytest.raises(CSVLoadError):
            load_csv(p)

    def test_nonexistent_file_raises(self, tmp_path: Path):
        with pytest.raises(CSVLoadError):
            load_csv(tmp_path / "ghost.csv")


class TestExcelLoader:
    def test_basic_xlsx(self, tmp_path: Path):
        p = tmp_path / "basic.xlsx"
        df_orig = pd.DataFrame(
            {
                "producto": ["A", "B", "C"],
                "precio": [10.0, 20.0, 30.0],
                "stock": [5, 3, 7],
            }
        )
        df_orig.to_excel(p, index=False, engine="openpyxl")

        df = load_excel(p)
        assert df.shape == (3, 3)
        assert set(df.columns) == {"producto", "precio", "stock"}

    def test_load_dataset_dispatches_to_excel(self, tmp_path: Path):
        p = tmp_path / "data.xlsx"
        pd.DataFrame({"x": [1, 2], "y": [3, 4]}).to_excel(p, index=False, engine="openpyxl")
        df = load_dataset(p)
        assert df.shape == (2, 2)

    def test_load_dataset_dispatches_to_csv(self, tmp_path: Path):
        p = tmp_path / "data.csv"
        p.write_text("x,y\n1,3\n2,4\n", encoding="utf-8")
        df = load_dataset(p)
        assert df.shape == (2, 2)

    def test_empty_xlsx_raises(self, tmp_path: Path):
        p = tmp_path / "empty.xlsx"
        pd.DataFrame().to_excel(p, index=False, engine="openpyxl")
        with pytest.raises(CSVLoadError):
            load_excel(p)

    def test_corrupt_xlsx_raises(self, tmp_path: Path):
        p = tmp_path / "corrupt.xlsx"
        p.write_bytes(b"this is not a valid xlsx file")
        with pytest.raises(CSVLoadError):
            load_excel(p)


class TestOptimizeDtypes:
    def test_downcasts_integers(self):
        df = pd.DataFrame({"x": pd.array([1, 2, 3], dtype="int64")})
        out = optimize_dtypes(df)
        # int8 alcanza para 1..3 — debe reducirse desde int64.
        assert out["x"].dtype.itemsize < 8

    def test_downcasts_floats(self):
        df = pd.DataFrame({"y": pd.array([1.0, 2.0, 3.0], dtype="float64")})
        out = optimize_dtypes(df)
        assert out["y"].dtype.itemsize < 8


# ----------------------- filter_engine -----------------------


class TestFilterEngine:
    @pytest.fixture
    def sample(self):
        return pd.DataFrame(
            {
                "producto": ["A", "B", "A", "C", "B", "A"],
                "precio": [10.5, 20.0, 11.0, 30.5, 21.0, 10.7],
                "fecha": pd.to_datetime(
                    [
                        "2024-01-01",
                        "2024-01-02",
                        "2024-01-03",
                        "2024-01-04",
                        "2024-01-05",
                        "2024-01-06",
                    ]
                ),
            }
        )

    def test_categorical_filter(self, sample):
        out = apply_filters(sample, {"categorical": {"producto": ["A"]}})
        assert len(out) == 3
        assert set(out["producto"]) == {"A"}

    def test_numeric_range_inclusive(self, sample):
        out = apply_filters(sample, {"numeric": {"precio": {"min": 11.0, "max": 21.0}}})
        # 11.0, 20.0, 21.0 — 3 filas (inclusivo en ambos extremos).
        assert len(out) == 3
        assert out["precio"].min() >= 11.0
        assert out["precio"].max() <= 21.0

    def test_numeric_only_min_or_max(self, sample):
        only_min = apply_filters(sample, {"numeric": {"precio": {"min": 15.0, "max": None}}})
        assert all(only_min["precio"] >= 15.0)
        only_max = apply_filters(sample, {"numeric": {"precio": {"min": None, "max": 15.0}}})
        assert all(only_max["precio"] <= 15.0)

    def test_temporal_range(self, sample):
        out = apply_filters(
            sample,
            {"temporal": {"fecha": {"start": "2024-01-03", "end": "2024-01-05"}}},
        )
        assert len(out) == 3
        assert out["fecha"].min() >= pd.Timestamp("2024-01-03")
        assert out["fecha"].max() <= pd.Timestamp("2024-01-05")

    def test_combined_filters(self, sample):
        out = apply_filters(
            sample,
            {
                "categorical": {"producto": ["A", "B"]},
                "numeric": {"precio": {"min": 11.0, "max": None}},
            },
        )
        # Producto A o B con precio >= 11 → (A,11.0), (B,20.0), (B,21.0).
        assert len(out) == 3
        assert set(out["producto"]) == {"A", "B"}
        assert all(out["precio"] >= 11.0)

    def test_empty_filters_returns_all(self, sample):
        out = apply_filters(sample, {})
        assert len(out) == len(sample)

    def test_does_not_mutate_input(self, sample):
        before = sample.copy()
        _ = apply_filters(sample, {"categorical": {"producto": ["A"]}})
        pd.testing.assert_frame_equal(sample, before)

    def test_unknown_column_is_ignored(self, sample):
        out = apply_filters(sample, {"categorical": {"no_existe": ["x"]}})
        assert len(out) == len(sample)

    def test_available_filters_lists_categorical_options(self, sample):
        cls = {
            "categorical": ["producto"],
            "numeric": ["precio"],
            "temporal": ["fecha"],
            "other": [],
        }
        opts = available_filters(sample, cls)
        assert any(c["column"] == "producto" for c in opts["categorical"])
        cat_meta = next(c for c in opts["categorical"] if c["column"] == "producto")
        assert set(cat_meta["options"]) == {"A", "B", "C"}
        num_meta = next(n for n in opts["numeric"] if n["column"] == "precio")
        assert math.isclose(num_meta["min"], 10.5)
        assert math.isclose(num_meta["max"], 30.5)
        assert any(t["column"] == "fecha" for t in opts["temporal"])


# ----------------- pipeline end-to-end (smoke) -----------------


class TestPipelineSmoke:
    """Pasa un DataFrame por todo el pipeline y verifica invariantes globales."""

    def test_clean_then_classify_then_optimize(self):
        df_raw = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "categoria": ["A", "B", "A", "C", "B"],
                "precio": [10.5, 20.0, np.nan, 30.5, 21.0],
                "fecha": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                "nulos_solo": ["NULL", "-", "N/A", None, ""],
            }
        )

        df = clean(df_raw)
        # "nulos_solo" debe desaparecer tras limpieza.
        assert "nulos_solo" not in df.columns

        df, cls = classify(df)
        # fecha → temporal; precio,id → numeric; categoria → categorical
        assert "fecha" in cls["temporal"]
        assert "categoria" in cls["categorical"]
        assert set(cls["numeric"]) == {"id", "precio"}

        df = optimize_dtypes(df)

        ov = dataset_overview(df, cls)
        assert ov["rows"] == 5
        assert ov["columns"] == 4
        assert ov["temporal_count"] == 1
        assert ov["categorical_count"] == 1
        assert ov["numeric_count"] == 2

        rows = numeric_summary(df, cls["numeric"])
        precio_row = next(r for r in rows if r["column"] == "precio")
        assert precio_row["count"] == 4  # uno NaN
        assert precio_row["nulls"] == 1
        # Media de [10.5, 20.0, 30.5, 21.0] = 20.5
        assert precio_row["mean"] == 20.5
