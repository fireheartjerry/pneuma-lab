# BaselinePsycheSubject-v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal integrated psyche subject inside `nervous_system/` that maintains affect state across ticks, persists scar memory across runs, runs a 3-candidate global-workspace competition, and converts the winner into bounded verification pressure with complete CausalTrace receipts — all as conservative harness evidence.

**Architecture:** `BaselinePsycheSubject` implements the existing `PsycheUnderTest` + `Perturbable` seam, so the existing `ReplayHarness` (ticking, intervention install, validation) and `PairedReplayRunner` (control/treated/null + report) drive it unchanged. A thin `subject_runtime` packages tick outputs into `PneumaOutputBundle`s and a conservative evidence frame; `subject_ablation` reuses the paired runner for interventions. Pure helpers (`manifold`, `hashing`) are reused; the promotable psyche scorer's frame is deliberately NOT used as the headline.

**Tech Stack:** Python 3, JSON Schema Draft 2020-12, pytest. Reuses `pneuma_lab.psyche.{interface,manifold,hashing}`, `pneuma_lab.replay.harness`, `pneuma_lab.interventions.{runner,perturbation,report}`, `pneuma_lab.schemas.validate`.

Reference spec: `docs/superpowers/specs/2026-07-10-baseline-psyche-subject-v0-design.md`.

---

## File structure

- Modify: `schemas/pneuma-output-bundle.schema.json` — add optional `psyche_state`, `workspace_broadcast`.
- Modify: `src/pneuma_lab/schemas/validate.py` — extend `_BUNDLE_MEMBER_KEYS`.
- Create: `src/pneuma_lab/nervous_system/scar_memory.py` — persistent scar store.
- Create: `src/pneuma_lab/nervous_system/workspace.py` — 3-candidate competition.
- Create: `src/pneuma_lab/nervous_system/subject.py` — `BaselinePsycheSubject`.
- Create: `src/pneuma_lab/nervous_system/subject_runtime.py` — `run_subject`.
- Create: `src/pneuma_lab/nervous_system/subject_ablation.py` — `run_subject_ablation`.
- Modify: `src/pneuma_lab/nervous_system/shadow_evidence.py` — add `subject_evidence_frame`.
- Modify: `src/pneuma_lab/nervous_system/__init__.py` — export `BaselinePsycheSubject`, `run_subject`.
- Create: `fixtures/nervous_system/subject/base.jsonl`, `ablate_scar.jsonl`, `clamp_certainty.jsonl`, `disable_workspace.jsonl`.
- Create: `tests/test_baseline_psyche_subject.py`.
- Modify: `tests/test_nervous_system.py` — extend the import-hygiene guard to new files (already globs `*.py`, so no change needed; confirm).
- Modify: `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`.

---

### Task 1: Bundle schema extension (psyche_state + workspace_broadcast)

**Files:**

- Modify: `schemas/pneuma-output-bundle.schema.json`
- Modify: `src/pneuma_lab/schemas/validate.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_baseline_psyche_subject.py
import json
from pathlib import Path

from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system" / "subject"


def test_output_bundle_accepts_psyche_and_workspace_members():
    bundle = {
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
        "psyche_state": None,
        "workspace_broadcast": None,
        "blocked_uses": ["no_runtime_authority"],
        "limitations": ["shadow_mode"],
    }
    validate.validate_bundle(bundle)
    assert "psyche_state" in validate._BUNDLE_MEMBER_KEYS
    assert "workspace_broadcast" in validate._BUNDLE_MEMBER_KEYS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py::test_output_bundle_accepts_psyche_and_workspace_members -q`
Expected: FAIL (`_BUNDLE_MEMBER_KEYS` lacks the new keys).

- [ ] **Step 3: Add the two optional members to the output bundle schema**

In `schemas/pneuma-output-bundle.schema.json`, inside `properties`, after the `consciousness_evidence` property, add:

```json
        "psyche_state": {
            "type": [
                "object",
                "null"
            ]
        },
        "workspace_broadcast": {
            "type": [
                "object",
                "null"
            ]
        },
```

- [ ] **Step 4: Extend the deep-validated member keys**

In `src/pneuma_lab/schemas/validate.py`, update `_BUNDLE_MEMBER_KEYS`:

```python
_BUNDLE_MEMBER_KEYS = (
    "world",
    "agent_trace",
    "governance",
    "risk_estimate",
    "instinct",
    "control_pressure",
    "causal_trace",
    "consciousness_evidence",
    "psyche_state",
    "workspace_broadcast",
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_baseline_psyche_subject.py::test_output_bundle_accepts_psyche_and_workspace_members -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add schemas/pneuma-output-bundle.schema.json src/pneuma_lab/schemas/validate.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): output bundle carries psyche_state + workspace_broadcast"
```

---

### Task 2: Persistent scar memory store (`scar_memory.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/scar_memory.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_scar_memory_roundtrip_and_motif(tmp_path):
    from pneuma_lab.nervous_system import scar_memory as sm

    path = tmp_path / "scars.json"
    assert sm.load(path) == {}
    sm.save(path, {"m1:regress": 0.3})
    assert sm.load(path) == {"m1:regress": 0.3}
    memory_frame = {
        "frame_kind": "memory",
        "scar_motif_matches": [
            {"motif_id": "m1:regress", "similarity": 0.9},
            {"motif_id": "m2:flaky", "similarity": 0.4},
        ],
    }
    assert sm.motif_of(memory_frame) == ("m1:regress", 0.9)
    assert sm.motif_of({"frame_kind": "memory"}) is None
    assert sm.motif_of(None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k scar_memory -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `scar_memory.py`**

```python
"""Small persistent scar/memory store for the baseline psyche subject.

Deterministic JSON on disk: sorted keys, rounded floats. This is the cross-run
memory the subject seeds from and writes back to; it is NOT the per-tick input
MemoryFrame (which is read-only observation).
"""

from __future__ import annotations

import json
from pathlib import Path


def load(path) -> dict:
    """Load the scar store, or {} when absent."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, scars: dict) -> None:
    """Persist the scar store deterministically."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rounded = {k: round(float(v), 6) for k, v in sorted(scars.items())}
    p.write_text(json.dumps(rounded, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def motif_of(memory_frame):
    """Return (motif_id, similarity) for the strongest scar match, else None."""
    if not isinstance(memory_frame, dict):
        return None
    matches = memory_frame.get("scar_motif_matches") or []
    best = None
    for m in matches:
        sim = float(m.get("similarity", 0.0))
        motif = m.get("motif_id")
        if motif is None:
            continue
        if best is None or sim > best[1] or (sim == best[1] and motif < best[0]):
            best = (motif, sim)
    return best
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k scar_memory -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/scar_memory.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): persistent scar memory store"
```

---

### Task 3: 3-candidate workspace competition (`workspace.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/workspace.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_workspace_competes_deterministically():
    from pneuma_lab.nervous_system import workspace as ws

    result = ws.compete({"risk_instinct": 0.5, "memory_scar": 0.86, "uncertainty_self_model": 0.4})
    assert result["winning_faculty"] == "memory_scar"
    assert result["winning_salience"] == 0.86
    assert result["salience_scores"]["scar_tissue"] == 0.86
    assert result["salience_scores"]["risk"] == 0.5
    assert result["salience_scores"]["uncertainty"] == 0.4
    losers = {c["faculty"] for c in result["competitors"]}
    assert losers == {"risk_instinct", "uncertainty_self_model"}
    # deterministic tie-break by fixed order
    tie = ws.compete({"risk_instinct": 0.5, "memory_scar": 0.5, "uncertainty_self_model": 0.5})
    assert tie["winning_faculty"] == "risk_instinct"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k workspace -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `workspace.py`**

```python
"""Pure, deterministic 3-candidate global-workspace competition.

Candidates: risk_instinct, memory_scar, uncertainty_self_model. Highest salience
wins; ties break by the fixed CANDIDATE_ORDER (deterministic). The named salience
terms map onto the WorkspaceBroadcast schema's risk / scar_tissue / uncertainty.
"""

from __future__ import annotations

CANDIDATE_ORDER = ("risk_instinct", "memory_scar", "uncertainty_self_model")
_TERM = {
    "risk_instinct": "risk",
    "memory_scar": "scar_tissue",
    "uncertainty_self_model": "uncertainty",
}


def compete(candidates: dict) -> dict:
    """Return the winning faculty + salience terms + losing competitors."""
    ordered = [(name, round(float(candidates.get(name, 0.0)), 6)) for name in CANDIDATE_ORDER]
    winner_name, winner_sal = max(ordered, key=lambda kv: (kv[1], -CANDIDATE_ORDER.index(kv[0])))
    salience_scores = {_TERM[name]: sal for name, sal in ordered}
    competitors = [
        {"faculty": name, "salience": sal}
        for name, sal in ordered
        if name != winner_name
    ]
    return {
        "winning_faculty": winner_name,
        "winning_salience": winner_sal,
        "salience_scores": salience_scores,
        "competitors": competitors,
        "conviction": min(1.0, max(0.0, winner_sal)),
    }
```

Note: `max` with key `(salience, -index)` picks the highest salience and, on a tie, the earliest `CANDIDATE_ORDER` index (largest `-index`). Verify the tie test: all 0.5 → indices 0,1,2 → `-index` 0,-1,-2 → max picks index 0 = `risk_instinct`. Correct.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k workspace -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/workspace.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): deterministic 3-candidate workspace competition"
```

---

### Task 4: Subject fixtures (base + 3 interventions)

**Files:**

- Create: `fixtures/nervous_system/subject/base.jsonl`
- Create: `fixtures/nervous_system/subject/ablate_scar.jsonl`
- Create: `fixtures/nervous_system/subject/clamp_certainty.jsonl`
- Create: `fixtures/nervous_system/subject/disable_workspace.jsonl`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_subject_fixtures_are_valid_input_frames():
    from pneuma_lab.schemas import validate

    for name in ("base.jsonl", "ablate_scar.jsonl", "clamp_certainty.jsonl", "disable_workspace.jsonl"):
        lines = [x for x in (FIX / name).read_text(encoding="utf-8").splitlines() if x.strip()]
        assert lines, name
        for line in lines:
            validate.validate_or_raise(json.loads(line))


def _frames(name):
    return [json.loads(x) for x in (FIX / name).read_text(encoding="utf-8").splitlines() if x.strip()]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k fixtures_are_valid -q`
Expected: FAIL (files missing).

- [ ] **Step 3: Generate the fixtures with a script**

Run this generator (writes 4 JSONL timelines; base has 3 ticks with a strong scar match `m1:regress`; the three variants are base + one intervention frame in the second tick):

```bash
python - <<'PY'
import json, os
d = "fixtures/nervous_system/subject"
os.makedirs(d, exist_ok=True)

GOV = {"schema_version":"0.1.0","frame_kind":"governance","run_id":"subj","timestamp":"2026-07-10T00:00:00Z",
       "verifier_isolation":True,"kill_switch_state":"on",
       "authority_ceilings":{"global_max":"hold","per_domain":{},"per_faculty":{}}}

def world(i, err, ts):
    w = {"schema_version":"0.1.0","frame_kind":"world","run_id":"subj","phase":"execution",
         "timestamp":ts,"stakes":{"reversibility":0.5,"risk":0.5,"stakes":0.5}}
    if err:
        w["tool_events"]=[{"tool":"run_tests","status":"error"}]
        w["verification_signals"]={"verdict":"fail","regression_found":True}
    else:
        w["verification_signals"]={"verdict":"pending"}
    return w

def agent(i, unc, retry, ts):
    return {"schema_version":"0.1.0","frame_kind":"agent_trace","run_id":"subj","phase":"execution",
            "timestamp":ts,"uncertainty":unc,"retry_count":retry}

def mem(ts):
    return {"schema_version":"0.1.0","frame_kind":"memory","run_id":"subj","timestamp":ts,
            "scar_motif_matches":[{"motif_id":"m1:regress","similarity":0.9,"historical_base_rate":0.7}],
            "historical_failures":[{"motif_id":"m1:regress","run_id":"prev","summary":"regressed"}],
            "retrieved_continuity":[{"ref":"anchor:identity","run_id":"prev","text":"careful SE agent"}]}

def tick(i, err, unc, retry):
    ts=f"2026-07-10T00:00:0{i+1}Z"
    return [world(i,err,ts), agent(i,unc,retry,ts), mem(ts)]

base = [GOV] + tick(0,False,0.3,0) + tick(1,True,0.5,1) + tick(2,True,0.6,2)

def write(name, frames):
    with open(f"{d}/{name}","w",encoding="utf-8") as f:
        for fr in frames:
            f.write(json.dumps(fr,sort_keys=True)+"\n")

write("base.jsonl", base)

def with_iv(iv):
    # insert the intervention frame right after the tick-1 world (second tick)
    frames = [GOV] + tick(0,False,0.3,0)
    frames += [world(1,True,"2026-07-10T00:00:02Z"), iv,
               agent(1,0.5,1,"2026-07-10T00:00:02Z"), mem("2026-07-10T00:00:02Z")]
    frames += tick(2,True,0.6,2)
    return frames

ablate = {"schema_version":"0.1.0","frame_kind":"intervention","experiment_id":"ablate-scar",
          "operation":"ablate","target":{"subsystem":"scar_graph","dimension":None},
          "duration":{"kind":"run"},"hypothesis":"ablate scar_graph -> winner flips off memory_scar",
          "expected_behavioral_change":{"direction":"decrease","target_signal":"control_pressure.verification"}}
clamp = {"schema_version":"0.1.0","frame_kind":"intervention","experiment_id":"clamp-certainty",
         "operation":"clamp","target":{"subsystem":"affect_manifold","dimension":"certainty"},"value":1.0,
         "duration":{"kind":"run"},"hypothesis":"clamp certainty high -> uncertainty salience drops",
         "expected_behavioral_change":{"direction":"decrease","target_signal":"control_pressure.verification"}}
disable = {"schema_version":"0.1.0","frame_kind":"intervention","experiment_id":"disable-workspace",
           "operation":"disable","target":{"subsystem":"workspace","dimension":None},
           "duration":{"kind":"run"},"hypothesis":"disable workspace -> no broadcast, pressure suppressed",
           "expected_behavioral_change":{"direction":"decrease","target_signal":"workspace_broadcast.integrity"}}

write("ablate_scar.jsonl", with_iv(ablate))
write("clamp_certainty.jsonl", with_iv(clamp))
write("disable_workspace.jsonl", with_iv(disable))
print("wrote subject fixtures")
PY
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k fixtures_are_valid -q`
Expected: PASS (every frame is schema-valid). If an intervention frame fails validation, compare against `schemas/intervention-frame.schema.json` and fix the generator.

- [ ] **Step 5: Commit**

```bash
git add fixtures/nervous_system/subject/ tests/test_baseline_psyche_subject.py
git commit -m "test(nervous-system): baseline-subject input-frame fixtures"
```

---

### Task 5: `BaselinePsycheSubject` (`subject.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/subject.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test** (drive the subject through the real `ReplayHarness`)

```python
def test_subject_ticks_produce_valid_linked_frames_via_harness():
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
    from pneuma_lab.replay.harness import ReplayHarness
    from pneuma_lab.schemas import validate

    subject = BaselinePsycheSubject(scars={"m1:regress": 0.5})
    result = ReplayHarness(subject, validate=True).run(_frames("base.jsonl"))
    outs = result.tick_outputs
    assert len(outs) == 3
    # state-hash chain links tick to tick
    prev = None
    for o in outs:
        ps, ct = o.psyche_state, o.causal_trace
        validate.validate_or_raise(ps)
        validate.validate_or_raise(o.workspace_broadcast)
        validate.validate_or_raise(o.control_pressure)
        validate.validate_or_raise(ct)
        validate.validate_or_raise(o.grounded_self_report)
        if prev is not None:
            assert ct["previous_state_hash"] == prev
        prev = ct["new_state_hash"]
        stages = [n["stage"] for n in ct["causal_path"]]
        assert stages == ["event", "internal_state", "broadcast", "pressure"]
        # additive-only, no authority
        assert o.control_pressure["pressures"]["verification"] >= 0.0
        assert o.control_pressure["authority_tier"] in ("cosmetic", "soft")
        assert o.grounded_self_report["affect_state_hash"] == ps["state_hash"]
    # with a strong seeded scar, memory_scar wins on the scar-matching ticks
    winners = [o.workspace_broadcast["winning_faculty"] for o in outs]
    assert "memory_scar" in winners
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k ticks_produce_valid -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `subject.py`**

```python
"""BaselinePsycheSubject-v0: a minimal integrated, replayable psyche subject.

Implements the PsycheUnderTest seam + the Perturbable hook, so the existing
ReplayHarness and PairedReplayRunner drive it unchanged. It maintains a 9-axis
affect manifold across ticks, seeds persistent scars across runs, runs a
3-candidate workspace competition, and emits verification-pressure ONLY. It never
actuates, grants authority, or contacts a verifier.
"""

from __future__ import annotations

from pneuma_lab.interventions.perturbation import PerturbationSet
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import workspace as ws
from pneuma_lab.psyche import manifold
from pneuma_lab.psyche.hashing import frame_id, state_hash
from pneuma_lab.psyche.interface import PsycheInputs, PsycheOutputs, PsycheUnderTest

_TIER_ORDER = ("cosmetic", "soft", "vote", "hold", "veto")
_SCAR_INCREMENT = 0.1


def _clip(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _min_tier(a, b):
    ia = _TIER_ORDER.index(a) if a in _TIER_ORDER else len(_TIER_ORDER)
    ib = _TIER_ORDER.index(b) if b in _TIER_ORDER else len(_TIER_ORDER)
    return _TIER_ORDER[min(ia, ib)]


class BaselinePsycheSubject(PsycheUnderTest):
    def __init__(self, *, scars=None):
        self._seed_scars = dict(scars or {})
        self.reset()

    def reset(self) -> None:
        # per-run carried state cleared; cross-run scars re-seeded (not cleared)
        self.affect = manifold.new_manifold()
        self.self_model_uncertainty = 0.0
        self.scars = dict(self._seed_scars)
        self.prev_state_hash = state_hash(self._interior())
        self._pert = PerturbationSet.empty()

    def set_active_interventions(self, interventions) -> None:
        self._pert = PerturbationSet(interventions)

    def _interior(self):
        return {
            "affect": self.affect,
            "self_model_uncertainty": self.self_model_uncertainty,
            "scars": {k: round(v, 6) for k, v in sorted(self.scars.items())},
        }

    def tick(self, inputs: PsycheInputs) -> PsycheOutputs:
        world = inputs.world
        trace = inputs.agent_trace or {}
        memory = inputs.memory
        governance = inputs.governance or {}
        run_id = world.get("run_id", "subj")
        ti = inputs.tick_index
        ts = world.get("timestamp", "2026-07-10T00:00:00Z")
        pert = self._pert

        # 1. appraise observables
        error = 1.0 if _has_error(world) else 0.0
        retry = float(trace.get("retry_count", 0) or 0)
        uncertainty_in = float(trace.get("uncertainty", 0.0) or 0.0)

        # 2. update affect (minimal explicit law over the 9-axis manifold)
        self.affect["tension"] = _clip(0.5 * self.affect["tension"] + 0.5 * error)
        self.affect["cognitive_load"] = _clip(min(1.0, retry / 3.0))
        self.affect["certainty"] = _clip(1.0 - 2.0 * uncertainty_in)
        self.self_model_uncertainty = _clip(uncertainty_in, 0.0, 1.0)

        # perturbations act at the affect axes the candidates read
        tension = pert.scalar("affect_manifold", "tension", self.affect["tension"])
        certainty = pert.scalar("affect_manifold", "certainty", self.affect["certainty"])

        # 3. update persistent scars from the input MemoryFrame
        motif = sm.motif_of(memory)
        if motif is not None and not pert.blocks("scar_graph"):
            self.scars[motif[0]] = round(self.scars.get(motif[0], 0.0) + _SCAR_INCREMENT, 6)

        new_hash = state_hash(self._interior())

        # 4. three candidate saliences (honoring perturbations)
        risk_sal = _clip(0.4 * error + 0.3 * max(0.0, tension), 0.0, 1.0)
        if pert.blocks("scar_graph") or motif is None:
            scar_sal = 0.0
        else:
            scar_sal = _clip(0.4 * motif[1] + self.scars.get(motif[0], 0.0), 0.0, 1.0)
        uncertainty_sal = _clip(0.5 * self.self_model_uncertainty + 0.5 * max(0.0, -certainty), 0.0, 1.0)

        # 5. workspace competition (suppressed when workspace is disabled)
        workspace_disabled = pert.blocks("workspace")
        comp = ws.compete({
            "risk_instinct": risk_sal,
            "memory_scar": scar_sal,
            "uncertainty_self_model": uncertainty_sal,
        })

        # 6. verification pressure = winner salience (0 when workspace disabled)
        verification = 0.0 if workspace_disabled else round(comp["winning_salience"], 6)
        global_max = governance.get("authority_ceilings", {}).get("global_max", "soft")
        tier = _min_tier("soft", global_max)

        # ids
        ps_id = frame_id(run_id, ti, "psyche_state")
        bc_id = frame_id(run_id, ti, "workspace_broadcast")
        cp_id = frame_id(run_id, ti, "control_pressure")
        ct_id = frame_id(run_id, ti, "causal_trace")
        in_id = frame_id(run_id, ti, "agent_trace")
        inst_id = frame_id(run_id, ti, "instinct_signal")

        psyche_state = {
            "schema_version": "0.1.0", "frame_kind": "psyche_state", "timestamp": ts,
            "run_id": run_id, "state_hash": new_hash,
            "affect_manifold": {k: round(v, 6) for k, v in self.affect.items()},
            "self_model": {"predicted_error": round(self.self_model_uncertainty, 6),
                           "self_model_reliability": None,
                           "identity_refs": _identity_refs(memory)},
            "identity_continuity_state": {"continuity_score": None,
                                          "anchors_carried": len(_identity_refs(memory))},
            "derived_signals": {"scar_strength": round(scar_sal, 6)},
        }

        broadcast = {
            "schema_version": "0.1.0", "frame_kind": "workspace_broadcast", "timestamp": ts,
            "run_id": run_id, "broadcast_id": bc_id,
            "winning_faculty": "none" if workspace_disabled else comp["winning_faculty"],
            "competitors": [] if workspace_disabled else comp["competitors"],
            "salience_scores": comp["salience_scores"],
            "winning_salience": 0.0 if workspace_disabled else comp["winning_salience"],
            "conviction": 0.0 if workspace_disabled else comp["conviction"],
            "disabled": workspace_disabled,
        }

        instinct = None
        if not workspace_disabled and comp["winning_faculty"] in ("risk_instinct", "memory_scar"):
            bucket = "high" if verification >= 0.66 else ("medium" if verification >= 0.33 else "low")
            instinct = {
                "schema_version": "0.1.0", "frame_kind": "instinct_signal", "timestamp": ts,
                "run_id": run_id, "motif_id": f"subject.{comp['winning_faculty']}-{bucket}",
                "match_type": "anomaly", "confidence": round(verification, 6),
                "severity": round(verification, 6),
                "recommended_action": "deepen_verification" if bucket == "high" else "continue_fast_path",
                "authority_request": "soft", "explanation_trace_id": ct_id,
            }

        pressure = {
            "schema_version": "0.1.0", "frame_kind": "control_pressure", "timestamp": ts,
            "run_id": run_id, "authority_tier": tier,
            "pressures": {"verification": verification},
            "sources": [bc_id], "causal_trace_id": ct_id,
        }

        report = {
            "schema_version": "0.1.0", "frame_kind": "grounded_self_report", "timestamp": ts,
            "run_id": run_id, "report_id": frame_id(run_id, ti, "grounded_self_report"),
            "report_text": f"verification-seeking state at {verification}; winner={broadcast['winning_faculty']}",
            "affect_state_hash": new_hash, "workspace_broadcast_id": bc_id,
            "causal_trace_id": ct_id,
            "reported_measurements": {"verification_pressure": verification},
            "uncertainty": round(self.self_model_uncertainty, 6),
        }

        causal_path = [
            {"stage": "event", "ref": in_id, "note": "observable world + agent trace"},
            {"stage": "internal_state", "ref": ps_id, "note": "affect updated; scars seeded"},
            {"stage": "broadcast", "ref": bc_id,
             "note": ("workspace disabled (expected break)" if workspace_disabled
                      else f"winner={comp['winning_faculty']}")},
            {"stage": "pressure", "ref": cp_id, "note": f"verification={verification}"},
        ]
        emitted = [ps_id, bc_id, cp_id]
        if instinct is not None:
            emitted.append(inst_id)
        causal_trace = {
            "schema_version": "0.1.0", "frame_kind": "causal_trace", "timestamp": ts,
            "run_id": run_id, "trace_id": ct_id, "input_evidence_refs": [in_id],
            "previous_state_hash": self.prev_state_hash, "new_state_hash": new_hash,
            "changed_dimensions": [{"dimension": "affect.tension", "to": round(self.affect["tension"], 6)}],
            "state_update_mechanism": "baseline_subject.affect_update+workspace_competition",
            "causal_path": causal_path, "emitted_outputs": emitted,
            "interventions_applied": pert.records(),
            "counterfactual_predictions": [
                {"condition": "if scar_graph ablated", "predicted_outcome": "memory_scar salience -> 0; winner may flip"},
                {"condition": "if affect_manifold.certainty clamped high", "predicted_outcome": "uncertainty salience drops"},
                {"condition": "if workspace disabled", "predicted_outcome": "no broadcast; verification pressure -> 0"},
            ],
        }

        self.prev_state_hash = new_hash
        return PsycheOutputs(
            psyche_state=psyche_state, workspace_broadcast=broadcast, control_pressure=pressure,
            causal_trace=causal_trace, grounded_self_report=report,
            instinct_signals=[instinct] if instinct is not None else [],
        )


def _has_error(world: dict) -> bool:
    for ev in world.get("tool_events", []) or []:
        if ev.get("status") == "error":
            return True
    vs = world.get("verification_signals", {}) or {}
    return vs.get("verdict") == "fail" or bool(vs.get("regression_found"))


def _identity_refs(memory):
    if not isinstance(memory, dict):
        return []
    return [c.get("ref") for c in memory.get("retrieved_continuity", []) if c.get("ref")]
```

- [ ] **Step 4: Run test — expect PASS, but tune if the winner assertion fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k ticks_produce_valid -q`
Expected: PASS. If `"memory_scar" in winners` fails, print the per-tick saliences:

```bash
python - <<'PY'
import json
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
from pneuma_lab.replay.harness import ReplayHarness
frames=[json.loads(x) for x in open("fixtures/nervous_system/subject/base.jsonl") if x.strip()]
r=ReplayHarness(BaselinePsycheSubject(scars={"m1:regress":0.5}),validate=True).run(frames)
for o in r.tick_outputs:
    print(o.workspace_broadcast["winning_faculty"], o.workspace_broadcast["salience_scores"], o.control_pressure["pressures"])
PY
```

Adjust the salience weights in `subject.py` (or the seed) so `memory_scar` wins at least one scar-matching tick with a seed of 0.5. The scar formula `0.4*0.9 + 0.5 = 0.86` should beat risk (≤0.7) and uncertainty (≤0.5); if not, recheck `_has_error`/perturbation wiring.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/subject.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): BaselinePsycheSubject integrated tick loop"
```

---

### Task 6: `run_subject` runtime + persistence (`subject_runtime.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/subject_runtime.py`
- Modify: `src/pneuma_lab/nervous_system/__init__.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_subject_is_deterministic_schema_valid_and_persists(tmp_path):
    from pneuma_lab.nervous_system.subject_runtime import run_subject
    from pneuma_lab.schemas import validate

    frames = _frames("base.jsonl")
    store = tmp_path / "scars.json"
    b1 = run_subject(frames, scar_store_path=store, shadow_log_path=tmp_path / "l1.jsonl")
    b2 = run_subject(frames, scar_store_path=tmp_path / "store2.json", shadow_log_path=tmp_path / "l2.jsonl")
    for b in b1:
        validate.validate_bundle(b)
        assert b["control_pressure"]["authority_tier"] in ("cosmetic", "soft")
        assert b["control_pressure"]["pressures"]["verification"] >= 0.0
        assert "verdict" not in b["control_pressure"]
        # causal refs resolve within the bundle
        ct = b["causal_trace"]
        present = {b["psyche_state"]["state_hash"]}
        assert ct["new_state_hash"] in present
    assert json.dumps(b1, sort_keys=True) == json.dumps(b2, sort_keys=True)
    # persistence: store written; a second run seeded from it differs on tick 0
    assert store.exists()
    b3 = run_subject(frames, scar_store_path=store, shadow_log_path=tmp_path / "l3.jsonl")
    p1 = b1[0]["control_pressure"]["pressures"]["verification"]
    p3 = b3[0]["control_pressure"]["pressures"]["verification"]
    assert p3 != p1  # run-2 seeded from accumulated scars -> different tick-0 pressure


def test_run_subject_kill_switch_suppresses(tmp_path):
    from pneuma_lab.nervous_system.subject_runtime import run_subject

    frames = _frames("base.jsonl")
    frames[0] = {**frames[0], "kill_switch_state": "off"}
    log = tmp_path / "log.jsonl"
    out = run_subject(frames, scar_store_path=tmp_path / "s.json", shadow_log_path=log)
    assert out == []
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows and rows[0]["status"] == "suppressed_by_governance"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k run_subject -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `subject_runtime.py`**

```python
"""Drive BaselinePsycheSubject over an input-frame timeline and package bundles.

Reuses ReplayHarness for ticking/validation. The promotable psyche scorer's
evidence frame is intentionally discarded; the bundle carries a conservative
subject_evidence_frame instead. Scars are seeded from and written back to a
persistent store (cross-run memory).
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.nervous_system import BLOCKED_USES, LIMITATIONS
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
from pneuma_lab.replay.harness import ReplayHarness
from pneuma_lab.schemas import validate


def _governance_of(frames):
    for fr in frames:
        if fr.get("frame_kind") == "governance":
            return fr
    return {}


def _base_timestamp(frames):
    for fr in frames:
        if isinstance(fr.get("timestamp"), str):
            return fr["timestamp"]
    return "2026-07-10T00:00:00Z"


def run_subject(input_frames, *, scar_store_path=None, shadow_log_path=None, schedule=None):
    governance = _governance_of(input_frames)
    run_id = governance.get("run_id", "subj")
    timestamp = _base_timestamp(input_frames)
    log_path = Path(shadow_log_path) if shadow_log_path else None

    def _append(row):
        if log_path is None:
            return
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as h:
            h.write(json.dumps(row, sort_keys=True) + "\n")

    if governance.get("kill_switch_state", "on") != "on":
        _append({"status": "suppressed_by_governance", "run_id": run_id,
                 "kill_switch_state": governance.get("kill_switch_state"), "timestamp": timestamp})
        return []

    seed = sm.load(scar_store_path) if scar_store_path else {}
    subject = BaselinePsycheSubject(scars=seed)
    result = ReplayHarness(subject, validate=True).run(input_frames, schedule=schedule)

    # one conservative evidence frame for the whole run slice (no ablation here)
    evidence = nse.subject_evidence_frame(
        ablation_result={"direction_ok": False, "null_holds": True},
        families_exercised=("global_workspace", "valenced_learning",
                            "identity_persistence", "higher_order_self_model"),
        run_id=run_id, timestamp=timestamp)

    bundles = []
    for o in result.tick_outputs:
        instinct = o.instinct_signals[0] if o.instinct_signals else None
        bundle = {
            "schema_version": "0.1.0", "bundle_kind": "pneuma_output",
            "run_id": run_id, "timestamp": o.psyche_state["timestamp"],
            "governance_status": "emitted",
            "risk_estimate": None, "instinct": instinct,
            "control_pressure": o.control_pressure, "causal_trace": o.causal_trace,
            "consciousness_evidence": evidence,
            "psyche_state": o.psyche_state, "workspace_broadcast": o.workspace_broadcast,
            "blocked_uses": list(BLOCKED_USES), "limitations": list(LIMITATIONS),
        }
        validate.validate_bundle(bundle)
        bundles.append(bundle)
        _append({"status": "emitted", "run_id": run_id, "tick": o.psyche_state["state_hash"],
                 "verification": o.control_pressure["pressures"]["verification"]})

    if scar_store_path:
        sm.save(scar_store_path, subject.scars)
    return bundles
```

- [ ] **Step 4: Export from `__init__.py`**

In `src/pneuma_lab/nervous_system/__init__.py`, after the `ShadowNervousSystem` import line, add:

```python
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject  # noqa: E402
from pneuma_lab.nervous_system.subject_runtime import run_subject  # noqa: E402
```

and extend `__all__` with `"BaselinePsycheSubject"`, `"run_subject"`.

- [ ] **Step 5: Run tests — expect failure on the evidence import (Task 7 adds it)**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k run_subject -q`
Expected: FAIL with `AttributeError: module ... shadow_evidence has no attribute 'subject_evidence_frame'`. Proceed to Task 7, then return and re-run.

- [ ] **Step 6: Commit (after Task 7 makes it green — see Task 7 Step 5)**

(No commit here; committed jointly in Task 7.)

---

### Task 7: Conservative subject evidence (`shadow_evidence.py`)

**Files:**

- Modify: `src/pneuma_lab/nervous_system/shadow_evidence.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_subject_evidence_is_conservative():
    from pneuma_lab.nervous_system import shadow_evidence as nse
    from pneuma_lab.schemas import validate

    frame = nse.subject_evidence_frame(
        ablation_result={"direction_ok": True, "null_holds": True},
        families_exercised=("global_workspace", "valenced_learning",
                            "identity_persistence", "higher_order_self_model"),
        run_id="subj", timestamp="2026-07-10T00:00:00Z")
    validate.validate_or_raise(frame)
    assert frame["evidence_level"] <= 1
    assert frame["real_subject_claim_status"] == "not_evaluated"
    assert frame["paired_replay_provenance"]["status"] == "uncertified_subject"
    for fam in ("global_workspace", "valenced_learning", "identity_persistence",
                "higher_order_self_model", "causal_intervention_robustness"):
        assert frame["indicator_families"][fam]["status"] != "intervention_backed"
    assert frame["indicator_families"]["global_workspace"]["status"] in ("attempted", "architecture_only")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k subject_evidence -q`
Expected: FAIL (`subject_evidence_frame` not defined).

- [ ] **Step 3: Add `subject_evidence_frame` to `shadow_evidence.py`**

Append to `src/pneuma_lab/nervous_system/shadow_evidence.py` (reuses the existing `_FAMILIES`, `_MISSING`, `_family` from that module):

```python
def subject_evidence_frame(*, ablation_result, families_exercised, run_id, timestamp):
    """Conservative evidence for the BaselinePsycheSubject slice (never > L1).

    Families genuinely exercised by the subject are marked ``attempted`` /
    ``architecture_only`` (architecture present + exercised) but NEVER
    ``intervention_backed``; the headline evidence_level stays <= 1.
    """
    coupled = bool(ablation_result.get("direction_ok")) and bool(ablation_result.get("null_holds"))
    level = 1 if coupled else 0
    note = ("Level-1-compatible harness evidence from an integrated minimal subject: "
            "3-candidate workspace + persistent scars + verification pressure, with "
            "intervention/null behaviour. NOT a Level-2/3/4 claim.")
    families = {name: _family("absent", 0.0, "not exercised in subject slice") for name in _FAMILIES}
    for name in families_exercised:
        if name in families:
            families[name] = _family("architecture_only", 0.2,
                                     "architecture present and exercised; not intervention-certified")
    families["causal_intervention_robustness"] = _family(
        "attempted" if coupled else "absent", 0.3 if coupled else 0.0, note)
    return {
        "schema_version": "0.2.0", "frame_kind": "consciousness_evidence", "timestamp": timestamp,
        "run_id": run_id, "evaluation_id": f"subject_evidence:{run_id}",
        "evaluation_scope": "internal_harness", "real_subject_claim_status": "not_evaluated",
        "indicator_families": families, "evidence_level": level,
        "missing_requirements": list(_MISSING),
        "strongest_positive_evidence": (
            "intervention flips the workspace winner / changes verification pressure; null holds"
            if coupled else None),
        "strongest_negative_evidence": (
            "minimal non-certified subject; no promotable paired-runner certification; no real subject"),
        "audit_status": "self_reported", "roleplay_confabulation_risk": 0.1,
        "intervention_tests": {
            "results": [], "executed_count": 0, "reported_total": 0, "integrity_ok": False,
            "integrity_errors": ["subject slice is not a certified paired-runner intervention"],
            "genuine_perturbation": False},
        "paired_replay_provenance": {
            "status": "uncertified_subject", "runner": None, "subject_factory": None,
            "subject_factory_eligible": False, "input_frames_sha256": None,
            "arm_output_sha256": {"control": None, "treated": None, "null": None},
            "arm_orders": [], "counterbalanced_passes": [], "ordinal_invariant": False},
    }
```

- [ ] **Step 4: Run tests — subject_evidence + run_subject now green**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k "subject_evidence or run_subject" -q`
Expected: PASS (all). If `run_subject` persistence assertion `p3 != p1` fails, print `b1[0]` and `b3[0]` pressures and adjust `_SCAR_INCREMENT` in `subject.py` so the accumulated store visibly changes tick-0 pressure.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/shadow_evidence.py src/pneuma_lab/nervous_system/subject_runtime.py src/pneuma_lab/nervous_system/__init__.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): run_subject runtime + conservative subject evidence + persistence"
```

---

### Task 8: Intervention / null (`subject_ablation.py`)

**Files:**

- Create: `src/pneuma_lab/nervous_system/subject_ablation.py`
- Test: `tests/test_baseline_psyche_subject.py`

- [ ] **Step 1: Write the failing test**

```python
def test_ablate_scar_flips_winner_and_null_holds():
    from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation
    from pneuma_lab.schemas import validate

    res = run_subject_ablation(_frames("ablate_scar.jsonl"), seed_scars={"m1:regress": 0.5})
    assert res["winner_control"] == "memory_scar"
    assert res["winner_treated"] != "memory_scar"     # scar ablated -> winner flips
    assert res["winner_changed"] is True
    assert res["observed_delta"] <= 0.0               # pressure drops (or holds) under ablation
    assert res["null_holds"] is True
    validate.validate_or_raise(res["evidence_frame"])
    assert res["evidence_frame"]["evidence_level"] <= 1


def test_disable_workspace_suppresses_broadcast():
    from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation

    res = run_subject_ablation(_frames("disable_workspace.jsonl"), seed_scars={"m1:regress": 0.5})
    assert res["treated_verification"] == 0.0
    assert res["winner_treated"] == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k "ablate_scar_flips or disable_workspace_suppresses" -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `subject_ablation.py`**

```python
"""Intervention/null test for BaselinePsycheSubject via the existing paired runner.

Reuses PairedReplayRunner (control/treated/null + counterbalancing + report). The
runner's promotable evidence frame is discarded; a conservative subject evidence
frame is emitted instead. Winner change is read directly from tick outputs.
"""

from __future__ import annotations

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject


def _last_broadcast(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].workspace_broadcast if outs else {}


def _last_verification(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].control_pressure["pressures"]["verification"] if outs else 0.0


def run_subject_ablation(input_frames, *, seed_scars=None):
    seed = dict(seed_scars or {})
    runner = PairedReplayRunner(psyche_factory=lambda: BaselinePsycheSubject(scars=dict(seed)))
    paired = runner.run(input_frames)

    control_bc = _last_broadcast(paired.control)
    treated_bc = _last_broadcast(paired.treated)
    null_bc = _last_broadcast(paired.null)
    winner_control = control_bc.get("winning_faculty")
    winner_treated = treated_bc.get("winning_faculty")
    winner_null = null_bc.get("winning_faculty")

    control_v = _last_verification(paired.control)
    treated_v = _last_verification(paired.treated)
    null_v = _last_verification(paired.null)
    observed_delta = round(treated_v - control_v, 6)
    null_delta = round(null_v - control_v, 6)
    null_holds = abs(null_delta) <= 1e-6 and winner_null == winner_control
    winner_changed = winner_treated != winner_control

    evidence = nse.subject_evidence_frame(
        ablation_result={"direction_ok": winner_changed or observed_delta < 0.0,
                         "null_holds": null_holds},
        families_exercised=("global_workspace", "valenced_learning",
                            "identity_persistence", "higher_order_self_model"),
        run_id=input_frames[0].get("run_id", "subj") if input_frames else "subj",
        timestamp="2026-07-10T00:00:00Z")

    return {
        "winner_control": winner_control, "winner_treated": winner_treated,
        "winner_null": winner_null, "winner_changed": winner_changed,
        "control_verification": control_v, "treated_verification": treated_v,
        "observed_delta": observed_delta, "null_delta": null_delta, "null_holds": null_holds,
        "report": paired.report, "evidence_frame": evidence,
    }
```

- [ ] **Step 4: Run tests — tune if winner does not flip**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -k "ablate_scar_flips or disable_workspace_suppresses" -q`
Expected: PASS. If `winner_control != "memory_scar"`, the seeded scar (0.5) is not winning the last tick — print `paired.control.tick_outputs[-1].workspace_broadcast` and raise the seed or lower the risk weight in `subject.py` until `memory_scar` wins control and `risk_instinct`/`uncertainty_self_model` wins treated. If `null_holds` fails, confirm the null arm neutralizes the intervention (it reuses the runner's `restore` path — the subject must honor `pert.blocks`/`pert.scalar` so `restore` is a no-op).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/nervous_system/subject_ablation.py tests/test_baseline_psyche_subject.py
git commit -m "feat(nervous-system): subject intervention/null via paired runner"
```

---

### Task 9: Docs + status + full verification

**Files:**

- Modify: `docs/nervous-system-v0.md`, `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`
- Test: `tests/test_nervous_system.py` (confirm the existing import-hygiene guard covers the new files)

- [ ] **Step 1: Confirm the import-hygiene guard still passes over the new files**

The guard in `tests/test_nervous_system.py::test_nervous_system_has_no_forbidden_imports` globs `pkg.glob("*.py")`, so it already covers `subject.py`, `workspace.py`, `scar_memory.py`, `subject_runtime.py`, `subject_ablation.py`. Run:

Run: `python -m pytest tests/test_nervous_system.py -k forbidden -q`
Expected: PASS. (If any new file imported a verifier/9to5 module it would fail — none do.)

- [ ] **Step 2: Update `docs/nervous-system-v0.md`**

Add a section "## 11. BaselinePsycheSubject-v0" covering: the subject as the first
integrated replayable subject; persistent scar memory (seed → accumulate → save);
the 3-candidate workspace (`risk_instinct` / `memory_scar` / `uncertainty_self_model`)
→ verification-only pressure; the fuller CausalTrace
(`event → internal_state → broadcast → pressure`); the three interventions
(scar ablate, certainty clamp, workspace disable) run via the existing paired
runner; and the explicit **harness-evidence-only** framing (evidence_level ≤ 1,
families at most `architecture_only`, `uncertified_subject`, `not_evaluated`).
State what remains before a Level-2/3/4 claim (certified promotable runner over a
persistent integrated subject, grounded self-report faithfulness under
perturbation, real non-toy subject, longitudinal + adversarial + external audit).

- [ ] **Step 3: Update `docs/io-contract.md`**

In the Bundles subsection, note that `PneumaOutputBundle` may also carry
`psyche_state` and `workspace_broadcast` members when produced by
`BaselinePsycheSubject` via `run_subject`.

- [ ] **Step 4: Update `docs/project-status.json`**

Extend the `pneuma_nervous_system_shadow` system's `evidence_refs` with:

```json
                "src/pneuma_lab/nervous_system/subject.py",
                "src/pneuma_lab/nervous_system/subject_runtime.py",
                "src/pneuma_lab/nervous_system/subject_ablation.py",
                "docs/superpowers/specs/2026-07-10-baseline-psyche-subject-v0-design.md",
                "tests/test_baseline_psyche_subject.py"
```

Keep `project.operational_nervous_system: false`,
`training_and_rsi.runtime_model_integration: "none"`, the two `nine_to_five`
edges `not_implemented`, and the evidence/strongest_result block unchanged (no new
Level claim).

- [ ] **Step 5: Update `CLAUDE.md`**

Append one sentence to the `nervous_system/` Tree Guide bullet:

```
It also hosts BaselinePsycheSubject-v0 (`subject.py`): a minimal integrated,
replayable PsycheUnderTest with persistent scar memory, a 3-candidate global
workspace, verification-only pressure, and scar/affect/workspace intervention
tests — driven by the existing ReplayHarness/PairedReplayRunner but reported as
conservative harness evidence only.
```

- [ ] **Step 6: Full verification**

Run: `python -m pytest tests/test_baseline_psyche_subject.py -q`
Expected: PASS (all).
Run: `python -m pytest tests/ -q`
Expected: PASS (all, including existing suites).
Run: `python -m pneuma_lab.status --check`
Expected: PASS.
Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 7: Commit**

```bash
git add docs/nervous-system-v0.md docs/io-contract.md docs/project-status.json CLAUDE.md
git commit -m "docs(nervous-system): BaselinePsycheSubject-v0 contract, status, framing"
```

---

## Self-review

**Spec coverage:** §3.1 subject → Task 5. §3.2 scar_memory → Task 2. §3.3 workspace
→ Task 3. §3.4 subject_runtime → Task 6. §3.5 subject_ablation → Task 8. §3.6
evidence → Task 7. §3.7 bundle schema → Task 1. §4 candidates → Task 5 salience
math. §5 CausalTrace → Task 5 causal_path. §6 fixtures → Task 4. §7 tests: state
persists across ticks (T5), memory persists across runs (T6), memory ablation
changes pressure/broadcast (T8), winner changes under interventions (T8),
CausalTrace refs resolve (T5/T6), evidence conservative (T7/T8), deterministic +
schema-valid (T6), no authority / no verifier bypass (T5/T6 + guard T9). §8 docs →
Task 9. §9 YAGNI (verification-only) honored in Task 5 `pressures`.

**Placeholder scan:** the salience weights and scar increment are concrete; the
"tune if it fails" steps (T5 S4, T7 S4, T8 S4) are empirical verification steps
with exact print-and-adjust instructions, not deferred work. No `TODO`/`TBD`.

**Type consistency:** `BaselinePsycheSubject(scars=...)`, `reset()`,
`set_active_interventions()`, `tick()->PsycheOutputs` consistent across T5/T6/T8.
`ws.compete()` return keys (`winning_faculty`, `winning_salience`,
`salience_scores`, `competitors`, `conviction`) consistent T3/T5. `sm.load/save/
motif_of` consistent T2/T5/T6. `subject_evidence_frame(ablation_result,
families_exercised, run_id, timestamp)` consistent T6/T7/T8. `run_subject(...,
scar_store_path, shadow_log_path, schedule)` consistent T6. `run_subject_ablation(
input_frames, seed_scars)` returns `winner_control/winner_treated/winner_changed/
observed_delta/null_delta/null_holds/treated_verification/evidence_frame` used in
T8 assertions. Bundle member keys match Task 1 schema + validate change.

```

```
