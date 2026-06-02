# core/outliers.py
"""Detección simple de outliers con el método IQR (Tukey).

Una observación es outlier si cae fuera de `[Q1 - k·IQR, Q3 + k·IQR]`.
Para series vacías, constantes o sin valor numérico válido devuelve 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def iqr_outlier_count(series: pd.Series, k: float = 1.5) -> int:
    """Cuenta valores fuera del rango IQR amplificado por `k`."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return 0
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0 or np.isnan(iqr):
        return 0
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return int(((s < lo) | (s > hi)).sum())
