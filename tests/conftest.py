"""Test bootstrap: make ``src/`` importable without an install.

``pyproject.toml`` sets ``pythonpath = ["src"]`` for pytest>=7, but we add the
path here too so ``python -m pytest`` and bare ``pytest`` both work regardless of
the installed pytest version.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
