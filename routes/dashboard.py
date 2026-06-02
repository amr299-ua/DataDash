# routes/dashboard.py
"""Rutas de presentación: home y dashboard."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, session, url_for

from core.cache import dataset_cache

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    return render_template("index.html")


@dashboard_bp.get("/dashboard")
def dashboard():
    token = session.get("dataset_token")
    if not token:
        flash("Sube un archivo para acceder al dashboard.", "info")
        return redirect(url_for("dashboard.index"))

    payload = dataset_cache.get(token)
    if payload is None:
        session.pop("dataset_token", None)
        flash("La sesión ha expirado. Vuelve a subir el archivo.", "warning")
        return redirect(url_for("dashboard.index"))

    return render_template(
        "dashboard.html",
        filename=payload["filename"],
        overview=payload["overview"],
        stats=payload["stats"],
        charts=payload["charts"],
        classification=payload["classification"],
        filter_options=payload.get(
            "filter_options", {"categorical": [], "numeric": [], "temporal": []}
        ),
        correlation=payload.get("correlation", {"available": False, "columns": [], "matrix": []}),
    )
