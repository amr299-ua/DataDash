# tests/test_cache_alignment.py
"""El TTL de Flask-Caching debe coincidir con el del dataset principal."""

from __future__ import annotations


def test_flask_cache_ttl_matches_dataset_ttl():
    from app import create_app
    from config import Config

    app = create_app()
    cache = app.config["FLASK_CACHE_INSTANCE"]
    # SimpleCache guarda `default_timeout` directamente.
    assert cache.cache.default_timeout == Config.DATASET_TTL_SECONDS
