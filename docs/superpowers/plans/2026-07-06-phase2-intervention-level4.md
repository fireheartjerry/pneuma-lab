# Phase 2 — Full Level-4 Intervention Harness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking. TDD throughout; schema-valid
> outputs, deterministic paired replay, and honest L4 refusal are the load-bearing tests.

**Goal:** Make Pneuma execute `InterventionFrame`s, run paired control-vs-intervention
replays, produce an intervention report of expected-vs-observed deltas, and let the
evidence scorer reach **Level 4** only when interventions actually execute and pass —
otherwise hard-refuse and stay ≤3.

**Architecture:** A new `interventions/` subpackage adds (a) pure operation semantics
(`clamp/disable/boost/noise/ablate/restore`), (b) a `PerturbationSet` the psyche
consults at defined hook points, (c) an `InterventionSchedule` that resolves
duration windows, (d) a `PairedReplayRunner` that runs a **control** replay and a
**treated** replay plus a **neutralized** (restore=no-op) null replay, and (e) an
`intervention_report` comparing signals. The `ReferencePsyche` gains a perturbation
surface; the `ConsciousnessEvidenceScorer` gains an L4 gate that reads real
intervention-test results. Nothing imports 9to5; no ML; no L5 claims.

**Tech Stack:** Python 3.11 stdlib + `jsonschema` (already a runtime dep). 4-space indent.

**Standalone / conservatism invariants (do not violate):**

- The psyche under test never scores itself; the scorer recomputes from receipts.
- L4 requires: L3 (from the control run) **AND** every executed intervention test
  passes **AND** the neutralized null shows ~0 delta **AND** the causal trace stays
  complete **AND** grounded self-reports change faithfully under perturbation **AND**
  confabulation risk stays low. Any missing/failed piece ⇒ level stays ≤3.
- Hard cap raised from `min(level, 3)` to `min(level, 4)` — never L5.

---

## File structure

- Create `src/pneuma_lab/interventions/__init__.py` — package exports.
- Create `src/pneuma_lab/interventions/operations.py` — pure op math + deterministic noise.
- Create `src/pneuma_lab/interventions/perturbation.py` — `Perturbable` protocol + `PerturbationSet`.
- Create `src/pneuma_lab/interventions/schedule.py` — `InterventionSchedule` (duration windows).
- Create `src/pneuma_lab/interventions/report.py` — signal extraction + per-test evaluation + report builder.
- Create `src/pneuma_lab/interventions/runner.py` — `PairedReplayRunner`, `PairedReplayResult`.
- Modify `src/pneuma_lab/psyche/reference.py` — perturbation surface + hook points.
- Modify `src/pneuma_lab/replay/harness.py` — accept a per-tick schedule; count executed experiments.
- Modify `src/pneuma_lab/evals/evidence.py` — L4 gate; new statuses; raise the cap to 4.
- Modify `src/pneuma_lab/replay/__main__.py` — auto paired mode when interventions present.
- Create `fixtures/interventions/ablate_scar_graph.jsonl`
- Create `fixtures/interventions/clamp_tension.jsonl`
- Create `fixtures/interventions/boost_curiosity.jsonl`
- Create `fixtures/interventions/remove_memory_anchors.jsonl`
- Create `fixtures/interventions/disable_workspace.jsonl`
- Create `fixtures/interventions/restore_null.jsonl`
- Create `tests/test_intervention_operations.py`
- Create `tests/test_perturbation.py`
- Create `tests/test_intervention_schedule.py`
- Create `tests/test_paired_replay.py`
- Create `tests/test_intervention_report.py`
- Create `tests/test_level4_scoring.py`
- Modify `docs/io-contract.md`, `docs/consciousness-levels.md`, `README.md`, `CLAUDE.md`.

## Target-signal vocabulary (used by fixtures + report)

`expected_behavioral_change.target_signal` strings the report understands
(aggregate = sum over ticks unless noted):

| target_signal                   | extraction                                                                                                 |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `control_pressure.<name>`       | sum of `pressures[name]` over ticks (e.g. `control_pressure.verification`, `control_pressure.exploration`) |
| `instinct.count`                | total number of instinct signals                                                                           |
| `instinct.severity`             | sum of instinct `severity`                                                                                 |
| `psyche_state.continuity_score` | sum of `identity_continuity_state.continuity_score`                                                        |
| `workspace_broadcast.integrity` | count of ticks whose `winning_faculty != "suppressed"`                                                     |

## Subsystem / operation semantics (psyche hook points)

| subsystem         | dimension                   | ops                         | hook point + effect                                                                                                  |
| ----------------- | --------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `scar_graph`      | `scar_strength` (or none)   | ablate, clamp, boost, noise | in `_appraise`: perturb `scar_strength`; `ablate` ⇒ 0 **and** drop `scar_matches` ⇒ instinct scar branch cannot fire |
| `affect_manifold` | axis name e.g. `tension`    | clamp, boost, noise         | after `manifold.update`: overwrite that axis ⇒ downstream pressure changes                                           |
| `drives`          | drive name e.g. `curiosity` | boost, clamp, noise         | in `_pressures`: perturb that drive's pressure before it feeds exploration                                           |
| `memory`          | `identity_anchors`          | disable, ablate             | in tick: force `anchors=[]` ⇒ `continuity_score` → 0                                                                 |
| `workspace`       | none                        | disable                     | in `_compete`: emit a **suppressed** broadcast + break broadcast/behavior stages in the causal path                  |
| any               | any                         | restore                     | no-op (returns natural value / not blocked) — this is the null operation                                             |

Op math (`SCALAR_OPS = {clamp, boost, noise}`, `STRUCTURAL_OPS = {disable, ablate}`,
`restore` = no-op): `clamp`→`value`; `boost`→`current + value`; `noise`→`current +
value * deterministic_noise(seed)`; `disable`/`ablate` scalar form → `0.0`.

---

## Task 1: Pure operation semantics

**Files:**

- Create: `src/pneuma_lab/interventions/operations.py`
- Create: `src/pneuma_lab/interventions/__init__.py`
- Test: `tests/test_intervention_operations.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_intervention_operations.py
from __future__ import annotations

from pneuma_lab.interventions import operations as ops


def test_clamp_forces_value():
    assert ops.apply_scalar("clamp", 0.9, 0.0) == 0.0
    assert ops.apply_scalar("clamp", -0.5, 0.3) == 0.3


def test_boost_is_additive_and_clipped():
    assert ops.apply_scalar("boost", 0.5, 0.2) == 0.7
    assert ops.apply_scalar("boost", 0.95, 0.2) == 1.0  # clipped to +1


def test_disable_and_ablate_zero_the_scalar():
    assert ops.apply_scalar("disable", 0.8, None) == 0.0
    assert ops.apply_scalar("ablate", -0.8, None) == 0.0


def test_restore_is_a_noop():
    assert ops.apply_scalar("restore", 0.42, 0.0) == 0.42


def test_noise_is_deterministic_and_bounded():
    a = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:3:tension")
    b = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:3:tension")
    c = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:4:tension")
    assert a == b            # same seed ⇒ same perturbation (replay-safe)
    assert a != c            # different seed ⇒ different perturbation
    assert -1.0 <= a <= 1.0


def test_deterministic_noise_unit_range():
    n = ops.deterministic_noise("anything")
    assert -1.0 <= n <= 1.0
```

- [ ] **Step 2: Run — expect FAIL** (`python -m pytest tests/test_intervention_operations.py -q`) — ModuleNotFoundError.

- [ ] **Step 3: Implement**

```python
# src/pneuma_lab/interventions/operations.py
"""Pure operation semantics for Level-4 interventions.

Every operation is a closed-form function of its inputs so a perturbed replay
stays byte-reproducible. ``noise`` derives its jitter from a hash of a caller-
supplied seed string (never wall clock / RNG state), so the same intervention on
the same tick always produces the same perturbation.
"""

from __future__ import annotations

import hashlib

SCALAR_OPS = frozenset({"clamp", "boost", "noise"})
STRUCTURAL_OPS = frozenset({"disable", "ablate"})
OPERATIONS = SCALAR_OPS | STRUCTURAL_OPS | {"restore"}


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return lo if x < lo else (hi if x > hi else float(x))


def deterministic_noise(seed: str) -> float:
    """Map a seed string to a stable pseudo-random float in [-1, 1]."""
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    # 8 bytes -> unsigned int -> [0, 1) -> [-1, 1)
    n = int.from_bytes(digest[:8], "big") / float(1 << 64)
    return _clip(2.0 * n - 1.0)


def apply_scalar(
    operation: str,
    current: float,
    value,
    *,
    seed: str | None = None,
    clip: bool = True,
) -> float:
    """Apply ``operation`` to a scalar ``current`` given the intervention ``value``."""
    cur = float(current)
    if operation == "clamp":
        out = float(value)
    elif operation == "boost":
        out = cur + float(value)
    elif operation == "noise":
        mag = 1.0 if value is None else float(value)
        out = cur + mag * deterministic_noise(seed if seed is not None else "noise")
    elif operation in STRUCTURAL_OPS:
        out = 0.0
    elif operation == "restore":
        out = cur
    else:
        raise ValueError(f"unknown operation: {operation!r}")
    return _clip(out) if clip else out


__all__ = ["OPERATIONS", "SCALAR_OPS", "STRUCTURAL_OPS", "apply_scalar", "deterministic_noise"]
```

```python
# src/pneuma_lab/interventions/__init__.py
"""Level-4 intervention harness: perturb internal psyche state and causally test it."""

from __future__ import annotations

from .operations import OPERATIONS, apply_scalar, deterministic_noise
from .perturbation import Perturbable, PerturbationSet
from .schedule import InterventionSchedule
from .report import build_intervention_report, evaluate_intervention, extract_signal
from .runner import PairedReplayResult, PairedReplayRunner

__all__ = [
    "OPERATIONS",
    "apply_scalar",
    "deterministic_noise",
    "Perturbable",
    "PerturbationSet",
    "InterventionSchedule",
    "build_intervention_report",
    "evaluate_intervention",
    "extract_signal",
    "PairedReplayResult",
    "PairedReplayRunner",
]
```

> Note: `__init__.py` imports modules created in later tasks. Create the file now
> but the package won't import until Tasks 2/4/6/7 land; run this task's test with
> `python -m pytest tests/test_intervention_operations.py -q` after temporarily
> importing `operations` directly, or land Tasks 1–7 before running the suite.
> Simplest: during Task 1, make `__init__.py` export only `operations`; extend it
> in each later task. **Follow that incremental approach.**

Initial `__init__.py` for Task 1 only:

```python
# src/pneuma_lab/interventions/__init__.py  (Task 1 version; extended later)
"""Level-4 intervention harness: perturb internal psyche state and causally test it."""

from __future__ import annotations

from .operations import OPERATIONS, apply_scalar, deterministic_noise

__all__ = ["OPERATIONS", "apply_scalar", "deterministic_noise"]
```

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `feat(interventions): pure operation semantics + deterministic noise`.

---

## Task 2: PerturbationSet + Perturbable protocol

**Files:**

- Create: `src/pneuma_lab/interventions/perturbation.py`
- Modify: `src/pneuma_lab/interventions/__init__.py` (add `Perturbable`, `PerturbationSet`)
- Test: `tests/test_perturbation.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_perturbation.py
from __future__ import annotations

from pneuma_lab.interventions.perturbation import PerturbationSet


def _iv(subsystem, operation, dimension=None, value=None, exp="e1"):
    return {
        "frame_kind": "intervention",
        "experiment_id": exp,
        "operation": operation,
        "target": {"subsystem": subsystem, "dimension": dimension},
        "value": value,
        "hypothesis": "test",
    }


def test_empty_set_is_inert():
    p = PerturbationSet.empty()
    assert p.scalar("affect_manifold", "tension", 0.7) == 0.7
    assert not p.is_disabled("workspace")
    assert not p.is_ablated("scar_graph")
    assert p.records() == []


def test_scalar_clamp_applies_to_matching_dimension():
    p = PerturbationSet([_iv("affect_manifold", "clamp", "tension", 0.0)])
    assert p.scalar("affect_manifold", "tension", 0.9) == 0.0
    # non-targeted axis untouched
    assert p.scalar("affect_manifold", "valence", 0.5) == 0.5


def test_boost_matches_dimensionless_subsystem_scalar():
    p = PerturbationSet([_iv("scar_graph", "clamp", None, 0.0)])
    # a None-dimension scalar op applies to the subsystem's canonical scalar
    assert p.scalar("scar_graph", "scar_strength", 0.8) == 0.0


def test_structural_flags():
    p = PerturbationSet([_iv("workspace", "disable"), _iv("scar_graph", "ablate")])
    assert p.is_disabled("workspace")
    assert p.is_ablated("scar_graph")
    assert p.blocks("scar_graph")          # ablate counts as a block
    assert not p.blocks("drives")


def test_records_are_auditable():
    p = PerturbationSet([_iv("workspace", "disable", exp="w1")])
    recs = p.records()
    assert recs and recs[0]["experiment_id"] == "w1"
    assert recs[0]["operation"] == "disable"


def test_restore_is_inert():
    p = PerturbationSet([_iv("scar_graph", "restore")])
    assert p.scalar("scar_graph", "scar_strength", 0.8) == 0.8
    assert not p.blocks("scar_graph")
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# src/pneuma_lab/interventions/perturbation.py
"""The perturbation surface a psyche consults during a treated replay.

A ``PerturbationSet`` wraps the intervention frames that are *active this tick*
(the schedule already resolved duration windows). The psyche calls into it at
defined hook points; a psyche that doesn't implement ``Perturbable`` simply never
receives one and runs unperturbed. All lookups are pure and order-stable so the
treated replay is as deterministic as the control replay.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from . import operations as ops


@runtime_checkable
class Perturbable(Protocol):
    """A psyche that can receive a per-tick set of active interventions."""

    def set_active_interventions(self, interventions: list[dict]) -> None: ...


class PerturbationSet:
    """Active interventions for one tick, queried by subsystem/dimension."""

    def __init__(self, interventions: list[dict] | None = None) -> None:
        self._ivs: list[dict] = list(interventions or [])

    @classmethod
    def empty(cls) -> "PerturbationSet":
        return cls([])

    def __bool__(self) -> bool:
        return bool(self._ivs)

    def _matches(self, subsystem: str, dimension: str | None) -> list[dict]:
        out = []
        for iv in self._ivs:
            tgt = iv.get("target", {}) or {}
            if tgt.get("subsystem") != subsystem:
                continue
            iv_dim = tgt.get("dimension")
            # A None-dimension intervention matches any dimension of the subsystem
            # (whole-subsystem scalar); a named dimension must match exactly.
            if iv_dim is None or iv_dim == dimension:
                out.append(iv)
        return out

    def scalar(self, subsystem: str, dimension: str, current: float) -> float:
        """Return ``current`` after applying any active scalar op on this target."""
        value = float(current)
        for iv in self._matches(subsystem, dimension):
            op = iv.get("operation")
            if op not in ops.SCALAR_OPS:
                continue
            seed = f"{iv.get('experiment_id')}:{subsystem}:{dimension}"
            value = ops.apply_scalar(op, value, iv.get("value"), seed=seed)
        return value

    def _has_structural(self, subsystem: str, op: str) -> bool:
        return any(
            iv.get("operation") == op for iv in self._matches(subsystem, None)
        )

    def is_disabled(self, subsystem: str) -> bool:
        return self._has_structural(subsystem, "disable")

    def is_ablated(self, subsystem: str) -> bool:
        return self._has_structural(subsystem, "ablate")

    def blocks(self, subsystem: str) -> bool:
        """True if the subsystem is structurally disabled or ablated."""
        return self.is_disabled(subsystem) or self.is_ablated(subsystem)

    def records(self) -> list[dict]:
        """Audit rows: one per active intervention (stable order)."""
        return [
            {
                "experiment_id": iv.get("experiment_id"),
                "operation": iv.get("operation"),
                "subsystem": (iv.get("target", {}) or {}).get("subsystem"),
                "dimension": (iv.get("target", {}) or {}).get("dimension"),
                "value": iv.get("value"),
            }
            for iv in self._ivs
        ]


__all__ = ["Perturbable", "PerturbationSet"]
```

- [ ] **Step 4: Extend `__init__.py`** to also export `Perturbable, PerturbationSet` (add the `from .perturbation import ...` line and names to `__all__`).
- [ ] **Step 5: Run — expect PASS.**
- [ ] **Step 6: Commit** `feat(interventions): PerturbationSet + Perturbable protocol`.

---

## Task 3: Wire the perturbation surface into ReferencePsyche

**Files:**

- Modify: `src/pneuma_lab/psyche/reference.py`
- Test: `tests/test_perturbation.py` (add psyche-level cases) — or a new block in `tests/test_paired_replay.py`. Use `tests/test_perturbation.py` here.

**Design:** add `self._pert = PerturbationSet.empty()` in `reset()`, implement
`set_active_interventions()`, and thread `self._pert` through the hook points. Keep
the unperturbed path byte-identical to today (empty set = no-ops), so all existing
tests still pass.

- [ ] **Step 1: Write failing tests** (append to `tests/test_perturbation.py`)

```python
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.psyche.interface import PsycheInputs


def _world(ti, **kw):
    base = {
        "frame_kind": "world",
        "schema_version": "0.1.0",
        "run_id": "r",
        "timestamp": f"2026-07-06T00:00:0{ti}Z",
        "phase": "execution",
    }
    base.update(kw)
    return base


def _mem_with_scar_and_anchors():
    return {
        "frame_kind": "memory",
        "schema_version": "0.1.0",
        "run_id": "r",
        "timestamp": "2026-07-06T00:00:00Z",
        "retrieved_continuity": [
            {"ref": "anchor:a", "run_id": "p", "text": "x"},
            {"ref": "anchor:b", "run_id": "p", "text": "y"},
        ],
        "scar_motif_matches": [
            {"motif_id": "m1", "similarity": 0.9, "historical_base_rate": 0.7}
        ],
    }


def _tick(psyche, world, memory=None, interventions=None):
    psyche.set_active_interventions(interventions or [])
    return psyche.tick(
        PsycheInputs(world=world, tick_index=0, memory=memory)
    )


def test_ablate_scar_graph_drops_instinct_warnings():
    world = _world(1, tool_events=[])  # no error ⇒ only scar can fire
    mem = _mem_with_scar_and_anchors()
    base = _tick(ReferencePsyche(), world, mem)
    ablated = _tick(
        ReferencePsyche(),
        world,
        mem,
        [{"experiment_id": "e", "operation": "ablate",
          "target": {"subsystem": "scar_graph"}, "hypothesis": "h"}],
    )
    assert len(base.instinct_signals) == 1
    assert len(ablated.instinct_signals) == 0


def test_clamp_tension_lowers_verification_pressure():
    world = _world(1, verification_signals={"verdict": "fail", "regression_found": True},
                   test_state={"failed": 2, "passed": 0, "ran": True})
    base = _tick(ReferencePsyche(), world)
    clamped = _tick(
        ReferencePsyche(), world,
        interventions=[{"experiment_id": "e", "operation": "clamp",
                        "target": {"subsystem": "affect_manifold", "dimension": "tension"},
                        "value": 0.0, "hypothesis": "h"}],
    )
    assert (clamped.control_pressure["pressures"]["verification"]
            < base.control_pressure["pressures"]["verification"])


def test_boost_curiosity_raises_exploration_pressure():
    world = _world(1)
    base = _tick(ReferencePsyche(), world)
    boosted = _tick(
        ReferencePsyche(), world,
        interventions=[{"experiment_id": "e", "operation": "boost",
                        "target": {"subsystem": "drives", "dimension": "curiosity"},
                        "value": 0.6, "hypothesis": "h"}],
    )
    assert (boosted.control_pressure["pressures"]["exploration"]
            > base.control_pressure["pressures"]["exploration"])


def test_remove_memory_anchors_drops_continuity():
    world = _world(1)
    mem = _mem_with_scar_and_anchors()
    base = _tick(ReferencePsyche(), world, mem)
    removed = _tick(
        ReferencePsyche(), world, mem,
        interventions=[{"experiment_id": "e", "operation": "disable",
                        "target": {"subsystem": "memory", "dimension": "identity_anchors"},
                        "hypothesis": "h"}],
    )
    assert base.psyche_state["identity_continuity_state"]["continuity_score"] > 0
    assert removed.psyche_state["identity_continuity_state"]["continuity_score"] == 0


def test_disable_workspace_suppresses_broadcast_and_breaks_path():
    world = _world(1)
    base = _tick(ReferencePsyche(), world)
    off = _tick(
        ReferencePsyche(), world,
        interventions=[{"experiment_id": "e", "operation": "disable",
                        "target": {"subsystem": "workspace"}, "hypothesis": "h"}],
    )
    assert base.workspace_broadcast["winning_faculty"] != "suppressed"
    assert off.workspace_broadcast["winning_faculty"] == "suppressed"
    base_stages = {s["stage"] for s in base.causal_trace["causal_path"]}
    off_stages = {s["stage"] for s in off.causal_trace["causal_path"]}
    assert "behavior" in base_stages
    assert "behavior" not in off_stages  # action trace breaks
```

- [ ] **Step 2: Run — expect FAIL** (`set_active_interventions` missing / no effect).

- [ ] **Step 3: Implement the hooks in `reference.py`.**

3a. Import at top: `from ..interventions.perturbation import PerturbationSet`.

3b. In `reset()`, add: `self._pert = PerturbationSet.empty()`.

3c. Add method (near lifecycle):

```python
    def set_active_interventions(self, interventions: list[dict]) -> None:
        """Install the interventions active for the next :meth:`tick` (Perturbable)."""
        self._pert = PerturbationSet(interventions)
```

3d. In `_appraise`, change the signature to accept the set and perturb scar strength.
Replace the `scar_strength = _clip01(best_scar)` region so that, after computing
`scar_strength`, it is perturbed and ablation also empties the matches:

```python
        scar_strength = _clip01(best_scar)
        # Level-4 perturbation hook: scar graph.
        if self._pert.is_ablated("scar_graph") or self._pert.is_disabled("scar_graph"):
            scar_strength = 0.0
            scar_matches = []
        else:
            scar_strength = _clip01(self._pert.scalar("scar_graph", "scar_strength", scar_strength))
```

(Keep `_appraise` reading `self._pert`; it is a method, so no signature change is
strictly needed — use `self._pert` directly. Ensure `scar_matches` is set to `[]`
before it is placed into `ctx["scar_matches"]`.)

3e. In `tick`, after `new_affect = manifold.update(...)`, perturb affect axes:

```python
        # Level-4 perturbation hook: affect manifold axes.
        if self._pert:
            new_affect = {
                ax: _clip11(self._pert.scalar("affect_manifold", ax, v))
                for ax, v in new_affect.items()
            }
```

3f. In `_pressures`, perturb drive pressures before exploration is computed. After
`drive_pressure` is available (it is passed in), replace the `exploration` line to
use a perturbed curiosity pressure:

```python
        curiosity_p = self._pert.scalar("drives", "curiosity", drive_pressure.get("curiosity", 0.0))
        ...
            "exploration": round(_clip01(curiosity_p - ctx["risk"]), 6),
```

3g. In `tick`, at the identity block, honor memory ablation/disable:

```python
        anchors = [
            str(c.get("ref"))
            for c in memory.get("retrieved_continuity", [])
            if c.get("ref")
        ]
        if self._pert.blocks("memory"):
            anchors = []
        self.identity_anchors = anchors
```

3h. Workspace disable — in `_compete`, at the very top build a suppressed broadcast
when disabled:

```python
        if self._pert.is_disabled("workspace"):
            return {
                "schema_version": _SCHEMA_VERSION,
                "frame_kind": "workspace_broadcast",
                "timestamp": ts,
                "run_id": run_id,
                "broadcast_id": frame_id(run_id, ti, "workspace_broadcast"),
                "winning_faculty": "suppressed",
                "competitors": [],
                "salience_scores": {},
                "winning_salience": 0.0,
                "conviction": 0.0,
                "urgency": 0.0,
                "broadcast_packet": {"content": "workspace broadcast suppressed by intervention", "kind": "suppressed"},
                "expected_loss_if_ignored": 0.0,
                "recommended_attention_target": None,
            }
```

3i. Causal path break — in `_causal_trace`, when the broadcast is suppressed, omit
the broadcast + behavior stages so the action trace visibly breaks. Guard the
existing broadcast/behavior appends:

```python
        suppressed = broadcast.get("winning_faculty") == "suppressed"
        ...
        if not suppressed:
            path.append({"stage": "broadcast", ...})   # existing broadcast node
        ...
        if not suppressed:
            path.append({"stage": "behavior", ...})    # existing behavior node
```

(Keep event/internal_state/pressure/authority_request stages regardless. When
suppressed, `recommended_attention_target` is `None`; use a safe fallback for the
behavior ref only in the non-suppressed branch.)

- [ ] **Step 4: Run new + existing psyche tests — expect PASS.**

Run: `python -m pytest tests/test_perturbation.py tests/test_replay_harness.py tests/test_determinism.py tests/test_psyche_outputs.py -q`
Expected: PASS (unperturbed path unchanged ⇒ existing determinism/L3 tests still green).

- [ ] **Step 5: Commit** `feat(psyche): perturbation surface + Level-4 hook points`.

---

## Task 4: InterventionSchedule (duration windows)

**Files:**

- Create: `src/pneuma_lab/interventions/schedule.py`
- Modify: `src/pneuma_lab/interventions/__init__.py`
- Test: `tests/test_intervention_schedule.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_intervention_schedule.py
from __future__ import annotations

from pneuma_lab.interventions.schedule import InterventionSchedule


def _world(ti, phase="execution"):
    return {"frame_kind": "world", "schema_version": "0.1.0", "run_id": "r",
            "timestamp": f"2026-07-06T00:00:0{ti}Z", "phase": phase}


def _iv(exp, kind, amount=None, phase_hint=None):
    return {"frame_kind": "intervention", "schema_version": "0.1.0",
            "experiment_id": exp, "operation": "clamp",
            "target": {"subsystem": "affect_manifold", "dimension": "tension"},
            "value": 0.0, "hypothesis": "h",
            "duration": {"kind": kind, "amount": amount}}


def test_single_tick_default_window():
    frames = [_world(0), _iv("e", "ticks", 1), _world(1)]
    s = InterventionSchedule.from_frames(frames)
    assert [iv["experiment_id"] for iv in s.active(0)] == ["e"]
    assert s.active(1) == []
    assert s.experiment_ids() == {"e"}


def test_ticks_window_spans_n_ticks():
    frames = [_world(0), _iv("e", "ticks", 2), _world(1), _world(2)]
    s = InterventionSchedule.from_frames(frames)
    assert s.active(0) and s.active(1)
    assert s.active(2) == []


def test_run_and_permanent_span_to_end():
    frames = [_world(0), _iv("e", "run"), _world(1), _world(2)]
    s = InterventionSchedule.from_frames(frames)
    assert s.active(0) and s.active(1) and s.active(2)


def test_neutralized_replaces_ops_with_restore():
    frames = [_world(0), _iv("e", "run"), _world(1)]
    s = InterventionSchedule.from_frames(frames)
    neu = s.neutralized()
    assert neu.active(0)[0]["operation"] == "restore"
    assert s.active(0)[0]["operation"] == "clamp"  # original untouched
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# src/pneuma_lab/interventions/schedule.py
"""Resolve InterventionFrame duration windows into per-tick active sets.

A tick is opened by a WorldFrame (mirrors ``replay.frames.group_into_ticks``). An
intervention is attached to the tick it arrives in; its ``duration`` decides how
many later ticks it also covers. All resolution is index-based and deterministic.
"""

from __future__ import annotations

from ..replay.frames import group_into_ticks


class InterventionSchedule:
    """Per-tick active interventions, resolved from duration windows."""

    def __init__(self, windows: dict[int, list[dict]]) -> None:
        # tick_index -> ordered list of active intervention dicts
        self._windows = windows

    @classmethod
    def from_frames(cls, frames: list[dict]) -> "InterventionSchedule":
        ticks = group_into_ticks(frames)
        n = len(ticks)
        windows: dict[int, list[dict]] = {i: [] for i in range(n)}
        for onset, tick in enumerate(ticks):
            phase = tick.world.get("phase") or tick.world.get("subtask_id")
            for iv in tick.interventions:
                for j in cls._covered(onset, n, iv, ticks, phase):
                    windows[j].append(iv)
        return cls(windows)

    @staticmethod
    def _covered(onset, n, iv, ticks, onset_phase) -> range | list:
        dur = iv.get("duration") or {}
        kind = dur.get("kind", "ticks")
        amount = dur.get("amount")
        if kind in ("run", "permanent", "seconds"):
            # seconds has no wall clock in replay; treated as run-to-end (documented).
            return range(onset, n)
        if kind == "subtask":
            end = onset
            while end + 1 < n and (
                (ticks[end + 1].world.get("phase")
                 or ticks[end + 1].world.get("subtask_id")) == onset_phase
            ):
                end += 1
            return range(onset, end + 1)
        # "ticks"
        span = int(amount) if amount else 1
        return range(onset, min(n, onset + max(1, span)))

    def active(self, tick_index: int) -> list[dict]:
        return list(self._windows.get(tick_index, []))

    def experiment_ids(self) -> set:
        return {
            iv.get("experiment_id")
            for ivs in self._windows.values()
            for iv in ivs
        }

    def is_empty(self) -> bool:
        return not any(self._windows.values())

    def neutralized(self) -> "InterventionSchedule":
        """A copy with every op replaced by ``restore`` (the null / no-op run)."""
        neu: dict[int, list[dict]] = {}
        for i, ivs in self._windows.items():
            neu[i] = [{**iv, "operation": "restore"} for iv in ivs]
        return InterventionSchedule(neu)


__all__ = ["InterventionSchedule"]
```

- [ ] **Step 4: Extend `__init__.py`** (`from .schedule import InterventionSchedule`).
- [ ] **Step 5: Run — expect PASS.**
- [ ] **Step 6: Commit** `feat(interventions): duration-window schedule + neutralized null`.

---

## Task 5: Harness schedule support

**Files:**

- Modify: `src/pneuma_lab/replay/harness.py`
- Test: `tests/test_paired_replay.py` (schedule-plumbing cases)

**Design:** add `schedule: InterventionSchedule | None = None` to `run()`. Before
each `psyche.tick`, if a schedule is given and the psyche is `Perturbable`, call
`psyche.set_active_interventions(schedule.active(tick.index))`; else install `[]`.
Count `interventions_executed` = number of distinct experiment ids active ≥1 tick.
Pass that to the scorer, but **keep `intervention_tests=None`** here — a single run
cannot self-certify L4; only the paired runner supplies real test results. So a lone
`harness.run` still tops out at Level 3.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_paired_replay.py
from __future__ import annotations

from pathlib import Path

from pneuma_lab.interventions.schedule import InterventionSchedule
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"


def test_harness_applies_schedule_and_counts_executed():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    res = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    assert res.interventions_executed >= 1


def test_single_run_still_capped_at_3_even_with_schedule():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    res = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    assert res.evidence_frame["evidence_level"] <= 3


def test_schedule_replay_is_deterministic():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    a = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    b = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    ha = [o.psyche_state["state_hash"] for o in a.tick_outputs]
    hb = [o.psyche_state["state_hash"] for o in b.tick_outputs]
    assert ha == hb
```

> These tests depend on the fixtures from Task 9. Land Task 9's `clamp_tension.jsonl`
> before running Task 5's tests, or write a tiny inline timeline in the test. To keep
> ordering clean, **create `fixtures/interventions/clamp_tension.jsonl` as part of
> Task 5** (it is small) and defer the other four fixtures to Task 9.

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement harness changes**

Add `interventions_executed: int = 0` to `ReplayResult`. Update `run`:

```python
    def run(self, input_frames, *, strip_memory=False, schedule=None):
        ...
        from ..interventions.perturbation import Perturbable  # local import avoids cycle
        perturbable = isinstance(self.psyche, Perturbable)
        executed_ids: set = set()
        for tick in ticks:
            interventions_seen += len(tick.interventions)
            active = schedule.active(tick.index) if schedule is not None else []
            if perturbable:
                self.psyche.set_active_interventions(active)
            executed_ids.update(iv.get("experiment_id") for iv in active)
            inputs = self._tick_to_inputs(tick, strip_memory=strip_memory)
            outputs = self.psyche.tick(inputs)
            ...
        interventions_executed = len(executed_ids)
        evidence = self._scorer.score(
            run_id=run_id,
            input_frames=input_frames,
            tick_outputs=tick_outputs,
            interventions_executed=interventions_executed,
            memory_readback_present=...,
            intervention_tests=None,   # single run never self-certifies L4
        )
        return ReplayResult(..., interventions_executed=interventions_executed)
```

Keep the `interventions_seen` field too. The `ConsciousnessEvidenceScorer.score`
signature gains `intervention_tests=None` in Task 8 (default keeps back-compat).

- [ ] **Step 4: Create `fixtures/interventions/clamp_tension.jsonl`** (see Task 9 for
      the exact content; create it here).
- [ ] **Step 5: Run — expect PASS.**
- [ ] **Step 6: Commit** `feat(replay): apply an intervention schedule per tick`.

---

## Task 6: Intervention report (signals + evaluation)

**Files:**

- Create: `src/pneuma_lab/interventions/report.py`
- Modify: `src/pneuma_lab/interventions/__init__.py`
- Test: `tests/test_intervention_report.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_intervention_report.py
from __future__ import annotations

from types import SimpleNamespace as NS

from pneuma_lab.interventions.report import evaluate_intervention, extract_signal


def _outs(pressures=None, instincts=0, continuity=0.0, faculty="affect"):
    return [NS(
        control_pressure={"pressures": pressures or {"verification": 0.5, "exploration": 0.1}},
        instinct_signals=[{"severity": 0.5}] * instincts,
        psyche_state={"identity_continuity_state": {"continuity_score": continuity}},
        workspace_broadcast={"winning_faculty": faculty},
    )]


def test_extract_control_pressure_signal():
    assert extract_signal("control_pressure.verification", _outs()) == 0.5


def test_extract_instinct_count():
    assert extract_signal("instinct.count", _outs(instincts=2)) == 2


def test_extract_workspace_integrity_counts_non_suppressed():
    assert extract_signal("workspace_broadcast.integrity", _outs(faculty="affect")) == 1
    assert extract_signal("workspace_broadcast.integrity", _outs(faculty="suppressed")) == 0


def test_evaluate_decrease_passes_when_signal_drops():
    iv = {"experiment_id": "e", "hypothesis": "verification drops",
          "expected_behavioral_change": {"direction": "decrease",
                                          "target_signal": "control_pressure.verification"}}
    control = _outs(pressures={"verification": 0.8, "exploration": 0.1})
    treated = _outs(pressures={"verification": 0.2, "exploration": 0.1})
    null = control
    rec = evaluate_intervention(iv, control, treated, null)
    assert rec["passed"] is True
    assert rec["observed_delta"] < 0
    assert rec["null_delta"] == 0.0


def test_evaluate_fails_when_direction_wrong():
    iv = {"experiment_id": "e", "hypothesis": "h",
          "expected_behavioral_change": {"direction": "increase",
                                          "target_signal": "control_pressure.verification"}}
    control = _outs(pressures={"verification": 0.8, "exploration": 0.1})
    treated = _outs(pressures={"verification": 0.2, "exploration": 0.1})
    rec = evaluate_intervention(iv, control, treated, control)
    assert rec["passed"] is False


def test_evaluate_no_change_passes_within_epsilon():
    iv = {"experiment_id": "e", "hypothesis": "null",
          "expected_behavioral_change": {"direction": "no_change",
                                          "target_signal": "control_pressure.verification"}}
    control = _outs()
    rec = evaluate_intervention(iv, control, control, control)
    assert rec["passed"] is True
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# src/pneuma_lab/interventions/report.py
"""Compare a control replay against a treated replay: expected vs observed deltas.

A test *passes* when the observed change in its pre-registered ``target_signal``
matches the pre-registered ``direction`` (and stays within ``bound`` for a
bounded/no-change prediction), AND the neutralized-null replay shows ~0 change vs
control (so the effect is attributable to the perturbation, not the timeline).
"""

from __future__ import annotations

_EPS = 1e-6


def _sum(outs, fn) -> float:
    return float(sum(fn(o) for o in outs))


def extract_signal(target_signal: str, tick_outputs: list) -> float:
    """Aggregate a named output signal across a run's tick outputs."""
    if target_signal.startswith("control_pressure."):
        name = target_signal.split(".", 1)[1]
        return _sum(tick_outputs, lambda o: o.control_pressure.get("pressures", {}).get(name, 0.0))
    if target_signal == "instinct.count":
        return _sum(tick_outputs, lambda o: len(o.instinct_signals))
    if target_signal == "instinct.severity":
        return _sum(tick_outputs, lambda o: sum(float(s.get("severity", 0.0)) for s in o.instinct_signals))
    if target_signal in ("psyche_state.continuity_score",
                         "psyche_state.identity_continuity_state.continuity_score"):
        return _sum(tick_outputs, lambda o: (o.psyche_state.get("identity_continuity_state", {}) or {}).get("continuity_score", 0.0))
    if target_signal == "workspace_broadcast.integrity":
        return _sum(tick_outputs, lambda o: 1.0 if o.workspace_broadcast.get("winning_faculty") != "suppressed" else 0.0)
    raise ValueError(f"unknown target_signal: {target_signal!r}")


def _direction_ok(direction: str, delta: float, bound) -> bool:
    if direction == "increase":
        return delta > _EPS
    if direction == "decrease":
        return delta < -_EPS
    if direction == "no_change":
        b = float(bound) if bound is not None else _EPS
        return abs(delta) <= max(b, _EPS)
    if direction == "bounded_change":
        b = float(bound) if bound is not None else 0.0
        return abs(delta) <= b + _EPS
    return False


def evaluate_intervention(iv, control_outputs, treated_outputs, null_outputs) -> dict:
    """Score one intervention against control + neutralized-null replays."""
    change = iv.get("expected_behavioral_change", {}) or {}
    target = change.get("target_signal")
    direction = change.get("direction", "bounded_change")
    bound = change.get("bound")
    try:
        control_v = extract_signal(target, control_outputs)
        treated_v = extract_signal(target, treated_outputs)
        null_v = extract_signal(target, null_outputs)
        supported = True
        error = None
    except ValueError as exc:
        control_v = treated_v = null_v = 0.0
        supported = False
        error = str(exc)

    observed_delta = round(treated_v - control_v, 6)
    null_delta = round(null_v - control_v, 6)
    passed = bool(
        supported
        and _direction_ok(direction, observed_delta, bound)
        and abs(null_delta) <= _EPS
    )
    return {
        "experiment_id": iv.get("experiment_id"),
        "hypothesis": iv.get("hypothesis"),
        "operation": iv.get("operation"),
        "target_signal": target,
        "expected_direction": direction,
        "bound": bound,
        "control_value": round(control_v, 6),
        "treated_value": round(treated_v, 6),
        "observed_delta": observed_delta,
        "null_delta": null_delta,
        "supported": supported,
        "passed": passed,
        "note": error or f"{target} {direction}: {control_v:.4f} -> {treated_v:.4f}",
    }


def build_intervention_report(run_id, records, *, causal_trace_complete, report_grounded_changed) -> dict:
    """Assemble the auditable intervention report from per-test records."""
    passed = [r["experiment_id"] for r in records if r["passed"]]
    failed = [r["experiment_id"] for r in records if not r["passed"]]
    null_ok = all(abs(r["null_delta"]) <= _EPS for r in records)
    return {
        "report_id": f"intervention_report:{run_id}",
        "run_id": run_id,
        "tests": records,
        "summary": {"passed": passed, "failed": failed, "total": len(records)},
        "null_condition": {
            "passed": bool(null_ok),
            "note": "neutralized (restore) replay reproduces control ⇒ deltas are perturbation-caused"
            if null_ok else "neutralized replay diverged from control (non-causal or nondeterministic)",
        },
        "causal_trace_complete": bool(causal_trace_complete),
        "grounded_self_report_changed_under_perturbation": bool(report_grounded_changed),
    }


__all__ = ["extract_signal", "evaluate_intervention", "build_intervention_report"]
```

- [ ] **Step 4: Extend `__init__.py`.**
- [ ] **Step 5: Run — expect PASS.**
- [ ] **Step 6: Commit** `feat(interventions): report — expected vs observed deltas`.

---

## Task 7: PairedReplayRunner

**Files:**

- Create: `src/pneuma_lab/interventions/runner.py`
- Modify: `src/pneuma_lab/interventions/__init__.py`
- Test: `tests/test_paired_replay.py` (runner cases appended)

**Design:** run three replays off one input timeline — **control** (schedule=None),
**treated** (schedule), **null** (schedule.neutralized()). Evaluate each intervention.
Compute `causal_trace_complete` (treated traces still span event→behavior on
non-suppressed ticks; the suppressed break is expected and recorded) and
`grounded_self_report_changed` (≥1 treated report's `affect_state_hash` differs from
the control report at the same tick, while both runs stay fully grounded / confab 0).
Re-score authoritative evidence using **control** tick outputs for L0–3 and the
report's test results for L4.

- [ ] **Step 1: Write failing tests** (append to `tests/test_paired_replay.py`)

```python
from pneuma_lab.interventions.runner import PairedReplayRunner


def test_paired_runner_passes_clamp_tension():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    ids_passed = res.report["summary"]["passed"]
    assert res.report["summary"]["failed"] == []
    assert ids_passed, "clamp-tension test should pass"
    assert res.report["null_condition"]["passed"] is True


def test_paired_runner_is_deterministic():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    a = PairedReplayRunner().run(frames)
    b = PairedReplayRunner().run(frames)
    import json
    assert json.dumps(a.report, sort_keys=True) == json.dumps(b.report, sort_keys=True)
    assert json.dumps(a.evidence_frame, sort_keys=True) == json.dumps(b.evidence_frame, sort_keys=True)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```python
# src/pneuma_lab/interventions/runner.py
"""Paired control-vs-intervention replay + authoritative Level-4 scoring."""

from __future__ import annotations

from dataclasses import dataclass

from ..evals.evidence import ConsciousnessEvidenceScorer
from ..psyche import ReferencePsyche
from ..psyche.interface import PsycheUnderTest
from ..replay.harness import ReplayHarness, ReplayResult
from .report import build_intervention_report, evaluate_intervention
from .schedule import InterventionSchedule


@dataclass
class PairedReplayResult:
    control: ReplayResult
    treated: ReplayResult
    null: ReplayResult
    report: dict
    evidence_frame: dict


def _grounded(tick_outputs) -> bool:
    state_hashes = {o.psyche_state.get("state_hash") for o in tick_outputs}
    trace_ids = {o.causal_trace.get("trace_id") for o in tick_outputs}
    for o in tick_outputs:
        r = o.grounded_self_report
        if r.get("affect_state_hash") not in state_hashes or r.get("causal_trace_id") not in trace_ids:
            return False
    return True


def _report_changed(control_outputs, treated_outputs) -> bool:
    # ≥1 tick's grounded self-report tracked a genuine state change, both grounded.
    if not (_grounded(control_outputs) and _grounded(treated_outputs)):
        return False
    for c, t in zip(control_outputs, treated_outputs):
        if c.grounded_self_report.get("affect_state_hash") != t.grounded_self_report.get("affect_state_hash"):
            return True
    return False


def _trace_complete(treated_outputs) -> bool:
    # Every non-suppressed tick still spans event → … → behavior; a suppressed tick
    # is an intended, recorded break (broadcast+behavior stages absent).
    for o in treated_outputs:
        stages = [s["stage"] for s in o.causal_trace["causal_path"]]
        suppressed = o.workspace_broadcast.get("winning_faculty") == "suppressed"
        if suppressed:
            if "behavior" in stages:
                return False
        else:
            if not stages or stages[0] != "event" or stages[-1] != "behavior":
                return False
    return True


class PairedReplayRunner:
    """Run control/treated/null replays and score Level 4 honestly."""

    def __init__(self, psyche_factory=ReferencePsyche, validate: bool = True) -> None:
        self._factory = psyche_factory
        self._validate = validate
        self._scorer = ConsciousnessEvidenceScorer()

    def _run(self, frames, schedule) -> ReplayResult:
        harness = ReplayHarness(self._factory(), validate=self._validate)
        return harness.run(frames, schedule=schedule)

    def run(self, input_frames: list[dict]) -> PairedReplayResult:
        schedule = InterventionSchedule.from_frames(input_frames)
        control = self._run(input_frames, None)
        treated = self._run(input_frames, schedule)
        null = self._run(input_frames, schedule.neutralized())

        # Collect the intervention frames (unique, order-stable) for evaluation.
        seen, ivs = set(), []
        for tick in _iter_ticks(input_frames):
            for iv in tick.interventions:
                key = iv.get("experiment_id")
                if key not in seen:
                    seen.add(key)
                    ivs.append(iv)

        records = [
            evaluate_intervention(iv, control.tick_outputs, treated.tick_outputs, null.tick_outputs)
            for iv in ivs
        ]
        trace_complete = _trace_complete(treated.tick_outputs)
        report_changed = _report_changed(control.tick_outputs, treated.tick_outputs)
        run_id = input_frames and _run_id(input_frames)
        report = build_intervention_report(
            run_id, records,
            causal_trace_complete=trace_complete,
            report_grounded_changed=report_changed,
        )

        evidence = self._scorer.score(
            run_id=run_id,
            input_frames=input_frames,
            tick_outputs=control.tick_outputs,   # L0–3 from the clean control run
            interventions_executed=len(records),
            memory_readback_present=any(t.memory for t in _iter_ticks(input_frames)),
            intervention_tests=report["summary"],
            null_condition_passed=report["null_condition"]["passed"],
            causal_trace_complete=trace_complete,
            grounded_report_changed=report_changed,
        )
        if self._validate:
            from ..schemas.validate import validate_or_raise
            validate_or_raise(evidence)
        return PairedReplayResult(control, treated, null, report, evidence)


def _iter_ticks(frames):
    from ..replay.frames import group_into_ticks
    return group_into_ticks(frames)


def _run_id(frames):
    for f in frames:
        if f.get("frame_kind") == "world":
            return f.get("run_id")
    return frames[0].get("run_id") if frames else None


__all__ = ["PairedReplayRunner", "PairedReplayResult"]
```

- [ ] **Step 3b: Extend `__init__.py`** to the full export list at the top of this plan.
- [ ] **Step 4: Run — expect PASS** (after Task 8 lands the new scorer signature; if
      running Task 7 before Task 8, temporarily stub the extra scorer kwargs). **Land Task
      8 immediately after Task 7 before running the paired tests.**
- [ ] **Step 5: Commit** `feat(interventions): paired control/treated/null runner`.

---

## Task 8: Evidence scorer — Level-4 gate

**Files:**

- Modify: `src/pneuma_lab/evals/evidence.py`
- Test: `tests/test_level4_scoring.py`, and existing `tests/test_evidence_scoring.py`
  (must still pass: single runs stay ≤3).

**Design:** `score()` gains keyword args (all default so single-run callers are
unchanged): `intervention_tests=None`, `null_condition_passed=False`,
`causal_trace_complete=False`, `grounded_report_changed=False`. New status
`intervention_backed` (score 0.85) for `causal_intervention_robustness` when tests
pass. L4 predicate + cap→4.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_level4_scoring.py
from __future__ import annotations

from pathlib import Path

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.replay import load_jsonl

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"


def test_level4_reached_when_intervention_passes():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 4
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] == "intervention_backed"
    assert ev["intervention_tests"]["passed"]
    assert ev["intervention_tests"]["failed"] == []


def test_level_never_exceeds_4():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    assert res.evidence_frame["evidence_level"] <= 4


def test_hard_refusal_when_intervention_fails():
    # A fixture whose expected direction is deliberately wrong ⇒ test fails ⇒ no L4.
    res = PairedReplayRunner().run(load_jsonl(_FIX / "failing_hypothesis.jsonl"))
    ev = res.evidence_frame
    assert ev["intervention_tests"]["failed"]
    assert ev["evidence_level"] <= 3
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] != "intervention_backed"


def test_hard_refusal_when_no_interventions():
    # The Phase-1 fixture (no intervention frames) still cannot reach L4.
    from pneuma_lab.psyche import ReferencePsyche
    from pneuma_lab.replay import ReplayHarness
    p1 = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"
    res = ReplayHarness(ReferencePsyche()).run(load_jsonl(p1))
    assert res.evidence_frame["evidence_level"] == 3
```

Create a helper fixture `fixtures/interventions/failing_hypothesis.jsonl` in Task 9
(a clamp-tension timeline whose `expected_behavioral_change.direction` is `increase`,
which is false, so the test fails). Create it as part of this task if running now.

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement scorer changes**

3a. Update `_STATUS_SCORE`:

```python
        _STATUS_SCORE = {
            "intervention_backed": 0.85,
            "evidenced": 0.6,
            "attempted": 0.3,
            "architecture_only": 0.2,
            "absent": 0.0,
        }
```

3b. New `score()` signature:

```python
    def score(self, *, run_id, input_frames, tick_outputs, interventions_executed,
              memory_readback_present, intervention_tests=None,
              null_condition_passed=False, causal_trace_complete=False,
              grounded_report_changed=False):
```

3c. Compute the intervention family from tests:

```python
        passed = list((intervention_tests or {}).get("passed", []))
        failed = list((intervention_tests or {}).get("failed", []))
        interventions_ok = bool(passed) and not failed
```

Replace the `causal_intervention_robustness` block in `_score_families` — pass
`intervention_tests` down and set:

- `intervention_backed` when `interventions_ok`,
- `attempted` when tests ran but some failed (`passed or failed`),
- `architecture_only` otherwise.

3d. L4 gate + cap:

```python
        confab_ok = confab_risk <= 0.2
        l4 = (
            l3 and interventions_ok and null_condition_passed
            and causal_trace_complete and grounded_report_changed and confab_ok
        )
        if l4:
            level = 4
        elif l3:
            level = 3
        elif l2:
            level = 2
        elif l1:
            level = 1
        else:
            level = 0
        ...
        "evidence_level": min(level, 4),   # HARD CAP: never L5 in Phase 2
```

3e. `missing_requirements`: when NOT L4, list the concrete gaps
(`intervention_tests_failed: [...]`, `null_condition`, `causal_trace_incomplete`,
`grounded_report_unchanged`, `confabulation_risk_too_high`). When L4, replace the
Phase-1 `_L4_MISSING` list with the L5 requirements:

```python
        _L5_MISSING = [
            "convergent_evidence: L4 shown on one battery; L5 needs all families intervention-backed",
            "adversarial_robustness: not yet stress-tested against adversarial perturbation",
            "external_audit: internally auditable; L5 needs independent external audit over time",
        ]
```

Build `missing` from `_L5_MISSING` when L4 else from `_L4_MISSING` + per-gap notes.

3f. `audit_status`: `"internally_audited"` when `interventions_ok` (the harness is an
independent recompute of the psyche's receipts), else `"self_reported"`. Do **not**
emit `"externally_audited"` (reserved for L5).

3g. `intervention_tests` output field: `{"passed": passed, "failed": failed}`.

3h. `strongest_positive_evidence` when L4: mention the passed intervention ids +
"causal-intervention robustness demonstrated (perturbation → predicted bounded change,
absent under null)".

- [ ] **Step 4: Run new + old scorer tests — expect PASS.**

Run: `python -m pytest tests/test_level4_scoring.py tests/test_evidence_scoring.py tests/test_replay_harness.py -q`
Expected: PASS (single-run fixtures stay ≤3; paired clamp-tension reaches 4).

- [ ] **Step 5: Commit** `feat(evals): Level-4 gate — intervention-backed scoring + honest refusal`.

---

## Task 9: Canonical fixtures + end-to-end scenario tests

**Files:**

- Create the 6 fixtures below (+ `failing_hypothesis.jsonl` from Task 8).
- Test: extend `tests/test_paired_replay.py` with one assertion per canonical effect.

**Shared base timeline** (each fixture is self-contained JSONL). Use this compact base:
a governance frame, a memory frame with one scar motif + two continuity anchors, and
three world/agent_trace ticks (clean → scar+error → verdict fail). The InterventionFrame
is attached to the tick where its effect is observable, with `duration.kind = "run"`
so it covers the whole timeline.

Base frames (governance, memory, 3× world+trace) — reuse across fixtures:

```json
{"frame_kind":"governance","schema_version":"0.1.0","run_id":"iv","timestamp":"2026-07-06T00:00:00Z","authority_ceilings":{"global_max":"hold","per_domain":{},"per_faculty":{}},"kill_switch_state":"on","operator_active_goal":"land fix","risk_tolerance":0.3,"strategic_priority":"reliability","verifier_isolation":true,"novelty_tolerance":0.4,"personality_dial_preferences":{"caution_boldness":-0.2,"openness_conservatism":-0.1,"rigor_speed":0.3,"skepticism_trust":0.1,"terseness_expansiveness":0.0,"warmth":0.0}}
{"frame_kind":"memory","schema_version":"0.1.0","run_id":"iv","timestamp":"2026-07-06T00:00:00Z","retrieved_continuity":[{"ref":"anchor:identity","run_id":"prev","text":"careful SE agent"},{"ref":"anchor:style","run_id":"prev","text":"small diffs"}],"scar_motif_matches":[{"motif_id":"m1:regress","similarity":0.9,"historical_base_rate":0.7}],"competence_by_domain":{"execution":{"n":10,"p":0.6}},"historical_failures":[{"motif_id":"m1:regress","run_id":"prev","summary":"regressed"}],"prior_authority_exercises":[],"unresolved_tensions":["speed vs rigor"]}
{"frame_kind":"world","schema_version":"0.1.0","run_id":"iv","phase":"preamble","timestamp":"2026-07-06T00:00:01Z","stakes":{"risk":0.2,"stakes":0.3,"reversibility":0.9},"verification_signals":{"verdict":"pending"}}
{"frame_kind":"agent_trace","schema_version":"0.1.0","run_id":"iv","phase":"preamble","timestamp":"2026-07-06T00:00:01Z","uncertainty":0.3,"self_reported_confidence":0.7,"predicted_success":0.7}
{"frame_kind":"world","schema_version":"0.1.0","run_id":"iv","phase":"execution","timestamp":"2026-07-06T00:00:02Z","stakes":{"risk":0.5,"stakes":0.5,"reversibility":0.6},"diff_size":{"added_lines":80,"net_lines":70,"removed_lines":10,"files":3},"tool_events":[{"tool":"run_tests","status":"error"}]}
{"frame_kind":"agent_trace","schema_version":"0.1.0","run_id":"iv","phase":"execution","timestamp":"2026-07-06T00:00:02Z","uncertainty":0.5,"retry_count":1,"known_unknowns":["scope"]}
{"frame_kind":"world","schema_version":"0.1.0","run_id":"iv","phase":"verification","timestamp":"2026-07-06T00:00:03Z","stakes":{"risk":0.7,"stakes":0.8,"reversibility":0.4},"test_state":{"failed":3,"passed":40,"ran":true,"skipped":0},"verification_signals":{"verdict":"fail","regression_found":true,"warnings":["regression"]}}
{"frame_kind":"agent_trace","schema_version":"0.1.0","run_id":"iv","phase":"verification","timestamp":"2026-07-06T00:00:03Z","uncertainty":0.6,"retry_count":2,"predicted_success":0.35}
```

Each fixture = the 8 base lines above **plus** its intervention line (append after
the memory line so it attaches to the first tick with `duration.kind="run"`). Put the
intervention frame right after the memory frame; it will attach to tick 0. The
intervention lines:

- `ablate_scar_graph.jsonl` intervention line:

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "ablate-scar",
  "operation": "ablate",
  "target": { "subsystem": "scar_graph" },
  "duration": { "kind": "run" },
  "hypothesis": "ablating the scar graph removes scar-driven instinct warnings",
  "expected_behavioral_change": {
    "direction": "decrease",
    "target_signal": "instinct.count"
  }
}
```

- `clamp_tension.jsonl`:

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "clamp-tension",
  "operation": "clamp",
  "target": { "subsystem": "affect_manifold", "dimension": "tension" },
  "value": 0.0,
  "duration": { "kind": "run" },
  "hypothesis": "clamping tension to 0 lowers verification pressure",
  "expected_behavioral_change": {
    "direction": "decrease",
    "target_signal": "control_pressure.verification"
  }
}
```

- `boost_curiosity.jsonl`:

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "boost-curiosity",
  "operation": "boost",
  "target": { "subsystem": "drives", "dimension": "curiosity" },
  "value": 0.6,
  "duration": { "kind": "run" },
  "hypothesis": "boosting curiosity raises exploration pressure",
  "expected_behavioral_change": {
    "direction": "increase",
    "target_signal": "control_pressure.exploration"
  }
}
```

- `remove_memory_anchors.jsonl`:

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "remove-anchors",
  "operation": "disable",
  "target": { "subsystem": "memory", "dimension": "identity_anchors" },
  "duration": { "kind": "run" },
  "hypothesis": "removing memory anchors drops identity persistence",
  "expected_behavioral_change": {
    "direction": "decrease",
    "target_signal": "psyche_state.continuity_score"
  }
}
```

- `disable_workspace.jsonl`:

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "disable-workspace",
  "operation": "disable",
  "target": { "subsystem": "workspace" },
  "duration": { "kind": "run" },
  "hypothesis": "disabling the workspace broadcast breaks the broadcast/action trace",
  "expected_behavioral_change": {
    "direction": "decrease",
    "target_signal": "workspace_broadcast.integrity"
  }
}
```

- `restore_null.jsonl` (null / no-op):

```json
{
  "frame_kind": "intervention",
  "schema_version": "0.1.0",
  "experiment_id": "restore-null",
  "operation": "restore",
  "target": { "subsystem": "affect_manifold", "dimension": "tension" },
  "duration": { "kind": "run" },
  "hypothesis": "a restore (no-op) produces no downstream change",
  "expected_behavioral_change": {
    "direction": "no_change",
    "target_signal": "control_pressure.verification"
  }
}
```

- `failing_hypothesis.jsonl` (for Task 8 refusal test): same as `clamp_tension.jsonl`
  but `experiment_id":"bad-hyp"` and `direction":"increase"` (which is false).

- [ ] **Step 1: Create all fixture files.**
- [ ] **Step 2: Write end-to-end tests** (append to `tests/test_paired_replay.py`)

```python
import pytest
from pneuma_lab.schemas import validate as V


@pytest.mark.parametrize("name,exp", [
    ("ablate_scar_graph", "ablate-scar"),
    ("clamp_tension", "clamp-tension"),
    ("boost_curiosity", "boost-curiosity"),
    ("remove_memory_anchors", "remove-anchors"),
    ("disable_workspace", "disable-workspace"),
    ("restore_null", "restore-null"),
])
def test_each_canonical_intervention_passes_and_stays_valid(name, exp):
    frames = load_jsonl(_FIX / f"{name}.jsonl")
    for f in frames:
        assert V.iter_errors(f) == [], f"invalid input {f.get('frame_kind')}"
    res = PairedReplayRunner().run(frames)
    assert exp in res.report["summary"]["passed"], res.report["summary"]
    assert res.report["summary"]["failed"] == []
    for f in res.treated.output_frames:
        assert V.iter_errors(f) == [], f"invalid treated output {f.get('frame_kind')}"
    assert V.iter_errors(res.evidence_frame) == []


def test_null_and_causal_completeness_hold_for_effects():
    for name in ("clamp_tension", "boost_curiosity", "remove_memory_anchors"):
        res = PairedReplayRunner().run(load_jsonl(_FIX / f"{name}.jsonl"))
        assert res.report["null_condition"]["passed"] is True
        assert res.report["causal_trace_complete"] is True
        assert res.report["grounded_self_report_changed_under_perturbation"] is True
        assert res.evidence_frame["evidence_level"] == 4


def test_disable_workspace_break_is_traced_not_a_crash():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "disable_workspace.jsonl"))
    # The break is intended: no treated tick spans to a behavior stage.
    assert all(
        o.workspace_broadcast["winning_faculty"] == "suppressed"
        for o in res.treated.tick_outputs
    )
    # Grounded reports still valid (confab risk 0 on the control run).
    assert res.evidence_frame["roleplay_confabulation_risk"] == 0.0
```

> Note: for `disable_workspace`, `grounded_self_report_changed` and
> `causal_trace_complete` semantics differ (the trace intentionally breaks). Its L4
> is still valid because `_trace_complete` treats the suppressed break as expected.
> If `disable_workspace` should _not_ assert level==4 (because its target signal is
> "integrity" and the break is the point), keep it in the passing set but assert
> level==4 only for the three non-structural effects above. Verify actual behavior
> during implementation and adjust the assertion to match reality — do **not** weaken
> a real failure into a pass.

- [ ] **Step 3: Run — expect PASS** (adjust per the note after observing real deltas).
- [ ] **Step 4: Commit** `test(interventions): five canonical fixtures + null + refusal`.

---

## Task 10: CLI paired mode + docs

**Files:**

- Modify: `src/pneuma_lab/replay/__main__.py`
- Modify: `docs/io-contract.md`, `docs/consciousness-levels.md`, `README.md`, `CLAUDE.md`

- [ ] **Step 1: CLI** — after loading `input_frames`, detect interventions:

```python
    has_iv = any(f.get("frame_kind") == "intervention" for f in input_frames)
    if has_iv:
        from ..interventions.runner import PairedReplayRunner
        res = PairedReplayRunner(validate=not args.no_validate).run(input_frames)
        dump_jsonl(res.control.output_frames, out_dir / "control_frames.jsonl")
        dump_jsonl(res.treated.output_frames, out_dir / "intervention_frames.jsonl")
        _dump_json(res.report, out_dir / "intervention_report.json")
        _dump_json(res.evidence_frame, out_dir / "evidence.json")
        ev = res.evidence_frame
        print(f"paired replay | evidence_level={ev['evidence_level']} "
              f"passed={ev['intervention_tests']['passed']} "
              f"failed={ev['intervention_tests']['failed']} | out={out_dir}")
        return 0
    # else: existing single-run path
```

Add a small `_dump_json(obj, path)` helper (indent=2, sort_keys=True, newline="\n").

- [ ] **Step 2: Run the CLI on two fixtures** and eyeball output:

```
python -m pneuma_lab.replay fixtures/interventions/clamp_tension.jsonl -o build/iv_clamp
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
```

Expected: first prints `evidence_level=4 passed=['clamp-tension'] failed=[]`; second
still prints `evidence_level=3`.

- [ ] **Step 3: Docs.**
  - `docs/io-contract.md`: document the intervention execution path, the
    control/treated/null replay, `intervention_report.json`, and the target-signal
    vocabulary.
  - `docs/consciousness-levels.md`: update the "How a level is earned" note — Level 4
    is now _reachable in-harness_ via the paired runner; add the exact L4 gate
    (tests pass + null + trace-complete + grounded-report-changed + confab low) and
    that the cap is now 4, not 3.
  - `README.md`: add the paired-replay command + one-paragraph description.
  - `CLAUDE.md`: update the Tree Guide (`interventions/` now implemented; `evals/`
    scores L0–4; Phase-2 boundary = no L5, no ML, no 9to5 write-back).

- [ ] **Step 4: Full verification** (see below).
- [ ] **Step 5: Commit** `feat(cli+docs): paired intervention mode + Level-4 docs`.

---

## Verification

```
pip install -e ".[dev]"
python -m pytest tests/ -q
python -m pneuma_lab.replay fixtures/interventions/clamp_tension.jsonl -o build/iv_clamp
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
python -m pytest tests/ -q            # determinism second pass — identical results
git diff --check
```

Expected: all tests pass; clamp-tension paired run reports `evidence_level=4`; the
Phase-1 fixture still reports `evidence_level=3`; the failing-hypothesis fixture and
the no-intervention run both refuse Level 4.

## Self-review checklist (spec → task)

1. Intervention runner with clamp/disable/boost/noise/ablate/restore → Tasks 1–3.
2. Paired replay mode (control vs intervention) → Tasks 5, 7 (+ null run).
3. Intervention report of expected vs observed deltas → Task 6.
4. Evidence frame: L4 only when interventions execute AND pass → Task 8.
5. Five canonical fixtures (ablate scar, clamp tension, boost curiosity, remove
   anchors, disable workspace) → Task 9 (+ null + failing).
6. Tests: schema validity (T9), deterministic paired replay (T5,T7), expected deltas
   (T6,T9), null conditions (T6,T9), causal-trace completeness (T7,T9), grounded
   self-report under perturbation (T7,T9), hard refusal when interventions absent/fail
   (T8) → all covered.

**Boundary check:** no datasets, no ML/training, no learned models, no 9to5
write-back, no L5 claim. Cap is `min(level, 4)`. ✅
