# core/data_loader.py
"""Carga de CSV con sniffing de delimitador y downcast de tipos numéricos."""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)

_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")
_DELIM_CANDIDATES = ",;\t|"


class CSVLoadError(Exception):
    """Error legible para el usuario al cargar un CSV."""


def _read_sample(path: Path, n_bytes: int = 16384) -> Tuple[str, str]:
    """Lee una muestra del archivo probando codificaciones comunes."""
    last_exc: Exception | None = None
    for encoding in _ENCODINGS:
        try:
            with open(path, "r", encoding=encoding) as f:
                sample = f.read(n_bytes)
            return sample, encoding
        except UnicodeDecodeError as exc:
            last_exc = exc
            continue
    raise CSVLoadError(
        "No se pudo decodificar el archivo con codificaciones comunes (utf-8, latin-1, cp1252)."
    ) from last_exc


def _sniff_delimiter(sample: str) -> str:
    """Detecta el delimitador. Usa csv.Sniffer y cae en heurística si falla."""
    if not sample.strip():
        raise CSVLoadError("El archivo está vacío o solo contiene espacios en blanco.")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_DELIM_CANDIDATES)
        return dialect.delimiter
    except csv.Error:
        first_line = sample.split("\n", 1)[0]
        counts = {d: first_line.count(d) for d in _DELIM_CANDIDATES}
        best = max(counts, key=counts.get)
        if counts[best] == 0:
            return ","
        return best


def load_csv(path: Path) -> pd.DataFrame:
    """Carga el CSV ubicado en `path`. Lanza CSVLoadError en caso de fallo."""
    path = Path(path)
    if not path.exists():
        raise CSVLoadError(f"Archivo no encontrado: {path}")
    if path.stat().st_size == 0:
        raise CSVLoadError("El archivo está vacío.")

    sample, encoding = _read_sample(path)
    delimiter = _sniff_delimiter(sample)
    logger.info("CSV %s — delimiter=%r encoding=%s", path.name, delimiter, encoding)

    try:
        df = pd.read_csv(
            path,
            sep=delimiter,
            encoding=encoding,
            engine="c",
            low_memory=False,
            skip_blank_lines=True,
            on_bad_lines="skip",
        )
    except pd.errors.EmptyDataError as exc:
        raise CSVLoadError("El archivo no contiene columnas analizables.") from exc
    except pd.errors.ParserError as exc:
        raise CSVLoadError(f"Error de parseo del CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise CSVLoadError("Error de codificación al leer el archivo.") from exc

    if df.empty or df.shape[1] == 0:
        raise CSVLoadError("El CSV se leyó pero no contiene datos analizables.")

    return df


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica downcast vectorizado a columnas numéricas para reducir memoria."""
    for col in df.select_dtypes(include=["integer"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")
    for col in df.select_dtypes(include=["floating"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")
    return df
