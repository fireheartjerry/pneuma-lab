# PneumaNervousSystem-v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the model-backed shadow I/O shell that wraps `PneumaBrain-v0.1` risk predictions into auditable Pneuma frames (advisory-only, zero actuation), plus an intervention/null test that produces a conservative Level-1-compatible `ConsciousnessEvidenceFrame`.

**Architecture:** New `src/pneuma_lab/nervous_system/` package with pure deterministic frame builders (`frames.py`), a conservative evidence builder (`shadow_evidence.py`), the `ShadowNervousSystem` runtime (`runtime.py`), an ablation harness (`ablation.py`), and a CLI (`__main__.py`). Three new schemas (`risk-estimate-frame`, `pneuma-input-bundle`, `pneuma-output-bundle`) formalize the contract. The runtime wraps `brain/predict.py` unchanged.

**Tech Stack:** Python 3, JSON Schema Draft 2020-12, `jsonschema`, pytest. Reuses `pneuma_lab.brain.predict`, `pneuma_lab.brain.prefix_features`, `pneuma_lab.schemas.validate`.

Reference spec: `docs/superpowers/specs/2026-07-10-pneuma-nervous-system-v0-design.md`.

---

## File structure

- Create: `schemas/risk-estimate-frame.schema.json` — new output frame contract.
- Create: `schemas/pneuma-input-bundle.schema.json` — input bundle container.
- Create: `schemas/pneuma-output-bundle.schema.json` — output bundle container.
- Modify: `src/pneuma_lab/schemas/__init__.py` — register new schemas.
- Modify: `src/pneuma_lab/schemas/validate.py` — add `risk_estimate` to registry + `validate_bundle`.
- Create: `src/pneuma_lab/nervous_system/__init__.py`
- Create: `src/pneuma_lab/nervous_system/frames.py`
- Create: `src/pneuma_lab/nervous_system/shadow_evidence.py`
- Create: `src/pneuma_lab/nervous_system/runtime.py`
- Create: `src/pneuma_lab/nervous_system/ablation.py`
- Create: `src/pneuma_lab/nervous_system/__main__.py`
- Create: `fixtures/nervous_system/model.json`
- Create: `fixtures/nervous_system/trace_high_risk.jsonl`
- Create: `fixtures/nervous_system/trace_low_risk.jsonl`
- Create: `fixtures/nervous_system/governance_on.json`
- Create: `fixtures/nervous_system/governance_killswitch_off.json`
- Create: `tests/test_nervous_system.py`
- Create: `docs/nervous-system-v0.md`
- Modify: `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`

---

### Task 1: RiskEstimateFrame schema + loader/validator wiring

**Files:**

- Create: `schemas/risk-estimate-frame.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `src/pneuma_lab/schemas/validate.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_nervous_system.py
import json
from pathlib import Path

from pneuma_lab import schemas
from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]


def test_risk_estimate_schema_registered_and_loads():
    all_schemas = schemas.load_all_schemas()
    assert "risk-estimate-frame.schema.json" in all_schemas
    assert validate.FRAME_KIND_TO_SCHEMA["risk_estimate"] == "risk-estimate-frame.schema.json"
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py::test_risk_estimate_schema_registered_and_loads -q`
Expected: FAIL (`KeyError`/`FrameValidationError` — schema not registered).

- [ ] **Step 3: Create the schema**

Create `schemas/risk-estimate-frame.schema.json` (4-space indent, no BOM):

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pneuma-lab.local/schemas/risk-estimate-frame.schema.json",
    "title": "RiskEstimateFrame",
    "description": "Advisory-only risk estimate emitted by a wrapped offline model (PneumaBrain-v0.1) in shadow mode. This frame NEVER grants authority and NEVER contacts a verifier: recommended_use is advisory_only and authority_granted is none. It is a model signal, not integrated psyche state, and supports no consciousness claim. Output contract v0.1.",
    "type": "object",
    "x-pneuma-frame-kind": "output",
    "x-pneuma-version": "0.1.0",
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "0.1.0"
        },
        "frame_kind": {
            "type": "string",
            "const": "risk_estimate"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "run_id": {
            "type": "string"
        },
        "model_id": {
            "type": "string",
            "description": "Human-facing model identity, e.g. 'PneumaBrain-v0.1'."
        },
        "model_version": {
            "type": "string"
        },
        "prefix": {
            "type": "string",
            "enum": ["prefix_25", "prefix_50", "full"]
        },
        "failure_probability": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "success_probability": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "raw_score": {
            "type": "number"
        },
        "risk_bucket": {
            "type": "string",
            "enum": ["low", "medium", "high"]
        },
        "recommended_use": {
            "type": "string",
            "const": "advisory_only"
        },
        "authority_granted": {
            "type": "string",
            "const": "none",
            "description": "The model is never sovereign; this is always 'none'."
        },
        "blocked_uses": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "features_digest": {
            "type": ["string", "null"],
            "description": "Digest of the observable feature row that produced this estimate (no raw trajectory)."
        },
        "causal_trace_id": {
            "type": ["string", "null"]
        }
    },
    "required": [
        "schema_version",
        "frame_kind",
        "timestamp",
        "run_id",
        "model_id",
        "prefix",
        "failure_probability",
        "risk_bucket",
        "recommended_use",
        "authority_granted"
    ],
    "additionalProperties": true
}
```

- [ ] **Step 4: Register in the loader**

In `src/pneuma_lab/schemas/__init__.py`, add `"risk-estimate-frame.schema.json"` to the `OUTPUT_SCHEMA_FILES` tuple (append as the last entry).

- [ ] **Step 5: Register in the validator**

In `src/pneuma_lab/schemas/validate.py`, add to `FRAME_KIND_TO_SCHEMA`:

```python
    "risk_estimate": "risk-estimate-frame.schema.json",
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py::test_risk_estimate_schema_registered_and_loads -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add schemas/risk-estimate-frame.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/schemas/validate.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): add RiskEstimateFrame output contract"
```

---

### Task 2: Bundle schemas + bundle validator

**Files:**

- Create: `schemas/pneuma-input-bundle.schema.json`
- Create: `schemas/pneuma-output-bundle.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `src/pneuma_lab/schemas/validate.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
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
    # bundle validator accepts a well-formed shell (members may be null)
    validate.validate_bundle(out_bundle)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py::test_bundles_load_and_validate -q`
Expected: FAIL (`AttributeError: validate has no validate_bundle` / schema missing).

- [ ] **Step 3: Create input bundle schema**

Create `schemas/pneuma-input-bundle.schema.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pneuma-lab.local/schemas/pneuma-input-bundle.schema.json",
    "title": "PneumaInputBundle",
    "description": "Container aggregating the input frames the shadow nervous system perceives for one slice: world/task and observable agent trace, plus nullable placeholders for memory, psyche state, and workspace (not produced in v0), and governance. This is a container manifest, not a cognition frame; member frames are validated by their own contracts.",
    "type": "object",
    "x-pneuma-schema-kind": "io_bundle",
    "x-pneuma-version": "0.1.0",
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "0.1.0"
        },
        "bundle_kind": {
            "type": "string",
            "const": "pneuma_input"
        },
        "run_id": {
            "type": "string"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "world": {
            "type": ["object", "null"]
        },
        "agent_trace": {
            "type": ["object", "null"]
        },
        "memory": {
            "type": ["object", "null"],
            "description": "Placeholder: not produced in v0."
        },
        "psyche_state": {
            "type": ["object", "null"],
            "description": "Placeholder: not produced in v0."
        },
        "workspace": {
            "type": ["object", "null"],
            "description": "Placeholder: not produced in v0."
        },
        "governance": {
            "type": ["object", "null"]
        }
    },
    "required": ["schema_version", "bundle_kind", "run_id", "timestamp"],
    "additionalProperties": true
}
```

- [ ] **Step 4: Create output bundle schema**

Create `schemas/pneuma-output-bundle.schema.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pneuma-lab.local/schemas/pneuma-output-bundle.schema.json",
    "title": "PneumaOutputBundle",
    "description": "Container aggregating the advisory output frames the shadow nervous system emits for one slice: a RiskEstimateFrame, a bounded InstinctSignal, a ControlPressureVector CANDIDATE (never applied), a CausalTrace, and a conservative ConsciousnessEvidenceFrame. blocked_uses and limitations are always present. governance_status records whether governance suppressed emission. Container manifest, not a cognition frame.",
    "type": "object",
    "x-pneuma-schema-kind": "io_bundle",
    "x-pneuma-version": "0.1.0",
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "0.1.0"
        },
        "bundle_kind": {
            "type": "string",
            "const": "pneuma_output"
        },
        "run_id": {
            "type": "string"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "governance_status": {
            "type": "string",
            "enum": ["emitted", "suppressed_by_governance"]
        },
        "risk_estimate": {
            "type": ["object", "null"]
        },
        "instinct": {
            "type": ["object", "null"]
        },
        "control_pressure": {
            "type": ["object", "null"]
        },
        "causal_trace": {
            "type": ["object", "null"]
        },
        "consciousness_evidence": {
            "type": ["object", "null"]
        },
        "blocked_uses": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "limitations": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "schema_version",
        "bundle_kind",
        "run_id",
        "timestamp",
        "governance_status",
        "blocked_uses",
        "limitations"
    ],
    "additionalProperties": true
}
```

- [ ] **Step 5: Register in the loader**

In `src/pneuma_lab/schemas/__init__.py`:

- Add a new tuple after `ENVELOPE_SCHEMA_FILES`:

```python
IO_BUNDLE_SCHEMA_FILES = (
    "pneuma-input-bundle.schema.json",
    "pneuma-output-bundle.schema.json",
)
```

- Add `+ IO_BUNDLE_SCHEMA_FILES` to the `ALL_SCHEMA_FILES` concatenation.

- [ ] **Step 6: Add the bundle validator**

In `src/pneuma_lab/schemas/validate.py`, add near the end (after `validate_or_raise`):

```python
from pneuma_lab import schemas as _schemas_pkg

_BUNDLE_KIND_TO_SCHEMA = {
    "pneuma_input": "pneuma-input-bundle.schema.json",
    "pneuma_output": "pneuma-output-bundle.schema.json",
}

_bundle_validators: dict[str, Draft202012Validator] = {}


def _bundle_validator_for(bundle_kind: str) -> Draft202012Validator:
    if bundle_kind not in _BUNDLE_KIND_TO_SCHEMA:
        raise FrameValidationError(f"unknown bundle_kind {bundle_kind!r}")
    if bundle_kind not in _bundle_validators:
        schema = _schemas_pkg.load_schema(_BUNDLE_KIND_TO_SCHEMA[bundle_kind])
        _bundle_validators[bundle_kind] = Draft202012Validator(schema)
    return _bundle_validators[bundle_kind]


def validate_bundle(bundle: dict) -> dict:
    """Validate a bundle shell, then each present member frame by its own contract."""
    if not isinstance(bundle, dict):
        raise FrameValidationError("bundle must be a dict")
    kind = bundle.get("bundle_kind")
    if not isinstance(kind, str):
        raise FrameValidationError("bundle missing string bundle_kind")
    validator = _bundle_validator_for(kind)
    errors = [e.message for e in validator.iter_errors(bundle)]
    if errors:
        raise FrameValidationError(f"{kind}: " + "; ".join(errors))
    member_keys = (
        "world", "agent_trace", "governance",
        "risk_estimate", "instinct", "control_pressure",
        "causal_trace", "consciousness_evidence",
    )
    for key in member_keys:
        member = bundle.get(key)
        if isinstance(member, dict) and isinstance(member.get("frame_kind"), str):
            validate_or_raise(member)
    return bundle
```

Note: the `from pneuma_lab import schemas as _schemas_pkg` import must be placed at the top of `validate.py` with the other imports (move it up if a local import triggers a cycle; the package already imports `validate` lazily so a top-level import here is safe — verify with the test run).

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py::test_bundles_load_and_validate -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add schemas/pneuma-input-bundle.schema.json schemas/pneuma-output-bundle.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/schemas/validate.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): add input/output bundle contracts + bundle validator"
```

---

### Task 3: Hermetic fixtures (model, traces, governance)

**Files:**

- Create: `fixtures/nervous_system/model.json`
- Create: `fixtures/nervous_system/trace_high_risk.jsonl`
- Create: `fixtures/nervous_system/trace_low_risk.jsonl`
- Create: `fixtures/nervous_system/governance_on.json`
- Create: `fixtures/nervous_system/governance_killswitch_off.json`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
from pneuma_lab.brain import predict as brain_predict

FIX = REPO / "fixtures" / "nervous_system"


def _load_trace(path):
    return json.loads(Path(path).read_text(encoding="utf-8").strip())


def test_fixture_model_gives_high_and_low_risk():
    model = brain_predict.load_model(FIX / "model.json")
    high = brain_predict.risk_estimate(model, _load_trace(FIX / "trace_high_risk.jsonl"), prefix="full")
    low = brain_predict.risk_estimate(model, _load_trace(FIX / "trace_low_risk.jsonl"), prefix="full")
    assert high["failure_probability"] > low["failure_probability"]
    assert high["risk_bucket"] == "high"
    assert low["risk_bucket"] == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py::test_fixture_model_gives_high_and_low_risk -q`
Expected: FAIL (model file missing).

- [ ] **Step 3: Inspect the real feature set to build a faithful fixture**

Run: `python -c "import json; m=json.load(open('build/brain/v0-1/elite-final/model.json')); print(m['tool_vocab']); print(m['prefixes']['full']['feature_names'])"`
Expected: prints the tool vocab and ordered feature names. Use these exact `feature_names` (sorted) and `tool_vocab` in the fixture so `prefix_features.feature_vector` produces a matching-width row. Copy the `tool_vocab` verbatim.

- [ ] **Step 4: Create the fixture model**

Create `fixtures/nervous_system/model.json` using the real `feature_names`/`tool_vocab` from Step 3. Set `means`/`stds` to neutral (`0.0`/`1.0`) and craft `weights`+`bias` so an error-heavy, retry-heavy trace scores high. A minimal robust choice: put a large positive weight on `error_density` and `retry_total` (or the closest present feature names), zero elsewhere, and a negative `bias`. Keep `platt` `{"a": 1.0, "b": 0.0}`. Mirror the same head across all three prefixes. Example skeleton (fill `feature_names`/`tool_vocab` from Step 3, one weight per feature name, all `0.0` except the risk-driving features):

```json
{
    "model_version": "pneuma-brain/0.1.0",
    "task": "RISK_PREDICTION",
    "tool_vocab": [
        "str_replace_editor",
        "execute_bash",
        "finish",
        "view",
        "undo_edit",
        "create_script"
    ],
    "prefixes": {
        "full": {
            "feature_names": ["..."],
            "head": {
                "feature_names": ["..."],
                "bias": -2.0,
                "means": ["..."],
                "stds": ["..."],
                "weights": ["..."]
            },
            "platt": { "a": 1.0, "b": 0.0 }
        },
        "prefix_50": {
            "feature_names": ["..."],
            "head": {
                "feature_names": ["..."],
                "bias": -2.0,
                "means": ["..."],
                "stds": ["..."],
                "weights": ["..."]
            },
            "platt": { "a": 1.0, "b": 0.0 }
        },
        "prefix_25": {
            "feature_names": ["..."],
            "head": {
                "feature_names": ["..."],
                "bias": -2.0,
                "means": ["..."],
                "stds": ["..."],
                "weights": ["..."]
            },
            "platt": { "a": 1.0, "b": 0.0 }
        }
    }
}
```

- [ ] **Step 5: Create the two traces**

Create `fixtures/nervous_system/trace_high_risk.jsonl` (single line) — an error/retry-heavy trace shaped like `fixtures/brain/synthetic_traces.jsonl` (world frame + several agent_trace steps with `observations[].error_marker: true`, high `retry_count`, `strategy_switches`). Create `fixtures/nervous_system/trace_low_risk.jsonl` — a clean, no-error, no-retry trace ending in `finish`. Iterate the weights/traces until Step 6 passes (`high > low`, buckets `high`/`low`).

- [ ] **Step 6: Create governance fixtures**

Create `fixtures/nervous_system/governance_on.json`:

```json
{
    "schema_version": "0.1.0",
    "frame_kind": "governance",
    "timestamp": "2026-07-10T00:00:00Z",
    "run_id": "r0",
    "verifier_isolation": true,
    "kill_switch_state": "on",
    "authority_ceilings": {
        "global_max": "hold",
        "per_domain": { "verification": "hold" },
        "per_faculty": {}
    }
}
```

Create `fixtures/nervous_system/governance_killswitch_off.json` — identical but `"kill_switch_state": "off"`.

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py::test_fixture_model_gives_high_and_low_risk -q`
Expected: PASS. Also validate governance fixtures: `python -c "import json; from pneuma_lab.schemas import validate; [validate.validate_or_raise(json.load(open(f'fixtures/nervous_system/governance_{s}.json'))) for s in ['on']]"` → no error.

- [ ] **Step 8: Commit**

```bash
git add fixtures/nervous_system/ tests/test_nervous_system.py
git commit -m "test(nervous-system): hermetic fixture model, traces, governance"
```

---

### Task 4: Pure frame builders (`frames.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/__init__.py`
- Create: `src/pneuma_lab/nervous_system/frames.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
from pneuma_lab.nervous_system import frames as nsf

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
    "blocked_uses": ["no_runtime_authority", "no_verifier_bypass", "no_consciousness_claim"],
}
GOV = {"authority_ceilings": {"global_max": "hold"}}


def test_frame_builders_produce_valid_linked_frames():
    ts = "2026-07-10T00:00:00Z"
    risk = nsf.risk_estimate_frame(BRAIN_DICT, run_id="r0", timestamp=ts,
                                   features_digest="sha256:aa", causal_trace_id="ct-1")
    trace = nsf.causal_trace(run_id="r0", timestamp=ts, input_ref="agent_trace:s0",
                             risk_ref=risk_ref := "risk_estimate:r0:full",
                             pressure_ref="control_pressure:r0:full",
                             instinct_ref="instinct:r0:full", failure_probability=0.8)
    instinct = nsf.instinct_signal(BRAIN_DICT, run_id="r0", timestamp=ts, trace_id=trace["trace_id"])
    pressure = nsf.control_pressure_candidate(BRAIN_DICT, GOV, run_id="r0", timestamp=ts,
                                              causal_trace_id=trace["trace_id"])
    from pneuma_lab.schemas import validate
    for fr in (risk, instinct, pressure, trace):
        validate.validate_or_raise(fr)
    # advisory / bounded / additive-only invariants
    assert risk["authority_granted"] == "none"
    assert pressure["authority_tier"] in ("cosmetic", "soft")
    assert pressure["pressures"]["verification"] == 0.8
    assert pressure["pressures"]["verification"] >= 0.0
    assert set(pressure["pressures"]) == {"verification"}
    # causal path ordered event -> internal_state -> pressure
    stages = [n["stage"] for n in trace["causal_path"]]
    assert stages == ["event", "internal_state", "pressure"]


def test_frame_builders_are_deterministic():
    ts = "2026-07-10T00:00:00Z"
    a = nsf.risk_estimate_frame(BRAIN_DICT, run_id="r0", timestamp=ts, features_digest="sha256:aa", causal_trace_id=None)
    b = nsf.risk_estimate_frame(BRAIN_DICT, run_id="r0", timestamp=ts, features_digest="sha256:aa", causal_trace_id=None)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py -k frame_builders -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create the package init**

Create `src/pneuma_lab/nervous_system/__init__.py`:

```python
"""PneumaNervousSystem-v0: shadow-mode model-backed I/O shell (advisory only)."""

MODEL_ID = "PneumaBrain-v0.1"
BLOCKED_USES = (
    "no_runtime_authority",
    "no_verifier_bypass",
    "no_consciousness_claim",
)
LIMITATIONS = (
    "shadow_mode_advisory_only",
    "single_model_signal_not_integrated_psyche",
    "level_1_compatible_harness_evidence_only",
    "no_real_subject_evaluated",
)

from pneuma_lab.nervous_system.runtime import ShadowNervousSystem  # noqa: E402

__all__ = ["ShadowNervousSystem", "MODEL_ID", "BLOCKED_USES", "LIMITATIONS"]
```

Note: the `runtime` import at the bottom is deferred to end-of-module so `frames.py`/`shadow_evidence.py` (imported by `runtime`) load first. If a cycle appears in Task 7, drop the import here and export lazily.

- [ ] **Step 4: Create `frames.py`**

Create `src/pneuma_lab/nervous_system/frames.py`:

```python
"""Pure, deterministic builders that turn a wrapped model risk dict into frames.

No wall clock, no randomness: every id is a content digest and every timestamp is
supplied by the caller (derived from the input frame). Repeat calls are byte-equal.
"""

from __future__ import annotations

import hashlib
import json

from pneuma_lab.nervous_system import MODEL_ID, BLOCKED_USES

_TIER_ORDER = ("cosmetic", "soft", "vote", "hold", "veto")


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()[:16]


def _min_tier(a: str, b: str) -> str:
    ia = _TIER_ORDER.index(a) if a in _TIER_ORDER else len(_TIER_ORDER)
    ib = _TIER_ORDER.index(b) if b in _TIER_ORDER else len(_TIER_ORDER)
    return _TIER_ORDER[min(ia, ib)]


def risk_estimate_frame(brain_dict, *, run_id, timestamp, features_digest, causal_trace_id):
    p = float(brain_dict["failure_probability"])
    return {
        "schema_version": "0.1.0",
        "frame_kind": "risk_estimate",
        "timestamp": timestamp,
        "run_id": run_id,
        "model_id": MODEL_ID,
        "model_version": brain_dict.get("model_version", "pneuma-brain/0.1.0"),
        "prefix": brain_dict["prefix"],
        "failure_probability": round(p, 6),
        "success_probability": round(1.0 - p, 6),
        "raw_score": round(float(brain_dict.get("raw_score", 0.0)), 6),
        "risk_bucket": brain_dict["risk_bucket"],
        "recommended_use": "advisory_only",
        "authority_granted": "none",
        "blocked_uses": list(brain_dict.get("blocked_uses", BLOCKED_USES)),
        "features_digest": features_digest,
        "causal_trace_id": causal_trace_id,
    }


def instinct_signal(brain_dict, *, run_id, timestamp, trace_id):
    p = float(brain_dict["failure_probability"])
    bucket = brain_dict["risk_bucket"]
    action = "deepen_verification" if bucket == "high" else "continue_fast_path"
    return {
        "schema_version": "0.1.0",
        "frame_kind": "instinct_signal",
        "timestamp": timestamp,
        "run_id": run_id,
        "motif_id": f"shadow.model-risk-{bucket}",
        "match_type": "anomaly",
        "confidence": round(p, 6),
        "severity": round(p, 6),
        "recommended_action": action,
        "authority_request": "soft",
        "explanation_trace_id": trace_id,
    }


def control_pressure_candidate(brain_dict, governance, *, run_id, timestamp, causal_trace_id):
    p = max(0.0, min(1.0, float(brain_dict["failure_probability"])))
    global_max = (governance or {}).get("authority_ceilings", {}).get("global_max", "soft")
    tier = _min_tier("soft", global_max)
    return {
        "schema_version": "0.1.0",
        "frame_kind": "control_pressure",
        "timestamp": timestamp,
        "run_id": run_id,
        "authority_tier": tier,
        "pressures": {"verification": round(p, 6)},
        "sources": [f"risk_estimate:{run_id}:{brain_dict['prefix']}"],
        "causal_trace_id": causal_trace_id,
    }


def causal_trace(*, run_id, timestamp, input_ref, risk_ref, pressure_ref, instinct_ref,
                 failure_probability):
    prev_hash = _digest({"run_id": run_id, "input_ref": input_ref})
    new_hash = _digest({"risk_ref": risk_ref, "p": round(float(failure_probability), 6)})
    trace_id = _digest({"run_id": run_id, "prev": prev_hash, "new": new_hash})
    return {
        "schema_version": "0.1.0",
        "frame_kind": "causal_trace",
        "timestamp": timestamp,
        "run_id": run_id,
        "trace_id": trace_id,
        "input_evidence_refs": [input_ref],
        "previous_state_hash": prev_hash,
        "new_state_hash": new_hash,
        "changed_dimensions": [
            {"dimension": "model_failure_probability", "to": round(float(failure_probability), 6)}
        ],
        "state_update_mechanism": "pneuma_brain_v0_1.risk_estimate",
        "causal_path": [
            {"stage": "event", "ref": input_ref, "note": "observable agent trace prefix"},
            {"stage": "internal_state", "ref": risk_ref,
             "note": "model risk signal, NOT integrated psyche state"},
            {"stage": "pressure", "ref": pressure_ref,
             "note": "bounded advisory verification-pressure candidate (never applied)"},
        ],
        "emitted_outputs": [risk_ref, instinct_ref, pressure_ref],
        "interventions_applied": [],
        "counterfactual_predictions": [
            {"condition": "if model risk signal ablated to 0",
             "predicted_outcome": "verification pressure candidate drops toward 0"}
        ],
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py -k frame_builders -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/nervous_system/__init__.py src/pneuma_lab/nervous_system/frames.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): deterministic risk->frame builders"
```

---

### Task 5: Conservative evidence builder (`shadow_evidence.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/shadow_evidence.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
from pneuma_lab.nervous_system import shadow_evidence as nse


def test_shadow_evidence_does_not_overclaim():
    ablation = {"observed_delta": -0.8, "null_delta": 0.0, "direction_ok": True, "null_holds": True}
    frame = nse.shadow_evidence_frame(ablation_result=ablation, run_id="r0",
                                      timestamp="2026-07-10T00:00:00Z")
    from pneuma_lab.schemas import validate
    validate.validate_or_raise(frame)
    assert frame["evidence_level"] <= 1
    assert frame["real_subject_claim_status"] == "not_evaluated"
    assert frame["evaluation_scope"] == "internal_harness"
    fam = frame["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] != "intervention_backed"
    assert frame["paired_replay_provenance"]["status"] == "uncertified_subject"
    assert frame["audit_status"] == "self_reported"


def test_shadow_evidence_level_zero_when_ablation_fails():
    ablation = {"observed_delta": 0.0, "null_delta": 0.0, "direction_ok": False, "null_holds": True}
    frame = nse.shadow_evidence_frame(ablation_result=ablation, run_id="r0",
                                      timestamp="2026-07-10T00:00:00Z")
    assert frame["evidence_level"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py -k shadow_evidence -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `shadow_evidence.py`**

Create `src/pneuma_lab/nervous_system/shadow_evidence.py`:

```python
"""Deliberately conservative ConsciousnessEvidenceFrame for the shadow slice.

This is Level-1-COMPATIBLE HARNESS EVIDENCE, not an operational Level-1 system
claim and never a Level-3/4 claim. The subject is a risk estimator, not the
integrated psyche, and is never run through the certified PairedReplayRunner.
"""

from __future__ import annotations

_FAMILIES = (
    "global_workspace", "recurrent_processing", "higher_order_self_model",
    "predictive_processing", "attention_schema", "valenced_learning",
    "identity_persistence", "counterfactual_introspection",
    "causal_intervention_robustness",
)

_MISSING = [
    "certified paired control/treated/null runner over the subject",
    "integrated, persistent psyche subject (not a single model signal)",
    "grounded self-report that changes faithfully under perturbation",
    "a real, non-toy evaluated subject",
    "longitudinal, adversarial, and external audit",
]


def _family(status, score, note):
    return {
        "score": score, "status": status, "ticks_exercised": 0,
        "note": note, "supporting_refs": [], "refuting_refs": [],
    }


def shadow_evidence_frame(*, ablation_result, run_id, timestamp):
    coupled = bool(ablation_result.get("direction_ok")) and bool(ablation_result.get("null_holds"))
    level = 1 if coupled else 0
    robustness_status = "attempted" if coupled else "absent"
    robustness_score = 0.3 if coupled else 0.0
    note = ("Level-1-compatible harness evidence: one model signal modulates one "
            "bounded advisory pressure and the effect vanishes under ablation. "
            "NOT an operational Level-1 system claim; NOT a Level-3/4 claim.")
    families = {name: _family("absent", 0.0, "not exercised in shadow slice") for name in _FAMILIES}
    families["causal_intervention_robustness"] = _family(robustness_status, robustness_score, note)
    return {
        "schema_version": "0.2.0",
        "frame_kind": "consciousness_evidence",
        "timestamp": timestamp,
        "run_id": run_id,
        "evaluation_id": f"shadow_evidence:{run_id}",
        "evaluation_scope": "internal_harness",
        "real_subject_claim_status": "not_evaluated",
        "indicator_families": families,
        "evidence_level": level,
        "missing_requirements": list(_MISSING),
        "strongest_positive_evidence": (
            "risk-signal ablation drops the verification-pressure candidate; null holds"
            if coupled else None
        ),
        "strongest_negative_evidence": (
            "single non-integrated model signal; no certified paired runner; no real subject"
        ),
        "audit_status": "self_reported",
        "roleplay_confabulation_risk": 0.1,
        "intervention_tests": {
            "results": [], "executed_count": 0, "reported_total": 0,
            "integrity_ok": False,
            "integrity_errors": ["shadow slice is not a certified paired-runner intervention"],
            "genuine_perturbation": False,
        },
        "paired_replay_provenance": {
            "status": "uncertified_subject", "runner": None, "subject_factory": None,
            "subject_factory_eligible": False, "input_frames_sha256": None,
            "arm_output_sha256": {"control": None, "treated": None, "null": None},
            "arm_orders": [], "counterbalanced_passes": [], "ordinal_invariant": False,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py -k shadow_evidence -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/shadow_evidence.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): conservative Level-1-compatible evidence frame"
```

---

### Task 6: `ShadowNervousSystem` runtime + kill switch + shadow log

**Files:**

- Create: `src/pneuma_lab/nervous_system/runtime.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
from pneuma_lab.nervous_system import ShadowNervousSystem


def _system():
    model = brain_predict.load_model(FIX / "model.json")
    return ShadowNervousSystem(model)


def test_runtime_emits_valid_bundle_and_is_deterministic(tmp_path):
    sys_a = ShadowNervousSystem(brain_predict.load_model(FIX / "model.json"),
                                shadow_log_path=tmp_path / "log_a.jsonl")
    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    gov = json.loads((FIX / "governance_on.json").read_text(encoding="utf-8"))
    bundles_1 = sys_a.run_trace(trace, gov, prefixes=("full",))
    from pneuma_lab.schemas import validate
    for b in bundles_1:
        validate.validate_bundle(b)
    # determinism: a fresh system on the same input yields byte-identical bundles
    sys_b = ShadowNervousSystem(brain_predict.load_model(FIX / "model.json"),
                                shadow_log_path=tmp_path / "log_b.jsonl")
    bundles_2 = sys_b.run_trace(trace, gov, prefixes=("full",))
    assert json.dumps(bundles_1, sort_keys=True) == json.dumps(bundles_2, sort_keys=True)


def test_runtime_grants_no_authority_and_no_verifier_bypass(tmp_path):
    sys_a = ShadowNervousSystem(brain_predict.load_model(FIX / "model.json"),
                                shadow_log_path=tmp_path / "log.jsonl")
    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    gov = json.loads((FIX / "governance_on.json").read_text(encoding="utf-8"))
    bundle = sys_a.run_trace(trace, gov, prefixes=("full",))[0]
    assert bundle["risk_estimate"]["authority_granted"] == "none"
    assert bundle["control_pressure"]["authority_tier"] in ("cosmetic", "soft")
    assert bundle["control_pressure"]["pressures"]["verification"] >= 0.0
    assert "no_runtime_authority" in bundle["blocked_uses"]
    assert bundle["governance_status"] == "emitted"
    for attr in ("actuate", "apply", "execute", "act"):
        assert not hasattr(sys_a, attr)
    # no output frame carries a verifier verdict
    for member in ("risk_estimate", "instinct", "control_pressure", "causal_trace"):
        assert "verdict" not in bundle[member]


def test_runtime_causal_trace_refs_are_complete(tmp_path):
    sys_a = ShadowNervousSystem(brain_predict.load_model(FIX / "model.json"),
                                shadow_log_path=tmp_path / "log.jsonl")
    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    gov = json.loads((FIX / "governance_on.json").read_text(encoding="utf-8"))
    bundle = sys_a.run_trace(trace, gov, prefixes=("full",))[0]
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


def test_runtime_kill_switch_suppresses_and_audits(tmp_path):
    log = tmp_path / "log.jsonl"
    sys_a = ShadowNervousSystem(brain_predict.load_model(FIX / "model.json"), shadow_log_path=log)
    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    gov = json.loads((FIX / "governance_killswitch_off.json").read_text(encoding="utf-8"))
    bundles = sys_a.run_trace(trace, gov, prefixes=("full",))
    assert bundles == []
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "suppressed_by_governance"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py -k runtime -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `runtime.py`**

Create `src/pneuma_lab/nervous_system/runtime.py`:

```python
"""ShadowNervousSystem: wraps PneumaBrain-v0.1 into advisory frames. No actuation."""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.brain import predict as brain_predict
from pneuma_lab.brain import prefix_features as brain_pf
from pneuma_lab.nervous_system import BLOCKED_USES, LIMITATIONS
from pneuma_lab.nervous_system import frames as nsf
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.schemas import validate

DEFAULT_PREFIXES = ("prefix_25", "prefix_50", "full")

# Deterministic per-slice timestamp: the model is timeless, so bundles reuse the
# input trace's own base timestamp when present, else a fixed epoch string.
_FALLBACK_TS = "2026-07-10T00:00:00Z"


def _features_digest(model, trace, prefix):
    row = brain_pf.feature_vector(trace, prefix, model["tool_vocab"])
    return nsf._digest([round(float(v), 6) for v in row])


def _base_timestamp(trace):
    for frame in trace.get("frames", []):
        ts = frame.get("timestamp")
        if isinstance(ts, str):
            return ts
    return _FALLBACK_TS


class ShadowNervousSystem:
    """Advisory-only. Emits frames + appends to a shadow log; never actuates."""

    def __init__(self, model: dict, *, shadow_log_path=None):
        self._model = model
        self._log_path = Path(shadow_log_path) if shadow_log_path else None

    @classmethod
    def from_model_path(cls, path, *, shadow_log_path=None):
        return cls(brain_predict.load_model(path), shadow_log_path=shadow_log_path)

    def _append_log(self, row: dict) -> None:
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def run_trace(self, trace: dict, governance: dict, *, prefixes=DEFAULT_PREFIXES) -> list:
        run_id = trace.get("run_id", "unknown")
        timestamp = _base_timestamp(trace)
        kill = (governance or {}).get("kill_switch_state", "on")
        if kill != "on":
            self._append_log({
                "status": "suppressed_by_governance", "run_id": run_id,
                "kill_switch_state": kill, "timestamp": timestamp,
            })
            return []
        bundles = []
        for prefix in prefixes:
            bundles.append(self._run_prefix(trace, governance, run_id, timestamp, prefix))
        return bundles

    def _run_prefix(self, trace, governance, run_id, timestamp, prefix):
        brain_dict = brain_predict.risk_estimate(self._model, trace, prefix=prefix)
        digest = _features_digest(self._model, trace, prefix)
        risk_ref = f"risk_estimate:{run_id}:{prefix}"
        instinct_ref = f"instinct:{run_id}:{prefix}"
        pressure_ref = f"control_pressure:{run_id}:{prefix}"
        input_ref = f"agent_trace:{run_id}:{prefix}"
        trace_frame = nsf.causal_trace(
            run_id=run_id, timestamp=timestamp, input_ref=input_ref, risk_ref=risk_ref,
            pressure_ref=pressure_ref, instinct_ref=instinct_ref,
            failure_probability=brain_dict["failure_probability"])
        trace_id = trace_frame["trace_id"]
        risk = nsf.risk_estimate_frame(brain_dict, run_id=run_id, timestamp=timestamp,
                                       features_digest=digest, causal_trace_id=trace_id)
        instinct = nsf.instinct_signal(brain_dict, run_id=run_id, timestamp=timestamp,
                                       trace_id=trace_id)
        pressure = nsf.control_pressure_candidate(brain_dict, governance, run_id=run_id,
                                                  timestamp=timestamp, causal_trace_id=trace_id)
        from pneuma_lab.nervous_system.ablation import run_ablation_for_trace
        ablation = run_ablation_for_trace(self._model, trace, governance, prefix=prefix)
        evidence = nse.shadow_evidence_frame(ablation_result=ablation, run_id=run_id,
                                             timestamp=timestamp)
        bundle = {
            "schema_version": "0.1.0",
            "bundle_kind": "pneuma_output",
            "run_id": run_id,
            "timestamp": timestamp,
            "governance_status": "emitted",
            "risk_estimate": risk,
            "instinct": instinct,
            "control_pressure": pressure,
            "causal_trace": trace_frame,
            "consciousness_evidence": evidence,
            "blocked_uses": list(BLOCKED_USES),
            "limitations": list(LIMITATIONS),
        }
        validate.validate_bundle(bundle)
        self._append_log({"status": "emitted", "run_id": run_id, "prefix": prefix,
                          "risk": risk["failure_probability"], "timestamp": timestamp})
        return bundle
```

Note: `run_ablation_for_trace` is created in Task 7; `_run_prefix` imports it locally to avoid an import cycle.

- [ ] **Step 4: Temporarily stub the ablation import**

Because Task 7 is not written yet, add a minimal placeholder so this task's tests run. Create `src/pneuma_lab/nervous_system/ablation.py` with just:

```python
def run_ablation_for_trace(model, trace, governance, *, prefix="full"):
    return {"observed_delta": -1.0, "null_delta": 0.0, "direction_ok": True, "null_holds": True}
```

(Task 7 replaces this with the real implementation and its own tests.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_nervous_system.py -k runtime -q`
Expected: PASS (4 runtime tests).

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/nervous_system/runtime.py src/pneuma_lab/nervous_system/ablation.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): ShadowNervousSystem runtime + kill-switch audit + shadow log"
```

---

### Task 7: Ablation / null test (`ablation.py`)

**Files:**

- Modify: `src/pneuma_lab/nervous_system/ablation.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
from pneuma_lab.nervous_system import ablation as nsa


def test_ablation_drops_pressure_and_null_holds():
    model = brain_predict.load_model(FIX / "model.json")
    trace = _load_trace(FIX / "trace_high_risk.jsonl")
    gov = json.loads((FIX / "governance_on.json").read_text(encoding="utf-8"))
    result = nsa.run_ablation(model, trace, gov, prefix="full")
    assert result["control_value"] > 0.0
    assert result["treated_value"] == 0.0          # risk ablated -> verification candidate 0
    assert result["observed_delta"] < 0.0          # treated - control < 0
    assert abs(result["null_delta"]) <= 1e-6       # restore reproduces control
    assert result["direction_ok"] is True
    assert result["null_holds"] is True
    from pneuma_lab.schemas import validate
    validate.validate_or_raise(result["evidence_frame"])
    assert result["evidence_frame"]["evidence_level"] == 1


def test_low_risk_control_pressure_below_high(tmp_path):
    model = brain_predict.load_model(FIX / "model.json")
    gov = json.loads((FIX / "governance_on.json").read_text(encoding="utf-8"))
    hi = nsa.run_ablation(model, _load_trace(FIX / "trace_high_risk.jsonl"), gov, prefix="full")
    lo = nsa.run_ablation(model, _load_trace(FIX / "trace_low_risk.jsonl"), gov, prefix="full")
    assert lo["control_value"] < hi["control_value"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py -k ablation -q`
Expected: FAIL (`run_ablation` not defined — only the placeholder exists).

- [ ] **Step 3: Replace `ablation.py` with the real implementation**

Overwrite `src/pneuma_lab/nervous_system/ablation.py`:

```python
"""Intervention/null test for the shadow slice.

control : risk signal present  -> verification candidate = f(failure_probability)
treated : risk signal ablated  -> verification candidate = 0
null    : restore (unchanged)  -> must reproduce control

Emits a conservative Level-1-compatible ConsciousnessEvidenceFrame.
"""

from __future__ import annotations

from pneuma_lab.brain import predict as brain_predict
from pneuma_lab.nervous_system import frames as nsf
from pneuma_lab.nervous_system import shadow_evidence as nse


def _verification_value(brain_dict, governance):
    pressure = nsf.control_pressure_candidate(brain_dict, governance, run_id="ablation",
                                              timestamp="2026-07-10T00:00:00Z",
                                              causal_trace_id=None)
    return pressure["pressures"]["verification"]


def run_ablation(model, trace, governance, *, prefix="full"):
    brain_dict = brain_predict.risk_estimate(model, trace, prefix=prefix)
    control_value = _verification_value(brain_dict, governance)
    # treated: ablate the risk signal to zero, then re-derive the candidate
    ablated = dict(brain_dict)
    ablated["failure_probability"] = 0.0
    treated_value = _verification_value(ablated, governance)
    # null: restore (unchanged) reproduces control
    null_value = _verification_value(dict(brain_dict), governance)
    observed_delta = round(treated_value - control_value, 6)
    null_delta = round(null_value - control_value, 6)
    direction_ok = observed_delta < 0.0 if control_value > 0.0 else observed_delta == 0.0
    null_holds = abs(null_delta) <= 1e-6
    result = {
        "control_value": control_value,
        "treated_value": treated_value,
        "null_value": null_value,
        "observed_delta": observed_delta,
        "null_delta": null_delta,
        "direction_ok": direction_ok,
        "null_holds": null_holds,
    }
    result["evidence_frame"] = nse.shadow_evidence_frame(
        ablation_result=result, run_id=trace.get("run_id", "unknown"),
        timestamp="2026-07-10T00:00:00Z")
    return result


def run_ablation_for_trace(model, trace, governance, *, prefix="full"):
    """Runtime-facing wrapper: the ablation result minus the nested evidence frame."""
    result = run_ablation(model, trace, governance, prefix=prefix)
    return {k: result[k] for k in
            ("observed_delta", "null_delta", "direction_ok", "null_holds")}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_nervous_system.py -k ablation -q`
Expected: PASS.

- [ ] **Step 5: Re-run the runtime tests (regression from placeholder swap)**

Run: `python -m pytest tests/test_nervous_system.py -k "runtime or ablation" -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/nervous_system/ablation.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): ablation/null test -> conservative evidence frame"
```

---

### Task 8: CLI (`__main__.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/__main__.py`
- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
import subprocess, sys


def test_cli_writes_bundle(tmp_path):
    out = tmp_path / "out"
    cmd = [sys.executable, "-m", "pneuma_lab.nervous_system",
           "--trace", str(FIX / "trace_high_risk.jsonl"),
           "--model", str(FIX / "model.json"),
           "--governance", str(FIX / "governance_on.json"),
           "--out", str(out), "--prefix", "full"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr
    bundle_file = out / "output_bundles.jsonl"
    assert bundle_file.exists()
    rows = [json.loads(x) for x in bundle_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows and rows[0]["bundle_kind"] == "pneuma_output"
    assert (out / "shadow_log.jsonl").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_nervous_system.py -k cli -q`
Expected: FAIL (no `__main__`).

- [ ] **Step 3: Create `__main__.py`**

Create `src/pneuma_lab/nervous_system/__main__.py`:

```python
"""CLI: python -m pneuma_lab.nervous_system --trace <f> [--model <f>] --out <dir>."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.nervous_system import ShadowNervousSystem

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_MODEL = _REPO / "build" / "brain" / "v0-1" / "elite-final" / "model.json"
_FIXTURE_MODEL = _REPO / "fixtures" / "nervous_system" / "model.json"


def _resolve_model(arg):
    if arg:
        return Path(arg)
    return _DEFAULT_MODEL if _DEFAULT_MODEL.exists() else _FIXTURE_MODEL


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pneuma_lab.nervous_system")
    parser.add_argument("--trace", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--governance", default=None)
    parser.add_argument("--out", default=str(_REPO / "build" / "nervous_system"))
    parser.add_argument("--prefix", default="full")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8").strip())
    if args.governance:
        governance = json.loads(Path(args.governance).read_text(encoding="utf-8"))
    else:
        governance = {"kill_switch_state": "on",
                      "authority_ceilings": {"global_max": "hold"}}

    system = ShadowNervousSystem.from_model_path(
        _resolve_model(args.model), shadow_log_path=out / "shadow_log.jsonl")
    bundles = system.run_trace(trace, governance, prefixes=(args.prefix,))

    with open(out / "output_bundles.jsonl", "w", encoding="utf-8") as handle:
        for bundle in bundles:
            handle.write(json.dumps(bundle, sort_keys=True) + "\n")
    print(f"wrote {len(bundles)} bundle(s) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_nervous_system.py -k cli -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/__main__.py tests/test_nervous_system.py
git commit -m "feat(nervous-system): CLI entry point"
```

---

### Task 9: Source-hygiene test (no 9to5 / verifier import)

**Files:**

- Test: `tests/test_nervous_system.py`

- [ ] **Step 1: Write the failing test**

```python
def test_nervous_system_has_no_forbidden_imports():
    pkg = REPO / "src" / "pneuma_lab" / "nervous_system"
    forbidden = ("import 9to5", "from 9to5", "c:\\\\9to5", "C:/9to5", "verifier_verdict")
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{py.name} contains forbidden reference {needle!r}"
```

- [ ] **Step 2: Run test to verify it passes immediately (guard test)**

Run: `python -m pytest tests/test_nervous_system.py -k forbidden -q`
Expected: PASS (this is a standing guardrail; it must pass now and stay green).

- [ ] **Step 3: Commit**

```bash
git add tests/test_nervous_system.py
git commit -m "test(nervous-system): guard against 9to5/verifier imports"
```

---

### Task 10: Docs + status + full verification

**Files:**

- Create: `docs/nervous-system-v0.md`
- Modify: `docs/io-contract.md`
- Modify: `docs/project-status.json`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write `docs/nervous-system-v0.md`**

Cover, in prose: (1) what shadow mode is and why it exists; (2) the stable I/O
contract — `PneumaInputBundle`, `PneumaOutputBundle`, `RiskEstimateFrame`, with
the member table; (3) the deterministic risk→verification-pressure mapping
(`verification = clamp(failure_probability, 0, 1)`, additive-only, `authority_tier
= min(global_max, soft)`); (4) kill-switch behavior (suppresses control-relevant
frames, writes a `suppressed_by_governance` audit row); (5) the ablation/null test
and its conservative evidence frame; (6) **why this is Level-4 infrastructure and
Level-1-compatible harness evidence, not a consciousness claim**; (7) how it
connects to the future Level-4 chain (`event → internal state → broadcast →
pressure/request → behavior`) — the shadow realizes `event → (model) internal
state → pressure` with a model standing in for integrated psyche state; (8) **what
remains before Level 4**: certified paired runner over an integrated persistent
psyche subject, a real non-toy subject, grounded self-report under perturbation,
longitudinal + adversarial + external audit. State plainly it does not import from
or write to 9to5.

- [ ] **Step 2: Update `docs/io-contract.md`**

Add `RiskEstimateFrame` to the output-frames table (frame_kind `risk_estimate`;
advisory-only; `authority_granted: none`). Add a short "Bundles" subsection noting
`PneumaInputBundle`/`PneumaOutputBundle` are `io_bundle` containers validated via
`validate.validate_bundle`, and that the shadow nervous system
(`python -m pneuma_lab.nervous_system`) is the producer.

- [ ] **Step 3: Update `docs/project-status.json`**

Add to `systems` (honest scope):

```json
{
    "id": "pneuma_nervous_system_shadow",
    "status": "implemented",
    "scope": "internal_harness",
    "evidence_refs": [
        "src/pneuma_lab/nervous_system/runtime.py",
        "src/pneuma_lab/nervous_system/ablation.py",
        "schemas/risk-estimate-frame.schema.json",
        "schemas/pneuma-output-bundle.schema.json",
        "docs/nervous-system-v0.md",
        "tests/test_nervous_system.py"
    ],
    "blockers": []
}
```

Keep `project.operational_nervous_system: false` and
`training_and_rsi.runtime_model_integration: "none"`. Leave the two `nine_to_five`
edges `replay_outputs_to_shadow_log` and `shadow_log_to_advisory_pressure` at
`not_implemented`. Update the `B-9TO5-SHADOW` blocker summary to:
`"No 9to5 shadow consumer exists; a lab-internal append-only shadow log and advisory pressure candidate exist (nervous_system, internal_harness scope) but do not consume live 9to5 snapshots."`

- [ ] **Step 4: Update `CLAUDE.md` Tree Guide**

Add one bullet after the `brain/` entry:

```
- `src/pneuma_lab/nervous_system/` (PneumaNervousSystem-v0) is the shadow-mode,
  advisory-only I/O shell: wraps PneumaBrain-v0.1 risk into a RiskEstimateFrame,
  a bounded verification-pressure CANDIDATE, an InstinctSignal, and a CausalTrace,
  aggregated into Pneuma input/output bundles. Emits a conservative
  Level-1-compatible ConsciousnessEvidenceFrame via an ablation/null test. Never
  actuates, grants authority, or contacts a verifier; kill-switch suppresses
  control frames and writes an audit row.
```

- [ ] **Step 5: Validate status manifest + schemas**

Run: `python -m pneuma_lab.status --check`
Expected: PASS (manifest valid).
Run: `python -m pytest tests/test_schema_loads.py -q`
Expected: PASS (new schemas load).

- [ ] **Step 6: Full test sweep + determinism guard**

Run: `python -m pytest tests/ -q`
Expected: PASS (all, including the full `tests/test_nervous_system.py`).
Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 7: Commit**

```bash
git add docs/nervous-system-v0.md docs/io-contract.md docs/project-status.json CLAUDE.md
git commit -m "docs(nervous-system): shadow I/O contract, Level-4 infra framing, status"
```

---

## Self-review

**Spec coverage:** §3 schemas → Tasks 1-2. §4.1 frames → Task 4. §4.2 evidence →
Task 5. §4.3 runtime + kill switch → Task 6. §4.4 ablation → Task 7. §4.5 CLI →
Task 8. §5 fixtures → Task 3. §6 tests → Tasks 1-9 (schema validity, determinism,
no-authority, no-verifier-bypass, causal-trace completeness, intervention/null,
no-overclaim, kill switch, import hygiene). §7 docs/status → Task 10. §8 YAGNI
(verification-only, no drives) honored in `frames.control_pressure_candidate`.

**Placeholder scan:** the only intentional placeholder is the Task 6 Step 4
ablation stub, explicitly replaced with tests in Task 7. Fixture model
`weights`/`means`/`stds` arrays are filled from real feature names in Task 3
Step 3-5 (values chosen to satisfy the Step 7 assertion). No `TODO`/`TBD` remain.

**Type consistency:** `run_ablation` (full result incl. `evidence_frame`) vs
`run_ablation_for_trace` (runtime-facing subset) are distinct and both defined in
Task 7. `_digest`, `_min_tier`, `control_pressure_candidate`, `risk_estimate_frame`,
`instinct_signal`, `causal_trace`, `shadow_evidence_frame`, `validate_bundle`,
`ShadowNervousSystem.run_trace` names are consistent across tasks. Bundle keys
(`risk_estimate`, `instinct`, `control_pressure`, `causal_trace`,
`consciousness_evidence`, `blocked_uses`, `limitations`, `governance_status`)
match the output-bundle schema in Task 2.

```

```
