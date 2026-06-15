from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ML_DIR = BACKEND_DIR.parent / "ml"

for path in (BACKEND_DIR, ML_DIR):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
