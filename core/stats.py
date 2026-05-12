# core/stats.py
"""Estadísticas descriptivas vectorizadas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def numeric_summary(df: pd.DataFrame, numeric_cols: List[str]) -> List[Dict[str, Any]]:
    """Una fila por cada columna numérica con métricas básicas."""
    if not numeric_cols:
        return []

    subset = df[numeric_cols]
    desc = subset.describe().T  # vectorizado

    summaries: List[Dict[str, Any]] = []
    for col in numeric_cols:
        if col not in desc.index:
            continue
        count = desc.at[col, "count"]
        if pd.isna(count) or count == 0:
            continue
        summaries.append(
            {
                "column": col,
                "count": int(count),
                "mean": _round(desc.at[col, "mean"]),
                "median": _round(subset[col].median()),
                "std": _round(desc.at[col, "std"]),
                "min": _round(desc.at[col, "min"]),
                "max": _round(desc.at[col, "max"]),
                "nulls": int(df[col].isna().sum()),
            }
        )
    return summaries


def dataset_overview(df: pd.DataFrame, classification: Dict[str, List[str]]) -> Dict[str, Any]:
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "numeric_count": len(classification.get("numeric", [])),
        "categorical_count": len(classification.get("categorical", [])),
        "temporal_count": len(classification.get("temporal", [])),
        "other_count": len(classification.get("other", [])),
        "total_nulls": int(df.isna().sum().sum()),
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 ** 2), 3),
    }


def _round(value: Any, ndigits: int = 4) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return round(v, ndigits)
