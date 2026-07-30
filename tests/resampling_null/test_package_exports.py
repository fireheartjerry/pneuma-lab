from __future__ import annotations

import importlib

import pytest


def test_lazy_export_table_is_immutable_and_preserves_resolution() -> None:
    package = importlib.import_module("pneuma_lab.resampling_null")

    with pytest.raises(TypeError):
        package._LAZY_EXPORTS["Arm"] = ("types", "Treatment")

    assert package.Arm.REAL.value == "REAL"
