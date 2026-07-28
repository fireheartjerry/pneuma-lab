"""The gauge card: schema validity, byte-stability, and the CLI contract."""

from __future__ import annotations

import json

import pytest

from pneuma_lab.gauge.card import (
    buildCard,
    cubeDigest,
    renderCard,
    validateCard,
    writeCard,
)
from pneuma_lab.gauge.synthetic import SyntheticSpec, syntheticCube
from pneuma_lab.schemas import GAUGE_SCHEMA_FILES, load_schema

COLLAPSED = SyntheticSpec(
    sd_item=0.005,
    sd_condition=0.05,
    sd_interaction=0.02,
    sd_error=0.15,
    sham_shift=0.05,
    name="collapsed",
)
GOOD = SyntheticSpec(
    sd_item=0.30,
    sd_condition=0.02,
    sd_interaction=0.01,
    sd_error=0.02,
    name="good_gauge",
)


def _card(spec: SyntheticSpec, **kw) -> dict:
    cube = syntheticCube(spec)
    truth = {item: (int(item[1:]) % 2) for item in cube.values("item_id")}
    return buildCard(
        cube,
        card_id=spec.name,
        condition_facets=("wording_id",),
        truth=truth,
        draws=kw.pop("draws", 150),
        **kw,
    )


def test_schema_is_registered_and_parses():
    assert "gauge-card.schema.json" in GAUGE_SCHEMA_FILES
    schema = load_schema("gauge-card.schema.json")
    assert schema["x-pneuma-schema-kind"] == "gauge_card"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_card_validates_against_the_schema():
    validateCard(_card(COLLAPSED))
    validateCard(_card(GOOD))


def test_card_reports_the_expected_verdicts():
    assert _card(COLLAPSED)["verdict"] == "UNINTERPRETABLE"
    assert _card(GOOD)["verdict"] == "USABLE"


def test_card_carries_every_remedy_including_skips():
    card = _card(COLLAPSED)
    names = [r["name"] for r in card["remedies"]]
    assert names == [
        "second_model",
        "thresholding",
        "calibration",
        "wording_averaging",
        "self_consistency",
    ]
    assert all(r["note"] for r in card["remedies"])


def test_card_is_json_serializable_despite_infinite_pi():
    card = _card(COLLAPSED)
    blob = json.dumps(card, allow_nan=False)
    assert "NaN" not in blob and "Infinity" not in blob


def test_card_is_byte_stable_across_rebuilds(tmp_path):
    first = writeCard(_card(COLLAPSED), tmp_path / "a.json").read_bytes()
    second = writeCard(_card(COLLAPSED), tmp_path / "b.json").read_bytes()
    assert first == second


def test_missing_required_section_fails_validation():
    import jsonschema

    card = _card(COLLAPSED)
    del card["remedies"]
    with pytest.raises(jsonschema.ValidationError):
        validateCard(card)


def test_unknown_verdict_fails_validation():
    import jsonschema

    card = _card(COLLAPSED)
    card["verdict"] = "PROBABLY_FINE"
    with pytest.raises(jsonschema.ValidationError):
        validateCard(card)


def test_markdown_rendering_contains_the_verdict_and_every_remedy():
    card = _card(COLLAPSED)
    text = renderCard(card)
    assert f"**Verdict: {card['verdict']}**" in text
    for remedy in card["remedies"]:
        assert remedy["name"] in text
        assert f"**{remedy['verdict']}**" in text
    assert "Placebo response" in text
    assert "placebo-dominance ratio" in text


def test_card_refuses_a_design_too_small_to_measure_repeatability():
    tiny = syntheticCube(
        SyntheticSpec(
            sd_item=0.1, sd_condition=0.1, sd_interaction=0.1, sd_error=0.1, n_reps=1
        )
    )
    with pytest.raises(ValueError, match="design too small"):
        buildCard(tiny, card_id="tiny", condition_facets=("wording_id",), draws=10)


def test_cube_digest_changes_with_the_data():
    a = syntheticCube(COLLAPSED, seed=1)
    b = syntheticCube(COLLAPSED, seed=2)
    assert cubeDigest(a) != cubeDigest(b)
    assert cubeDigest(a) == cubeDigest(syntheticCube(COLLAPSED, seed=1))


def test_ceilings_are_present_and_bound_validity():
    card = _card(COLLAPSED)
    ceil = card["ceilings"]
    assert 0.0 <= ceil["validity_r"] <= 1.0
    assert 0.5 <= ceil["auroc"] <= 1.0
    assert ceil["assumptions"]


# --------------------------------------------------------------------- CLI


def test_cli_selftest_exits_zero_offline(capsys):
    from pneuma_lab.gauge.__main__ import main

    assert main(["selftest"]) == 0
    assert "all gauges recovered their known verdict" in capsys.readouterr().out


def test_cli_analyze_gates_on_an_uninterpretable_channel(tmp_path):
    from pneuma_lab.gauge.__main__ import main
    from pneuma_lab.gauge.items import loadItems

    bank = loadItems()
    cube = syntheticCube(COLLAPSED)
    # Relabel synthetic items onto real bank ids so the truth join has something to do.
    rows = []
    ids = [i["item_id"] for i in bank]
    mapping = {f"i{n:03d}": ids[n % len(ids)] for n in range(48)}
    for r in cube.rows:
        rows.append(type(r)(**{**r.asDict(), "item_id": mapping[r.item_id]}))
    from pneuma_lab.gauge.cube import ResponseCube

    path = tmp_path / "cube.jsonl"
    ResponseCube(rows).toJsonl(path)

    code = main(["analyze", "--cube", str(path), "--out", str(tmp_path)])
    assert code == 2
    card = json.loads((tmp_path / "gauge_card.json").read_text(encoding="utf-8"))
    assert card["verdict"] in {"UNINTERPRETABLE", "DEGENERATE"}
    validateCard(card)
    assert (tmp_path / "gauge_card.md").exists()


def test_cli_dry_run_prints_the_plan(tmp_path, capsys):
    from pneuma_lab.gauge.__main__ import main

    config = {
        "out": str(tmp_path),
        "stages": [
            {
                "name": "tiny",
                "models": ["m"],
                "wordings": ["w1", "w2"],
                "scales": ["p2"],
                "replicates": 2,
                "items": 4,
            }
        ],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["run", "--config", str(path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "planned elicitations: 16" in out
    assert "tiny" in out


def test_cli_reports_errors_as_exit_one(tmp_path, capsys):
    from pneuma_lab.gauge.__main__ import main

    assert main(["analyze", "--cube", str(tmp_path / "nope.jsonl")]) == 1
    assert "error:" in capsys.readouterr().err
