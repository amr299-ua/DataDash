# routes/api.py
"""API JSON interna que alimenta el dashboard."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify, request, session

from core.cache import dataset_cache
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
