# tests/test_reclassify.py
"""Override manual del tipo clasificado por columna."""

from __future__ import annotations

import pandas as pd
import pytest

from app import create_app
from core.cache import dataset_cache


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _seed(client) -> str:
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": ["a", "b", "a", "c"]})
    classification = {"numeric": ["x"], "categorical": ["y"], "temporal": [], "other": []}
    payload = {
        "df": df,
        "classification": classification,
        "overview": {"rows": 4, "columns": 2, "numeric_count": 1,
                     "categorical_count": 1, "temporal_count": 0, "other_count": 0,
                     "total_nulls": 0, "memory_mb": 0.001},
        "stats": [],
        "charts": [],
        "filter_options": {"categorical": [], "numeric": [], "temporal": []},
        "correlation": {"available": False, "columns": [], "matrix": []},
        "filename": "t.csv",
    }
    token = dataset_cache.put(payload)
    with client.session_transaction() as sess:
        sess["dataset_token"] = token
    return token


class TestReclassify:
    def test_moves_column_between_buckets(self, client):
        _seed(client)
        resp = client.post("/api/reclassify", json={"x": "categorical"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "x" in data["classification"]["categorical"]
        assert "x" not in data["classification"]["numeric"]

    def test_unknown_column_is_ignored(self, client):
        _seed(client)
        resp = client.post("/api/reclassify", json={"no-existe": "categorical"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["classification"]["numeric"] == ["x"]
        assert data["classification"]["categorical"] == ["y"]

    def test_invalid_target_type_is_ignored(self, client):
        _seed(client)
        resp = client.post("/api/reclassify", json={"x": "invalid-type"})
        assert resp.status_code == 200
        data = resp.get_json()
        # x permanece en numeric (target inválido).
        assert "x" in data["classification"]["numeric"]

    def test_returns_recomputed_derivations(self, client):
        _seed(client)
        resp = client.post("/api/reclassify", json={"x": "categorical"})
        data = resp.get_json()
        assert "overview" in data
        assert "stats" in data
        assert "charts" in data
        assert "correlation" in data
        assert "filter_options" in data

    def test_404_without_session(self, client):
        resp = client.post("/api/reclassify", json={"x": "categorical"})
        assert resp.status_code == 404

    def test_400_for_non_dict_body(self, client):
        _seed(client)
        resp = client.post("/api/reclassify", json=["not", "a", "dict"])
        assert resp.status_code == 400
