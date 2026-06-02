# routes/_helpers.py
"""Helpers compartidos por los blueprints de cara al usuario."""

from __future__ import annotations

from typing import Any

from flask import abort, current_app, session
from werkzeug.utils import secure_filename

from core.cache import dataset_cache


def active_payload_or_404() -> dict[str, Any]:
    """Devuelve el payload activo o aborta con 404/410 si no hay sesión válida."""
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="El dataset ha expirado.")
    return payload


def processed_stem(original: str) -> str:
    """Deriva un nombre amigable: 'ventas.xlsx' → 'ventas_cleaned'."""
    base = secure_filename(original or "dataset") or "dataset"
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return f"{stem}_cleaned"


def clear_derived_cache() -> None:
    """Limpia Flask-Caching si está disponible; silencia fallos defensivamente."""
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE")
    if flask_cache is None:
        return
    try:
        flask_cache.clear()
    except Exception:  # noqa: BLE001
        current_app.logger.warning("No se pudo limpiar Flask-Caching.")
