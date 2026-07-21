"""All-ten foundation suite policy and completeness-report tests."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

pytest.importorskip("torch")

from pneuma_lab import schemas as pls  # noqa: E402
from pneuma_lab.foundation import suite as foundation_suite  # noqa: E402
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS  # noqa: E402
from pneuma_lab.foundation.suite import (  # noqa: E402
    SuitePolicyError,
    build_suite_completeness_report,
    load_suite_policy,
    validate_suite_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json"
REGISTRY = ROOT / "docs/data/training-readiness/dataset-registry.json"
AUTHORITATIVE_PLAN = (
    ROOT / "docs/superpowers/plans/2026-07-13-foundation-training-launch-preparation.md"
)

EXPECTED_FAMILY_MATRIX = {
    "multi-swe-bench": (
        "train",
        "later",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        None,
    ),
    "open-swe-traces": (
        "train",
        "later",
        "metadata_only",
        "metadata_only",
        "approved_processed_lane_only",
        "approved_processed_lane_only",
        None,
    ),
    "sec-bench-pro": (
        "governance",
        "never",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        None,
    ),
    "swe-bench": (
        "eval",
        "never",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "processed/swe-bench/normalized_metadata.jsonl",
    ),
    "swe-bench-pro": (
        "eval",
        "never",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        None,
    ),
    "swe-chat": (
        "governance",
        "never",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        None,
    ),
    "swe-evo": (
        "train",
        "later",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        "metadata_only",
        None,
    ),
    "swe-gym": (
        "train",
        "first_stage",
        "approved_processed_lane_only",
        "approved_processed_lane_only",
        "approved_processed_lane_only",
        "approved_processed_lane_only",
        None,
    ),
    "swe-mera": (
        "eval",
        "never",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "processed/swe-mera/normalized_metadata.jsonl",
    ),
    "swe-polybench": (
        "eval",
        "later",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "identity_metadata_only",
        "processed/swe-polybench/normalized_metadata.jsonl",
    ),
}

EXPECTED_EVALUATION_IDENTITY = {
    "required_families": ["swe-bench", "swe-mera", "swe-polybench"],
    "blocked_unavailable_families": ["swe-bench-pro"],
}


def _matrix_mutations() -> tuple[tuple[str, str, str], ...]:
    cases = []
    for family, (
        _role,
        _gradient,
        _access,
        _access_500k,
        _access_2m,
        _access_8m,
        identity_path,
    ) in EXPECTED_FAMILY_MATRIX.items():
        for field in (
            "terminal_role",
            "gradient_eligibility",
            "payload_access_100k",
            "payload_access_500k",
            "payload_access_2m",
            "payload_access_8m",
        ):
            for mutation in ("missing", "wrong_value", "wrong_type"):
                cases.append((family, field, mutation))
        if identity_path is None:
            cases.append((family, "identity_metadata_relative_path", "unexpected"))
        else:
            for mutation in ("missing", "wrong_value", "wrong_type"):
                cases.append((family, "identity_metadata_relative_path", mutation))
    return tuple(cases)


def _wrong_value(field: str) -> str:
    return {
        "terminal_role": "other",
        "gradient_eligibility": "sometimes",
        "payload_access_100k": "payload_allowed",
        "payload_access_500k": "payload_allowed",
        "payload_access_2m": "payload_allowed",
        "payload_access_8m": "payload_allowed",
        "identity_metadata_relative_path": "processed/wrong/metadata.jsonl",
    }[field]


def _different_valid_value(field: str, current: str) -> str:
    values = {
        "terminal_role": ("train", "eval", "governance"),
        "gradient_eligibility": ("first_stage", "later", "never"),
        "payload_access_100k": (
            "metadata_only",
            "identity_metadata_only",
            "approved_processed_lane_only",
        ),
        "payload_access_500k": (
            "metadata_only",
            "identity_metadata_only",
            "approved_processed_lane_only",
        ),
        "payload_access_2m": (
            "metadata_only",
            "identity_metadata_only",
            "approved_processed_lane_only",
        ),
        "payload_access_8m": (
            "metadata_only",
            "identity_metadata_only",
            "approved_processed_lane_only",
        ),
    }[field]
    return next(value for value in values if value != current)


def _suite_fixture() -> dict:
    return load_suite_policy(POLICY)


def test_suite_policy_pins_exact_evaluation_identity_block() -> None:
    policy = _suite_fixture()
    assert policy["evaluation_identity"] == EXPECTED_EVALUATION_IDENTITY
    validate_suite_policy(policy, _registry_fixture())

    for mutation in (
        {"required_families": ["swe-bench"]},
        {"blocked_unavailable_families": []},
        {"unexpected": True},
    ):
        changed = copy.deepcopy(policy)
        changed["evaluation_identity"].update(mutation)
        with pytest.raises(SuitePolicyError, match="evaluation identity"):
            validate_suite_policy(changed, _registry_fixture())

    missing = copy.deepcopy(policy)
    missing.pop("evaluation_identity")
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(missing, _registry_fixture())

    reordered = copy.deepcopy(policy)
    families = reordered.pop("families")
    evaluation_identity = reordered.pop("evaluation_identity")
    reordered["families"] = families
    reordered["evaluation_identity"] = evaluation_identity
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(reordered, _registry_fixture())


def test_evaluation_identity_scope_comes_from_exact_suite_policy() -> None:
    assert foundation_suite.evaluation_identity_scope(_suite_fixture()) == (
        ("swe-bench", "swe-mera", "swe-polybench"),
        ("swe-bench-pro",),
    )

    partial = _suite_fixture()
    partial["evaluation_identity"]["required_families"] = ["swe-bench"]
    with pytest.raises(SuitePolicyError, match="evaluation identity"):
        foundation_suite.evaluation_identity_scope(partial)


def _registry_fixture() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _write_fixture(data_root: Path, relative_path: str) -> Path:
    path = data_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"metadata-only test fixture")
    return path


def _make_real_directory_link(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"directory junctions unavailable: {result.stderr.strip()}")
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


EXPECTED_PUBLIC_SUITE_API = (
    "SuitePolicyError",
    "build_suite_completeness_report",
    "evaluation_identity_scope",
    "load_suite_policy",
    "open_authorized_payload",
    "validate_suite_policy",
)


def _assert_exact_public_suite_api() -> None:
    assert tuple(foundation_suite.__all__) == EXPECTED_PUBLIC_SUITE_API
    module_defined_public_callables = {
        name
        for name, value in vars(foundation_suite).items()
        if not name.startswith("_")
        and callable(value)
        and getattr(value, "__module__", None) == foundation_suite.__name__
    }
    assert module_defined_public_callables == set(EXPECTED_PUBLIC_SUITE_API)


def _plan_task_section(plan: str, task_number: int) -> str:
    marker = f"### Task {task_number}:"
    assert marker in plan
    section = plan.split(marker, 1)[1]
    next_marker = f"### Task {task_number + 1}:"
    return section.split(next_marker, 1)[0]


def _assert_secure_stream_plan(plan: str) -> None:
    assert "assert_payload_read_allowed" not in plan

    task_3 = _plan_task_section(plan, 3)
    assert "def build_eval_identity_index(" in task_3
    build_identity_block = task_3.split(
        "def build_eval_identity_index(",
        1,
    )[1].split("```", 1)[0]
    assert "with open_authorized_payload(" in build_identity_block
    assert "as stream:" in build_identity_block
    assert "for raw_line in stream:" in build_identity_block
    assert "json.loads(raw_line)" in build_identity_block
    source_path_reopen = re.compile(
        r"(?:Path\(\s*source_path\s*\)|\bsource_path)\s*\.\s*"
        r"(?:open|read_text|read_bytes)\s*\(|\bopen\s*\(\s*source_path\b"
    )
    assert source_path_reopen.search(build_identity_block) is None

    task_4 = _plan_task_section(plan, 4)
    prepare_paragraph = task_4.split(
        "`prepare_stage()` must, in order:",
        1,
    )[1].split("\n\n", 1)[0]
    for required in (
        "separate `with open_authorized_payload(...) as stream` contexts",
        "stream-aware converter",
        "verified binary stream",
        "adapter-report mapping parsed from its yielded verified binary stream",
        "must never pass either protected pathname",
        "current path-opening `run_full_conversion()` implementation",
    ):
        assert required in prepare_paragraph
    path_reopening_conversion = re.compile(r"(?<!`)run_full_conversion\s*\(\s*(?!\))")
    assert path_reopening_conversion.search(task_4) is None


def test_verified_stream_is_the_only_public_payload_access_api() -> None:
    _assert_exact_public_suite_api()


def test_public_api_drift_guard_rejects_check_only_alias(monkeypatch) -> None:
    monkeypatch.setattr(
        foundation_suite,
        "validate_data_access",
        foundation_suite._validate_payload_request,
        raising=False,
    )
    with pytest.raises(AssertionError):
        _assert_exact_public_suite_api()


def test_plan_and_package_forbid_check_then_reopen_payload_access() -> None:
    plan = AUTHORITATIVE_PLAN.read_text(encoding="utf-8")
    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "src/pneuma_lab/foundation").glob("*.py"))
    )

    assert "assert_payload_read_allowed" not in package_text
    _assert_secure_stream_plan(plan)


@pytest.mark.parametrize(
    "mutation",
    ["task_3_reopen", "task_4_path_converter", "task_4_path_mapping"],
)
def test_plan_drift_guard_rejects_insecure_stream_mutations(mutation: str) -> None:
    plan = AUTHORITATIVE_PLAN.read_text(encoding="utf-8")
    if mutation == "task_3_reopen":
        drifted = plan.replace(
            "for raw_line in stream:",
            'for raw_line in Path(source_path).open("rb"):',
            1,
        )
    elif mutation == "task_4_path_converter":
        drifted = plan.replace(
            "consume the processed OpenHands traces and adapter report only inside "
            "separate `with open_authorized_payload(...) as stream` contexts; "
            "verify or run a stream-aware conversion entry point",
            "call run_full_conversion(input_path=trace_path, "
            "adapter_report_path=adapter_report_path)",
            1,
        )
    else:
        drifted = plan.replace(
            "and an adapter-report mapping parsed from its yielded verified binary stream",
            "and an adapter-report pathname",
            1,
        )
    assert drifted != plan
    with pytest.raises(AssertionError):
        _assert_secure_stream_plan(drifted)


def test_suite_has_exactly_ten_coherent_family_roles() -> None:
    policy = load_suite_policy(POLICY)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert validate_suite_policy(policy, registry) == ACTIVE_DATASET_GROUPS
    assert policy["first_stage"]["authorized_lane_candidates"] == [
        "swe-gym-openhands-sampled"
    ]


@pytest.mark.parametrize(
    ("field", "mutation"),
    [
        ("manifest_kind", "missing"),
        ("manifest_kind", "wrong"),
        ("manifest_schema_version", "missing"),
        ("manifest_schema_version", "wrong"),
    ],
)
def test_suite_requires_exact_identity_and_version(
    field: str,
    mutation: str,
) -> None:
    policy = _suite_fixture()
    if mutation == "missing":
        policy.pop(field)
    else:
        policy[field] = "wrong"
    with pytest.raises(SuitePolicyError, match="manifest"):
        validate_suite_policy(policy, _registry_fixture())


@pytest.mark.parametrize("location", ["top", "first_stage", "family"])
def test_suite_rejects_extra_policy_keys(location: str) -> None:
    policy = _suite_fixture()
    if location == "top":
        policy["unexpected"] = True
    elif location == "first_stage":
        policy["first_stage"]["unexpected"] = True
    else:
        policy["families"][0]["unexpected"] = True
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, _registry_fixture())


@pytest.mark.parametrize("mutation", ["deleted", "duplicated", "moved"])
def test_suite_reconciles_candidate_lane_exactly_once(mutation: str) -> None:
    registry = _registry_fixture()
    lanes = registry["lanes"]
    index = next(
        index
        for index, lane in enumerate(lanes)
        if lane["lane_id"] == "swe-gym-openhands-sampled"
    )
    if mutation == "deleted":
        lanes.pop(index)
    elif mutation == "duplicated":
        lanes.append(copy.deepcopy(lanes[index]))
    else:
        lanes[index]["source_family"] = "open-swe-traces"
    with pytest.raises(SuitePolicyError, match="candidate lane"):
        validate_suite_policy(_suite_fixture(), registry)


@pytest.mark.parametrize("field", ["lane_id", "source_family"])
def test_suite_rejects_contradictory_candidate_lane_structure(field: str) -> None:
    registry = _registry_fixture()
    candidate = next(
        lane
        for lane in registry["lanes"]
        if lane["lane_id"] == "swe-gym-openhands-sampled"
    )
    candidate.pop(field)
    with pytest.raises(SuitePolicyError, match="candidate lane"):
        validate_suite_policy(_suite_fixture(), registry)


@pytest.mark.parametrize(
    ("family", "field", "mutation"),
    _matrix_mutations(),
    ids=lambda value: str(value),
)
def test_suite_requires_exact_family_policy_matrix(
    family: str,
    field: str,
    mutation: str,
) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    item = next(entry for entry in policy["families"] if entry["family"] == family)
    if mutation == "missing":
        item.pop(field)
    elif mutation == "wrong_type":
        item[field] = ["wrong-type"]
    elif mutation == "unexpected":
        item[field] = f"processed/{family}/unexpected.jsonl"
    else:
        item[field] = _wrong_value(field)
    with pytest.raises(SuitePolicyError, match="exact policy matrix"):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize(
    ("family", "field"),
    [
        (family, field)
        for family in EXPECTED_FAMILY_MATRIX
        for field in (
            "terminal_role",
            "gradient_eligibility",
            "payload_access_100k",
            "payload_access_500k",
            "payload_access_2m",
            "payload_access_8m",
        )
    ],
)
def test_suite_rejects_every_valid_to_valid_matrix_mutation(
    family: str,
    field: str,
) -> None:
    policy = _suite_fixture()
    item = next(entry for entry in policy["families"] if entry["family"] == family)
    item[field] = _different_valid_value(field, item[field])

    with pytest.raises(SuitePolicyError, match="exact policy matrix"):
        validate_suite_policy(policy, _registry_fixture())


def test_suite_requires_documented_family_order() -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"][0], policy["families"][1] = (
        policy["families"][1],
        policy["families"][0],
    )
    with pytest.raises(SuitePolicyError, match="documented order"):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_suite_family_membership_fails_closed(mutation: str) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if mutation == "missing":
        policy["families"].pop()
    elif mutation == "duplicate":
        policy["families"][-1] = copy.deepcopy(policy["families"][0])
    else:
        policy["families"][-1]["family"] = "unknown-family"
    with pytest.raises(SuitePolicyError, match="each active family exactly once"):
        validate_suite_policy(policy, registry)


def test_suite_policy_shape_errors_are_domain_errors() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy = _suite_fixture()
    policy["families"][0] = "multi-swe-bench"
    with pytest.raises(SuitePolicyError, match="family entries must be objects"):
        validate_suite_policy(policy, registry)

    policy = _suite_fixture()
    policy["first_stage"].pop("authorized_lane_candidates")
    with pytest.raises(SuitePolicyError, match="authorized lane candidates"):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize(
    "first_stage",
    [
        None,
        [],
        {
            "stage": 100_000,
            "authorized_lane_candidates": ["swe-gym-openhands-sampled"],
        },
        {"stage": "100k", "authorized_lane_candidates": "swe-gym-openhands-sampled"},
        {"stage": "100k", "authorized_lane_candidates": [123]},
    ],
)
def test_suite_rejects_malformed_first_stage(first_stage: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["first_stage"] = first_stage
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize("families", [None, {}, "families"])
def test_suite_rejects_malformed_families_container(families: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"] = families
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, registry)


@pytest.mark.parametrize("family", [None, [], 7])
def test_suite_rejects_malformed_family_name(family: object) -> None:
    policy = _suite_fixture()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    policy["families"][0]["family"] = family
    with pytest.raises(SuitePolicyError):
        validate_suite_policy(policy, registry)


def test_load_suite_policy_rejects_invalid_json_and_non_object(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(SuitePolicyError, match="valid JSON"):
        load_suite_policy(malformed)

    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(SuitePolicyError, match="JSON object"):
        load_suite_policy(non_object)


@pytest.mark.parametrize(
    "payload",
    (
        b'{"manifest_kind":"x","manifest_kind":"x"}',
        (b'{"evaluation_identity":{"required_families":[],"required_families":[]}}'),
    ),
)
def test_load_suite_policy_rejects_duplicate_members_at_every_depth(
    tmp_path: Path,
    payload: bytes,
) -> None:
    path = tmp_path / "duplicate.json"
    path.write_bytes(payload)
    with pytest.raises(SuitePolicyError, match="duplicate"):
        load_suite_policy(path)


@pytest.mark.parametrize("constant", (b"NaN", b"Infinity", b"-Infinity"))
def test_load_suite_policy_rejects_nonstandard_constants(
    tmp_path: Path,
    constant: bytes,
) -> None:
    path = tmp_path / "constant.json"
    path.write_bytes(b'{"value":' + constant + b"}")
    with pytest.raises(SuitePolicyError, match="valid JSON"):
        load_suite_policy(path)


def test_load_suite_policy_wraps_recursion_and_unicode_failures(
    tmp_path: Path,
) -> None:
    # Depth must exceed the C json scanner recursion guard on every
    # supported interpreter (Python 3.12.13 parses ~8k levels; 3.14's
    # stack guard allows ~10k+), so 2000 parses cleanly and never
    # exercises the wrapping path.
    nesting_depth = 100000
    recursive = tmp_path / "recursive.json"
    recursive.write_bytes(b"[" * nesting_depth + b"0" + b"]" * nesting_depth)
    malformed_utf8 = tmp_path / "malformed-utf8.json"
    malformed_utf8.write_bytes(b'{"value":"\xff"}')
    for path in (recursive, malformed_utf8):
        with pytest.raises(SuitePolicyError, match="valid JSON"):
            load_suite_policy(path)


def test_payload_opener_denies_governance_lanes_before_open(tmp_path: Path) -> None:
    policy = _suite_fixture()
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="100k",
            family="sec-bench-pro",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        ):
            pytest.fail("denied payload must not be yielded")


def test_payload_opener_allows_only_the_approved_first_stage_lane(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    approved = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        policy,
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=approved,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-verifier",
            data_root=tmp_path,
            path=approved,
        ):
            pytest.fail("denied payload must not be yielded")


@pytest.mark.parametrize(
    "path",
    [
        "processed/SWE-Gym/openhands-sampled/records.jsonl",
        "processed/swe-gym/OpenHands-Sampled/records.jsonl",
        "processed/swe-gym/openhands-sampled/../records.jsonl",
        "processed/swe-gym/./openhands-sampled/records.jsonl",
        "processed/archive/processed/swe-gym/openhands-sampled/records.jsonl",
        "processed-copy/swe-gym/openhands-sampled/records.jsonl",
        "processed/swe-gym-copy/openhands-sampled/records.jsonl",
        "processed/swe-gym/openhands-sampled-copy/records.jsonl",
        "processed/swe-gym/not-openhands-sampled/records.jsonl",
    ],
)
def test_payload_opener_rejects_ambiguous_approved_lane_paths(
    tmp_path: Path,
    path: str,
) -> None:
    candidate = f"{tmp_path.as_posix()}/{path}"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=candidate,
        ):
            pytest.fail("ambiguous path must not be yielded")


def test_payload_opener_accepts_exact_trusted_approved_lane_path(
    tmp_path: Path,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        _suite_fixture(),
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=payload,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"


def test_payload_opener_allows_only_declared_identity_metadata(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    metadata = _write_fixture(
        tmp_path,
        "processed/swe-bench/normalized_metadata.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        policy,
        stage="100k",
        family="swe-bench",
        lane_id=None,
        data_root=tmp_path,
        path=metadata,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="100k",
            family="swe-bench",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/swe-bench/records.jsonl",
        ):
            pytest.fail("undeclared metadata must not be yielded")


@pytest.mark.parametrize(
    "path",
    [
        "processed/SWE-Bench/normalized_metadata.jsonl",
        "processed/swe-bench/Normalized_Metadata.jsonl",
        "processed/swe-bench/../normalized_metadata.jsonl",
        "processed/./swe-bench/normalized_metadata.jsonl",
        "processed/archive/processed/swe-bench/normalized_metadata.jsonl",
        "processed-copy/swe-bench/normalized_metadata.jsonl",
        "processed/swe-bench-copy/normalized_metadata.jsonl",
        "processed/swe-bench/not-normalized_metadata.jsonl",
        "processed/swe-bench/normalized_metadata.jsonl.bak",
        "processed/swe-bench/normalized_metadata.jsonl/descendant",
    ],
)
def test_payload_opener_rejects_ambiguous_identity_paths(
    tmp_path: Path,
    path: str,
) -> None:
    candidate = f"{tmp_path.as_posix()}/{path}"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-bench",
            lane_id=None,
            data_root=tmp_path,
            path=candidate,
        ):
            pytest.fail("ambiguous path must not be yielded")


def test_payload_opener_accepts_exact_trusted_identity_path(tmp_path: Path) -> None:
    metadata = _write_fixture(
        tmp_path,
        "processed/swe-bench/normalized_metadata.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        _suite_fixture(),
        stage="100k",
        family="swe-bench",
        lane_id=None,
        data_root=tmp_path,
        path=metadata,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"


def test_payload_opener_enforces_the_same_matrix_at_the_500k_stage(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    approved = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        policy,
        stage="500k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=approved,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"

    metadata = _write_fixture(
        tmp_path,
        "processed/swe-bench/normalized_metadata.jsonl",
    )
    with foundation_suite.open_authorized_payload(
        policy,
        stage="500k",
        family="swe-bench",
        lane_id=None,
        data_root=tmp_path,
        path=metadata,
    ) as stream:
        assert stream.read() == b"metadata-only test fixture"

    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="500k",
            family="sec-bench-pro",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        ):
            pytest.fail("denied payload must not be yielded")

    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="500k",
            family="swe-gym",
            lane_id="swe-gym-openhands-verifier",
            data_root=tmp_path,
            path=approved,
        ):
            pytest.fail("denied payload must not be yielded")


def test_payload_opener_opens_both_approved_lanes_at_the_2m_stage(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    openhands = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    traces = _write_fixture(
        tmp_path,
        "processed/open-swe-traces/pneuma-trace/pneuma_traces.jsonl",
    )
    for family, lane_id, payload in (
        ("swe-gym", "swe-gym-openhands-sampled", openhands),
        ("open-swe-traces", "open-swe-traces", traces),
    ):
        with foundation_suite.open_authorized_payload(
            policy,
            stage="2m",
            family=family,
            lane_id=lane_id,
            data_root=tmp_path,
            path=payload,
        ) as stream:
            assert stream.read() == b"metadata-only test fixture"


def test_payload_opener_denies_the_traces_lane_before_the_2m_stage(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    traces = _write_fixture(
        tmp_path,
        "processed/open-swe-traces/pneuma-trace/pneuma_traces.jsonl",
    )
    for stage in ("100k", "500k"):
        with pytest.raises(SuitePolicyError, match="metadata-only"):
            with foundation_suite.open_authorized_payload(
                policy,
                stage=stage,
                family="open-swe-traces",
                lane_id="open-swe-traces",
                data_root=tmp_path,
                path=traces,
            ):
                pytest.fail("denied payload must not be yielded")


def test_payload_opener_keeps_2m_denials_for_unapproved_families(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    for family in ("multi-swe-bench", "swe-evo", "swe-chat", "sec-bench-pro"):
        with pytest.raises(SuitePolicyError, match="metadata-only"):
            with foundation_suite.open_authorized_payload(
                policy,
                stage="2m",
                family=family,
                lane_id=family,
                data_root=tmp_path,
                path=tmp_path / f"processed/{family}/records.jsonl",
            ):
                pytest.fail("denied payload must not be yielded")


@pytest.mark.parametrize(
    ("stage", "family"),
    [("1m", "swe-gym"), ("8m", "swe-gym"), ("100k", "unknown-family")],
)
def test_payload_opener_unknown_stage_or_family_fails_closed(
    tmp_path: Path,
    stage: str,
    family: str,
) -> None:
    with pytest.raises(SuitePolicyError):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage=stage,
            family=family,
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "payload.jsonl",
        ):
            pytest.fail("invalid request must not be yielded")


@pytest.mark.parametrize("path", [None, object(), ""])
def test_payload_opener_rejects_missing_or_non_path_values(
    tmp_path: Path,
    path: object,
) -> None:
    with pytest.raises(SuitePolicyError):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=path,
        ):
            pytest.fail("invalid path must not be yielded")


def test_payload_opener_rejects_malformed_family_without_builtin_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family=[],
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path="processed/swe-gym/openhands-sampled/records.jsonl",
        ):
            pytest.fail("malformed request must not be yielded")


def test_payload_opener_rejects_existing_path_outside_trusted_root(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    untrusted = _write_fixture(
        tmp_path / "untrusted",
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    with pytest.raises(SuitePolicyError, match="trusted data root"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=trusted,
            path=untrusted,
        ):
            pytest.fail("outside path must not be yielded")


def test_payload_opener_rejects_explicit_untrusted_windows_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=Path(
                r"C:\untrusted-root\processed\swe-gym\openhands-sampled\rows.jsonl"
            ),
        ):
            pytest.fail("outside path must not be yielded")


def test_payload_opener_rejects_nonexistent_trusted_lane_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError, match="exist"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=tmp_path / "processed/swe-gym/openhands-sampled/missing.jsonl",
        ):
            pytest.fail("missing path must not be yielded")


def test_payload_opener_rejects_simulated_nested_reparse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/nested/records.jsonl",
    )
    nested = payload.parent
    monkeypatch.setattr(
        foundation_suite,
        "_is_link_or_reparse",
        lambda path: path == nested,
        raising=False,
    )
    with pytest.raises(SuitePolicyError, match="trusted data root"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        ):
            pytest.fail("reparse path must not be yielded")


def test_payload_opener_rejects_nested_resolution_escape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/nested/records.jsonl",
    )
    nested = payload.parent
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    real_resolve = Path.resolve

    def relocated_resolve(path: Path, *args, **kwargs) -> Path:
        if path == nested:
            return outside
        if path == payload:
            return outside / payload.name
        return real_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", relocated_resolve)
    with pytest.raises(SuitePolicyError, match="trusted data root"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        ):
            pytest.fail("escaped path must not be yielded")


def test_payload_opener_rejects_real_nested_symlink_when_supported(
    tmp_path: Path,
) -> None:
    lane = tmp_path / "processed/swe-gym/openhands-sampled"
    lane.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "records.jsonl").write_bytes(b"outside")
    link = lane / "nested"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    with pytest.raises(SuitePolicyError, match="trusted data root"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=link / "records.jsonl",
        ):
            pytest.fail("symlink path must not be yielded")


def test_payload_opener_rejects_alternate_stream_syntax(tmp_path: Path) -> None:
    base = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    alternate = Path(f"{base}:alternate")
    try:
        alternate.write_bytes(b"alternate stream or colon-named file")
    except OSError as exc:
        pytest.skip(f"alternate-stream fixture unavailable: {exc}")

    with pytest.raises(SuitePolicyError):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=alternate,
        ):
            pytest.fail("alternate stream must not be yielded")


def test_open_authorized_payload_yields_and_closes_the_verified_stream(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    real_open = os.open
    opened_fds: list[int] = []

    def tracked_open(path, flags, mode=0o777, *, dir_fd=None):
        tracked_open.flags = flags
        kwargs = {} if dir_fd is None else {"dir_fd": dir_fd}
        fd = real_open(path, flags, mode, **kwargs)
        opened_fds.append(fd)
        return fd

    tracked_open.flags = 0

    monkeypatch.setattr(foundation_suite.os, "open", tracked_open)
    with foundation_suite.open_authorized_payload(
        _suite_fixture(),
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=payload,
    ) as stream:
        assert stream.tell() == 0
        assert stream.read() == b"metadata-only test fixture"
        assert stream.closed is False

    assert stream.closed is True
    assert len(opened_fds) == 1
    expected_flags = (
        getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    assert tracked_open.flags & expected_flags == expected_flags


def test_open_authorized_payload_denial_never_opens_a_descriptor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def unexpected_open(*_args, **_kwargs):
        pytest.fail("denied payload must not be opened")

    monkeypatch.setattr(foundation_suite.os, "open", unexpected_open)
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="sec-bench-pro",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        ):
            pytest.fail("denied payload must not be yielded")


def test_open_authorized_payload_rejects_injected_outside_handle_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    outside = _write_fixture(tmp_path / "outside", "records.jsonl")
    real_open = os.open
    opened_fds: list[int] = []

    def tracked_open(path, flags, mode=0o777, *, dir_fd=None):
        kwargs = {} if dir_fd is None else {"dir_fd": dir_fd}
        fd = real_open(path, flags, mode, **kwargs)
        opened_fds.append(fd)
        return fd

    monkeypatch.setattr(foundation_suite.os, "open", tracked_open)
    monkeypatch.setattr(
        foundation_suite,
        "_final_path_from_fd",
        lambda _fd: outside.resolve(strict=True),
        raising=False,
    )

    yielded = False
    with pytest.raises(SuitePolicyError, match="opened payload"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        ):
            yielded = True

    assert yielded is False
    assert len(opened_fds) == 1
    with pytest.raises(OSError):
        os.fstat(opened_fds[0])


def test_open_authorized_payload_rejects_directory_link_swap_before_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/nested/records.jsonl",
    )
    nested = payload.parent
    saved_nested = nested.with_name("nested-before-race")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / payload.name).write_bytes(b"outside bytes must never be yielded")
    staged_link = nested.with_name("nested-race-link")
    _make_real_directory_link(staged_link, outside)

    real_open = os.open
    attack_ran = False

    def raced_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal attack_ran
        if not attack_ran:
            nested.rename(saved_nested)
            staged_link.rename(nested)
            attack_ran = True
        kwargs = {} if dir_fd is None else {"dir_fd": dir_fd}
        return real_open(path, flags, mode, **kwargs)

    monkeypatch.setattr(foundation_suite.os, "open", raced_open)
    yielded = False
    with pytest.raises(SuitePolicyError, match="opened payload"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        ) as stream:
            yielded = True
            assert stream.read() != b"outside bytes must never be yielded"

    assert attack_ran is True
    assert yielded is False


def test_open_authorized_payload_rejects_final_file_replacement_before_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    replacement = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/replacement.tmp",
    )
    replacement.write_bytes(b"replacement bytes must never be yielded")
    real_open = os.open
    attack_ran = False

    def raced_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal attack_ran
        if not attack_ran:
            os.replace(replacement, payload)
            attack_ran = True
        kwargs = {} if dir_fd is None else {"dir_fd": dir_fd}
        return real_open(path, flags, mode, **kwargs)

    monkeypatch.setattr(foundation_suite.os, "open", raced_open)
    yielded = False
    with pytest.raises(SuitePolicyError, match="opened payload"):
        with foundation_suite.open_authorized_payload(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        ) as stream:
            yielded = True
            assert stream.read() != b"replacement bytes must never be yielded"

    assert attack_ran is True
    assert yielded is False


def test_completeness_report_is_schema_valid_and_lists_all_families(
    tmp_path: Path,
) -> None:
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    schema = pls.load_schema("foundation-suite-report.schema.json")
    Draft202012Validator(schema).validate(report)
    assert tuple(item["family"] for item in report["families"]) == (
        ACTIVE_DATASET_GROUPS
    )
    assert all(item["payload_opened"] is False for item in report["families"])


def test_suite_report_schema_rejects_duplicate_family_and_extra_fields(
    tmp_path: Path,
) -> None:
    schema = pls.load_schema("foundation-suite-report.schema.json")
    validator = Draft202012Validator(schema)
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["families"][-1] = copy.deepcopy(report["families"][0])
    with pytest.raises(ValidationError):
        validator.validate(report)

    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(report)


@pytest.mark.parametrize(
    ("family", "field", "value"),
    [
        ("swe-chat", "terminal_role", "train"),
        ("swe-chat", "gradient_eligibility", "first_stage"),
        ("swe-chat", "payload_access_100k", "approved_processed_lane_only"),
        ("swe-chat", "payload_access_500k", "approved_processed_lane_only"),
        ("swe-chat", "payload_access_2m", "approved_processed_lane_only"),
        ("swe-chat", "payload_access_8m", "approved_processed_lane_only"),
    ],
)
def test_suite_report_schema_pins_family_role_matrix(
    tmp_path: Path,
    family: str,
    field: str,
    value: str,
) -> None:
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    item = next(entry for entry in report["families"] if entry["family"] == family)
    item[field] = value
    with pytest.raises(ValidationError):
        Draft202012Validator(
            pls.load_schema("foundation-suite-report.schema.json")
        ).validate(report)


def test_suite_report_schema_rejects_wrong_family_and_reordering(
    tmp_path: Path,
) -> None:
    validator = Draft202012Validator(
        pls.load_schema("foundation-suite-report.schema.json")
    )
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["families"][0]["family"] = "swe-chat"
    with pytest.raises(ValidationError):
        validator.validate(report)

    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    report["families"][0], report["families"][1] = (
        report["families"][1],
        report["families"][0],
    )
    with pytest.raises(ValidationError):
        validator.validate(report)


@pytest.mark.parametrize("mutation", ["changed", "removed", "added"])
def test_suite_report_schema_pins_identity_metadata_paths(
    tmp_path: Path,
    mutation: str,
) -> None:
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    if mutation == "added":
        report["families"][0]["identity_metadata_relative_path"] = (
            "processed/multi-swe-bench/normalized_metadata.jsonl"
        )
    else:
        item = next(
            entry for entry in report["families"] if entry["family"] == "swe-bench"
        )
        if mutation == "changed":
            item["identity_metadata_relative_path"] = "processed/swe-bench/other.jsonl"
        else:
            item.pop("identity_metadata_relative_path")
    with pytest.raises(ValidationError):
        Draft202012Validator(
            pls.load_schema("foundation-suite-report.schema.json")
        ).validate(report)


@pytest.mark.parametrize("mutation", ["fewer", "extra"])
def test_suite_report_schema_requires_exactly_ten_entries(
    tmp_path: Path,
    mutation: str,
) -> None:
    report = build_suite_completeness_report(_suite_fixture(), tmp_path)
    if mutation == "fewer":
        report["families"].pop()
    else:
        report["families"].append(copy.deepcopy(report["families"][-1]))
    with pytest.raises(ValidationError):
        Draft202012Validator(
            pls.load_schema("foundation-suite-report.schema.json")
        ).validate(report)
