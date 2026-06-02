# routes/downloads.py
"""Descargas del dataset procesado (CSV/JSON)."""

from __future__ import annotations

import io
import json

from flask import Blueprint, Response, send_file

from routes._helpers import active_payload_or_404, processed_stem

downloads_bp = Blueprint("downloads", __name__)


@downloads_bp.get("/download/csv")
def download_csv():
    payload = active_payload_or_404()
    df = payload["df"]
    # BytesIO con UTF-8 BOM para que Excel abra acentos sin desconfiguraciones.
    buf = io.BytesIO()
    buf.write("﻿".encode())
    df.to_csv(buf, index=False, encoding="utf-8")
    buf.seek(0)
    filename = processed_stem(payload.get("filename", "dataset")) + ".csv"
    # send_file añade charset automáticamente para mimetypes text/*, así que
    # pasamos sólo el tipo base para evitar `charset=utf-8; charset=utf-8`.
    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@downloads_bp.get("/download/json")
def download_json():
    payload = active_payload_or_404()
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
    wrapper = '{"meta":' + json.dumps(meta, ensure_ascii=False) + ',"data":' + body + "}"
    filename = processed_stem(payload.get("filename", "dataset")) + ".json"
    return Response(
        wrapper,
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
