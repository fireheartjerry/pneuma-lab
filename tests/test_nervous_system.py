"""Tests for PneumaNervousSystem-v0: the shadow-mode model-backed I/O shell.

Covers schema validity, deterministic shadow outputs, no runtime authority
change, no verifier bypass, complete CausalTrace references, the
intervention/null ablation, honest (non-overclaiming) evidence, kill-switch
suppression, and import hygiene.
"""

import json
import subprocess
import sys
from pathlib import Path

from pneuma_lab import schemas
from pneuma_lab.brain import predict as brain_predict
from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system"


def _load_trace(path):
    return json.loads(Path(path).read_text(encoding="utf-8").strip())


# --------------------------------------------------------------------------- #
# Task 1: RiskEstimateFrame schema                                            #
# --------------------------------------------------------------------------- #
def test_risk_estimate_schema_registered_and_loads():
    all_schemas = schemas.load_all_schemas()
    assert "risk-estimate-frame.schema.json" in all_schemas
    assert (
        validate.FRAME_KIND_TO_SCHEMA["risk_estimate"]
        == "risk-estimate-frame.schema.json"
    )
    frame = {
        "schema_version": "0.1.0",
        "frame_kind": "risk_estimate",
        "timestamp": "2026-07-10T00:00:00Z",
        "run_id": "r0",
        "model_id": "PneumaBrain-v0.1",
        "model_version": "pneuma-brain/0.1.0",
        "prefix": "full",
        "failure_probability": 0.7,
        "success_probability": 0.3,
        "raw_score": 0.8,
        "risk_bucket": "high",
        "recommended_use": "advisory_only",
        "authority_granted": "none",
        "blocked_uses": ["no_runtime_authority"],
        "features_digest": "sha256:ab",
        "causal_trace_id": None,
    }
    validate.validate_or_raise(frame)


# --------------------------------------------------------------------------- #
# Task 2: bundle schemas + validator                                          #
# --------------------------------------------------------------------------- #
def test_bundles_load_and_validate():
    all_schemas = schemas.load_all_schemas()
    assert "pneuma-input-bundle.schema.json" in all_schemas
    assert "pneuma-output-bundle.schema.json" in all_schemas
    out_bundle = {
        "schema_version": "0.1.0",
        "bundle_kind": "pneuma_output",
        "run_id": "r0",
        "timestamp": "2026-07-10T00:00:00Z",
        "governance_status": "emitted",
        "risk_estimate": None,
        "instinct": None,
        "control_pressure": None,
        "causal_trace": None,
        "consciousness_evidence": None,
        "blocked_uses": ["no_runtime_authority"],
        "limitations": ["shadow_mode"],
    }
    validate.validate_bundle(out_bundle)


# --------------------------------------------------------------------------- #
# Task 3: hermetic fixtures                                                    #
# --------------------------------------------------------------------------- #
def test_fixture_model_gives_high_and_low_risk():
    model = brain_predict.load_model(FIX / "model.json")
    high = brain_predict.risk_estimate(
        model, _load_trace(FIX / "trace_high_risk.jsonl"), prefix="full"
    )
    low = brain_predict.risk_estimate(
        model, _load_trace(FIX / "trace_low_risk.jsonl"), prefix="full"
    )
    assert high["failure_probability"] > low["failure_probability"]
    assert high["risk_bucket"] == "high"
    assert low["risk_bucket"] == "low"


def test_fixture_governance_frames_valid():
    for name in ("governance_on.json", "governance_killswitch_off.json"):
        validate.validate_or_raise(json.loads((FIX / name).read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# Task 4: pure frame builders                                                 #
# --------------------------------------------------------------------------- #
BRAIN_DICT = {
    "frame_type": "RiskEstimateFrame",
    "task_type": "RISK_PREDICTION",
    "failure_probability": 0.8,
    "success_probability": 0.2,
    "raw_score": 1.2,
    "risk_bucket": "high",
    "prefix": "full",
    "model_version": "pneuma-brain/0.1.0",
    "recommended_use": "advisory_only",
    "blocked_uses": [
        "no_runtime_authority",
        "no_verifier_bypass",
        "no_consciousness_claim",
    ],
}
GOV = {"authority_ceilings": {"global_max": "hold"}}


def test_frame_builders_produce_valid_linked_frames():
    from pneuma_lab.nervous_system import frames as nsf

    ts = "2026-07-10T00:00:00Z"
    trace = nsf.causal_trace(
        run_id="r0",
        timestamp=ts,
        input_ref="agent_trace:r0:full",
        risk_ref="risk_estimate:r0:full",
        pressure_ref="control_pressure:r0:full",
        instinct_ref="instinct:r0:full",
        failure_probability=0.8,
    )
    risk = nsf.risk_estimate_frame(
        BRAIN_DICT,
        run_id="r0",
        timestamp=ts,
        features_digest="sha256:aa",
        causal_trace_id=trace["trace_id"],
    )
    instinct = nsf.instinct_signal(
        BRAIN_DICT, run_id="r0", timestamp=ts, trace_id=trace["trace_id"]
    )
    pressure = nsf.control_pressure_candidate(
        BRAIN_DICT, GOV, run_id="r0", timestamp=ts, causal_trace_id=trace["trace_id"]
    )
    for fr in (risk, instinct, pressure, trace):
        validate.validate_or_raise(fr)
    assert risk["authority_granted"] == "none"
    assert pressure["authority_tier"] in ("cosmetic", "soft")
    assert pressure["pressures"]["verification"] == 0.8
    assert pressure["pressures"]["verification"] >= 0.0
    assert set(pressure["pressures"]) == {"verification"}
    stages = [n["stage"] for n in trace["causal_path"]]
    assert stages == ["event", "internal_state", "pressure"]


def test_frame_builders_are_deterministic():
    from pneuma_lab.nervous_system import frames as nsf

    ts = "2026-07-10T00:00:00Z"
    a = nsf.risk_estimate_frame(
        BRAIN_DICT,
        run_id="r0",
        timestamp=ts,
        features_digest="sha256:aa",
        causal_trace_id=None,
    )
    b = nsf.risk_estimate_frame(
        BRAIN_DICT,
        run_id="r0",
        timestamp=ts,
        features_digest="sha256:aa",
        causal_trace_id=None,
    )
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --------------------------------------------------------------------------- #
# Task 5: conservative evidence builder                                       #
# --------------------------------------------------------------------------- #
def test_shadow_evidence_does_not_overclaim():
    from pneuma_lab.nervous_system import shadow_evidence as nse

    ablation = {
        "observed_delta": -0.8,
        "null_delta": 0.0,
        "direction_ok": True,
        "null_holds": True,
    }
    frame = nse.shadow_evidence_frame(
        ablation_result=ablation, run_id="r0", timestamp="2026-07-10T00:00:00Z"
    )
    validate.validate_or_raise(frame)
    assert frame["evidence_level"] <= 1
    assert frame["real_subject_claim_status"] == "not_evaluated"
    assert frame["evaluation_scope"] == "internal_harness"
    fam = frame["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] != "intervention_backed"
    assert frame["paired_replay_provenance"]["status"] == "uncertified_subject"
    assert frame["audit_status"] == "self_reported"


def test_shadow_evidence_level_zero_when_ablation_fails():
    from pneuma_lab.nervous_system import shadow_evidence as nse

    ablation = {
        "observed_delta": 0.0,
        "null_delta": 0.0,
        "direction_ok": False,
        "null_holds": True,
    }
    frame = nse.shadow_evidence_frame(
        ablation_result=ablation, run_id="r0", timestamp="2026-07-10T00:00:00Z"
    )
    validate.validate_or_raise(frame)
    assert frame["evidence_level"] == 0


# --------------------------------------------------------------------------- #
# Task 6: ShadowNervousSystem runtime + kill switch + shadow log              #
# --------------------------------------------------------------------------- #
def _model():
    return brain_predict.load_model(FIX / "model.json")


def _gov(name="governance_on.json"):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_runtime_emits_valid_bundle_and_is_deterministic(tmp_path):
    from pneuma_lab.nervous_system import ShadowNervousSystem

    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    sys_a = ShadowNervousSystem(_model(), shadow_log_path=tmp_path / "log_a.jsonl")
    bundles_1 = sys_a.run_trace(trace, _gov(), prefixes=("full",))
    for b in bundles_1:
        validate.validate_bundle(b)
    sys_b = ShadowNervousSystem(_model(), shadow_log_path=tmp_path / "log_b.jsonl")
    bundles_2 = sys_b.run_trace(trace, _gov(), prefixes=("full",))
    assert json.dumps(bundles_1, sort_keys=True) == json.dumps(
        bundles_2, sort_keys=True
    )


def test_runtime_grants_no_authority_and_no_verifier_bypass(tmp_path):
    from pneuma_lab.nervous_system import ShadowNervousSystem

    sys_a = ShadowNervousSystem(_model(), shadow_log_path=tmp_path / "log.jsonl")
    bundle = sys_a.run_trace(
        _load_trace(FIX / "trace_high_risk.jsonl"), _gov(), prefixes=("full",)
    )[0]
    assert bundle["risk_estimate"]["authority_granted"] == "none"
    assert bundle["control_pressure"]["authority_tier"] in ("cosmetic", "soft")
    assert bundle["control_pressure"]["pressures"]["verification"] >= 0.0
    assert "no_runtime_authority" in bundle["blocked_uses"]
    assert bundle["governance_status"] == "emitted"
    for attr in ("actuate", "apply", "execute", "act"):
        assert not hasattr(sys_a, attr)
    for member in ("risk_estimate", "instinct", "control_pressure", "causal_trace"):
        assert "verdict" not in bundle[member]


def test_runtime_causal_trace_refs_are_complete(tmp_path):
    from pneuma_lab.nervous_system import ShadowNervousSystem

    sys_a = ShadowNervousSystem(_model(), shadow_log_path=tmp_path / "log.jsonl")
    bundle = sys_a.run_trace(
        _load_trace(FIX / "trace_high_risk.jsonl"), _gov(), prefixes=("full",)
    )[0]
    ct = bundle["causal_trace"]
    present = {
        f"risk_estimate:{bundle['run_id']}:full",
        f"instinct:{bundle['run_id']}:full",
        f"control_pressure:{bundle['run_id']}:full",
    }
    assert set(ct["emitted_outputs"]) == present
    assert bundle["control_pressure"]["causal_trace_id"] == ct["trace_id"]
    assert bundle["instinct"]["explanation_trace_id"] == ct["trace_id"]
    assert bundle["risk_estimate"]["causal_trace_id"] == ct["trace_id"]
    stages = [n["stage"] for n in ct["causal_path"]]
    assert stages == ["event", "internal_state", "pressure"]


def test_runtime_kill_switch_suppresses_and_audits(tmp_path):
    from pneuma_lab.nervous_system import ShadowNervousSystem

    log = tmp_path / "log.jsonl"
    sys_a = ShadowNervousSystem(_model(), shadow_log_path=log)
    bundles = sys_a.run_trace(
        _load_trace(FIX / "trace_high_risk.jsonl"),
        _gov("governance_killswitch_off.json"),
        prefixes=("full",),
    )
    assert bundles == []
    rows = [
        json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["status"] == "suppressed_by_governance"


# --------------------------------------------------------------------------- #
# Task 7: ablation / null test                                                #
# --------------------------------------------------------------------------- #
def test_ablation_drops_pressure_and_null_holds():
    from pneuma_lab.nervous_system import ablation as nsa

    result = nsa.run_ablation(
        _model(), _load_trace(FIX / "trace_high_risk.jsonl"), _gov(), prefix="full"
    )
    assert result["control_value"] > 0.0
    assert result["treated_value"] == 0.0
    assert result["observed_delta"] < 0.0
    assert abs(result["null_delta"]) <= 1e-6
    assert result["direction_ok"] is True
    assert result["null_holds"] is True
    validate.validate_or_raise(result["evidence_frame"])
    assert result["evidence_frame"]["evidence_level"] == 1


def test_low_risk_control_pressure_below_high():
    from pneuma_lab.nervous_system import ablation as nsa

    hi = nsa.run_ablation(
        _model(), _load_trace(FIX / "trace_high_risk.jsonl"), _gov(), prefix="full"
    )
    lo = nsa.run_ablation(
        _model(), _load_trace(FIX / "trace_low_risk.jsonl"), _gov(), prefix="full"
    )
    assert lo["control_value"] < hi["control_value"]


# --------------------------------------------------------------------------- #
# Task 8: CLI                                                                  #
# --------------------------------------------------------------------------- #
def test_cli_writes_bundle(tmp_path):
    out = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "pneuma_lab.nervous_system",
        "--trace",
        str(FIX / "trace_high_risk.jsonl"),
        "--model",
        str(FIX / "model.json"),
        "--governance",
        str(FIX / "governance_on.json"),
        "--out",
        str(out),
        "--prefix",
        "full",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr
    bundle_file = out / "output_bundles.jsonl"
    assert bundle_file.exists()
    rows = [
        json.loads(x)
        for x in bundle_file.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    assert rows and rows[0]["bundle_kind"] == "pneuma_output"
    assert (out / "shadow_log.jsonl").exists()


# --------------------------------------------------------------------------- #
# Task 9: source hygiene — no 9to5 / verifier imports                         #
# --------------------------------------------------------------------------- #
def test_nervous_system_has_no_forbidden_imports():
    import ast

    pkg = REPO / "src" / "pneuma_lab" / "nervous_system"
    # Real import statements only: no 9to5 module, no verifier module. The word
    # "9to5" may legitimately appear in prose (e.g. "imports nothing from 9to5").
    for py in pkg.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                low = name.lower()
                assert "9to5" not in low, f"{py.name} imports 9to5 module {name!r}"
                assert "verifier" not in low, (
                    f"{py.name} imports a verifier module {name!r}"
                )
    # No hard-coded 9to5 filesystem path or verifier-verdict access anywhere.
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for needle in ("C:/9to5", "C:\\9to5", "c:/9to5", "verifier_verdict"):
            assert needle not in text, (
                f"{py.name} contains forbidden reference {needle!r}"
            )
