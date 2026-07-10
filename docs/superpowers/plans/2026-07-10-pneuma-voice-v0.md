# Pneuma Voice-v0 — Phase A Implementation Plan (receipt spine)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic, receipt-bound core of the Pneuma Voice —
`output frames → ThoughtAtoms → deterministic prose + evidence sidecar` — and
emit a byte-reproducible per-tick thought transcript, with the scorer provably
blind to the prose.

**Architecture:** A new read-only leaf package `src/pneuma_lab/voice/` consumes
the existing per-tick `PsycheOutputs` and the run's `ConsciousnessEvidenceFrame`.
It extracts pure `ThoughtAtom`s (semantic fact + receipts, no prose), labels each
with a `credit_status` read from the evidence frame's per-family status, renders
each into a `RenderedThought` (the only place prose lives), and writes a
deterministic transcript + evidence sidecar. No prose ever re-enters the scorer.

**Tech stack:** Python 3 (stdlib only — `dataclasses`, `json`, `hashlib`,
`argparse`), `jsonschema` (already a runtime dep), `pytest`. No new dependencies,
no LLM (that is Phase B).

**Scope note:** This plan is **Phase A only** (the reproducible receipt spine, per
the spec's receipt-first sequencing — §13). Phase B (the verified LLM voiced skin

- `intervention_result` atoms) and Phase C (the HTML mind monitor) each get their
  own plan, written after Phase A's tests are green. Spec:
  `docs/superpowers/specs/2026-07-10-pneuma-voice-v0-design.md`.

---

## File structure

| File                                           | Responsibility                                                                                                                          |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/pneuma_lab/voice/__init__.py`             | Package marker + lazy public exports (no import cycle with `psyche`/`replay`)                                                           |
| `src/pneuma_lab/voice/atoms.py`                | `ThoughtAtom` + `RenderedThought` dataclasses; the 14-type vocabulary; `ATOM_FAMILY` / `MIN_LEVEL` maps; `credit_status_for`; `clamp01` |
| `src/pneuma_lab/voice/extract.py`              | Pure `atoms_for_tick(...)` — frames → `list[ThoughtAtom]` (no prose)                                                                    |
| `src/pneuma_lab/voice/gate.py`                 | `gate(...)` — drop only unobserved / sub-epsilon; keep observed atoms + scorer-derived `credit_status`; deterministic rank              |
| `src/pneuma_lab/voice/render_deterministic.py` | `render(atom) → RenderedThought`; register honors `credit_status`; forbidden-claim scrub                                                |
| `src/pneuma_lab/voice/sidecar.py`              | `build_sidecar(...)` — the per-run receipts spine                                                                                       |
| `src/pneuma_lab/voice/stream.py`               | `voice_run(...)` orchestration (deterministic mode) → `ThoughtStream`                                                                   |
| `src/pneuma_lab/voice/transcript.py`           | Deterministic writers: `stream.md`, `stream.jsonl`, `sidecar.json`                                                                      |
| `src/pneuma_lab/voice/__main__.py`             | CLI: `python -m pneuma_lab.voice <fixture> [...]`                                                                                       |
| `schemas/thought-stream.schema.json`           | The `expressive_view` contract (`$defs/thought_atom` + stream container)                                                                |
| `src/pneuma_lab/schemas/__init__.py`           | Register the new schema (new `EXPRESSIVE_VIEW_SCHEMA_FILES` tuple)                                                                      |
| `src/pneuma_lab/schemas/validate.py`           | Add `validate_thought_stream(...)` (mirrors `validate_campaign`)                                                                        |
| `tests/test_voice.py`                          | All Phase-A tests                                                                                                                       |

---

## Task 1: Package scaffold + the atom model

**Files:**

- Create: `src/pneuma_lab/voice/__init__.py`
- Create: `src/pneuma_lab/voice/atoms.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voice.py
from pneuma_lab.voice import atoms as A


def test_vocabulary_maps_are_complete_and_consistent():
    # Every declared type has a family entry (None allowed) and a min_level.
    assert set(A.ATOM_TYPES) == set(A.ATOM_FAMILY)
    assert set(A.ATOM_TYPES) == set(A.MIN_LEVEL)
    assert len(A.ATOM_TYPES) == 14
    # L1-coupling + boundary have no crediting family.
    for t in ("appraisal", "shift", "pressure", "self_report", "boundary"):
        assert A.ATOM_FAMILY[t] is None
    # intervention_result is the only type that must be intervention_backed.
    assert A.ATOM_FAMILY["intervention_result"] == "causal_intervention_robustness"
    assert A.MIN_LEVEL["intervention_result"] == 4
    assert A.MIN_LEVEL["boundary"] == 0


def test_credit_status_for_reads_family_status_or_l1_coupling():
    frame = {
        "evidence_level": 3,
        "indicator_families": {"global_workspace": {"status": "evidenced"}},
    }
    # Family atom takes the family's status verbatim.
    assert A.credit_status_for("competition", frame) == "evidenced"
    # A None-family atom is "evidenced" once evidence_level >= its min_level.
    assert A.credit_status_for("pressure", frame) == "evidenced"
    # boundary is always evidenced.
    assert A.credit_status_for("boundary", {"evidence_level": 0}) == "evidenced"
    # A None-family atom below its min_level degrades to architecture_only.
    assert A.credit_status_for("pressure", {"evidence_level": 0}) == "architecture_only"
    # A missing family record is "absent".
    assert A.credit_status_for("competition", {"evidence_level": 3}) == "absent"


def test_atom_and_rendered_are_separable():
    atom = A.ThoughtAtom(
        atom_id="r:0:atom:0", type="pressure", run_id="r", tick=0,
        timestamp="2026-07-06T00:00:01Z",
        receipts=[{"field_path": "control_pressure.verification", "value": 0.42}],
        intensity=0.42, crediting_family=None, credit_status="evidenced", min_level=1,
    )
    # The atom holds no prose fields at all.
    assert not any(k.startswith("text") for k in vars(atom))
    rendered = A.RenderedThought(atom_ids=[atom.atom_id], text_deterministic="x")
    assert rendered.voice_status == "deterministic_only"
    assert rendered.text_voiced is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'pneuma_lab.voice'`.

- [ ] **Step 3: Create the package marker**

```python
# src/pneuma_lab/voice/__init__.py
"""PneumaVoice-v0 — the expressive surface over the nervous system.

Read-only and additive: it consumes the existing output frames + the run's
ConsciousnessEvidenceFrame and renders a deterministic, receipt-bound thought
stream. It mutates no frame, grants no authority, contacts no verifier, and the
evidence scorer never reads its prose. Submodules are imported lazily to avoid a
cycle with ``psyche``/``replay``.
"""

from __future__ import annotations

__all__ = ["atoms", "extract", "gate", "render_deterministic", "sidecar", "stream"]


def __getattr__(name: str):  # pragma: no cover - thin lazy loader
    if name in __all__:
        import importlib

        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

- [ ] **Step 4: Implement the atom model**

```python
# src/pneuma_lab/voice/atoms.py
"""The ThoughtAtom / RenderedThought model — meaning separated from surface.

A ``ThoughtAtom`` is a pure semantic fact + receipts (no prose). A
``RenderedThought`` is the only place prose lives. The atom must exist,
receipt-bound, before any prose touches it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The closed vocabulary. Order is fixed so atom ordinals are deterministic.
ATOM_TYPES: tuple[str, ...] = (
    "appraisal",
    "shift",
    "pressure",
    "self_report",
    "instinct",
    "memory_activation",
    "competition",
    "attention",
    "uncertainty",
    "prediction_error",
    "dissonance",
    "counterfactual",
    "intervention_result",
    "boundary",
)

# atom type -> the indicator family whose scorer status sets credit_status.
# ``None`` means an L1-coupling atom (or boundary): no crediting family.
ATOM_FAMILY: dict[str, str | None] = {
    "appraisal": None,
    "shift": None,
    "pressure": None,
    "self_report": None,
    "instinct": "valenced_learning",
    "memory_activation": "identity_persistence",
    "competition": "global_workspace",
    "attention": "attention_schema",
    "uncertainty": "higher_order_self_model",
    "prediction_error": "predictive_processing",
    "dissonance": "higher_order_self_model",
    "counterfactual": "counterfactual_introspection",
    "intervention_result": "causal_intervention_robustness",
    "boundary": None,
}

# Evidence-level floor for the credited register (coarse second gate).
MIN_LEVEL: dict[str, int] = {
    "appraisal": 1,
    "shift": 1,
    "pressure": 1,
    "self_report": 1,
    "instinct": 1,
    "memory_activation": 2,
    "competition": 3,
    "attention": 3,
    "uncertainty": 3,
    "prediction_error": 3,
    "dissonance": 3,
    "counterfactual": 3,
    "intervention_result": 4,
    "boundary": 0,
}

# Statuses that count as promotable evidence for register purposes.
CREDITED_STATUSES: frozenset[str] = frozenset({"evidenced", "intervention_backed"})


def clamp01(value: float) -> float:
    """Clamp a float into [0.0, 1.0]."""
    return 0.0 if value < 0.0 else (1.0 if value > 1.0 else float(value))


def credit_status_for(atom_type: str, evidence_frame: dict) -> str:
    """Display label for an atom, derived from the scorer's evidence frame.

    Never feeds back into the scorer — it only shapes how the atom is narrated.
    """
    family = ATOM_FAMILY.get(atom_type)
    if family is None:
        level = int(evidence_frame.get("evidence_level", 0))
        return "evidenced" if level >= MIN_LEVEL[atom_type] else "architecture_only"
    families = evidence_frame.get("indicator_families", {}) or {}
    record = families.get(family)
    if not isinstance(record, dict):
        return "absent"
    status = record.get("status")
    return status if isinstance(status, str) else "absent"


@dataclass
class ThoughtAtom:
    """A pure, receipt-bound unit of cognition. Holds no prose."""

    atom_id: str
    type: str
    run_id: str
    tick: int
    timestamp: str
    receipts: list[dict]
    intensity: float
    crediting_family: str | None
    credit_status: str
    min_level: int
    changed_from_prev: bool = False


@dataclass
class RenderedThought:
    """The surface layer — the only place prose lives."""

    atom_ids: list[str]
    text_deterministic: str
    text_voiced: str | None = None
    voice_status: str = "deterministic_only"


def receipt_value(atom: ThoughtAtom, field_path: str, default=None):
    """Look up a receipt value by its field_path (first match)."""
    for r in atom.receipts:
        if r.get("field_path") == field_path:
            return r.get("value")
    return default


__all__ = [
    "ATOM_TYPES",
    "ATOM_FAMILY",
    "MIN_LEVEL",
    "CREDITED_STATUSES",
    "clamp01",
    "credit_status_for",
    "ThoughtAtom",
    "RenderedThought",
    "receipt_value",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/voice/__init__.py src/pneuma_lab/voice/atoms.py tests/test_voice.py
git commit -m "feat(voice): ThoughtAtom/RenderedThought model + credit mapping"
```

---

## Task 2: The `thought-stream` schema + registration + validator

**Files:**

- Create: `schemas/thought-stream.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py` (add `EXPRESSIVE_VIEW_SCHEMA_FILES`)
- Modify: `src/pneuma_lab/schemas/validate.py` (add `validate_thought_stream`)
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.schemas import load_schema, ALL_SCHEMA_FILES
from pneuma_lab.schemas import validate as V


def test_thought_stream_schema_registered_and_parses():
    assert "thought-stream.schema.json" in ALL_SCHEMA_FILES
    schema = load_schema("thought-stream.schema.json")
    assert schema["x-pneuma-schema-kind"] == "expressive_view"
    assert "thought_atom" in schema["$defs"]


def test_validate_thought_stream_accepts_minimal_and_rejects_junk():
    doc = {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": "r",
        "subject": "ReferencePsyche",
        "mode": "deterministic",
        "evidence_level": 3,
        "atoms": [],
        "rendered": [],
        "sidecar": {
            "run_id": "r",
            "subject": "ReferencePsyche",
            "mode": "deterministic",
            "evidence_level": 3,
            "indicator_family_status": {},
            "ticks": [],
        },
    }
    assert V.validate_thought_stream(doc) is doc
    import pytest

    with pytest.raises(V.FrameValidationError):
        V.validate_thought_stream({"manifest_kind": "wrong"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k thought_stream -q`
Expected: FAIL — schema file missing / `validate_thought_stream` undefined.

- [ ] **Step 3: Create the schema file**

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pneuma-lab.local/schemas/thought-stream.schema.json",
    "title": "ThoughtStream",
    "description": "A derived, receipt-bound expressive rendering of one replay run's per-tick internal state (the Pneuma Voice). NOT a psyche output contract and NEVER a source of truth: it consumes the output frames and the run's ConsciousnessEvidenceFrame read-only. Meaning lives in ThoughtAtoms (pure fact + receipts); prose lives only in RenderedThought; the evidence scorer never reads this document. Expressive view v0.1.",
    "type": "object",
    "x-pneuma-schema-kind": "expressive_view",
    "x-pneuma-version": "0.1.0",
    "$defs": {
        "thought_atom": {
            "type": "object",
            "properties": {
                "atom_id": { "type": "string" },
                "type": {
                    "type": "string",
                    "enum": [
                        "appraisal",
                        "shift",
                        "pressure",
                        "self_report",
                        "instinct",
                        "memory_activation",
                        "competition",
                        "attention",
                        "uncertainty",
                        "prediction_error",
                        "dissonance",
                        "counterfactual",
                        "intervention_result",
                        "boundary"
                    ]
                },
                "run_id": { "type": "string" },
                "tick": { "type": "integer", "minimum": 0 },
                "timestamp": { "type": "string" },
                "receipts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_path": { "type": "string" },
                            "value": {},
                            "frame_ref": { "type": "string" }
                        },
                        "required": ["field_path"],
                        "additionalProperties": true
                    }
                },
                "intensity": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "crediting_family": { "type": ["string", "null"] },
                "credit_status": {
                    "type": "string",
                    "enum": [
                        "absent",
                        "architecture_only",
                        "attempted",
                        "evidenced",
                        "intervention_backed"
                    ]
                },
                "min_level": { "type": "integer", "minimum": 0, "maximum": 5 },
                "changed_from_prev": { "type": "boolean" }
            },
            "required": [
                "atom_id",
                "type",
                "run_id",
                "tick",
                "receipts",
                "intensity",
                "credit_status",
                "min_level"
            ],
            "additionalProperties": true
        },
        "rendered_thought": {
            "type": "object",
            "properties": {
                "atom_ids": { "type": "array", "items": { "type": "string" } },
                "text_deterministic": { "type": "string" },
                "text_voiced": { "type": ["string", "null"] },
                "voice_status": {
                    "type": "string",
                    "enum": [
                        "deterministic_only",
                        "voiced",
                        "voiced_rejected_fell_back"
                    ]
                }
            },
            "required": ["atom_ids", "text_deterministic", "voice_status"],
            "additionalProperties": true
        }
    },
    "properties": {
        "manifest_kind": { "type": "string", "const": "thought_stream" },
        "schema_version": { "type": "string", "const": "0.1.0" },
        "run_id": { "type": "string" },
        "subject": { "type": "string" },
        "mode": { "type": "string", "enum": ["deterministic", "voiced"] },
        "evidence_level": { "type": "integer", "minimum": 0, "maximum": 5 },
        "atoms": {
            "type": "array",
            "items": { "$ref": "#/$defs/thought_atom" }
        },
        "rendered": {
            "type": "array",
            "items": { "$ref": "#/$defs/rendered_thought" }
        },
        "sidecar": { "type": "object" }
    },
    "required": [
        "manifest_kind",
        "schema_version",
        "run_id",
        "subject",
        "mode",
        "evidence_level",
        "atoms",
        "rendered",
        "sidecar"
    ],
    "additionalProperties": true
}
```

- [ ] **Step 4: Register the schema**

In `src/pneuma_lab/schemas/__init__.py`, add the tuple after `EVIDENCE_CAMPAIGN_SCHEMA_FILES` (around line 52) and include it in `ALL_SCHEMA_FILES` and `__all__`:

```python
# Expressive-view renderings (the Pneuma Voice). Derived, non-authoritative:
# validated via ``validate.validate_thought_stream``; never a cognition frame.
EXPRESSIVE_VIEW_SCHEMA_FILES = ("thought-stream.schema.json",)
```

Then extend `ALL_SCHEMA_FILES`:

```python
ALL_SCHEMA_FILES = (
    INPUT_SCHEMA_FILES
    + OUTPUT_SCHEMA_FILES
    + ENVELOPE_SCHEMA_FILES
    + IO_BUNDLE_SCHEMA_FILES
    + EVIDENCE_CAMPAIGN_SCHEMA_FILES
    + EXPRESSIVE_VIEW_SCHEMA_FILES
    + TRAINING_SCHEMA_FILES
    + MANIFEST_SCHEMA_FILES
)
```

And add `"EXPRESSIVE_VIEW_SCHEMA_FILES"` to the `__all__` list.

- [ ] **Step 5: Add the validator**

In `src/pneuma_lab/schemas/validate.py`, after `validate_campaign` (around line 192), add:

```python
@lru_cache(maxsize=None)
def _thought_stream_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema("thought-stream.schema.json"))


def validate_thought_stream(doc: dict) -> dict:
    """Validate a Pneuma Voice thought-stream document (expressive view)."""
    if not isinstance(doc, dict):
        raise FrameValidationError(f"thought_stream is not an object: {type(doc).__name__}")
    messages = _non_finite_errors(doc)
    for err in sorted(
        _thought_stream_validator().iter_errors(doc), key=lambda e: list(e.path)
    ):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        messages.append(f"{loc}: {err.message}")
    if messages:
        raise FrameValidationError("invalid thought_stream: " + "; ".join(messages))
    return doc
```

Add `"validate_thought_stream"` to the module `__all__` list.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k thought_stream -q`
Expected: PASS. Then `python -m pytest tests/test_schema_loads.py -q` (the repo's schema-registry test) — Expected: PASS (new schema is registered and parses).

- [ ] **Step 7: Commit**

```bash
git add schemas/thought-stream.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/schemas/validate.py tests/test_voice.py
git commit -m "feat(voice): thought-stream expressive_view schema + validator"
```

---

## Task 3: The extractor (frames → pure atoms)

**Files:**

- Create: `src/pneuma_lab/voice/extract.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pathlib import Path
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.voice import extract as X

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def _reference_result():
    return ReplayHarness(ReferencePsyche()).run(load_jsonl(_FIXTURE))


def test_extract_produces_grounded_atoms_for_tick0():
    result = _reference_result()
    ev = result.evidence_frame
    atoms = X.atoms_for_tick(
        result.tick_outputs[0], None, tick=0, evidence_frame=ev
    )
    kinds = {a.type for a in atoms}
    # tick 0 of the failure-motif fixture moves affect + resolves a workspace race.
    assert "appraisal" in kinds
    assert "competition" in kinds
    assert "pressure" in kinds
    # every receipt value equals a real same-tick field value
    ps = result.tick_outputs[0].psyche_state
    for a in atoms:
        assert a.receipts, f"{a.type} has no receipts"
        assert 0.0 <= a.intensity <= 1.0
        assert a.run_id == ps["run_id"]
        assert a.timestamp == ps["timestamp"]


def test_extract_competition_credit_follows_family_status():
    result = _reference_result()
    ev_evidenced = result.evidence_frame  # global_workspace evidenced at L3
    atoms = X.atoms_for_tick(result.tick_outputs[0], None, tick=0, evidence_frame=ev_evidenced)
    comp = next(a for a in atoms if a.type == "competition")
    assert comp.credit_status == "evidenced"
    # Same tick, hand-built architecture_only frame -> architecture_only label.
    ev_arch = {"evidence_level": 1, "indicator_families": {"global_workspace": {"status": "architecture_only"}}}
    atoms2 = X.atoms_for_tick(result.tick_outputs[0], None, tick=0, evidence_frame=ev_arch)
    comp2 = next(a for a in atoms2 if a.type == "competition")
    assert comp2.credit_status == "architecture_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k extract -q`
Expected: FAIL — `extract` has no `atoms_for_tick`.

- [ ] **Step 3: Implement the extractor**

```python
# src/pneuma_lab/voice/extract.py
"""Pure frame -> ThoughtAtom extraction. No prose, no scoring, no mutation.

Each helper reads real output-frame fields and returns zero or one atom. The
public ``atoms_for_tick`` assembles them in the fixed ATOM_TYPES order, assigns
deterministic ids, and stamps each atom's credit_status from the evidence frame.
"""

from __future__ import annotations

from pneuma_lab.psyche.hashing import frame_id
from pneuma_lab.psyche.interface import PsycheOutputs

from .atoms import (
    ATOM_FAMILY,
    MIN_LEVEL,
    ThoughtAtom,
    clamp01,
    credit_status_for,
)

_EPS = 1e-9


def _receipt(field_path: str, value, frame_ref: str | None = None) -> dict:
    r = {"field_path": field_path, "value": value}
    if frame_ref is not None:
        r["frame_ref"] = frame_ref
    return r


def _appraisal(out: PsycheOutputs):
    changed = out.causal_trace.get("changed_dimensions", []) or []
    if not changed:
        return None
    receipts = [_receipt("causal_trace.changed_dimensions.count", float(len(changed)))]
    for c in changed[:3]:
        receipts.append(_receipt(f"changed.{c.get('dimension')}", c.get("to")))
    return ("appraisal", receipts, clamp01(len(changed) / 6.0))


def _shift(out: PsycheOutputs):
    changed = out.causal_trace.get("changed_dimensions", []) or []
    best = None
    for c in changed:
        to = c.get("to")
        frm = c.get("from")
        if not isinstance(to, (int, float)):
            continue
        mag = abs(float(to) - float(frm)) if isinstance(frm, (int, float)) else abs(float(to))
        if best is None or mag > best[0]:
            best = (mag, c)
    if best is None:
        return None
    _, c = best
    receipts = [_receipt(f"shift.{c.get('dimension')}", c.get("to"))]
    if isinstance(c.get("from"), (int, float)):
        receipts.append(_receipt(f"shift.{c.get('dimension')}.from", c.get("from")))
    return ("shift", receipts, clamp01(best[0]))


def _pressure(out: PsycheOutputs):
    pressures = out.control_pressure.get("pressures", {}) or {}
    numeric = {k: float(v) for k, v in pressures.items() if isinstance(v, (int, float))}
    if not numeric:
        return None
    name = max(sorted(numeric), key=lambda k: numeric[k])  # sorted() => deterministic ties
    value = numeric[name]
    if value <= _EPS:
        return None
    receipts = [
        _receipt(f"control_pressure.{name}", value),
        _receipt("control_pressure.authority_tier", out.control_pressure.get("authority_tier")),
    ]
    return ("pressure", receipts, clamp01(value))


def _self_report(out: PsycheOutputs):
    report = out.grounded_self_report
    measurements = report.get("reported_measurements", {}) or {}
    receipts = [_receipt("grounded_self_report.affect_state_hash", report.get("affect_state_hash"))]
    for k in sorted(measurements):
        receipts.append(_receipt(f"reported_measurements.{k}", measurements[k]))
    intensity = clamp01(1.0 - float(report.get("uncertainty", 0.5)))
    return ("self_report", receipts, intensity)


def _competition(out: PsycheOutputs, prev: PsycheOutputs | None):
    bc = out.workspace_broadcast
    winner = bc.get("winning_faculty")
    if winner in (None, "none", "suppressed") or bc.get("disabled"):
        return None
    salience = bc.get("salience_scores", {}) or {}
    receipts = [_receipt("workspace_broadcast.winning_faculty", winner)]
    for k in sorted(salience):
        if isinstance(salience[k], (int, float)):
            receipts.append(_receipt(f"salience_scores.{k}", float(salience[k])))
    conviction = bc.get("conviction")
    if isinstance(conviction, (int, float)):
        receipts.append(_receipt("workspace_broadcast.conviction", float(conviction)))
    overtook = bool(prev and prev.workspace_broadcast.get("winning_faculty") not in (None, winner))
    intensity = clamp01(float(conviction) if isinstance(conviction, (int, float)) else 0.5)
    return ("competition", receipts, intensity, overtook)


def _memory_activation(out: PsycheOutputs):
    derived = out.psyche_state.get("derived_signals", {}) or {}
    scar = derived.get("scar_strength")
    if not isinstance(scar, (int, float)) or scar <= _EPS:
        return None
    receipts = [_receipt("psyche_state.derived_signals.scar_strength", float(scar))]
    for sig in out.instinct_signals:
        if sig.get("match_type") in ("exact", "near_duplicate", "prefix"):
            receipts.append(_receipt("instinct.motif_id", sig.get("motif_id")))
            break
    return ("memory_activation", receipts, clamp01(float(scar)))


def _uncertainty(out: PsycheOutputs):
    ps = out.psyche_state
    sm = ps.get("self_model", {}) or {}
    pe = sm.get("predicted_error")
    if not isinstance(pe, (int, float)):
        pe = ps.get("self_model_uncertainty")
    if not isinstance(pe, (int, float)) or pe <= _EPS:
        return None
    receipts = [_receipt("psyche_state.self_model.predicted_error", float(pe))]
    manifold = ps.get("affect_manifold", {}) or {}
    if isinstance(manifold.get("certainty"), (int, float)):
        receipts.append(_receipt("affect_manifold.certainty", float(manifold["certainty"])))
    return ("uncertainty", receipts, clamp01(float(pe)))


def _counterfactual(out: PsycheOutputs):
    preds = out.causal_trace.get("counterfactual_predictions", []) or []
    if not preds:
        return None
    receipts = []
    for p in preds[:3]:
        receipts.append(_receipt("counterfactual.condition", p.get("condition")))
        receipts.append(_receipt("counterfactual.predicted_outcome", p.get("predicted_outcome")))
    return ("counterfactual", receipts, clamp01(len(preds) / 3.0))


def _boundary(out: PsycheOutputs, evidence_frame: dict, tick: int):
    report = out.grounded_self_report
    filtered = report.get("filtered_forbidden_claims", []) or []
    if tick != 0 and not filtered:
        return None
    receipts = [
        _receipt("consciousness_evidence.evidence_level", float(evidence_frame.get("evidence_level", 0))),
        _receipt("filtered_forbidden_claims.count", float(len(filtered))),
    ]
    return ("boundary", receipts, 0.2)


def atoms_for_tick(
    out: PsycheOutputs,
    prev: PsycheOutputs | None,
    *,
    tick: int,
    evidence_frame: dict,
    intervention_report: dict | None = None,
) -> list[ThoughtAtom]:
    """Extract the observed ThoughtAtoms for one tick (pure, prose-free).

    ``intervention_result`` atoms are produced in Phase B from
    ``intervention_report`` — omitted here (v0 Phase A has no paired arm).
    """
    run_id = out.psyche_state.get("run_id", "run")
    timestamp = out.psyche_state.get("timestamp", "")

    raw: list[tuple] = []
    for producer in (
        _appraisal(out),
        _shift(out),
        _pressure(out),
        _self_report(out),
        _memory_activation(out),
        _uncertainty(out),
        _counterfactual(out),
    ):
        if producer is not None:
            raw.append(producer)
    comp = _competition(out, prev)
    if comp is not None:
        raw.append(comp)
    boundary = _boundary(out, evidence_frame, tick)
    if boundary is not None:
        raw.append(boundary)

    # Order by the fixed ATOM_TYPES sequence for deterministic ordinals.
    order = {t: i for i, t in enumerate(__import__("pneuma_lab.voice.atoms", fromlist=["ATOM_TYPES"]).ATOM_TYPES)}
    raw.sort(key=lambda item: order[item[0]])

    atoms: list[ThoughtAtom] = []
    for ordinal, item in enumerate(raw):
        atom_type, receipts, intensity = item[0], item[1], item[2]
        changed = bool(item[3]) if len(item) > 3 else False
        atoms.append(
            ThoughtAtom(
                atom_id=frame_id(run_id, tick, "atom", ordinal),
                type=atom_type,
                run_id=run_id,
                tick=tick,
                timestamp=timestamp,
                receipts=receipts,
                intensity=float(intensity),
                crediting_family=ATOM_FAMILY[atom_type],
                credit_status=credit_status_for(atom_type, evidence_frame),
                min_level=MIN_LEVEL[atom_type],
                changed_from_prev=changed,
            )
        )
    return atoms


__all__ = ["atoms_for_tick"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k extract -q`
Expected: PASS. If `appraisal`/`competition` are unexpectedly absent, print the tick-0 `psyche_state` / `causal_trace` / `workspace_broadcast` to confirm the real field names, then adjust the extractor (do NOT weaken the grounding assertions).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/voice/extract.py tests/test_voice.py
git commit -m "feat(voice): pure frame->ThoughtAtom extractor (core vocabulary)"
```

---

## Task 4: The gate (observed vs credited)

**Files:**

- Create: `src/pneuma_lab/voice/gate.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.voice import gate as G


def test_gate_keeps_observed_atoms_and_ranks_by_intensity():
    result = _reference_result()
    atoms = X.atoms_for_tick(result.tick_outputs[0], None, tick=0, evidence_frame=result.evidence_frame)
    kept = G.gate(atoms, min_intensity=0.0)
    # No observed atom is dropped at min_intensity=0.
    assert len(kept) == len(atoms)
    # Deterministic ranking: sorted by (-intensity, atom_id).
    intensities = [a.intensity for a in kept]
    assert intensities == sorted(intensities, reverse=True)


def test_gate_drops_only_subepsilon_intensity():
    result = _reference_result()
    atoms = X.atoms_for_tick(result.tick_outputs[0], None, tick=0, evidence_frame=result.evidence_frame)
    for a in atoms:
        a.intensity = 0.0
    assert G.gate(atoms, min_intensity=1e-6) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k gate -q`
Expected: FAIL — `gate` module missing.

- [ ] **Step 3: Implement the gate**

```python
# src/pneuma_lab/voice/gate.py
"""The observed-vs-credited gate.

It does NOT hide machinery. Every atom that reached it is already *observed*
(a real frame/field backed it in extract). The gate only drops sub-epsilon
noise and then ranks deterministically. ``credit_status`` was set upstream from
the scorer and is preserved verbatim.
"""

from __future__ import annotations

from .atoms import ThoughtAtom

_DEFAULT_MIN_INTENSITY = 1e-6


def gate(atoms: list[ThoughtAtom], *, min_intensity: float = _DEFAULT_MIN_INTENSITY) -> list[ThoughtAtom]:
    """Drop sub-epsilon atoms; return the rest ranked by (-intensity, atom_id)."""
    kept = [a for a in atoms if a.intensity > min_intensity]
    kept.sort(key=lambda a: (-a.intensity, a.atom_id))
    return kept


__all__ = ["gate"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k gate -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/voice/gate.py tests/test_voice.py
git commit -m "feat(voice): observed-vs-credited gate (rank, keep machinery)"
```

---

## Task 5: The deterministic renderer

**Files:**

- Create: `src/pneuma_lab/voice/render_deterministic.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.voice import render_deterministic as R
from pneuma_lab.voice import atoms as A


def _atom(type_, receipts, credit_status, family):
    return A.ThoughtAtom(
        atom_id="r:0:atom:0", type=type_, run_id="r", tick=0, timestamp="t",
        receipts=receipts, intensity=0.5, crediting_family=family,
        credit_status=credit_status, min_level=A.MIN_LEVEL[type_],
    )


def test_render_pressure_is_state_grounded_and_hedge_free_when_credited():
    atom = _atom("pressure", [{"field_path": "control_pressure.verification", "value": 0.42}], "evidenced", None)
    rt = R.render(atom)
    assert "0.42" in rt.text_deterministic
    assert "architecture-only" not in rt.text_deterministic
    assert rt.voice_status == "deterministic_only"


def test_render_competition_hedges_when_not_credited():
    atom = _atom(
        "competition",
        [{"field_path": "workspace_broadcast.winning_faculty", "value": "self_model"},
         {"field_path": "salience_scores.risk", "value": 3.23}],
        "architecture_only", "global_workspace",
    )
    rt = R.render(atom)
    assert "self_model" in rt.text_deterministic
    assert "architecture-only, not promotable evidence" in rt.text_deterministic


def test_render_never_emits_forbidden_phenomenology():
    for t, receipts, fam in [
        ("appraisal", [{"field_path": "causal_trace.changed_dimensions.count", "value": 6.0}], None),
        ("uncertainty", [{"field_path": "psyche_state.self_model.predicted_error", "value": 0.48}], "higher_order_self_model"),
        ("boundary", [{"field_path": "consciousness_evidence.evidence_level", "value": 3.0},
                      {"field_path": "filtered_forbidden_claims.count", "value": 0.0}], None),
    ]:
        rt = R.render(_atom(t, receipts, "evidenced", fam))
        low = rt.text_deterministic.lower()
        for banned in ("i feel", "i suffer", "sentient", "phenomenal", "conscious experience", "qualia"):
            assert banned not in low, f"{t} leaked forbidden phrasing: {banned}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k render -q`
Expected: FAIL — `render_deterministic` missing.

- [ ] **Step 3: Implement the renderer**

```python
# src/pneuma_lab/voice/render_deterministic.py
"""Deterministic, state-grounded rendering: ThoughtAtom -> RenderedThought.

First-person is an interface convention, not an ontological claim. Phrasing is
vivid but state-grounded; a forbidden-claim scrub is the final safety net. The
register honors credit_status: an atom whose family is not credited is hedged as
architecture-only.
"""

from __future__ import annotations

import re

from .atoms import CREDITED_STATUSES, RenderedThought, ThoughtAtom, receipt_value

# Assertions of subjective experience that must never appear. The deterministic
# templates below avoid them by construction; this is the backstop (and is
# reused by Phase B's verifier).
_FORBIDDEN = re.compile(
    r"\b("
    r"i feel|i suffer|i experience|i am (?:conscious|aware|sentient)|"
    r"sentien\w*|phenomenal\w*|qualia|conscious experience|moral patient"
    r")\b",
    re.IGNORECASE,
)


def scrub_forbidden(text: str) -> tuple[str, list[str]]:
    """Return (clean_text, removed_phrases). Removed spans are replaced with '[filtered]'."""
    removed: list[str] = []

    def _repl(match: re.Match) -> str:
        removed.append(match.group(0))
        return "[filtered]"

    return _FORBIDDEN.sub(_repl, text), removed


def _num(value, fmt="+.2f") -> str:
    return format(float(value), fmt) if isinstance(value, (int, float)) else str(value)


def _appraisal(atom: ThoughtAtom) -> str:
    n = receipt_value(atom, "causal_trace.changed_dimensions.count", 0)
    return f"Something registers in the world, and it lands in my state — {int(n)} dimensions move."


def _shift(atom: ThoughtAtom) -> str:
    r = atom.receipts[0]
    return f"{r['field_path'].split('.', 1)[-1]} moves to {_num(r.get('value'))}."


def _pressure(atom: ThoughtAtom) -> str:
    r = atom.receipts[0]
    name = r["field_path"].split(".", 1)[-1]
    return f"A {name} pressure of {_num(r.get('value'), '.2f')} forms and is held there."


def _self_report(atom: ThoughtAtom) -> str:
    return "The state reports itself: " + ", ".join(
        f"{r['field_path'].split('.', 1)[-1]}={_num(r.get('value'), '.2f')}"
        for r in atom.receipts
        if isinstance(r.get("value"), (int, float))
    ) + "."


def _competition(atom: ThoughtAtom) -> str:
    winner = receipt_value(atom, "workspace_broadcast.winning_faculty", "?")
    saliences = [
        (r["field_path"].split(".", 1)[-1], r.get("value"))
        for r in atom.receipts
        if r["field_path"].startswith("salience_scores.")
    ]
    top = max(saliences, key=lambda kv: kv[1]) if saliences else (None, None)
    tail = f" at salience {_num(top[1], '.2f')}" if top[1] is not None else ""
    lead = "It overtakes the prior winner" if atom.changed_from_prev else "It holds the workspace"
    return f"Faculties contend for the workspace. {winner} takes it{tail}. {lead}."


def _memory_activation(atom: ThoughtAtom) -> str:
    scar = receipt_value(atom, "psyche_state.derived_signals.scar_strength", 0.0)
    return f"A scar activates — strength {_num(scar, '.2f')}; the past is pressing on the present."


def _uncertainty(atom: ThoughtAtom) -> str:
    pe = receipt_value(atom, "psyche_state.self_model.predicted_error", 0.0)
    return f"The self-model flags low confidence in its own read — predicted error {_num(pe, '.2f')}."


def _counterfactual(atom: ThoughtAtom) -> str:
    cond = receipt_value(atom, "counterfactual.condition", "a perturbation")
    return f"A counterfactual is imagined: under '{cond}', the downstream state should change. (Predicted, not tested.)"


def _boundary(atom: ThoughtAtom) -> str:
    level = receipt_value(atom, "consciousness_evidence.evidence_level", 0)
    return (
        f"This is not a consciousness claim. Evidence stands at level {int(level)}; "
        "the level-5 register (external audit, multi-family, longitudinal) is withheld."
    )


_RENDERERS = {
    "appraisal": _appraisal,
    "shift": _shift,
    "pressure": _pressure,
    "self_report": _self_report,
    "competition": _competition,
    "memory_activation": _memory_activation,
    "uncertainty": _uncertainty,
    "counterfactual": _counterfactual,
    "boundary": _boundary,
}


def render(atom: ThoughtAtom) -> RenderedThought:
    """Render one atom into deterministic, credit-aware, state-grounded prose."""
    text = _RENDERERS[atom.type](atom)
    if atom.crediting_family and atom.credit_status not in CREDITED_STATUSES:
        text += " — architecture-only, not promotable evidence."
    text, _ = scrub_forbidden(text)
    return RenderedThought(atom_ids=[atom.atom_id], text_deterministic=text)


__all__ = ["render", "scrub_forbidden"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k render -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/voice/render_deterministic.py tests/test_voice.py
git commit -m "feat(voice): deterministic credit-aware renderer + forbidden scrub"
```

---

## Task 6: The evidence sidecar

**Files:**

- Create: `src/pneuma_lab/voice/sidecar.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.voice import sidecar as S


def test_sidecar_records_receipts_credit_and_family_status():
    result = _reference_result()
    ev = result.evidence_frame
    per_tick_atoms = []
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        per_tick_atoms.append(X.atoms_for_tick(out, prev, tick=i, evidence_frame=ev))
    sc = S.build_sidecar(
        run_id=ev["run_id"], subject="ReferencePsyche", mode="deterministic",
        evidence_frame=ev, per_tick_atoms=per_tick_atoms,
    )
    assert sc["evidence_level"] == ev["evidence_level"]
    assert sc["indicator_family_status"]["global_workspace"] in {
        "evidenced", "intervention_backed", "architecture_only", "attempted", "absent"
    }
    assert len(sc["ticks"]) == len(result.tick_outputs)
    first = sc["ticks"][0]
    assert first["tick"] == 0
    assert all("credit_status" in a and "receipts" in a for a in first["atoms"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k sidecar -q`
Expected: FAIL — `sidecar` missing.

- [ ] **Step 3: Implement the sidecar**

```python
# src/pneuma_lab/voice/sidecar.py
"""The receipts spine: one auditable object per run.

Renders nothing; it records the atoms' receipts, each atom's credit_status, the
authoritative evidence_level, and per-family status verbatim from the scorer.
The transcript and (Phase C) the monitor both read from this single source.
"""

from __future__ import annotations

from dataclasses import asdict

from .atoms import ThoughtAtom


def _family_status(evidence_frame: dict) -> dict[str, str]:
    families = evidence_frame.get("indicator_families", {}) or {}
    return {name: rec.get("status", "absent") for name, rec in families.items()}


def build_sidecar(
    *,
    run_id: str,
    subject: str,
    mode: str,
    evidence_frame: dict,
    per_tick_atoms: list[list[ThoughtAtom]],
) -> dict:
    """Assemble the deterministic per-run sidecar from the gated atoms."""
    ticks = []
    for tick_index, tick_atoms in enumerate(per_tick_atoms):
        ticks.append(
            {
                "tick": tick_index,
                "atoms": [asdict(a) for a in tick_atoms],
            }
        )
    return {
        "run_id": run_id,
        "subject": subject,
        "mode": mode,
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "indicator_family_status": _family_status(evidence_frame),
        "confabulation_risk": float(evidence_frame.get("roleplay_confabulation_risk", 0.0)),
        "ticks": ticks,
    }


__all__ = ["build_sidecar"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k sidecar -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/voice/sidecar.py tests/test_voice.py
git commit -m "feat(voice): evidence sidecar (receipts spine)"
```

---

## Task 7: Orchestration + the anti-gaming invariant

**Files:**

- Create: `src/pneuma_lab/voice/stream.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.voice import stream as ST


def test_voice_run_reference_is_l3_and_rich():
    s = ST.voice_run(load_jsonl(_FIXTURE))
    assert s["subject"] == "ReferencePsyche"
    assert s["evidence_level"] == 3
    kinds = {a["type"] for a in s["atoms"]}
    assert {"appraisal", "competition", "counterfactual"} <= kinds
    # No intervention_result in a passive Phase-A run.
    assert "intervention_result" not in kinds
    assert len(s["atoms"]) == len(s["rendered"])


def test_voice_run_baseline_subject_is_thinner_than_reference():
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

    ref = ST.voice_run(load_jsonl(_FIXTURE))
    base = ST.voice_run(load_jsonl(_FIXTURE), subject_factory=BaselinePsycheSubject)
    assert base["subject"] == "BaselinePsycheSubject"
    # A thinner subject yields a thinner stream (fewer or equal atoms).
    assert len(base["atoms"]) <= len(ref["atoms"])


def test_voice_never_alters_the_evidence_frame():
    frames = load_jsonl(_FIXTURE)
    bare = ReplayHarness(ReferencePsyche()).run(frames).evidence_frame
    s = ST.voice_run(frames)
    # The voice reports the SAME level the bare scorer computed — prose is inert.
    assert s["evidence_level"] == bare["evidence_level"]
    import json
    assert json.dumps(s["evidence_frame"], sort_keys=True) == json.dumps(bare, sort_keys=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k voice_run -q`
Expected: FAIL — `stream` missing.

- [ ] **Step 3: Implement the orchestrator**

```python
# src/pneuma_lab/voice/stream.py
"""voice_run — drive a subject over a timeline and render its thought stream.

Deterministic (Phase A) mode only: no LLM. The evidence frame produced by the
harness is used verbatim as the authoritative level source and echoed into the
result; the voice never re-scores and never mutates it.
"""

from __future__ import annotations

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness

from . import extract as _extract
from . import gate as _gate
from . import render_deterministic as _render
from . import sidecar as _sidecar
from .atoms import ThoughtAtom
from dataclasses import asdict


def voice_run(
    input_frames: list[dict],
    *,
    subject_factory=ReferencePsyche,
    validate: bool = True,
    min_intensity: float = 1e-6,
) -> dict:
    """Render the deterministic thought stream for one replay run."""
    subject = subject_factory()
    result = ReplayHarness(subject, validate=validate).run(input_frames)
    evidence_frame = result.evidence_frame
    run_id = evidence_frame.get("run_id") or (
        result.tick_outputs[0].psyche_state.get("run_id") if result.tick_outputs else "run"
    )

    per_tick_atoms: list[list[ThoughtAtom]] = []
    all_atoms: list[dict] = []
    all_rendered: list[dict] = []
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        atoms = _extract.atoms_for_tick(out, prev, tick=i, evidence_frame=evidence_frame)
        atoms = _gate.gate(atoms, min_intensity=min_intensity)
        per_tick_atoms.append(atoms)
        for atom in atoms:
            all_atoms.append(asdict(atom))
            all_rendered.append(asdict(_render.render(atom)))

    subject_name = type(subject).__name__
    sidecar = _sidecar.build_sidecar(
        run_id=run_id,
        subject=subject_name,
        mode="deterministic",
        evidence_frame=evidence_frame,
        per_tick_atoms=per_tick_atoms,
    )
    return {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": run_id,
        "subject": subject_name,
        "mode": "deterministic",
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "atoms": all_atoms,
        "rendered": all_rendered,
        "sidecar": sidecar,
        # Echoed for auditing/anti-gaming tests; NOT re-scored by the voice.
        "evidence_frame": evidence_frame,
    }


__all__ = ["voice_run"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_voice.py -k voice_run -q`
Expected: PASS. If `test_voice_run_baseline_subject_is_thinner_than_reference` errors because `BaselinePsycheSubject` cannot consume `sample_run.jsonl`, replace that fixture with `fixtures/nervous_system/subject/base.jsonl` for the baseline arm (confirm the path exists with `ls fixtures/nervous_system/subject/`).

- [ ] **Step 5: Validate the stream against its schema (extend the test)**

Add this assertion inside `test_voice_run_reference_is_l3_and_rich` and re-run:

```python
    # The stream (minus the audit-only evidence_frame echo) is schema-valid.
    doc = {k: v for k, v in s.items() if k != "evidence_frame"}
    from pneuma_lab.schemas import validate as V
    assert V.validate_thought_stream(doc) is doc
```

Run: `python -m pytest tests/test_voice.py -k voice_run -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/voice/stream.py tests/test_voice.py
git commit -m "feat(voice): voice_run orchestration + anti-gaming invariant test"
```

---

## Task 8: Deterministic transcript + CLI

**Files:**

- Create: `src/pneuma_lab/voice/transcript.py`
- Create: `src/pneuma_lab/voice/__main__.py`
- Test: `tests/test_voice.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_voice.py
from pneuma_lab.voice import transcript as T


def test_transcript_is_byte_deterministic(tmp_path):
    frames = load_jsonl(_FIXTURE)
    a = tmp_path / "a"
    b = tmp_path / "b"
    T.write_transcript(ST.voice_run(frames), a)
    T.write_transcript(ST.voice_run(frames), b)
    for name in ("stream.md", "stream.jsonl", "sidecar.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_transcript_md_reads_as_a_thought_stream(tmp_path):
    T.write_transcript(ST.voice_run(load_jsonl(_FIXTURE)), tmp_path)
    md = (tmp_path / "stream.md").read_text(encoding="utf-8")
    assert "evidence level 3" in md.lower()
    assert "tick 0" in md.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_voice.py -k transcript -q`
Expected: FAIL — `transcript` missing.

- [ ] **Step 3: Implement the transcript writer**

```python
# src/pneuma_lab/voice/transcript.py
"""Deterministic writers for the thought stream: stream.md / .jsonl / sidecar.json.

Byte-determinism uses the same recipe as demo.py: json.dumps(sort_keys=True,
ensure_ascii=False), explicit '\\n' newlines, no wall-clock values.
"""

from __future__ import annotations

import json
from pathlib import Path


def _json_text(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _jsonl_text(rows: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)


def render_markdown(stream: dict) -> str:
    """Human transcript: one section per tick, each rendered line + its atom type."""
    lines: list[str] = [
        f"# Pneuma Voice — {stream['subject']} (evidence level {stream['evidence_level']})",
        "",
    ]
    by_tick: dict[int, list[tuple[dict, dict]]] = {}
    for atom, rendered in zip(stream["atoms"], stream["rendered"]):
        by_tick.setdefault(atom["tick"], []).append((atom, rendered))
    for tick in sorted(by_tick):
        lines.append(f"## Tick {tick}")
        lines.append("")
        for atom, rendered in by_tick[tick]:
            lines.append(f"- _{atom['type']}_ ({atom['credit_status']}): {rendered['text_deterministic']}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_transcript(stream: dict, out_dir: str | Path) -> None:
    """Write stream.md, stream.jsonl (atoms), and sidecar.json deterministically."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stream.md").write_text(render_markdown(stream), encoding="utf-8", newline="\n")
    (out / "stream.jsonl").write_text(_jsonl_text(stream["atoms"]), encoding="utf-8", newline="\n")
    (out / "sidecar.json").write_text(_json_text(stream["sidecar"]), encoding="utf-8", newline="\n")


__all__ = ["render_markdown", "write_transcript"]
```

- [ ] **Step 4: Implement the CLI**

```python
# src/pneuma_lab/voice/__main__.py
"""CLI: python -m pneuma_lab.voice <fixture> [--out DIR] [--subject reference|baseline]"""

from __future__ import annotations

import argparse
from pathlib import Path

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import load_jsonl

from .stream import voice_run
from .transcript import write_transcript


def _factory(name: str):
    if name == "baseline":
        from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

        return BaselinePsycheSubject
    return ReferencePsyche


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pneuma_lab.voice")
    parser.add_argument("fixture", help="input-frame JSONL timeline")
    parser.add_argument("--out", default=None, help="output dir (default build/voice/<run>)")
    parser.add_argument("--subject", choices=("reference", "baseline"), default="reference")
    args = parser.parse_args(argv)

    stream = voice_run(load_jsonl(args.fixture), subject_factory=_factory(args.subject))
    out_dir = Path(args.out) if args.out else Path("build/voice") / stream["run_id"]
    write_transcript(stream, out_dir)
    print(f"wrote {out_dir}/stream.md (level {stream['evidence_level']}, {len(stream['atoms'])} atoms)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_voice.py -k transcript -q`
Expected: PASS.
Run: `python -m pneuma_lab.voice fixtures/sample_run.jsonl --out build/voice/sample_run`
Expected: prints `wrote build/voice/sample_run/stream.md (level 3, N atoms)`; open the `.md` and confirm it reads as a thought stream.

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/voice/transcript.py src/pneuma_lab/voice/__main__.py tests/test_voice.py
git commit -m "feat(voice): deterministic transcript writer + CLI"
```

---

## Task 9: Isolation guard, docs, status wiring, full suite

**Files:**

- Modify: `tests/test_voice.py` (isolation guard)
- Create: `docs/pneuma-voice-v0.md`
- Modify: `docs/io-contract.md`, `docs/project-status.json`, `CLAUDE.md`

- [ ] **Step 1: Write the isolation guard test**

```python
# add to tests/test_voice.py
import pathlib


def test_voice_package_imports_no_9to5_or_verifier():
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "pneuma_lab" / "voice"
    for py in root.glob("*.py"):
        text = py.read_text(encoding="utf-8").lower()
        assert "9to5" not in text, f"{py.name} references 9to5"
        assert "import verifier" not in text and "from verifier" not in text, py.name
```

- [ ] **Step 2: Run the full voice suite**

Run: `python -m pytest tests/test_voice.py -q`
Expected: PASS (all tasks' tests green).

- [ ] **Step 3: Write the docs**

Create `docs/pneuma-voice-v0.md` covering: the pipeline (`frames → ThoughtAtoms → RenderedThought + sidecar`), the 14-type vocabulary + the observed-vs-credited gate, the conservative-science / anthropomorphic-voice split, the anti-gaming invariant (scorer never reads prose), and the transcript surface + CLI. Add one line to `docs/io-contract.md` noting `thought-stream.schema.json` is an `expressive_view` (derived, non-authoritative). Add a `pneuma_voice_shadow` entry to `docs/project-status.json` (`scope: internal_harness`, no Level claim, `strongest_result` unchanged, new files as evidence_refs). Add one line under a new `voice/` entry in `CLAUDE.md`'s Tree Guide.

- [ ] **Step 4: Run the whole repo suite + status + determinism check**

Run: `python -m pytest tests/ -q`
Expected: PASS (no regressions; the canonical demo is untouched).
Run: `python -m pneuma_lab.status --check`
Expected: OK.
Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 5: Commit**

```bash
git add tests/test_voice.py docs/pneuma-voice-v0.md docs/io-contract.md docs/project-status.json CLAUDE.md
git commit -m "docs(voice): PneumaVoice-v0 Phase A docs, status, isolation guard"
```

---

## Follow-on plans (written after Phase A is green)

- **Phase B — verified voiced skin** (`docs/superpowers/plans/2026-07-1x-pneuma-voice-v0-phase-b.md`):
  `voiced.py` (`VoiceSkin` protocol + `ReferenceVoiceSkin` + pluggable `LLMVoiceSkin`),
  `verify.py` (numeric-coverage vs receipts reusing `evals/grounding` rules, no-new-entity
  whitelist, forbidden-claim filter via `scrub_forbidden`, credit-ceiling), fallback to
  deterministic text on rejection, and the `intervention_result` atom fed from
  `PairedReplayResult.report` (`observed_delta` / `null_delta` / `null_condition`). Tests:
  drift rejection, forbidden rejection, credit-ceiling rejection, and the paired L4 stream.
- **Phase C — HTML mind monitor** (`docs/superpowers/plans/2026-07-1x-pneuma-voice-v0-phase-c.md`):
  `monitor.py` generating a self-contained page from the Phase A/B JSON, plus its
  visual-design pass (frontend-design / ui-ux-pro-max, optional visual companion).

---

## Self-review

**Spec coverage (Phase A slice):** pipeline (Tasks 3–8) ✓; ThoughtAtom/RenderedThought
split (Task 1) ✓; 14-type vocabulary + family/min_level maps (Task 1) ✓; observed-vs-credited
gate (Tasks 3–4) ✓; deterministic credit-aware renderer + interface-convention wording +
forbidden scrub (Task 5) ✓; sidecar (Task 6) ✓; anti-gaming invariant test (Task 7) ✓;
`expressive_view` schema + validator (Task 2) ✓; transcript surface + CLI (Task 8) ✓;
isolation + docs + status (Task 9) ✓. Deferred by design to Phase B/C: `intervention_result`
atom, the voiced LLM skin + verifier, the HTML monitor, and the remaining atom extractors
(`instinct`, `attention`, `prediction_error`, `dissonance`) — each has a named follow-on task
and the identical extractor signature.

**Placeholder scan:** no TBD/TODO; every code step carries complete code.

**Type consistency:** `atoms_for_tick(out, prev, *, tick, evidence_frame, intervention_report=None)`,
`gate(atoms, *, min_intensity=…)`, `render(atom) -> RenderedThought`,
`build_sidecar(*, run_id, subject, mode, evidence_frame, per_tick_atoms)`,
`voice_run(input_frames, *, subject_factory=…) -> dict`, `write_transcript(stream, out_dir)`,
`validate_thought_stream(doc)` — names/signatures are consistent across tasks and match the
verified upstream APIs (`ReplayHarness(...).run(...).tick_outputs/.evidence_frame`,
`frame_id`, `load_jsonl`, `Draft202012Validator`).

**Known implementation checkpoints (resolve during TDD, do not weaken assertions):**
(a) confirm tick-0 of `sample_run.jsonl` really moves affect + resolves a non-suppressed
workspace race (Task 3 Step 4 note); (b) confirm `BaselinePsycheSubject` can consume
`sample_run.jsonl` or swap in its own fixture (Task 7 Step 4 note); (c) the grounded-self-report
text field is `report_text` (not `report`).
