# tests/test_main_routes.py
"""Tests de integración para los endpoints en routes/main.py."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app()
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    with app.test_client() as c:
        yield c


class TestIndex:
    def test_get_index_returns_200_with_form(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"upload-form" in resp.data


class TestUpload:
    CSV = b"col1,col2\nx,1\ny,2\nz,3\n"

    def test_happy_path_redirects_to_dashboard(self, client):
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(self.CSV), "data.csv")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/dashboard")

    def test_no_file_redirects_to_index(self, client):
        resp = client.post("/upload", data={}, follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/")

    def test_empty_filename_redirects(self, client):
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(b""), "")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)

    def test_rejected_extension(self, client):
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(b"abc"), "data.txt")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/")

    def test_corrupted_excel_redirects_to_index(self, client):
        garbage = b"not actually an xlsx file"
        resp = client.post(
            "/upload",
            data={"file": (io.BytesIO(garbage), "broken.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/")

    def test_upload_deletes_temp_file(self, client, tmp_path):
        client.post(
            "/upload",
            data={"file": (io.BytesIO(self.CSV), "data.csv")},
            content_type="multipart/form-data",
        )
        residuals = list(Path(tmp_path).glob("__tmp_*"))
        assert residuals == []

    def test_upload_sets_dataset_token(self, client):
        client.post(
            "/upload",
            data={"file": (io.BytesIO(self.CSV), "data.csv")},
            content_type="multipart/form-data",
        )
        with client.session_transaction() as sess:
            assert "dataset_token" in sess


class TestDashboard:
    def test_redirects_when_no_dataset(self, client):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert resp.location.endswith("/")

    def test_renders_after_upload(self, client):
        client.post(
            "/upload",
            data={"file": (io.BytesIO(b"a,b\n1,2\n3,4\n"), "small.csv")},
            content_type="multipart/form-data",
        )
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        # KPI rows visibles.
        assert b"kpi-rows" in resp.data

    def test_expired_token_redirects(self, client):
        # Token inventado que el DatasetCache no conoce.
        with client.session_transaction() as sess:
            sess["dataset_token"] = "no-such-token"
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)
        with client.session_transaction() as sess:
            assert "dataset_token" not in sess


class TestReset:
    def test_reset_clears_session_and_redirects(self, client):
        with client.session_transaction() as sess:
            sess["dataset_token"] = "abc"
        resp = client.post("/reset", follow_redirects=False)
        assert resp.status_code in (302, 303)
        with client.session_transaction() as sess:
            assert "dataset_token" not in sess

    def test_reset_without_token_still_redirects(self, client):
        resp = client.post("/reset", follow_redirects=False)
        assert resp.status_code in (302, 303)
