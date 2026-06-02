# tests/test_sheet_picker.py
"""Detección y selección de hojas en archivos Excel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.data_loader import CSVLoadError
from core.sheet_picker import list_sheets, load_sheet


def _make_workbook(tmp_path: Path) -> Path:
    p = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        pd.DataFrame({"a": [1, 2]}).to_excel(w, sheet_name="Ventas", index=False)
        pd.DataFrame({"b": [3, 4]}).to_excel(w, sheet_name="Clientes", index=False)
    return p


class TestSheetPicker:
    def test_list_sheets_returns_all(self, tmp_path):
        p = _make_workbook(tmp_path)
        assert list_sheets(p) == ["Ventas", "Clientes"]

    def test_load_sheet_by_name(self, tmp_path):
        p = _make_workbook(tmp_path)
        df = load_sheet(p, "Clientes")
        assert list(df.columns) == ["b"]

    def test_load_sheet_default_first(self, tmp_path):
        p = _make_workbook(tmp_path)
        df = load_sheet(p, None)
        assert list(df.columns) == ["a"]

    def test_unknown_sheet_raises(self, tmp_path):
        p = _make_workbook(tmp_path)
        with pytest.raises(CSVLoadError, match="no encontrada"):
            load_sheet(p, "Inexistente")

    def test_list_sheets_corrupted_file_raises(self, tmp_path):
        p = tmp_path / "broken.xlsx"
        p.write_bytes(b"not really an xlsx")
        with pytest.raises(CSVLoadError):
            list_sheets(p)


# ----------------------- flujo integrado -----------------------

class TestSheetPickerFlow:
    """Excel con varias hojas debe pasar por /upload/sheet antes del dashboard."""

    def _client(self, tmp_path):
        from app import create_app
        app = create_app()
        app.config["TESTING"] = True
        app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
        return app, app.test_client()

    def _multi_sheet_bytes(self, tmp_path):
        path = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            pd.DataFrame({"a": [1, 2, 3]}).to_excel(w, sheet_name="Ventas", index=False)
            pd.DataFrame({"b": [4, 5, 6]}).to_excel(w, sheet_name="Clientes", index=False)
        return path.read_bytes()

    def test_multi_sheet_upload_redirects_to_picker(self, tmp_path):
        import io as _io
        _, client = self._client(tmp_path)
        body = self._multi_sheet_bytes(tmp_path)
        r = client.post(
            "/upload",
            data={"file": (_io.BytesIO(body), "multi.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert r.status_code in (302, 303)
        assert r.location.endswith("/upload/sheet")

    def test_choose_sheet_renders_options(self, tmp_path):
        import io as _io
        _, client = self._client(tmp_path)
        body = self._multi_sheet_bytes(tmp_path)
        client.post(
            "/upload",
            data={"file": (_io.BytesIO(body), "multi.xlsx")},
            content_type="multipart/form-data",
        )
        r = client.get("/upload/sheet")
        assert r.status_code == 200
        assert b"Ventas" in r.data
        assert b"Clientes" in r.data

    def test_process_sheet_finalises_dataset(self, tmp_path):
        import io as _io
        _, client = self._client(tmp_path)
        body = self._multi_sheet_bytes(tmp_path)
        client.post(
            "/upload",
            data={"file": (_io.BytesIO(body), "multi.xlsx")},
            content_type="multipart/form-data",
        )
        r = client.post("/upload/sheet", data={"sheet": "Clientes"}, follow_redirects=False)
        assert r.status_code in (302, 303)
        assert r.location.endswith("/dashboard")
        with client.session_transaction() as sess:
            assert "dataset_token" in sess
            assert "pending_upload" not in sess

    def test_single_sheet_excel_skips_picker(self, tmp_path):
        import io as _io
        _, client = self._client(tmp_path)
        path = tmp_path / "one.xlsx"
        pd.DataFrame({"x": [1, 2, 3]}).to_excel(path, index=False, engine="openpyxl")
        r = client.post(
            "/upload",
            data={"file": (_io.BytesIO(path.read_bytes()), "one.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert r.status_code in (302, 303)
        assert r.location.endswith("/dashboard")
