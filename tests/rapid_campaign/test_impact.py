from __future__ import annotations

import pytest

from pneuma_lab.rapid_campaign.impact import ImpactError, classify_change


@pytest.mark.parametrize(
    ("domains", "level", "power", "required"),
    [
        ({"paper", "plot"}, "C0", False, {"analysis", "paper"}),
        ({"dashboard", "observer"}, "C1", False, {"campaign_control"}),
        ({"batch_wiring"}, "C2", False, {"provider_binding", "package", "authorization"}),
        ({"model", "packet"}, "C3", False, {"input_seals", "images", "sboms", "run_spec", "package", "authorization"}),
        ({"sample_size"}, "C4", True, {"power", "input_seals", "images", "sboms", "run_spec", "package", "authorization"}),
        ({"dashboard", "effect_target"}, "C4", True, {"power", "input_seals", "images", "sboms", "run_spec", "package", "authorization"}),
    ],
)
def test_change_classes_are_minimal_and_power_is_c4_only(domains, level, power, required) -> None:
    result = classify_change(domains)
    assert result.level == level
    assert result.rerun_power is power
    assert set(result.regenerate) == required


def test_unknown_domain_fails_closed() -> None:
    with pytest.raises(ImpactError, match="unknown"):
        classify_change({"mystery-knob"})

