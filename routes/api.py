# routes/api.py
"""API JSON interna que alimenta el dashboard."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Tuple

from flask import Blueprint, abort, current_app, jsonify, request, session

from core.cache import dataset_cache
from core.chart_builder import build_charts
from core.correlation import correlation_matrix
from core.filter_engine import apply_filters
from core.stats import dataset_overview, numeric_summary
from core.table_builder import page as build_page

api_bp = Blueprint("api", __name__)


def _current_token_and_payload() -> Tuple[str, Dict[str, Any]]:
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo en la sesión.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="El dataset ha expirado.")
    return token, payload


def _current_payload() -> Dict[str, Any]:
    return _current_token_and_payload()[1]


def _filters_from_request() -> Dict[str, Any]:
    """Lee el body JSON para POST; en GET devuelve {}."""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        return body if isinstance(body, dict) else {}
    return {}


def _filters_signature(filters: Dict[str, Any]) -> str:
    """Hash determinista de un dict de filtros para usarlo como clave de caché."""
    try:
        normalized = json.dumps(filters or {}, sort_keys=True, default=str)
    except (TypeError, ValueError):
        normalized = repr(filters)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def _memo(key: str, builder):
    """Wrapper sobre Flask-Caching: si la app no lo expone, calcula sin caché."""
    cache = current_app.extensions.get("cache") if current_app else None
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE") if current_app else None
    if flask_cache is None:
        # Fallback: ejecuta sin cachear.
        return builder()
    cached = flask_cache.get(key)
    if cached is not None:
        return cached
    value = builder()
    flask_cache.set(key, value)
    return value


@api_bp.get("/charts")
def charts():
    payload = _current_payload()
    return jsonify({"charts": payload["charts"]})


@api_bp.get("/stats")
def stats():
    payload = _current_payload()
    return jsonify({"overview": payload["overview"], "numeric": payload["stats"]})


@api_bp.get("/data")
@api_bp.get("/table")
def table():
    payload = _current_payload()
    page_number = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", default=25, type=int) or 25
    search = request.args.get("q", default=None, type=str) or None
    sort_by = request.args.get("sort_by", default=None, type=str) or None
    sort_dir = request.args.get("sort_dir", default=None, type=str) or None
    return jsonify(build_page(
        payload["df"], page_number, page_size,
        search=search, sort_by=sort_by, sort_dir=sort_dir,
    ))


@api_bp.get("/classification")
def classification():
    payload = _current_payload()
    return jsonify(payload["classification"])


@api_bp.get("/filter_options")
def filter_options():
    payload = _current_payload()
    return jsonify(
        payload.get(
            "filter_options",
            {"categorical": [], "numeric": [], "temporal": []},
        )
    )


@api_bp.get("/correlation")
def correlation():
    """Matriz de correlación de Pearson sobre las columnas numéricas activas."""
    payload = _current_payload()
    return jsonify(
        payload.get(
            "correlation",
            {"available": False, "columns": [], "matrix": []},
        )
    )


@api_bp.post("/filter")
def filter_dataset():
    """Aplica filtros y devuelve overview/stats/charts/correlation/table recalculados.

    Body JSON: {
      "filters": {"categorical": {...}, "numeric": {...}, "temporal": {...}},
      "page": <int, opcional>,
      "page_size": <int, opcional>
    }

    NOTA: NO muta el df cacheado. Cada llamada filtra una copia y la descarta al
    terminar — el dataset original sigue intacto para futuros filtrados. Las
    derivaciones (overview, numeric, charts, correlation) se memoizan con
    Flask-Caching usando (token, filters_signature) como clave; la tabla incluye
    además page/page_size en su propia clave porque cambia con la paginación.
    """
    token, payload = _current_token_and_payload()
    body = _filters_from_request()
    raw_filters = body.get("filters") if isinstance(body, dict) else {}
    if not isinstance(raw_filters, dict):
        raw_filters = {}
    page_number = int(body.get("page", 1) or 1)
    page_size = int(body.get("page_size", 25) or 25)

    df_full = payload["df"]
    classification = payload["classification"]
    sig = _filters_signature(raw_filters)

    # El DataFrame filtrado se memoiza por (token, sig) — la operación más cara.
    def _build_filtered():
        return apply_filters(df_full, raw_filters)

    filtered = _memo(f"flt:{token}:{sig}", _build_filtered)

    overview = _memo(
        f"ovw:{token}:{sig}",
        lambda: dataset_overview(filtered, classification),
    )
    stats_rows = _memo(
        f"num:{token}:{sig}",
        lambda: numeric_summary(filtered, classification.get("numeric", [])),
    )
    charts_payload = _memo(
        f"chr:{token}:{sig}",
        lambda: build_charts(filtered, classification),
    )
    correlation_payload = _memo(
        f"cor:{token}:{sig}",
        lambda: correlation_matrix(filtered, classification.get("numeric", [])),
    )
    table_payload = _memo(
        f"tbl:{token}:{sig}:{page_number}:{page_size}",
        lambda: build_page(filtered, page_number, page_size),
    )

    return jsonify(
        {
            "overview": overview,
            "numeric": stats_rows,
            "charts": charts_payload,
            "correlation": correlation_payload,
            "table": table_payload,
            "filtered_rows": int(len(filtered)),
            "total_rows": int(len(df_full)),
        }
    )
