# tests/test_load_csv_typed.py
"""Verifica que load_csv aprovecha la pre-inferencia de tipos sobre una muestra."""

from __future__ import annotations

import pandas as pd

from core.data_loader import load_csv


def test_large_csv_keeps_integer_dtype(tmp_path):
    """Tras la pre-inferencia, las columnas numéricas no deben caer a object."""
    rows = 20_000
    p = tmp_path / "big.csv"
    df = pd.DataFrame({"a": range(rows), "b": [f"row-{i}" for i in range(rows)]})
    df.to_csv(p, index=False)

    out = load_csv(p)
    assert len(out) == rows
    # `a` debe seguir siendo entero (no object/string).
    assert out["a"].dtype.kind in ("i", "u")
    # `b` es string.
    assert out["b"].dtype == "object" or out["b"].dtype.name == "string"


def test_small_csv_still_works(tmp_path):
    """Archivos pequeños (menos que el sample) deben seguir funcionando igual."""
    p = tmp_path / "small.csv"
    pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]}).to_csv(p, index=False)
    out = load_csv(p)
    assert len(out) == 3
    assert out["x"].dtype.kind in ("i", "u")


def test_csv_with_mixed_types_does_not_crash(tmp_path):
    """Si la muestra ve un int pero el resto incluye texto, la carga sigue funcionando."""
    p = tmp_path / "mixed.csv"
    # 100 enteros, luego un texto al final.
    lines = ["v"] + [str(i) for i in range(100)] + ["xyz"]
    p.write_text("\n".join(lines), encoding="utf-8")
    out = load_csv(p)
    assert len(out) == 101
