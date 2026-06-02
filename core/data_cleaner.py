# core/data_cleaner.py
"""Limpieza ligera: normaliza nulos, elimina columnas vacías."""

from __future__ import annotations

import numpy as np
import pandas as pd

_NULL_TOKENS = {
    "",
    "NULL",
    "null",
    "NaN",
    "nan",
    "N/A",
    "n/a",
    "NA",
    "na",
    "None",
    "none",
    "-",
    "--",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve un DataFrame limpio: nulos normalizados, columnas vacías eliminadas.

    No muta `df`. Las operaciones se hacen vectorizadas.
    """
    df = df.copy()

    # Normaliza nombres de columnas: strip de espacios.
    df.columns = [str(c).strip() for c in df.columns]

    # Strip + reemplazo vectorizado de tokens nulos en columnas tipo object.
    obj_cols = df.select_dtypes(include=["object"]).columns
    for col in obj_cols:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].mask(df[col].isin(_NULL_TOKENS), other=pd.NA)

    # Reemplaza valores NA pandas por np.nan para uniformidad downstream.
    df = df.replace({pd.NA: np.nan})

    # Elimina columnas completamente vacías y filas completamente vacías.
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    df = df.reset_index(drop=True)

    return df
