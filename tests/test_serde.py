# tests/test_serde.py
"""Tests para utilidades de serialización JSON-safe."""

from __future__ import annotations

import math

import numpy as np

from core._serde import safe_round


class TestSafeRound:
    def test_returns_none_for_none(self):
        assert safe_round(None) is None

    def test_returns_none_for_nan(self):
        assert safe_round(float("nan")) is None

    def test_returns_none_for_inf(self):
        assert safe_round(math.inf) is None
        assert safe_round(-math.inf) is None

    def test_returns_none_for_numpy_nan(self):
        assert safe_round(np.nan) is None

    def test_rounds_to_4_decimals_by_default(self):
        assert safe_round(1.234567) == 1.2346

    def test_respects_custom_ndigits(self):
        assert safe_round(1.234567, ndigits=2) == 1.23

    def test_returns_none_for_unparseable(self):
        assert safe_round("not-a-number") is None

    def test_passes_through_integer(self):
        assert safe_round(5) == 5.0
