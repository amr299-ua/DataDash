# routes/main.py
"""Rutas de cara al usuario: upload y dashboard."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from core.cache import dataset_cache
from core.chart_builder import build_charts
from core.column_classifier import classify
from core.data_cleaner import clean
from core.data_loader import CSVLoadError, load_csv, optimize_dtypes
from core.stats import dataset_overview, numeric_summary

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.get("/")
def index():
    return render_template("index.html")


@main_bp.post("/upload")
def upload():
    if "file" not in request.files:
        flash("No se envió ningún archivo.", "danger")
        return redirect(url_for("main.index"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("Selecciona un archivo CSV antes de continuar.", "danger")
        return redirect(url_for("main.index"))

    filename = secure_filename(file.filename) or "dataset.csv"
    if not filename.lower().endswith(".csv"):
        flash("Solo se aceptan archivos con extensión .csv.", "danger")
        return redirect(url_for("main.index"))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"__tmp_{filename}"
    file.save(temp_path)

    try:
        df = load_csv(temp_path)
        df = clean(df)
        if df.empty or df.shape[1] == 0:
            raise CSVLoadError("El archivo no contiene datos analizables tras la limpieza.")
        classification = classify(df)
        df = optimize_dtypes(df)
    except CSVLoadError as exc:
        logger.warning("CSV load failure for %s: %s", filename, exc)
        flash(str(exc), "danger")
        return redirect(url_for("main.index"))
    except Exception as exc:  # noqa: BLE001 — error inesperado, lo reportamos al usuario.
        logger.exception("Unexpected error processing %s", filename)
        flash(f"Error inesperado al procesar el archivo: {exc}", "danger")
        return redirect(url_for("main.index"))
    finally:
        # Almacenamiento efímero: el CSV se borra apenas se procesa.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("No se pudo eliminar el upload temporal %s", temp_path)

    overview = dataset_overview(df, classification)
    stats = numeric_summary(df, classification["numeric"])
    charts = build_charts(df, classification)

    # Si ya había un dataset previo en sesión, lo desechamos.
    previous_token = session.get("dataset_token")
    if previous_token:
        dataset_cache.discard(previous_token)

    token = dataset_cache.put(
        {
            "df": df,
            "classification": classification,
            "overview": overview,
            "stats": stats,
            "charts": charts,
            "filename": filename,
        }
    )
    session["dataset_token"] = token
    return redirect(url_for("main.dashboard"))


@main_bp.get("/dashboard")
def dashboard():
    token = session.get("dataset_token")
    if not token:
        flash("Sube un archivo para acceder al dashboard.", "info")
        return redirect(url_for("main.index"))

    payload = dataset_cache.get(token)
    if payload is None:
        session.pop("dataset_token", None)
        flash("La sesión ha expirado. Vuelve a subir el archivo.", "warning")
        return redirect(url_for("main.index"))

    return render_template(
        "dashboard.html",
        filename=payload["filename"],
        overview=payload["overview"],
        stats=payload["stats"],
        charts=payload["charts"],
        classification=payload["classification"],
    )


@main_bp.post("/reset")
def reset():
    token = session.pop("dataset_token", None)
    if token:
        dataset_cache.discard(token)
    return redirect(url_for("main.index"))
