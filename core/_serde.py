# core/_serde.py
"""Utilidades de serialización JSON-safe compartidas por el pipeline.

Cualquier valor numérico que pueda contener NaN/Inf debe pasar por `safe_round`
antes de ser incluido en un payload JSON, porque `json.dumps(allow_nan=True)`
produce JSON no estándar que Chart.js rechaza.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def safe_round(value: Any, ndigits: int = 4) -> float | None:
    """Convierte a float redondeado o None si no es serializable.

    Reglas: NaN/Inf/None/unparseable → None. Resto → round(float, ndigits).
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return round(v, ndigits)
