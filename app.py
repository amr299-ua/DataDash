# app.py
"""Punto de entrada Flask. Factory pattern, blueprints, error handlers."""
from __future__ import annotations

import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_caching import Cache

from config import DEV_DEFAULT_SECRET, Config


# Cache global compartido entre blueprints. Backend SimpleCache (en memoria);
# no se persiste a disco — coherente con la política "sin base de datos".
cache = Cache(config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 600,  # 10 minutos para derivaciones de filtros
    "CACHE_THRESHOLD": 500,        # cap aproximado de entradas antes de evict
})


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    env = os.environ.get("DATADASH_ENV", "development").lower()
    if env == "production" and app.config["SECRET_KEY"] == DEV_DEFAULT_SECRET:
        raise RuntimeError(
            "DATADASH_SECRET no está definido y DATADASH_ENV=production. "
            "Exporta DATADASH_SECRET con un valor aleatorio antes de arrancar."
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Flask-Caching: inicializa el SimpleCache y lo deja accesible para las rutas.
    cache.init_app(app)
    app.config["FLASK_CACHE_INSTANCE"] = cache

    # Importes diferidos para evitar import circular con blueprints que usan config.
    from routes.api import api_bp
    from routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    _register_error_handlers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(413)
    def too_large(_err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "El archivo supera el límite de 50 MB."}), 413
        flash("El archivo supera el límite de 50 MB.", "danger")
        return redirect(url_for("main.index"))

    @app.errorhandler(404)
    def not_found(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(err.description or "Not found")}), 404
        return render_template("error.html", code=404, message="Página no encontrada."), 404

    @app.errorhandler(410)
    def gone(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(err.description or "Gone")}), 410
        return render_template("error.html", code=410, message="Recurso expirado."), 410

    @app.errorhandler(500)
    def server_error(err):
        app.logger.exception("Unhandled 500: %s", err)
        if request.path.startswith("/api/"):
            return jsonify({"error": "Error interno del servidor."}), 500
        return render_template("error.html", code=500, message="Error interno del servidor."), 500


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
