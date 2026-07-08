# SWE-Gym-Lite → PneumaTrace Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic adapter that turns each SWE-Gym-Lite task row into a durable, validated `PneumaTrace` JSONL artifact (envelope wrapping existing input frames), with quarantine/skip policy and a hermetic golden test fixture.

**Architecture:** A new non-cognitive envelope schema (`schemas/pneuma-trace.schema.json`) plus a dataset-agnostic builder (`adapters/envelope.py`: canonical JSON, deterministic ids, content hash, envelope validation) and a dataset-specific adapter (`adapters/swe_gym_lite.py`: parquet → world/governance frames + labels/oracle/supervision → 4 output files). All output is byte-deterministic; tests are hermetic (no `/c/pneuma-data`, no network).

**Tech Stack:** Python 3.11, `pyarrow` (parquet read), `jsonschema` (Draft 2020-12), `hashlib.blake2b`/`sha256`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-07-07-swe-gym-lite-pneuma-trace-adapter-design.md`

---

## File Structure

- Create `schemas/pneuma-trace.schema.json` — the envelope contract (`x-pneuma-schema-kind: "envelope"`).
- Modify `src/pneuma_lab/schemas/__init__.py` — add `ENVELOPE_SCHEMA_FILES` bucket; fold into `ALL_SCHEMA_FILES`.
- Modify `tests/test_schema_loads.py` — envelope count + coverage.
- Create `src/pneuma_lab/adapters/envelope.py` — dataset-agnostic: canonical JSON, ids, content hash, envelope validation.
- Create `tests/test_pneuma_trace_envelope.py` — envelope unit tests.
- Create `src/pneuma_lab/adapters/swe_gym_lite.py` — dataset-specific: frame builders, `build_trace`, `run`, `read_lite_parquet`.
- Create `tests/test_swe_gym_lite_adapter.py` — frame construction, run() behavior, quarantine/skip, oracle coverage, determinism.
- Add a `main()` + `if __name__ == "__main__"` CLI to `src/pneuma_lab/adapters/swe_gym_lite.py` (invoked `python -m pneuma_lab.adapters.swe_gym_lite`) — includes `--emit-fixture` drift check.
- Create `fixtures/adapters/swe_gym_lite/` — `input_rows.jsonl`, `golden/*`, `LICENSE_PROVENANCE.md`.
- Create `tests/test_swe_gym_lite_golden.py` — hermetic golden byte-match + fixture-drift.

Deterministic conventions used everywhere:

- Canonical JSON: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, UTF-8, one object/line + `\n`.
- Identity hash: `blake2b(digest_size=16)` over `"swe-gym\x00" + instance_id + "\x00" + hf_revision` → `trace_id="ptrace:"+h`, `run_id="run:"+h`. (`hf_revision` differs between Lite and full SWE-Gym, so ids never collide across variants.)
- Content hash: `blake2b(digest_size=32)` over canonical JSON of the trace with `build.content_hash=""` and no `validation` block.

---

## Task 1: Envelope schema + registration

**Files:**

- Create: `schemas/pneuma-trace.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Test: `tests/test_schema_loads.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_schema_loads.py`:

```python
def test_envelope_bucket_registered() -> None:
    assert pls.ENVELOPE_SCHEMA_FILES == ("pneuma-trace.schema.json",)
    assert "pneuma-trace.schema.json" in pls.ALL_SCHEMA_FILES


def test_envelope_schema_shape() -> None:
    schema = pls.load_schema("pneuma-trace.schema.json")
    assert schema["x-pneuma-schema-kind"] == "envelope"
    assert schema["type"] == "object"
    for key in ("trace_id", "run_id", "provenance", "build", "frames"):
        assert key in schema["properties"], f"missing property {key}"
```

Also update the existing count test in the same file so envelopes are counted:

```python
# replace the body of test_expected_counts with:
def test_expected_counts() -> None:
    assert len(pls.INPUT_SCHEMA_FILES) == EXPECTED_INPUT_COUNT
    assert len(pls.OUTPUT_SCHEMA_FILES) == EXPECTED_OUTPUT_COUNT
    assert len(pls.ENVELOPE_SCHEMA_FILES) == 1
    assert len(pls.ALL_SCHEMA_FILES) == EXPECTED_INPUT_COUNT + EXPECTED_OUTPUT_COUNT + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_schema_loads.py -q`
Expected: FAIL (`AttributeError: module ... has no attribute 'ENVELOPE_SCHEMA_FILES'`).

- [ ] **Step 3: Create the envelope schema** `schemas/pneuma-trace.schema.json` (4-space indent):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pneuma-lab.local/schemas/pneuma-trace.schema.json",
  "title": "PneumaTrace",
  "description": "A durable, deterministic envelope wrapping existing validated Pneuma input frames plus dataset provenance, privacy status, labels, test oracle, and reference supervision. NON-cognitive: it introduces no new interior/cognition semantics. Envelope contract v0.1.",
  "type": "object",
  "x-pneuma-schema-kind": "envelope",
  "x-pneuma-version": "0.1.0",
  "required": [
    "schema_version",
    "trace_id",
    "run_id",
    "adapter",
    "provenance",
    "build",
    "privacy",
    "labels",
    "oracle",
    "reference_supervision",
    "frames"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "0.1.0" },
    "trace_id": { "type": "string", "pattern": "^ptrace:[0-9a-f]+$" },
    "run_id": { "type": "string", "pattern": "^run:[0-9a-f]+$" },
    "adapter": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": { "type": "string" },
        "version": { "type": "string" }
      },
      "additionalProperties": true
    },
    "provenance": {
      "type": "object",
      "required": [
        "dataset",
        "source_id",
        "hf_repo",
        "hf_revision",
        "source_file",
        "source_row"
      ],
      "properties": {
        "dataset": { "type": "string" },
        "dataset_variant": { "type": "string" },
        "source_id": { "type": "string" },
        "hf_repo": { "type": "string" },
        "hf_revision": { "type": "string" },
        "source_file": { "type": "string" },
        "source_row": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": true
    },
    "build": {
      "type": "object",
      "required": [
        "deterministic",
        "content_hash",
        "generated_from",
        "frame_sources"
      ],
      "properties": {
        "deterministic": { "type": "boolean", "const": true },
        "content_hash": { "type": "string" },
        "generated_from": { "type": "array", "items": { "type": "string" } },
        "frame_sources": {
          "type": "object",
          "additionalProperties": { "type": "string" }
        }
      },
      "additionalProperties": true
    },
    "privacy": {
      "type": "object",
      "required": ["status", "pii_scanned", "redactions"],
      "properties": {
        "status": { "type": "string" },
        "pii_scanned": { "type": "boolean" },
        "redactions": { "type": "array" }
      },
      "additionalProperties": true
    },
    "validation": {
      "type": "object",
      "properties": {
        "schema": { "type": "string" },
        "status": { "type": "string" }
      },
      "additionalProperties": true
    },
    "labels": { "type": "object" },
    "oracle": {
      "type": "object",
      "required": ["kind"],
      "properties": {
        "kind": { "type": "string" },
        "fail_to_pass": { "type": "array", "items": { "type": "string" } },
        "pass_to_pass": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": true
    },
    "reference_supervision": { "type": "object" },
    "frames": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["frame_kind"],
        "properties": { "frame_kind": { "type": "string" } },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true
}
```

- [ ] **Step 4: Register the bucket** — edit `src/pneuma_lab/schemas/__init__.py`. After the `OUTPUT_SCHEMA_FILES = (...)` block add:

```python
ENVELOPE_SCHEMA_FILES = ("pneuma-trace.schema.json",)
```

Change `ALL_SCHEMA_FILES`:

```python
ALL_SCHEMA_FILES = INPUT_SCHEMA_FILES + OUTPUT_SCHEMA_FILES + ENVELOPE_SCHEMA_FILES
```

Add `"ENVELOPE_SCHEMA_FILES"` to the `__all__` list.

- [ ] **Step 5: Run tests to verify pass**

Run: `python -m pytest tests/test_schema_loads.py -q`
Expected: PASS. Then `python -c "import json,glob; [json.load(open(f)) for f in glob.glob('schemas/*.json')]; print('all schemas parse')"` → prints `all schemas parse`.

- [ ] **Step 6: Commit**

```bash
git add schemas/pneuma-trace.schema.json src/pneuma_lab/schemas/__init__.py tests/test_schema_loads.py
git commit -m "feat(adapters): add PneumaTrace envelope schema + envelopes bucket"
```

---

## Task 2: Canonical JSON + deterministic ids + content hash

**Files:**

- Create: `src/pneuma_lab/adapters/envelope.py`
- Test: `tests/test_pneuma_trace_envelope.py`

- [ ] **Step 1: Write the failing test** `tests/test_pneuma_trace_envelope.py`:

```python
from __future__ import annotations

import copy

from pneuma_lab.adapters import envelope as env


def test_canonical_json_is_sorted_and_compact():
    s = env.canonical_json({"b": 1, "a": 2})
    assert s == '{"a":2,"b":1}'


def test_identity_hash_is_deterministic_and_prefixed():
    ids1 = env.derive_ids("swe-gym", "getmoto__moto-5752", "f70b1a29")
    ids2 = env.derive_ids("swe-gym", "getmoto__moto-5752", "f70b1a29")
    assert ids1 == ids2
    assert ids1["trace_id"].startswith("ptrace:")
    assert ids1["run_id"].startswith("run:")
    assert ids1["trace_id"][len("ptrace:"):] == ids1["run_id"][len("run:"):]


def test_identity_hash_changes_with_revision():
    a = env.derive_ids("swe-gym", "x", "rev-a")
    b = env.derive_ids("swe-gym", "x", "rev-b")
    assert a["trace_id"] != b["trace_id"]


def test_content_hash_excludes_self_and_validation():
    trace = {
        "build": {"content_hash": "SHOULD_BE_IGNORED"},
        "validation": {"status": "valid"},
        "labels": {"x": 1},
    }
    h1 = env.content_hash(trace)
    trace2 = copy.deepcopy(trace)
    trace2["build"]["content_hash"] = "DIFFERENT"
    trace2["validation"] = {"status": "invalid"}
    assert env.content_hash(trace2) == h1  # blanked/removed before hashing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pneuma_trace_envelope.py -q`
Expected: FAIL (`ModuleNotFoundError: pneuma_lab.adapters.envelope`).

- [ ] **Step 3: Implement** `src/pneuma_lab/adapters/envelope.py`:

```python
"""Dataset-agnostic PneumaTrace envelope helpers.

Deterministic by construction: canonical JSON, identity ids, and a content hash
that excludes self-referential fields. No wall-clock, no randomness.
"""

from __future__ import annotations

import copy
import hashlib
import json

SCHEMA_VERSION = "0.1.0"
ENVELOPE_SCHEMA_FILE = "pneuma-trace.schema.json"


def canonical_json(obj) -> str:
    """Byte-stable JSON: sorted keys, compact separators, UTF-8, no ASCII escaping."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _identity_hash(dataset: str, instance_id: str, hf_revision: str) -> str:
    payload = f"{dataset}\x00{instance_id}\x00{hf_revision}".encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def derive_ids(dataset: str, instance_id: str, hf_revision: str) -> dict[str, str]:
    """Sibling ids from one identity hash: trace (artifact) + run (execution)."""
    h = _identity_hash(dataset, instance_id, hf_revision)
    return {"trace_id": f"ptrace:{h}", "run_id": f"run:{h}"}


def content_hash(trace: dict) -> str:
    """Integrity hash over the trace with build.content_hash blanked and no validation."""
    clone = copy.deepcopy(trace)
    if isinstance(clone.get("build"), dict):
        clone["build"]["content_hash"] = ""
    clone.pop("validation", None)
    return hashlib.blake2b(canonical_json(clone).encode("utf-8"), digest_size=32).hexdigest()


__all__ = [
    "SCHEMA_VERSION",
    "ENVELOPE_SCHEMA_FILE",
    "canonical_json",
    "derive_ids",
    "content_hash",
]
```

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_pneuma_trace_envelope.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/adapters/envelope.py tests/test_pneuma_trace_envelope.py
git commit -m "feat(adapters): deterministic canonical JSON, ids, content hash"
```

---

## Task 3: Envelope validation

**Files:**

- Modify: `src/pneuma_lab/adapters/envelope.py`
- Test: `tests/test_pneuma_trace_envelope.py`

- [ ] **Step 1: Write the failing test** — append:

```python
def _minimal_valid_trace():
    return {
        "schema_version": "0.1.0",
        "trace_id": "ptrace:abc123",
        "run_id": "run:abc123",
        "adapter": {"name": "swe-gym", "version": "0.1.0"},
        "provenance": {"dataset": "swe-gym", "source_id": "x", "hf_repo": "r",
                        "hf_revision": "rev", "source_file": "f", "source_row": 0},
        "build": {"deterministic": True, "content_hash": "h",
                   "generated_from": ["dataset"], "frame_sources": {"world-frame": "dataset-derived"}},
        "privacy": {"status": "clean", "pii_scanned": False, "redactions": []},
        "labels": {},
        "oracle": {"kind": "test-based"},
        "reference_supervision": {},
        "frames": [{"frame_kind": "world"}],
    }


def test_valid_envelope_passes():
    assert env.envelope_errors(_minimal_valid_trace()) == []


def test_malformed_envelope_rejected():
    bad = _minimal_valid_trace()
    del bad["provenance"]
    errs = env.envelope_errors(bad)
    assert errs and any("provenance" in e for e in errs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pneuma_trace_envelope.py -q`
Expected: FAIL (`AttributeError: ... 'envelope_errors'`).

- [ ] **Step 3: Implement** — add to `envelope.py` (imports at top: `from functools import lru_cache`, `from jsonschema import Draft202012Validator`, `from pneuma_lab.schemas import load_schema`):

```python
@lru_cache(maxsize=1)
def _envelope_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema(ENVELOPE_SCHEMA_FILE))


def envelope_errors(trace: dict) -> list[str]:
    """Human-readable envelope-schema errors (empty list = valid)."""
    if not isinstance(trace, dict):
        return [f"trace is not an object: {type(trace).__name__}"]
    out: list[str] = []
    for err in sorted(_envelope_validator().iter_errors(trace), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        out.append(f"{loc}: {err.message}")
    return out
```

Add `"envelope_errors"` to `__all__`.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_pneuma_trace_envelope.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/adapters/envelope.py tests/test_pneuma_trace_envelope.py
git commit -m "feat(adapters): envelope schema validation helper"
```

---

## Task 4: SWE-Gym-Lite frame builders

**Files:**

- Create: `src/pneuma_lab/adapters/swe_gym_lite.py`
- Test: `tests/test_swe_gym_lite_adapter.py`

- [ ] **Step 1: Write the failing test** `tests/test_swe_gym_lite_adapter.py`:

```python
from __future__ import annotations

import pytest

from pneuma_lab.adapters import swe_gym_lite as swe
from pneuma_lab.schemas import validate


SAMPLE_ROW = {
    "instance_id": "getmoto__moto-5752",
    "repo": "getmoto/moto",
    "base_commit": "b2300f1eae1323e3e8bc45f97e530ce129dff12e",
    "version": "4.0",
    "created_at": "2022-12-10 20:23:01",
    "problem_statement": "describe_parameters depends on filter order",
    "patch": "diff --git a/moto/ssm/models.py b/moto/ssm/models.py\n@@ -1 +1 @@\n-x\n+y\n",
    "test_patch": "diff --git a/tests/x.py b/tests/x.py\n@@ -1 +1 @@\n-a\n+b\n",
    "hints_text": "Here's the culprit",
    "FAIL_TO_PASS": ["tests/x.py::test_a"],
    "PASS_TO_PASS": ["tests/x.py::test_b"],
}


def test_normalize_created_at():
    assert swe.normalize_created_at("2022-12-10 20:23:01") == "2022-12-10T20:23:01+00:00"


def test_as_list_handles_json_string_and_list():
    assert swe.as_list('["a","b"]') == ["a", "b"]
    assert swe.as_list(["a", "b"]) == ["a", "b"]
    assert swe.as_list(None) == []


def test_world_frame_validates():
    f = swe.build_world_frame(SAMPLE_ROW, run_id="run:abc", timestamp="2022-12-10T20:23:01+00:00")
    assert f["frame_kind"] == "world"
    assert validate.iter_errors(f) == []
    assert f["repo_state"]["head_sha"] == SAMPLE_ROW["base_commit"]
    assert f["test_state"] == {"ran": False, "not_yet_run": True}


def test_governance_frame_validates():
    f = swe.build_governance_frame(run_id="run:abc", timestamp="2022-12-10T20:23:01+00:00")
    assert f["frame_kind"] == "governance"
    assert f["verifier_isolation"] is True
    assert f["kill_switch_state"] == "off"
    assert validate.iter_errors(f) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: FAIL (`ModuleNotFoundError: pneuma_lab.adapters.swe_gym_lite`).

- [ ] **Step 3: Implement the builders** — create `src/pneuma_lab/adapters/swe_gym_lite.py`:

```python
"""SWE-Gym-Lite task rows -> PneumaTrace artifacts (task-only, honest, deterministic).

Emits exactly two frames per trace: a real dataset-derived world-frame and a
minimal synthetic governance-frame. Gold patch / tests / hints are supervision in
the envelope, never psyche-input frames. No agent-trace/memory frames (no agent ran).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

FRAME_SCHEMA_VERSION = "0.1.0"


def normalize_created_at(raw: str) -> str:
    """'2022-12-10 20:23:01' -> ISO-8601 UTC. Raises ValueError if unparseable."""
    dt = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def as_list(value) -> list[str]:
    """SWE-Bench test lists arrive as a real list or a JSON-encoded string."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(v) for v in parsed] if isinstance(parsed, list) else []
    return []


def build_world_frame(row: dict, run_id: str, timestamp: str) -> dict:
    """Real exteroception at t0. Tests are NOT run here; the oracle lives in labels."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "world",
        "timestamp": timestamp,
        "run_id": run_id,
        "phase": "preamble",
        "objective": row.get("problem_statement", ""),
        "repo_state": {
            "head_sha": row["base_commit"],
            "repo": row.get("repo", ""),
        },
        "test_state": {"ran": False, "not_yet_run": True},
    }


def build_governance_frame(run_id: str, timestamp: str) -> dict:
    """Minimal synthetic contract frame. kill_switch 'off' = psyche is a no-op (data)."""
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "frame_kind": "governance",
        "timestamp": timestamp,
        "run_id": run_id,
        "verifier_isolation": True,
        "kill_switch_state": "off",
    }
```

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: PASS (4 passed). If a frame fails validation, print `validate.iter_errors(f)` and add the missing required field (check `schemas/world-frame.schema.json` / `governance-frame.schema.json` `required`).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/adapters/swe_gym_lite.py tests/test_swe_gym_lite_adapter.py
git commit -m "feat(adapters): SWE-Gym-Lite world/governance frame builders"
```

---

## Task 5: Row → trace builder (+ skip policy)

**Files:**

- Modify: `src/pneuma_lab/adapters/swe_gym_lite.py`
- Test: `tests/test_swe_gym_lite_adapter.py`

- [ ] **Step 1: Write the failing test** — append:

```python
from pneuma_lab.adapters import envelope as env


def test_build_trace_structure_and_validation():
    trace = swe.build_trace(SAMPLE_ROW, hf_revision="f70b1a29",
                            source_file="raw/.../train.parquet", source_row=0)
    assert trace["trace_id"].startswith("ptrace:")
    assert trace["run_id"].startswith("run:")
    assert trace["labels"]["has_patch"] is True
    assert trace["labels"]["benchmark"] == "swe-gym-lite"
    assert trace["oracle"]["fail_to_pass"] == ["tests/x.py::test_a"]
    assert trace["reference_supervision"]["gold_patch"] == SAMPLE_ROW["patch"]
    assert trace["reference_supervision"]["hints_text"] == "Here's the culprit"
    assert trace["build"]["frame_sources"]["governance-frame"] == "synthetic-contract-minimum"
    assert [f["frame_kind"] for f in trace["frames"]] == ["world", "governance"]
    # content hash recomputes to the stored value
    assert env.content_hash(trace) == trace["build"]["content_hash"]
    # whole envelope validates
    assert env.envelope_errors(trace) == []
    # each frame validates against its existing schema
    for f in trace["frames"]:
        assert validate.iter_errors(f) == []


def test_build_trace_skips_row_missing_base_commit():
    bad = dict(SAMPLE_ROW)
    del bad["base_commit"]
    with pytest.raises(swe.SkipRow) as ei:
        swe.build_trace(bad, hf_revision="f70b1a29", source_file="f", source_row=1)
    assert "base_commit" in str(ei.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: FAIL (`AttributeError: ... 'SkipRow'` / `'build_trace'`).

- [ ] **Step 3: Implement** — add to `swe_gym_lite.py` (add imports at top: `import hashlib`, `from pneuma_lab.adapters import envelope as env`):

```python
DATASET = "swe-gym"
DATASET_VARIANT = "SWE-Gym-Lite"
BENCHMARK = "swe-gym-lite"
HF_REPO = "SWE-Gym/SWE-Gym-Lite"
ADAPTER = {"name": "swe-gym", "version": "0.1.0"}


class SkipRow(ValueError):
    """Row cannot produce a valid trace (missing/dirty required data)."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_trace(row: dict, hf_revision: str, source_file: str, source_row: int) -> dict:
    """Assemble one PneumaTrace. Raises SkipRow for unbuildable rows."""
    instance_id = row.get("instance_id")
    if not instance_id:
        raise SkipRow("missing instance_id")
    if not row.get("base_commit"):
        raise SkipRow("missing base_commit")
    created_at = row.get("created_at")
    if not created_at:
        raise SkipRow("missing created_at")
    try:
        timestamp = normalize_created_at(created_at)
    except (ValueError, AttributeError) as exc:
        raise SkipRow(f"unparseable created_at: {created_at!r}") from exc

    ids = env.derive_ids(DATASET, instance_id, hf_revision)
    world = build_world_frame(row, ids["run_id"], timestamp)
    governance = build_governance_frame(ids["run_id"], timestamp)

    gold_patch = row.get("patch") or ""
    test_patch = row.get("test_patch") or ""
    hints_text = row.get("hints_text") or ""
    fail_to_pass = as_list(row.get("FAIL_TO_PASS"))
    pass_to_pass = as_list(row.get("PASS_TO_PASS"))

    trace = {
        "schema_version": "0.1.0",
        "trace_id": ids["trace_id"],
        "run_id": ids["run_id"],
        "adapter": dict(ADAPTER),
        "provenance": {
            "dataset": DATASET,
            "dataset_variant": DATASET_VARIANT,
            "source_id": instance_id,
            "hf_repo": HF_REPO,
            "hf_revision": hf_revision,
            "source_file": source_file,
            "source_row": source_row,
        },
        "build": {
            "deterministic": True,
            "content_hash": "",
            "generated_from": ["dataset", "instance_id", "hf_revision"],
            "frame_sources": {
                "world-frame": "dataset-derived",
                "governance-frame": "synthetic-contract-minimum",
            },
        },
        "privacy": {"status": "clean", "pii_scanned": False, "redactions": []},
        "labels": {
            "instance_id": instance_id,
            "benchmark": BENCHMARK,
            "repo": row.get("repo", ""),
            "language": "python",
            "split": "train",
            "task_family": "issue-resolution",
            "has_patch": bool(gold_patch),
            "has_tests": bool(test_patch or fail_to_pass or pass_to_pass),
            "has_trajectory": False,
        },
        "oracle": {
            "kind": "test-based",
            "fail_to_pass": fail_to_pass,
            "pass_to_pass": pass_to_pass,
        },
        "reference_supervision": {
            "gold_patch": gold_patch,
            "gold_patch_sha256": _sha256(gold_patch),
            "test_patch": test_patch,
            "test_patch_sha256": _sha256(test_patch),
            "hints_text": hints_text,
        },
        "frames": [world, governance],
    }
    trace["build"]["content_hash"] = env.content_hash(trace)
    trace["validation"] = {"schema": env.ENVELOPE_SCHEMA_FILE, "status": "valid"}
    return trace
```

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/adapters/swe_gym_lite.py tests/test_swe_gym_lite_adapter.py
git commit -m "feat(adapters): SWE-Gym-Lite row->PneumaTrace builder + skip policy"
```

---

## Task 6: run() — sort, validate/quarantine, index, deterministic report

**Files:**

- Modify: `src/pneuma_lab/adapters/swe_gym_lite.py`
- Test: `tests/test_swe_gym_lite_adapter.py`

`run()` returns a dict of four **canonical strings** (exact bytes to write), so tests
compare strings without touching disk.

- [ ] **Step 1: Write the failing test** — append:

```python
def _rows():
    r2 = dict(SAMPLE_ROW, instance_id="aaa__lib-1", hints_text="")   # sorts first, no hints
    r3 = dict(SAMPLE_ROW, instance_id="zzz__lib-9")                   # sorts last
    return [SAMPLE_ROW, r2, r3]


def test_run_counts_sort_and_determinism():
    out1 = swe.run(_rows(), hf_revision="f70b1a29", source_file="f.parquet")
    out2 = swe.run(_rows(), hf_revision="f70b1a29", source_file="f.parquet")
    assert out1 == out2  # byte-identical across runs

    import json as _json
    report = _json.loads(out1["adapter_report.json"])
    assert report["counts"] == {"source_rows": 3, "traces_emitted": 3,
                                 "valid": 3, "invalid": 0, "skipped": 0}
    assert report["ordering"] == {"emission_sort_key": "instance_id", "source_row_preserved": True}
    assert report["oracle_coverage"]["hints_present"] == 2  # r2 has empty hints
    # traces sorted by instance_id
    ids = [_json.loads(l)["labels"]["instance_id"]
           for l in out1["pneuma_traces.jsonl"].splitlines()]
    assert ids == ["aaa__lib-1", "getmoto__moto-5752", "zzz__lib-9"]
    # index rows carry the required fields
    idx0 = _json.loads(out1["trace_index.jsonl"].splitlines()[0])
    assert idx0["frame_kinds"] == ["world-frame", "governance-frame"]
    assert idx0["content_hash"]


def test_run_skips_unbuildable_row():
    bad = dict(SAMPLE_ROW, instance_id="bad__row-1")
    del bad["base_commit"]
    out = swe.run(_rows() + [bad], hf_revision="f70b1a29", source_file="f.parquet")
    import json as _json
    report = _json.loads(out["adapter_report.json"])
    assert report["counts"]["skipped"] == 1
    assert report["skipped_source_ids"] == [{"source_id": "bad__row-1", "reason": "missing base_commit"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: FAIL (`AttributeError: ... 'run'`).

- [ ] **Step 3: Implement** — add to `swe_gym_lite.py` (add `from pneuma_lab.schemas import validate` at top):

```python
ADAPTER_REPORT_SCHEMA_VERSION = "0.1.0"


def _index_row(trace: dict) -> dict:
    labels = trace["labels"]
    return {
        "trace_id": trace["trace_id"],
        "run_id": trace["run_id"],
        "source_id": labels["instance_id"],
        "repo": labels["repo"],
        "split": labels["split"],
        "benchmark": labels["benchmark"],
        "has_patch": labels["has_patch"],
        "has_tests": labels["has_tests"],
        "has_trajectory": labels["has_trajectory"],
        "num_frames": len(trace["frames"]),
        "frame_kinds": ["world-frame", "governance-frame"],
        "oracle_kind": trace["oracle"]["kind"],
        "privacy_status": trace["privacy"]["status"],
        "validation_status": trace["validation"]["status"],
        "content_hash": trace["build"]["content_hash"],
    }


def _jsonl(objs: list[dict]) -> str:
    return "".join(env.canonical_json(o) + "\n" for o in objs)


def _sha256(text: str) -> str:  # (already defined in Task 5; keep single definition)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(rows, hf_revision: str, source_file: str) -> dict[str, str]:
    """Build all traces; return the four output files as canonical strings."""
    indexed = sorted(enumerate(rows), key=lambda p: str(p[1].get("instance_id", "")))
    valid, invalid, skipped = [], [], []
    for source_row, row in indexed:
        try:
            trace = build_trace(row, hf_revision, source_file, source_row)
        except SkipRow as exc:
            skipped.append({"source_id": row.get("instance_id", f"<row {source_row}>"),
                            "reason": str(exc)})
            continue
        frame_errs = [e for f in trace["frames"] for e in validate.iter_errors(f)]
        env_errs = env.envelope_errors(trace)
        if frame_errs or env_errs:
            trace["validation"]["status"] = "invalid"
            invalid.append({"trace_id": trace["trace_id"],
                            "source_id": trace["provenance"]["source_id"],
                            "errors": {"envelope": env_errs, "frames": frame_errs},
                            "trace": trace})
        else:
            valid.append(trace)

    traces_str = _jsonl(valid)
    invalid_str = _jsonl(invalid)
    index_str = _jsonl([_index_row(t) for t in valid])

    def present(field):
        return sum(1 for t in valid if t["reference_supervision"].get(field))

    report = {
        "adapter_report_schema_version": ADAPTER_REPORT_SCHEMA_VERSION,
        "adapter": dict(ADAPTER),
        "dataset": DATASET,
        "hf_repo": HF_REPO,
        "hf_revision": hf_revision,
        "counts": {
            "source_rows": len(rows),
            "traces_emitted": len(valid) + len(invalid),
            "valid": len(valid),
            "invalid": len(invalid),
            "skipped": len(skipped),
        },
        "frame_validation": {
            "world-frame": {"valid": len(valid), "invalid": len(invalid)},
            "governance-frame": {"valid": len(valid), "invalid": len(invalid)},
        },
        "oracle_coverage": {
            "fail_to_pass_present": sum(1 for t in valid if t["oracle"]["fail_to_pass"]),
            "pass_to_pass_present": sum(1 for t in valid if t["oracle"]["pass_to_pass"]),
            "gold_patch_present": present("gold_patch"),
            "test_patch_present": present("test_patch"),
            "hints_present": present("hints_text"),
        },
        "ordering": {"emission_sort_key": "instance_id", "source_row_preserved": True},
        "skipped_source_ids": skipped,
        "invalid_source_ids": [x["source_id"] for x in invalid],
        "traces_file_sha256": _sha256(traces_str),
        "trace_index_file_sha256": _sha256(index_str),
        "invalid_traces_file_sha256": _sha256(invalid_str),
        "warnings": [],
    }
    return {
        "pneuma_traces.jsonl": traces_str,
        "pneuma_traces.invalid.jsonl": invalid_str,
        "trace_index.jsonl": index_str,
        "adapter_report.json": env.canonical_json(report) + "\n",
    }
```

Note: keep only ONE `_sha256` definition in the file (it was introduced in Task 5) — do not paste a second copy; the block above shows it only for context.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_swe_gym_lite_adapter.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/adapters/swe_gym_lite.py tests/test_swe_gym_lite_adapter.py
git commit -m "feat(adapters): SWE-Gym-Lite run() with quarantine/skip + deterministic report"
```

---

## Task 7: Parquet reader + CLI + hermetic golden fixture

**Files:**

- Modify: `src/pneuma_lab/adapters/swe_gym_lite.py` (add `read_lite_parquet`, `write_outputs`, and the `main()` CLI)
- Create: `fixtures/adapters/swe_gym_lite/input_rows.jsonl`, `fixtures/adapters/swe_gym_lite/LICENSE_PROVENANCE.md`, `fixtures/adapters/swe_gym_lite/golden/*`
- Test: `tests/test_swe_gym_lite_golden.py`

- [ ] **Step 1: Add IO helpers to `swe_gym_lite.py`:**

```python
import os
import pyarrow.parquet as pq

OUTPUT_FILES = (
    "pneuma_traces.jsonl",
    "pneuma_traces.invalid.jsonl",
    "trace_index.jsonl",
    "adapter_report.json",
)

# Fields the adapter reads; the fixture keeps exactly these (minimum needed).
SOURCE_FIELDS = (
    "instance_id", "repo", "base_commit", "version", "created_at",
    "problem_statement", "patch", "test_patch", "hints_text",
    "FAIL_TO_PASS", "PASS_TO_PASS",
)


def read_lite_parquet(path: str) -> list[dict]:
    """Read the raw SWE-Gym-Lite parquet into a list of row dicts."""
    table = pq.read_table(path)
    return table.to_pylist()


def write_outputs(out_dir: str, files: dict[str, str]) -> None:
    """Write the four canonical strings to out_dir (created if needed)."""
    os.makedirs(out_dir, exist_ok=True)
    for name in OUTPUT_FILES:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(files[name])
```

- [ ] **Step 2: Add the CLI to `src/pneuma_lab/adapters/swe_gym_lite.py`** (append at the
      end of the module — invoked `python -m pneuma_lab.adapters.swe_gym_lite`). Add
      `import argparse` and `import sys` to the module's imports:

```python
DEFAULT_INPUT = "C:/pneuma-data/raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet"
DEFAULT_OUT = "C:/pneuma-data/processed/swe-gym/lite"
DEFAULT_HF_REVISION = "f70b1a29ab120eb0a0ee7a1deb029825e735b2b0"
FIXTURE_DIR = os.path.join("fixtures", "adapters", "swe_gym_lite")
FIXTURE_SOURCE_FILE = "fixtures/adapters/swe_gym_lite/input_rows.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pneuma_lab.adapters.swe_gym_lite")
    p.add_argument("--input", default=DEFAULT_INPUT)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--hf-revision", default=DEFAULT_HF_REVISION)
    p.add_argument("--emit-fixture", action="store_true",
                   help="Check adapter output against the committed golden fixture (fails on drift).")
    p.add_argument("--update-fixture", action="store_true",
                   help="Rewrite the golden fixture from the fixture input (explicit opt-in).")
    return p


def _fixture_rows() -> list[dict]:
    with open(os.path.join(FIXTURE_DIR, "input_rows.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.emit_fixture or args.update_fixture:
        files = run(_fixture_rows(), hf_revision=DEFAULT_HF_REVISION,
                    source_file=FIXTURE_SOURCE_FILE)
        golden = os.path.join(FIXTURE_DIR, "golden")
        if args.update_fixture:
            write_outputs(golden, files)
            print(f"golden fixture rewritten in {golden}")
            return 0
        drift = [name for name in OUTPUT_FILES
                 if open(os.path.join(golden, name), encoding="utf-8").read() != files[name]]
        if drift:
            print(f"FIXTURE DRIFT in: {drift}. Re-run with --update-fixture to accept.", file=sys.stderr)
            return 1
        print("fixture matches golden.")
        return 0

    rows = read_lite_parquet(args.input)
    files = run(rows, hf_revision=args.hf_revision, source_file=args.input)
    write_outputs(args.out, files)
    report = json.loads(files["adapter_report.json"])
    print(f"wrote {report['counts']['valid']} traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(`json` is already imported at the top of the module from Task 4.)

- [ ] **Step 3: Generate the tiny fixture input** (authoring-time; uses the real parquet, allowed here). Run:

```bash
python - <<'PY'
import json, os
from pneuma_lab.adapters import swe_gym_lite as swe
rows = swe.read_lite_parquet(swe.__dict__.get("DEFAULT_INPUT",
    "C:/pneuma-data/raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet"))
# choose 3 SMALL rows, at least one WITH hints and one WITHOUT, for coverage tests
small = sorted(rows, key=lambda r: len(r.get("patch","")) + len(r.get("test_patch","")))
with_hints = next(r for r in small if (r.get("hints_text") or "").strip())
without_hints = next(r for r in small if not (r.get("hints_text") or "").strip())
third = next(r for r in small if r["instance_id"] not in {with_hints["instance_id"], without_hints["instance_id"]})
picked = [with_hints, without_hints, third]
os.makedirs("fixtures/adapters/swe_gym_lite", exist_ok=True)
with open("fixtures/adapters/swe_gym_lite/input_rows.jsonl","w",encoding="utf-8",newline="") as f:
    for r in picked:
        f.write(json.dumps({k: r.get(k) for k in swe.SOURCE_FIELDS}, ensure_ascii=False)+"\n")
print("wrote fixture rows:", [r["instance_id"] for r in picked])
PY
```

- [ ] **Step 4: Write `fixtures/adapters/swe_gym_lite/LICENSE_PROVENANCE.md`:**

```markdown
# Test fixture — SWE-Gym-Lite (NOT redistributed dataset bulk)

3 rows sampled from `SWE-Gym/SWE-Gym-Lite` (HF revision
`f70b1a29ab120eb0a0ee7a1deb029825e735b2b0`), kept ONLY for hermetic adapter tests.
Fields limited to the minimum the adapter reads. Upstream license: see the SWE-Gym
dataset card (parent SWE-Gym is MIT; task content derives from upstream repos under
their own licenses). Do not treat this as a redistributable dataset copy.
```

- [ ] **Step 5: Generate the golden output** (explicit opt-in) and confirm:

Run: `python -m pneuma_lab.adapters.swe_gym_lite --update-fixture`
Expected: prints `golden fixture rewritten in fixtures/adapters/swe_gym_lite/golden`.
Then run: `python -m pneuma_lab.adapters.swe_gym_lite --emit-fixture`
Expected: prints `fixture matches golden.`

- [ ] **Step 6: Write the hermetic golden + drift tests** `tests/test_swe_gym_lite_golden.py`:

```python
from __future__ import annotations

import json
import os

from pneuma_lab.adapters import swe_gym_lite as swe

FIXTURE = os.path.join("fixtures", "adapters", "swe_gym_lite")


def _fixture_rows():
    with open(os.path.join(FIXTURE, "input_rows.jsonl"), encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_golden_byte_match():
    files = swe.run(_fixture_rows(), hf_revision="f70b1a29ab120eb0a0ee7a1deb029825e735b2b0",
                    source_file="fixtures/adapters/swe_gym_lite/input_rows.jsonl")
    for name in swe.OUTPUT_FILES:
        want = open(os.path.join(FIXTURE, "golden", name), encoding="utf-8").read()
        assert files[name] == want, f"golden drift in {name}"


def test_two_run_determinism():
    rows = _fixture_rows()
    a = swe.run(rows, hf_revision="rev", source_file="f")
    b = swe.run(rows, hf_revision="rev", source_file="f")
    assert a == b


def test_emit_fixture_passes_when_golden_current():
    # committed golden matches the adapter's current output
    assert swe.main(["--emit-fixture"]) == 0


def test_emit_fixture_detects_drift(tmp_path, monkeypatch):
    # copy the fixture to a temp dir, corrupt a golden file, point the CLI there:
    # --emit-fixture must return 1 (nonzero) without touching the committed golden.
    import shutil
    tmp_fix = tmp_path / "swe_gym_lite"
    shutil.copytree(FIXTURE, tmp_fix)
    (tmp_fix / "golden" / "adapter_report.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(swe, "FIXTURE_DIR", str(tmp_fix))
    assert swe.main(["--emit-fixture"]) == 1
```

- [ ] **Step 7: Run all tests**

Run: `python -m pytest tests/ -q`
Expected: PASS (full suite green, incl. the 3 new golden/determinism tests).

- [ ] **Step 8: Ensure `.gitignore` keeps only the tiny fixture** — confirm `git status` shows the fixture files as additions and NO `/c/pneuma-data` or `*.parquet` staged:

Run: `git status --porcelain fixtures/ | head` and `git check-ignore fixtures/adapters/swe_gym_lite/input_rows.jsonl || echo "not ignored (good)"`
Expected: fixture files listed as untracked additions; `not ignored (good)`.

- [ ] **Step 9: Commit**

```bash
git add src/pneuma_lab/adapters/swe_gym_lite.py \
        fixtures/adapters/swe_gym_lite tests/test_swe_gym_lite_golden.py
git commit -m "feat(adapters): SWE-Gym-Lite CLI, parquet reader, hermetic golden fixture"
```

---

## Task 8: Run on the full 230-row Lite set + doc note

**Files:**

- Modify: `docs/io-contract.md` (short adapter note)

- [ ] **Step 1: Produce the real out-of-repo artifact** (uses `/c/pneuma-data`):

Run: `python -m pneuma_lab.adapters.swe_gym_lite --input "C:/pneuma-data/raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet" --out "C:/pneuma-data/processed/swe-gym/lite"`
Expected: prints `wrote 230 traces to C:/pneuma-data/processed/swe-gym/lite`.

- [ ] **Step 2: Sanity-check the artifact** (no network, reads local output):

```bash
python - <<'PY'
import json
d="C:/pneuma-data/processed/swe-gym/lite"
rep=json.load(open(d+"/adapter_report.json",encoding="utf-8"))
print("counts:", rep["counts"])
assert rep["counts"] == {"source_rows":230,"traces_emitted":230,"valid":230,"invalid":0,"skipped":0}, rep["counts"]
n=sum(1 for _ in open(d+"/pneuma_traces.jsonl",encoding="utf-8"))
assert n==230, n
print("OK: 230 valid traces, report consistent")
PY
```

Expected: `OK: 230 valid traces, report consistent`.

- [ ] **Step 3: Re-run and confirm byte-determinism** of the out-of-repo artifact:

```bash
python -m pneuma_lab.adapters.swe_gym_lite --out "C:/pneuma-data/processed/swe-gym/lite_b"
python - <<'PY'
import hashlib, os
for name in ["pneuma_traces.jsonl","trace_index.jsonl","adapter_report.json","pneuma_traces.invalid.jsonl"]:
    a=open("C:/pneuma-data/processed/swe-gym/lite/"+name,"rb").read()
    b=open("C:/pneuma-data/processed/swe-gym/lite_b/"+name,"rb").read()
    assert a==b, f"NONDETERMINISM in {name}"
print("byte-identical across runs")
PY
```

Expected: `byte-identical across runs`.

- [ ] **Step 4: Add a short adapter note to `docs/io-contract.md`** (append a section):

```markdown
## Adapters (Phase 3)

`src/pneuma_lab/adapters/` converts external SWE datasets into `PneumaTrace`
envelopes (`schemas/pneuma-trace.schema.json`, `x-pneuma-schema-kind: "envelope"`)
that wrap existing validated input frames. First adapter: `swe_gym_lite` — task-only,
deterministic, quarantine/skip policy, out-of-repo output under
`C:/pneuma-data/processed/swe-gym/lite/`. Run: `python -m pneuma_lab.adapters.swe_gym_lite`.
See `docs/superpowers/specs/2026-07-07-swe-gym-lite-pneuma-trace-adapter-design.md`.
```

- [ ] **Step 5: Final full-suite run + commit**

Run: `python -m pytest tests/ -q`
Expected: PASS (all green).

```bash
git add docs/io-contract.md
git commit -m "docs: note Phase-3 SWE-Gym-Lite PneumaTrace adapter in io-contract"
```

---

## Definition of Done (from spec §12)

- `schemas/pneuma-trace.schema.json` exists, valid, in the `envelopes` bucket.
- `envelope.py` + `swe_gym_lite.py` + CLI produce the four byte-deterministic files
  under `processed/swe-gym/lite/` for all 230 Lite rows.
- All 9 spec tests present and passing; `pytest tests/ -q` fully green.
- Tiny hermetic golden fixture committed; tests never touch `/c/pneuma-data` or network.
- No raw dataset bulk in the repo; no 9to5 changes; no ML training.
- `docs/io-contract.md` updated.

## Test → spec-requirement map (spec §11)

1. Schema validity → Task 1 (`test_envelope_bucket_registered`, `test_envelope_schema_shape`).
2. Envelope unit determinism/hash/canonical → Task 2.
3. Frame construction validates → Task 4 (`test_world_frame_validates`, `test_governance_frame_validates`).
4. Golden byte-match → Task 7 (`test_golden_byte_match`).
5. Two-run determinism → Task 7 (`test_two_run_determinism`) + Task 8 Step 3.
6. Quarantine + skip → Task 5 (`test_build_trace_skips_...`) + Task 6 (`test_run_skips_unbuildable_row`; invalid path via envelope/frame errors).
7. Malformed envelope rejected → Task 3 (`test_malformed_envelope_rejected`).
8. Oracle-coverage counts → Task 6 (`test_run_counts_sort_and_determinism` asserts `hints_present`).
9. Fixture-drift protection → Task 7 (`test_emit_fixture_detects_drift`) + `--emit-fixture` CLI.

```

```
