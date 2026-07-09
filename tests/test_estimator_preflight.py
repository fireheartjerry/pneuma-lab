"""Hermetic tests for the fail-closed E1/E2 trainer authorization gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.estimators import train
from pneuma_lab.training import preflight

DEV_REPOS_SHA256 = "sha256:" + "1" * 64
EVAL_REPOS_SHA256 = "sha256:" + "2" * 64
HF_REVISION = "a" * 40
AUTHORIZED_CODE_COMMIT = "b" * 40
EXECUTION_HEAD = "c" * 40


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return _sha256(path)


def _clean_code_state(
    _root: Path, authorized_code_commit: str
) -> preflight.VerifiedCodeState:
    return preflight.VerifiedCodeState(
        authorized_code_commit=authorized_code_commit,
        execution_head=EXECUTION_HEAD,
        authorized_commit_is_ancestor=True,
        protected_paths_unchanged=True,
        worktree_clean=True,
    )


def _read_worktree_control(root: Path, relative: str) -> bytes:
    return (root / relative).read_bytes()


def _bundle(root: Path) -> dict:
    run_id = "local-e1-e2-test"
    traces_rel = Path("data/pneuma_traces.jsonl")
    report_rel = Path("data/adapter_report.json")
    split_rel = Path("docs/data/training-readiness/local-e1-e2-split.json")
    auth_rel = Path("docs/data/training-authorizations/local-e1-e2-auth.json")
    manifest_rel = Path("docs/data/training-runs/local-e1-e2-run.json")
    artifact_rel = Path(f"build/training_runs/openhands-sampled/{run_id}")

    traces_path = root / traces_rel
    traces_path.parent.mkdir(parents=True, exist_ok=True)
    traces_path.write_text("{}\n{}\n{}\n{}\n", encoding="utf-8", newline="\n")
    traces_sha = _sha256(traces_path)

    report = {
        "adapter_report_schema_version": "0.1.0",
        "adapter": {"name": "openhands-sampled", "version": "0.1.0"},
        "dataset": "swe-gym",
        "hf_repo": "SWE-Gym/OpenHands-Sampled-Trajectories",
        "hf_revision": HF_REVISION,
        "counts": {"valid": 4},
        "traces_file_sha256": traces_sha.removeprefix("sha256:"),
    }
    report_sha = _write_json(root / report_rel, report)

    split = {
        "estimator_split_manifest_schema_version": "0.1.0",
        "dataset_id": "swe-gym-openhands-sampled",
        "source_traces_sha256": traces_sha,
        "method": "sha256_repo_mod10_lt3_eval_v1",
        "dev_repos_sha256": DEV_REPOS_SHA256,
        "eval_repos_sha256": EVAL_REPOS_SHA256,
        "dev_traces": 2,
        "eval_traces": 1,
        "excluded_traces": 1,
    }
    split_sha = _write_json(root / split_rel, split)

    artifact_root = artifact_rel.as_posix() + "/"
    authorization = {
        "authorization_schema_version": "0.1.0",
        "authorization_id": "auth-local-e1-e2-test",
        "run_id": run_id,
        "dataset_id": "swe-gym-openhands-sampled",
        "decision": "authorized",
        "scope": "local_research",
        "estimators": ["e1-v0", "e2-v0"],
        "authorized_code_commit": AUTHORIZED_CODE_COMMIT,
        "source_traces_sha256": traces_sha,
        "split_manifest_sha256": split_sha,
        "artifact_root": artifact_root,
        "reviewer": "test-reviewer",
        "reviewed_at": "2026-07-09T18:00:00Z",
        "release_authorization": "not_authorized",
        "runtime_integration": "none",
    }
    auth_sha = _write_json(root / auth_rel, authorization)

    manifest = {
        "estimator_run_manifest_schema_version": "0.1.0",
        "run_id": run_id,
        "dataset_id": "swe-gym-openhands-sampled",
        "estimators": ["e1-v0", "e2-v0"],
        "task_types": ["RISK_PREDICTION", "VERIFICATION_PRESSURE"],
        "training_authorization": "authorized_local_research",
        "authorization_ref": {
            "authorization_id": authorization["authorization_id"],
            "path": auth_rel.as_posix(),
            "sha256": auth_sha,
        },
        "release_authorization": "not_authorized",
        "runtime_integration": "none",
        "source_code": {
            "authorized_code_commit": AUTHORIZED_CODE_COMMIT,
            "required_tree_state": "clean",
        },
        "source": {
            "traces_path": traces_rel.as_posix(),
            "traces_sha256": traces_sha,
            "adapter_report_path": report_rel.as_posix(),
            "adapter_report_sha256": report_sha,
            "adapter_name": "openhands-sampled",
            "adapter_version": "0.1.0",
            "hf_repo": "SWE-Gym/OpenHands-Sampled-Trajectories",
            "hf_revision": HF_REVISION,
            "expected_trace_count": 4,
        },
        "split": {
            "manifest_path": split_rel.as_posix(),
            "manifest_sha256": split_sha,
            "method": "sha256_repo_mod10_lt3_eval_v1",
            "dev_repos_sha256": DEV_REPOS_SHA256,
            "eval_repos_sha256": EVAL_REPOS_SHA256,
            "expected_dev_traces": 2,
            "expected_eval_traces": 1,
            "expected_excluded_traces": 1,
        },
        "feature_contract": {
            "feature_extractor_version": "pneuma-estimators-features/0.1.0",
            "scrubbed_fields": [
                "outcome",
                "oracle",
                "reference_supervision",
                "labels.resolved",
            ],
        },
        "training": {
            "algorithm": "full-batch-logistic-regression-l2-v1",
            "learning_rate": 0.3,
            "learning_rate_decay": 0.005,
            "iterations": 800,
            "l2_lambda": 0.001,
            "randomness": "none",
        },
        "class_imbalance_handling": "unweighted_baseline_reproduction_only",
        "model_use": "offline_advisory_only",
        "artifact_root": artifact_root,
    }
    _write_json(root / manifest_rel, manifest)
    return {
        "root": root,
        "manifest_rel": manifest_rel.as_posix(),
        "manifest_path": root / manifest_rel,
        "traces_rel": traces_rel.as_posix(),
        "traces_path": traces_path,
        "report_path": root / report_rel,
        "split_rel": split_rel.as_posix(),
        "split_path": root / split_rel,
        "auth_rel": auth_rel.as_posix(),
        "auth_path": root / auth_rel,
        "artifact_rel": artifact_rel.as_posix() + "/",
        "artifact_path": root / artifact_rel,
    }


def _verify(bundle: dict, **kwargs) -> preflight.VerifiedEstimatorRun:
    kwargs.setdefault("code_state_checker", _clean_code_state)
    return preflight.verify_estimator_run(
        bundle["manifest_rel"],
        bundle["traces_rel"],
        bundle["artifact_rel"],
        repo_root=bundle["root"],
        require_tracked=False,
        **kwargs,
    )


def test_valid_hash_bound_local_research_run_passes_static_preflight(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    assert run.manifest["run_id"] == "local-e1-e2-test"
    assert run.manifest_sha256 == _sha256(bundle["manifest_path"])
    assert run.artifact_root == bundle["artifact_path"].resolve()


def test_not_authorized_manifest_fails_before_source_bytes_are_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["training_authorization"] = "not_authorized"
    _write_json(bundle["manifest_path"], manifest)
    touched: list[Path] = []
    original_sha = preflight._sha256_file

    def recording_sha(path: Path) -> str:
        touched.append(path)
        if path == bundle["traces_path"]:
            raise AssertionError("trace bytes must not be read")
        return original_sha(path)

    monkeypatch.setattr(preflight, "_sha256_file", recording_sha)
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "run_manifest_invalid"
    assert bundle["traces_path"] not in touched


def test_hashed_but_denied_authorization_artifact_cannot_authorize(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    authorization = json.loads(bundle["auth_path"].read_text(encoding="utf-8"))
    authorization["decision"] = "denied"
    auth_sha = _write_json(bundle["auth_path"], authorization)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["authorization_ref"]["sha256"] = auth_sha
    _write_json(bundle["manifest_path"], manifest)

    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "authorization_artifact_invalid"


def test_authorization_must_bind_the_same_run(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    authorization = json.loads(bundle["auth_path"].read_text(encoding="utf-8"))
    authorization["run_id"] = "different-run"
    auth_sha = _write_json(bundle["auth_path"], authorization)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["authorization_ref"]["sha256"] = auth_sha
    _write_json(bundle["manifest_path"], manifest)

    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "authorization_binding_mismatch"


def test_authorization_review_time_must_be_a_real_calendar_value(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    authorization = json.loads(bundle["auth_path"].read_text(encoding="utf-8"))
    authorization["reviewed_at"] = "2026-99-99T99:99:99Z"
    auth_sha = _write_json(bundle["auth_path"], authorization)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["authorization_ref"]["sha256"] = auth_sha
    _write_json(bundle["manifest_path"], manifest)
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "authorization_artifact_invalid"


def test_untracked_authorization_cannot_authorize(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    def tracked_except_authorization(_root: Path, relative: str) -> bool:
        return relative != bundle["auth_rel"]

    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_estimator_run(
            bundle["manifest_rel"],
            bundle["traces_rel"],
            bundle["artifact_rel"],
            repo_root=tmp_path,
            tracked_checker=tracked_except_authorization,
            code_state_checker=_clean_code_state,
            committed_reader=_read_worktree_control,
        )
    assert exc_info.value.code == "control_artifact_untracked"


def test_untracked_run_manifest_cannot_request_training(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_estimator_run(
            bundle["manifest_rel"],
            bundle["traces_rel"],
            bundle["artifact_rel"],
            repo_root=tmp_path,
            tracked_checker=lambda _root, _relative: False,
        )
    assert exc_info.value.code == "control_artifact_untracked"


def test_split_contract_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    split = json.loads(bundle["split_path"].read_text(encoding="utf-8"))
    split["dev_traces"] = 3
    _write_json(bundle["split_path"], split)
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "split_hash_mismatch"


def test_source_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    bundle["traces_path"].write_text("different source\n", encoding="utf-8")
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "source_hash_mismatch"


def test_adapter_report_file_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    bundle["report_path"].write_text("{}\n", encoding="utf-8")
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "source_hash_mismatch"


def test_hash_bound_adapter_report_content_must_match_manifest(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    report = json.loads(bundle["report_path"].read_text(encoding="utf-8"))
    report["hf_revision"] = "d" * 40
    report_sha = _write_json(bundle["report_path"], report)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["source"]["adapter_report_sha256"] = report_sha
    _write_json(bundle["manifest_path"], manifest)
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "adapter_report_mismatch"


@pytest.mark.parametrize(
    ("attribute", "drifted_value"),
    (("learning_rate", 0.4), ("feature_extractor", "drifted-extractor")),
)
def test_current_implementation_must_match_the_declared_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    drifted_value: object,
) -> None:
    bundle = _bundle(tmp_path)
    if attribute == "learning_rate":
        monkeypatch.setattr(preflight.logistic, "LEARNING_RATE", drifted_value)
    else:
        monkeypatch.setattr(
            preflight.features, "FEATURE_EXTRACTOR_VERSION", drifted_value
        )
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "implementation_drift"


@pytest.mark.parametrize(
    ("state_changes", "expected_code"),
    (
        ({"authorized_commit_is_ancestor": False}, "authorized_code_not_ancestor"),
        ({"protected_paths_unchanged": False}, "authorized_code_drift"),
        ({"worktree_clean": False}, "worktree_not_clean"),
    ),
)
def test_code_state_must_be_ancestor_unchanged_and_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state_changes: dict,
    expected_code: str,
) -> None:
    bundle = _bundle(tmp_path)
    source_touched = False
    original_sha = preflight._sha256_file

    def recording_sha(path: Path) -> str:
        nonlocal source_touched
        if path in (bundle["traces_path"], bundle["report_path"]):
            source_touched = True
        return original_sha(path)

    monkeypatch.setattr(preflight, "_sha256_file", recording_sha)

    def inspected_state(
        _root: Path, authorized_code_commit: str
    ) -> preflight.VerifiedCodeState:
        fields = {
            "authorized_code_commit": authorized_code_commit,
            "execution_head": EXECUTION_HEAD,
            "authorized_commit_is_ancestor": True,
            "protected_paths_unchanged": True,
            "worktree_clean": True,
        }
        fields.update(state_changes)
        return preflight.VerifiedCodeState(**fields)

    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle, code_state_checker=inspected_state)
    assert exc_info.value.code == expected_code
    assert source_touched is False


def test_arbitrary_output_directory_is_rejected_before_source_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path)
    touched_source = False
    original_sha = preflight._sha256_file

    def recording_sha(path: Path) -> str:
        nonlocal touched_source
        if path in (bundle["traces_path"], bundle["report_path"]):
            touched_source = True
        return original_sha(path)

    monkeypatch.setattr(preflight, "_sha256_file", recording_sha)
    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_estimator_run(
            bundle["manifest_rel"],
            bundle["traces_rel"],
            "build/estimators",
            repo_root=tmp_path,
            require_tracked=False,
            code_state_checker=_clean_code_state,
        )
    assert exc_info.value.code == "artifact_root_not_approved"
    assert touched_source is False


def test_nonempty_run_root_is_rejected_before_source_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path)
    bundle["artifact_path"].mkdir(parents=True)
    (bundle["artifact_path"] / "stale.txt").write_text("stale", encoding="utf-8")
    source_touched = False
    original_sha = preflight._sha256_file

    def recording_sha(path: Path) -> str:
        nonlocal source_touched
        if path in (bundle["traces_path"], bundle["report_path"]):
            source_touched = True
        return original_sha(path)

    monkeypatch.setattr(preflight, "_sha256_file", recording_sha)
    with pytest.raises(preflight.PreflightError) as exc_info:
        _verify(bundle)
    assert exc_info.value.code == "artifact_root_not_empty"
    assert source_touched is False


def test_observed_split_is_rechecked_before_fit(tmp_path: Path) -> None:
    run = _verify(_bundle(tmp_path))
    preflight.verify_loaded_corpus(
        run,
        dev_repos_sha256=DEV_REPOS_SHA256,
        eval_repos_sha256=EVAL_REPOS_SHA256,
        dev_traces=2,
        eval_traces=1,
        excluded_traces=1,
        total_traces=4,
    )
    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_loaded_corpus(
            run,
            dev_repos_sha256=DEV_REPOS_SHA256,
            eval_repos_sha256=EVAL_REPOS_SHA256,
            dev_traces=3,
            eval_traces=0,
            excluded_traces=1,
            total_traces=4,
        )
    assert exc_info.value.code == "observed_split_mismatch"


def test_source_change_between_preflight_and_fit_is_detected(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    bundle["traces_path"].write_text("changed\n", encoding="utf-8")
    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_loaded_corpus(
            run,
            dev_repos_sha256=DEV_REPOS_SHA256,
            eval_repos_sha256=EVAL_REPOS_SHA256,
            dev_traces=2,
            eval_traces=1,
            excluded_traces=1,
            total_traces=4,
        )
    assert exc_info.value.code == "source_changed_during_load"


def test_corpus_bytes_are_hashed_in_the_same_pass_that_parses_them(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    bundle["traces_path"].write_text("{}\n", encoding="utf-8", newline="\n")
    with pytest.raises(preflight.PreflightError) as exc_info:
        train.loadCorpus(
            str(bundle["traces_path"]),
            expected_sha256=run.manifest["source"]["traces_sha256"],
        )
    assert exc_info.value.code == "source_changed_during_load"


def test_code_state_is_rechecked_after_load_before_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path)
    dirty = False

    def changing_state(
        _root: Path, authorized_code_commit: str
    ) -> preflight.VerifiedCodeState:
        return preflight.VerifiedCodeState(
            authorized_code_commit=authorized_code_commit,
            execution_head=EXECUTION_HEAD,
            authorized_commit_is_ancestor=True,
            protected_paths_unchanged=True,
            worktree_clean=not dirty,
        )

    run = _verify(bundle, code_state_checker=changing_state)
    dirty = True
    source_touched = False
    original_sha = preflight._sha256_file

    def recording_sha(path: Path) -> str:
        nonlocal source_touched
        if path in (bundle["traces_path"], bundle["report_path"]):
            source_touched = True
        return original_sha(path)

    monkeypatch.setattr(preflight, "_sha256_file", recording_sha)
    with pytest.raises(preflight.PreflightError) as exc_info:
        preflight.verify_loaded_corpus(
            run,
            dev_repos_sha256=DEV_REPOS_SHA256,
            eval_repos_sha256=EVAL_REPOS_SHA256,
            dev_traces=2,
            eval_traces=1,
            excluded_traces=1,
            total_traces=4,
        )
    assert exc_info.value.code == "worktree_not_clean"
    assert source_touched is False


def test_trainer_returns_before_load_for_unauthorized_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path)
    manifest = json.loads(bundle["manifest_path"].read_text(encoding="utf-8"))
    manifest["training_authorization"] = "not_authorized"
    _write_json(bundle["manifest_path"], manifest)
    monkeypatch.setattr(preflight, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        preflight, "_default_tracked_checker", lambda _root, _relative: True
    )
    monkeypatch.setattr(preflight, "_default_committed_reader", _read_worktree_control)
    load_called = False

    def forbidden_load(_path: str):
        nonlocal load_called
        load_called = True
        raise AssertionError("loadCorpus must not run")

    monkeypatch.setattr(train, "loadCorpus", forbidden_load)
    status = train.main(
        [
            "--run-manifest",
            bundle["manifest_rel"],
            "--traces",
            bundle["traces_rel"],
            "--out",
            bundle["artifact_rel"],
        ]
    )
    assert status == 2
    assert load_called is False


def test_training_provenance_and_receipt_are_exactly_bound(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    provenance = train.buildTrainingProvenance(run)
    assert provenance["binding_status"] == "verified_before_fit"
    assert provenance["run_manifest"]["sha256"] == _sha256(
        bundle["manifest_path"]
    )
    assert provenance["authorization"]["scope"] == "local_research"
    assert provenance["source_code"] == {
        "authorized_code_commit": AUTHORIZED_CODE_COMMIT,
        "execution_head": EXECUTION_HEAD,
        "required_tree_state": "clean",
        "verified_tree_state": "clean",
        "protected_paths_unchanged": ["src/", "schemas/", "pyproject.toml"],
    }
    assert provenance["release_authorization"] == "not_authorized"
    assert provenance["runtime_integration"] == "none"
    assert provenance["model_use"] == "offline_advisory_only"

    output_paths = train.prepareOutputPaths(run)
    artifacts = []
    for relative in train.ESTIMATOR_ARTIFACT_FILES:
        artifact = output_paths[relative]
        artifact.write_text("{}\n", encoding="utf-8", newline="\n")
        artifacts.append(str(artifact))
    receipt = train.writeRunReceipt(run, provenance, artifacts)
    on_disk = json.loads(
        (bundle["artifact_path"] / "run_receipt.json").read_text(encoding="utf-8")
    )
    assert on_disk == receipt
    assert receipt["status"] == "completed_local_research"
    assert receipt["artifacts_sha256"] == {
        relative: _sha256(output_paths[relative])
        for relative in train.ESTIMATOR_ARTIFACT_FILES
    }


def test_nested_output_symlink_is_rejected_when_supported(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    outside = tmp_path / "outside"
    outside.mkdir()
    bundle["artifact_path"].mkdir(parents=True)
    try:
        (bundle["artifact_path"] / "e1-v0").symlink_to(
            outside, target_is_directory=True
        )
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable on this platform: {exc}")
    with pytest.raises(preflight.PreflightError) as exc_info:
        train.prepareOutputPaths(run)
    assert exc_info.value.code in {
        "artifact_root_not_empty",
        "artifact_root_not_approved",
    }


def test_unexpected_post_write_file_prevents_completion_receipt(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    run = _verify(bundle)
    provenance = train.buildTrainingProvenance(run)
    output_paths = train.prepareOutputPaths(run)
    artifacts = []
    for relative in train.ESTIMATOR_ARTIFACT_FILES:
        output_paths[relative].write_text("{}\n", encoding="utf-8", newline="\n")
        artifacts.append(str(output_paths[relative]))
    (bundle["artifact_path"] / "unexpected.txt").write_text(
        "unexpected", encoding="utf-8"
    )
    with pytest.raises(preflight.PreflightError) as exc_info:
        train.writeRunReceipt(run, provenance, artifacts)
    assert exc_info.value.code == "artifact_layout_invalid"
