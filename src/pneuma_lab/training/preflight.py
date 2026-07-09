"""Fail-closed authorization gates for the legacy E1/E2 estimator trainer.

This module does not authorize a run by itself.  It verifies that a requested
run is exactly described by a schema-valid manifest and by a separately
reviewed, Git-tracked authorization artifact.  Source bytes, split semantics,
trainer constants, and the repo-local output root are all bound before fitting.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator

from pneuma_lab.estimators import features
from pneuma_lab.estimators import logistic
from pneuma_lab.schemas import load_schema
from pneuma_lab.training.governance import (
    APPROVED_ARTIFACT_ROOT_PREFIX,
    DATASET_1_ID,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_MANIFEST_SCHEMA = "estimator-run-manifest.schema.json"
AUTHORIZATION_SCHEMA = "estimator-training-authorization.schema.json"
RUN_MANIFEST_ROOT = Path("docs/data/training-runs")
AUTHORIZATION_ROOT = Path("docs/data/training-authorizations")
SPLIT_CONTRACT_ROOT = Path("docs/data/training-readiness")
SPLIT_CONTRACT_VERSION = "0.1.0"
SPLIT_METHOD = "sha256_repo_mod10_lt3_eval_v1"
ESTIMATORS = frozenset(("e1-v0", "e2-v0"))
TASK_TYPES = frozenset(("RISK_PREDICTION", "VERIFICATION_PRESSURE"))
SCRUBBED_FIELDS = frozenset(
    (*features.SCRUBBED_TOP_LEVEL_FIELDS, "labels.resolved")
)

TrackedChecker = Callable[[Path, str], bool]
CommittedReader = Callable[[Path, str], bytes]


@dataclass(frozen=True)
class VerifiedCodeState:
    """Observed Git state for the authorized implementation commit."""

    authorized_code_commit: str
    execution_head: str
    authorized_commit_is_ancestor: bool
    protected_paths_unchanged: bool
    worktree_clean: bool


CodeStateChecker = Callable[[Path, str], VerifiedCodeState]


class PreflightError(ValueError):
    """A stable, operator-readable fail-closed preflight failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"estimator preflight failed [{code}]: {message}")


@dataclass(frozen=True)
class VerifiedEstimatorRun:
    """Paths and immutable metadata established by static preflight."""

    manifest: dict
    authorization: dict
    code_state: VerifiedCodeState
    code_state_checker: CodeStateChecker = field(repr=False, compare=False)
    repo_root: Path
    manifest_path: Path
    manifest_sha256: str
    authorization_path: Path
    traces_path: Path
    adapter_report_path: Path
    split_contract_path: Path
    artifact_root: Path


def _fail(code: str, message: str) -> None:
    raise PreflightError(code, message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        _fail("artifact_unreadable", f"cannot read {path}: {exc}")
    return f"sha256:{digest.hexdigest()}"


def _normalized_sha256(value: object) -> str:
    text = str(value or "")
    return text if text.startswith("sha256:") else f"sha256:{text}"


def _load_json_with_hash(path: Path, *, code: str) -> tuple[dict, str]:
    """Parse and hash the same immutable byte snapshot from one file read."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _fail(code, f"cannot load JSON from {path}: {exc}")
    return _parse_json_snapshot(raw, path=path, code=code)


def _parse_json_snapshot(raw: bytes, *, path: Path, code: str) -> tuple[dict, str]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(code, f"cannot load JSON from {path}: {exc}")
    if not isinstance(value, dict):
        _fail(code, f"{path} must contain one JSON object")
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    return value, digest


def _default_committed_reader(repo_root: Path, relative_path: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{relative_path}"],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        _fail("control_artifact_unreadable", f"cannot execute Git: {exc}")
    if result.returncode != 0:
        _fail(
            "control_artifact_unreadable",
            f"cannot read committed control artifact: {relative_path}",
        )
    return result.stdout


def _load_control_json_with_hash(
    path: Path,
    *,
    repo_root: Path,
    require_tracked: bool,
    committed_reader: CommittedReader,
    code: str,
) -> tuple[dict, str]:
    if not require_tracked:
        return _load_json_with_hash(path, code=code)
    relative = path.relative_to(repo_root).as_posix()
    raw = committed_reader(repo_root, relative)
    return _parse_json_snapshot(raw, path=path, code=code)


def _validate_schema(value: dict, schema_name: str, *, code: str) -> None:
    validator = Draft202012Validator(load_schema(schema_name))
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "$"
        _fail(code, f"{location}: {error.message}")


def _default_tracked_checker(repo_root: Path, relative_path: str) -> bool:
    try:
        tracked = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-files",
                "--error-unmatch",
                "--",
                relative_path,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        unchanged = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--quiet",
                "HEAD",
                "--",
                relative_path,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return tracked.returncode == 0 and unchanged.returncode == 0


def _default_code_state_checker(
    repo_root: Path, authorized_code_commit: str
) -> VerifiedCodeState:
    """Inspect committed-code drift and the complete worktree without mutation."""
    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        ancestor = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                authorized_code_commit,
                "HEAD",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        code_diff = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--quiet",
                f"{authorized_code_commit}..HEAD",
                "--",
                "src",
                "schemas",
                "pyproject.toml",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        status = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        _fail("code_state_unverifiable", f"cannot execute Git: {exc}")
    if (
        head.returncode != 0
        or ancestor.returncode not in (0, 1)
        or code_diff.returncode not in (0, 1)
        or status.returncode != 0
    ):
        _fail("code_state_unverifiable", "Git could not verify the authorized code")
    execution_head = head.stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", execution_head):
        _fail("code_state_unverifiable", "execution HEAD is not a full commit hash")
    return VerifiedCodeState(
        authorized_code_commit=authorized_code_commit,
        execution_head=execution_head,
        authorized_commit_is_ancestor=ancestor.returncode == 0,
        protected_paths_unchanged=code_diff.returncode == 0,
        worktree_clean=status.stdout == "",
    )


def _validate_code_state(state: VerifiedCodeState, authorized_commit: str) -> None:
    _assert_equal(
        state.authorized_code_commit,
        authorized_commit,
        code="code_state_unverifiable",
        field="authorized_code_commit",
    )
    if not re.fullmatch(r"[0-9a-f]{40}", state.execution_head):
        _fail("code_state_unverifiable", "execution HEAD is not a full commit hash")
    if not state.authorized_commit_is_ancestor:
        _fail(
            "authorized_code_not_ancestor",
            "authorized code commit is not an ancestor of execution HEAD",
        )
    if not state.protected_paths_unchanged:
        _fail(
            "authorized_code_drift",
            "src/, schemas/, or pyproject.toml changed after code authorization",
        )
    if not state.worktree_clean:
        _fail(
            "worktree_not_clean",
            "tracked or untracked worktree changes are present",
        )


def _control_path(
    repo_root: Path,
    declared_path: object,
    approved_root: Path,
    *,
    label: str,
    require_tracked: bool,
    tracked_checker: TrackedChecker,
) -> Path:
    raw = Path(str(declared_path or ""))
    if raw.is_absolute():
        _fail("control_path_not_relative", f"{label} path must be repo-relative")

    approved = (repo_root / approved_root).resolve()
    candidate = (repo_root / raw).resolve()
    try:
        candidate.relative_to(approved)
        relative = candidate.relative_to(repo_root).as_posix()
    except ValueError:
        _fail(
            "control_path_not_approved",
            f"{label} must stay under {approved_root.as_posix()}/",
        )
    if candidate.suffix.lower() != ".json":
        _fail("control_path_not_json", f"{label} must be a JSON file")
    if require_tracked and not tracked_checker(repo_root, relative):
        _fail(
            "control_artifact_untracked",
            f"{label} must be committed and unchanged before it can authorize training",
        )
    if not candidate.is_file():
        _fail("control_artifact_missing", f"{label} does not exist: {relative}")
    return candidate


def _runtime_path(repo_root: Path, value: object) -> Path:
    raw = Path(str(value or ""))
    return raw.resolve() if raw.is_absolute() else (repo_root / raw).resolve()


def _assert_equal(actual: object, expected: object, *, code: str, field: str) -> None:
    if actual != expected:
        _fail(code, f"{field} does not match the authorized value")


def _validate_split_contract(contract: dict, manifest: dict) -> None:
    expected_keys = {
        "estimator_split_manifest_schema_version",
        "dataset_id",
        "source_traces_sha256",
        "method",
        "dev_repos_sha256",
        "eval_repos_sha256",
        "dev_traces",
        "eval_traces",
        "excluded_traces",
    }
    if set(contract) != expected_keys:
        _fail(
            "split_contract_invalid",
            "split contract fields differ from the strict estimator split contract",
        )
    split = manifest["split"]
    expected_values = {
        "estimator_split_manifest_schema_version": SPLIT_CONTRACT_VERSION,
        "dataset_id": manifest["dataset_id"],
        "source_traces_sha256": manifest["source"]["traces_sha256"],
        "method": split["method"],
        "dev_repos_sha256": split["dev_repos_sha256"],
        "eval_repos_sha256": split["eval_repos_sha256"],
        "dev_traces": split["expected_dev_traces"],
        "eval_traces": split["expected_eval_traces"],
        "excluded_traces": split["expected_excluded_traces"],
    }
    for field, expected in expected_values.items():
        _assert_equal(
            contract.get(field),
            expected,
            code="split_contract_mismatch",
            field=field,
        )
    for field in ("dev_traces", "eval_traces", "excluded_traces"):
        value = contract[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail("split_contract_invalid", f"{field} must be a non-negative integer")


def _validate_current_implementation(manifest: dict) -> None:
    if frozenset(manifest["estimators"]) != ESTIMATORS:
        _fail("estimator_scope_mismatch", "trainer always fits exactly E1 and E2")
    if frozenset(manifest["task_types"]) != TASK_TYPES:
        _fail("task_scope_mismatch", "trainer task types are not exactly declared")
    feature_contract = manifest["feature_contract"]
    _assert_equal(
        feature_contract["feature_extractor_version"],
        features.FEATURE_EXTRACTOR_VERSION,
        code="implementation_drift",
        field="feature_extractor_version",
    )
    if frozenset(feature_contract["scrubbed_fields"]) != SCRUBBED_FIELDS:
        _fail("implementation_drift", "scrubbed_fields differ from the extractor")
    expected_training = {
        "algorithm": "full-batch-logistic-regression-l2-v1",
        "learning_rate": logistic.LEARNING_RATE,
        "learning_rate_decay": logistic.LR_DECAY,
        "iterations": logistic.N_ITERATIONS,
        "l2_lambda": logistic.L2_LAMBDA,
        "randomness": "none",
    }
    if manifest["training"] != expected_training:
        _fail("implementation_drift", "trainer constants differ from the run manifest")
    _assert_equal(
        manifest["class_imbalance_handling"],
        "unweighted_baseline_reproduction_only",
        code="implementation_drift",
        field="class_imbalance_handling",
    )
    _assert_equal(
        manifest["model_use"],
        "offline_advisory_only",
        code="implementation_drift",
        field="model_use",
    )


def _validate_authorization_review(authorization: dict) -> None:
    try:
        datetime.strptime(authorization["reviewed_at"], "%Y-%m-%dT%H:%M:%SZ")
    except (KeyError, TypeError, ValueError):
        _fail(
            "authorization_artifact_invalid",
            "reviewed_at must be a real UTC calendar timestamp",
        )


def require_empty_artifact_root(artifact_root: Path) -> None:
    if not artifact_root.exists():
        return
    if artifact_root.is_symlink() or artifact_root.resolve() != artifact_root:
        _fail(
            "artifact_root_not_approved",
            "artifact root must not be a symlink or junction",
        )
    if not artifact_root.is_dir():
        _fail("artifact_root_not_approved", "artifact root must be a directory")
    try:
        next(artifact_root.iterdir())
    except StopIteration:
        return
    except OSError as exc:
        _fail("artifact_root_unreadable", f"cannot inspect artifact root: {exc}")
    _fail(
        "artifact_root_not_empty",
        "artifact root must be absent or empty before an authorized run",
    )


def verify_estimator_run(
    manifest_path: str | Path,
    traces_path: str | Path,
    artifact_root: str | Path,
    *,
    repo_root: str | Path | None = None,
    require_tracked: bool = True,
    tracked_checker: TrackedChecker | None = None,
    code_state_checker: CodeStateChecker | None = None,
    committed_reader: CommittedReader | None = None,
) -> VerifiedEstimatorRun:
    """Verify all static gates before the trainer may read trace bytes.

    Production callers use the fail-closed Git-tracking default.  Hermetic
    tests may explicitly disable it or inject a tracking checker.
    """

    root = Path(repo_root or REPO_ROOT).resolve()
    checker = tracked_checker or _default_tracked_checker
    inspect_code_state = code_state_checker or _default_code_state_checker
    read_committed = committed_reader or _default_committed_reader
    manifest_file = _control_path(
        root,
        manifest_path,
        RUN_MANIFEST_ROOT,
        label="estimator run manifest",
        require_tracked=require_tracked,
        tracked_checker=checker,
    )
    manifest, manifest_hash = _load_control_json_with_hash(
        manifest_file,
        repo_root=root,
        require_tracked=require_tracked,
        committed_reader=read_committed,
        code="run_manifest_unreadable",
    )
    _validate_schema(manifest, RUN_MANIFEST_SCHEMA, code="run_manifest_invalid")
    _validate_current_implementation(manifest)
    authorized_code_commit = manifest["source_code"]["authorized_code_commit"]
    code_state = inspect_code_state(root, authorized_code_commit)
    _validate_code_state(code_state, authorized_code_commit)

    authorization_path = _control_path(
        root,
        manifest["authorization_ref"]["path"],
        AUTHORIZATION_ROOT,
        label="authorization artifact",
        require_tracked=require_tracked,
        tracked_checker=checker,
    )
    split_path = _control_path(
        root,
        manifest["split"]["manifest_path"],
        SPLIT_CONTRACT_ROOT,
        label="estimator split contract",
        require_tracked=require_tracked,
        tracked_checker=checker,
    )

    authorization, authorization_hash = _load_control_json_with_hash(
        authorization_path,
        repo_root=root,
        require_tracked=require_tracked,
        committed_reader=read_committed,
        code="authorization_artifact_invalid",
    )
    split_contract, split_hash = _load_control_json_with_hash(
        split_path,
        repo_root=root,
        require_tracked=require_tracked,
        committed_reader=read_committed,
        code="split_contract_invalid",
    )
    _assert_equal(
        authorization_hash,
        manifest["authorization_ref"]["sha256"],
        code="authorization_hash_mismatch",
        field="authorization_ref.sha256",
    )
    _assert_equal(
        split_hash,
        manifest["split"]["manifest_sha256"],
        code="split_hash_mismatch",
        field="split.manifest_sha256",
    )

    _validate_schema(
        authorization,
        AUTHORIZATION_SCHEMA,
        code="authorization_artifact_invalid",
    )
    _validate_authorization_review(authorization)
    authorization_bindings = {
        "authorization_id": manifest["authorization_ref"]["authorization_id"],
        "run_id": manifest["run_id"],
        "dataset_id": manifest["dataset_id"],
        "authorized_code_commit": authorized_code_commit,
        "source_traces_sha256": manifest["source"]["traces_sha256"],
        "split_manifest_sha256": manifest["split"]["manifest_sha256"],
        "artifact_root": manifest["artifact_root"],
        "release_authorization": manifest["release_authorization"],
        "runtime_integration": manifest["runtime_integration"],
    }
    for field, expected in authorization_bindings.items():
        _assert_equal(
            authorization.get(field),
            expected,
            code="authorization_binding_mismatch",
            field=field,
        )
    if frozenset(authorization["estimators"]) != ESTIMATORS:
        _fail(
            "authorization_binding_mismatch",
            "authorization estimators differ from the trainer scope",
        )

    _validate_split_contract(split_contract, manifest)

    approved_build_root = (root / APPROVED_ARTIFACT_ROOT_PREFIX).resolve()
    expected_artifact_root = approved_build_root / manifest["run_id"]
    try:
        approved_build_root.relative_to(root)
    except ValueError:
        _fail("artifact_root_not_approved", "approved artifact root escapes the repo")
    declared_artifact_root = _runtime_path(root, manifest["artifact_root"])
    requested_artifact_root = _runtime_path(root, artifact_root)
    if (
        declared_artifact_root != expected_artifact_root
        or requested_artifact_root != expected_artifact_root
    ):
        _fail(
            "artifact_root_not_approved",
            "--out must exactly match the manifest's run-scoped repo-local root",
        )
    require_empty_artifact_root(expected_artifact_root)

    declared_traces = _runtime_path(root, manifest["source"]["traces_path"])
    requested_traces = _runtime_path(root, traces_path)
    if requested_traces != declared_traces:
        _fail("source_path_mismatch", "--traces differs from the run manifest")
    adapter_report_path = _runtime_path(
        root, manifest["source"]["adapter_report_path"]
    )

    # Source bytes are intentionally touched only after the authorization,
    # split, implementation, and output-scope gates above have all passed.
    traces_hash = _sha256_file(declared_traces)
    adapter_report, adapter_report_hash = _load_json_with_hash(
        adapter_report_path, code="adapter_report_invalid"
    )
    _assert_equal(
        traces_hash,
        manifest["source"]["traces_sha256"],
        code="source_hash_mismatch",
        field="source.traces_sha256",
    )
    _assert_equal(
        adapter_report_hash,
        manifest["source"]["adapter_report_sha256"],
        code="source_hash_mismatch",
        field="source.adapter_report_sha256",
    )
    source = manifest["source"]
    report_bindings = {
        "adapter_report_schema_version": adapter_report.get(
            "adapter_report_schema_version"
        ),
        "dataset": adapter_report.get("dataset"),
        "adapter.name": (adapter_report.get("adapter") or {}).get("name"),
        "adapter.version": (adapter_report.get("adapter") or {}).get("version"),
        "hf_repo": adapter_report.get("hf_repo"),
        "hf_revision": adapter_report.get("hf_revision"),
        "expected_trace_count": (adapter_report.get("counts") or {}).get("valid"),
    }
    expected_report_values = {
        "adapter_report_schema_version": "0.1.0",
        "dataset": "swe-gym",
        "adapter.name": source["adapter_name"],
        "adapter.version": source["adapter_version"],
        "hf_repo": source["hf_repo"],
        "hf_revision": source["hf_revision"],
        "expected_trace_count": source["expected_trace_count"],
    }
    for field, actual in report_bindings.items():
        _assert_equal(
            actual,
            expected_report_values[field],
            code="adapter_report_mismatch",
            field=field,
        )
    report_trace_count = report_bindings["expected_trace_count"]
    if (
        isinstance(report_trace_count, bool)
        or not isinstance(report_trace_count, int)
        or report_trace_count < 1
    ):
        _fail(
            "adapter_report_mismatch",
            "counts.valid must be a positive integer",
        )
    _assert_equal(
        _normalized_sha256(adapter_report.get("traces_file_sha256")),
        traces_hash,
        code="adapter_report_mismatch",
        field="traces_file_sha256",
    )

    return VerifiedEstimatorRun(
        manifest=manifest,
        authorization=authorization,
        code_state=code_state,
        code_state_checker=inspect_code_state,
        repo_root=root,
        manifest_path=manifest_file,
        manifest_sha256=manifest_hash,
        authorization_path=authorization_path,
        traces_path=declared_traces,
        adapter_report_path=adapter_report_path,
        split_contract_path=split_path,
        artifact_root=expected_artifact_root,
    )


def verify_loaded_corpus(
    run: VerifiedEstimatorRun,
    *,
    dev_repos_sha256: str,
    eval_repos_sha256: str,
    dev_traces: int,
    eval_traces: int,
    excluded_traces: int,
    total_traces: int,
) -> None:
    """Re-bind the loaded corpus and observed split immediately before fit."""

    source = run.manifest["source"]
    split = run.manifest["split"]
    current_code_state = run.code_state_checker(
        run.repo_root, run.code_state.authorized_code_commit
    )
    _validate_code_state(current_code_state, run.code_state.authorized_code_commit)
    _assert_equal(
        current_code_state.execution_head,
        run.code_state.execution_head,
        code="code_state_changed_during_load",
        field="execution_head",
    )
    require_empty_artifact_root(run.artifact_root)
    _assert_equal(
        _sha256_file(run.traces_path),
        source["traces_sha256"],
        code="source_changed_during_load",
        field="source.traces_sha256",
    )
    _assert_equal(
        _sha256_file(run.adapter_report_path),
        source["adapter_report_sha256"],
        code="source_changed_during_load",
        field="source.adapter_report_sha256",
    )
    observed = {
        "dev_repos_sha256": _normalized_sha256(dev_repos_sha256),
        "eval_repos_sha256": _normalized_sha256(eval_repos_sha256),
        "expected_dev_traces": dev_traces,
        "expected_eval_traces": eval_traces,
        "expected_excluded_traces": excluded_traces,
    }
    for field, actual in observed.items():
        _assert_equal(
            actual,
            split[field],
            code="observed_split_mismatch",
            field=field,
        )
    _assert_equal(
        total_traces,
        source["expected_trace_count"],
        code="observed_source_count_mismatch",
        field="source.expected_trace_count",
    )
    if dev_traces + eval_traces + excluded_traces != total_traces:
        _fail(
            "observed_source_count_mismatch",
            "loaded dev/eval/excluded counts do not cover the source corpus",
        )


__all__ = [
    "AUTHORIZATION_ROOT",
    "CodeStateChecker",
    "CommittedReader",
    "ESTIMATORS",
    "PreflightError",
    "REPO_ROOT",
    "RUN_MANIFEST_ROOT",
    "SCRUBBED_FIELDS",
    "SPLIT_CONTRACT_ROOT",
    "SPLIT_METHOD",
    "TASK_TYPES",
    "VerifiedEstimatorRun",
    "VerifiedCodeState",
    "require_empty_artifact_root",
    "verify_estimator_run",
    "verify_loaded_corpus",
]
