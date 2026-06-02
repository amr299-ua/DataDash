# tests/test_cache_config.py
"""DATADASH_CACHE_TYPE permite cambiar el backend de Flask-Caching."""

from __future__ import annotations

import importlib
import os
from unittest import mock


def _fresh_create_app():
    import app as app_module
    import config as config_module

    importlib.reload(config_module)
    importlib.reload(app_module)
    return app_module.create_app


def test_default_backend_is_simple_cache():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DATADASH_CACHE_TYPE", None)
        create_app = _fresh_create_app()
        app = create_app()
        config = app.config["FLASK_CACHE_CONFIG"]
        assert config["CACHE_TYPE"] == "SimpleCache"


def test_filesystem_backend_via_env(tmp_path):
    env = {
        "DATADASH_CACHE_TYPE": "FileSystemCache",
        "DATADASH_CACHE_DIR": str(tmp_path / "ddcache"),
    }
    with mock.patch.dict(os.environ, env, clear=False):
        create_app = _fresh_create_app()
        app = create_app()
        config = app.config["FLASK_CACHE_CONFIG"]
        assert config["CACHE_TYPE"] == "FileSystemCache"
        assert config["CACHE_DIR"] == env["DATADASH_CACHE_DIR"]


def test_filesystem_cache_actually_persists_get_set(tmp_path):
    env = {
        "DATADASH_CACHE_TYPE": "FileSystemCache",
        "DATADASH_CACHE_DIR": str(tmp_path / "ddcache"),
    }
    with mock.patch.dict(os.environ, env, clear=False):
        create_app = _fresh_create_app()
        app = create_app()
        cache = app.config["FLASK_CACHE_INSTANCE"]
        with app.app_context():
            cache.set("foo", 42)
            assert cache.get("foo") == 42
