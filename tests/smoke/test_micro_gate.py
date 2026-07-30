from __future__ import annotations

import importlib
import sys

from pneuma_lab.status import load_manifest, validate_manifest


def test_project_status_manifest_is_coherent() -> None:
    assert validate_manifest(load_manifest()) == []


def test_resampling_null_package_import_is_lazy_and_derives_seeds() -> None:
    package = importlib.import_module("pneuma_lab.resampling_null")

    assert "pneuma_lab.resampling_null.prefix_index" not in sys.modules
    assert "pneuma_lab.resampling_null.publication" not in sys.modules
    assert "pneuma_lab.resampling_null.storage" not in sys.modules
    assert package.derive_seed(7, "task-1", "prefix") == 15058118438168183076

    from pneuma_lab.resampling_null import Arm

    assert Arm.REAL.value == "REAL"
