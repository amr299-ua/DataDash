# core/column_classifier.py
"""Clasifica columnas como numéricas, categóricas, temporales o de alta cardinalidad."""
from __future__ import annotations

import warnings
from typing import Dict, List, Optional

import pandas as pd

CATEGORICAL_MAX_UNIQUE = 50
CATEGORICAL_MAX_RATIO = 0.5
DATETIME_PARSE_THRESHOLD = 0.8


def classify(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Clasifica las columnas. Muta `df` parseando columnas temporales."""
    numeric: List[str] = []
    categorical: List[str] = []
    temporal: List[str] = []
    other: List[str] = []
    n_rows = max(1, len(df))

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_datetime64_any_dtype(series):
            temporal.append(col)
            continue

        if pd.api.types.is_bool_dtype(series):
            categorical.append(col)
            continue

        if pd.api.types.is_numeric_dtype(series):
            numeric.append(col)
            continue

        if series.dtype == "object" or pd.api.types.is_string_dtype(series):
            parsed = _try_parse_datetime(series)
            if parsed is not None:
                df[col] = parsed
                temporal.append(col)
                continue

            # Heurística por cardinalidad.
            nunique = series.nunique(dropna=True)
            if nunique == 0:
                other.append(col)
                continue
            ratio = nunique / n_rows
            if nunique <= CATEGORICAL_MAX_UNIQUE or ratio <= CATEGORICAL_MAX_RATIO:
                categorical.append(col)
            else:
                other.append(col)
        else:
            other.append(col)

    return {
        "numeric": numeric,
        "categorical": categorical,
        "temporal": temporal,
        "other": other,
    }


def _try_parse_datetime(series: pd.Series) -> Optional[pd.Series]:
    """Parsea como datetime si al menos DATETIME_PARSE_THRESHOLD de la muestra es válido."""
    sample = series.dropna()
    if sample.empty:
        return None
    sample = sample.head(80)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed_sample = pd.to_datetime(sample, errors="coerce", utc=False)
        except (ValueError, TypeError):
            return None

    if parsed_sample.notna().mean() < DATETIME_PARSE_THRESHOLD:
        return None

    # Filtros adicionales: cadenas puramente numéricas como "12345" o "1.5" no son fechas.
    str_sample = sample.astype(str)
    looks_numeric = str_sample.str.fullmatch(r"-?\d+(\.\d+)?").mean()
    if looks_numeric > 0.5:
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return pd.to_datetime(series, errors="coerce", utc=False)
        except (ValueError, TypeError):
            return None
