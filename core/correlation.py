# core/correlation.py
"""Matriz de correlación de Pearson sobre columnas numéricas.

El frontend renderiza la matriz como grid CSS (sin librería extra). Aquí solo
producimos un payload JSON-safe: columnas + matriz cuadrada con valores en
[-1, 1] o None para celdas indefinidas (varianza cero, NaN, etc.).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

MAX_CORRELATION_COLS = 25


def correlation_matrix(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
    """Calcula Pearson entre las columnas numéricas indicadas.

    - Si hay menos de 2 columnas numéricas, devuelve `{available: False, ...}`
    - Si hay más de MAX_CORRELATION_COLS, se queda con las primeras N para
      mantener el grid renderizable.
    - Valores NaN/Inf se sanitizan a `None` para que el JSON sea válido.
    """
    cols = [c for c in numeric_cols if c in df.columns]
    if len(cols) < 2:
        return {"available": False, "reason": "Se necesitan al menos 2 columnas numéricas.", "columns": [], "matrix": []}

    truncated = False
    if len(cols) > MAX_CORRELATION_COLS:
        cols = cols[:MAX_CORRELATION_COLS]
        truncated = True

    subset = df[cols]
    # pandas .corr() ya es vectorizado y excluye NaN par a par.
    corr = subset.corr(method="pearson", numeric_only=True)
    # Reindex para garantizar el mismo orden de filas/columnas que `cols`.
    corr = corr.reindex(index=cols, columns=cols)

    matrix: List[List[Optional[float]]] = []
    for row_col in cols:
        row_vals: List[Optional[float]] = []
        for col_col in cols:
            v = corr.at[row_col, col_col]
            row_vals.append(_sanitize(v))
        matrix.append(row_vals)

    return {
        "available": True,
        "columns": cols,
        "matrix": matrix,
        "truncated": truncated,
        "total_numeric": len(numeric_cols),
    }


def _sanitize(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    # Clamp defensivamente — Pearson siempre cae en [-1, 1] pero redondeos pueden desbordar.
    if v > 1.0:
        v = 1.0
    elif v < -1.0:
        v = -1.0
    return round(v, 4)
