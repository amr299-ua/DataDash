# tests/test_custom_chart.py
"""POST /api/chart/custom — gráficos personalizados."""

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
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [10, 20, 15, 25],
            "cat": ["a", "b", "a", "b"],
        }
    )
    payload = {
        "df": df,
        "classification": {
            "numeric": ["x", "y"],
            "categorical": ["cat"],
            "temporal": [],
            "other": [],
        },
        "overview": {},
        "stats": [],
        "charts": [],
        "filter_options": {},
        "correlation": {},
        "filename": "t.csv",
    }
    token = dataset_cache.put(payload)
    with client.session_transaction() as sess:
        sess["dataset_token"] = token
    return token


class TestCustomChart:
    def test_scatter(self, client):
        _seed(client)
        resp = client.post("/api/chart/custom", json={"type": "scatter", "x": "x", "y": "y"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "scatter"
        first = data["data"]["datasets"][0]["data"][0]
        assert first == {"x": 1.0, "y": 10.0}

    def test_bar_groups_by_x(self, client):
        _seed(client)
        resp = client.post("/api/chart/custom", json={"type": "bar", "x": "cat", "y": "y"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["type"] == "bar"
        labels = data["data"]["labels"]
        assert set(labels) == {"a", "b"}

    def test_line(self, client):
        _seed(client)
        resp = client.post("/api/chart/custom", json={"type": "line", "x": "x", "y": "y"})
        assert resp.status_code == 200
        assert resp.get_json()["type"] == "line"

    def test_invalid_type(self, client):
        _seed(client)
        resp = client.post("/api/chart/custom", json={"type": "pie", "x": "x", "y": "y"})
        assert resp.status_code == 400

    def test_unknown_column(self, client):
        _seed(client)
        resp = client.post(
            "/api/chart/custom", json={"type": "scatter", "x": "x", "y": "no-existe"}
        )
        assert resp.status_code == 400

    def test_scatter_requires_numeric_columns(self, client):
        _seed(client)
        resp = client.post("/api/chart/custom", json={"type": "scatter", "x": "cat", "y": "y"})
        assert resp.status_code == 400

    def test_no_session_returns_404(self, client):
        resp = client.post("/api/chart/custom", json={"type": "scatter", "x": "x", "y": "y"})
        assert resp.status_code == 404
