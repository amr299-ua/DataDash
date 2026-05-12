# config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("DATADASH_SECRET", "dev-secret-change-me")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {"csv"}
    DATASET_TTL_SECONDS = 3600  # 1 hora de inactividad antes de expirar
    MAX_CHARTS = 12
    DEFAULT_PAGE_SIZE = 25
    JSON_SORT_KEYS = False
