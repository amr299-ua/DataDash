# core/sheet_picker.py
"""Selección de hoja en archivos Excel.

Permite enumerar las hojas disponibles antes de cargar el dataset, y leer una
hoja concreta por nombre. Mantiene el mismo error legible (CSVLoadError) que
el resto del pipeline para que las rutas no tengan que distinguir orígenes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.data_loader import CSVLoadError


def list_sheets(path: Path) -> list[str]:
    """Devuelve los nombres de las hojas del workbook (orden original)."""
    try:
        return list(pd.ExcelFile(path, engine="openpyxl").sheet_names)
    except Exception as exc:  # noqa: BLE001 — openpyxl/zip pueden lanzar varias.
        raise CSVLoadError(f"No se pudieron listar las hojas del Excel: {exc}") from exc


def load_sheet(path: Path, sheet: str | None) -> pd.DataFrame:
    """Lee una hoja concreta del Excel; si `sheet` es None, lee la primera."""
    try:
        if sheet is None:
            return pd.read_excel(path, engine="openpyxl", sheet_name=0)
        return pd.read_excel(path, engine="openpyxl", sheet_name=sheet)
    except ValueError as exc:
        raise CSVLoadError(f"Hoja '{sheet}' no encontrada en el archivo.") from exc
