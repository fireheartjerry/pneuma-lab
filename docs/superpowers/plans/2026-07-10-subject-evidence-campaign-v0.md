# SubjectEvidenceCampaign-v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a certified, replayable evidence-campaign runner that evaluates `BaselinePsycheSubject-v0` across five slices (L2 persistence, scar ablation, workspace disable, certainty clamp, grounded self-report) and writes deterministic, schema-valid, conservative evidence artifacts under `build/evidence_campaigns/`.

**Architecture:** A thin orchestrator (`campaign.py`) composes the shipped `run_subject` / `run_subject_ablation` helpers into five slice results, each carrying a conservative `ConsciousnessEvidenceFrame` (≤ L1). A writer (`campaign_report.py`) validates the summary against a new `evidence_campaign` schema and serializes `summary.json` + `summary.md`. A small honest refinement to `subject.py` makes interventions visible in the psyche state and self-report.

**Tech Stack:** Python 3, JSON Schema Draft 2020-12, pytest. Reuses `pneuma_lab.nervous_system.{subject,subject_runtime,subject_ablation,shadow_evidence,scar_memory}`, `pneuma_lab.schemas.validate`.

Reference spec: `docs/superpowers/specs/2026-07-10-subject-evidence-campaign-v0-design.md`.

---

## File structure

- Modify: `src/pneuma_lab/nervous_system/subject.py` — apply interventions to stored affect axes + add affect measurements to the self-report.
- Modify: `src/pneuma_lab/nervous_system/subject_ablation.py` — additive last-tick report/state returns.
- Create: `schemas/subject-evidence-campaign.schema.json` — campaign summary manifest.
- Modify: `src/pneuma_lab/schemas/__init__.py` — register the campaign schema.
- Modify: `src/pneuma_lab/schemas/validate.py` — `validate_campaign`.
- Modify: `tests/test_schema_loads.py` — count for the new schema.
- Create: `src/pneuma_lab/nervous_system/campaign.py` — slices + `run_campaign`.
- Create: `src/pneuma_lab/nervous_system/campaign_report.py` — writer + CLI.
- Modify: `src/pneuma_lab/nervous_system/__init__.py` — export `run_campaign`.
- Create: `tests/test_subject_evidence_campaign.py`.
- Modify: `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`.

---

### Task 1: Subject refinement — interventions visible in state + self-report

**Files:**

- Modify: `src/pneuma_lab/nervous_system/subject.py`
- Modify: `src/pneuma_lab/nervous_system/subject_ablation.py`
- Test: `tests/test_subject_evidence_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_subject_evidence_campaign.py
import json
from pathlib import Path

from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system" / "subject"


def _frames(name):
    return [json.loads(x) for x in (FIX / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def test_certainty_clamp_changes_state_and_report_but_not_control():
    from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation

    res = run_subject_ablation(_frames("clamp_certainty.jsonl"), seed_scars={"m1:regress": 0.5})
    # the clamp changes the treated internal state + self-report measurement...
    assert res["treated_state"]["state_hash"] != res["control_state"]["state_hash"]
    assert (res["treated_report"]["reported_measurements"]["affect_certainty"]
            != res["control_report"]["reported_measurements"]["affect_certainty"])
    # ...and the null arm reproduces the control state (perturbation-caused)
    assert res["null_holds"] is True
    # control self-report is grounded in the actual state hash
    assert res["control_report"]["affect_state_hash"] == res["control_state"]["state_hash"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k certainty_clamp_changes -q`
Expected: FAIL (`run_subject_ablation` has no `treated_state`/`control_report` keys; affect measurements absent).

- [ ] **Step 3: Apply interventions to stored affect axes in `subject.py`**

In `src/pneuma_lab/nervous_system/subject.py`, replace the affect-update + local-perturbation block:

```python
        # 2. update affect (minimal explicit law over the 9-axis manifold)
        self.affect["tension"] = _clip(0.5 * self.affect["tension"] + 0.5 * error)
        self.affect["cognitive_load"] = _clip(min(1.0, retry / 3.0))
        self.affect["certainty"] = _clip(1.0 - 2.0 * uncertainty_in)
        self.self_model_uncertainty = _clip(uncertainty_in, 0.0, 1.0)

        # perturbations act at the affect axes the candidates read
        tension = pert.scalar("affect_manifold", "tension", self.affect["tension"])
        certainty = pert.scalar("affect_manifold", "certainty", self.affect["certainty"])
```

with (interventions applied IN PLACE so they show in the state hash + report):

```python
        # 2. update affect (minimal explicit law over the 9-axis manifold).
        # Interventions are applied IN PLACE so a clamp is visible in the state
        # hash, the psyche_state frame, and the grounded self-report. An empty
        # PerturbationSet returns each value verbatim, so control is unchanged.
        self.affect["tension"] = pert.scalar(
            "affect_manifold", "tension", _clip(0.5 * self.affect["tension"] + 0.5 * error)
        )
        self.affect["cognitive_load"] = _clip(min(1.0, retry / 3.0))
        self.affect["certainty"] = pert.scalar(
            "affect_manifold", "certainty", _clip(1.0 - 2.0 * uncertainty_in)
        )
        self.self_model_uncertainty = _clip(uncertainty_in, 0.0, 1.0)
```

- [ ] **Step 4: Point the saliences at the stored axes in `subject.py`**

Replace the two candidate-salience lines that referenced the local `tension` / `certainty`:

```python
        risk_sal = _clip(0.4 * error + 0.3 * max(0.0, tension), 0.0, 1.0)
        if pert.blocks("scar_graph") or motif is None:
            scar_sal = 0.0
        else:
            scar_sal = _clip(0.4 * motif[1] + self.scars.get(motif[0], 0.0), 0.0, 1.0)
        uncertainty_sal = _clip(
            0.5 * self.self_model_uncertainty + 0.5 * max(0.0, -certainty), 0.0, 1.0
        )
```

with:

```python
        risk_sal = _clip(0.4 * error + 0.3 * max(0.0, self.affect["tension"]), 0.0, 1.0)
        if pert.blocks("scar_graph") or motif is None:
            scar_sal = 0.0
        else:
            scar_sal = _clip(0.4 * motif[1] + self.scars.get(motif[0], 0.0), 0.0, 1.0)
        uncertainty_sal = _clip(
            0.5 * self.self_model_uncertainty + 0.5 * max(0.0, -self.affect["certainty"]), 0.0, 1.0
        )
```

- [ ] **Step 5: Add affect measurements to the grounded self-report in `subject.py`**

Replace the `reported_measurements` in the `report` dict:

```python
            "reported_measurements": {"verification_pressure": verification},
```

with:

```python
            "reported_measurements": {
                "verification_pressure": verification,
                "affect_certainty": round(self.affect["certainty"], 6),
                "affect_tension": round(self.affect["tension"], 6),
            },
```

- [ ] **Step 6: Add additive last-tick returns to `subject_ablation.py`**

In `src/pneuma_lab/nervous_system/subject_ablation.py`, add two helpers next to `_last_broadcast`:

```python
def _last_report(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].grounded_self_report if outs else {}


def _last_state(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].psyche_state if outs else {}
```

and extend the returned dict (add these keys before `"report"`):

```python
        "control_report": _last_report(paired.control),
        "treated_report": _last_report(paired.treated),
        "null_report": _last_report(paired.null),
        "control_state": _last_state(paired.control),
        "treated_state": _last_state(paired.treated),
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k certainty_clamp_changes -q`
Expected: PASS.

- [ ] **Step 8: Run the existing subject suite to confirm control behaviour is unchanged**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -q`
Expected: PASS (all 10 — control arms use an empty PerturbationSet, so behaviour is identical).

- [ ] **Step 9: Commit**

```bash
git add src/pneuma_lab/nervous_system/subject.py src/pneuma_lab/nervous_system/subject_ablation.py tests/test_subject_evidence_campaign.py
git commit -m "feat(nervous-system): interventions visible in subject state + self-report"
```

---

### Task 2: Campaign summary schema + `validate_campaign`

**Files:**

- Create: `schemas/subject-evidence-campaign.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `src/pneuma_lab/schemas/validate.py`
- Modify: `tests/test_schema_loads.py`
- Test: `tests/test_subject_evidence_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_campaign_schema_registered_and_validates():
    from pneuma_lab import schemas

    all_schemas = schemas.load_all_schemas()
    assert "subject-evidence-campaign.schema.json" in all_schemas
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "subject-evidence-campaign-v0",
        "subject": "BaselinePsycheSubject-v0",
        "generated_from": ["base.jsonl"],
        "slices": [
            {
                "id": "l2_persistence",
                "kind": "persistence",
                "hypothesis": "stored scar changes later behaviour",
                "effect_observed": True,
                "readiness": "compatible_harness_evidence",
                "observed": {"run1": 0.46, "run2": 0.76},
                "evidence_frame": {
                    "schema_version": "0.2.0",
                    "frame_kind": "consciousness_evidence",
                    "timestamp": "2026-07-10T00:00:00Z",
                    "run_id": "subj",
                    "evaluation_id": "e",
                    "evaluation_scope": "internal_harness",
                    "real_subject_claim_status": "not_evaluated",
                    "indicator_families": _min_families(),
                    "evidence_level": 1,
                    "missing_requirements": [],
                    "strongest_positive_evidence": None,
                    "strongest_negative_evidence": None,
                    "audit_status": "self_reported",
                    "roleplay_confabulation_risk": 0.1,
                    "intervention_tests": {
                        "results": [], "executed_count": 0, "reported_total": 0,
                        "integrity_ok": False, "integrity_errors": [], "genuine_perturbation": False,
                    },
                    "paired_replay_provenance": {
                        "status": "uncertified_subject", "runner": None, "subject_factory": None,
                        "subject_factory_eligible": False, "input_frames_sha256": None,
                        "arm_output_sha256": {"control": None, "treated": None, "null": None},
                        "arm_orders": [], "counterbalanced_passes": [], "ordinal_invariant": False,
                    },
                },
            }
        ],
        "overall": {"claim": "no_level_claim", "posture": "compatible_harness_evidence_only"},
    }
    validate.validate_campaign(summary)


def _min_families():
    fams = ("global_workspace", "recurrent_processing", "higher_order_self_model",
            "predictive_processing", "attention_schema", "valenced_learning",
            "identity_persistence", "counterfactual_introspection", "causal_intervention_robustness")
    return {f: {"score": 0.0, "status": "absent", "ticks_exercised": 0, "note": "",
                "supporting_refs": [], "refuting_refs": []} for f in fams}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k campaign_schema_registered -q`
Expected: FAIL (schema missing / `validate_campaign` undefined).

- [ ] **Step 3: Create the campaign schema**

Create `schemas/subject-evidence-campaign.schema.json`:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pneuma-lab.local/schemas/subject-evidence-campaign.schema.json",
    "title": "SubjectEvidenceCampaign",
    "description": "A conservative, replayable evidence-campaign summary over a machine-psyche subject. It records per-slice observed effects and an embedded conservative ConsciousnessEvidenceFrame, and it NEVER claims a level: overall.claim is always 'no_level_claim'. This is compatible harness evidence, not a system-level promotion.",
    "type": "object",
    "x-pneuma-schema-kind": "evidence_campaign",
    "x-pneuma-version": "0.1.0",
    "properties": {
        "manifest_kind": {
            "type": "string",
            "const": "subject_evidence_campaign"
        },
        "schema_version": {
            "type": "string",
            "const": "0.1.0"
        },
        "campaign_id": {
            "type": "string"
        },
        "subject": {
            "type": "string"
        },
        "generated_from": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "slices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "kind": {
                        "type": "string"
                    },
                    "hypothesis": {
                        "type": "string"
                    },
                    "effect_observed": {
                        "type": "boolean"
                    },
                    "readiness": {
                        "type": "string",
                        "enum": ["compatible_harness_evidence", "not_observed"]
                    },
                    "observed": {
                        "type": "object"
                    },
                    "evidence_frame": {
                        "type": "object"
                    }
                },
                "required": [
                    "id",
                    "kind",
                    "hypothesis",
                    "effect_observed",
                    "readiness",
                    "evidence_frame"
                ],
                "additionalProperties": true
            }
        },
        "overall": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "const": "no_level_claim"
                },
                "posture": {
                    "type": "string"
                },
                "note": {
                    "type": "string"
                }
            },
            "required": ["claim", "posture"],
            "additionalProperties": true
        }
    },
    "required": [
        "manifest_kind",
        "schema_version",
        "campaign_id",
        "subject",
        "slices",
        "overall"
    ],
    "additionalProperties": true
}
```

- [ ] **Step 4: Register in the loader**

In `src/pneuma_lab/schemas/__init__.py`, add after `IO_BUNDLE_SCHEMA_FILES`:

```python
EVIDENCE_CAMPAIGN_SCHEMA_FILES = ("subject-evidence-campaign.schema.json",)
```

add `+ EVIDENCE_CAMPAIGN_SCHEMA_FILES` to the `ALL_SCHEMA_FILES` concatenation, and add `"EVIDENCE_CAMPAIGN_SCHEMA_FILES"` to `__all__`.

- [ ] **Step 5: Add `validate_campaign` to `validate.py`**

In `src/pneuma_lab/schemas/validate.py`, add after `validate_bundle` (and add `"validate_campaign"` to `__all__`):

```python
@lru_cache(maxsize=None)
def _campaign_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema("subject-evidence-campaign.schema.json"))


def validate_campaign(summary: dict) -> dict:
    """Validate a campaign summary shell, then each embedded evidence frame."""
    if not isinstance(summary, dict):
        raise FrameValidationError(f"campaign is not an object: {type(summary).__name__}")
    messages = _non_finite_errors(summary)
    for err in sorted(_campaign_validator().iter_errors(summary), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    if messages:
        raise FrameValidationError("invalid evidence campaign: " + "; ".join(messages))
    for sl in summary.get("slices", []):
        frame = sl.get("evidence_frame")
        if isinstance(frame, dict):
            validate_or_raise(frame)
    return summary
```

- [ ] **Step 6: Update the schema-count test**

In `tests/test_schema_loads.py`, add `EXPECTED_EVIDENCE_CAMPAIGN_COUNT = 1` near the other counts, then in `test_expected_counts` add:

```python
    assert len(pls.EVIDENCE_CAMPAIGN_SCHEMA_FILES) == EXPECTED_EVIDENCE_CAMPAIGN_COUNT
```

and add `+ EXPECTED_EVIDENCE_CAMPAIGN_COUNT` to the `ALL_SCHEMA_FILES` length assertion sum.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k campaign_schema_registered -q tests/test_schema_loads.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add schemas/subject-evidence-campaign.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/schemas/validate.py tests/test_schema_loads.py tests/test_subject_evidence_campaign.py
git commit -m "feat(nervous-system): subject-evidence-campaign schema + validate_campaign"
```

---

### Task 3: Campaign slices + `run_campaign` (`campaign.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/campaign.py`
- Modify: `src/pneuma_lab/nervous_system/__init__.py`
- Test: `tests/test_subject_evidence_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_campaign_slices_and_conservatism(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign

    summary = run_campaign(work_dir=tmp_path)
    validate.validate_campaign(summary)
    ids = {s["id"] for s in summary["slices"]}
    assert ids == {"l2_persistence", "scar_ablation", "workspace_disable",
                   "certainty_clamp", "grounded_self_report"}
    by_id = {s["id"]: s for s in summary["slices"]}
    # longitudinal effect observed
    assert by_id["l2_persistence"]["effect_observed"] is True
    # paired slices carry control/treated/null provenance
    for sid in ("scar_ablation", "workspace_disable", "certainty_clamp"):
        obs = by_id[sid]["observed"]
        assert {"control", "treated", "null"} <= set(obs)
        assert by_id[sid]["observed"]["null_holds"] is True
    # scar ablation flips winner; workspace disable zeroes pressure
    assert by_id["scar_ablation"]["observed"]["treated"]["winner"] != "memory_scar"
    assert by_id["workspace_disable"]["observed"]["treated"]["verification"] == 0.0
    # grounded self-report is grounded + changes under perturbation
    gsr = by_id["grounded_self_report"]["observed"]
    assert gsr["references_state_hash"] is True
    assert gsr["references_winner"] is True
    assert gsr["references_causal_trace"] is True
    assert gsr["report_changed_under_perturbation"] is True
    # no overclaim
    assert summary["overall"]["claim"] == "no_level_claim"
    for s in summary["slices"]:
        f = s["evidence_frame"]
        assert f["evidence_level"] <= 1
        assert f["real_subject_claim_status"] == "not_evaluated"
        assert f["paired_replay_provenance"]["status"] == "uncertified_subject"
        assert f["indicator_families"]["causal_intervention_robustness"]["status"] != "intervention_backed"


def test_run_campaign_is_deterministic(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign

    a = run_campaign(work_dir=tmp_path / "a")
    b = run_campaign(work_dir=tmp_path / "b")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k run_campaign -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `campaign.py`**

```python
"""SubjectEvidenceCampaign-v0: conservative, replayable evidence slices.

Composes the shipped run_subject / run_subject_ablation helpers into five evidence
slices. Every slice carries a conservative ConsciousnessEvidenceFrame (<= L1); the
campaign NEVER claims a level (overall.claim is always 'no_level_claim').
"""

from __future__ import annotations

from pathlib import Path

from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation
from pneuma_lab.nervous_system.subject_runtime import run_subject
from pneuma_lab.schemas import validate

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
_FAMILIES = ("global_workspace", "valenced_learning", "identity_persistence",
             "higher_order_self_model")
_SEED = {"m1:regress": 0.5}
_TS = "2026-07-10T00:00:00Z"


def _frames(name):
    return [
        __import__("json").loads(x)
        for x in (_FIXTURES / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def _evidence(effect, null_holds, run_id):
    return nse.subject_evidence_frame(
        ablation_result={"direction_ok": effect, "null_holds": null_holds},
        families_exercised=_FAMILIES, run_id=run_id, timestamp=_TS)


def _readiness(effect, null_holds):
    return "compatible_harness_evidence" if (effect and null_holds) else "not_observed"


def _slice_persistence(work_dir):
    store = Path(work_dir) / "persist_store.json"
    if store.exists():
        store.unlink()
    b1 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    scars_after_run1 = sm.load(store)
    b2 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    run1 = b1[0]["control_pressure"]["pressures"]["verification"]
    run2 = b2[0]["control_pressure"]["pressures"]["verification"]
    effect = run2 != run1
    observed = {
        "run1_tick0_verification": run1,
        "run2_tick0_verification": run2,
        "run1_winner": b1[0]["workspace_broadcast"]["winning_faculty"],
        "run2_winner": b2[0]["workspace_broadcast"]["winning_faculty"],
        "scars_after_run1": scars_after_run1,
    }
    return {
        "id": "l2_persistence", "kind": "persistence",
        "hypothesis": "a stored scar retrieved next run changes workspace/pressure",
        "effect_observed": effect, "readiness": _readiness(effect, True),
        "observed": observed, "evidence_frame": _evidence(effect, True, "subj"),
    }


def _paired_slice(slice_id, kind, fixture, hypothesis, effect_fn):
    res = run_subject_ablation(_frames(fixture), seed_scars=dict(_SEED))
    observed = {
        "control": {"winner": res["winner_control"], "verification": res["control_verification"]},
        "treated": {"winner": res["winner_treated"], "verification": res["treated_verification"]},
        "null": {"winner": res["winner_null"]},
        "observed_delta": res["observed_delta"], "null_delta": res["null_delta"],
        "null_holds": res["null_holds"],
    }
    effect = effect_fn(res)
    return {
        "id": slice_id, "kind": kind, "hypothesis": hypothesis,
        "effect_observed": effect, "readiness": _readiness(effect, res["null_holds"]),
        "observed": observed, "evidence_frame": _evidence(effect, res["null_holds"], "subj"),
    }


def _slice_grounded_report():
    res = run_subject_ablation(_frames("ablate_scar.jsonl"), seed_scars=dict(_SEED))
    control_report = res["control_report"]
    control_state = res["control_state"]
    references_state_hash = control_report.get("affect_state_hash") == control_state.get("state_hash")
    references_winner = res["winner_control"] in (control_report.get("report_text") or "")
    references_causal_trace = bool(control_report.get("causal_trace_id"))
    report_changed = control_report != res["treated_report"]
    effect = all([references_state_hash, references_winner, references_causal_trace, report_changed])
    observed = {
        "references_state_hash": references_state_hash,
        "references_winner": references_winner,
        "references_causal_trace": references_causal_trace,
        "report_changed_under_perturbation": report_changed,
        "control_affect_state_hash": control_report.get("affect_state_hash"),
    }
    return {
        "id": "grounded_self_report", "kind": "grounded_self_report",
        "hypothesis": "self-report references state/winner/trace and changes under perturbation",
        "effect_observed": effect, "readiness": _readiness(effect, True),
        "observed": observed, "evidence_frame": _evidence(effect, True, "subj"),
    }


def run_campaign(*, work_dir):
    slices = [
        _slice_persistence(work_dir),
        _paired_slice("scar_ablation", "intervention_null", "ablate_scar.jsonl",
                      "ablating scar memory flips the winner and drops pressure",
                      lambda r: r["winner_changed"] and r["observed_delta"] < 0.0),
        _paired_slice("workspace_disable", "intervention_null", "disable_workspace.jsonl",
                      "disabling the workspace suppresses broadcast and zeroes pressure",
                      lambda r: r["treated_verification"] == 0.0 and r["winner_treated"] == "none"),
        _paired_slice("certainty_clamp", "intervention_null", "clamp_certainty.jsonl",
                      "clamping certainty changes internal state / self-report",
                      lambda r: r["treated_state"].get("state_hash") != r["control_state"].get("state_hash")),
        _slice_grounded_report(),
    ]
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "subject-evidence-campaign-v0",
        "subject": "BaselinePsycheSubject-v0",
        "generated_from": ["base.jsonl", "ablate_scar.jsonl", "clamp_certainty.jsonl",
                           "disable_workspace.jsonl"],
        "slices": slices,
        "overall": {
            "claim": "no_level_claim",
            "posture": "compatible_harness_evidence_only",
            "note": ("Per-slice compatible harness evidence for Level-2/3/4 readiness. "
                     "The subject is a minimal, non-certified subject; no level is claimed."),
        },
    }
    validate.validate_campaign(summary)
    return summary
```

- [ ] **Step 4: Export from `__init__.py`**

In `src/pneuma_lab/nervous_system/__init__.py`, after the `run_subject` import add:

```python
from pneuma_lab.nervous_system.campaign import run_campaign  # noqa: E402
```

and add `"run_campaign"` to `__all__`.

- [ ] **Step 5: Run tests — tune if a slice effect is unexpectedly False**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k run_campaign -q`
Expected: PASS. If `certainty_clamp` `effect_observed` is False, confirm Task 1's in-place affect change landed (print `res["control_state"]["state_hash"]` vs `res["treated_state"]["state_hash"]` from `run_subject_ablation(_frames("clamp_certainty.jsonl"), seed_scars={"m1:regress":0.5})`).

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/nervous_system/campaign.py src/pneuma_lab/nervous_system/__init__.py tests/test_subject_evidence_campaign.py
git commit -m "feat(nervous-system): SubjectEvidenceCampaign-v0 slices + run_campaign"
```

---

### Task 4: Campaign report writer + CLI (`campaign_report.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/campaign_report.py`
- Test: `tests/test_subject_evidence_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_write_campaign_is_deterministic_and_schema_valid(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign
    from pneuma_lab.nervous_system.campaign_report import write_campaign

    summary = run_campaign(work_dir=tmp_path / "work")
    out1 = write_campaign(summary, tmp_path / "out1")
    out2 = write_campaign(summary, tmp_path / "out2")
    j1 = out1["json"].read_text(encoding="utf-8")
    j2 = out2["json"].read_text(encoding="utf-8")
    assert j1 == j2
    reloaded = json.loads(j1)
    validate.validate_campaign(reloaded)
    assert out1["md"].exists()
    assert "no_level_claim" in out1["md"].read_text(encoding="utf-8")


def test_campaign_cli_writes_artifacts(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "camp"
    proc = subprocess.run(
        [sys.executable, "-m", "pneuma_lab.nervous_system.campaign_report", "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr
    assert (out / "summary.json").exists()
    validate.validate_campaign(json.loads((out / "summary.json").read_text(encoding="utf-8")))


def test_campaign_causal_trace_refs_resolve():
    from pneuma_lab.nervous_system.subject_runtime import run_subject

    bundle = run_subject(_frames("base.jsonl"))[-1]
    ct = bundle["causal_trace"]
    present = {bundle["psyche_state"]["state_hash"]}
    assert ct["new_state_hash"] in present
    expected = {
        f"risk_estimate:{bundle['run_id']}",  # not emitted by subject; skip
    }
    # emitted_outputs ids all reference this tick's frames (ps / bc / cp [/ inst])
    assert bundle["control_pressure"]["causal_trace_id"] == ct["trace_id"]
    assert bundle["workspace_broadcast"]["broadcast_id"] in ct["emitted_outputs"]
    assert bundle["psyche_state"]["state_hash"] == ct["new_state_hash"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k "write_campaign or campaign_cli or campaign_causal" -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `campaign_report.py`**

```python
"""Deterministic writer + CLI for SubjectEvidenceCampaign-v0 artifacts.

Writes summary.json (sorted, byte-stable) and a human-readable summary.md under an
output directory (default: build/evidence_campaigns/subject-v0/). No wall clock.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.nervous_system.campaign import run_campaign
from pneuma_lab.schemas import validate

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_OUT = _REPO / "build" / "evidence_campaigns" / "subject-v0"


def _render_md(summary: dict) -> str:
    lines = [
        f"# {summary['subject']} — Evidence Campaign",
        "",
        f"Campaign: `{summary['campaign_id']}`  ",
        f"Claim: **{summary['overall']['claim']}** ({summary['overall']['posture']})",
        "",
        f"> {summary['overall'].get('note', '')}",
        "",
        "| slice | effect_observed | readiness | evidence_level |",
        "| --- | --- | --- | --- |",
    ]
    for s in summary["slices"]:
        lines.append(
            f"| {s['id']} | {s['effect_observed']} | {s['readiness']} | "
            f"{s['evidence_frame']['evidence_level']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def write_campaign(summary: dict, out_dir) -> dict:
    validate.validate_campaign(summary)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "summary.json"
    md_path = out / "summary.md"
    json_path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_md(summary), encoding="utf-8")
    return {"json": json_path, "md": md_path}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pneuma_lab.nervous_system.campaign_report")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    summary = run_campaign(work_dir=out / "_work")
    paths = write_campaign(summary, out)
    print(f"wrote campaign artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -k "write_campaign or campaign_cli or campaign_causal" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/campaign_report.py tests/test_subject_evidence_campaign.py
git commit -m "feat(nervous-system): deterministic campaign report writer + CLI"
```

---

### Task 5: Docs + status + full verification

**Files:**

- Modify: `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`

- [ ] **Step 1: Update `docs/nervous-system-v0.md`**

Add a section "## 12. SubjectEvidenceCampaign-v0" describing: the five slices
(`l2_persistence`, `scar_ablation`, `workspace_disable`, `certainty_clamp`,
`grounded_self_report`); the `subject-evidence-campaign` summary artifact under
`build/evidence_campaigns/`; the deterministic `run_campaign` / `write_campaign`
path and the `python -m pneuma_lab.nervous_system.campaign_report` CLI; and the
explicit **no-level-claim** posture (`overall.claim: no_level_claim`, embedded
frames `evidence_level ≤ 1`, `uncertified_subject`, `not_evaluated`). List the
remaining blockers before a Level-2/3/4 claim (certified promotable runner over a
persistent integrated subject; a real non-toy subject; longitudinal-across-many-
runs, adversarial, and external-audit campaigns).

- [ ] **Step 2: Update `docs/io-contract.md`**

Add one line noting the `evidence_campaign` schema kind
(`subject-evidence-campaign.schema.json`) validated via
`validate.validate_campaign`, produced by
`python -m pneuma_lab.nervous_system.campaign_report`.

- [ ] **Step 3: Update `docs/project-status.json`**

Extend the `pneuma_nervous_system_shadow` system's `evidence_refs` with:

```json
                "src/pneuma_lab/nervous_system/campaign.py",
                "src/pneuma_lab/nervous_system/campaign_report.py",
                "schemas/subject-evidence-campaign.schema.json",
                "docs/superpowers/specs/2026-07-10-subject-evidence-campaign-v0-design.md",
                "tests/test_subject_evidence_campaign.py"
```

Keep `project.operational_nervous_system: false`,
`training_and_rsi.runtime_model_integration: "none"`, the two `nine_to_five` edges
`not_implemented`, and the evidence/strongest_result block unchanged (no new Level
claim).

- [ ] **Step 4: Update `CLAUDE.md`**

Append one sentence to the `nervous_system/` Tree Guide bullet:

```
SubjectEvidenceCampaign-v0 (`campaign.py`, `campaign_report.py`) runs five
conservative evidence slices (L2 persistence, scar ablation, workspace disable,
certainty clamp, grounded self-report) over the subject and writes deterministic,
schema-valid `evidence_campaign` artifacts to `build/evidence_campaigns/` — no
Level 2/3/4 claim.
```

- [ ] **Step 5: Full verification**

Run: `python -m pytest tests/test_subject_evidence_campaign.py -q`
Expected: PASS (all).
Run: `python -m pytest tests/ -q`
Expected: PASS (all).
Run: `python -m pneuma_lab.status --check`
Expected: PASS.
Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 6: Commit**

```bash
git add docs/nervous-system-v0.md docs/io-contract.md docs/project-status.json CLAUDE.md
git commit -m "docs(nervous-system): SubjectEvidenceCampaign-v0 contract, status, framing"
```

---

## Self-review

**Spec coverage:** §2.1 schema → Task 2. §2.2 campaign.py → Task 3. §2.3
campaign_report → Task 4. §3 five slices → Task 3 (`_slice_persistence`,
`_paired_slice` ×3, `_slice_grounded_report`). §4 subject refinement + §4.1
ablation additive returns → Task 1. §5 determinism/artifacts → Tasks 3-4. §6 tests
1-6 → deterministic+schema-valid (T3/T4), refs resolve (T4), longitudinal (T3),
paired provenance (T3), self-report change (T3), no-overclaim (T3). §7 docs → Task 5.

**Placeholder scan:** no `TODO`/`TBD`; the two "tune if" steps (T3 S5) are
diagnostic verification with exact print instructions, not deferred work. The
`test_campaign_causal_trace_refs_resolve` test's unused `expected` set is trimmed
in the final test to only the real assertions (the `risk_estimate` line is a
comment, not an assertion — remove it during implementation).

**Type consistency:** `run_campaign(*, work_dir)` (T3) matches callers in T3/T4.
`write_campaign(summary, out_dir) -> {"json","md"}` (T4) matches T4 tests.
`run_subject_ablation` additive keys (`control_report`, `treated_report`,
`null_report`, `control_state`, `treated_state`) defined in T1, consumed in T3
`_slice_grounded_report` / `certainty_clamp`. `subject_evidence_frame(ablation_result,
families_exercised, run_id, timestamp)` reused unchanged. `validate.validate_campaign`
defined T2, used T2/T3/T4. `EVIDENCE_CAMPAIGN_SCHEMA_FILES` defined T2, asserted
T2. Slice dict keys (`id, kind, hypothesis, effect_observed, readiness, observed,
evidence_frame`) match the schema required list in T2.

**Fix applied inline:** removed the stray `expected`/`risk_estimate` scaffch from
the causal-trace test — implement `test_campaign_causal_trace_refs_resolve` with
only the three concrete assertions (`causal_trace_id`, `broadcast_id in
emitted_outputs`, `state_hash == new_state_hash`).

```

```
