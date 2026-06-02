# routes/uploads.py
"""Rutas de ingesta: upload y reset."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from core.cache import dataset_cache
from core.chart_builder import build_charts
from core.column_classifier import classify
from core.correlation import correlation_matrix
from core.data_cleaner import clean
from core.data_loader import CSVLoadError, load_dataset, optimize_dtypes
from core.filter_engine import available_filters
from core.stats import dataset_overview, numeric_summary
from routes._helpers import clear_derived_cache

uploads_bp = Blueprint("uploads", __name__)
logger = logging.getLogger(__name__)


@uploads_bp.post("/upload")
def upload():
    if "file" not in request.files:
        flash("No se envió ningún archivo.", "danger")
        return redirect(url_for("dashboard.index"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("Selecciona un archivo CSV o Excel antes de continuar.", "danger")
        return redirect(url_for("dashboard.index"))

    filename = secure_filename(file.filename) or "dataset.csv"
    lower = filename.lower()
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    extension = lower.rsplit(".", 1)[-1] if "." in lower else ""
    if extension not in allowed:
        flash("Solo se aceptan archivos .csv o .xlsx.", "danger")
        return redirect(url_for("dashboard.index"))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    # Sufijo uuid para evitar colisiones con uploads concurrentes del mismo nombre.
    unique = uuid.uuid4().hex[:8]
    temp_path = upload_dir / f"__tmp_{unique}_{filename}"
    file.save(temp_path)

    try:
        df = load_dataset(temp_path)
        df = clean(df)
        if df.empty or df.shape[1] == 0:
            raise CSVLoadError("El archivo no contiene datos analizables tras la limpieza.")
        df, classification = classify(df)
        df = optimize_dtypes(df)
    except CSVLoadError as exc:
        logger.warning("CSV load failure for %s: %s", filename, exc)
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.index"))
    except Exception as exc:  # noqa: BLE001 — error inesperado, lo reportamos al usuario.
        logger.exception("Unexpected error processing %s", filename)
        flash(f"Error inesperado al procesar el archivo: {exc}", "danger")
        return redirect(url_for("dashboard.index"))
    finally:
        # Almacenamiento efímero: el CSV se borra apenas se procesa.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("No se pudo eliminar el upload temporal %s", temp_path)

    overview = dataset_overview(df, classification)
    stats = numeric_summary(df, classification["numeric"])
    charts = build_charts(df, classification)
    filter_options = available_filters(df, classification)
    correlation = correlation_matrix(df, classification["numeric"])

    # Si ya había un dataset previo en sesión, lo desechamos y purgamos la caché
    # de derivaciones (claves indexadas por token previo).
    previous_token = session.get("dataset_token")
    if previous_token:
        dataset_cache.discard(previous_token)
    clear_derived_cache()

    token = dataset_cache.put(
        {
            "df": df,
            "classification": classification,
            "overview": overview,
            "stats": stats,
            "charts": charts,
            "filter_options": filter_options,
            "correlation": correlation,
            "filename": filename,
        }
    )
    session["dataset_token"] = token
    return redirect(url_for("dashboard.dashboard"))


@uploads_bp.post("/reset")
def reset():
    token = session.pop("dataset_token", None)
    if token:
        dataset_cache.discard(token)
    clear_derived_cache()
    return redirect(url_for("dashboard.index"))
