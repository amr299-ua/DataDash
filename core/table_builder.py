# core/table_builder.py
"""Payloads paginados para la tabla del frontend."""
from __future__ import annotations

import math
from typing import Any, Dict

import numpy as np
import pandas as pd


def page(df: pd.DataFrame, page_number: int, page_size: int) -> Dict[str, Any]:
    """Devuelve un slice de `df` listo para serializar como JSON."""
    page_size = max(1, min(100, int(page_size)))
    n_rows = len(df)
    n_pages = max(1, math.ceil(n_rows / page_size))
    page_number = max(1, min(int(page_number), n_pages))

    start = (page_number - 1) * page_size
    end = start + page_size
    slice_df = df.iloc[start:end]

    columns = [str(c) for c in df.columns]
    rows = [[_serialize(v) for v in row] for row in slice_df.itertuples(index=False, name=None)]

    return {
        "columns": columns,
        "rows": rows,
        "page": page_number,
        "page_size": page_size,
        "total_rows": n_rows,
        "total_pages": n_pages,
    }


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    # Cubre NaN, NaT, pd.NA — todos quedan como None.
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (int, float, bool, str)):
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
        return value
    return str(value)
