# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEV_DEFAULT_SECRET = "dev-secret-change-me"


class Config:
    SECRET_KEY = os.environ.get("DATADASH_SECRET", DEV_DEFAULT_SECRET)
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx"}
    DATASET_TTL_SECONDS = 3600  # 1 hora de inactividad antes de expirar
    MAX_CHARTS = 12
    DEFAULT_PAGE_SIZE = 25
    JSON_SORT_KEYS = False

    # Configuración para Flask-Caching. El TTL coincide con DATASET_TTL_SECONDS
    # para que el cache de derivaciones no expire antes que el propio dataset.
    # Backend configurable por env: DATADASH_CACHE_TYPE (default: SimpleCache).
    # Para deploys con varios workers usar FileSystemCache + DATADASH_CACHE_DIR.
    FLASK_CACHE_CONFIG = {
        "CACHE_TYPE": os.environ.get("DATADASH_CACHE_TYPE", "SimpleCache"),
        "CACHE_DEFAULT_TIMEOUT": DATASET_TTL_SECONDS,
        "CACHE_THRESHOLD": 500,
        "CACHE_DIR": os.environ.get("DATADASH_CACHE_DIR", str(BASE_DIR / "cache")),
    }
