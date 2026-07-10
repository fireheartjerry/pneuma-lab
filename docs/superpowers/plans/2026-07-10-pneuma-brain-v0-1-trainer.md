# PneumaBrain-v0.1 Local Multi-Task Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, CPU-only, task-conditioned multi-task trainer that consumes a `PneumaTrainingExample` corpus and trains the one head with real labels today (`RISK_PREDICTION`) on Dataset #1, gated by the signed corpus authorization, reporting per-task/per-dataset AUROC/Brier/ECE against the E-0 baseline (~0.70).

**Architecture:** A new `src/pneuma_lab/brain/` package. Observable-only features are read from each example's `input.observable_summary` (no raw frames, no prefix windows). A repo-grouped split mirrors the estimator split method. Each task gets its own standardized logistic head (reusing `estimators.logistic`); heads are trained only on examples whose `task_mask` includes them (masked, never negative), so adding proxy-label heads later is data-only. A fail-closed corpus preflight requires a signed `pneuma-brain-corpus-authorization` bound to the corpus-manifest hash, the code commit, and an empty repo-local output root before any fit. All artifacts are canonical JSON under `build/` (gitignored). Advisory-only: no runtime integration, no verifier bypass.

**Tech Stack:** Pure Python stdlib + `jsonschema` (already a dep). Reuses `pneuma_lab.estimators.logistic`, `pneuma_lab.estimators.metrics`, `pneuma_lab.adapters.envelope.canonical_json`, and `pneuma_lab.schemas.load_schema`. No numpy/torch/GPU.

**Scope note (read first):** Only `RISK_PREDICTION` has real labels in the D1 corpus today (the converter emits `target={"resolved":...}` and `task_mask=["RISK_PREDICTION"]`). The other four v0.1 heads (`VERIFICATION_PRESSURE`, `FAILURE_SHAPE`, `SCAR_MOTIF`, `TASK_DIFFICULTY`) need constructed/proxy-label converters that do **not** exist yet — those are a **separate follow-up plan** (`pneuma-brain-v0-1-proxy-heads`). This plan builds the multi-task _framework_ and runs the one real head end-to-end. The framework masks unlabeled heads, so the follow-up is data-only.

**Label convention (locked):** `RISK_PREDICTION` predicts **failure**. `y = 0 if example.target.resolved else 1`. A higher score means higher failure probability.

---

## File Structure

- Create `src/pneuma_lab/brain/__init__.py` — package marker + public exports.
- Create `src/pneuma_lab/brain/features.py` — `observable_summary` → named leakage-safe feature vector + frozen tool vocabulary.
- Create `src/pneuma_lab/brain/corpus.py` — load `PneumaTrainingExample` JSONL, select examples per task, derive labels.
- Create `src/pneuma_lab/brain/split.py` — deterministic repo-grouped dev/eval split.
- Create `src/pneuma_lab/brain/model.py` — `MultiTaskModel`: per-task standardized logistic head; canonical-JSON (de)serialization.
- Create `src/pneuma_lab/brain/report.py` — per-task/per-dataset scoring + markdown report.
- Create `src/pneuma_lab/brain/preflight.py` — fail-closed corpus authorization gate.
- Create `src/pneuma_lab/brain/train.py` — CLI orchestrator: preflight → load → featurize → split → fit → score → write artifacts.
- Create `fixtures/brain/synthetic_corpus.jsonl` — hermetic schema-valid examples for tests.
- Create `fixtures/brain/authorization_authorized.json` — hermetic signed authorization for preflight tests.
- Create `tests/test_brain_features.py`, `tests/test_brain_corpus.py`, `tests/test_brain_split.py`, `tests/test_brain_model.py`, `tests/test_brain_report.py`, `tests/test_brain_preflight.py`, `tests/test_brain_train.py`.
- Modify `docs/project-status.json` and `src/pneuma_lab/status.py` — register the `pneuma_brain_trainer` system (final task).
- Modify `CLAUDE.md` Tree Guide — one line for `src/pneuma_lab/brain/` (final task).

---

## Task 1: Package marker

**Files:**

- Create: `src/pneuma_lab/brain/__init__.py`
- Test: `tests/test_brain_features.py` (import smoke lives with Task 2)

- [ ] **Step 1: Create the package file**

```python
"""PneumaBrain-v0.1 local multi-task trainer (offline, advisory-only).

Deterministic, CPU-only. Consumes PneumaTrainingExample corpora and trains
task-conditioned logistic heads over observable-only features. No runtime
integration, no verifier bypass, no consciousness claim.
"""

from __future__ import annotations

BRAIN_VERSION = "pneuma-brain/0.1.0"

__all__ = ["BRAIN_VERSION"]
```

- [ ] **Step 2: Verify import**

Run: `python -c "import pneuma_lab.brain as b; print(b.BRAIN_VERSION)"`
Expected: prints `pneuma-brain/0.1.0`

- [ ] **Step 3: Commit**

```bash
git add src/pneuma_lab/brain/__init__.py
git commit -m "feat(brain): add PneumaBrain-v0.1 package marker"
```

---

## Task 2: Feature extraction

**Files:**

- Create: `src/pneuma_lab/brain/features.py`
- Test: `tests/test_brain_features.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import math

import pytest

from pneuma_lab.brain import features as feat


def _summary() -> dict:
    return {
        "tool_call_count": 10,
        "tool_counts": {"read_file": 6, "edit_file": 3, "run_tests": 1},
        "retry_count_max": 4,
        "retry_count_mean": 1.5,
        "steps_retry_ge2": 3,
        "strategy_switches_final": 2,
        "error_observation_count": 4,
        "observation_count": 20,
        "error_density": 0.2,
        "assistant_text_length_mean": 430.0,
        "assistant_text_length_max": 1800,
        "observation_length_mean": 900.0,
        "observation_length_max": 12000,
    }


def test_scalar_features_are_named_and_log1p_scaled() -> None:
    row = feat.scalar_features(_summary())
    assert row["retry_count_max"] == 4.0
    assert row["error_density"] == pytest.approx(0.2)
    assert row["log1p_tool_call_count"] == pytest.approx(math.log1p(10))


def test_freeze_tool_vocab_is_deterministic_top_n() -> None:
    vocab = feat.freeze_tool_vocab([_summary(), _summary()], n=2)
    assert vocab == ["read_file", "edit_file"]


def test_feature_row_matches_feature_names_length() -> None:
    vocab = feat.freeze_tool_vocab([_summary()], n=2)
    names = feat.feature_names(vocab)
    row = feat.feature_row(_summary(), vocab)
    assert len(row) == len(names)
    assert names[-2:] == ["tool_count__read_file", "tool_count__edit_file"]
    assert row[-2:] == [6.0, 3.0]


def test_assert_no_leakage_rejects_target_keys() -> None:
    with pytest.raises(ValueError):
        feat.assert_no_leakage({"input": {"nested": {"resolved": True}}})
    feat.assert_no_leakage({"input": _summary()})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_features.py -q`
Expected: FAIL (module `pneuma_lab.brain.features` not found)

- [ ] **Step 3: Write the implementation**

```python
"""Leakage-safe, observable-only feature extraction from corpus examples.

Features are read from each PneumaTrainingExample's ``input.observable_summary``
(full-trace only; the examples carry no raw frames, so no prefix windows).
Deterministic: no wall-clock, no randomness. A frozen tool vocabulary is built
from the dev split only.
"""

from __future__ import annotations

import math

CORPUS_FEATURE_VERSION = "pneuma-brain-features/0.1.0"
N_FROZEN_TOOLS = 6

SCALAR_FEATURE_NAMES = (
    "log1p_tool_call_count",
    "retry_count_max",
    "retry_count_mean",
    "steps_retry_ge2",
    "strategy_switches_final",
    "error_density",
    "log1p_error_observation_count",
    "log1p_observation_count",
    "log1p_assistant_len_mean",
    "log1p_assistant_len_max",
    "log1p_observation_len_mean",
    "log1p_observation_len_max",
)

TOOL_COUNT_PREFIX = "tool_count__"

# Any of these keys appearing anywhere under input is a leakage bug.
FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "resolved",
        "outcome",
        "labels",
        "gold",
        "oracle",
        "fail_to_pass",
        "pass_to_pass",
        "patch",
        "verdict",
    }
)


def _log1p(value) -> float:
    return math.log1p(float(value or 0))


def scalar_features(summary: dict) -> dict:
    """Named scalar features from one observable_summary block."""
    return {
        "log1p_tool_call_count": _log1p(summary.get("tool_call_count")),
        "retry_count_max": float(summary.get("retry_count_max") or 0),
        "retry_count_mean": float(summary.get("retry_count_mean") or 0.0),
        "steps_retry_ge2": float(summary.get("steps_retry_ge2") or 0),
        "strategy_switches_final": float(summary.get("strategy_switches_final") or 0),
        "error_density": float(summary.get("error_density") or 0.0),
        "log1p_error_observation_count": _log1p(summary.get("error_observation_count")),
        "log1p_observation_count": _log1p(summary.get("observation_count")),
        "log1p_assistant_len_mean": _log1p(summary.get("assistant_text_length_mean")),
        "log1p_assistant_len_max": _log1p(summary.get("assistant_text_length_max")),
        "log1p_observation_len_mean": _log1p(summary.get("observation_length_mean")),
        "log1p_observation_len_max": _log1p(summary.get("observation_length_max")),
    }


def freeze_tool_vocab(summaries: list[dict], n: int = N_FROZEN_TOOLS) -> list[str]:
    """Top-n tools by total count, ties broken by name. Deterministic."""
    totals: dict[str, int] = {}
    for summary in summaries:
        for tool, count in (summary.get("tool_counts") or {}).items():
            totals[str(tool)] = totals.get(str(tool), 0) + int(count)
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tool for tool, _ in ordered[:n]]


def feature_names(tool_vocab: list[str]) -> list[str]:
    """Fixed, deterministic feature-name order."""
    return list(SCALAR_FEATURE_NAMES) + [
        f"{TOOL_COUNT_PREFIX}{tool}" for tool in tool_vocab
    ]


def feature_row(summary: dict, tool_vocab: list[str]) -> list[float]:
    """One ordered float row for a summary against a frozen tool vocabulary."""
    scalars = scalar_features(summary)
    row = [scalars[name] for name in SCALAR_FEATURE_NAMES]
    counts = summary.get("tool_counts") or {}
    row.extend(float(counts.get(tool, 0)) for tool in tool_vocab)
    return row


def _walk_keys(value) -> list[str]:
    if isinstance(value, dict):
        keys = [str(k) for k in value]
        for child in value.values():
            keys.extend(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for child in value:
            keys.extend(_walk_keys(child))
        return keys
    return []


def assert_no_leakage(example: dict) -> None:
    """Raise if any forbidden target/oracle key appears under input."""
    keys = {key.lower() for key in _walk_keys(example.get("input") or {})}
    forbidden = sorted(FORBIDDEN_INPUT_KEYS.intersection(keys))
    if forbidden:
        raise ValueError(f"example input has forbidden leakage keys: {forbidden}")


__all__ = [
    "CORPUS_FEATURE_VERSION",
    "N_FROZEN_TOOLS",
    "SCALAR_FEATURE_NAMES",
    "TOOL_COUNT_PREFIX",
    "FORBIDDEN_INPUT_KEYS",
    "scalar_features",
    "freeze_tool_vocab",
    "feature_names",
    "feature_row",
    "assert_no_leakage",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_features.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/brain/features.py tests/test_brain_features.py
git commit -m "feat(brain): observable-only feature extraction with leakage guard"
```

---

## Task 3: Synthetic corpus fixture

**Files:**

- Create: `fixtures/brain/synthetic_corpus.jsonl`
- Test: `tests/test_brain_corpus.py` (Task 4 consumes this fixture)

- [ ] **Step 1: Generate the fixture with a one-off script**

Create and run this throwaway generator (do NOT commit the script; commit only its JSONL output). It builds 12 schema-valid `RISK_PREDICTION` examples across 4 repos with a learnable signal (more errors/retries → unresolved).

```python
# scratch_gen.py  (run once, then delete)
import json, hashlib
from pneuma_lab.schemas import load_schema
from jsonschema import Draft202012Validator

def example(i, repo, resolved, errs, retries, tools):
    src = hashlib.sha256(f"{repo}-{i}".encode()).hexdigest()[:16]
    return {
        "example_id": f"pte:swe-gym-openhands-sampled:{src}:risk:full",
        "dataset_id": "swe-gym-openhands-sampled",
        "dataset_family": "swe-gym",
        "source_path_or_hash": f"sha256:{src}",
        "source_revision": None,
        "example_type": "TrajectoryExample",
        "input_modality": "structured_features",
        "task_type": "RISK_PREDICTION",
        "task_mask": ["RISK_PREDICTION"],
        "input": {
            "trace_id": f"t{i}", "run_id": f"r{i}", "task_id": f"{repo}#{i}",
            "repo": repo, "prefix": "full",
            "trajectory": {"num_messages": 10, "num_agent_steps": 8},
            "observable_summary": {
                "tool_call_count": sum(tools.values()),
                "tool_counts": tools,
                "retry_count_max": retries, "retry_count_mean": retries / 2.0,
                "steps_retry_ge2": retries, "strategy_switches_final": errs,
                "error_observation_count": errs, "observation_count": 20,
                "error_density": errs / 20.0,
                "assistant_text_length_mean": 400.0, "assistant_text_length_max": 1800,
                "observation_length_mean": 900.0, "observation_length_max": 12000,
            },
            "objective": {"present": True, "mode": "digest_only"},
            "feature_refs": ["pneuma-estimators-features/0.1.0"],
        },
        "target": {"resolved": resolved},
        "label_provenance": {"kind": "harness_outcome", "description": "synthetic", "confidence": "high"},
        "privacy_status": "public_or_benchmark",
        "redaction_receipt": {"status": "not_needed", "report_ref": None},
        "leakage_risk": "low",
        "allowed_training_uses": ["test"], "blocked_training_uses": ["runtime"],
        "model_use_tier": "train_after_adapter", "training_weight": 0.0,
        "split_policy": "repo_grouped",
        "split_group": {"repo": repo, "task_id": f"{repo}#{i}", "session_or_user": None, "era": None},
        "canonical_feature_refs": ["pneuma-estimators-features/0.1.0"],
        "evidence_refs": [{"kind": "synthetic_fixture", "ref": "fixtures/brain/synthetic_corpus.jsonl"}],
    }

rows = []
repos = ["org/alpha", "org/beta", "org/gamma", "org/delta"]
for i in range(12):
    repo = repos[i % 4]
    resolved = (i % 2 == 0)            # half resolved
    errs = 1 if resolved else 8        # signal: failures have more errors
    retries = 0 if resolved else 4
    tools = {"read_file": 6, "edit_file": 3, "run_tests": 1} if resolved else {"read_file": 2, "edit_file": 9}
    rows.append(example(i, repo, resolved, errs, retries, tools))

schema = load_schema("pneuma-training-example.schema.json")
v = Draft202012Validator(schema)
for r in rows:
    errs = list(v.iter_errors(r))
    assert not errs, errs

import pathlib
p = pathlib.Path("fixtures/brain/synthetic_corpus.jsonl")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8", newline="")
print("wrote", p)
```

Run: `python scratch_gen.py && rm scratch_gen.py`
Expected: prints `wrote fixtures/brain/synthetic_corpus.jsonl`; script deleted.

- [ ] **Step 2: Verify the fixture is schema-valid and non-empty**

Run: `python -c "import json; rows=[json.loads(l) for l in open('fixtures/brain/synthetic_corpus.jsonl',encoding='utf-8')]; print(len(rows))"`
Expected: prints `12`

- [ ] **Step 3: Commit**

```bash
git add fixtures/brain/synthetic_corpus.jsonl
git commit -m "test(brain): add hermetic synthetic RISK_PREDICTION corpus fixture"
```

---

## Task 4: Corpus loading and labels

**Files:**

- Create: `src/pneuma_lab/brain/corpus.py`
- Test: `tests/test_brain_corpus.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.brain import corpus

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "brain" / "synthetic_corpus.jsonl"


def test_load_examples_reads_all_rows() -> None:
    examples = corpus.load_examples(FIXTURE)
    assert len(examples) == 12
    assert all("task_mask" in e for e in examples)


def test_examples_for_task_selects_by_mask_and_target() -> None:
    examples = corpus.load_examples(FIXTURE)
    risk = corpus.examples_for_task(examples, "RISK_PREDICTION")
    assert len(risk) == 12
    assert corpus.examples_for_task(examples, "FAILURE_SHAPE") == []


def test_risk_label_is_failure_is_one() -> None:
    resolved = {"target": {"resolved": True}}
    failed = {"target": {"resolved": False}}
    assert corpus.risk_label(resolved) == 0
    assert corpus.risk_label(failed) == 1


def test_repo_of_reads_split_group() -> None:
    examples = corpus.load_examples(FIXTURE)
    assert corpus.repo_of(examples[0]) in {"org/alpha", "org/beta", "org/gamma", "org/delta"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_corpus.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the implementation**

```python
"""Load PneumaTrainingExample corpora and derive per-task supervision."""

from __future__ import annotations

import json
from pathlib import Path


def load_examples(path: str | Path) -> list[dict]:
    """Read a PneumaTrainingExample JSONL file into a list of dicts."""
    examples: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def examples_for_task(examples: list[dict], task_type: str) -> list[dict]:
    """Examples whose task_mask includes task_type and that carry a target."""
    selected = []
    for example in examples:
        if task_type in (example.get("task_mask") or []) and example.get("target"):
            selected.append(example)
    return selected


def risk_label(example: dict) -> int:
    """RISK_PREDICTION label: failure=1. resolved=True -> 0, else 1."""
    resolved = (example.get("target") or {}).get("resolved")
    if resolved is None:
        raise ValueError("RISK_PREDICTION example is missing target.resolved")
    return 0 if bool(resolved) else 1


def repo_of(example: dict) -> str:
    """Repository used for the grouped split."""
    return (example.get("split_group") or {}).get("repo") or ""


__all__ = ["load_examples", "examples_for_task", "risk_label", "repo_of"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_corpus.py -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/brain/corpus.py tests/test_brain_corpus.py
git commit -m "feat(brain): corpus loading and RISK label derivation"
```

---

## Task 5: Repo-grouped split

**Files:**

- Create: `src/pneuma_lab/brain/split.py`
- Test: `tests/test_brain_split.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pneuma_lab.brain import split


def test_split_is_deterministic_and_repo_grouped() -> None:
    a = split.split_of_repo("pandas-dev/pandas")
    b = split.split_of_repo("pandas-dev/pandas")
    assert a == b
    assert a in {"dev", "eval"}


def test_split_method_matches_estimator_convention() -> None:
    assert split.SPLIT_METHOD == "sha256_repo_mod10_lt3_eval_v1"


def test_assign_groups_examples_whole_repo_to_one_split() -> None:
    examples = [
        {"split_group": {"repo": "org/alpha"}},
        {"split_group": {"repo": "org/alpha"}},
        {"split_group": {"repo": "org/beta"}},
    ]
    assignment = split.assign(examples)
    assert assignment[0] == assignment[1]  # same repo -> same split
    assert set(assignment.values()) <= {"dev", "eval"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_split.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the implementation**

```python
"""Deterministic repo-grouped dev/eval split.

Mirrors the estimator split method ``sha256_repo_mod10_lt3_eval_v1``: repos whose
sha256 digit sum mod 10 is < 3 go to eval, the rest to dev. Because the split is
a pure function of the repository, every example for one repo lands in the same
split, so no repository can straddle train and eval.
"""

from __future__ import annotations

import hashlib

SPLIT_METHOD = "sha256_repo_mod10_lt3_eval_v1"


def split_of_repo(repo: str) -> str:
    """'eval' if sha256(repo) mod 10 < 3 else 'dev'. Deterministic."""
    digest = hashlib.sha256((repo or "").encode("utf-8")).hexdigest()
    return "eval" if (int(digest, 16) % 10) < 3 else "dev"


def assign(examples: list[dict]) -> dict[int, str]:
    """Map each example index to its split by repository."""
    result: dict[int, str] = {}
    for index, example in enumerate(examples):
        repo = (example.get("split_group") or {}).get("repo") or ""
        result[index] = split_of_repo(repo)
    return result


__all__ = ["SPLIT_METHOD", "split_of_repo", "assign"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_split.py -q`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/brain/split.py tests/test_brain_split.py
git commit -m "feat(brain): deterministic repo-grouped split"
```

---

## Task 6: Multi-task model

**Files:**

- Create: `src/pneuma_lab/brain/model.py`
- Test: `tests/test_brain_model.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import json

from pneuma_lab.brain import model as m


def _separable():
    # Two features; class 1 has larger values -> perfectly separable.
    rows = [[0.0, 0.0], [0.1, 0.2], [5.0, 5.0], [5.1, 4.9]]
    labels = [0, 0, 1, 1]
    names = ["f0", "f1"]
    return names, rows, labels


def test_fit_and_predict_learns_direction() -> None:
    names, rows, labels = _separable()
    head = m.fit_head(names, rows, labels)
    lo = m.predict_head(head, [0.0, 0.0])
    hi = m.predict_head(head, [5.0, 5.0])
    assert hi > lo
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0


def test_model_round_trips_through_canonical_json() -> None:
    names, rows, labels = _separable()
    model = m.MultiTaskModel(BRAIN_VERSION_OK="pneuma-brain/0.1.0")
    model.add_task("RISK_PREDICTION", m.fit_head(names, rows, labels))
    text = model.to_json()
    restored = m.MultiTaskModel.from_json(text)
    assert restored.tasks() == ["RISK_PREDICTION"]
    original = m.predict_head(model.head("RISK_PREDICTION"), [5.0, 5.0])
    loaded = m.predict_head(restored.head("RISK_PREDICTION"), [5.0, 5.0])
    assert original == loaded
    # canonical JSON is stable
    assert json.loads(text)["model_version"] == "pneuma-brain/0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_model.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the implementation**

```python
"""Task-conditioned multi-task model: one standardized logistic head per task."""

from __future__ import annotations

import json

from pneuma_lab.brain import BRAIN_VERSION
from pneuma_lab.estimators import logistic as logit


def fit_head(feature_names: list[str], rows: list[list[float]], labels: list[int]) -> dict:
    """Standardize on the given rows and fit one logistic head."""
    means, stds = logit.standardizationParams(rows)
    rows_std = [logit.standardizeRow(row, means, stds) for row in rows]
    weights, bias = logit.trainLogistic(rows_std, labels)
    return {
        "feature_names": list(feature_names),
        "means": list(means),
        "stds": list(stds),
        "weights": list(weights),
        "bias": bias,
    }


def predict_head(head: dict, row: list[float]) -> float:
    """Predicted probability for one raw (unstandardized) feature row."""
    row_std = logit.standardizeRow(row, head["means"], head["stds"])
    return logit.predictProb(row_std, head["weights"], head["bias"])


class MultiTaskModel:
    """A named collection of per-task heads with canonical-JSON serialization."""

    def __init__(self, BRAIN_VERSION_OK: str = BRAIN_VERSION) -> None:
        self.model_version = BRAIN_VERSION_OK
        self._heads: dict[str, dict] = {}

    def add_task(self, task_type: str, head: dict) -> None:
        self._heads[task_type] = head

    def head(self, task_type: str) -> dict:
        return self._heads[task_type]

    def tasks(self) -> list[str]:
        return sorted(self._heads)

    def to_json(self) -> str:
        payload = {
            "model_version": self.model_version,
            "heads": {task: self._heads[task] for task in sorted(self._heads)},
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "MultiTaskModel":
        payload = json.loads(text)
        model = cls(BRAIN_VERSION_OK=payload["model_version"])
        for task, head in payload["heads"].items():
            model.add_task(task, head)
        return model


__all__ = ["fit_head", "predict_head", "MultiTaskModel"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_model.py -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/brain/model.py tests/test_brain_model.py
git commit -m "feat(brain): task-conditioned multi-task logistic model"
```

---

## Task 7: Scoring and report

**Files:**

- Create: `src/pneuma_lab/brain/report.py`
- Test: `tests/test_brain_report.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from pneuma_lab.brain import report


def test_score_split_reports_auroc_brier_ece() -> None:
    probs = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]
    scored = report.score_split(probs, labels)
    assert scored["n"] == 4
    assert scored["n_pos"] == 2
    assert scored["auroc"] == 1.0
    assert 0.0 <= scored["brier"] <= 1.0
    assert scored["ece"] >= 0.0


def test_score_split_handles_single_class() -> None:
    scored = report.score_split([0.3, 0.4], [0, 0])
    assert scored["auroc"] is None


def test_markdown_contains_task_and_metrics() -> None:
    payload = {
        "model_version": "pneuma-brain/0.1.0",
        "split_method": "sha256_repo_mod10_lt3_eval_v1",
        "tasks": {
            "RISK_PREDICTION": {
                "dev": {"n": 8, "n_pos": 4, "auroc": 0.9, "brier": 0.1, "ece": 0.05},
                "eval": {"n": 4, "n_pos": 2, "auroc": 0.75, "brier": 0.2, "ece": 0.1},
                "baseline_e0_auroc": 0.70,
            }
        },
    }
    text = report.markdown(payload)
    assert "RISK_PREDICTION" in text
    assert "0.75" in text
    assert "baseline" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_report.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the implementation**

```python
"""Per-task scoring and a compact deterministic markdown report."""

from __future__ import annotations

from pneuma_lab.estimators import metrics as met

# The E-0 observable-feature logistic baseline (prefix-10 B1 AUROC) to beat.
BASELINE_E0_AUROC = 0.70


def score_split(probs: list[float], labels: list[int]) -> dict:
    """AUROC (None if single-class), Brier, ECE, and counts for one split."""
    n = len(probs)
    n_pos = sum(1 for y in labels if y == 1)
    return {
        "n": n,
        "n_pos": n_pos,
        "auroc": met.auroc(probs, labels),
        "brier": met.brier(probs, labels) if n else None,
        "ece": met.ece(probs, labels) if n else None,
    }


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def markdown(payload: dict) -> str:
    """Render a stable markdown report from a scored payload."""
    lines = [
        "# PneumaBrain-v0.1 training report",
        "",
        f"- model_version: `{payload['model_version']}`",
        f"- split_method: `{payload['split_method']}`",
        "",
        "| task | split | n | n_pos | AUROC | Brier | ECE | E-0 baseline |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task in sorted(payload["tasks"]):
        entry = payload["tasks"][task]
        baseline = _fmt(entry.get("baseline_e0_auroc"))
        for split_name in ("dev", "eval"):
            split = entry.get(split_name) or {}
            lines.append(
                f"| {task} | {split_name} | {split.get('n', 0)} | "
                f"{split.get('n_pos', 0)} | {_fmt(split.get('auroc'))} | "
                f"{_fmt(split.get('brier'))} | {_fmt(split.get('ece'))} | {baseline} |"
            )
    lines.append("")
    lines.append(
        "Advisory-only. No runtime integration, no verifier bypass, no consciousness claim."
    )
    return "\n".join(lines) + "\n"


__all__ = ["BASELINE_E0_AUROC", "score_split", "markdown"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_report.py -q`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/brain/report.py tests/test_brain_report.py
git commit -m "feat(brain): per-task scoring and markdown report"
```

---

## Task 8: Fail-closed corpus authorization preflight

**Files:**

- Create: `src/pneuma_lab/brain/preflight.py`
- Create: `fixtures/brain/authorization_authorized.json`
- Test: `tests/test_brain_preflight.py`

- [ ] **Step 1: Create the hermetic signed-authorization fixture**

`fixtures/brain/authorization_authorized.json` — a schema-valid `decision: authorized` artifact for tests (hashes are placeholders that the test binds explicitly):

```json
{
    "authorization_schema_version": "0.1.0",
    "authorization_id": "brain-test-auth",
    "corpus_id": "pneuma-brain-v0",
    "decision": "authorized",
    "scope": "local_research",
    "corpus_manifest_sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "member_lanes": ["swe-gym-openhands-sampled"],
    "members": [
        {
            "lane_id": "swe-gym-openhands-sampled",
            "source_traces_sha256": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
            "split_manifest_sha256": "sha256:2222222222222222222222222222222222222222222222222222222222222222"
        }
    ],
    "authorized_code_commit": "0000000000000000000000000000000000000000",
    "reviewer": "test",
    "reviewed_at": "2026-07-10T00:00:00Z",
    "release_authorization": "not_authorized",
    "runtime_integration": "none"
}
```

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.brain import preflight

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "brain" / "authorization_authorized.json"


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_authorized_artifact_passes_when_manifest_hash_matches(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = _sha256_file(manifest)
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    out = tmp_path / "run"
    verified = preflight.verify_corpus_run(auth_path, manifest, out, require_clean_code=False)
    assert verified["decision"] == "authorized"


def test_not_authorized_decision_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text("{}", encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["decision"] = "not_authorized"
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(auth_path, manifest, tmp_path / "run", require_clean_code=False)


def test_manifest_hash_mismatch_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text("{}", encoding="utf-8")
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")  # placeholder hash
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(auth_path, manifest, tmp_path / "run", require_clean_code=False)


def test_nonempty_output_root_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = _sha256_file(manifest)
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    out = tmp_path / "run"
    out.mkdir()
    (out / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(auth_path, manifest, out, require_clean_code=False)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_preflight.py -q`
Expected: FAIL (module not found)

- [ ] **Step 4: Write the implementation**

```python
"""Fail-closed corpus authorization gate for the PneumaBrain-v0.1 trainer.

The trainer must not fit anything unless a schema-valid, decision=authorized
corpus authorization is bound to the exact corpus manifest bytes, the output
root is empty and repo-local, and (in production) the worktree is clean. This
module verifies those bindings; it does not authorize anything by itself.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab.schemas import load_schema

AUTHORIZATION_SCHEMA = "pneuma-brain-corpus-authorization.schema.json"


class BrainPreflightError(ValueError):
    """A stable, operator-readable fail-closed preflight failure."""


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BrainPreflightError(message)


def _worktree_clean() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout == ""


def verify_corpus_run(
    authorization_path: str | Path,
    corpus_manifest_path: str | Path,
    output_root: str | Path,
    *,
    require_clean_code: bool = True,
) -> dict:
    """Verify the signed authorization binds this corpus manifest and output root."""
    auth_file = Path(authorization_path)
    manifest_file = Path(corpus_manifest_path)
    out_dir = Path(output_root)

    _require(auth_file.is_file(), f"authorization artifact missing: {auth_file}")
    _require(manifest_file.is_file(), f"corpus manifest missing: {manifest_file}")

    import json

    try:
        authorization = json.loads(auth_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrainPreflightError(f"cannot read authorization: {exc}") from exc

    errors = sorted(
        Draft202012Validator(load_schema(AUTHORIZATION_SCHEMA)).iter_errors(authorization),
        key=lambda item: list(item.path),
    )
    if errors:
        raise BrainPreflightError(f"authorization is not schema-valid: {errors[0].message}")

    _require(authorization.get("decision") == "authorized", "authorization decision is not 'authorized'")
    _require(
        authorization.get("corpus_manifest_sha256") == _sha256_file(manifest_file),
        "authorization corpus_manifest_sha256 does not match the corpus manifest bytes",
    )

    if require_clean_code:
        _require(_worktree_clean(), "worktree is not clean; commit or stash before an authorized run")

    if out_dir.exists():
        _require(out_dir.is_dir(), "output root exists but is not a directory")
        _require(not any(out_dir.iterdir()), "output root must be empty before an authorized run")

    return authorization


__all__ = ["AUTHORIZATION_SCHEMA", "BrainPreflightError", "verify_corpus_run"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_preflight.py -q`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/brain/preflight.py fixtures/brain/authorization_authorized.json tests/test_brain_preflight.py
git commit -m "feat(brain): fail-closed corpus authorization preflight"
```

---

## Task 9: Training CLI orchestrator (end-to-end on the fixture)

**Files:**

- Create: `src/pneuma_lab/brain/train.py`
- Test: `tests/test_brain_train.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pneuma_lab.brain import train

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "brain"
CORPUS = FIXTURES / "synthetic_corpus.jsonl"
AUTH = FIXTURES / "authorization_authorized.json"


def _prepare_auth(tmp_path) -> Path:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = "sha256:" + hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    return auth_path, manifest


def test_run_training_writes_model_and_report(tmp_path) -> None:
    auth_path, manifest = _prepare_auth(tmp_path)
    out = tmp_path / "run"
    result = train.run_training(
        corpus_path=CORPUS,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out,
        require_clean_code=False,
    )
    assert (out / "model.json").is_file()
    assert (out / "metrics.json").is_file()
    assert (out / "report.md").is_file()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert "RISK_PREDICTION" in metrics["tasks"]
    # The synthetic corpus is separable; dev AUROC should be strong.
    assert metrics["tasks"]["RISK_PREDICTION"]["dev"]["auroc"] >= 0.9


def test_run_training_is_byte_deterministic(tmp_path) -> None:
    auth_path, manifest = _prepare_auth(tmp_path)
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    train.run_training(corpus_path=CORPUS, authorization_path=auth_path, corpus_manifest_path=manifest, output_root=out_a, require_clean_code=False)
    train.run_training(corpus_path=CORPUS, authorization_path=auth_path, corpus_manifest_path=manifest, output_root=out_b, require_clean_code=False)
    assert (out_a / "model.json").read_bytes() == (out_b / "model.json").read_bytes()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_brain_train.py -q`
Expected: FAIL (module not found)

- [ ] **Step 3: Write the implementation**

```python
"""PneumaBrain-v0.1 training orchestrator (offline, advisory-only, deterministic).

Pipeline: corpus preflight -> load examples -> freeze tool vocab on dev ->
featurize -> repo-grouped split -> fit RISK head on dev -> score dev/eval ->
write model.json, metrics.json, report.md. Only tasks with real labels train;
others are masked. No numpy, no randomness, no wall-clock.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pneuma_lab.brain import corpus as corpus_mod
from pneuma_lab.brain import features as feat
from pneuma_lab.brain import model as model_mod
from pneuma_lab.brain import preflight
from pneuma_lab.brain import report as report_mod
from pneuma_lab.brain import split as split_mod
from pneuma_lab.brain import BRAIN_VERSION

# v0.1 heads with a real label source today. Others are masked until proxy
# converters exist (see the proxy-heads follow-up plan).
TRAINABLE_TASKS = ("RISK_PREDICTION",)
LABELERS = {"RISK_PREDICTION": corpus_mod.risk_label}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(path)


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def run_training(
    *,
    corpus_path: str | Path,
    authorization_path: str | Path,
    corpus_manifest_path: str | Path,
    output_root: str | Path,
    require_clean_code: bool = True,
) -> dict:
    """Verify authorization, then train and score every trainable task."""
    preflight.verify_corpus_run(
        authorization_path,
        corpus_manifest_path,
        output_root,
        require_clean_code=require_clean_code,
    )
    out = Path(output_root)
    examples = corpus_mod.load_examples(corpus_path)
    for example in examples:
        feat.assert_no_leakage(example)

    assignment = split_mod.assign(examples)
    dev_examples = [e for i, e in enumerate(examples) if assignment[i] == "dev"]
    tool_vocab = feat.freeze_tool_vocab(
        [e["input"]["observable_summary"] for e in dev_examples]
    )
    names = feat.feature_names(tool_vocab)

    model = model_mod.MultiTaskModel(BRAIN_VERSION_OK=BRAIN_VERSION)
    tasks_report: dict[str, dict] = {}

    for task in TRAINABLE_TASKS:
        task_examples = corpus_mod.examples_for_task(examples, task)
        if not task_examples:
            continue
        labeler = LABELERS[task]
        indexed = [(e, split_mod.split_of_repo(corpus_mod.repo_of(e))) for e in task_examples]
        dev_rows, dev_labels = [], []
        eval_rows, eval_labels = [], []
        for example, where in indexed:
            row = feat.feature_row(example["input"]["observable_summary"], tool_vocab)
            label = labeler(example)
            if where == "dev":
                dev_rows.append(row)
                dev_labels.append(label)
            else:
                eval_rows.append(row)
                eval_labels.append(label)
        if not dev_rows:
            continue
        head = model_mod.fit_head(names, dev_rows, dev_labels)
        model.add_task(task, head)
        dev_probs = [model_mod.predict_head(head, row) for row in dev_rows]
        eval_probs = [model_mod.predict_head(head, row) for row in eval_rows]
        tasks_report[task] = {
            "dev": report_mod.score_split(dev_probs, dev_labels),
            "eval": report_mod.score_split(eval_probs, eval_labels),
            "baseline_e0_auroc": report_mod.BASELINE_E0_AUROC,
        }

    metrics = {
        "model_version": BRAIN_VERSION,
        "split_method": split_mod.SPLIT_METHOD,
        "feature_version": feat.CORPUS_FEATURE_VERSION,
        "tool_vocab": tool_vocab,
        "n_examples": len(examples),
        "tasks": tasks_report,
    }

    _write(out / "model.json", model.to_json() + "\n")
    _write(out / "metrics.json", _canonical(metrics))
    _write(out / "report.md", report_mod.markdown(metrics))
    return metrics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.brain.train")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--corpus-manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-dirty-code", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        metrics = run_training(
            corpus_path=args.corpus,
            authorization_path=args.authorization,
            corpus_manifest_path=args.corpus_manifest,
            output_root=args.out,
            require_clean_code=not args.allow_dirty_code,
        )
    except preflight.BrainPreflightError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    risk = metrics["tasks"].get("RISK_PREDICTION", {})
    print(f"trained tasks: {sorted(metrics['tasks'])}; RISK eval={risk.get('eval')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_brain_train.py -q`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the whole suite to confirm no regressions**

Run: `python -m pytest tests/ -q`
Expected: PASS (all green, no failures)

- [ ] **Step 6: Commit**

```bash
git add src/pneuma_lab/brain/train.py tests/test_brain_train.py
git commit -m "feat(brain): end-to-end multi-task training orchestrator + CLI"
```

---

## Task 10: Register the system in project status and docs

**Files:**

- Modify: `src/pneuma_lab/status.py` (add to `_CURRENT_SYSTEM_STATE`)
- Modify: `docs/project-status.json` (add system record)
- Modify: `CLAUDE.md` (Tree Guide line)

- [ ] **Step 1: Add the system to the canonical registry in `status.py`**

In `_CURRENT_SYSTEM_STATE`, after the `pneuma_brain_v0_corpus` line add:

```python
    "pneuma_brain_trainer": ("implemented", "offline_research"),
```

- [ ] **Step 2: Add the matching system record to `docs/project-status.json`**

In the `systems` array, after the `pneuma_brain_v0_corpus` object add:

```json
{
    "id": "pneuma_brain_trainer",
    "status": "implemented",
    "scope": "offline_research",
    "evidence_refs": [
        "src/pneuma_lab/brain/train.py",
        "src/pneuma_lab/brain/model.py",
        "src/pneuma_lab/brain/preflight.py",
        "tests/test_brain_train.py"
    ],
    "blockers": []
}
```

- [ ] **Step 3: Add one Tree Guide line to `CLAUDE.md`**

Under the `src/pneuma_lab/` bullets, add:

```
- `src/pneuma_lab/brain/` (Phase 4) is the offline, CPU-only PneumaBrain-v0.1
  multi-task trainer: observable-only features, repo-grouped split, per-task
  logistic heads, a fail-closed corpus-authorization preflight, and a
  deterministic model/metrics/report writer. Advisory-only; no runtime.
```

- [ ] **Step 4: Run both checkers**

Run: `python -m pneuma_lab.status --check`
Expected: `PASS: docs/project-status.json is schema-valid and checkout-coherent.`

Run: `python -m pytest tests/ -q`
Expected: PASS (all green)

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/status.py docs/project-status.json CLAUDE.md
git commit -m "docs(status): register pneuma_brain_trainer system"
```

---

## Task 11 (HUMAN / real-data): Materialize D1 corpus, sign authorization, run

> This task needs the local processed D1 traces at `C:\pneuma-data` and a human authorization decision. It is not hermetic and is executed by the operator, not a subagent. The synthetic-fixture pipeline (Tasks 1-10) proves the trainer works without it.

- [ ] **Step 1: Materialize the full D1 training corpus**

Run (adjust paths to the real processed adapter output):

```bash
python -m pneuma_lab.converters.openhands_sampled_training \
  --mode full --confirm-full-conversion \
  --input C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl \
  --adapter-report C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json \
  --output build/training_examples/openhands-sampled/full/examples.jsonl
```

Expected: `wrote N full examples and 0 invalid records ...` with N matching the adapter report's valid count.

- [ ] **Step 2: Prepare and sign the corpus authorization**

Compute the corpus-manifest hash and the source-traces hash, then fill a signed copy of the template (`decision: authorized`, real hashes, `authorized_code_commit` = current HEAD, `reviewer` = your name, `reviewed_at` = now UTC) and commit it under `docs/data/training-authorizations/`. Verify:

Run: `python -c "import json,jsonschema; from pneuma_lab.schemas import load_schema; jsonschema.Draft202012Validator(load_schema('pneuma-brain-corpus-authorization.schema.json')).validate(json.load(open('docs/data/training-authorizations/pneuma-brain-v0.signed.json')))"`
Expected: no output (valid).

- [ ] **Step 3: Run the trainer on the real corpus**

Run:

```bash
python -m pneuma_lab.brain.train \
  --corpus build/training_examples/openhands-sampled/full/examples.jsonl \
  --authorization docs/data/training-authorizations/pneuma-brain-v0.signed.json \
  --corpus-manifest docs/data/training-readiness/pneuma-brain-v0-corpus.json \
  --out build/brain/v0-1/run-1
```

Expected: prints trained tasks and RISK eval metrics; `build/brain/v0-1/run-1/report.md` written.

- [ ] **Step 4: Compare to the E-0 baseline**

Open `build/brain/v0-1/run-1/report.md`. Record the RISK_PREDICTION eval AUROC and compare to the E-0 baseline (~0.70). This is the headline v0.1 result. Note: build artifacts stay gitignored; commit only the report summary into a docs note if you want it tracked.

---

## Self-Review

- **Spec coverage:** Roadmap §3.1 (observable-only input) → Tasks 2/4; §3.2 five heads → framework in Tasks 6/9 with RISK trained and the rest masked (proxy heads deferred, noted in Scope); §4 "ready to start training" gate → Task 8 preflight + Task 11 signing; §5 readiness architecture → reuses the corpus manifest + authorization schema already shipped; E-0 baseline comparison → Task 7/11. Materialize-corpus gap → Task 11.
- **Placeholder scan:** none — every code step carries full code; the only intentionally operator-run steps are Task 11 (real data + human signature), clearly flagged.
- **Type consistency:** `fit_head`/`predict_head` names consistent across model.py, train.py, tests; `score_split` used identically in report.py and train.py; `verify_corpus_run(...)` signature consistent across preflight.py, train.py, tests; `split_of_repo`/`assign`/`SPLIT_METHOD` consistent.
