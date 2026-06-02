# core/filter_engine.py
"""Filtrado vectorizado sobre el DataFrame cacheado.

`available_filters` produce la metadata que la UI usa para pintar controles
(multi-select para categóricas, min/max para numéricas, rango de fechas para
temporales). `apply_filters` consume el diccionario que envía el frontend y
devuelve un DataFrame filtrado SIN mutar el original.

Reglas de filtrado:
- Categóricas: lista de valores aceptados. Si está vacía/ausente, no filtra.
- Numéricas: `{"min": <float|None>, "max": <float|None>}` — None = sin límite.
- Temporales: `{"start": <ISO string|None>, "end": <ISO string|None>}` — inclusivo.

Filtros desconocidos o columnas inexistentes se ignoran silenciosamente (defensivo).
"""

from __future__ import annotations

import contextlib
from typing import Any

import numpy as np
import pandas as pd

# Límite de valores únicos que exponemos al frontend por columna categórica.
# Más allá de esto, la UI ofrece un input de texto libre (substring match).
CATEGORICAL_MAX_OPTIONS = 50


def available_filters(df: pd.DataFrame, classification: dict[str, list[str]]) -> dict[str, Any]:
    """Devuelve metadata serializable JSON para alimentar los controles del frontend."""
    filters: dict[str, Any] = {
        "categorical": [],
        "numeric": [],
        "temporal": [],
    }

    for col in classification.get("categorical", []):
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        uniques = series.astype(str).unique().tolist()
        truncated = len(uniques) > CATEGORICAL_MAX_OPTIONS
        if truncated:
            # Ordena por frecuencia y toma los más comunes; mejor UX que orden alfabético.
            top = series.astype(str).value_counts().head(CATEGORICAL_MAX_OPTIONS).index.tolist()
            options = [str(v) for v in top]
        else:
            options = sorted([str(v) for v in uniques])
        filters["categorical"].append(
            {
                "column": col,
                "options": options,
                "truncated": truncated,
            }
        )

    for col in classification.get("numeric", []):
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        try:
            cmin = float(series.min())
            cmax = float(series.max())
        except (TypeError, ValueError):
            continue
        if np.isnan(cmin) or np.isnan(cmax) or np.isinf(cmin) or np.isinf(cmax):
            continue
        filters["numeric"].append(
            {
                "column": col,
                "min": cmin,
                "max": cmax,
            }
        )

    for col in classification.get("temporal", []):
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        try:
            tmin = pd.Timestamp(series.min())
            tmax = pd.Timestamp(series.max())
        except (TypeError, ValueError):
            continue
        if pd.isna(tmin) or pd.isna(tmax):
            continue
        filters["temporal"].append(
            {
                "column": col,
                "min": tmin.isoformat(),
                "max": tmax.isoformat(),
            }
        )

    return filters


def apply_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Aplica el diccionario de filtros del frontend de forma vectorizada.

    Acumula una máscara por filtro y las combina con AND (default) u OR según
    `filters["combinator"]`. Nunca itera por filas.
    """
    if not filters or not isinstance(filters, dict):
        return df

    combinator = str(filters.get("combinator") or "AND").upper()
    if combinator not in ("AND", "OR"):
        combinator = "AND"

    masks: list[pd.Series] = []

    # Categóricos — { col: [valor1, valor2, ...] }
    for col, allowed in (filters.get("categorical") or {}).items():
        if col not in df.columns or not allowed:
            continue
        if not isinstance(allowed, (list, tuple, set)):
            continue
        allowed_str = {str(v) for v in allowed}
        col_str = df[col].astype("string")
        masks.append(col_str.isin(allowed_str))

    # Numéricos — { col: {"min": x, "max": y} }
    for col, bounds in (filters.get("numeric") or {}).items():
        if col not in df.columns or not isinstance(bounds, dict):
            continue
        col_num = pd.to_numeric(df[col], errors="coerce")
        lo = bounds.get("min")
        hi = bounds.get("max")
        m = pd.Series(True, index=df.index)
        if lo is not None:
            with contextlib.suppress(TypeError, ValueError):
                m &= col_num >= float(lo)
        if hi is not None:
            with contextlib.suppress(TypeError, ValueError):
                m &= col_num <= float(hi)
        masks.append(m)

    # Temporales — { col: {"start": iso, "end": iso} }
    for col, bounds in (filters.get("temporal") or {}).items():
        if col not in df.columns or not isinstance(bounds, dict):
            continue
        col_dt = pd.to_datetime(df[col], errors="coerce")
        start = bounds.get("start")
        end = bounds.get("end")
        m = pd.Series(True, index=df.index)
        if start:
            with contextlib.suppress(TypeError, ValueError):
                m &= col_dt >= pd.Timestamp(start)
        if end:
            with contextlib.suppress(TypeError, ValueError):
                m &= col_dt <= pd.Timestamp(end)
        masks.append(m)

    if not masks:
        return df

    if combinator == "OR":
        final = masks[0].copy()
        for m in masks[1:]:
            final |= m
    else:
        final = masks[0].copy()
        for m in masks[1:]:
            final &= m

    return df.loc[final].reset_index(drop=True)
