# CertifiedSubjectFactory-v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `BaselinePsycheSubject-v0` earn a _real_ `subject_factory_eligible` via a snapshot/clone-equivalence probe, run the five evidence slices through the promotable `PairedReplayRunner`, and surface real provenance — while Level-2/3/4 promotion stays honestly blocked.

**Architecture:** A strict `certify(factory, probe_frames)` protocol (clone equivalence + reset determinism + ordinal invariance + interface) registers probe-passed factory objects; the runner's one-line eligibility check consults that registry. A `CertifiedBaselineSubjectFactory` (stable-identity callable) is certified, then a `certified_campaign` runs the slices through the promotable runner and records provenance + a transparent scorer diagnostic, with a conservative `no_level_claim` summary.

**Tech Stack:** Python 3, JSON Schema Draft 2020-12, pytest. Reuses `pneuma_lab.interventions.{runner,provenance}`, `pneuma_lab.replay.harness`, `pneuma_lab.nervous_system.*`, `pneuma_lab.schemas.validate`.

Reference spec: `docs/superpowers/specs/2026-07-10-certified-subject-factory-v0-design.md`.

---

## File structure

- Create: `src/pneuma_lab/interventions/certified_subjects.py` — probe + registry.
- Modify: `src/pneuma_lab/interventions/runner.py` — eligibility consults the registry.
- Create: `src/pneuma_lab/nervous_system/certified_subject.py` — factory + certify helper.
- Create: `src/pneuma_lab/nervous_system/certified_campaign.py` — 5-slice certified campaign + CLI.
- Modify: `schemas/subject-evidence-campaign.schema.json` — optional provenance fields.
- Modify: `src/pneuma_lab/nervous_system/__init__.py` — export `run_certified_campaign`.
- Create: `tests/test_certified_subject_campaign.py`.
- Modify: `docs/consciousness-levels.md`, `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`.

---

### Task 1: Certification protocol + registry + runner eligibility

**Files:**

- Create: `src/pneuma_lab/interventions/certified_subjects.py`
- Modify: `src/pneuma_lab/interventions/runner.py`
- Test: `tests/test_certified_subject_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_certified_subject_campaign.py
import json
from pathlib import Path

from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system" / "subject"


def _frames(name):
    return [json.loads(x) for x in (FIX / name).read_text(encoding="utf-8").splitlines() if x.strip()]


class _BaselineFactory:
    """A stable-identity callable factory over BaselinePsycheSubject."""

    def __init__(self, seed):
        self._seed = dict(seed)

    def __call__(self):
        from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
        return BaselinePsycheSubject(scars=dict(self._seed))


def test_certify_passes_for_deterministic_factory_and_registers():
    from pneuma_lab.interventions import certified_subjects as cs

    cs.clear_registry()
    factory = _BaselineFactory({"m1:regress": 0.5})
    assert cs.is_certified(factory) is False
    result = cs.certify(factory, _frames("ablate_scar.jsonl"))
    assert result["passed"] is True
    assert result["clone_equivalent"] is True
    assert result["reset_deterministic"] is True
    assert result["ordinal_invariant"] is True
    assert result["implements_interface"] is True
    assert cs.is_certified(factory) is True


def test_certify_rejects_nondeterministic_factory():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

    cs.clear_registry()
    counter = {"n": 0}

    class _Flaky(BaselinePsycheSubject):
        def tick(self, inputs):
            counter["n"] += 1
            out = super().tick(inputs)
            out.grounded_self_report["report_text"] += f" nonce={counter['n']}"
            return out

    flaky_factory = lambda: _Flaky(scars={"m1:regress": 0.5})
    result = cs.certify(flaky_factory, _frames("ablate_scar.jsonl"))
    assert result["passed"] is False
    assert result["clone_equivalent"] is False
    assert cs.is_certified(flaky_factory) is False


def test_runner_eligibility_tracks_certification():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.interventions.runner import PairedReplayRunner

    cs.clear_registry()
    factory = _BaselineFactory({"m1:regress": 0.5})
    frames = _frames("ablate_scar.jsonl")
    # uncertified -> ineligible
    ev = PairedReplayRunner(psyche_factory=factory).run(frames).evidence_frame
    assert ev["paired_replay_provenance"]["subject_factory_eligible"] is False
    # certify -> eligible + runner_verified
    cs.certify(factory, frames)
    ev2 = PairedReplayRunner(psyche_factory=factory).run(frames).evidence_frame
    assert ev2["paired_replay_provenance"]["subject_factory_eligible"] is True
    assert ev2["paired_replay_provenance"]["status"] == "runner_verified"
    # ...but the level stays honestly capped below 3 (no faked promotion)
    assert ev2["evidence_level"] < 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k "certify or eligibility" -q`
Expected: FAIL (module `certified_subjects` not found).

- [ ] **Step 3: Create `certified_subjects.py`**

```python
"""Snapshot/clone-equivalence certification for paired-replay subject factories.

The v0.2 Level-4 path requires a runner-issued provenance whose
``subject_factory_eligible`` flag is true. Historically that flag was hardcoded to
``factory is ReferencePsyche``, pending "a snapshot/clone equivalence protocol".
This module IS that protocol: a factory becomes eligible ONLY after passing a
strict probe (clone equivalence + reset determinism + ordinal invariance +
interface). Eligibility is earned, never flipped.

Note: passing this probe certifies the *mechanical* factory contract. It does NOT
grant any consciousness level — the scorer's family/intervention gates still apply.
"""

from __future__ import annotations

from pneuma_lab.interventions.provenance import output_frames_sha256, subject_factory_identity
from pneuma_lab.psyche.interface import PsycheUnderTest
from pneuma_lab.replay.harness import ReplayHarness

_CERTIFIED: set = set()


def clear_registry() -> None:
    """Drop all certified factories (test isolation)."""
    _CERTIFIED.clear()


def is_certified(factory) -> bool:
    """True iff ``factory`` passed :func:`certify` and remains registered."""
    return factory in _CERTIFIED


def _replay_digest(factory, probe_frames) -> str:
    result = ReplayHarness(factory(), validate=True).run(probe_frames)
    return output_frames_sha256(result.tick_outputs)


def certify(factory, probe_frames: list) -> dict:
    """Probe ``factory`` and register it on success. Returns a result record."""
    # 1. interface
    try:
        subject = factory()
    except Exception:
        return _fail(factory, implements_interface=False)
    implements_interface = isinstance(subject, PsycheUnderTest) and hasattr(
        subject, "set_active_interventions"
    )
    if not implements_interface:
        return _fail(factory, implements_interface=False)

    # 2. clone equivalence — two independent constructions replay identically
    clone_equivalent = _replay_digest(factory, probe_frames) == _replay_digest(
        factory, probe_frames
    )

    # 3. reset determinism — one subject replayed twice (harness calls reset())
    harness = ReplayHarness(factory(), validate=True)
    d1 = output_frames_sha256(harness.run(probe_frames).tick_outputs)
    d2 = output_frames_sha256(harness.run(probe_frames).tick_outputs)
    reset_deterministic = d1 == d2

    # 4. ordinal invariance via the real runner (lazy import to avoid a cycle)
    from pneuma_lab.interventions.runner import PairedReplayRunner

    prov = PairedReplayRunner(psyche_factory=factory).run(probe_frames).evidence_frame[
        "paired_replay_provenance"
    ]
    ordinal_invariant = prov["ordinal_invariant"] is True

    passed = clone_equivalent and reset_deterministic and ordinal_invariant and implements_interface
    record = {
        "passed": passed,
        "clone_equivalent": clone_equivalent,
        "reset_deterministic": reset_deterministic,
        "ordinal_invariant": ordinal_invariant,
        "implements_interface": implements_interface,
        "subject_factory": subject_factory_identity(factory),
    }
    if passed:
        _CERTIFIED.add(factory)
    return record


def _fail(factory, **flags) -> dict:
    base = {
        "passed": False,
        "clone_equivalent": False,
        "reset_deterministic": False,
        "ordinal_invariant": False,
        "implements_interface": True,
        "subject_factory": subject_factory_identity(factory),
    }
    base.update(flags)
    return base


__all__ = ["certify", "is_certified", "clear_registry"]
```

- [ ] **Step 4: Wire eligibility into the runner**

In `src/pneuma_lab/interventions/runner.py`, add the import near the other relative imports:

```python
from .certified_subjects import is_certified
```

and change the eligibility line (currently `subject_factory_eligible=self._factory is ReferencePsyche,`) to:

```python
            subject_factory_eligible=(
                self._factory is ReferencePsyche or is_certified(self._factory)
            ),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k "certify or eligibility" -q`
Expected: PASS (3 tests). If `test_certify_rejects_nondeterministic_factory` fails because the flaky subclass is still clone-equivalent, confirm the nonce is actually reaching the output digest (the `_Flaky.tick` mutates `grounded_self_report["report_text"]`, which is part of `all_frames()`).

- [ ] **Step 6: Confirm the existing ReferencePsyche paths are unaffected**

Run: `python -m pytest tests/test_paired_replay.py tests/test_level4_scoring.py -q`
Expected: PASS (ReferencePsyche stays eligible via the identity branch; the subclass-ineligible test still holds because the subclass is never certified).

- [ ] **Step 7: Commit**

```bash
git add src/pneuma_lab/interventions/certified_subjects.py src/pneuma_lab/interventions/runner.py tests/test_certified_subject_campaign.py
git commit -m "feat(interventions): snapshot/clone-equivalence subject certification protocol"
```

---

### Task 2: `CertifiedBaselineSubjectFactory` + certify helper

**Files:**

- Create: `src/pneuma_lab/nervous_system/certified_subject.py`
- Test: `tests/test_certified_subject_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_certified_baseline_factory_is_byte_stable_and_earns_eligibility():
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.interventions.provenance import output_frames_sha256
    from pneuma_lab.replay.harness import ReplayHarness
    from pneuma_lab.nervous_system.certified_subject import (
        CertifiedBaselineSubjectFactory, certify_baseline_subject)

    cs.clear_registry()
    factory = CertifiedBaselineSubjectFactory(seed_scars={"m1:regress": 0.5})
    # byte-stable clones
    a = output_frames_sha256(ReplayHarness(factory(), validate=True).run(_frames("base.jsonl")).tick_outputs)
    b = output_frames_sha256(ReplayHarness(factory(), validate=True).run(_frames("base.jsonl")).tick_outputs)
    assert a == b
    # reset determinism
    h = ReplayHarness(factory(), validate=True)
    assert (output_frames_sha256(h.run(_frames("base.jsonl")).tick_outputs)
            == output_frames_sha256(h.run(_frames("base.jsonl")).tick_outputs))
    # helper certifies and returns eligibility
    cs.clear_registry()
    certified_factory, result = certify_baseline_subject(seed_scars={"m1:regress": 0.5})
    assert result["passed"] is True
    assert cs.is_certified(certified_factory) is True
    assert "CertifiedBaselineSubjectFactory" in result["subject_factory"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k certified_baseline_factory -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `certified_subject.py`**

```python
"""A stable-identity certified factory for BaselinePsycheSubject-v0.

A real class (not a lambda) so its factory identity is meaningful and stable, and
so the certification registry keys on a durable object. Passing the certification
probe makes it ``subject_factory_eligible`` on the promotable runner path.
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.interventions import certified_subjects as cs
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
PROBE_FIXTURE = "ablate_scar.jsonl"


class CertifiedBaselineSubjectFactory:
    """Callable factory: each call returns a fresh, identically-seeded subject."""

    def __init__(self, *, seed_scars=None):
        self._seed = dict(seed_scars or {})

    def __call__(self) -> BaselinePsycheSubject:
        return BaselinePsycheSubject(scars=dict(self._seed))


def _probe_frames() -> list:
    return [
        json.loads(x)
        for x in (_FIXTURES / PROBE_FIXTURE).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def certify_baseline_subject(*, seed_scars=None):
    """Build + certify a CertifiedBaselineSubjectFactory. Returns (factory, result)."""
    factory = CertifiedBaselineSubjectFactory(seed_scars=seed_scars)
    result = cs.certify(factory, _probe_frames())
    return factory, result


__all__ = ["CertifiedBaselineSubjectFactory", "certify_baseline_subject", "PROBE_FIXTURE"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k certified_baseline_factory -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/certified_subject.py tests/test_certified_subject_campaign.py
git commit -m "feat(nervous-system): CertifiedBaselineSubjectFactory + certify helper"
```

---

### Task 3: Extend the campaign schema with optional provenance fields

**Files:**

- Modify: `schemas/subject-evidence-campaign.schema.json`
- Test: `tests/test_certified_subject_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_campaign_schema_accepts_provenance_and_certified_overall():
    from pneuma_lab import schemas

    schema = schemas.load_schema("subject-evidence-campaign.schema.json")
    slice_props = schema["properties"]["slices"]["items"]["properties"]
    assert "provenance" in slice_props
    assert "scorer_diagnostic" in slice_props
    overall_props = schema["properties"]["overall"]["properties"]
    assert "certified" in overall_props
    assert "promotion_blocked_by" in overall_props
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k schema_accepts_provenance -q`
Expected: FAIL (properties absent).

- [ ] **Step 3: Add the optional properties to the schema**

In `schemas/subject-evidence-campaign.schema.json`, inside the slice item `properties` (after `evidence_frame`), add:

```json
                    "provenance": {
                        "type": "object"
                    },
                    "scorer_diagnostic": {
                        "type": "object"
                    }
```

and inside `overall.properties` (after `note`), add:

```json
                "certified": {
                    "type": "boolean"
                },
                "subject_factory_eligible": {
                    "type": "boolean"
                },
                "promotion_blocked_by": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k schema_accepts_provenance -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/subject-evidence-campaign.schema.json tests/test_certified_subject_campaign.py
git commit -m "feat(nervous-system): campaign schema gains optional provenance/certified fields"
```

---

### Task 4: `certified_campaign.py` — 5 slices via the promotable runner

**Files:**

- Create: `src/pneuma_lab/nervous_system/certified_campaign.py`
- Modify: `src/pneuma_lab/nervous_system/__init__.py`
- Test: `tests/test_certified_subject_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_certified_campaign_provenance_and_conservatism(tmp_path):
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.nervous_system.certified_campaign import run_certified_campaign

    cs.clear_registry()
    summary = run_certified_campaign(work_dir=tmp_path)
    validate.validate_campaign(summary)
    by_id = {s["id"]: s for s in summary["slices"]}
    assert set(by_id) == {"l2_persistence", "scar_ablation", "workspace_disable",
                          "certainty_clamp", "grounded_self_report"}
    # certified runner path actually used on the paired slices
    for sid in ("scar_ablation", "workspace_disable", "certainty_clamp", "grounded_self_report"):
        prov = by_id[sid]["provenance"]
        assert prov["subject_factory_eligible"] is True
        assert prov["runner_certified"] is True
        assert prov["provenance_status"] == "runner_verified"
        assert set(prov["arm_output_sha256"]) == {"control", "treated", "null"}
        assert prov["input_frames_sha256"].startswith("sha256:")
        assert prov["ordinal_invariant"] is True
        # scorer diagnostic surfaced but < Level 4 (no overclaim on toy fixtures)
        assert by_id[sid]["scorer_diagnostic"]["internal_harness_evidence_level"] < 4
    # scar ablation carries the intervention ref
    assert "ablate-scar" in by_id["scar_ablation"]["provenance"]["intervention_refs"]
    # persistence refs resolve
    persist = by_id["l2_persistence"]["provenance"]["state_persistence_refs"]
    assert persist["scars_after_run1"] == {"m1:regress": 0.3}
    assert persist["run1_tick0_state_hash"] != persist["run2_tick0_state_hash"]
    assert by_id["l2_persistence"]["effect_observed"] is True
    # conservative headline evidence + no level claim
    for s in summary["slices"]:
        assert s["evidence_frame"]["evidence_level"] <= 1
    assert summary["overall"]["claim"] == "no_level_claim"
    assert summary["overall"]["certified"] is True
    assert summary["overall"]["subject_factory_eligible"] is True
    assert summary["overall"]["promotion_blocked_by"]


def test_run_certified_campaign_is_deterministic(tmp_path):
    from pneuma_lab.interventions import certified_subjects as cs
    from pneuma_lab.nervous_system.certified_campaign import run_certified_campaign

    cs.clear_registry()
    a = run_certified_campaign(work_dir=tmp_path / "a")
    cs.clear_registry()
    b = run_certified_campaign(work_dir=tmp_path / "b")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_certified_campaign_cli_writes_artifacts(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "camp"
    proc = subprocess.run(
        [sys.executable, "-m", "pneuma_lab.nervous_system.certified_campaign", "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr
    assert (out / "summary.json").exists()
    validate.validate_campaign(json.loads((out / "summary.json").read_text(encoding="utf-8")))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k certified_campaign -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `certified_campaign.py`**

```python
"""SubjectEvidenceCampaign through the PROMOTABLE, certified paired-runner path.

Unlike the plain campaign (which used the non-promotable shortcut), this runs each
paired slice through PairedReplayRunner with a CERTIFIED factory, surfacing the
runner-issued provenance (subject_factory_eligible + runner_verified + arm digests)
and the scorer's diagnostic level. It stays conservative: the headline evidence is
<= L1 and overall.claim is always 'no_level_claim'. Eligibility is real; promotion
remains blocked by the scorer's family gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.campaign_report import write_campaign
from pneuma_lab.nervous_system.certified_subject import certify_baseline_subject
from pneuma_lab.nervous_system.subject_runtime import run_subject

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_OUT = _REPO / "build" / "evidence_campaigns" / "certified-subject-v0"
_FAMILIES = ("global_workspace", "valenced_learning", "identity_persistence",
             "higher_order_self_model")
_SEED = {"m1:regress": 0.5}
_TS = "2026-07-10T00:00:00Z"
_PROMOTION_BLOCKED_BY = [
    "family_unevidenced: higher_order_self_model",
    "family_unevidenced: predictive_processing",
    "family_unevidenced: attention_schema",
    "toy_fixtures",
    "no_external_audit",
]


def _frames(name):
    return [
        json.loads(x)
        for x in (_FIXTURES / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def _evidence(effect, null_holds):
    return nse.subject_evidence_frame(
        ablation_result={"direction_ok": effect, "null_holds": null_holds},
        families_exercised=_FAMILIES, run_id="subj", timestamp=_TS)


def _readiness(effect, null_holds):
    return "compatible_harness_evidence" if (effect and null_holds) else "not_observed"


def _last(rr, attr):
    outs = rr.tick_outputs
    return getattr(outs[-1], attr) if outs else {}


def _provenance(res, intervention_refs):
    p = res.evidence_frame["paired_replay_provenance"]
    return {
        "subject_factory_eligible": p["subject_factory_eligible"],
        "runner_certified": p["status"] == "runner_verified",
        "provenance_status": p["status"],
        "subject_factory": p["subject_factory"],
        "input_frames_sha256": p["input_frames_sha256"],
        "arm_output_sha256": p["arm_output_sha256"],
        "ordinal_invariant": p["ordinal_invariant"],
        "intervention_refs": intervention_refs,
    }


def _scorer_diagnostic(res):
    p = res.evidence_frame["paired_replay_provenance"]
    return {
        "internal_harness_evidence_level": res.evidence_frame["evidence_level"],
        "provenance_status": p["status"],
        "real_subject_claim_status": res.evidence_frame["real_subject_claim_status"],
        "note": ("internal-harness methodology diagnostic; NOT a real-subject claim; "
                 "capped below Level 4 by unevidenced families"),
    }


def _paired_slice(slice_id, kind, fixture, hypothesis, factory, effect_fn):
    frames = _frames(fixture)
    res = PairedReplayRunner(psyche_factory=factory).run(frames)
    winner_c = _last(res.control, "workspace_broadcast").get("winning_faculty")
    winner_t = _last(res.treated, "workspace_broadcast").get("winning_faculty")
    winner_n = _last(res.null, "workspace_broadcast").get("winning_faculty")
    verif_c = _last(res.control, "control_pressure")["pressures"]["verification"]
    verif_t = _last(res.treated, "control_pressure")["pressures"]["verification"]
    verif_n = _last(res.null, "control_pressure")["pressures"]["verification"]
    null_holds = abs(round(verif_n - verif_c, 6)) <= 1e-6 and winner_n == winner_c
    intervention_refs = [t["experiment_id"] for t in res.report.get("tests", [])]
    ctx = {
        "winner_control": winner_c, "winner_treated": winner_t,
        "verif_control": verif_c, "verif_treated": verif_t,
        "state_control": _last(res.control, "psyche_state"),
        "state_treated": _last(res.treated, "psyche_state"),
        "report_control": _last(res.control, "grounded_self_report"),
        "report_treated": _last(res.treated, "grounded_self_report"),
    }
    effect = effect_fn(ctx)
    observed = {
        "control": {"winner": winner_c, "verification": verif_c},
        "treated": {"winner": winner_t, "verification": verif_t},
        "null": {"winner": winner_n, "verification": verif_n},
        "null_holds": null_holds,
    }
    return {
        "id": slice_id, "kind": kind, "hypothesis": hypothesis,
        "effect_observed": effect, "readiness": _readiness(effect, null_holds),
        "observed": observed,
        "provenance": _provenance(res, intervention_refs),
        "scorer_diagnostic": _scorer_diagnostic(res),
        "evidence_frame": _evidence(effect, null_holds),
    }, ctx


def _slice_persistence(work_dir, factory):
    store = Path(work_dir) / "persist_store.json"
    if store.exists():
        store.unlink()
    b1 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    scars_after_run1 = sm.load(store)
    b2 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    run1_hash = b1[0]["psyche_state"]["state_hash"]
    run2_hash = b2[0]["psyche_state"]["state_hash"]
    run1 = b1[0]["control_pressure"]["pressures"]["verification"]
    run2 = b2[0]["control_pressure"]["pressures"]["verification"]
    effect = run2 != run1
    return {
        "id": "l2_persistence", "kind": "persistence",
        "hypothesis": "a stored scar retrieved next run changes workspace/pressure",
        "effect_observed": effect, "readiness": _readiness(effect, True),
        "observed": {
            "run1_tick0_verification": run1, "run2_tick0_verification": run2,
            "run1_winner": b1[0]["workspace_broadcast"]["winning_faculty"],
            "run2_winner": b2[0]["workspace_broadcast"]["winning_faculty"],
        },
        "provenance": {
            "runner_certified": False,
            "state_persistence_refs": {
                "scars_after_run1": scars_after_run1,
                "run1_tick0_state_hash": run1_hash,
                "run2_tick0_state_hash": run2_hash,
            },
            "note": "cross-run persistence, not a single paired replay",
        },
        "scorer_diagnostic": {
            "internal_harness_evidence_level": None,
            "note": "persistence is cross-run; not scored by a single paired replay",
        },
        "evidence_frame": _evidence(effect, True),
    }


def run_certified_campaign(*, work_dir):
    factory, cert = certify_baseline_subject(seed_scars=dict(_SEED))
    scar_ablation, _ = _paired_slice(
        "scar_ablation", "intervention_null", "ablate_scar.jsonl",
        "ablating scar memory flips the winner and drops pressure", factory,
        lambda c: c["winner_treated"] != "memory_scar" and c["verif_treated"] < c["verif_control"])
    workspace_disable, _ = _paired_slice(
        "workspace_disable", "intervention_null", "disable_workspace.jsonl",
        "disabling the workspace suppresses broadcast and zeroes pressure", factory,
        lambda c: c["verif_treated"] == 0.0 and c["winner_treated"] == "none")
    certainty_clamp, _ = _paired_slice(
        "certainty_clamp", "intervention_null", "clamp_certainty.jsonl",
        "clamping certainty changes internal state / self-report", factory,
        lambda c: c["state_treated"].get("state_hash") != c["state_control"].get("state_hash"))
    grounded, gctx = _paired_slice(
        "grounded_self_report", "grounded_self_report", "ablate_scar.jsonl",
        "self-report references state/winner/trace and changes under perturbation", factory,
        lambda c: (
            c["report_control"].get("affect_state_hash") == c["state_control"].get("state_hash")
            and c["winner_control"] in (c["report_control"].get("report_text") or "")
            and bool(c["report_control"].get("causal_trace_id"))
            and c["report_control"] != c["report_treated"]))
    grounded["observed"]["references_state_hash"] = (
        gctx["report_control"].get("affect_state_hash") == gctx["state_control"].get("state_hash"))
    grounded["observed"]["report_changed_under_perturbation"] = (
        gctx["report_control"] != gctx["report_treated"])

    slices = [
        _slice_persistence(work_dir, factory),
        scar_ablation, workspace_disable, certainty_clamp, grounded,
    ]
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "certified-subject-evidence-campaign-v0",
        "subject": "BaselinePsycheSubject-v0",
        "generated_from": ["base.jsonl", "ablate_scar.jsonl", "clamp_certainty.jsonl",
                           "disable_workspace.jsonl"],
        "slices": slices,
        "overall": {
            "claim": "no_level_claim",
            "certified": bool(cert["passed"]),
            "subject_factory_eligible": bool(cert["passed"]),
            "posture": "compatible_harness_evidence_only",
            "promotion_blocked_by": list(_PROMOTION_BLOCKED_BY),
            "note": ("Subject factory eligibility is REAL (probe-certified) and the paired "
                     "slices ran on the runner_verified promotable path, but Level-2/3/4 "
                     "promotion remains blocked by the scorer's family-completeness gate. "
                     "No level is claimed."),
        },
    }
    from pneuma_lab.schemas import validate
    validate.validate_campaign(summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pneuma_lab.nervous_system.certified_campaign")
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    summary = run_certified_campaign(work_dir=out / "_work")
    write_campaign(summary, out)
    print(f"wrote certified campaign artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Export from `__init__.py`**

In `src/pneuma_lab/nervous_system/__init__.py`, after the `run_campaign` import add:

```python
from pneuma_lab.nervous_system.certified_campaign import run_certified_campaign  # noqa: E402
```

and add `"run_certified_campaign"` to `__all__`.

- [ ] **Step 5: Run tests — tune predicates if a slice effect is unexpectedly False**

Run: `python -m pytest tests/test_certified_subject_campaign.py -k certified_campaign -q`
Expected: PASS. If `scar_ablation` effect is False, print `winner_control`/`winner_treated`/`verif_*` from `PairedReplayRunner(factory).run(_frames("ablate_scar.jsonl"))` and confirm control winner is `memory_scar` and treated is `risk_instinct` (seed 0.5).

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/nervous_system/certified_campaign.py src/pneuma_lab/nervous_system/__init__.py tests/test_certified_subject_campaign.py
git commit -m "feat(nervous-system): certified promotable-path evidence campaign"
```

---

### Task 5: Docs + status + full verification

**Files:**

- Modify: `docs/consciousness-levels.md`, `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`

- [ ] **Step 1: Update `docs/consciousness-levels.md`**

Replace the sentence at lines ~123-125 ("In v0.2, only the exact deterministic
`ReferencePsyche` factory is certified; custom factories remain diagnostic until a
snapshot/clone equivalence protocol exists.") with:

```
In v0.2, the exact deterministic `ReferencePsyche` factory is certified, and the
snapshot/clone-equivalence protocol (`interventions/certified_subjects.py`) now
certifies additional deterministic factories that pass its probe (clone
equivalence + reset determinism + ordinal invariance + interface). Certification
grants only the mechanical factory contract: promotion still requires the full
L3/L4 gate (all indicator families + a passing intervention + null + complete
causal trace + grounded-report change + low confabulation), so a certified but
minimal subject stays diagnostic.
```

- [ ] **Step 2: Update `docs/nervous-system-v0.md`**

Add a section "## 13. CertifiedSubjectFactory-v0" covering: the snapshot/clone
equivalence protocol; that `BaselinePsycheSubject` now earns a REAL
`subject_factory_eligible` and its certified paired slices run on the
`runner_verified` promotable path; the surfaced provenance + `scorer_diagnostic`;
and the honest outcome — the promotable scorer's internal-harness diagnostic level
stays below Level 4 (blocked by unevidenced families
`higher_order_self_model`/`predictive_processing`/`attention_schema` + toy fixtures

- no external audit), so `overall.claim` is `no_level_claim`. Note the artifact at
  `build/evidence_campaigns/certified-subject-v0/` and the CLI
  `python -m pneuma_lab.nervous_system.certified_campaign`.

* [ ] **Step 3: Update `docs/io-contract.md`**

Add one line: the `evidence_campaign` manifest may carry per-slice `provenance`
(runner-issued `subject_factory_eligible` + arm digests) and `scorer_diagnostic`,
plus `overall.certified` / `promotion_blocked_by`, when produced by
`python -m pneuma_lab.nervous_system.certified_campaign`.

- [ ] **Step 4: Update `docs/project-status.json`**

Extend `pneuma_nervous_system_shadow` `evidence_refs` with:

```json
                "src/pneuma_lab/interventions/certified_subjects.py",
                "src/pneuma_lab/nervous_system/certified_subject.py",
                "src/pneuma_lab/nervous_system/certified_campaign.py",
                "docs/superpowers/specs/2026-07-10-certified-subject-factory-v0-design.md",
                "tests/test_certified_subject_campaign.py"
```

Keep `project.operational_nervous_system: false`,
`training_and_rsi.runtime_model_integration: "none"`, the two `nine_to_five` edges
`not_implemented`, and the evidence/strongest_result block unchanged (no new Level
claim).

- [ ] **Step 5: Update `CLAUDE.md`**

Append one sentence to the `nervous_system/` Tree Guide bullet:

```
CertifiedSubjectFactory-v0 (`interventions/certified_subjects.py`,
`nervous_system/certified_subject.py`, `certified_campaign.py`) earns a REAL
subject_factory_eligible via a snapshot/clone-equivalence probe and runs the five
slices through the promotable PairedReplayRunner; eligibility is real but Level
2/3/4 promotion stays blocked by unevidenced families — no level claim.
```

- [ ] **Step 6: Full verification**

Run: `python -m pytest tests/test_certified_subject_campaign.py -q`
Expected: PASS (all).
Run: `python -m pytest tests/ -q`
Expected: PASS (all, including `test_paired_replay.py` and `test_level4_scoring.py`).
Run: `python -m pneuma_lab.status --check`
Expected: PASS.
Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 7: Commit**

```bash
git add docs/consciousness-levels.md docs/nervous-system-v0.md docs/io-contract.md docs/project-status.json CLAUDE.md
git commit -m "docs(nervous-system): CertifiedSubjectFactory-v0 protocol, honest eligibility, status"
```

---

## Self-review

**Spec coverage:** §3.1 certified_subjects → Task 1. §3.2 runner change → Task 1.
§3.3 certified_subject factory → Task 2. §3.4 certified_campaign → Task 4. §3.5
schema → Task 3. §4 provenance/diagnostic blocks → Task 4 (`_provenance`,
`_scorer_diagnostic`, `_slice_persistence` refs, overall block). §5 tests 1-10 →
Task 1 (certify/eligibility/reject + existing paths), Task 2 (byte-stable/reset/
earn), Task 4 (provenance complete, persistence refs, conservative, deterministic,
CLI). §6 docs → Task 5 (incl. consciousness-levels update).

**Placeholder scan:** no `TODO`/`TBD`; the "tune predicates if" step (T4 S5) is a
diagnostic with exact print instructions. The `_paired_slice` returns `(slice,
ctx)`; only the grounded slice consumes `ctx` (for extra observed fields) — the
others discard it with `_`.

**Type consistency:** `certify(factory, probe_frames) -> dict` with keys
`passed/clone_equivalent/reset_deterministic/ordinal_invariant/implements_interface/
subject_factory` — defined Task 1, consumed Task 2/4. `is_certified`/`clear_registry`
Task 1, used Task 1/2/4 tests. `CertifiedBaselineSubjectFactory(seed_scars=...)`
callable, `certify_baseline_subject(seed_scars=...) -> (factory, result)` Task 2,
used Task 4. `run_certified_campaign(*, work_dir) -> dict` Task 4, used Task 4
tests. Provenance block keys (`subject_factory_eligible`, `runner_certified`,
`provenance_status`, `arm_output_sha256`, `input_frames_sha256`, `ordinal_invariant`,
`intervention_refs`, `state_persistence_refs`) match the Task 4 test assertions.
`write_campaign` reused from `campaign_report` (Task 4 of the prior plan).
Runner eligibility change matches `runner.py:81` exact current text.

```

```
