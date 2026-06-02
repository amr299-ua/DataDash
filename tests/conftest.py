# tests/conftest.py
"""Configuración común de pytest. Añade la raíz del proyecto al sys.path para
que los tests puedan importar `core.*` sin instalar el paquete.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
