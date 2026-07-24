"""Test bootstrap: make ``src/`` importable without an install.

``pyproject.toml`` sets ``pythonpath = ["src"]`` for pytest>=7, but we add the
path here too so ``python -m pytest`` and bare ``pytest`` both work regardless of
the installed pytest version.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Fast-by-default test selection.
#
# The `foundation` local-Qwen program is ~52% of the suite, filesystem-heavy,
# and not imported by the NeurIPS paper. We auto-tag its tests with the
# `foundation` marker (registered in pyproject.toml) purely by filename, so the
# default `addopts` deselection keeps the daily loop fast without hand-annotating
# 44 files. New paper test files match nothing here and stay in the fast loop.
# ---------------------------------------------------------------------------
_FOUNDATION_PREFIX = "test_foundation_"

# Windows CRLF / committed-shard-digest quarantine. On a native Windows checkout
# the foundation shard fixtures are stored/read with CRLF, so their recomputed
# sha256 no longer matches the manifest and `FoundationDatasetError: shard hash
# does not match manifest` is raised (src/pneuma_lab/foundation/dataset.py). This
# is an environment artifact, not a scientific regression (the same code passes
# on LF/WSL). We xfail *only* that specific exception in the three affected files,
# so any other (genuine) failure in them still surfaces as a real failure.
_CRLF_XFAIL_FILES = {
    "test_foundation_runner.py",
    "test_foundation_runner_failures.py",
    "test_foundation_validation_batches.py",
    "test_foundation_variants.py",
}


def _crlf_shard_exc():
    """Lazily resolve FoundationDatasetError on Windows; None elsewhere/on error."""
    if os.name != "nt":
        return None
    try:
        from pneuma_lab.foundation.dataset import FoundationDatasetError
    except Exception:
        return None
    return FoundationDatasetError


def pytest_collection_modifyitems(config, items):
    crlf_exc = _crlf_shard_exc()
    for item in items:
        name = Path(str(item.fspath)).name
        if not name.startswith(_FOUNDATION_PREFIX):
            continue
        item.add_marker("foundation")
        if crlf_exc is not None and name in _CRLF_XFAIL_FILES:
            item.add_marker(
                pytest.mark.xfail(
                    reason="Windows CRLF/shard-digest env artifact, not a regression",
                    raises=crlf_exc,
                    strict=False,
                )
            )
