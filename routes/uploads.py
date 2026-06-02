# routes/uploads.py
"""Rutas de ingesta: upload, selector de hoja Excel y reset."""

from __future__ import annotations

import contextlib
import logging
import uuid
from pathlib import Path

import pandas as pd
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
from core.correlation import correlation_matrix
from core.data_cleaner import clean
from core.data_loader import CSVLoadError, load_dataset, optimize_dtypes
from core.filter_engine import available_filters
from core.sheet_picker import list_sheets, load_sheet
from core.stats import dataset_overview, numeric_summary
from routes._helpers import clear_derived_cache

uploads_bp = Blueprint("uploads", __name__)
logger = logging.getLogger(__name__)


def _process_and_persist(df: pd.DataFrame, filename: str) -> str:
    """Limpia, clasifica y persiste un DataFrame; devuelve el token de sesión."""
    df = clean(df)
    if df.empty or df.shape[1] == 0:
        raise CSVLoadError("El archivo no contiene datos analizables tras la limpieza.")
    df, classification = classify(df)
    df = optimize_dtypes(df)

    overview = dataset_overview(df, classification)
    stats = numeric_summary(df, classification["numeric"])
    charts = build_charts(df, classification)
    filter_options = available_filters(df, classification)
    correlation = correlation_matrix(df, classification["numeric"])

    # Descarta el dataset anterior y limpia derivaciones cacheadas.
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
    return token


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

    # Si el archivo es .xlsx con varias hojas, derivamos al selector antes de procesar.
    if extension == "xlsx":
        try:
            sheets = list_sheets(temp_path)
        except CSVLoadError as exc:
            with contextlib.suppress(OSError):
                temp_path.unlink(missing_ok=True)
            flash(str(exc), "danger")
            return redirect(url_for("dashboard.index"))
        if len(sheets) > 1:
            pending_dir = upload_dir / "pending"
            pending_dir.mkdir(parents=True, exist_ok=True)
            pending_path = pending_dir / f"{unique}.xlsx"
            temp_path.rename(pending_path)
            session["pending_upload"] = {
                "path": str(pending_path),
                "filename": filename,
                "sheets": sheets,
            }
            return redirect(url_for("uploads.choose_sheet"))

    try:
        df = load_dataset(temp_path)
        _process_and_persist(df, filename)
    except CSVLoadError as exc:
        logger.warning("CSV load failure for %s: %s", filename, exc)
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.index"))
    except Exception as exc:  # noqa: BLE001 — error inesperado, lo reportamos al usuario.
        logger.exception("Unexpected error processing %s", filename)
        flash(f"Error inesperado al procesar el archivo: {exc}", "danger")
        return redirect(url_for("dashboard.index"))
    finally:
        # Almacenamiento efímero: el archivo se borra apenas se procesa.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("No se pudo eliminar el upload temporal %s", temp_path)

    return redirect(url_for("dashboard.dashboard"))


@uploads_bp.get("/upload/sheet")
def choose_sheet():
    """Muestra el selector de hoja cuando un Excel tiene varias."""
    pending = session.get("pending_upload")
    if not pending:
        return redirect(url_for("dashboard.index"))
    return render_template(
        "sheet_picker.html",
        filename=pending["filename"],
        sheets=pending["sheets"],
    )


@uploads_bp.post("/upload/sheet")
def process_sheet():
    pending = session.pop("pending_upload", None)
    if not pending:
        return redirect(url_for("dashboard.index"))

    sheet = request.form.get("sheet")
    if not sheet or sheet not in pending["sheets"]:
        # Restauramos para que el usuario pueda volver a elegir.
        session["pending_upload"] = pending
        flash("Selecciona una hoja válida.", "danger")
        return redirect(url_for("uploads.choose_sheet"))

    temp_path = Path(pending["path"])
    try:
        df = load_sheet(temp_path, sheet)
        _process_and_persist(df, pending["filename"])
    except CSVLoadError as exc:
        logger.warning("Error procesando hoja %s: %s", sheet, exc)
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.index"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error procesando hoja %s", sheet)
        flash(f"Error inesperado: {exc}", "danger")
        return redirect(url_for("dashboard.index"))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("No se pudo eliminar el upload pendiente %s", temp_path)

    return redirect(url_for("dashboard.dashboard"))


@uploads_bp.post("/reset")
def reset():
    token = session.pop("dataset_token", None)
    if token:
        dataset_cache.discard(token)
    # Limpia también cualquier upload pendiente del selector de hoja.
    pending = session.pop("pending_upload", None)
    if pending:
        with contextlib.suppress(OSError):
            Path(pending["path"]).unlink(missing_ok=True)
    clear_derived_cache()
    return redirect(url_for("dashboard.index"))
