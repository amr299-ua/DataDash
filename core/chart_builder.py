# core/chart_builder.py
"""Construye configuraciones Chart.js a partir del DataFrame clasificado."""
from __future__ import annotations

import colorsys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from core._serde import safe_round

MAX_CATEGORIES = 12
MAX_HISTOGRAM_BINS = 20
MAX_CHARTS = 12
SCATTER_MAX_POINTS = 2000


def build_charts(df: pd.DataFrame, classification: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Genera hasta MAX_CHARTS visualizaciones a partir de la clasificación."""
    charts: List[Dict[str, Any]] = []
    numeric = classification.get("numeric", [])
    categorical = classification.get("categorical", [])
    temporal = classification.get("temporal", [])

    # 1) Distribución de cada categórica.
    for col in categorical:
        chart = _categorical_distribution(df, col)
        if chart is not None:
            charts.append(chart)
        if len(charts) >= MAX_CHARTS:
            return charts

    # 2) Histograma de cada numérica.
    for col in numeric:
        chart = _numeric_histogram(df, col)
        if chart is not None:
            charts.append(chart)
        if len(charts) >= MAX_CHARTS:
            return charts

    # 3) Series temporales para pares (temporal, numérica).
    for t_col in temporal:
        for n_col in numeric:
            chart = _time_series(df, t_col, n_col)
            if chart is not None:
                charts.append(chart)
            if len(charts) >= MAX_CHARTS:
                return charts

    # 4) Scatter para los dos primeros numéricos si queda espacio.
    if len(numeric) >= 2 and len(charts) < MAX_CHARTS:
        chart = _scatter(df, numeric[0], numeric[1])
        if chart is not None:
            charts.append(chart)

    return charts


def _categorical_distribution(df: pd.DataFrame, col: str) -> Optional[Dict[str, Any]]:
    counts = df[col].dropna().astype(str).value_counts()
    if counts.empty:
        return None

    if len(counts) > MAX_CATEGORIES:
        top = counts.head(MAX_CATEGORIES - 1)
        other_sum = int(counts.iloc[MAX_CATEGORIES - 1 :].sum())
        labels: List[str] = [str(x) for x in top.index] + ["Otros"]
        values: List[int] = [int(v) for v in top.values] + [other_sum]
    else:
        labels = [str(x) for x in counts.index]
        values = [int(v) for v in counts.values]

    palette = _palette(len(labels))
    chart_type = "pie" if len(labels) <= 6 else "bar"

    dataset = {
        "label": col,
        "data": values,
        "backgroundColor": palette,
        "borderColor": palette if chart_type == "bar" else ["#ffffff"] * len(labels),
        "borderWidth": 1,
    }

    options = _base_options(show_legend=(chart_type == "pie"))
    if chart_type == "bar":
        options["scales"] = {
            "y": {"beginAtZero": True, "title": {"display": True, "text": "Frecuencia"}},
            "x": {"title": {"display": True, "text": col}},
        }

    return {
        "id": f"cat-{_slug(col)}",
        "title": f"Distribución de {col}",
        "type": chart_type,
        "data": {"labels": labels, "datasets": [dataset]},
        "options": options,
    }


def _numeric_histogram(df: pd.DataFrame, col: str) -> Optional[Dict[str, Any]]:
    series = df[col].dropna()
    if series.empty:
        return None
    if series.nunique() <= 1:
        return None

    n_bins = min(MAX_HISTOGRAM_BINS, max(5, int(np.sqrt(len(series)))))
    try:
        counts, edges = np.histogram(series, bins=n_bins)
    except ValueError:
        return None

    labels = [f"{edges[i]:.2f}–{edges[i + 1]:.2f}" for i in range(len(counts))]
    palette = _palette(1)
    return {
        "id": f"hist-{_slug(col)}",
        "title": f"Histograma — {col}",
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": f"Frecuencia de {col}",
                    "data": [int(c) for c in counts],
                    "backgroundColor": palette[0],
                    "borderColor": palette[0],
                    "borderWidth": 1,
                }
            ],
        },
        "options": {
            **_base_options(show_legend=False),
            "scales": {
                "y": {"beginAtZero": True, "title": {"display": True, "text": "Frecuencia"}},
                "x": {"title": {"display": True, "text": col}},
            },
        },
    }


def _time_series(df: pd.DataFrame, t_col: str, n_col: str) -> Optional[Dict[str, Any]]:
    pair = df[[t_col, n_col]].dropna()
    if pair.empty:
        return None
    pair = pair.sort_values(t_col)

    # Agrupa por día para mantener payloads acotados.
    grouped = pair.groupby(pair[t_col].dt.date)[n_col].mean()
    if grouped.empty:
        return None
    # Si quedan demasiados puntos, agrupa por mes.
    if len(grouped) > 500:
        grouped = pair.groupby(pair[t_col].dt.to_period("M"))[n_col].mean()
        labels = [str(p) for p in grouped.index]
    else:
        labels = [d.isoformat() for d in grouped.index]

    values = [safe_round(v) for v in grouped.values]
    palette = _palette(1)
    return {
        "id": f"ts-{_slug(t_col)}-{_slug(n_col)}",
        "title": f"{n_col} a lo largo de {t_col}",
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": n_col,
                    "data": values,
                    "backgroundColor": palette[0],
                    "borderColor": palette[0],
                    "borderWidth": 2,
                    "fill": False,
                    "tension": 0.25,
                    "pointRadius": 2,
                }
            ],
        },
        "options": {
            **_base_options(show_legend=False),
            "scales": {
                "x": {"title": {"display": True, "text": t_col}},
                "y": {"title": {"display": True, "text": n_col}},
            },
        },
    }


def _scatter(df: pd.DataFrame, x_col: str, y_col: str) -> Optional[Dict[str, Any]]:
    pair = df[[x_col, y_col]].dropna()
    if pair.empty:
        return None
    if len(pair) > SCATTER_MAX_POINTS:
        pair = pair.sample(n=SCATTER_MAX_POINTS, random_state=42)

    points = [{"x": safe_round(x), "y": safe_round(y)} for x, y in pair.itertuples(index=False, name=None)]
    palette = _palette(1)
    return {
        "id": f"scatter-{_slug(x_col)}-{_slug(y_col)}",
        "title": f"{y_col} vs {x_col}",
        "type": "scatter",
        "data": {
            "datasets": [
                {
                    "label": f"{y_col} vs {x_col}",
                    "data": points,
                    "backgroundColor": palette[0],
                    "borderColor": palette[0],
                    "pointRadius": 3,
                }
            ]
        },
        "options": {
            **_base_options(show_legend=False),
            "scales": {
                "x": {"type": "linear", "title": {"display": True, "text": x_col}},
                "y": {"title": {"display": True, "text": y_col}},
            },
        },
    }


def _palette(n: int) -> List[str]:
    """Paleta HSL distribuida uniformemente."""
    if n <= 0:
        return []
    colors = []
    for i in range(n):
        hue = (i / max(n, 1)) * 0.85
        r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.6)
        colors.append(f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, 0.85)")
    return colors


def _base_options(show_legend: bool) -> Dict[str, Any]:
    return {
        "responsive": True,
        "maintainAspectRatio": False,
        "plugins": {
            "legend": {"display": show_legend, "position": "bottom"},
            "tooltip": {"enabled": True},
        },
    }


def _slug(text: str) -> str:
    s = "".join(c if c.isalnum() else "-" for c in str(text)).strip("-").lower()
    return s or "col"


