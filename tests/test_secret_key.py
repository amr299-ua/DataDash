# tests/test_secret_key.py
"""Garantiza que el SECRET_KEY no es el default en modo no-debug."""

from __future__ import annotations

import importlib
import os
from unittest import mock

import pytest


def _fresh_create_app():
    """Reimporta app/config para que Config.SECRET_KEY se reevalúe con el env actual."""
    import app as app_module
    import config as config_module

    importlib.reload(config_module)
    importlib.reload(app_module)
    return app_module.create_app


def test_create_app_aborts_when_secret_missing_in_production():
    env = {"DATADASH_ENV": "production"}
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("DATADASH_SECRET", None)
        create_app = _fresh_create_app()
        with pytest.raises(RuntimeError, match="DATADASH_SECRET"):
            create_app()


def test_create_app_works_with_explicit_secret_in_production():
    env = {"DATADASH_ENV": "production", "DATADASH_SECRET": "supersecret"}
    with mock.patch.dict(os.environ, env, clear=False):
        create_app = _fresh_create_app()
        app = create_app()
        assert app.config["SECRET_KEY"] == "supersecret"


def test_create_app_works_in_dev_with_default_secret():
    """En modo dev se permite el default para no romper el flujo local."""
    env = {"DATADASH_ENV": "development"}
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("DATADASH_SECRET", None)
        create_app = _fresh_create_app()
        app = create_app()
        assert app.config["SECRET_KEY"]  # cualquier valor no vacío
