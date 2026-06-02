# routes/api_custom.py
"""Constructor de gráficos personalizados (scatter | bar | line).

A diferencia de los charts auto-generados en `core/chart_builder`, aquí el
usuario elige columna X, columna Y y tipo de gráfico desde el modal del
dashboard. El payload devuelto sigue el mismo contrato Chart.js que
dashboard.js consume.
"""

from __future__ import annotations

import pandas as pd
from flask import Blueprint, abort, jsonify, request, session

from core._serde import safe_round
from core.cache import dataset_cache

api_custom_bp = Blueprint("api_custom", __name__)

ALLOWED_TYPES = {"scatter", "bar", "line"}
SCATTER_MAX_POINTS = 2000


def _payload() -> dict:
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="Dataset expirado.")
    return payload


def _scatter(df: pd.DataFrame, x: str, y: str) -> dict:
    if not (pd.api.types.is_numeric_dtype(df[x]) and pd.api.types.is_numeric_dtype(df[y])):
        return {"error": "Scatter requiere dos columnas numéricas."}
    pair = df[[x, y]].dropna()
    if pair.empty:
        return {"error": "No hay datos válidos para esa combinación."}
    if len(pair) > SCATTER_MAX_POINTS:
        pair = pair.sample(SCATTER_MAX_POINTS, random_state=42)
    points = [
        {"x": safe_round(a), "y": safe_round(b)} for a, b in pair.itertuples(index=False, name=None)
    ]
    return {
        "id": f"custom-scatter-{x}-{y}",
        "title": f"{y} vs {x}",
        "type": "scatter",
        "data": {"datasets": [{"label": f"{y} vs {x}", "data": points, "pointRadius": 3}]},
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "x": {"type": "linear", "title": {"display": True, "text": x}},
                "y": {"title": {"display": True, "text": y}},
            },
        },
    }


def _bar(df: pd.DataFrame, x: str, y: str) -> dict:
    if not pd.api.types.is_numeric_dtype(df[y]):
        return {"error": "El eje Y de una barra debe ser numérico."}
    pair = df[[x, y]].dropna()
    if pair.empty:
        return {"error": "No hay datos válidos para esa combinación."}
    grouped = pair.groupby(x, sort=True)[y].mean()
    return {
        "id": f"custom-bar-{x}-{y}",
        "title": f"{y} medio por {x}",
        "type": "bar",
        "data": {
            "labels": [str(v) for v in grouped.index],
            "datasets": [
                {
                    "label": f"{y} medio",
                    "data": [safe_round(v) for v in grouped.values],
                }
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "x": {"title": {"display": True, "text": x}},
                "y": {"beginAtZero": True, "title": {"display": True, "text": y}},
            },
        },
    }


def _line(df: pd.DataFrame, x: str, y: str) -> dict:
    if not pd.api.types.is_numeric_dtype(df[y]):
        return {"error": "El eje Y de una línea debe ser numérico."}
    pair = df[[x, y]].dropna()
    if pair.empty:
        return {"error": "No hay datos válidos para esa combinación."}
    pair = pair.sort_values(x)
    return {
        "id": f"custom-line-{x}-{y}",
        "title": f"{y} a lo largo de {x}",
        "type": "line",
        "data": {
            "labels": [str(v) for v in pair[x]],
            "datasets": [
                {
                    "label": y,
                    "data": [safe_round(v) for v in pair[y]],
                    "fill": False,
                    "tension": 0.25,
                    "pointRadius": 2,
                }
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "x": {"title": {"display": True, "text": x}},
                "y": {"title": {"display": True, "text": y}},
            },
        },
    }


_BUILDERS = {"scatter": _scatter, "bar": _bar, "line": _line}


@api_custom_bp.post("/chart/custom")
def custom_chart():
    body = request.get_json(silent=True) or {}
    chart_type = body.get("type")
    x = body.get("x")
    y = body.get("y")

    if chart_type not in ALLOWED_TYPES:
        return jsonify({"error": f"Tipo no soportado. Usa: {sorted(ALLOWED_TYPES)}"}), 400

    payload = _payload()
    df = payload["df"]
    if x not in df.columns or y not in df.columns:
        return jsonify({"error": "Columna X o Y no existe en el dataset."}), 400

    spec = _BUILDERS[chart_type](df, x, y)
    if "error" in spec:
        return jsonify(spec), 400
    return jsonify(spec)
