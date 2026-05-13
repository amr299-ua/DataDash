# routes/api.py
"""API JSON interna que alimenta el dashboard."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify, request, session

from core.cache import dataset_cache
from core.chart_builder import build_charts
from core.filter_engine import apply_filters
from core.stats import dataset_overview, numeric_summary
from core.table_builder import page as build_page

api_bp = Blueprint("api", __name__)


def _current_payload():
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo en la sesión.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="El dataset ha expirado.")
    return payload


def _filters_from_request():
    """Acepta los filtros tanto desde JSON (POST) como desde query string (GET)."""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        return body if isinstance(body, dict) else {}
    return {}


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
    return jsonify(build_page(payload["df"], page_number, page_size))


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


@api_bp.post("/filter")
def filter_dataset():
    """Aplica filtros y devuelve overview/stats/charts/table recalculados.

    Body JSON: {
      "filters": {"categorical": {...}, "numeric": {...}, "temporal": {...}},
      "page": <int, opcional>,
      "page_size": <int, opcional>
    }

    NOTA: NO muta el df cacheado. Cada llamada filtra una copia y la descarta al
    terminar — el dataset original sigue intacto para futuros filtrados.
    """
    payload = _current_payload()
    body = _filters_from_request()
    raw_filters = body.get("filters") if isinstance(body, dict) else {}
    if not isinstance(raw_filters, dict):
        raw_filters = {}
    page_number = int(body.get("page", 1) or 1)
    page_size = int(body.get("page_size", 25) or 25)

    df_full = payload["df"]
    classification = payload["classification"]

    filtered = apply_filters(df_full, raw_filters)
    overview = dataset_overview(filtered, classification)
    stats_rows = numeric_summary(filtered, classification.get("numeric", []))
    charts_payload = build_charts(filtered, classification)
    table_payload = build_page(filtered, page_number, page_size)

    return jsonify(
        {
            "overview": overview,
            "numeric": stats_rows,
            "charts": charts_payload,
            "table": table_payload,
            "filtered_rows": int(len(filtered)),
            "total_rows": int(len(df_full)),
        }
    )
