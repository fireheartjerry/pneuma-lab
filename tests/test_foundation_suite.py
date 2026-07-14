"""All-ten foundation suite policy and completeness-report tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from pneuma_lab import schemas as pls
from pneuma_lab.foundation import suite as foundation_suite
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS
from pneuma_lab.foundation.suite import (
    SuitePolicyError,
    assert_payload_read_allowed,
    build_suite_completeness_report,
    load_suite_policy,
    validate_suite_policy,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json"
REGISTRY = ROOT / "docs/data/training-readiness/dataset-registry.json"

EXPECTED_FAMILY_MATRIX = {
    "multi-swe-bench": ("train", "later", "metadata_only", None),
    "open-swe-traces": ("train", "later", "metadata_only", None),
    "sec-bench-pro": ("governance", "never", "metadata_only", None),
    "swe-bench": (
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-bench/normalized_metadata.jsonl",
    ),
    "swe-bench-pro": ("eval", "never", "metadata_only", None),
    "swe-chat": ("governance", "never", "metadata_only", None),
    "swe-evo": ("train", "later", "metadata_only", None),
    "swe-gym": ("train", "first_stage", "approved_processed_lane_only", None),
    "swe-mera": (
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-mera/normalized_metadata.jsonl",
    ),
    "swe-polybench": (
        "eval",
        "later",
        "identity_metadata_only",
        "processed/swe-polybench/normalized_metadata.jsonl",
    ),
}


def _matrix_mutations() -> tuple[tuple[str, str, str], ...]:
    cases = []
    for family, (_role, _gradient, _access, identity_path) in (
        EXPECTED_FAMILY_MATRIX.items()
    ):
        for field in (
            "terminal_role",
            "gradient_eligibility",
            "payload_access_100k",
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
    }[field]
    return next(value for value in values if value != current)


def _suite_fixture() -> dict:
    return load_suite_policy(POLICY)


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


def test_payload_guard_denies_governance_lanes_before_open(tmp_path: Path) -> None:
    policy = _suite_fixture()
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="sec-bench-pro",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/sec-bench-pro/records.jsonl",
        )


def test_payload_guard_allows_only_the_approved_first_stage_lane(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    approved = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    assert_payload_read_allowed(
        policy,
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=approved,
    )
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-verifier",
            data_root=tmp_path,
            path=approved,
        )


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
def test_payload_guard_rejects_ambiguous_approved_lane_paths(
    tmp_path: Path,
    path: str,
) -> None:
    candidate = f"{tmp_path.as_posix()}/{path}"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=candidate,
        )


def test_payload_guard_accepts_exact_trusted_approved_lane_path(
    tmp_path: Path,
) -> None:
    payload = _write_fixture(
        tmp_path,
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    assert_payload_read_allowed(
        _suite_fixture(),
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=payload,
    )


def test_payload_guard_allows_only_declared_identity_metadata(
    tmp_path: Path,
) -> None:
    policy = _suite_fixture()
    metadata = _write_fixture(
        tmp_path,
        "processed/swe-bench/normalized_metadata.jsonl",
    )
    assert_payload_read_allowed(
        policy,
        stage="100k",
        family="swe-bench",
        lane_id=None,
        data_root=tmp_path,
        path=metadata,
    )
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            policy,
            stage="100k",
            family="swe-bench",
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "processed/swe-bench/records.jsonl",
        )


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
def test_payload_guard_rejects_ambiguous_identity_paths(
    tmp_path: Path,
    path: str,
) -> None:
    candidate = f"{tmp_path.as_posix()}/{path}"
    with pytest.raises(SuitePolicyError, match="metadata-only"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-bench",
            lane_id=None,
            data_root=tmp_path,
            path=candidate,
        )


def test_payload_guard_accepts_exact_trusted_identity_path(tmp_path: Path) -> None:
    metadata = _write_fixture(
        tmp_path,
        "processed/swe-bench/normalized_metadata.jsonl",
    )
    assert_payload_read_allowed(
        _suite_fixture(),
        stage="100k",
        family="swe-bench",
        lane_id=None,
        data_root=tmp_path,
        path=metadata,
    )


@pytest.mark.parametrize(
    ("stage", "family"),
    [("1m", "swe-gym"), ("100k", "unknown-family")],
)
def test_payload_guard_unknown_stage_or_family_fails_closed(
    tmp_path: Path,
    stage: str,
    family: str,
) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage=stage,
            family=family,
            lane_id=None,
            data_root=tmp_path,
            path=tmp_path / "payload.jsonl",
        )


@pytest.mark.parametrize("path", [None, object(), ""])
def test_payload_guard_rejects_missing_or_non_path_values(
    tmp_path: Path,
    path: object,
) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=path,
        )


def test_payload_guard_rejects_malformed_family_without_builtin_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family=[],
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path="processed/swe-gym/openhands-sampled/records.jsonl",
        )


def test_payload_guard_rejects_existing_path_outside_trusted_root(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    untrusted = _write_fixture(
        tmp_path / "untrusted",
        "processed/swe-gym/openhands-sampled/records.jsonl",
    )
    with pytest.raises(SuitePolicyError, match="trusted data root"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=trusted,
            path=untrusted,
        )


def test_payload_guard_rejects_explicit_untrusted_windows_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=Path(
                r"C:\untrusted-root\processed\swe-gym\openhands-sampled\rows.jsonl"
            ),
        )


def test_payload_guard_rejects_nonexistent_trusted_lane_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(SuitePolicyError, match="exist"):
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=tmp_path / "processed/swe-gym/openhands-sampled/missing.jsonl",
        )


def test_payload_guard_rejects_simulated_nested_reparse(
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
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        )


def test_payload_guard_rejects_nested_resolution_escape(
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
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=payload,
        )


def test_payload_guard_rejects_real_nested_symlink_when_supported(
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
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=link / "records.jsonl",
        )


def test_payload_guard_rejects_alternate_stream_syntax(tmp_path: Path) -> None:
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
        assert_payload_read_allowed(
            _suite_fixture(),
            stage="100k",
            family="swe-gym",
            lane_id="swe-gym-openhands-sampled",
            data_root=tmp_path,
            path=alternate,
        )


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

    assert_payload_read_allowed(
        _suite_fixture(),
        stage="100k",
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=tmp_path,
        path=payload,
    )

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
            entry
            for entry in report["families"]
            if entry["family"] == "swe-bench"
        )
        if mutation == "changed":
            item["identity_metadata_relative_path"] = (
                "processed/swe-bench/other.jsonl"
            )
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
