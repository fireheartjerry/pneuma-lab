# Foundation Training Launch Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify every local artifact needed to start the first authorized Qwen3.5-2B 100K-token Pneuma foundation smoke run, while leaving training unstarted and optimizer-step count at zero.

**Architecture:** Keep one CLI-first path for WSL2 and the optional RunPod reproduction. Preparation emits deterministic, zero-weight canonical records and content-addressed receipts; a separate operator-approved authorization supplies exact lane-level effective weights in memory, which avoids circularly authorizing a shard before its hash exists. Training and resume are dependency-injected orchestration surfaces that verify authorization, code, cache, data, environment, and resources before model allocation or optimizer construction.

**Tech Stack:** Python 3.12, PyTorch, Transformers pinned to commit `11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69`, bitsandbytes NF4, Accelerate, PEFT, Hugging Face Hub, JSON Schema 2020-12, SQLite/FTS5, psutil, NVIDIA `nvidia-smi`, pytest, uv, WSL2, optional RunPod SSH/tmux.

---

## Scope and non-negotiable invariants

- This plan may install a local WSL environment, cache the pinned 2B checkpoint, read the approved processed OpenHands Sampled lane, and create ignored artifacts under `build/foundation/`.
- This plan must not invoke `train`, `resume`, backward propagation, `optimizer.step()`, a cloud API, a paid resource, or the 397B model.
- `C:\pneuma-data` and `/mnt/c/pneuma-data` are read-only source roots. Before/after metadata receipts must prove that preparation did not change them.
- All ten active families appear in the suite report. Only `swe-gym-openhands-sampled` can receive an effective weight in the first authorization. Eval and governance lanes remain zero-weight.
- Persisted `FoundationTrainingRecord.training_weight` is always `0.0`. Only `apply_verified_authorization()` may create an in-memory positive `effective_weight`, and only for an exact authorized lane.
- A candidate is not an authorization. `train` and `resume` reject pending and candidate records before loading model weights or creating an optimizer.
- The existing PneumaBrain authorization does not authorize this Qwen program.
- `START-HERE-TRAINING.md` must continue to say `TRAINING HAS NOT STARTED` until a later, explicitly authorized training action actually begins.

## File and responsibility map

**Contracts and reviewed policy**

- Create `schemas/foundation-training-record.schema.json`: immutable zero-weight record contract.
- Create `schemas/foundation-suite-report.schema.json`: all-ten role and presence report.
- Modify `schemas/foundation-training-authorization.schema.json`: candidate/final scope, exact lane weights, receipt bindings.
- Modify `schemas/foundation-run-manifest.schema.json`: lifecycle, bindings, telemetry, checkpoints, termination.
- Modify `src/pneuma_lab/schemas/__init__.py`: register every new schema.
- Create `docs/data/training-readiness/pneuma-foundation-v0-suite.json`: reviewed role overlay for all ten families.
- Create `docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json`: conservative local-only provenance posture; no redistribution claim.

**Data preparation and authorization**

- Create `src/pneuma_lab/foundation/records.py`: render, validate, tensorize, and apply verified effective weights.
- Create `src/pneuma_lab/foundation/suite.py`: validate exact family/lane roles and build completeness reports.
- Create `src/pneuma_lab/foundation/source_presence.py`: metadata-only source inventory and payload access guard.
- Create `src/pneuma_lab/foundation/eval_identities.py`: normalized held-out identity readers.
- Create `src/pneuma_lab/foundation/artifacts.py`: canonical hashing and atomic artifact writes shared by preparation, authorization, cache, and reports.
- Modify `src/pneuma_lab/foundation/contamination.py`: nested record identity and complete overlap receipts.
- Modify `src/pneuma_lab/foundation/data.py`: nested-record deduplication, inventories, and zero-weight shard enforcement.
- Create `src/pneuma_lab/foundation/preparation.py`: deterministic 100K orchestration and receipts.
- Modify `src/pneuma_lab/foundation/authorization.py`: candidate, exact phrase finalization, and final verification.

**Environment, cache, dry-run, and operations**

- Modify `pyproject.toml` and create `uv.lock`: exact foundation dependencies.
- Create `.wslconfig.foundation.example`: 24 GiB WSL memory, 8 GiB swap, host headroom.
- Create `scripts/foundation/setup-linux.sh`: shared pinned Linux setup for WSL and optional cloud.
- Create `scripts/foundation/setup-wsl.sh`: Python 3.12/uv setup only; no authorization or training.
- Create `src/pneuma_lab/foundation/environment.py`: setup plan and lock verification.
- Modify `src/pneuma_lab/foundation/doctor.py`: require Python 3.12 and validate the exact environment.
- Create `src/pneuma_lab/foundation/model_cache.py`: pinned 2B snapshot download and hash receipt.
- Create `src/pneuma_lab/foundation/dry_run.py`: no-gradient cache/config/hook/parity/forward verification.
- Create `src/pneuma_lab/foundation/telemetry.py`: live bounded resource sampler and aggregate metrics.
- Create `src/pneuma_lab/foundation/run_manifest.py`: atomic run state and event log writer.
- Modify `src/pneuma_lab/foundation/checkpoints.py`: exact safe-boundary format `0.2.0`.

**Runner, CLI, reports, cloud bundle, and guide**

- Create `src/pneuma_lab/foundation/dataset.py`: hash-verifying shard reader, deterministic sampler, single-document collator.
- Modify `src/pneuma_lab/foundation/core.py` and `optimizer.py`: masked forecasts and effective-weight enforcement.
- Create `src/pneuma_lab/foundation/runner.py`: preflight, train, resume, signal/resource stop handling.
- Create `src/pneuma_lab/foundation/evaluation.py`: validation/regression metrics and optional falsification-result ingestion.
- Create `src/pneuma_lab/foundation/reports.py`: capability, causal, governance, memory-integrity, resource, and welfare-precaution reports.
- Create `src/pneuma_lab/foundation/cloud_bundle.py`: authorized-only portable tar bundle and $45 quote gate.
- Create `src/pneuma_lab/foundation/cli.py`; reduce `__main__.py` to the module entrypoint.
- Create `src/pneuma_lab/foundation/operator_guide.py`: test guide commands against CLI help/constants.
- Create `START-HERE-TRAINING.md`: precise operator runbook with the final `train` action unchecked.
- Modify `docs/project-status.json`, `docs/foundation/local-first-foundation.md`, and their tests.

### Task 1: Canonical zero-weight foundation records and masked forecasts

**Files:**
- Create: `schemas/foundation-training-record.schema.json`
- Create: `src/pneuma_lab/foundation/records.py`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `src/pneuma_lab/foundation/core.py`
- Modify: `src/pneuma_lab/foundation/optimizer.py`
- Create: `tests/test_foundation_records.py`
- Modify: `tests/test_foundation_core.py`
- Modify: `tests/test_foundation_optimizer.py`
- Modify: `tests/test_foundation_schemas.py`

- [ ] **Step 1: Write failing schema, rendering, and masking tests**

Add tests that establish the complete public contract:

```python
def test_openhands_example_renders_zero_weight_record(tokenizer) -> None:
    record = render_foundation_record(
        _canonical_openhands_example(resolved=True),
        lane_disposition=LaneDisposition(
            terminal_role=TerminalRole.TRAIN,
            gradient_eligibility=GradientEligibility.FIRST_STAGE,
            license_disposition="local_research_candidate_no_redistribution",
            privacy_disposition="redaction_verified",
            dual_use_disposition="not_flagged",
            oracle_disposition="target_only",
        ),
        split_assignment={"split_id": "train", "quarantine_id": None},
        tokenizer=tokenizer,
        tokenizer_revision="1" * 40,
        source_receipt_hashes=("a" * 64, "b" * 64),
    )
    assert record["source"]["dataset_family"] == "swe-gym"
    assert record["source"]["lane_id"] == "swe-gym-openhands-sampled"
    assert record["training_weight"] == 0.0
    assert record["rendered"]["target_text"] == '{"resolved":true}'
    assert record["forecast_targets"]["action_success"] == {
        "applicable": True,
        "value": 1.0,
        "provenance": "observed_outcome",
    }
    assert record["forecast_targets"]["verifier_outcome"]["applicable"] is False
    assert record["forecast_targets"]["tool_cost"]["applicable"] is False
    assert record["forecast_targets"]["token_cost"]["applicable"] is False
    assert record["forecast_targets"]["latency_cost"] == {
        "applicable": False,
        "value": None,
        "provenance": None,
    }
    Draft202012Validator(load_schema("foundation-training-record.schema.json")).validate(record)


def test_masked_forecast_loss_uses_only_applicable_targets() -> None:
    predictions = {name: torch.tensor([9.0]) for name in FORECAST_TARGETS}
    targets = {name: torch.tensor([0.0]) for name in FORECAST_TARGETS}
    masks = {name: torch.tensor([False]) for name in FORECAST_TARGETS}
    predictions["action_success"] = torch.tensor([2.0])
    masks["action_success"] = torch.tensor([True])
    assert metacognitive_loss(predictions, targets, masks).item() == 4.0
    masks["action_success"] = torch.tensor([False])
    with pytest.raises(ValueError, match="applicable"):
        metacognitive_loss(predictions, targets, masks)
```

- [ ] **Step 2: Run the focused tests and confirm the missing-contract failure**

Run:

```powershell
python -m pytest tests/test_foundation_records.py tests/test_foundation_core.py tests/test_foundation_optimizer.py tests/test_foundation_schemas.py -q
```

Expected: collection fails because `pneuma_lab.foundation.records` and `foundation-training-record.schema.json` do not exist, or the old two-argument loss rejects the mask.

- [ ] **Step 3: Add the record types, deterministic renderer, schema, and masked loss**

Use these exact Python contracts:

```python
class TerminalRole(str, Enum):
    TRAIN = "train"
    EVAL = "eval"
    GOVERNANCE = "governance"


class GradientEligibility(str, Enum):
    FIRST_STAGE = "first_stage"
    LATER = "later"
    NEVER = "never"


@dataclass(frozen=True)
class LaneDisposition:
    terminal_role: TerminalRole
    gradient_eligibility: GradientEligibility
    license_disposition: str
    privacy_disposition: str
    dual_use_disposition: str
    oracle_disposition: str


@dataclass(frozen=True)
class EffectiveTrainingRecord:
    record: Mapping
    effective_weight: float


def _forecast_targets(example: Mapping) -> dict[str, dict]:
    resolved = bool((example.get("target") or {}).get("resolved"))
    values = {
        "action_success": resolved,
        "expected_error": not resolved,
    }
    return {
        name: {
            "applicable": name in values,
            "value": float(values[name]) if name in values else None,
            "provenance": "observed_outcome" if name in values else None,
        }
        for name in FORECAST_TARGETS
    }


def _digest_text(value: str) -> str:
    if value.startswith("sha256:") and len(value) == 71:
        return value.removeprefix("sha256:")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def foundation_identity(example: Mapping, *, prompt_text: str) -> dict:
    input_value = example.get("input") or {}
    split_group = example.get("split_group") or {}
    objective = input_value.get("objective") or {}
    fuzzy_source = str(objective.get("text_sha256") or prompt_text)
    task_id = split_group.get("task_id") or input_value.get("task_id")
    return {
        "repo": split_group.get("repo") or input_value.get("repo"),
        "issue_or_pr": input_value.get("issue_or_pr") or task_id,
        "task_id": task_id,
        "base_commit": input_value.get("base_commit"),
        "patch_sha256": input_value.get("patch_sha256"),
        "test_patch_sha256": input_value.get("test_patch_sha256"),
        "fuzzy_text_sha256": _digest_text(fuzzy_source),
    }


def foundation_observations(example: Mapping) -> dict:
    input_value = example.get("input") or {}
    summary = input_value.get("observable_summary") or {}
    trajectory = input_value.get("trajectory") or {}
    target = example.get("target") or {}
    return {
        "language": str(input_value.get("language") or "unknown"),
        "tools": sorted(str(name) for name in (summary.get("tool_counts") or {})),
        "trajectory_length": int(trajectory.get("num_agent_steps") or 0),
        "labels": {"resolved": bool(target.get("resolved"))},
    }


def validate_foundation_record(record: Mapping) -> None:
    validator = Draft202012Validator(load_schema("foundation-training-record.schema.json"))
    errors = sorted(validator.iter_errors(dict(record)), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise FoundationRecordError(detail)


def render_prompt_payload(example: Mapping) -> dict:
    input_value = example.get("input") or {}
    objective = input_value.get("objective") or {}
    return {
        "prefix": input_value.get("prefix"),
        "trajectory": input_value.get("trajectory") or {},
        "observable_summary": input_value.get("observable_summary") or {},
        "objective": {
            "present": bool(objective.get("present")),
            "text_length": int(objective.get("text_length") or 0),
        },
        "feature_refs": sorted(str(value) for value in input_value.get("feature_refs") or ()),
    }


def render_foundation_record(
    example: Mapping,
    *,
    lane_disposition: LaneDisposition,
    split_assignment: Mapping,
    tokenizer,
    tokenizer_revision: str,
    source_receipt_hashes: tuple[str, ...],
) -> dict:
    prompt_text = json.dumps(render_prompt_payload(example), sort_keys=True, separators=(",", ":"))
    target_text = json.dumps(example["target"], sort_keys=True, separators=(",", ":"))
    prompt_tokens = len(tokenizer.encode(prompt_text, add_special_tokens=False))
    target_tokens = len(tokenizer.encode(target_text, add_special_tokens=False))
    source = {
        "dataset_family": str(example["dataset_family"]),
        "lane_id": str(example["dataset_id"]),
        "source_record_id": str(example["example_id"]),
        "source_revision": example.get("source_revision"),
        "receipt_hashes": sorted(source_receipt_hashes),
    }
    identity = foundation_identity(example, prompt_text=prompt_text)
    payload = {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:" + hashlib.sha256(
            json.dumps(source, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source": source,
        "disposition": asdict(lane_disposition),
        "identity": identity,
        "split": {
            "split_id": str(split_assignment["split_id"]),
            "quarantine_id": split_assignment.get("quarantine_id"),
        },
        "rendered": {"prompt_text": prompt_text, "target_text": target_text},
        "tokenization": {
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": tokenizer_revision,
            "prompt_tokens": prompt_tokens,
            "target_tokens": target_tokens,
            "total_tokens": prompt_tokens + target_tokens,
        },
        "training_weight": 0.0,
        "forecast_targets": _forecast_targets(example),
        "observations": foundation_observations(example),
    }
    validate_foundation_record(payload)
    return payload
```

The schema must require every top-level key above, use `additionalProperties: false` at every object boundary, enumerate all eight forecast keys, require `training_weight` to be exactly `0.0`, and permit `null` only for identity fields, quarantine, unavailable forecast values/provenance, and source revision. Register it in `FOUNDATION_SCHEMA_FILES`.

Replace the loss and tensor extraction with:

```python
def metacognitive_loss(predictions, targets, masks):
    expected = set(FORECAST_TARGETS)
    if set(predictions) != expected or set(targets) != expected or set(masks) != expected:
        raise ValueError("forecasts, targets, and applicability masks must match the contract")
    losses = []
    for name in FORECAST_TARGETS:
        mask = masks[name].to(device=predictions[name].device, dtype=torch.bool)
        if mask.any():
            target = targets[name].to(
                device=predictions[name].device,
                dtype=predictions[name].dtype,
            )
            losses.append(torch.nn.functional.mse_loss(predictions[name][mask], target[mask]))
    if not losses:
        raise ValueError("at least one applicable forecast target is required")
    return torch.stack(losses).mean()


def forecast_tensors(record, *, device=None):
    values = record.get("forecast_targets") or {}
    if set(values) != set(FORECAST_TARGETS):
        raise TrainingBatchError("all forecast target entries are required")
    targets = {
        name: torch.tensor(
            [float(values[name]["value"] or 0.0)],
            dtype=torch.float32,
            device=device,
        )
        for name in FORECAST_TARGETS
    }
    masks = {
        name: torch.tensor(
            [bool(values[name]["applicable"])],
            dtype=torch.bool,
            device=device,
        )
        for name in FORECAST_TARGETS
    }
    for name in FORECAST_TARGETS:
        entry = values[name]
        if entry["applicable"] and entry["provenance"] not in {
            "observed_outcome",
            "specified_intervention",
        }:
            raise TrainingBatchError(f"forecast target is not outcome-derived: {name}")
    return targets, masks
```

The current OpenHands canonical input is a full-trajectory observable summary. Therefore tool/token cost would be visible in the prompt, `resolved` is a harness outcome rather than an explicit verifier verdict, and latency/retrieval/intervention outcomes are absent. Mask all six of those targets. Only `action_success` and `expected_error` are applicable for this 100K correctness smoke; a temporal-prefix adapter is required before cost, verifier, retrieval, or intervention supervision can become applicable.

The prompt renderer is an explicit allowlist and excludes trace IDs, run IDs, repository names, task/issue IDs, objective hashes, source paths, and every target-bearing field. Identity remains in the record only for splitting, deduplication, and leakage checks; it never enters model tokens.

- [ ] **Step 4: Run focused tests and schema checks**

Run:

```powershell
python -m pytest tests/test_foundation_records.py tests/test_foundation_core.py tests/test_foundation_optimizer.py tests/test_foundation_schemas.py tests/test_schema_loads.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the record contract**

```powershell
git add schemas/foundation-training-record.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/foundation/records.py src/pneuma_lab/foundation/core.py src/pneuma_lab/foundation/optimizer.py tests/test_foundation_records.py tests/test_foundation_core.py tests/test_foundation_optimizer.py tests/test_foundation_schemas.py
git commit -m "feat: add canonical foundation training records"
```

### Task 2: All-ten suite policy and metadata-only blocked-source checks

**Files:**
- Create: `docs/data/training-readiness/pneuma-foundation-v0-suite.json`
- Create: `schemas/foundation-suite-report.schema.json`
- Create: `src/pneuma_lab/foundation/suite.py`
- Create: `src/pneuma_lab/foundation/source_presence.py`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Create: `tests/test_foundation_suite.py`
- Create: `tests/test_foundation_source_presence.py`

- [ ] **Step 1: Write failing all-ten and no-payload-access tests**

```python
def test_suite_has_exactly_ten_coherent_family_roles() -> None:
    policy = load_suite_policy(ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert validate_suite_policy(policy, registry) == ACTIVE_DATASET_GROUPS
    assert policy["first_stage"]["authorized_lane_candidates"] == [
        "swe-gym-openhands-sampled"
    ]


def test_blocked_presence_probe_never_opens_payload(tmp_path, monkeypatch) -> None:
    blocked = tmp_path / "processed" / "swe-chat"
    blocked.mkdir(parents=True)
    (blocked / "present.bin").write_bytes(b"metadata probe fixture")
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("payload opened")))
    report = probe_family_presence(tmp_path, "swe-chat")
    assert report.inspection == "filesystem_metadata_only"
    assert report.payload_opened is False
    assert report.file_count == 1


def test_payload_guard_denies_governance_lanes_before_open(tmp_path) -> None:
    policy = _suite_fixture()
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="sec-bench-pro",
            lane_id=None,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        )
```

- [ ] **Step 2: Run tests and confirm missing suite modules fail**

Run:

```powershell
python -m pytest tests/test_foundation_suite.py tests/test_foundation_source_presence.py -q
```

Expected: collection fails for the two missing modules and policy file.

- [ ] **Step 3: Add the reviewed role overlay and fail-closed APIs**

The committed suite policy must encode this exact matrix:

```json
{
    "manifest_kind": "pneuma_foundation_dataset_suite",
    "manifest_schema_version": "0.1.0",
    "first_stage": {
        "stage": "100k",
        "authorized_lane_candidates": ["swe-gym-openhands-sampled"]
    },
    "families": [
        {"family": "multi-swe-bench", "terminal_role": "train", "gradient_eligibility": "later", "payload_access_100k": "metadata_only"},
        {"family": "open-swe-traces", "terminal_role": "train", "gradient_eligibility": "later", "payload_access_100k": "metadata_only"},
        {"family": "sec-bench-pro", "terminal_role": "governance", "gradient_eligibility": "never", "payload_access_100k": "metadata_only"},
        {"family": "swe-bench", "terminal_role": "eval", "gradient_eligibility": "never", "payload_access_100k": "identity_metadata_only", "identity_metadata_relative_path": "processed/swe-bench/normalized_metadata.jsonl"},
        {"family": "swe-bench-pro", "terminal_role": "eval", "gradient_eligibility": "never", "payload_access_100k": "metadata_only"},
        {"family": "swe-chat", "terminal_role": "governance", "gradient_eligibility": "never", "payload_access_100k": "metadata_only"},
        {"family": "swe-evo", "terminal_role": "train", "gradient_eligibility": "later", "payload_access_100k": "metadata_only"},
        {"family": "swe-gym", "terminal_role": "train", "gradient_eligibility": "first_stage", "payload_access_100k": "approved_processed_lane_only"},
        {"family": "swe-mera", "terminal_role": "eval", "gradient_eligibility": "never", "payload_access_100k": "identity_metadata_only", "identity_metadata_relative_path": "processed/swe-mera/normalized_metadata.jsonl"},
        {"family": "swe-polybench", "terminal_role": "eval", "gradient_eligibility": "later", "payload_access_100k": "identity_metadata_only", "identity_metadata_relative_path": "processed/swe-polybench/normalized_metadata.jsonl"}
    ]
}
```

Implement these exact public APIs:

```python
@dataclass(frozen=True)
class FamilyPresence:
    family: str
    exists: bool
    file_count: int
    byte_count: int
    newest_mtime_ns: int | None
    inspection: str = "filesystem_metadata_only"
    payload_opened: bool = False


def validate_suite_policy(policy: Mapping, registry: Mapping) -> tuple[str, ...]:
    families = [str(item.get("family")) for item in policy.get("families") or ()]
    if len(families) != 10 or set(families) != set(ACTIVE_DATASET_GROUPS):
        raise SuitePolicyError("suite policy must contain each active family exactly once")
    governed = governed_dataset_groups(registry)
    if set(governed) != set(families):
        raise SuitePolicyError("suite and registry families differ")
    candidates = policy["first_stage"]["authorized_lane_candidates"]
    if candidates != ["swe-gym-openhands-sampled"]:
        raise SuitePolicyError("100k may nominate only the OpenHands Sampled lane")
    return ACTIVE_DATASET_GROUPS


def probe_family_presence(data_root: Path, family: str) -> FamilyPresence:
    root = Path(data_root) / "processed" / family
    count = 0
    byte_count = 0
    newest = None
    if root.exists():
        for directory, _subdirs, files in os.walk(root):
            for name in files:
                stat = (Path(directory) / name).stat()
                count += 1
                byte_count += stat.st_size
                newest = max(newest or stat.st_mtime_ns, stat.st_mtime_ns)
    return FamilyPresence(family, root.exists(), count, byte_count, newest)


def assert_payload_read_allowed(policy, *, stage, family, lane_id, path):
    item = next(entry for entry in policy["families"] if entry["family"] == family)
    access = item[f"payload_access_{stage}"]
    approved_lane = (
        access == "approved_processed_lane_only"
        and family == "swe-gym"
        and lane_id == "swe-gym-openhands-sampled"
        and "processed/swe-gym/openhands-sampled" in Path(path).as_posix().casefold()
    )
    identity_metadata = (
        access == "identity_metadata_only"
        and Path(path).as_posix().casefold().endswith(
            str(item["identity_metadata_relative_path"]).casefold()
        )
    )
    if not (approved_lane or identity_metadata):
        raise SuitePolicyError(f"{family} is metadata-only for stage {stage}")
```

The suite-report schema must require all ten entries, presence counts, `inspection="filesystem_metadata_only"`, `payload_opened=false`, and the first-stage exact lane list. Register it in `FOUNDATION_SCHEMA_FILES`.

- [ ] **Step 4: Run suite, schema, and registry tests**

```powershell
python -m pytest tests/test_foundation_suite.py tests/test_foundation_source_presence.py tests/test_foundation_data.py tests/test_dataset_readiness.py tests/test_foundation_schemas.py -q
```

Expected: all selected tests pass, including status-drift reporting when blocked bytes exist.

- [ ] **Step 5: Commit the suite policy**

```powershell
git add docs/data/training-readiness/pneuma-foundation-v0-suite.json schemas/foundation-suite-report.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/foundation/suite.py src/pneuma_lab/foundation/source_presence.py tests/test_foundation_suite.py tests/test_foundation_source_presence.py
git commit -m "feat: govern all ten foundation dataset families"
```

### Task 3: Identity normalization and complete contamination receipts

**Files:**
- Modify: `docs/data/training-readiness/pneuma-foundation-v0-suite.json`
- Create: `src/pneuma_lab/foundation/artifacts.py`
- Create: `src/pneuma_lab/foundation/eval_identities.py`
- Modify: `src/pneuma_lab/foundation/contamination.py`
- Modify: `src/pneuma_lab/foundation/data.py`
- Modify: `tests/test_foundation_contamination.py`
- Modify: `tests/test_foundation_data.py`
- Create: `tests/test_foundation_artifacts.py`

- [ ] **Step 1: Write failing nested-identity and missing-index tests**

```python
def test_contamination_receipt_detects_every_identity_dimension() -> None:
    training = [IdentityRecord("swe-gym", "swe-gym-openhands-sampled", "o/r", "1", "t1", "a", "b", "c", "d")]
    evaluation = [IdentityRecord("swe-bench", "swe-bench", "o/r", "9", "t9", "z", "y", "x", "w")]
    receipt = build_contamination_receipt(training, evaluation)
    assert receipt["finding_count"] == 1
    assert receipt["findings"][0]["dimensions"] == ["repository"]


def test_required_missing_eval_identity_index_fails(tmp_path: Path) -> None:
    with pytest.raises(ContaminationIndexError, match="swe-mera"):
        load_required_eval_identities(
            {"swe-bench": tmp_path / "swe-bench.jsonl"},
            required_families=("swe-bench", "swe-mera", "swe-polybench"),
        )


def test_atomic_json_and_jsonl_are_canonical(tmp_path: Path) -> None:
    json_path = tmp_path / "receipt.json"
    jsonl_path = tmp_path / "identities.jsonl"
    write_atomic_json(json_path, {"b": 2, "a": 1})
    write_atomic_jsonl(jsonl_path, ({"b": 2, "a": 1},))
    assert json_path.read_bytes() == b'{\n    "a": 1,\n    "b": 2\n}\n'
    assert jsonl_path.read_bytes() == b'{"a":1,"b":2}\n'
    assert sha256_file(jsonl_path) == hashlib.sha256(jsonl_path.read_bytes()).hexdigest()
```

- [ ] **Step 2: Run the focused tests and confirm failure**

```powershell
python -m pytest tests/test_foundation_artifacts.py tests/test_foundation_contamination.py tests/test_foundation_data.py -q
```

Expected: failure because `IdentityRecord`, nested extraction, and required-index enforcement do not exist.

- [ ] **Step 3: Implement normalized identities and receipt coverage**

```python
@dataclass(frozen=True)
class IdentityRecord:
    family: str
    lane_id: str
    repo: str | None
    issue_or_pr: str | None
    task_id: str | None
    base_commit: str | None
    patch_sha256: str | None
    test_patch_sha256: str | None
    fuzzy_text_sha256: str | None


def identity_from_foundation_record(record: Mapping) -> IdentityRecord:
    source = record["source"]
    identity = record["identity"]
    return IdentityRecord(
        family=source["dataset_family"],
        lane_id=source["lane_id"],
        repo=identity.get("repo"),
        issue_or_pr=identity.get("issue_or_pr"),
        task_id=identity.get("task_id"),
        base_commit=identity.get("base_commit"),
        patch_sha256=identity.get("patch_sha256"),
        test_patch_sha256=identity.get("test_patch_sha256"),
        fuzzy_text_sha256=identity.get("fuzzy_text_sha256"),
    )


IDENTITY_FIELDS = (
    "repo",
    "issue_or_pr",
    "task_id",
    "base_commit",
    "patch_sha256",
    "test_patch_sha256",
    "fuzzy_text_sha256",
)


def build_contamination_receipt(training, evaluation):
    training_values = tuple(training)
    evaluation_values = tuple(evaluation)
    findings = []
    for left in training_values:
        for right in evaluation_values:
            dimensions = [
                field for field in IDENTITY_FIELDS
                if getattr(left, field) is not None
                and getattr(left, field) == getattr(right, field)
            ]
            if dimensions:
                findings.append({
                    "training_lane": left.lane_id,
                    "evaluation_lane": right.lane_id,
                    "dimensions": dimensions,
                })
    return {
        "manifest_kind": "pneuma_foundation_contamination_receipt",
        "manifest_schema_version": "0.1.0",
        "training_count": len(training_values),
        "evaluation_count": len(evaluation_values),
        "finding_count": len(findings),
        "findings": findings,
        "repo_issue_disjoint": not findings,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_atomic_bytes(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_atomic_json(path: Path, value: Mapping) -> None:
    payload = (json.dumps(dict(value), indent=4, sort_keys=True) + "\n").encode("utf-8")
    write_atomic_bytes(path, payload)


def write_atomic_jsonl(path: Path, values: Iterable[Mapping]) -> None:
    payload = "".join(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n"
        for value in values
    ).encode("utf-8")
    write_atomic_bytes(path, payload)


def iter_eval_metadata_identities(path, *, family, allowed_fields):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            unknown = set(value) - set(allowed_fields) - {"lane_id"}
            if unknown:
                raise ContaminationIndexError(f"unexpected identity fields: {sorted(unknown)}")
            fields = {name: value.get(name) for name in IDENTITY_FIELDS}
            yield IdentityRecord(family=family, lane_id=value["lane_id"], **fields)


def load_required_eval_identities(paths, *, required_families):
    missing = sorted(set(required_families) - set(paths))
    if missing:
        raise ContaminationIndexError(f"missing required evaluation identity indexes: {missing}")
    return tuple(
        identity
        for family in required_families
        for identity in iter_eval_metadata_identities(
            paths[family],
            family=family,
            allowed_fields=frozenset(IDENTITY_FIELDS),
        )
    )


def build_eval_identity_index(*, source_path, output_path, family, lane_id, suite_policy):
    assert_payload_read_allowed(
        suite_policy,
        stage="100k",
        family=family,
        lane_id=lane_id,
        path=source_path,
    )
    identities = []
    with Path(source_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            task_id = str(value["source_id"])
            suffix = task_id.rsplit("-", 1)[-1]
            identities.append(IdentityRecord(
                family=family,
                lane_id=lane_id,
                repo=value.get("repo"),
                issue_or_pr=suffix if suffix.isdigit() else None,
                task_id=task_id,
                base_commit=value.get("base_commit"),
                patch_sha256=None,
                test_patch_sha256=None,
                fuzzy_text_sha256=None,
            ))
    write_atomic_jsonl(output_path, (asdict(identity) for identity in identities))
    return {
        "family": family,
        "lane_id": lane_id,
        "source_path": Path(source_path).as_posix(),
        "allowed_source_fields": ["source_id", "repo", "base_commit"],
        "identity_count": len(identities),
        "output_sha256": sha256_file(output_path),
    }
```

Place `sha256_file`, `write_atomic_bytes`, `write_atomic_json`, and `write_atomic_jsonl` in `artifacts.py`; import them into the other modules instead of copying private implementations.

Update `dedup_fingerprint()` and `build_diversity_inventory()` to read `record["identity"]`, `record["source"]`, `record["tokenization"]`, `record["observations"]`, and `record["forecast_targets"]`. Preserve hashes already prefixed with `sha256:` instead of hashing the digest text again. Build identity indexes only from the three exact `normalized_metadata.jsonl` paths committed in the suite policy, and retain only `source_id`, `repo`, and `base_commit`; never copy `source_file`, license prose, samples, patches, tests, or task text. Require identity indexes for `swe-bench`, `swe-mera`, and `swe-polybench`; report `swe-bench-pro` as blocked/unavailable rather than falsely disjoint.

- [ ] **Step 4: Run contamination and cross-dataset tests**

```powershell
python -m pytest tests/test_foundation_artifacts.py tests/test_foundation_contamination.py tests/test_foundation_data.py tests/test_cross_dataset_leakage.py -q
```

Expected: every repo, issue, task, commit, patch, test-patch, and fuzzy overlap case passes, and the existing seven-repository quarantine remains intact.

- [ ] **Step 5: Commit identity enforcement**

```powershell
git add docs/data/training-readiness/pneuma-foundation-v0-suite.json src/pneuma_lab/foundation/artifacts.py src/pneuma_lab/foundation/eval_identities.py src/pneuma_lab/foundation/contamination.py src/pneuma_lab/foundation/data.py tests/test_foundation_artifacts.py tests/test_foundation_contamination.py tests/test_foundation_data.py
git commit -m "feat: enforce foundation identity disjointness"
```

### Task 4: Deterministic 100K preparation and conservative license receipt

**Files:**
- Create: `docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json`
- Create: `src/pneuma_lab/foundation/preparation.py`
- Create: `tests/test_foundation_preparation.py`
- Modify: `tests/test_foundation_data.py`

- [ ] **Step 1: Write failing deterministic-preparation tests**

```python
def test_prepare_100k_is_repeatable_and_never_exceeds_ceiling(tmp_path, tokenizer) -> None:
    request = _preparation_request(tmp_path, stage="100k")
    first = prepare_stage(request, tokenizer=tokenizer)
    first_bytes = first.shard_path.read_bytes()
    second = prepare_stage(request, tokenizer=tokenizer)
    assert second.shard_path.read_bytes() == first_bytes
    manifest = json.loads(second.shard_manifest_path.read_text(encoding="utf-8"))
    assert manifest["inventory"]["token_count"] <= 100_000
    assert manifest["inventory"]["labels"]["resolved"] > 0
    assert manifest["inventory"]["labels"]["unresolved"] > 0
    assert all(json.loads(line)["training_weight"] == 0.0 for line in first_bytes.decode().splitlines())


def test_prepare_has_no_training_dependency_imports() -> None:
    source = inspect.getsource(preparation)
    assert "foundation.optimizer" not in source
    assert "foundation.runner" not in source
    assert "load_local_qwen" not in source
```

- [ ] **Step 2: Run the focused test and confirm failure**

```powershell
python -m pytest tests/test_foundation_preparation.py tests/test_foundation_data.py -q
```

Expected: collection fails because `preparation.py` does not exist.

- [ ] **Step 3: Implement restartable preparation and receipts**

Use these public contracts:

```python
@dataclass(frozen=True)
class PreparationRequest:
    stage: str
    repo_root: Path
    data_root: Path
    tokenizer_snapshot: Path
    output_root: Path
    seed: int = 20260713
    dry_run: bool = False


@dataclass(frozen=True)
class PreparationResult:
    preparation_manifest_path: Path
    suite_report_path: Path
    license_receipt_path: Path
    source_presence_receipt_path: Path
    source_integrity_receipt_path: Path
    shard_path: Path
    shard_manifest_path: Path
    split_receipt_path: Path
    contamination_receipt_path: Path
    diversity_receipt_path: Path
    selection_receipt_path: Path


STAGE_TOKEN_CEILINGS = {
    "100k": 100_000,
    "500k": 500_000,
    "1m": 1_000_000,
    "2m": 2_000_000,
    "8m": 8_000_000,
    "16m": 16_000_000,
    "32m": 32_000_000,
}


def deterministic_split(repo: str) -> str:
    bucket = int(hashlib.sha256(repo.casefold().encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "held_out"


def select_complete_records(records, *, token_ceiling):
    ordered = sorted(records, key=lambda item: item["record_id"])
    resolved = next(
        (record for record in ordered if record["observations"]["labels"]["resolved"] is True),
        None,
    )
    unresolved = next(
        (record for record in ordered if record["observations"]["labels"]["resolved"] is False),
        None,
    )
    if resolved is None or unresolved is None:
        raise PreparationError("stage source must contain resolved and unresolved examples")
    selected = [resolved, unresolved]
    selected_ids = {resolved["record_id"], unresolved["record_id"]}
    tokens = sum(int(record["tokenization"]["total_tokens"]) for record in selected)
    if tokens > token_ceiling:
        raise PreparationError("label anchors exceed stage token ceiling")
    for record in ordered:
        if record["record_id"] in selected_ids:
            continue
        count = int(record["tokenization"]["total_tokens"])
        if tokens + count > token_ceiling:
            continue
        selected.append(record)
        tokens += count
    if not selected:
        raise PreparationError("stage selection produced no records")
    labels = {record["observations"]["labels"]["resolved"] for record in selected}
    if labels != {False, True}:
        raise PreparationError("stage selection must contain resolved and unresolved examples")
    return selected
```

`prepare_stage()` must, in order: validate the registry and suite; collect metadata-only presence for all ten; call `assert_payload_read_allowed()` before opening the processed OpenHands traces and adapter report; verify or run `run_full_conversion()` into `build/training_examples/openhands-sampled/full/`; hash the conversion report, conversion hash manifest, and committed license receipt and pass those digests as `source_receipt_hashes`; render records; join repo-grouped splits; select complete train records; build required eval identity indexes; produce a zero-finding contamination receipt; write the content-addressed shard; and write source before/after, suite, split, contamination, diversity, and selection receipts. A temporary or partial output is replaced atomically only after its content hash is known. Task 5 adds candidate generation after all preparation receipts are stable.

The license receipt must state:

```json
{
    "receipt_kind": "dataset_license_posture",
    "receipt_schema_version": "0.1.0",
    "dataset_id": "swe-gym-openhands-sampled",
    "artifact_card_license_declared": false,
    "upstream_code_license": "Apache-2.0",
    "mirror_directory_license_observed": "MIT",
    "decision": "local_research_candidate_no_redistribution",
    "cloud_redistribution_allowed": false,
    "requires_exact_operator_authorization": true,
    "sources": [
        "https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories",
        "https://github.com/SWE-Gym/SWE-Gym",
        "https://huggingface.co/datasets/neulab/agent-data-collection/blob/main/swe-gym_openhands_sampled_trajectories/LICENSE"
    ]
}
```

This is a conservative project-use posture, not a legal opinion or a redistribution license.

- [ ] **Step 4: Run preparation tests twice and compare bytes**

```powershell
python -m pytest tests/test_foundation_preparation.py tests/test_foundation_data.py -q
```

Expected: all tests pass, including restart-after-partial-output, source before/after equality, blocked-lane denial before writes, and byte-identical repetition.

- [ ] **Step 5: Commit deterministic preparation**

```powershell
git add docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json src/pneuma_lab/foundation/preparation.py tests/test_foundation_preparation.py tests/test_foundation_data.py
git commit -m "feat: prepare deterministic foundation smoke shards"
```

### Task 5: Exact lane-level operator authorization

**Files:**
- Modify: `schemas/foundation-training-authorization.schema.json`
- Modify: `src/pneuma_lab/foundation/authorization.py`
- Modify: `src/pneuma_lab/foundation/preparation.py`
- Modify: `tests/test_foundation_authorization.py`
- Modify: `tests/test_foundation_preparation.py`

- [ ] **Step 1: Write failing candidate/final separation tests**

```python
def test_candidate_cannot_authorize_and_finalization_is_exact(tmp_path: Path) -> None:
    candidate_path = _write_candidate(tmp_path)
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        verify_foundation_authorization(candidate_path, **_verify_args(tmp_path))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    digest = authorization_scope_digest(candidate["scope"])
    phrase = required_approval_phrase(candidate)
    final_path = tmp_path / "build/foundation/authorizations/final/100k.json"
    final = finalize_authorization(
        candidate_path,
        supplied_scope_digest=digest,
        supplied_approval_phrase=phrase,
        operator_id="student-operator",
        approved_at="2026-07-13T12:00:00Z",
        output_path=final_path,
    )
    assert final["authorization_status"] == "authorized"
    verified = verify_foundation_authorization(final_path, **_verify_args(tmp_path))
    assert verified.authorized_lane_weights == {"swe-gym-openhands-sampled": 1.0}


def test_family_permission_cannot_leak_to_swe_gym_sibling_lanes(tmp_path: Path) -> None:
    verified = _verified_authorization(tmp_path)
    assert apply_verified_authorization(_record("swe-gym-openhands-sampled"), verified).effective_weight == 1.0
    with pytest.raises(FoundationAuthorizationError, match="lane"):
        apply_verified_authorization(_record("swe-gym-openhands-verifier"), verified)
```

- [ ] **Step 2: Run authorization tests and confirm the old family-level format fails**

```powershell
python -m pytest tests/test_foundation_authorization.py tests/test_foundation_records.py -q
```

Expected: failure because the old schema has no `candidate`, nested `scope`, receipt hashes, or exact lane weights.

- [ ] **Step 3: Refactor the scope and add the deliberate approval handshake**

Use these exact public contracts:

```python
APPROVAL_PHRASE_PREFIX = "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE"


@dataclass(frozen=True)
class VerifiedFoundationAuthorization:
    model_key: str
    token_ceiling: int
    shard_path: Path
    shard_manifest_path: Path
    output_root: Path
    authorized_lane_weights: Mapping[str, float]
    scope_digest: str
    manifest: Mapping


def authorization_scope_digest(scope: Mapping) -> str:
    payload = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def required_approval_phrase(candidate: Mapping) -> str:
    digest = authorization_scope_digest(candidate["scope"])
    return f"{APPROVAL_PHRASE_PREFIX} {digest}"


def build_authorization_candidate(
    preparation: PreparationResult,
    *,
    repo_root: Path,
    code_commit: str,
    model_key: str = "2b",
) -> dict:
    spec = MODEL_SPECS[model_key]
    preparation_manifest = _load_json(preparation.preparation_manifest_path)
    stage = preparation_manifest["stage"]
    receipt_paths = {
        "preparation": preparation.preparation_manifest_path,
        "suite": preparation.suite_report_path,
        "license": preparation.license_receipt_path,
        "source_presence": preparation.source_presence_receipt_path,
        "source_integrity": preparation.source_integrity_receipt_path,
        "split": preparation.split_receipt_path,
        "contamination": preparation.contamination_receipt_path,
        "diversity": preparation.diversity_receipt_path,
        "selection": preparation.selection_receipt_path,
    }
    scope = {
        "model": {"key": model_key, "model_id": spec.model_id, "revision": spec.revision},
        "tokenizer": {"model_id": spec.model_id, "revision": spec.revision},
        "stage": stage,
        "execution_profile": "local",
        "token_ceiling": int(preparation_manifest["token_ceiling"]),
        "allowed_learning_rates": [0.00005, 0.0001, 0.0002],
        "code_commit": code_commit,
        "shard": artifact_binding(preparation.shard_path, repo_root=repo_root),
        "shard_manifest": artifact_binding(preparation.shard_manifest_path, repo_root=repo_root),
        "receipts": {
            name: artifact_binding(path, repo_root=repo_root)
            for name, path in sorted(receipt_paths.items())
        },
        "authorized_lane_weights": {"swe-gym-openhands-sampled": 1.0},
        "source_data_policy": {
            "root": preparation_manifest["source_root"],
            "write_allowed": False,
            "private_cloud_transfer_allowed": False,
        },
        "output_root": "build/foundation/runs/",
        "budget": {
            "paid_compute_usd": 0,
            "cloud_jobs_used": 0,
            "paid_compute_ceiling_usd": 0,
            "cloud_job_ceiling": 0,
            "cloud_lifetime_cap_usd": 45,
        },
    }
    candidate = {
        "manifest_kind": "pneuma_foundation_training_authorization",
        "manifest_schema_version": "0.2.0",
        "authorization_status": "candidate",
        "scope": scope,
        "operator_approval": None,
    }
    path = repo_root / f"build/foundation/authorizations/candidates/{stage}.json"
    write_atomic_json(path, candidate)
    return candidate


def artifact_binding(path: Path, *, repo_root: Path) -> dict:
    resolved = Path(path).resolve()
    root = Path(repo_root).resolve()
    if root not in resolved.parents:
        raise FoundationAuthorizationError(f"artifact escapes repository: {resolved}")
    return {
        "path": resolved.relative_to(root).as_posix(),
        "sha256": sha256_file(resolved),
    }


def finalize_authorization(
    candidate_path,
    *,
    supplied_scope_digest,
    supplied_approval_phrase,
    operator_id,
    approved_at,
    output_path,
):
    candidate = _load_json(Path(candidate_path))
    if candidate["authorization_status"] != "candidate":
        raise FoundationAuthorizationError("only a candidate can be finalized")
    expected_digest = authorization_scope_digest(candidate["scope"])
    if supplied_scope_digest != expected_digest:
        raise FoundationAuthorizationError("supplied scope digest does not match")
    if supplied_approval_phrase != required_approval_phrase(candidate):
        raise FoundationAuthorizationError("approval phrase does not match exact scope")
    final = {
        **candidate,
        "authorization_status": "authorized",
        "operator_approval": {
            "operator_id": operator_id,
            "approved_at": approved_at,
            "scope_digest": expected_digest,
            "approval_phrase_sha256": hashlib.sha256(
                supplied_approval_phrase.encode("utf-8")
            ).hexdigest(),
        },
    }
    write_atomic_json(Path(output_path), final)
    return final
```

After the builder exists, update `prepare_stage()` to import `build_authorization_candidate` locally as its final operation and add `authorization_candidate_path` to `PreparationResult`. In `authorization.py`, import `PreparationResult` only under `TYPE_CHECKING`; this prevents a preparation/authorization import cycle. The preparation manifest carries the exact stage token ceiling consumed by the candidate builder. The schema version becomes `0.2.0`; statuses are `not_authorized`, `candidate`, and `authorized`. `scope` must bind model and tokenizer IDs/revisions, stage, execution profile, ceiling, clean code commit, shard and manifest hashes, suite/source/split/contamination/diversity/selection receipt hashes, `authorized_lane_weights`, source root/write policy, `private_cloud_transfer_allowed`, output root, and local/cloud budget. The first local authorization sets `execution_profile="local"` and `private_cloud_transfer_allowed=false`. The only allowed 100K weight map is `{"swe-gym-openhands-sampled": 1.0}`. Verification re-hashes every artifact and rejects a dirty/different commit, candidate status, sibling lane, old PneumaBrain authorization, any nonzero paid compute, or any cloud job.

Add this to `records.py`:

```python
def apply_verified_authorization(record, authorization):
    lane_id = record["source"]["lane_id"]
    weight = authorization.authorized_lane_weights.get(lane_id)
    if weight is None or weight <= 0.0:
        raise FoundationAuthorizationError(f"record lane is not authorized: {lane_id}")
    if record["training_weight"] != 0.0:
        raise FoundationAuthorizationError("persisted records must remain zero-weight")
    applicable = any(item["applicable"] for item in record["forecast_targets"].values())
    if not record["rendered"]["target_text"] or not applicable:
        raise FoundationAuthorizationError("positive effective record lacks supervised targets")
    return EffectiveTrainingRecord(record=record, effective_weight=float(weight))
```

- [ ] **Step 4: Run authorization, schema, and pending-template tests**

```powershell
python -m pytest tests/test_foundation_authorization.py tests/test_foundation_records.py tests/test_foundation_schemas.py -q
```

Expected: all tests pass; the committed pending template remains non-authorizing.

- [ ] **Step 5: Commit exact authorization**

```powershell
git add schemas/foundation-training-authorization.schema.json src/pneuma_lab/foundation/authorization.py src/pneuma_lab/foundation/preparation.py src/pneuma_lab/foundation/records.py tests/test_foundation_authorization.py tests/test_foundation_preparation.py tests/test_foundation_records.py tests/test_foundation_schemas.py
git commit -m "feat: require exact foundation run authorization"
```

### Task 6: Reproducible WSL2 Python 3.12 environment

**Files:**
- Modify: `pyproject.toml`
- Create: `uv.lock`
- Create: `.wslconfig.foundation.example`
- Create: `scripts/foundation/setup-linux.sh`
- Create: `scripts/foundation/setup-wsl.sh`
- Create: `src/pneuma_lab/foundation/environment.py`
- Modify: `src/pneuma_lab/foundation/doctor.py`
- Create: `tests/test_foundation_environment.py`
- Modify: `tests/test_foundation_doctor.py`

- [ ] **Step 1: Write failing environment and setup-safety tests**

```python
def test_doctor_requires_exact_python_312_and_usable_wsl_memory() -> None:
    probe = _ready_probe(python_version=(3, 14, 4), ram_gb=23.2)
    report = doctor_report(probe)
    assert "python_3_12_required" in report["blockers"]
    probe = _ready_probe(python_version=(3, 12, 11), ram_gb=23.2)
    assert doctor_report(probe)["ready"] is True


def test_cloud_doctor_requires_linux_a40_without_requiring_wsl() -> None:
    probe = _ready_probe(
        system="Linux",
        release="6.8.0-generic",
        gpu_name="NVIDIA A40",
        gpu_total_vram_gb=44.5,
        python_version=(3, 12, 11),
    )
    assert doctor_report(probe, profile="cloud")["ready"] is True
    assert "wsl2_required" in doctor_report(probe, profile="local")["blockers"]


def test_setup_script_cannot_authorize_or_train() -> None:
    script = (ROOT / "scripts/foundation/setup-wsl.sh").read_text(encoding="utf-8")
    script += (ROOT / "scripts/foundation/setup-linux.sh").read_text(encoding="utf-8")
    forbidden = ("authorization-finalize", " foundation train", " foundation resume")
    assert not any(value in script for value in forbidden)
    assert "https://astral.sh/uv/0.11.28/install.sh" in script
    assert "uv sync --python 3.12 --extra dev --extra foundation --locked" in script
```

- [ ] **Step 2: Run environment tests and confirm missing files and version checks**

```powershell
python -m pytest tests/test_foundation_environment.py tests/test_foundation_doctor.py -q
```

Expected: collection fails for `environment.py` and the old doctor accepts Python 3.14.

- [ ] **Step 3: Pin dependencies, generate the lock, and add safe setup files**

Replace the foundation extra with exact pins:

```toml
foundation = [
    "torch==2.13.0",
    "torchvision==0.28.0",
    "bitsandbytes==0.49.2",
    "accelerate==1.14.0",
    "peft==0.19.1",
    "psutil==7.2.2",
    "pillow==12.3.0",
    "safetensors==0.8.0",
    "huggingface-hub==1.23.0",
    "transformers @ git+https://github.com/huggingface/transformers.git@11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69",
]
```

Use this WSL configuration:

```ini
[wsl2]
memory=24GB
swap=8GB
processors=20
localhostForwarding=true
```

Use this shared Linux setup body:

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
profile="${1:-local}"
if [[ "$(uname -s)" != "Linux" ]] || [[ "$profile" != "local" && "$profile" != "cloud" ]]; then
    echo "BLOCKED: expected Linux and profile local or cloud" >&2
    exit 2
fi
if [[ "${repo_root,,}" == /mnt/c/pneuma-data* ]]; then
    echo "BLOCKED: repository cannot live under the immutable corpus root" >&2
    exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/0.11.28/install.sh | sh
fi
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if [[ "$(uv --version)" != "uv 0.11.28" ]]; then
    echo "BLOCKED: expected uv 0.11.28" >&2
    exit 2
fi
cd "$repo_root"
uv python install 3.12
uv sync --python 3.12 --extra dev --extra foundation --locked
uv run python -m pneuma_lab.foundation doctor --profile "$profile"
echo "SETUP COMPLETE; TRAINING HAS NOT STARTED"
```

Save that body as `scripts/foundation/setup-linux.sh`. Use this WSL-only wrapper as `scripts/foundation/setup-wsl.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

if ! grep -qi microsoft /proc/version; then
    echo "BLOCKED: this wrapper must run inside WSL2" >&2
    exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "$repo_root/scripts/foundation/setup-linux.sh" local
```

Generate and verify the lock inside WSL, not with Windows Python:

```powershell
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc '$HOME/.local/bin/uv lock --python 3.12 && $HOME/.local/bin/uv sync --python 3.12 --extra dev --extra foundation --locked'
```

Add these environment APIs:

```python
UV_VERSION = "0.11.28"
PYTHON_SERIES = (3, 12)
TRANSFORMERS_COMMIT = "11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69"
MIN_USABLE_WSL_RAM_GB = 22.0


def setup_plan(repo_root: Path) -> dict:
    return {
        "copy_wslconfig": "Copy-Item .wslconfig.foundation.example $HOME\\.wslconfig",
        "restart": "wsl --shutdown",
        "enter": "wsl -d Ubuntu",
        "repo": f"cd /mnt/{repo_root.drive[0].lower()}{repo_root.as_posix()[2:]}",
        "setup": "bash scripts/foundation/setup-wsl.sh",
        "training_started": False,
    }


def verify_lock(lock_path: Path) -> None:
    text = Path(lock_path).read_text(encoding="utf-8")
    required = (
        "2.13.0",
        "0.28.0",
        "0.49.2",
        "1.14.0",
        "0.19.1",
        TRANSFORMERS_COMMIT,
    )
    missing = [value for value in required if value not in text]
    if missing:
        raise EnvironmentError(f"foundation lock is missing pins: {missing}")
```

Change `doctor_report(probe, *, profile="local")` to require exactly Python 3.12, BF16 CUDA support, the pinned Transformers commit exposed through package metadata, bitsandbytes CUDA availability, SQLite FTS5, and the existing optional dependencies. The local profile additionally requires WSL2, at least 22.0 GiB visible RAM, and at least 7.5 GiB VRAM. The cloud profile requires generic Linux, an A40 48GB device, and at least 40 GiB visible VRAM. The local process ceilings remain 7.5 GiB VRAM and 24 GiB RAM.

- [ ] **Step 4: Run environment tests in Windows and WSL**

```powershell
python -m pytest tests/test_foundation_environment.py tests/test_foundation_doctor.py -q
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pytest tests/test_foundation_environment.py tests/test_foundation_doctor.py -q'
```

Expected: both selected suites pass; WSL doctor is allowed to remain `BLOCKED` until the operator has copied `.wslconfig.foundation.example`, run `wsl --shutdown`, and executed the setup script.

- [ ] **Step 5: Commit the reproducible environment**

```powershell
git add pyproject.toml uv.lock .wslconfig.foundation.example scripts/foundation/setup-linux.sh scripts/foundation/setup-wsl.sh src/pneuma_lab/foundation/environment.py src/pneuma_lab/foundation/doctor.py tests/test_foundation_environment.py tests/test_foundation_doctor.py
git commit -m "build: pin the foundation WSL environment"
```

### Task 7: Pinned 2B model cache and no-gradient dry run

**Files:**
- Create: `src/pneuma_lab/foundation/model_cache.py`
- Create: `src/pneuma_lab/foundation/dry_run.py`
- Modify: `src/pneuma_lab/foundation/runtime.py`
- Create: `tests/test_foundation_model_cache.py`
- Create: `tests/test_foundation_dry_run.py`
- Create: `tests/test_foundation_qwen_smoke.py`
- Modify: `tests/test_foundation_runtime.py`

- [ ] **Step 1: Write failing cache and no-optimizer tests**

```python
def test_cache_download_is_exactly_2b_and_writes_verified_receipt(tmp_path: Path) -> None:
    calls = []
    result = prepare_pinned_snapshot(
        "2b",
        cache_root=tmp_path,
        snapshot_download=lambda **kwargs: _fake_snapshot(tmp_path, calls, kwargs),
    )
    assert calls[0]["repo_id"] == "Qwen/Qwen3.5-2B"
    assert calls[0]["revision"] == "15852e8c16360a2fea060d615a32b45270f8a8fc"
    assert result.receipt_path.is_file()
    assert all(not path.is_symlink() for path in result.snapshot_path.rglob("*"))
    with pytest.raises(ModelCacheError, match="2B"):
        prepare_pinned_snapshot("4b", cache_root=tmp_path, snapshot_download=lambda **kwargs: None)


def test_dry_run_never_constructs_optimizer_or_gradients(fake_runtime, fake_tokenizer) -> None:
    optimizer_factory = Mock(side_effect=AssertionError("optimizer constructed"))
    report = run_no_gradient_dry_run(
        _dry_run_request(),
        runtime_loader=lambda **kwargs: fake_runtime,
        tokenizer_loader=lambda **kwargs: fake_tokenizer,
        optimizer_factory=optimizer_factory,
    )
    assert report["optimizer_constructed"] is False
    assert report["backward_called"] is False
    assert report["gradient_tensor_count"] == 0
    optimizer_factory.assert_not_called()
```

- [ ] **Step 2: Run tests and confirm missing cache/dry-run modules**

```powershell
python -m pytest tests/test_foundation_model_cache.py tests/test_foundation_dry_run.py tests/test_foundation_runtime.py -q
```

Expected: collection fails because the cache and dry-run modules do not exist.

- [ ] **Step 3: Implement an offline-verifiable local snapshot**

Use these contracts:

```python
@dataclass(frozen=True)
class CachedSnapshot:
    model_key: str
    snapshot_path: Path
    receipt_path: Path
    revision: str


def prepare_pinned_snapshot(model_key, *, cache_root, snapshot_download=None):
    if model_key != "2b":
        raise ModelCacheError("preparation may download only the pinned 2B model")
    spec = MODEL_SPECS[model_key]
    root = Path(cache_root).resolve() / "models" / model_key / spec.revision
    loader = snapshot_download or huggingface_hub.snapshot_download
    loader(
        repo_id=spec.model_id,
        revision=spec.revision,
        local_dir=root,
        allow_patterns=("*.json", "*.safetensors", "*.model", "*.txt", "*.tiktoken"),
    )
    files = []
    receipt_path = root / "pneuma-snapshot-receipt.json"
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path == receipt_path:
            continue
        if path.is_symlink():
            raise ModelCacheError(f"snapshot contains a symlink: {path}")
        files.append({
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    if not any(item["path"] == "config.json" for item in files):
        raise ModelCacheError("snapshot is missing config.json")
    receipt = {
        "receipt_kind": "pneuma_pinned_model_snapshot",
        "receipt_schema_version": "0.1.0",
        "model_id": spec.model_id,
        "revision": spec.revision,
        "files": files,
    }
    write_atomic_json(receipt_path, receipt)
    verify_pinned_snapshot(model_key, cache_root=cache_root)
    return CachedSnapshot(model_key, root, receipt_path, spec.revision)
```

`verify_pinned_snapshot()` must recompute every file hash, reject missing/extra symlinks, validate `config.json` through `validate_pinned_config()`, and set no network flags. Update `load_local_qwen()` to accept `snapshot_path: Path | None`; when supplied it passes the local path to all loaders with `local_files_only=True`, `HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1`.

The dry-run request and result are:

```python
@dataclass(frozen=True)
class DryRunRequest:
    model_key: str
    cache_root: Path
    output_root: Path
    stage: str


def run_no_gradient_dry_run(
    request,
    *,
    runtime_loader=load_local_qwen,
    tokenizer_loader=None,
    optimizer_factory=None,
):
    cached = verify_pinned_snapshot(request.model_key, cache_root=request.cache_root)
    tokenizer_loader = tokenizer_loader or AutoTokenizer.from_pretrained
    tokenizer = tokenizer_loader(cached.snapshot_path, local_files_only=True)
    with torch.inference_mode():
        runtime = runtime_loader(
            request.model_key,
            allow_download=False,
            vision=False,
            snapshot_path=cached.snapshot_path,
        )
        cases = build_required_cache_cases(tokenizer)
        reference_outputs = capture_case_outputs(runtime.model, cases)
        installed = install_junctions(runtime.model, runtime.architecture_plan)
        with CoreDisabled(installed):
            disabled_outputs = capture_case_outputs(runtime.model, cases)
        parity = compare_captured_outputs(reference_outputs, disabled_outputs)
        output = run_one_synthetic_forward(runtime.model, tokenizer)
    report = {
        "report_kind": "pneuma_foundation_no_gradient_dry_run",
        "model_revision": cached.revision,
        "parity": parity,
        "output_shape": list(output.logits.shape),
        "optimizer_constructed": False,
        "backward_called": False,
        "gradient_tensor_count": sum(
            parameter.grad is not None for parameter in runtime.model.parameters()
        ),
    }
    write_atomic_json(request.output_root / "dry-run-report.json", report)
    return report


def capture_case_outputs(model, cases):
    outputs = {}
    cache = None
    device = next(model.parameters()).device
    for name, boundary, model_inputs in cases:
        cache = cache_for_boundary(cache, boundary)
        prepared = {key: value.to(device) for key, value in model_inputs.items()}
        result = model(**prepared, past_key_values=cache, use_cache=True)
        outputs[name] = result.logits.detach().cpu()
        cache = result.past_key_values
    return outputs


def compare_captured_outputs(reference, modified):
    if set(reference) != set(modified):
        raise DryRunError("parity case sets differ")
    maximum = 0.0
    for name in sorted(reference):
        torch.testing.assert_close(reference[name], modified[name], atol=1e-5, rtol=1e-5)
        maximum = max(maximum, float((reference[name] - modified[name]).abs().max().item()))
    return {"case_names": sorted(reference), "max_absolute_error": maximum}


def build_required_cache_cases(tokenizer):
    values = (
        ("fresh", CacheBoundary.NEW_DOCUMENT, "Fix the failing local test."),
        ("cached", CacheBoundary.TOOL_TICK, "Inspect the next tool observation."),
        ("packed_reset", CacheBoundary.NEW_DOCUMENT, "Start a distinct repository task."),
        ("explicit_reset", CacheBoundary.EXPLICIT_RESET, "Reset all recurrent state."),
        ("continued", CacheBoundary.TOOL_TICK, "Continue only this tool tick."),
    )
    return tuple(
        (name, boundary, tokenizer(text, return_tensors="pt"))
        for name, boundary, text in values
    )


def run_one_synthetic_forward(model, tokenizer):
    device = next(model.parameters()).device
    inputs = {
        key: value.to(device)
        for key, value in tokenizer(
            "Predict whether this synthetic local action succeeds.",
            return_tensors="pt",
        ).items()
    }
    return model(**inputs, use_cache=False)
```

The real dry run covers fresh, cached, packed-reset, explicit reset, and deliberate tool-tick continuation parity. It uses one synthetic, non-corpus record and never calls the supplied optimizer factory. It verifies latent width 256, 64 active memory slots, two candidates, four total microsteps, and one layer-19 junction. After five warm-ups, time twenty disabled-core and twenty enabled-core forwards with CUDA synchronization, calculate p95, and fail if enabled p95 exceeds disabled p95 by more than 25%. Compute the analytic projection/core operation estimate from sequence length, hidden width, latent width, two candidates, four microsteps, and active memory slots; fail if estimated additional FLOPs exceed 20% of the measured base forward estimate.

- [ ] **Step 4: Run offline tests and the opt-in real smoke test when cache exists**

```powershell
python -m pytest tests/test_foundation_model_cache.py tests/test_foundation_dry_run.py tests/test_foundation_runtime.py -q
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pytest tests/test_foundation_qwen_smoke.py -q -m qwen_smoke'
```

Expected: unit tests pass. The opt-in smoke test skips with `pinned 2B snapshot is not cached` until Task 14 downloads it; after download it passes without gradients.

- [ ] **Step 5: Commit the cache and dry-run surfaces**

```powershell
git add src/pneuma_lab/foundation/model_cache.py src/pneuma_lab/foundation/dry_run.py src/pneuma_lab/foundation/runtime.py tests/test_foundation_model_cache.py tests/test_foundation_dry_run.py tests/test_foundation_runtime.py tests/test_foundation_qwen_smoke.py
git commit -m "feat: verify the pinned Qwen dry-run path"
```

### Task 8: Live telemetry and complete run manifests

**Files:**
- Modify: `schemas/foundation-run-manifest.schema.json`
- Modify: `src/pneuma_lab/foundation/resources.py`
- Create: `src/pneuma_lab/foundation/telemetry.py`
- Create: `src/pneuma_lab/foundation/run_manifest.py`
- Create: `tests/fixtures/foundation/nvidia-smi-sample.csv`
- Create: `tests/test_foundation_telemetry.py`
- Create: `tests/test_foundation_run_manifest.py`
- Modify: `tests/test_foundation_resources.py`
- Modify: `tests/test_foundation_schemas.py`

- [ ] **Step 1: Write failing parser, stop-path, and manifest tests**

```python
def test_nvidia_smi_parser_accepts_missing_power_and_throttle() -> None:
    sample = parse_nvidia_smi_line("3458, 4693, 81, [N/A], 92, Not Active")
    assert sample.global_vram_used_gb == pytest.approx(3458 / 1024)
    assert sample.global_vram_free_gb == pytest.approx(4693 / 1024)
    assert sample.power_watts is None
    assert sample.thermal_throttled is False


@pytest.mark.parametrize(
    ("sample", "action", "reason"),
    [
        (_sample(gpu_temp_c=86.0), "pause", "gpu_temperature"),
        (_sample(process_vram_gb=7.6), "pause", "vram"),
        (_sample(process_ram_gb=24.1), "pause", "ram"),
        (_sample(loss_finite=False), "fail", "non_finite_loss"),
        (_sample(disk_free_gb=1.0), "fail", "disk_risk"),
    ],
)
def test_resource_decisions_are_classified(sample, action, reason) -> None:
    decision = ResourceGuard().evaluate([sample])
    assert decision.action == action
    assert reason in decision.reasons
```

- [ ] **Step 2: Run telemetry tests and confirm missing types/schema fields**

```powershell
python -m pytest tests/test_foundation_telemetry.py tests/test_foundation_run_manifest.py tests/test_foundation_resources.py tests/test_foundation_schemas.py -q
```

Expected: failure because the sampler and expanded manifest do not exist.

- [ ] **Step 3: Implement bounded sampling, aggregation, and atomic run state**

Expand `ResourceSample` and `ResourceDecision`:

```python
@dataclass(frozen=True)
class ResourceSample:
    sampled_at: float
    gpu_temp_c: float
    thermal_throttled: bool
    process_vram_gb: float
    reserved_vram_gb: float
    global_vram_used_gb: float
    global_vram_free_gb: float
    process_ram_gb: float
    system_ram_gb: float
    gpu_utilization_percent: float
    tokens_per_second: float
    steps_per_second: float
    power_watts: float | None
    disk_free_gb: float
    loss_finite: bool = True


@dataclass(frozen=True)
class ResourceDecision:
    action: str
    reasons: tuple[str, ...]
```

Use this bounded sampler seam:

```python
NVIDIA_QUERY = (
    "memory.used,memory.free,temperature.gpu,power.draw,utilization.gpu,"
    "clocks_throttle_reasons.active"
)


class LiveResourceSampler:
    def __init__(self, *, output_root: Path, max_samples: int = 720):
        self.output_root = Path(output_root)
        self.samples = deque(maxlen=max_samples)

    def sample(self, *, tokens_per_second=0.0, steps_per_second=0.0, loss_finite=True):
        cuda = torch.cuda
        process = psutil.Process()
        global_sample = read_nvidia_smi(NVIDIA_QUERY)
        disk = shutil.disk_usage(self.output_root)
        value = ResourceSample(
            sampled_at=time.time(),
            gpu_temp_c=global_sample.gpu_temp_c,
            thermal_throttled=global_sample.thermal_throttled,
            process_vram_gb=cuda.memory_allocated() / 1024**3,
            reserved_vram_gb=cuda.memory_reserved() / 1024**3,
            global_vram_used_gb=global_sample.global_vram_used_gb,
            global_vram_free_gb=global_sample.global_vram_free_gb,
            process_ram_gb=process.memory_info().rss / 1024**3,
            system_ram_gb=psutil.virtual_memory().used / 1024**3,
            gpu_utilization_percent=global_sample.gpu_utilization_percent,
            tokens_per_second=tokens_per_second,
            steps_per_second=steps_per_second,
            power_watts=global_sample.power_watts,
            disk_free_gb=disk.free / 1024**3,
            loss_finite=loss_finite,
        )
        self.samples.append(value)
        return value
```

`ResourceGuard.evaluate(samples, *, authorization_unchanged=True, operator_interrupt=False, budget_ok=True, regression_ok=True, checkpoint_required_gb=0.0)` returns `pause` for temperature, sustained throttling, process VRAM, process RAM, and explicit signal; `fail` for non-finite loss, authorization drift, disk free below `checkpoint_required_gb + 2.0`, budget drift, and regression failure; otherwise `continue`.

The run-manifest schema version becomes `0.2.0` and requires: run/status/mode; model and tokenizer pins; authorization/scope/code/shard/receipt bindings; config, seed, learning rate and curriculum; progress; p50/p95 base/core latency; peak process/reserved/global VRAM, RAM, temperature, power and throttle intervals; validation metrics; checkpoint lineage; termination reason; structured report paths; and paid/cloud budget. `RunManifestWriter` atomically replaces `manifest.json` and appends one JSON object per line to `events.jsonl`.

- [ ] **Step 4: Run telemetry/resource/schema tests**

```powershell
python -m pytest tests/test_foundation_telemetry.py tests/test_foundation_run_manifest.py tests/test_foundation_resources.py tests/test_foundation_schemas.py -q
```

Expected: all selected tests pass with the recorded `nvidia-smi` fixture and missing-power case.

- [ ] **Step 5: Commit telemetry and run-state contracts**

```powershell
git add schemas/foundation-run-manifest.schema.json src/pneuma_lab/foundation/resources.py src/pneuma_lab/foundation/telemetry.py src/pneuma_lab/foundation/run_manifest.py tests/fixtures/foundation/nvidia-smi-sample.csv tests/test_foundation_telemetry.py tests/test_foundation_run_manifest.py tests/test_foundation_resources.py tests/test_foundation_schemas.py
git commit -m "feat: record foundation runtime telemetry"
```

### Task 9: Exact optimizer-boundary checkpoint and resume

**Files:**
- Modify: `src/pneuma_lab/foundation/checkpoints.py`
- Modify: `tests/test_foundation_checkpoint.py`
- Create: `tests/test_foundation_exact_resume.py`

- [ ] **Step 1: Write the failing uninterrupted-versus-resumed equality test**

```python
def test_interrupted_and_resumed_fake_training_are_exactly_equal(tmp_path: Path) -> None:
    uninterrupted = run_fake_training(seed=17, steps=8)
    first_half = run_fake_training(seed=17, steps=4, checkpoint_root=tmp_path)
    resumed = run_fake_training(
        seed=999,
        steps=8,
        checkpoint_root=tmp_path,
        resume_from=first_half.checkpoint,
    )
    assert_state_dict_equal(uninterrupted.trainable_state, resumed.trainable_state)
    assert_nested_equal(uninterrupted.optimizer_state, resumed.optimizer_state)
    assert_nested_equal(uninterrupted.scheduler_state, resumed.scheduler_state)
    assert uninterrupted.progress == resumed.progress
    assert uninterrupted.metrics == resumed.metrics
```

Add separate tests that the schedule requests a checkpoint every 500 optimizer steps or 1,800 seconds, whichever comes first; a time request waits for the next optimizer boundary; pending gradients reject a save; and changed authorization/model/shard/code/optimizer/curriculum bindings reject resume.

- [ ] **Step 2: Run checkpoint tests and confirm the `0.1.0` format is insufficient**

```powershell
python -m pytest tests/test_foundation_checkpoint.py tests/test_foundation_exact_resume.py -q
```

Expected: failure because scheduler, cursor, bindings, recurrent state, telemetry, and lineage are not restored.

- [ ] **Step 3: Introduce checkpoint format `0.2.0` and safe-boundary validation**

Use these exact state types:

```python
@dataclass(frozen=True)
class ResumeBindings:
    authorization_digest: str
    model_revision: str
    tokenizer_revision: str
    shard_hashes: tuple[str, ...]
    code_commit: str
    optimizer_definition: str
    curriculum_digest: str


@dataclass(frozen=True)
class TrainingProgress:
    epoch: int
    sampler_seed: int
    dataset_cursor: int
    microbatch: int
    optimizer_step: int
    tokens_seen: int
    selected_learning_rate: float


def assert_safe_boundary(parameters, *, microbatch, gradient_accumulation):
    if microbatch % gradient_accumulation != 0:
        raise CheckpointError("checkpoint requested outside optimizer boundary")
    if any(parameter.grad is not None for parameter in parameters):
        raise CheckpointError("safe-boundary checkpoint requires cleared gradients")
```

Change `CheckpointManager.save()` to accept `trainable_modules`, `optimizer`, `scheduler`, `progress`, `bindings`, `recurrent_state`, `active_memory`, `telemetry_state`, `best_validation`, `lineage`, `termination_reason`, and `gradient_accumulation`. Save only the shared core once, each projection shell without the shared-core prefix, and permitted LoRA keys; never serialize frozen Qwen weights. Save CPU and all CUDA RNG states. `load()` verifies expected bindings before mutating any object, restores optimizer tensors onto their parameter devices, restores sampler/cursor/telemetry/recurrent state, and returns a structured `RestoredCheckpoint`.

Retain the last three safe checkpoints plus the named best validation checkpoint. Store `metric_name` and `higher_is_better` instead of assuming higher is universally better.

- [ ] **Step 4: Run exact-resume and retention tests**

```powershell
python -m pytest tests/test_foundation_checkpoint.py tests/test_foundation_exact_resume.py -q
```

Expected: uninterrupted and interrupted/resumed fake runs are bit-for-bit equal in trainable weights, optimizer/scheduler state, cursor, and metrics.

- [ ] **Step 5: Commit exact resume support**

```powershell
git add src/pneuma_lab/foundation/checkpoints.py tests/test_foundation_checkpoint.py tests/test_foundation_exact_resume.py
git commit -m "feat: make foundation resume exact"
```

### Task 10: Hash-verifying dataset, single-document collator, and weighted optimizer seam

**Files:**
- Create: `src/pneuma_lab/foundation/dataset.py`
- Modify: `src/pneuma_lab/foundation/optimizer.py`
- Create: `tests/test_foundation_dataset.py`
- Modify: `tests/test_foundation_optimizer.py`

- [ ] **Step 1: Write failing dataset-boundary and effective-weight tests**

```python
def test_collator_masks_prompt_and_preserves_one_document(tokenizer) -> None:
    batch = FoundationCollator(tokenizer, sequence_length=512)([_effective_record()])
    assert batch.document_count == 1
    assert batch.input_ids.shape[0] == 1
    assert (batch.labels[0, : batch.prompt_length] == -100).all()
    assert batch.forecast_masks["action_success"].item() is True


def test_dataset_rejects_shard_hash_change(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    shard.write_text(shard.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(FoundationDatasetError, match="hash"):
        FoundationShardDataset(shard, manifest)


def test_optimizer_uses_mask_and_authorized_effective_weight() -> None:
    loop, model = _optimizer_loop()
    step = loop.train_microbatch(
        model_inputs={"hidden": torch.randn(1, 3, 16)},
        forecast_targets=_targets(),
        forecast_masks=_masks(action_success=True),
        effective_weight=torch.tensor([1.0]),
        document_count=1,
    )
    assert model.forward_calls == 1
    assert step.forecast_loss >= 0.0
```

- [ ] **Step 2: Run dataset/optimizer tests and confirm missing collator and signature**

```powershell
python -m pytest tests/test_foundation_dataset.py tests/test_foundation_optimizer.py -q
```

Expected: collection fails for `dataset.py`, and the optimizer lacks masks/effective weight.

- [ ] **Step 3: Implement deterministic reading, sampling, and one-record collation**

```python
@dataclass(frozen=True)
class FoundationBatch:
    input_ids: Tensor
    attention_mask: Tensor
    labels: Tensor
    forecast_targets: Mapping[str, Tensor]
    forecast_masks: Mapping[str, Tensor]
    effective_weight: Tensor
    token_count: int
    prompt_length: int
    document_count: int = 1


class FoundationShardDataset:
    def __init__(self, shard_path: Path, manifest_path: Path):
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if sha256_file(Path(shard_path)) != manifest["sha256"]:
            raise FoundationDatasetError("shard hash does not match manifest")
        self.records = tuple(
            json.loads(line) for line in Path(shard_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        return self.records[index]


class FoundationCollator:
    def __init__(self, tokenizer, *, sequence_length=512):
        self.tokenizer = tokenizer
        self.sequence_length = sequence_length

    def __call__(self, records):
        if len(records) != 1 or not isinstance(records[0], EffectiveTrainingRecord):
            raise FoundationDatasetError("each microbatch must contain one authorized document")
        effective = records[0]
        prompt = effective.record["rendered"]["prompt_text"]
        target = effective.record["rendered"]["target_text"]
        prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=True)
        target_ids = self.tokenizer.encode(target, add_special_tokens=False) + [self.tokenizer.eos_token_id]
        if len(target_ids) >= self.sequence_length:
            target_ids = target_ids[: self.sequence_length - 1] + [self.tokenizer.eos_token_id]
        prompt_ids = prompt_ids[: self.sequence_length - len(target_ids)]
        ids = prompt_ids + target_ids
        prompt_length = len(prompt_ids)
        labels = [-100] * prompt_length + ids[prompt_length:]
        targets, masks = forecast_tensors(effective.record)
        return FoundationBatch(
            input_ids=torch.tensor([ids]),
            attention_mask=torch.ones((1, len(ids)), dtype=torch.long),
            labels=torch.tensor([labels]),
            forecast_targets=targets,
            forecast_masks=masks,
            effective_weight=torch.tensor([effective.effective_weight]),
            token_count=len(ids),
            prompt_length=prompt_length,
        )
```

Add `DeterministicSampler(seed, epoch, cursor)` whose permutation is `random.Random(seed + epoch).shuffle(indices)` and whose cursor is checkpointed. Group microbatches into complete accumulation windows before starting a window; skip a window if its token sum would exceed the authorized ceiling, so the run never leaves pending gradients or exceeds the cap.

Update `FoundationOptimizerLoop.train_microbatch()` to accept masks and effective weight, reject nonpositive/nonfinite weights, reset shared state before the one base forward, compute masked forecast loss, multiply the combined loss by the single-record effective weight, and call `optimizer.step()` only at the configured boundary.

- [ ] **Step 4: Run dataset, optimizer, cache-boundary, and record tests**

```powershell
python -m pytest tests/test_foundation_dataset.py tests/test_foundation_optimizer.py tests/test_foundation_runtime.py tests/test_foundation_records.py -q
```

Expected: all selected tests pass; multi-document packing and unauthorized records fail before model forward.

- [ ] **Step 5: Commit the training input seam**

```powershell
git add src/pneuma_lab/foundation/dataset.py src/pneuma_lab/foundation/optimizer.py tests/test_foundation_dataset.py tests/test_foundation_optimizer.py
git commit -m "feat: add the authorized foundation data loader"
```

### Task 11: Integrated preflight, train, and resume runner

**Files:**
- Create: `src/pneuma_lab/foundation/runner.py`
- Modify: `src/pneuma_lab/foundation/training.py`
- Create: `tests/test_foundation_runner.py`
- Create: `tests/test_foundation_runner_failures.py`

- [ ] **Step 1: Write failing dependency-order and stop-path tests**

```python
def test_unauthorized_train_stops_before_cache_model_or_optimizer(tmp_path: Path) -> None:
    calls = []
    deps = _runner_dependencies(calls, authorization_error="not authorized")
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        run_foundation_training(_run_request(tmp_path), dependencies=deps)
    assert calls == ["verify_authorization"]


def test_preflight_never_loads_model_or_constructs_optimizer(tmp_path: Path) -> None:
    calls = []
    result = preflight_foundation_run(_run_request(tmp_path), dependencies=_runner_dependencies(calls))
    assert result.ready is True
    assert "load_model" not in calls
    assert "build_optimizer" not in calls


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("pause", "paused"), ("fail", "failed")],
)
def test_runner_stops_at_safe_boundary_and_checkpoints(decision, expected_status, tmp_path) -> None:
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(resource_action=decision),
    )
    assert result.status == expected_status
    assert result.last_checkpoint is not None
    assert result.progress.microbatch % 32 == 0
```

- [ ] **Step 2: Run runner tests and confirm the orchestration surface is missing**

```powershell
python -m pytest tests/test_foundation_runner.py tests/test_foundation_runner_failures.py -q
```

Expected: collection fails because `runner.py` does not exist.

- [ ] **Step 3: Implement preflight-first dependency-injected orchestration**

Use these request and result contracts:

```python
@dataclass(frozen=True)
class FoundationRunRequest:
    repo_root: Path
    authorization_path: Path
    registry_path: Path
    suite_path: Path
    cache_root: Path
    run_root: Path
    stage: str
    learning_rate: float
    execution_profile: str = "local"
    seed: int = 20260713
    checkpoint_path: Path | None = None


@dataclass(frozen=True)
class FoundationPreflightResult:
    ready: bool
    authorization: VerifiedFoundationAuthorization
    cache: CachedSnapshot
    environment: Mapping


@dataclass(frozen=True)
class FoundationRunResult:
    run_id: str
    status: str
    progress: TrainingProgress
    last_checkpoint: Path | None
    run_manifest_path: Path


@dataclass(frozen=True)
class RunnerDependencies:
    verify_authorization: Callable
    verify_cache: Callable
    environment_probe: Callable
    clean_commit: Callable
    tokenizer_loader: Callable
    model_loader: Callable
    junction_installer: Callable
    optimizer_builder: Callable
    scheduler_builder: Callable
    telemetry_factory: Callable
    clock: Callable


def assert_clean_commit(repo_root: Path, *, expected: str) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != expected or status:
        raise FoundationRunError("code commit is dirty or differs from authorization")


def default_runner_dependencies() -> RunnerDependencies:
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup

    def scheduler_builder(optimizer, token_ceiling):
        total_steps = max(1, token_ceiling // (512 * 32))
        warmup_steps = max(1, int(total_steps * 0.03))
        return get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    return RunnerDependencies(
        verify_authorization=verify_foundation_authorization,
        verify_cache=verify_pinned_snapshot,
        environment_probe=live_probe,
        clean_commit=assert_clean_commit,
        tokenizer_loader=AutoTokenizer.from_pretrained,
        model_loader=load_local_qwen,
        junction_installer=install_junctions,
        optimizer_builder=lambda parameters, lr: torch.optim.AdamW(parameters, lr=lr),
        scheduler_builder=scheduler_builder,
        telemetry_factory=LiveResourceSampler,
        clock=time.monotonic,
    )
```

Preflight order is exact and contains no allocation:

```python
def preflight_foundation_run(request, *, dependencies=None):
    dependencies = dependencies or default_runner_dependencies()
    authorization = dependencies.verify_authorization(
        request.authorization_path,
        repo_root=request.repo_root,
        registry_path=request.registry_path,
        suite_path=request.suite_path,
    )
    if authorization.manifest["scope"].get("execution_profile", "local") != request.execution_profile:
        raise FoundationRunError("execution profile differs from the authorized scope")
    validate_training_request(FoundationTrainingRequest(
        model_key=authorization.model_key,
        token_ceiling=authorization.token_ceiling,
    ))
    dependencies.clean_commit(
        request.repo_root,
        expected=authorization.manifest["scope"]["code_commit"],
    )
    cache = dependencies.verify_cache(
        authorization.model_key,
        cache_root=request.cache_root,
    )
    environment = doctor_report(
        dependencies.environment_probe(),
        profile=request.execution_profile,
    )
    if not environment["ready"]:
        raise FoundationRunError(f"environment is blocked: {environment['blockers']}")
    if request.learning_rate not in authorization.manifest["scope"]["allowed_learning_rates"]:
        raise FoundationRunError("learning rate is outside the approved scope")
    return FoundationPreflightResult(True, authorization, cache, environment)
```

After preflight, the real run must: set deterministic Python/CPU/CUDA seeds; set offline Hugging Face variables; load the tokenizer and 4-bit NF4/double-quantized model from the verified snapshot; call `prepare_model_for_kbit_training()`; freeze every base parameter; enable gradient checkpointing; set `model.config.use_cache=False`; install one validated layer-19 junction; cast the shared core and projection shells to BF16; assert trainable parameters are at most 25M; construct AdamW only over the shared core/projections/permitted LoRA; construct the persisted scheduler; create a microbatch-one DataLoader with eight workers; apply exact lane weights in memory; create complete 32-microbatch windows that stay under the token ceiling; reset DeltaNet/Pneuma state for each document; perform one base forward per microbatch; validate/sample/checkpoint only at safe boundaries; and atomically export only core/projection/LoRA state.

Use this guarded allocation order in `run_foundation_training()`:

```python
def run_foundation_training(request, *, dependencies=None):
    dependencies = dependencies or default_runner_dependencies()
    preflight = preflight_foundation_run(request, dependencies=dependencies)
    tokenizer = dependencies.tokenizer_loader(
        preflight.cache.snapshot_path,
        local_files_only=True,
    )
    runtime = dependencies.model_loader(
        preflight.authorization.model_key,
        allow_download=False,
        vision=False,
        snapshot_path=preflight.cache.snapshot_path,
    )
    configured = configure_quantized_training_model(runtime.model)
    installed = dependencies.junction_installer(configured, runtime.architecture_plan)
    optimizer = dependencies.optimizer_builder(
        unique_trainable_parameters(installed),
        lr=request.learning_rate,
    )
    scheduler = dependencies.scheduler_builder(optimizer, preflight.authorization.token_ceiling)
    return execute_safe_boundary_loop(
        request=request,
        preflight=preflight,
        tokenizer=tokenizer,
        runtime=runtime,
        installed=installed,
        optimizer=optimizer,
        scheduler=scheduler,
        dependencies=dependencies,
    )
```

`resume_foundation_training()` calls the same preflight first, constructs the same definitions, verifies all `ResumeBindings`, restores the checkpoint, and continues from the exact sampler cursor. Register SIGINT/SIGTERM as a pause request; the handler cannot write a checkpoint mid-accumulation. NaN/Inf, authorization drift, disk risk, or regression drift produces `failed`; thermal/memory/throttle/operator signal produces `paused`. Every termination gets a safe checkpoint and manifest reason.

- [ ] **Step 4: Run runner, exact-resume, optimizer, and resource tests**

```powershell
python -m pytest tests/test_foundation_runner.py tests/test_foundation_runner_failures.py tests/test_foundation_exact_resume.py tests/test_foundation_optimizer.py tests/test_foundation_resources.py -q
```

Expected: all selected tests pass with fake model/tokenizer seams; no real model allocation or optimizer step occurs in the test process outside fake fixtures.

- [ ] **Step 5: Commit the integrated runner**

```powershell
git add src/pneuma_lab/foundation/runner.py src/pneuma_lab/foundation/training.py tests/test_foundation_runner.py tests/test_foundation_runner_failures.py
git commit -m "feat: integrate the gated foundation runner"
```

### Task 12: Evaluation and claim-bounded reports

**Files:**
- Create: `src/pneuma_lab/foundation/evaluation.py`
- Create: `src/pneuma_lab/foundation/reports.py`
- Create: `tests/test_foundation_evaluation.py`
- Create: `tests/test_foundation_reports.py`
- Modify: `tests/test_foundation_claim_boundary.py`

- [ ] **Step 1: Write failing 100K and later-gate report tests**

```python
def test_100k_evaluation_is_smoke_only() -> None:
    report = evaluate_run(_completed_run(stage="100k"), validation_batches=_validation_batches())
    assert report["stage"] == "100k"
    assert report["falsification_gate"]["status"] == "not_applicable_before_2m"
    assert "validation_loss" in report["metrics"]


def test_reports_cannot_emit_level_or_consciousness_claims(tmp_path: Path) -> None:
    paths = materialize_reports(_run_manifest(), _evaluation_report(), output_root=tmp_path)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths.values()).casefold()
    for forbidden in ("level 5", "level 6", "is conscious", "phenomenal consciousness"):
        assert forbidden not in combined
```

- [ ] **Step 2: Run evaluation/report tests and confirm missing modules**

```powershell
python -m pytest tests/test_foundation_evaluation.py tests/test_foundation_reports.py tests/test_foundation_claim_boundary.py -q
```

Expected: collection fails because evaluation and report modules do not exist.

- [ ] **Step 3: Implement stage-aware evaluation and fixed report sections**

```python
def evaluate_run(run_manifest, *, validation_batches, variant_results=None):
    metrics = aggregate_validation_metrics(validation_batches)
    stage = run_manifest["curriculum"]["stage"]
    if stage in {"100k", "500k"}:
        gate = {"status": "not_applicable_before_2m", "decision": None}
    else:
        if variant_results is None:
            raise EvaluationError("2m and later evaluation requires four variant results")
        decision = evaluate_early_kill_gate(variant_results)
        gate = {
            "status": "passed" if decision.keep_recurrent_junction else "killed",
            "decision": asdict(decision),
        }
    return {
        "report_kind": "pneuma_foundation_evaluation",
        "report_schema_version": "0.1.0",
        "run_id": run_manifest["run_id"],
        "stage": stage,
        "metrics": metrics,
        "falsification_gate": gate,
    }


REPORT_SECTIONS = (
    "capability",
    "causal",
    "governance",
    "memory_integrity",
    "resource",
    "precautionary_welfare",
)
```

`materialize_reports()` writes one JSON report per fixed section and an index under `build/foundation/runs/<run-id>/reports/`. It imports neither the legacy scorer nor consciousness levels. The 100K report covers validation loss, forecast metrics, parity, throughput, p95 latency overhead, estimated FLOPs overhead, resume integrity, resources, denied action classes, memory integrity, and explicit `no_consciousness_claim`. It fails the regression section above 25% p95 latency or 20% estimated additional FLOPs. Across the three 100K learning-rate runs, call the existing `select_learning_rate()` with stability and validation metrics; ties select the lower rate. For 8M and later, call `next_token_stage()` and allow 16M or 32M only when the preceding doubling improves held-out resolved rate by at least 0.5 absolute points; saturation, instability, or a regression gate returns no next stage. At 2M and later, consume four repo-disjoint variant-result files and pass them to the existing early kill gate.

- [ ] **Step 4: Run report, falsification, and profile tests**

```powershell
python -m pytest tests/test_foundation_evaluation.py tests/test_foundation_reports.py tests/test_foundation_claim_boundary.py tests/test_foundation_falsification.py tests/test_foundation_profiles.py -q
```

Expected: all selected tests pass and no foundation/runtime package imports a legacy level scorer.

- [ ] **Step 5: Commit evaluation and reports**

```powershell
git add src/pneuma_lab/foundation/evaluation.py src/pneuma_lab/foundation/reports.py tests/test_foundation_evaluation.py tests/test_foundation_reports.py tests/test_foundation_claim_boundary.py
git commit -m "feat: add claim-bounded foundation reports"
```

### Task 13: Complete CLI with strict command separation

**Files:**
- Create: `src/pneuma_lab/foundation/cli.py`
- Modify: `src/pneuma_lab/foundation/__main__.py`
- Create: `tests/test_foundation_cli.py`

- [ ] **Step 1: Write failing CLI surface and no-fall-through tests**

```python
REQUIRED_COMMANDS = {
    "doctor",
    "duration",
    "setup-plan",
    "prepare",
    "preflight",
    "download-model",
    "dry-run",
    "authorization-candidate",
    "authorization-finalize",
    "train",
    "resume",
    "evaluate",
    "report",
    "cloud-bundle",
}


def test_cli_exposes_every_documented_command() -> None:
    help_text = _parser().format_help()
    assert REQUIRED_COMMANDS.issubset(set(_subcommand_names(_parser())))
    assert "397b" not in help_text.casefold()


def test_prepare_and_dry_run_cannot_fall_through_to_train(tmp_path: Path) -> None:
    calls = []
    handlers = _handlers(calls)
    assert main(["prepare", "--stage", "100k", "--data-root", str(tmp_path)], handlers=handlers) == 0
    assert main(["dry-run", "--stage", "100k"], handlers=handlers) == 0
    assert calls == ["prepare", "dry_run"]
```

- [ ] **Step 2: Run CLI tests and confirm only doctor/duration exist**

```powershell
python -m pytest tests/test_foundation_cli.py tests/test_foundation_doctor.py -q
```

Expected: required-command test fails because the existing CLI has only `doctor` and `duration`.

- [ ] **Step 3: Add lazy handlers and all exact commands**

Use an injectable handler boundary:

```python
@dataclass(frozen=True)
class CommandHandlers:
    doctor: Callable
    setup_plan: Callable
    prepare: Callable
    preflight: Callable
    download_model: Callable
    dry_run: Callable
    authorization_candidate: Callable
    authorization_finalize: Callable
    train: Callable
    resume: Callable
    evaluate: Callable
    report: Callable
    cloud_bundle: Callable


def main(argv=None, *, handlers=None):
    args = _parser().parse_args(argv)
    handlers = handlers or default_handlers()
    if args.command == "duration":
        print(f"{args.tokens} tokens at {args.tps:g} tokens/s: {duration_hours(args.tokens, args.tps):.2f} hours")
        return 0
    handler = getattr(handlers, args.command.replace("-", "_"))
    try:
        result = handler(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    render_command_result(result, as_json=getattr(args, "as_json", False))
    return 0
```

The parser must define these exact required arguments:

```text
doctor [--profile {local,cloud}] [--json]
setup-plan [--json]
prepare --stage {100k,500k,2m,8m,16m,32m} --data-root PATH [--cache-root PATH] [--dry-run] [--json]
preflight --stage {100k,500k,2m,8m,16m,32m} --authorization PATH --lr {5e-5,1e-4,2e-4} [--profile {local,cloud}] [--json]
download-model --model 2b [--cache-root PATH] [--dry-run] [--json]
dry-run --stage 100k [--cache-root PATH] [--dry-run] [--json]
authorization-candidate --stage {100k,500k,2m,8m,16m,32m} [--profile {local,cloud}] [--local-authorization PATH] [--local-gate-report PATH] [--quoted-hourly-usd FLOAT] [--quoted-tax-inclusive-usd FLOAT] [--json]
authorization-finalize --candidate PATH --scope-digest HEX --approval-phrase TEXT --operator-id TEXT
train --stage {100k,500k,2m,8m,16m,32m} --authorization PATH --lr {5e-5,1e-4,2e-4} [--profile {local,cloud}]
resume --authorization PATH --checkpoint PATH [--profile {local,cloud}]
evaluate --run PATH [--variant-results PATH]
report --run PATH
cloud-bundle --stage {2m,8m} --authorization PATH --quoted-hourly-usd FLOAT --quoted-tax-inclusive-usd FLOAT [--dry-run]
```

`default_handlers()` performs imports inside each handler so `doctor`, `duration`, `setup-plan`, and `--help` work without torch. `preflight` calls only `preflight_foundation_run()`. `train` and `resume` have no shared call path with `prepare` or `dry-run`.

For `authorization-candidate --profile local`, the handler prints the candidate already emitted by `prepare`. For `--profile cloud`, it requires all four cloud-only arguments, calls `build_cloud_reproduction_candidate()`, and writes `build/foundation/authorizations/candidates/<stage>-cloud.json`. `authorization-finalize` derives `build/foundation/authorizations/final/<stage>.json` for local candidates and `<stage>-cloud.json` for cloud candidates; it never overwrites its input candidate.

Reduce `__main__.py` to:

```python
from pneuma_lab.foundation.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI/help/authorization tests**

```powershell
python -m pytest tests/test_foundation_cli.py tests/test_foundation_doctor.py tests/test_foundation_authorization.py tests/test_foundation_runner.py -q
python -m pneuma_lab.foundation --help
```

Expected: tests pass and help lists every required command without importing a model.

- [ ] **Step 5: Commit the CLI**

```powershell
git add src/pneuma_lab/foundation/cli.py src/pneuma_lab/foundation/__main__.py tests/test_foundation_cli.py
git commit -m "feat: expose the foundation training CLI"
```

### Task 14: Authorized-only cloud bundle and hard budget quote gate

**Files:**
- Create: `src/pneuma_lab/foundation/cloud_bundle.py`
- Modify: `src/pneuma_lab/foundation/budget.py`
- Modify: `src/pneuma_lab/foundation/authorization.py`
- Create: `tests/test_foundation_cloud_bundle.py`
- Modify: `tests/test_foundation_budget.py`
- Modify: `tests/test_foundation_authorization.py`

- [ ] **Step 1: Write failing raw-path and quote-cap tests**

```python
def test_cloud_bundle_rejects_raw_corpus_and_unapproved_transfer(tmp_path: Path) -> None:
    request = _bundle_request(tmp_path, source_paths=[tmp_path / "pneuma-data/raw/x"])
    with pytest.raises(CloudBundleError, match="raw corpus"):
        build_cloud_bundle(request)
    request = _bundle_request(tmp_path, cloud_transfer_allowed=False)
    with pytest.raises(CloudBundleError, match="transfer posture"):
        build_cloud_bundle(request)


def test_quote_gate_enforces_lifetime_tax_and_72_hour_caps() -> None:
    authorization = authorize_reproduction_quote(
        stage="2m",
        quoted_hourly_usd=0.44,
        quoted_tax_inclusive_usd=38.0,
        prepaid_credit_usd=38.0,
        auto_pay_enabled=False,
        termination_hours=72,
        measured_tokens_per_second=20.0,
        prior_lifetime_spend_usd=0.0,
    )
    assert authorization.allowed is True
    with pytest.raises(BudgetViolation, match="45"):
        authorize_reproduction_quote(
            stage="2m",
            quoted_hourly_usd=0.44,
            quoted_tax_inclusive_usd=45.01,
            prepaid_credit_usd=38.0,
            auto_pay_enabled=False,
            termination_hours=72,
            measured_tokens_per_second=20.0,
            prior_lifetime_spend_usd=0.0,
        )


def test_cloud_candidate_is_separate_and_binds_local_gates(tmp_path: Path) -> None:
    candidate = build_cloud_reproduction_candidate(
        _local_authorization(tmp_path),
        local_gate_report_path=_local_gate_report(tmp_path, passed=True),
        quote=_safe_quote(),
        output_path=tmp_path / "build/foundation/authorizations/candidates/2m-cloud.json",
        repo_root=tmp_path,
    )
    assert candidate["authorization_status"] == "candidate"
    assert candidate["scope"]["execution_profile"] == "cloud"
    assert candidate["scope"]["source_data_policy"]["private_cloud_transfer_allowed"] is True
    assert candidate["scope"]["local_gate_report"]["sha256"]
```

- [ ] **Step 2: Run cloud/budget tests and confirm missing bundle guard**

```powershell
python -m pytest tests/test_foundation_cloud_bundle.py tests/test_foundation_budget.py -q
```

Expected: collection fails because `cloud_bundle.py` does not exist.

- [ ] **Step 3: Implement a local tar builder and quote-only cloud authorization**

```python
@dataclass(frozen=True)
class CloudBundleRequest:
    repo_root: Path
    data_root: Path
    authorization_path: Path
    output_path: Path
    stage: str
    quote: CloudQuote
    dry_run: bool = False


def build_cloud_bundle(request: CloudBundleRequest) -> dict:
    verified = verify_foundation_authorization(
        request.authorization_path,
        repo_root=request.repo_root,
        registry_path=request.repo_root / "docs/data/training-readiness/dataset-registry.json",
        suite_path=request.repo_root / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
    )
    scope = verified.manifest["scope"]
    if not scope["source_data_policy"].get("private_cloud_transfer_allowed", False):
        raise CloudBundleError("authorization transfer posture does not allow a cloud shard copy")
    paths = authorized_bundle_paths(verified, repo_root=request.repo_root)
    data_root = request.data_root.resolve()
    for path in paths:
        resolved = path.resolve()
        if resolved == data_root or data_root in resolved.parents:
            raise CloudBundleError("raw corpus paths may never enter a cloud bundle")
        if "swe-chat" in resolved.as_posix().casefold() or "sec-bench-pro" in resolved.as_posix().casefold():
            raise CloudBundleError("blocked dataset content may never enter a cloud bundle")
    quote = authorize_reproduction_quote_from_request(request, verified)
    manifest = build_bundle_manifest(paths, authorization=verified, quote=quote)
    if not request.dry_run:
        write_reproducible_tar(request.output_path, paths, manifest)
    return manifest


def build_cloud_reproduction_candidate(
    local_authorization_path: Path,
    *,
    local_gate_report_path: Path,
    quote: CloudQuote,
    output_path: Path,
    repo_root: Path,
) -> dict:
    local = verify_foundation_authorization(
        local_authorization_path,
        repo_root=repo_root,
        registry_path=repo_root / "docs/data/training-readiness/dataset-registry.json",
        suite_path=repo_root / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
    )
    gate = _load_json(local_gate_report_path)
    if gate.get("local_gates_passed") is not True:
        raise CloudBundleError("cloud reproduction requires all local gates")
    cloud_scope = copy.deepcopy(local.manifest["scope"])
    cloud_scope["execution_profile"] = "cloud"
    cloud_scope["source_data_policy"]["root"] = "bundle://authorized-shard"
    cloud_scope["source_data_policy"]["private_cloud_transfer_allowed"] = True
    cloud_scope["local_gate_report"] = artifact_binding(
        local_gate_report_path,
        repo_root=repo_root,
    )
    cloud_scope["budget"] = {
        "paid_compute_usd": 0,
        "cloud_jobs_used": 0,
        "paid_compute_ceiling_usd": quote.tax_inclusive_usd,
        "cloud_job_ceiling": 1,
        "cloud_lifetime_cap_usd": 45,
    }
    candidate = {
        "manifest_kind": "pneuma_foundation_training_authorization",
        "manifest_schema_version": "0.2.0",
        "authorization_status": "candidate",
        "scope": cloud_scope,
        "operator_approval": None,
    }
    write_atomic_json(output_path, candidate)
    return candidate
```

The bundle contains: tracked source at the authorized clean commit, the final authorization, exact suite/license/split/leakage/diversity/selection receipts, the authorized content-addressed shard, its manifest, model-cache receipt but not model weights, dependency lock, and setup script. It contains no secrets, raw source paths, unapproved lane payloads, notebook, checkpoint, or Hugging Face cache.

`authorize_reproduction_quote()` enforces one lifetime cloud job, $45 tax-inclusive including prior spend, at most $38 prepaid credit, auto-pay false, 72-hour termination, 2M default, and for 8M at least 30.9 measured tokens/second plus all-in fit. It only validates a human-provided current quote; it never contacts RunPod or creates a Pod. A cloud candidate is separate from the local authorization, binds the passed local-gate report and quote, uses `execution_profile="cloud"`, and still requires the exact operator finalization handshake. If private transfer remains unapproved, the guide marks cloud reproduction skipped.

- [ ] **Step 4: Run cloud, budget, authorization, and path-policy tests**

```powershell
python -m pytest tests/test_foundation_cloud_bundle.py tests/test_foundation_budget.py tests/test_foundation_authorization.py tests/test_foundation_data.py -q
```

Expected: all selected tests pass; a dry-run lists only permitted files and makes no network call.

- [ ] **Step 5: Commit cloud safeguards**

```powershell
git add src/pneuma_lab/foundation/cloud_bundle.py src/pneuma_lab/foundation/budget.py src/pneuma_lab/foundation/authorization.py tests/test_foundation_cloud_bundle.py tests/test_foundation_budget.py tests/test_foundation_authorization.py
git commit -m "feat: guard the optional cloud reproduction bundle"
```

### Task 15: Marked operator guide, command drift checker, and canonical status

**Files:**
- Create: `START-HERE-TRAINING.md`
- Create: `src/pneuma_lab/foundation/operator_guide.py`
- Create: `tests/test_foundation_operator_guide.py`
- Modify: `docs/project-status.json`
- Modify: `schemas/project-status.schema.json`
- Modify: `docs/foundation/local-first-foundation.md`
- Modify: `tests/test_project_status.py`

- [ ] **Step 1: Write failing marker, command, and status-truth tests**

```python
def test_operator_guide_is_marked_and_last_action_is_train() -> None:
    text = (ROOT / "START-HERE-TRAINING.md").read_text(encoding="utf-8")
    assert text.startswith("# TRAINING HAS NOT STARTED")
    assert "No Jupyter notebook is required." in text
    checklist = [line for line in text.splitlines() if line.startswith("- [")]
    assert checklist[-1].startswith("- [ ] `python -m pneuma_lab.foundation train")


def test_guide_commands_match_cli() -> None:
    report = check_operator_guide(ROOT / "START-HERE-TRAINING.md", parser=_parser())
    assert report == {"valid": True, "unknown_commands": [], "missing_commands": []}


def test_project_status_keeps_training_unstarted() -> None:
    status = json.loads((ROOT / "docs/project-status.json").read_text(encoding="utf-8"))
    launch = status["foundation_training_launch"]
    assert launch["tooling"] == "implemented"
    assert launch["training_status"] == "not_started"
    assert launch["optimizer_steps"] == 0
```

- [ ] **Step 2: Run guide/status tests and confirm missing guide fields**

```powershell
python -m pytest tests/test_foundation_operator_guide.py tests/test_project_status.py -q
```

Expected: collection or assertions fail because the root guide and launch status fields do not exist.

- [ ] **Step 3: Write the exact operator runbook and checker**

The guide starts with:

```markdown
# TRAINING HAS NOT STARTED

This repository is being prepared for a local Qwen3.5-2B 100K-token smoke run.
No optimizer update has run. No cloud resource has been created. No Jupyter
notebook is required; local WSL2 and optional RunPod both use the same CLI.
```

It must contain these headings, in this order:

```text
1. What “all ten datasets” means
2. Current readiness and hard safety boundaries
3. Windows WSL2 memory setup
4. WSL Python 3.12 environment
5. Close GPU-heavy Windows applications
6. Download and verify only Qwen3.5-2B
7. Prepare the deterministic 100K shard
8. Review the exact authorization candidate
9. Finalize only the displayed digest
10. Run non-training preflight and no-gradient dry run
11. Start, monitor, interrupt, and resume training
12. Evaluate and report
13. Optional one-time RunPod reproduction
14. Common failures and exact recovery
15. Final operator checklist
```

Include the exact Windows commands:

```powershell
Copy-Item .wslconfig.foundation.example "$HOME\.wslconfig"
wsl --shutdown
wsl -d Ubuntu
```

Include the exact local WSL commands:

```bash
cd /mnt/c/pneuma-lab
bash scripts/foundation/setup-wsl.sh
source .venv/bin/activate
python -m pneuma_lab.foundation doctor
python -m pneuma_lab.foundation download-model --model 2b
python -m pneuma_lab.foundation prepare --stage 100k --data-root /mnt/c/pneuma-data
python -m pneuma_lab.foundation authorization-candidate --stage 100k
read -r -p "Paste the displayed scope digest: " PNEUMA_SCOPE_DIGEST
read -r -p "Paste the displayed approval phrase: " PNEUMA_APPROVAL_PHRASE
python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/100k.json --scope-digest "$PNEUMA_SCOPE_DIGEST" --approval-phrase "$PNEUMA_APPROVAL_PHRASE" --operator-id student-operator
python -m pneuma_lab.foundation preflight --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5
python -m pneuma_lab.foundation dry-run --stage 100k
```

`check_operator_guide()` permits the two shell variables only in the finalization sequence and verifies that the preceding paragraph tells the operator to paste the values printed by `authorization-candidate`. Empty input and values that differ from the candidate fail closed.

The launch/checkpoint/report commands are:

```bash
python -m pneuma_lab.foundation train --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5
read -r -p "Paste the run directory printed by train: " PNEUMA_RUN_PATH
read -r -p "Paste the checkpoint path printed by pause: " PNEUMA_CHECKPOINT_PATH
python -m pneuma_lab.foundation resume --authorization build/foundation/authorizations/final/100k.json --checkpoint "$PNEUMA_CHECKPOINT_PATH"
python -m pneuma_lab.foundation evaluate --run "$PNEUMA_RUN_PATH"
python -m pneuma_lab.foundation report --run "$PNEUMA_RUN_PATH"
```

The guide documents three LR runs (`5e-5`, `1e-4`, `2e-4`), expected output after each preparation command, checkpoint/log/report paths, 20 and 50 tokens/s duration tables, safe Ctrl+C pause, resume, temperature/memory/disk failures, source before/after receipt check, and `git diff -- C:/pneuma-data` being insufficient because the corpus is a separate non-repository root.

The RunPod section says: open <https://www.runpod.io/>, log into a personal RunPod account, and re-check the live On-Demand A40 48GB quote; one-time credit at most $38 with tax-inclusive checkout at most $45; auto-pay off; official PyTorch template; 30GB container and 80GB volume; 72-hour auto-termination; SSH plus `tmux`; no notebook upload; no raw corpus upload; download outputs before termination; stopped volume still bills. GitHub login is needed only if the repository cannot be cloned anonymously. A read-only Hugging Face token is optional only if anonymous public-model limits block the download. No dataset credential, gated-dataset acceptance, model API, hosted database, or recurring service is required. Secrets stay in provider secrets or process environment and never enter Git, bundles, logs, manifests, or notebooks. Link only the official pricing, billing, connection, pricing-model, and lifecycle pages from the approved design. If the exact authorization says private cloud transfer is false, the section says `SKIP CLOUD REPRODUCTION`.

When a separately finalized cloud authorization exists, the guide includes these exact local commands:

```bash
read -r -p "Paste the live hourly A40 quote: " RUNPOD_HOURLY_USD
read -r -p "Paste the tax-inclusive checkout total: " RUNPOD_TAX_TOTAL_USD
read -r -p "Paste the completed local-gate report path: " PNEUMA_LOCAL_GATE_REPORT
python -m pneuma_lab.foundation authorization-candidate --stage 2m --profile cloud --local-authorization build/foundation/authorizations/final/2m.json --local-gate-report "$PNEUMA_LOCAL_GATE_REPORT" --quoted-hourly-usd "$RUNPOD_HOURLY_USD" --quoted-tax-inclusive-usd "$RUNPOD_TAX_TOTAL_USD"
read -r -p "Paste the displayed cloud scope digest: " PNEUMA_CLOUD_SCOPE_DIGEST
read -r -p "Paste the displayed cloud approval phrase: " PNEUMA_CLOUD_APPROVAL_PHRASE
python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/2m-cloud.json --scope-digest "$PNEUMA_CLOUD_SCOPE_DIGEST" --approval-phrase "$PNEUMA_CLOUD_APPROVAL_PHRASE" --operator-id student-operator
python -m pneuma_lab.foundation cloud-bundle --stage 2m --authorization build/foundation/authorizations/final/2m-cloud.json --quoted-hourly-usd "$RUNPOD_HOURLY_USD" --quoted-tax-inclusive-usd "$RUNPOD_TAX_TOTAL_USD"
read -r -p "Paste the RunPod SSH host: " RUNPOD_SSH_HOST
read -r -p "Paste the RunPod SSH port: " RUNPOD_SSH_PORT
scp -P "$RUNPOD_SSH_PORT" build/foundation/cloud/pneuma-2m.tar "root@$RUNPOD_SSH_HOST:/workspace/"
scp -P "$RUNPOD_SSH_PORT" build/foundation/authorizations/final/2m-cloud.json "root@$RUNPOD_SSH_HOST:/workspace/"
ssh -p "$RUNPOD_SSH_PORT" "root@$RUNPOD_SSH_HOST"
```

On the Pod, the guide uses:

```bash
cd /workspace
mkdir -p pneuma-2m
tar -xf pneuma-2m.tar -C pneuma-2m
cd pneuma-2m
bash scripts/foundation/setup-linux.sh cloud
tmux new -s pneuma
uv run python -m pneuma_lab.foundation doctor --profile cloud
uv run python -m pneuma_lab.foundation download-model --model 2b
uv run python -m pneuma_lab.foundation preflight --stage 2m --profile cloud --authorization /workspace/2m-cloud.json --lr 5e-5
uv run python -m pneuma_lab.foundation train --stage 2m --profile cloud --authorization /workspace/2m-cloud.json --lr 5e-5
tar -czf /workspace/pneuma-results.tar.gz build/foundation/runs
```

After detaching from `tmux` with `Ctrl+B`, then `D`, the local result command is:

```bash
scp -P "$RUNPOD_SSH_PORT" "root@$RUNPOD_SSH_HOST:/workspace/pneuma-results.tar.gz" build/foundation/cloud/
```

The final UI steps are explicit: verify the result archive locally, click **Terminate Pod**, confirm termination, and confirm no stopped volume or running Pod remains. The guide warns that the planning quote is not an authorization; the operator must replace it with the live quote in the cloud candidate and bundle command.

Add canonical status fields:

```json
"foundation_training_launch": {
    "tooling": "implemented",
    "local_artifacts": "runtime_checked_not_committed",
    "model_cache_required": "qwen3.5-2b-pinned",
    "authorization_state": "exact_operator_authorization_required",
    "training_status": "not_started",
    "optimizer_steps": 0,
    "cloud_resources_created": 0,
    "paid_compute_usd": 0
}
```

The checker parses fenced `python -m pneuma_lab.foundation` commands, maps documented shell variables to syntactically valid fixture paths, digests, phrases, hosts, ports, and floats, and calls the real parser. It also verifies every required command appears once in an operational section and the actual train command is the last unchecked checklist item.

- [ ] **Step 4: Run guide, status, claim-boundary, and CLI tests**

```powershell
python -m pytest tests/test_foundation_operator_guide.py tests/test_project_status.py tests/test_foundation_claim_boundary.py tests/test_foundation_cli.py -q
python -m pneuma_lab.status --check
```

Expected: all selected tests and the canonical status checker pass.

- [ ] **Step 5: Commit the operator surface**

```powershell
git add START-HERE-TRAINING.md src/pneuma_lab/foundation/operator_guide.py tests/test_foundation_operator_guide.py docs/project-status.json schemas/project-status.schema.json docs/foundation/local-first-foundation.md tests/test_project_status.py
git commit -m "docs: add the foundation training operator guide"
```

### Task 16: Full verification and real preparation without training

**Files:**
- Create ignored artifacts only under: `build/foundation/`
- Do not modify: `C:\pneuma-data\**`
- Do not invoke: `train`, `resume`, any cloud command that creates a resource, or any optimizer operation

- [ ] **Step 1: Establish the clean-code and immutable-source baselines**

Run:

```powershell
git status --short --branch
python -m pneuma_lab.status --check
python -m pneuma_lab.dataset_readiness --check
python -m pneuma_lab.foundation setup-plan --json
```

Expected: clean feature branch, status/readiness pass, setup plan says `training_started: false`.

Create the metadata baseline without opening payloads:

```powershell
python -m pneuma_lab.foundation prepare --stage 100k --data-root C:/pneuma-data --dry-run --json
```

Expected: lists only `build/foundation/` writes, reports all ten families, and states `payload_opened=false` for SWE-Chat and SEC-Bench-Pro.

- [ ] **Step 2: Configure WSL memory manually, then install the pinned environment**

Do not overwrite an existing `%UserProfile%\.wslconfig` silently. Show its current contents; if it differs, ask the user before replacing it. After the reviewed copy:

```powershell
Copy-Item .wslconfig.foundation.example "$HOME\.wslconfig"
wsl --shutdown
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'bash scripts/foundation/setup-wsl.sh'
```

Expected: setup ends with `SETUP COMPLETE; TRAINING HAS NOT STARTED`, and WSL `doctor` reports `READY`.

- [ ] **Step 3: Download and verify the pinned 2B snapshot**

```powershell
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pneuma_lab.foundation download-model --model 2b'
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -m pneuma_lab.foundation dry-run --stage 100k'
```

Expected: the receipt binds revision `15852e8c16360a2fea060d615a32b45270f8a8fc`; dry run reports parity pass, zero gradients, no optimizer, VRAM/RAM/latency measurements, and `TRAINING HAS NOT STARTED`.

- [ ] **Step 4: Materialize the real 100K shard and verify deterministic replay**

```powershell
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pneuma_lab.foundation prepare --stage 100k --data-root /mnt/c/pneuma-data'
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pneuma_lab.foundation prepare --stage 100k --data-root /mnt/c/pneuma-data'
```

Expected: both runs print identical shard, manifest, split, contamination, diversity, selection, source-receipt, and candidate hashes; token count is at most 100K; all persisted weights are zero; only the approved processed OpenHands lane payload was opened; source before/after metadata is identical.

- [ ] **Step 5: Stop for exact human authorization**

Run only:

```powershell
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pneuma_lab.foundation authorization-candidate --stage 100k'
```

Expected: prints the exact scope, digest, and deliberate phrase. Report those values to the user and stop. Do not call `authorization-finalize` until the user supplies that exact digest and phrase back in a new message.

- [ ] **Step 6: After explicit user approval, finalize and run non-training preflight**

Read the exact values the user returns and pass them without transforming them:

```powershell
$scopeDigest = Read-Host "Paste the user-returned scope digest"
$approvalPhrase = Read-Host "Paste the user-returned exact approval phrase"
wsl.exe -d Ubuntu --cd /mnt/c/pneuma-lab -- env "PNEUMA_SCOPE_DIGEST=$scopeDigest" "PNEUMA_APPROVAL_PHRASE=$approvalPhrase" bash -lc 'uv run python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/100k.json --scope-digest "$PNEUMA_SCOPE_DIGEST" --approval-phrase "$PNEUMA_APPROVAL_PHRASE" --operator-id student-operator'
wsl -d Ubuntu --cd /mnt/c/pneuma-lab bash -lc 'uv run python -m pneuma_lab.foundation preflight --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5'
```

Expected: final authorization verifies every hash and exact lane; preflight reports `READY`, `model_allocated=false`, `optimizer_constructed=false`, and `optimizer_steps=0`.

- [ ] **Step 7: Run completion verification**

Use the `superpowers:verification-before-completion` skill, then run:

```powershell
python -m pytest tests/ -q
python -m pneuma_lab.status --check
python -m pneuma_lab.dataset_readiness --check
python -m pneuma_lab.foundation.operator_guide START-HERE-TRAINING.md
git diff --check
git status --short --branch
```

Inside WSL also run:

```bash
uv run python -m pneuma_lab.foundation preflight --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5
uv run python -m pytest tests/test_foundation_qwen_smoke.py -q -m qwen_smoke
uv run python -m pneuma_lab.foundation dry-run --stage 100k
```

Expected: full suite passes; status and dataset readiness pass; real cached Qwen no-gradient smoke passes; guide checker passes; no whitespace errors; no tracked changes remain beyond deliberate status/documentation updates; source before/after receipt matches; `training_status=not_started`; `optimizer_steps=0`; paid compute and cloud resources remain zero.

- [ ] **Step 8: Preserve the authorized clean commit**

Do not change or commit tracked files after the authorization candidate is built. Verify:

```powershell
git status --short --branch
git rev-parse HEAD
```

Expected: the tracked tree is clean and `HEAD` equals the code commit inside the final authorization. If a tracked correction is required, make and commit it, then rerun preparation, candidate review, user approval, finalization, and preflight. Do not add `build/foundation/`, the model cache, final local authorization, secrets, raw paths, or machine-specific receipts to Git.

## Implementation stop points

1. Stop before replacing an existing user `.wslconfig` whose contents differ from the reviewed example.
2. Stop after printing the real authorization candidate digest and phrase. Exact operator approval is required in a new user message.
3. Stop if the OpenHands license posture cannot remain local-only and non-redistributed within the operator-approved scope.
4. Skip optional cloud reproduction if the live quote, tax, transfer posture, 72-hour duration, or lifetime spend gate fails.
5. Never cross the final unchecked `train` command during preparation implementation.

## Completion evidence checklist

- [ ] Every new schema validates and is registered.
- [ ] All ten families appear once with coherent roles.
- [ ] SWE-Chat and SEC-Bench-Pro remain metadata-only and zero-weight.
- [ ] The 100K persisted shard is deterministic, content-addressed, and zero-weight.
- [ ] Exact authorized weight applies only to `swe-gym-openhands-sampled` in memory.
- [ ] Candidate/final authorization files are separate and byte changes invalidate the final scope.
- [ ] WSL uses Python 3.12 and the committed lock.
- [ ] Only pinned Qwen3.5-2B is cached; 397B is neither downloaded nor loadable.
- [ ] Real dry run has parity, one synthetic forward, zero gradients, and no optimizer.
- [ ] Checkpoint/resume equality passes for the fake integrated run.
- [ ] Thermal, memory, signal, NaN, disk, budget, and regression paths are tested.
- [ ] `START-HERE-TRAINING.md` commands parse against the real CLI.
- [ ] Full pytest, status, readiness, preflight, guide, Qwen smoke, and whitespace checks pass.
- [ ] `C:\pneuma-data` before/after metadata matches.
- [ ] Training is still `not_started`, optimizer steps are zero, cloud resources are zero, and paid compute is $0.
