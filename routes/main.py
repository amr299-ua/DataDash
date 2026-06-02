# routes/main.py
"""Rutas de cara al usuario: upload y dashboard."""
from __future__ import annotations

import io
import json
import logging
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
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
        flash("Selecciona un archivo CSV o Excel antes de continuar.", "danger")
        return redirect(url_for("main.index"))

    filename = secure_filename(file.filename) or "dataset.csv"
    lower = filename.lower()
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    extension = lower.rsplit(".", 1)[-1] if "." in lower else ""
    if extension not in allowed:
        flash("Solo se aceptan archivos .csv o .xlsx.", "danger")
        return redirect(url_for("main.index"))

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
    filter_options = available_filters(df, classification)
    correlation = correlation_matrix(df, classification["numeric"])

    # Si ya había un dataset previo en sesión, lo desechamos y purgamos la caché
    # de derivaciones (claves indexadas por token previo).
    previous_token = session.get("dataset_token")
    if previous_token:
        dataset_cache.discard(previous_token)
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE")
    if flask_cache is not None:
        try:
            flask_cache.clear()
        except Exception:  # noqa: BLE001
            logger.warning("No se pudo limpiar Flask-Caching tras nuevo upload.")

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
        filter_options=payload.get("filter_options", {"categorical": [], "numeric": [], "temporal": []}),
        correlation=payload.get("correlation", {"available": False, "columns": [], "matrix": []}),
    )


@main_bp.post("/reset")
def reset():
    token = session.pop("dataset_token", None)
    if token:
        dataset_cache.discard(token)
    flask_cache = current_app.config.get("FLASK_CACHE_INSTANCE")
    if flask_cache is not None:
        try:
            flask_cache.clear()
        except Exception:  # noqa: BLE001
            logger.warning("No se pudo limpiar Flask-Caching en reset.")
    return redirect(url_for("main.index"))


# ----------------------------------------------------------------------
# Descargas del dataset procesado (CSV/JSON)
# ----------------------------------------------------------------------

def _active_payload_or_404():
    token = session.get("dataset_token")
    if not token:
        abort(404, description="No hay dataset activo.")
    payload = dataset_cache.get(token)
    if payload is None:
        abort(410, description="El dataset ha expirado.")
    return payload


def _processed_stem(original: str) -> str:
    """Deriva un nombre amigable: 'ventas.xlsx' → 'ventas_cleaned'."""
    base = secure_filename(original or "dataset") or "dataset"
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return f"{stem}_cleaned"


@main_bp.get("/download/csv")
def download_csv():
    payload = _active_payload_or_404()
    df = payload["df"]
    # BytesIO con UTF-8 BOM para que Excel abra acentos sin desconfiguraciones.
    buf = io.BytesIO()
    buf.write("﻿".encode("utf-8"))
    df.to_csv(buf, index=False, encoding="utf-8")
    buf.seek(0)
    filename = _processed_stem(payload.get("filename", "dataset")) + ".csv"
    # send_file añade charset automáticamente para mimetypes text/*, así que
    # pasamos sólo el tipo base para evitar `charset=utf-8; charset=utf-8`.
    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@main_bp.get("/download/json")
def download_json():
    payload = _active_payload_or_404()
    df = payload["df"]
    # to_json maneja fechas y NaN correctamente; usamos orient=records para una
    # estructura amigable al consumir el archivo en otras herramientas.
    body = df.to_json(orient="records", date_format="iso", force_ascii=False)
    # Envolvemos en {data: [...], meta: {...}} para incluir contexto de procesado.
    meta = {
        "filename": payload.get("filename"),
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "classification": payload.get("classification", {}),
    }
    wrapper = '{"meta":' + json.dumps(meta, ensure_ascii=False) + ',"data":' + body + '}'
    filename = _processed_stem(payload.get("filename", "dataset")) + ".json"
    return Response(
        wrapper,
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
