# Pneuma Voice-v0 — Phase B Implementation Plan (verified voiced skin + intervention_result)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the optional, verified natural-language _voiced skin_ over the deterministic thought stream, and the `intervention_result` atom that narrates a tested counterfactual from a paired replay — without ever letting prose touch the evidence scorer.

**Architecture:** A `VoiceSkin` fuses a tick's already-grounded `RenderedThought`s into flowing prose; a `verify_voiced` gate accepts it only if every number/identifier it uses appears in the deterministic source and it makes no forbidden claim and drops no architecture-only hedge — else it falls back to the deterministic text. A `voice_run_paired` drives `PairedReplayRunner`, renders the treated arm, and appends `intervention_result` atoms built from the intervention report. The scorer still never reads any prose.

**Tech stack:** Python stdlib + jsonschema + pytest. The real `LLMVoiceSkin` is a thin adapter around a caller-supplied `generate(prompt)->str`; tests use the deterministic `ReferenceVoiceSkin` (no network, no LLM dependency).

**Prereq:** Phase A merged/committed (package `src/pneuma_lab/voice/` with atoms, extract, gate, render_deterministic, sidecar, stream, transcript).

---

## Task B1: The voiced skin + the verifier

**Files:**

- Create: `src/pneuma_lab/voice/voiced.py`
- Create: `src/pneuma_lab/voice/verify.py`
- Modify: `src/pneuma_lab/voice/__init__.py` (add `"voiced"`, `"verify"` to `__all__`)
- Test: append to `tests/test_voice.py`

- [ ] **Step 1 — failing tests** (append to `tests/test_voice.py`):

```python
from pneuma_lab.voice import voiced as VZ
from pneuma_lab.voice import verify as VF
from pneuma_lab.voice import render_deterministic as R


def _rt(text):
    return {"atom_ids": ["a"], "text_deterministic": text, "text_voiced": None, "voice_status": "deterministic_only"}


def test_reference_skin_is_deterministic_and_fuses():
    rendered = [_rt("Tension climbs to -0.38."), _rt("A verification pressure of 0.42 forms and is held there.")]
    skin = VZ.ReferenceVoiceSkin()
    a = skin.voice_tick([], rendered)
    b = skin.voice_tick([], rendered)
    assert a == b
    assert "-0.38" in a and "0.42" in a  # fused, numbers preserved


def test_verify_accepts_faithful_fusion():
    source = ["Tension climbs to -0.38.", "self_model takes it at salience 1.00."]
    ok, reasons = VF.verify_voiced("Tension climbs to -0.38 while self_model takes it at salience 1.00.", source)
    assert ok, reasons


def test_verify_rejects_invented_number():
    source = ["A verification pressure of 0.42 forms."]
    ok, reasons = VF.verify_voiced("A verification pressure of 0.99 forms.", source)
    assert not ok and any("0.99" in r for r in reasons)


def test_verify_rejects_invented_identifier():
    source = ["self_model takes it at salience 1.00."]
    ok, reasons = VF.verify_voiced("risk_instinct takes it at salience 1.00.", source)
    assert not ok and any("risk_instinct" in r for r in reasons)


def test_verify_rejects_forbidden_claim():
    ok, reasons = VF.verify_voiced("I'm conscious of the tension at 0.42.", ["tension at 0.42."])
    assert not ok and any("forbidden" in r.lower() for r in reasons)


def test_verify_rejects_dropped_hedge():
    source = ["A workspace race resolved (self_model, 1.00) — architecture-only, not promotable evidence."]
    ok, reasons = VF.verify_voiced("A workspace race resolved (self_model, 1.00).", source)
    assert not ok and any("architecture-only" in r for r in reasons)
```

- [ ] **Step 2 — run `python -m pytest tests/test_voice.py -k "skin or verify" -q`; confirm FAIL (no modules).**

- [ ] **Step 3 — create `src/pneuma_lab/voice/verify.py`:**

```python
"""Verify a voiced passage against the deterministic source it must only rephrase.

The skin may make the grounded RenderedThoughts read naturally, but may add no
number, no snake_case/dotted identifier, no forbidden claim, and may not drop an
architecture-only hedge. On any violation the caller falls back to deterministic
text. This gate — not the scorer — is what keeps the vivid voice honest; the
scorer never sees prose at all.
"""

from __future__ import annotations

import re

from .render_deterministic import scrub_forbidden

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# snake_case (has an underscore) or dotted identifiers — the tokens that name
# real faculties/dimensions/motifs and must not be invented.
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[_.][A-Za-z0-9]+)+")
_HEDGE = "architecture-only"


def verify_voiced(text: str, source_texts: list[str]) -> tuple[bool, list[str]]:
    """Return (accepted, reasons). Empty reasons == accepted."""
    source = " ".join(source_texts)
    reasons: list[str] = []

    source_numbers = set(_NUMBER.findall(source))
    for tok in _NUMBER.findall(text):
        if tok not in source_numbers:
            reasons.append(f"invented number: {tok}")

    source_idents = set(_IDENT.findall(source))
    for tok in _IDENT.findall(text):
        if tok not in source_idents:
            reasons.append(f"invented identifier: {tok}")

    _, removed = scrub_forbidden(text)
    if removed:
        reasons.append(f"forbidden claim(s): {removed}")

    if _HEDGE in source and _HEDGE not in text:
        reasons.append("dropped architecture-only hedge")

    return (not reasons, reasons)


__all__ = ["verify_voiced"]
```

- [ ] **Step 4 — create `src/pneuma_lab/voice/voiced.py`:**

```python
"""Optional natural-language skin over the deterministic thought stream.

A ``VoiceSkin`` receives a tick's atoms + their deterministic RenderedThoughts
and returns one flowing passage. It sees ONLY atoms + rendered text — never raw
frames. ``ReferenceVoiceSkin`` is the deterministic, network-free stand-in used
in tests; ``LLMVoiceSkin`` is a thin adapter around a caller-supplied generate()
callable (the real "voice"). Every skin's output is checked by ``verify_voiced``
before it is accepted; on rejection the caller keeps the deterministic text.
"""

from __future__ import annotations

from typing import Callable, Protocol


class VoiceSkin(Protocol):
    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        """Fuse a tick's grounded thoughts into one passage (facts only)."""
        ...


class ReferenceVoiceSkin:
    """Deterministic fusion: joins the grounded sentences into one paragraph.

    Introduces no new facts (it only concatenates existing ``text_deterministic``
    strings), so it always passes ``verify_voiced``. This is the reproducible
    default and the honest lower bound on how "alive" the voice can read.
    """

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        return " ".join(r["text_deterministic"].strip() for r in rendered).strip()


class LLMVoiceSkin:
    """Thin adapter around a caller-supplied ``generate(prompt) -> str``.

    The real, top-notch voice. It is given ONLY the atoms + deterministic
    RenderedThoughts (never raw frames), and its output is verified before use.
    Not exercised in the test suite (no network); wire a real model in via the
    ``generate`` callable.
    """

    _SYSTEM = (
        "Rephrase these grounded thoughts into one vivid, first-person passage. "
        "First-person is an interface convention, not an ontological claim. Use "
        "ONLY the facts, numbers, and names present below. Add no number, faculty, "
        "or claim not given. Never claim to feel, to be aware/conscious/sentient, "
        "to suffer, or to be a moral patient. Keep every architecture-only caveat."
    )

    def __init__(self, generate: Callable[[str], str]):
        self._generate = generate

    def voice_tick(self, atoms: list[dict], rendered: list[dict]) -> str:
        body = "\n".join(f"- {r['text_deterministic']}" for r in rendered)
        return self._generate(f"{self._SYSTEM}\n\n{body}").strip()


__all__ = ["VoiceSkin", "ReferenceVoiceSkin", "LLMVoiceSkin"]
```

- [ ] **Step 5 — add `"voiced"` and `"verify"` to `__all__` in `src/pneuma_lab/voice/__init__.py`** (keep the list otherwise unchanged).

- [ ] **Step 6 — run `python -m pytest tests/test_voice.py -k "skin or verify" -q` → PASS. Then `python -m pytest tests/test_voice.py -q` → all pass.**

- [ ] **Step 7 — commit:**

```bash
git add src/pneuma_lab/voice/voiced.py src/pneuma_lab/voice/verify.py src/pneuma_lab/voice/__init__.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): verified voiced skin (ReferenceVoiceSkin + LLM adapter + verifier)
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task B2: intervention_result atom + paired stream + skin wiring

**Files:**

- Modify: `src/pneuma_lab/voice/extract.py` (add `intervention_result_atoms`)
- Modify: `src/pneuma_lab/voice/render_deterministic.py` (add `_intervention_result` renderer)
- Modify: `src/pneuma_lab/voice/stream.py` (add `voice_run_paired`; thread `skin` through both run functions)
- Test: append to `tests/test_voice.py`

- [ ] **Step 1 — failing tests** (append). First discover a passing intervention fixture and the restore/null fixture: run `ls fixtures/interventions/` and pick one non-restore scenario (e.g. `ablate_scar_graph.jsonl` or `clamp_tension.jsonl`) whose paired report has a passing test, and the `restore` null fixture. Use those names below (replace `<PASS_FIXTURE>` / `<RESTORE_FIXTURE>`):

```python
from pneuma_lab.voice import stream as ST

_IV_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"


def test_paired_stream_has_intervention_result_and_is_l4_capable():
    s = ST.voice_run_paired(load_jsonl(_IV_DIR / "<PASS_FIXTURE>"))
    kinds = {a["type"] for a in s["atoms"]}
    assert "intervention_result" in kinds
    ir = next(a for a in s["atoms"] if a["type"] == "intervention_result")
    paths = {r["field_path"] for r in ir["receipts"]}
    assert "intervention.observed_delta" in paths and "intervention.experiment_id" in paths


def test_restore_null_has_no_intervention_result():
    s = ST.voice_run_paired(load_jsonl(_IV_DIR / "<RESTORE_FIXTURE>"))
    assert "intervention_result" not in {a["type"] for a in s["atoms"]}


def test_skin_cannot_inflate_the_level():
    frames = load_jsonl(_FIXTURE)
    off = ST.voice_run(frames)
    on = ST.voice_run(frames, skin=VZ.ReferenceVoiceSkin())
    import json
    assert json.dumps(off["evidence_frame"], sort_keys=True) == json.dumps(on["evidence_frame"], sort_keys=True)
    assert off["evidence_level"] == on["evidence_level"]
    # With the skin on, rendered thoughts carry voiced text and a voiced status.
    assert any(r["voice_status"] == "voiced" for r in on["rendered"])


def test_voiced_falls_back_on_rejected_drift():
    class DriftSkin:
        def voice_tick(self, atoms, rendered):
            return "verification pressure of 0.99999 forms"  # invented number
    frames = load_jsonl(_FIXTURE)
    on = ST.voice_run(frames, skin=DriftSkin())
    # Every rendered thought either stayed deterministic or was voiced-and-verified;
    # none contains the injected 0.99999.
    assert all("0.99999" not in (r.get("text_voiced") or "") for r in on["rendered"])
    assert any(r["voice_status"] == "voiced_rejected_fell_back" for r in on["rendered"])
```

- [ ] **Step 2 — run the new tests; confirm FAIL.**

- [ ] **Step 3 — add `intervention_result_atoms` to `extract.py`** (near the bottom, before `atoms_for_tick`; import nothing new):

```python
def intervention_result_atoms(
    report: dict,
    *,
    run_id: str,
    tick: int,
    timestamp: str,
    evidence_frame: dict,
    start_ordinal: int,
) -> list[ThoughtAtom]:
    """Run-level atoms for each tested counterfactual (from a paired report).

    Emitted only for tests that genuinely perturbed and passed; the restore/null
    scenario produces none. Attached to the final tick by the paired stream.
    """
    atoms: list[ThoughtAtom] = []
    ordinal = start_ordinal
    for test in report.get("tests", []) or []:
        if not test.get("passed") or abs(float(test.get("observed_delta", 0.0))) <= _EPS:
            continue
        receipts = [
            _receipt("intervention.experiment_id", test.get("experiment_id")),
            _receipt("intervention.target_signal", test.get("target_signal")),
            _receipt("intervention.control_value", test.get("control_value")),
            _receipt("intervention.treated_value", test.get("treated_value")),
            _receipt("intervention.observed_delta", test.get("observed_delta")),
            _receipt("intervention.null_delta", test.get("null_delta")),
        ]
        atoms.append(
            ThoughtAtom(
                atom_id=frame_id(run_id, tick, "atom", ordinal),
                type="intervention_result",
                run_id=run_id,
                tick=tick,
                timestamp=timestamp,
                receipts=receipts,
                intensity=clamp01(abs(float(test.get("observed_delta", 0.0)))),
                crediting_family=ATOM_FAMILY["intervention_result"],
                credit_status=credit_status_for("intervention_result", evidence_frame),
                min_level=MIN_LEVEL["intervention_result"],
                changed_from_prev=True,
            )
        )
        ordinal += 1
    return atoms
```

Also update `atoms_for_tick`'s `__all__` line at the bottom of `extract.py` to `__all__ = ["atoms_for_tick", "intervention_result_atoms"]`.

- [ ] **Step 4 — add the `_intervention_result` renderer to `render_deterministic.py`** and register it in `_RENDERERS`:

```python
def _intervention_result(atom: ThoughtAtom) -> str:
    exp = receipt_value(atom, "intervention.experiment_id", "an intervention")
    delta = receipt_value(atom, "intervention.observed_delta", 0.0)
    null_delta = receipt_value(atom, "intervention.null_delta", 0.0)
    ctrl = receipt_value(atom, "intervention.control_value", 0.0)
    treated = receipt_value(atom, "intervention.treated_value", 0.0)
    return (
        f"The counterfactual was tested ({exp}): the target signal moved "
        f"{_num(ctrl, '.2f')} → {_num(treated, '.2f')} (delta {_num(delta, '.2f')}); "
        f"under the null it moved {_num(null_delta, '.2f')}. This part of the state is "
        "load-bearing, not decoration."
    )
```

Add `"intervention_result": _intervention_result,` to the `_RENDERERS` dict.

- [ ] **Step 5 — rework `stream.py`** to (a) thread an optional `skin`, and (b) add `voice_run_paired`. Replace the file body with:

```python
"""voice_run / voice_run_paired — drive a subject and render its thought stream.

The evidence frame produced by the harness/runner is used verbatim as the level
source and echoed into the result; the voice never re-scores and never mutates
it. An optional VoiceSkin makes each tick read naturally, but is accepted only if
verify_voiced passes — otherwise the deterministic text stands.
"""

from __future__ import annotations

from dataclasses import asdict

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness

from . import extract as _extract
from . import gate as _gate
from . import render_deterministic as _render
from . import sidecar as _sidecar
from .atoms import ThoughtAtom
from .verify import verify_voiced


def _render_tick(atoms, skin):
    """Render a tick's gated atoms; apply + verify the skin when present."""
    rendered = [_render.render(a) for a in atoms]
    dicts = [asdict(r) for r in rendered]
    if skin is not None and rendered:
        source = [r.text_deterministic for r in rendered]
        voiced = skin.voice_tick([asdict(a) for a in atoms], dicts)
        ok, _reasons = verify_voiced(voiced, source)
        if ok:
            for d in dicts:
                d["text_voiced"] = voiced
                d["voice_status"] = "voiced"
        else:
            for d in dicts:
                d["voice_status"] = "voiced_rejected_fell_back"
    return dicts


def _assemble(*, result, evidence_frame, subject_name, skin, min_intensity, extra_last_tick_atoms=None):
    run_id = evidence_frame.get("run_id") or (
        result.tick_outputs[0].psyche_state.get("run_id") if result.tick_outputs else "run"
    )
    per_tick_atoms: list[list[ThoughtAtom]] = []
    all_atoms: list[dict] = []
    all_rendered: list[dict] = []
    last = len(result.tick_outputs) - 1
    for i, out in enumerate(result.tick_outputs):
        prev = result.tick_outputs[i - 1] if i else None
        atoms = _extract.atoms_for_tick(out, prev, tick=i, evidence_frame=evidence_frame)
        if i == last and extra_last_tick_atoms:
            atoms = atoms + extra_last_tick_atoms
        atoms = _gate.gate(atoms, min_intensity=min_intensity)
        per_tick_atoms.append(atoms)
        for d in _render_tick(atoms, skin):
            all_rendered.append(d)
        for atom in atoms:
            all_atoms.append(asdict(atom))
    mode = "voiced" if skin is not None else "deterministic"
    sidecar = _sidecar.build_sidecar(
        run_id=run_id, subject=subject_name, mode=mode,
        evidence_frame=evidence_frame, per_tick_atoms=per_tick_atoms,
    )
    return {
        "manifest_kind": "thought_stream",
        "schema_version": "0.1.0",
        "run_id": run_id,
        "subject": subject_name,
        "mode": mode,
        "evidence_level": int(evidence_frame.get("evidence_level", 0)),
        "atoms": all_atoms,
        "rendered": all_rendered,
        "sidecar": sidecar,
        "evidence_frame": evidence_frame,
    }


def voice_run(input_frames, *, subject_factory=ReferencePsyche, validate=True, min_intensity=1e-6, skin=None):
    """Deterministic (or voiced) thought stream for a passive replay run."""
    subject = subject_factory()
    result = ReplayHarness(subject, validate=validate).run(input_frames)
    return _assemble(
        result=result, evidence_frame=result.evidence_frame,
        subject_name=type(subject).__name__, skin=skin, min_intensity=min_intensity,
    )


def voice_run_paired(input_frames, *, subject_factory=ReferencePsyche, min_intensity=1e-6, skin=None):
    """Thought stream for a paired replay: renders the treated arm and appends
    intervention_result atoms (the tested counterfactuals) to the final tick."""
    from pneuma_lab.interventions.runner import PairedReplayRunner

    paired = PairedReplayRunner(psyche_factory=subject_factory).run(input_frames)
    evidence_frame = paired.evidence_frame
    treated = paired.treated
    run_id = evidence_frame.get("run_id") or (
        treated.tick_outputs[0].psyche_state.get("run_id") if treated.tick_outputs else "run"
    )
    timestamp = treated.tick_outputs[-1].psyche_state.get("timestamp", "") if treated.tick_outputs else ""
    extra = _extract.intervention_result_atoms(
        paired.report, run_id=run_id, tick=max(0, len(treated.tick_outputs) - 1),
        timestamp=timestamp, evidence_frame=evidence_frame, start_ordinal=1000,
    )
    return _assemble(
        result=treated, evidence_frame=evidence_frame,
        subject_name=type(subject_factory()).__name__, skin=skin,
        min_intensity=min_intensity, extra_last_tick_atoms=extra,
    )


__all__ = ["voice_run", "voice_run_paired"]
```

- [ ] **Step 6 — run `python -m pytest tests/test_voice.py -q`.** Fix the `<PASS_FIXTURE>`/`<RESTORE_FIXTURE>` names in the tests to real files under `fixtures/interventions/` (discovered in Step 1). If the chosen PASS fixture's report has no passing genuinely-perturbing test, pick another (inspect via a quick `python -c` printing `PairedReplayRunner().run(load_jsonl(...)).report["summary"]`). Do NOT weaken assertions. Confirm all pass + `python -m pytest tests/ -q` (no regressions) + `python -m pneuma_lab.demo` still exits 0.

- [ ] **Step 7 — commit:**

```bash
git add src/pneuma_lab/voice/extract.py src/pneuma_lab/voice/render_deterministic.py src/pneuma_lab/voice/stream.py tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): intervention_result atom + paired stream + verified skin wiring
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task B3: CLI flags + docs

**Files:**

- Modify: `src/pneuma_lab/voice/__main__.py` (add `--paired` and `--skin {none,reference}`)
- Modify: `docs/pneuma-voice-v0.md` (document Phase B)
- Test: append a CLI smoke assertion to `tests/test_voice.py`

- [ ] **Step 1 — failing test** (append):

```python
def test_cli_paired_and_skin(tmp_path, capsys):
    from pneuma_lab.voice.__main__ import main
    rc = main([str(_IV_DIR / "<PASS_FIXTURE>"), "--paired", "--skin", "reference", "--out", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "stream.md").exists()
```

- [ ] **Step 2 — update `__main__.py`:** add `parser.add_argument("--paired", action="store_true")` and `parser.add_argument("--skin", choices=("none", "reference"), default="none")`. Build the skin: `skin = voiced.ReferenceVoiceSkin() if args.skin == "reference" else None` (import `from . import voiced`). Call `voice_run_paired(...)` when `--paired` else `voice_run(...)`, passing `skin=skin` and `subject_factory=_factory(args.subject)`. Keep the print + return 0.

- [ ] **Step 3 — run `python -m pytest tests/test_voice.py -k cli -q` → PASS; full suite green.**

- [ ] **Step 4 — docs:** add a short "Phase B — verified voiced skin" section to `docs/pneuma-voice-v0.md` covering: the `VoiceSkin` protocol + `ReferenceVoiceSkin`/`LLMVoiceSkin`, the `verify_voiced` gate (numbers/identifiers must be in the deterministic source, no forbidden claim, hedge preserved) + deterministic fallback, the `intervention_result` atom + `voice_run_paired`, and the reaffirmed invariant (skin cannot inflate the level — tested). Update `docs/project-status.json` `pneuma_voice_shadow` evidence_refs to include `voiced.py`/`verify.py` (keep no-Level-claim).

- [ ] **Step 5 — commit:**

```bash
git add src/pneuma_lab/voice/__main__.py docs/pneuma-voice-v0.md docs/project-status.json tests/test_voice.py
git commit -m "$(cat <<'EOF'
feat(voice): CLI --paired/--skin + Phase B docs
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- Spec coverage: voiced skin (B1), verifier (B1), intervention_result atom (B2), paired stream (B2), skin-can't-inflate test (B2), CLI + docs (B3). ✓
- Anti-gaming preserved: `_render_tick`/`_assemble` read `evidence_frame` only; the scorer is never called from voice; `test_skin_cannot_inflate_the_level` asserts byte-identical evidence with skin on/off.
- Determinism: `ReferenceVoiceSkin` is pure; `verify_voiced` is pure; paired stream ordering is fixed. The LLM adapter is non-deterministic by nature and is NOT in the deterministic byte-guarantee (only the deterministic layer is).
- Type consistency: `voice_run(..., skin=None)`, `voice_run_paired(..., skin=None)`, `verify_voiced(text, source_texts) -> (bool, list)`, `ReferenceVoiceSkin().voice_tick(atoms, rendered) -> str`, `intervention_result_atoms(report, *, run_id, tick, timestamp, evidence_frame, start_ordinal)`.
- Checkpoint: fixture names under `fixtures/interventions/` must be resolved to real files in B2/B3 (discover via `ls`); pick a genuinely-passing scenario for PASS and the `restore` scenario for RESTORE.
