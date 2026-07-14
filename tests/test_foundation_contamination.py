"""Complete identity-level evaluation disjointness is mandatory."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

import pytest

from pneuma_lab.foundation import contamination, eval_identities
from pneuma_lab.foundation.contamination import build_contamination_receipt
from pneuma_lab.foundation.eval_identities import (
    EVAL_METADATA_FIELDS,
    IDENTITY_FIELDS,
    ContaminationIndexError,
    IdentityRecord,
    IdentityRecordError,
    build_eval_identity_index,
    identity_from_foundation_record,
    iter_eval_metadata_identities,
    load_required_eval_identities,
)
from pneuma_lab.foundation.suite import load_suite_policy


ROOT = Path(__file__).resolve().parents[1]
SUITE_POLICY = ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json"


def _suite_policy() -> dict:
    return load_suite_policy(SUITE_POLICY)


def _identity(**overrides) -> IdentityRecord:
    values = {
        "family": "swe-gym",
        "lane_id": "swe-gym-openhands-sampled",
        "repo": "o/r",
        "issue_or_pr": "1",
        "task_id": "task-1",
        "base_commit": "a",
        "patch_sha256": "b",
        "test_patch_sha256": "c",
        "fuzzy_text_sha256": "d",
    }
    values.update(overrides)
    return IdentityRecord(**values)


def _evaluation_identity(family: str, **overrides) -> IdentityRecord:
    values = {
        "family": family,
        "lane_id": family,
        "repo": f"eval/{family}",
        "issue_or_pr": "900",
        "task_id": f"{family}-900",
        "base_commit": f"{family}-commit",
        "patch_sha256": f"{family}-patch",
        "test_patch_sha256": f"{family}-test-patch",
        "fuzzy_text_sha256": f"{family}-text",
    }
    values.update(overrides)
    return IdentityRecord(**values)


def _complete_evaluation(*identities: IdentityRecord) -> tuple[IdentityRecord, ...]:
    by_family = {identity.family: identity for identity in identities}
    return tuple(
        by_family.get(family, _evaluation_identity(family))
        for family in ("swe-bench", "swe-mera", "swe-polybench")
    )


def _make_directory_alias(link: Path, target: Path) -> None:
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
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_identity_record_and_nested_identity_extraction() -> None:
    record = {
        "source": {
            "dataset_family": "swe-gym",
            "lane_id": "swe-gym-openhands-sampled",
        },
        "identity": {
            "repo": "o/r",
            "issue_or_pr": "1",
            "task_id": None,
            "base_commit": "a",
            "patch_sha256": "b",
            "test_patch_sha256": "c",
            "fuzzy_text_sha256": "d",
        },
    }
    assert IDENTITY_FIELDS == (
        "repo",
        "issue_or_pr",
        "task_id",
        "base_commit",
        "patch_sha256",
        "test_patch_sha256",
        "fuzzy_text_sha256",
    )
    assert identity_from_foundation_record(record) == _identity(task_id=None)


@pytest.mark.parametrize(
    "record",
    (
        None,
        {},
        {"source": [], "identity": {}},
        {"source": {"dataset_family": None, "lane_id": "x"}, "identity": {}},
        {
            "source": {"dataset_family": "x", "lane_id": "y"},
            "identity": {field: None for field in IDENTITY_FIELDS} | {"repo": 1},
        },
    ),
)
def test_nested_identity_extraction_fails_closed(record) -> None:
    with pytest.raises(IdentityRecordError):
        identity_from_foundation_record(record)


def test_contamination_receipt_detects_every_identity_dimension() -> None:
    training = [
        IdentityRecord(
            "swe-gym",
            "swe-gym-openhands-sampled",
            "o/r",
            "1",
            "t1",
            "a",
            "b",
            "c",
            "d",
        )
    ]
    evaluation = [
        IdentityRecord(
            "swe-bench",
            "swe-bench",
            "o/r",
            "9",
            "t9",
            "z",
            "y",
            "x",
            "w",
        )
    ]
    receipt = build_contamination_receipt(
        training,
        _complete_evaluation(*evaluation),
        suite_policy=_suite_policy(),
    )
    assert receipt["finding_count"] == 1
    assert receipt["findings"][0]["dimensions"] == ["repository"]

    receipt = build_contamination_receipt(
        [_identity()],
        _complete_evaluation(
            _identity(family="swe-bench", lane_id="swe-bench")
        ),
        suite_policy=_suite_policy(),
    )
    assert receipt["findings"][0]["dimensions"] == [
        "repository",
        "repo_issue_or_pr",
        "task",
        "base_commit",
        "patch",
        "test_patch",
        "fuzzy_text",
    ]
    assert receipt["repo_issue_disjoint"] is False


def test_contamination_accepts_proven_disjoint_sets() -> None:
    receipt = build_contamination_receipt(
        [_identity(repo="org/a", issue_or_pr="1")],
        _complete_evaluation(
            _identity(
                family="swe-bench",
                lane_id="swe-bench",
                repo="org/b",
                issue_or_pr="2",
                task_id="task-2",
                base_commit="z",
                patch_sha256="y",
                test_patch_sha256="x",
                fuzzy_text_sha256="w",
            )
        ),
        suite_policy=_suite_policy(),
    )
    assert receipt["finding_count"] == 0
    assert receipt["findings"] == []
    assert receipt["repo_issue_disjoint"] is True


@pytest.mark.parametrize(
    ("training_digest", "evaluation_digest"),
    (
        ("SHA256:" + "A" * 64, "sha256:" + "a" * 64),
        (
            "  SHA256:" + "G" * 64 + "  ",
            "sha256:"
            + hashlib.sha256(("sha256:" + "g" * 64).encode("utf-8")).hexdigest(),
        ),
    ),
)
def test_contamination_uses_shared_digest_canonicalization(
    training_digest: str,
    evaluation_digest: str,
) -> None:
    receipt = build_contamination_receipt(
        [
            _identity(
                repo="train/only",
                issue_or_pr="1",
                task_id="training-task",
                base_commit="training-commit",
                patch_sha256=training_digest,
                test_patch_sha256="training-test-patch",
                fuzzy_text_sha256="training-text",
            )
        ],
        _complete_evaluation(
            _evaluation_identity(
                "swe-bench",
                patch_sha256=evaluation_digest,
            )
        ),
        suite_policy=_suite_policy(),
    )
    assert receipt["finding_count"] == 1
    assert receipt["findings"][0]["dimensions"] == ["patch"]


def test_contamination_receipt_records_complete_policy_coverage() -> None:
    evaluation = _complete_evaluation()
    receipt = build_contamination_receipt(
        [_identity(repo="train/repo")],
        evaluation,
        suite_policy=_suite_policy(),
    )
    assert receipt["required_evaluation_families"] == [
        "swe-bench",
        "swe-mera",
        "swe-polybench",
    ]
    assert receipt["evaluation_family_counts"] == {
        "swe-bench": 1,
        "swe-mera": 1,
        "swe-polybench": 1,
    }
    assert receipt["blocked_evaluation_family_status"] == {
        "swe-bench-pro": "blocked_unavailable",
    }
    assert receipt["evaluation_coverage_complete"] is True
    assert receipt["repo_issue_disjoint"] is True


def test_contamination_normalizes_each_identity_exactly_once(monkeypatch) -> None:
    original = getattr(contamination, "_normalize_identity", lambda identity: None)
    calls = []

    def counted(identity: IdentityRecord):
        calls.append(identity)
        return original(identity)

    monkeypatch.setattr(contamination, "_normalize_identity", counted, raising=False)
    training = tuple(
        _identity(
            lane_id=f"training-{index}",
            repo=f"train/repo-{index}",
            issue_or_pr=str(index),
            task_id=f"training-task-{index}",
        )
        for index in range(5)
    )
    evaluation = _complete_evaluation(
        _evaluation_identity(
            "swe-bench",
            repo="train/repo-3",
            issue_or_pr="3",
        )
    )
    receipt = build_contamination_receipt(
        training,
        evaluation,
        suite_policy=_suite_policy(),
    )
    assert len(calls) == len(training) + len(evaluation)
    assert receipt["finding_count"] == 1
    assert receipt["findings"][0]["dimensions"] == [
        "repository",
        "repo_issue_or_pr",
    ]


@pytest.mark.parametrize(
    "evaluation",
    (
        (),
        (_evaluation_identity("swe-bench"),),
        _complete_evaluation() + (_evaluation_identity("unexpected-eval"),),
        _complete_evaluation() + (_evaluation_identity("swe-bench-pro"),),
    ),
)
def test_contamination_receipt_rejects_incomplete_or_extra_policy_coverage(
    evaluation: tuple[IdentityRecord, ...],
) -> None:
    with pytest.raises(ContaminationIndexError, match="evaluation famil"):
        build_contamination_receipt(
            [_identity()],
            evaluation,
            suite_policy=_suite_policy(),
        )


def test_eval_identity_index_parsing_is_strict_and_derives_numeric_issue(
    tmp_path: Path,
) -> None:
    path = tmp_path / "swe-bench.jsonl"
    path.write_text(
        '{"base_commit":"a","repo":"o/r","source_id":"o__r-123"}\n',
        encoding="utf-8",
    )
    assert tuple(
        iter_eval_metadata_identities(path, "swe-bench", EVAL_METADATA_FIELDS)
    ) == (
        IdentityRecord(
            "swe-bench",
            "swe-bench",
            "o/r",
            "123",
            "o__r-123",
            "a",
            None,
            None,
            None,
        ),
    )

    for invalid in (
        b"\n",
        b"not-json\n",
        b"[]\n",
        b'{"base_commit":"a","repo":"o/r","source_id":"x","extra":1}\n',
        (
            b'{"base_commit":"a","repo":"o/r","source_id":"x",'
            b'"source_id":"y"}\n'
        ),
    ):
        path.write_bytes(invalid)
        with pytest.raises(ContaminationIndexError):
            tuple(iter_eval_metadata_identities(path, "swe-bench", EVAL_METADATA_FIELDS))


@pytest.mark.parametrize(
    "raw_line",
    (
        b'{"source_id":"   ","repo":null,"base_commit":null}\n',
        b'{"source_id":"task-1","repo":"   ","base_commit":null}\n',
        b'{"source_id":"task-1","repo":null,"base_commit":"   "}\n',
        b'{"source_id":[],"repo":null,"base_commit":null}\n',
        b'{"source_id":"task-1","repo":{},"base_commit":null}\n',
    ),
)
def test_eval_identity_index_rejects_semantically_empty_or_malformed_rows(
    tmp_path: Path,
    raw_line: bytes,
) -> None:
    path = tmp_path / "swe-bench.jsonl"
    path.write_bytes(raw_line)
    with pytest.raises(ContaminationIndexError):
        tuple(iter_eval_metadata_identities(path, "swe-bench", EVAL_METADATA_FIELDS))


@pytest.mark.parametrize("constant", (b"NaN", b"Infinity", b"-Infinity"))
def test_eval_identity_decoder_rejects_constants_in_discarded_fields(
    constant: bytes,
) -> None:
    raw_line = (
        b'{"source_id":"task-1","repo":"org/repo","base_commit":null,'
        b'"discarded":'
        + constant
        + b"}"
    )
    with pytest.raises(ContaminationIndexError, match="valid JSON"):
        eval_identities._metadata_row(
            raw_line,
            line_number=1,
            allow_unretained_fields=True,
        )


def test_eval_identity_decoder_wraps_recursion_and_unicode_failures() -> None:
    deeply_nested = (
        b'{"source_id":"task-1","repo":"org/repo","base_commit":null,'
        b'"discarded":'
        + b"[" * 2000
        + b"0"
        + b"]" * 2000
        + b"}"
    )
    for raw_line in (deeply_nested, b'{"source_id":"\xff"}'):
        with pytest.raises(ContaminationIndexError, match="valid JSON"):
            eval_identities._metadata_row(
                raw_line,
                line_number=1,
                allow_unretained_fields=True,
            )


def test_eval_identity_decoder_rejects_nested_duplicate_members() -> None:
    with pytest.raises(ContaminationIndexError, match="duplicate"):
        eval_identities._metadata_row(
            (
                b'{"source_id":"task-1","repo":"org/repo",'
                b'"base_commit":null,"discarded":{"key":1,"key":2}}'
            ),
            line_number=1,
            allow_unretained_fields=True,
        )


def test_eval_identity_index_rejects_empty_and_allowlist_order_is_irrelevant(
    tmp_path: Path,
) -> None:
    path = tmp_path / "swe-bench.jsonl"
    path.write_bytes(b"")
    with pytest.raises(ContaminationIndexError, match="record"):
        tuple(iter_eval_metadata_identities(path, "swe-bench", EVAL_METADATA_FIELDS))

    path.write_text(
        '{"base_commit":null,"repo":"o/r","source_id":"o__r-1"}\n',
        encoding="utf-8",
    )
    identities = tuple(
        iter_eval_metadata_identities(
            path,
            "swe-bench",
            tuple(reversed(EVAL_METADATA_FIELDS)),
        )
    )
    assert identities[0].issue_or_pr == "1"


def test_required_missing_eval_identity_index_fails(tmp_path: Path) -> None:
    with pytest.raises(ContaminationIndexError, match="swe-mera"):
        load_required_eval_identities(
            {"swe-bench": tmp_path / "swe-bench.jsonl"},
            suite_policy=_suite_policy(),
        )


def test_required_eval_identity_indexes_are_deterministic(tmp_path: Path) -> None:
    paths = {}
    for family in ("swe-bench", "swe-mera", "swe-polybench"):
        path = tmp_path / f"{family}.jsonl"
        path.write_text(
            json.dumps(
                {"source_id": f"{family}-1", "repo": family, "base_commit": None}
            )
            + "\n",
            encoding="utf-8",
        )
        paths[family] = path
    identities = load_required_eval_identities(
        dict(reversed(tuple(paths.items()))),
        suite_policy=_suite_policy(),
    )
    assert tuple(identity.family for identity in identities) == (
        "swe-bench",
        "swe-mera",
        "swe-polybench",
    )


@pytest.mark.parametrize("extra_family", ("unexpected-eval", "swe-bench-pro"))
def test_required_eval_identity_indexes_reject_extra_or_blocked_family(
    tmp_path: Path,
    extra_family: str,
) -> None:
    paths = {}
    for family in (
        "swe-bench",
        "swe-mera",
        "swe-polybench",
        extra_family,
    ):
        path = tmp_path / f"{family}.jsonl"
        path.write_text(
            json.dumps(
                {"source_id": f"{family}-1", "repo": family, "base_commit": None}
            )
            + "\n",
            encoding="utf-8",
        )
        paths[family] = path
    with pytest.raises(ContaminationIndexError, match="unexpected"):
        load_required_eval_identities(paths, suite_policy=_suite_policy())


def test_required_eval_identity_indexes_reject_zero_row_required_family(
    tmp_path: Path,
) -> None:
    paths = {}
    for family in ("swe-bench", "swe-mera", "swe-polybench"):
        path = tmp_path / f"{family}.jsonl"
        path.write_text(
            ""
            if family == "swe-mera"
            else json.dumps(
                {"source_id": f"{family}-1", "repo": family, "base_commit": None}
            )
            + "\n",
            encoding="utf-8",
        )
        paths[family] = path
    with pytest.raises(ContaminationIndexError, match="at least one record"):
        load_required_eval_identities(paths, suite_policy=_suite_policy())


def test_required_eval_identity_indexes_reject_file_aliases(
    tmp_path: Path,
) -> None:
    bench = tmp_path / "swe-bench.jsonl"
    mera = tmp_path / "swe-mera.jsonl"
    polybench = tmp_path / "swe-polybench.jsonl"
    bench.write_text(
        '{"source_id":"swe-bench-1","repo":"org/repo","base_commit":null}\n',
        encoding="utf-8",
    )
    try:
        mera.hardlink_to(bench)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    polybench.write_text(
        '{"source_id":"swe-polybench-1","repo":"org/other",'
        '"base_commit":null}\n',
        encoding="utf-8",
    )
    with pytest.raises(ContaminationIndexError, match="duplicated"):
        load_required_eval_identities(
            {
                "swe-bench": bench,
                "swe-mera": mera,
                "swe-polybench": polybench,
            },
            suite_policy=_suite_policy(),
        )


def test_eval_identity_index_uses_only_authorized_verified_stream(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "pneuma-data"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text(
        '{"source_id":"o__r-7","repo":"o/r","base_commit":"abc"}\n',
        encoding="utf-8",
    )
    output = tmp_path / "repo/build/identities/swe-bench.jsonl"
    opened = []
    source_bytes = source.read_bytes()

    class VerifiedStream:
        def __enter__(self):
            opened.append(source)
            self.stream = io.BytesIO(source_bytes)
            return self.stream

        def __exit__(self, *_args):
            self.stream.close()

    def authorized(*_args, **kwargs):
        assert kwargs["data_root"] == data_root
        assert kwargs["path"] == source
        return VerifiedStream()

    monkeypatch.setattr(eval_identities, "open_authorized_payload", authorized)
    real_open = Path.open
    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes

    def guarded_open(path: Path, *args, **kwargs):
        if path == source and opened:
            pytest.fail("protected source path was reopened")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    def guarded_read_text(path: Path, *args, **kwargs):
        if path == source:
            pytest.fail("protected source path used read_text")
        return real_read_text(path, *args, **kwargs)

    def guarded_read_bytes(path: Path, *args, **kwargs):
        if path == source:
            pytest.fail("protected source path used read_bytes")
        return real_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    receipt = build_eval_identity_index(
        {
            "families": [
                {
                    "family": "swe-bench",
                    "identity_metadata_relative_path": (
                        "processed/swe-bench/normalized_metadata.jsonl"
                    ),
                }
            ]
        },
        family="swe-bench",
        repo_root=tmp_path / "repo",
        data_root=data_root,
        source_path=source,
        output_path=output,
        allowed_fields=EVAL_METADATA_FIELDS,
    )
    assert opened == [source]
    assert output.read_bytes() == (
        b'{"base_commit":"abc","repo":"o/r","source_id":"o__r-7"}\n'
    )
    assert receipt["source_relative_path"] == (
        "processed/swe-bench/normalized_metadata.jsonl"
    )
    assert str(tmp_path) not in json.dumps(receipt)


def test_eval_identity_index_filters_unretained_source_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "pneuma-data"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    output = tmp_path / "repo/build/identities/swe-bench.jsonl"
    source_bytes = (
        b'{"source_id":"o__r-7","repo":"o/r","base_commit":"abc",'
        b'"source_file":"C:/private/source.jsonl","license":"review prose",'
        b'"sample":{"patch":"private patch text"}}\n'
    )

    class VerifiedStream:
        def __enter__(self):
            self.stream = io.BytesIO(source_bytes)
            return self.stream

        def __exit__(self, *_args):
            self.stream.close()

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        lambda *_args, **_kwargs: VerifiedStream(),
    )
    build_eval_identity_index(
        {
            "families": [
                {
                    "family": "swe-bench",
                    "identity_metadata_relative_path": (
                        "processed/swe-bench/normalized_metadata.jsonl"
                    ),
                }
            ]
        },
        family="swe-bench",
        repo_root=tmp_path / "repo",
        data_root=data_root,
        source_path=source,
        output_path=output,
        allowed_fields=EVAL_METADATA_FIELDS,
    )
    assert output.read_bytes() == (
        b'{"base_commit":"abc","repo":"o/r","source_id":"o__r-7"}\n'
    )


def test_eval_identity_index_rejects_output_inside_protected_data_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "pneuma-data"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    output = data_root / "generated/swe-bench.jsonl"

    def unexpected_open(*_args, **_kwargs):
        pytest.fail("protected output must fail before opening source payload")

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        unexpected_open,
    )
    with pytest.raises(ContaminationIndexError, match="output"):
        build_eval_identity_index(
            {
                "families": [
                    {
                        "family": "swe-bench",
                        "identity_metadata_relative_path": (
                            "processed/swe-bench/normalized_metadata.jsonl"
                        ),
                    }
                ]
            },
            family="swe-bench",
            repo_root=tmp_path / "repo",
            data_root=data_root,
            source_path=source,
            output_path=output,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
    assert not output.exists()


def test_eval_identity_index_rejects_output_via_data_root_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "pneuma-data"
    data_root.mkdir()
    repo_root = tmp_path / "repo"
    (repo_root / "build").mkdir(parents=True)
    alias = repo_root / "build" / "identities"
    _make_directory_alias(alias, data_root)
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    output = alias / "swe-bench.jsonl"

    def unexpected_open(*_args, **_kwargs):
        pytest.fail("aliased protected output must fail before source access")

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        unexpected_open,
    )
    with pytest.raises(ContaminationIndexError, match="output"):
        build_eval_identity_index(
            {
                "families": [
                    {
                        "family": "swe-bench",
                        "identity_metadata_relative_path": (
                            "processed/swe-bench/normalized_metadata.jsonl"
                        ),
                    }
                ]
            },
            family="swe-bench",
            repo_root=repo_root,
            data_root=data_root,
            source_path=source,
            output_path=output,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
    assert not output.exists()


@pytest.mark.parametrize("alias_level", ("repo", "build", "output_parent"))
def test_eval_identity_index_rejects_output_path_reparse_ancestors(
    tmp_path: Path,
    monkeypatch,
    alias_level: str,
) -> None:
    data_root = tmp_path / "pneuma-data"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    repo_root = tmp_path / "repo"
    external = tmp_path / f"external-{alias_level}"
    external.mkdir()
    if alias_level == "repo":
        _make_directory_alias(repo_root, external)
        output = repo_root / "build/identities/swe-bench.jsonl"
    elif alias_level == "build":
        repo_root.mkdir()
        _make_directory_alias(repo_root / "build", external)
        output = repo_root / "build/identities/swe-bench.jsonl"
    else:
        (repo_root / "build").mkdir(parents=True)
        _make_directory_alias(repo_root / "build" / "identities", external)
        output = repo_root / "build/identities/swe-bench.jsonl"

    def unexpected_open(*_args, **_kwargs):
        pytest.fail("reparse output must fail before opening source payload")

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        unexpected_open,
    )
    with pytest.raises(ContaminationIndexError, match="link|reparse"):
        build_eval_identity_index(
            {
                "families": [
                    {
                        "family": "swe-bench",
                        "identity_metadata_relative_path": (
                            "processed/swe-bench/normalized_metadata.jsonl"
                        ),
                    }
                ]
            },
            family="swe-bench",
            repo_root=repo_root,
            data_root=data_root,
            source_path=source,
            output_path=output,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
    assert not output.exists()


@pytest.mark.parametrize(
    "output_relative",
    (Path("README.md"), Path("build")),
)
def test_eval_identity_index_rejects_output_outside_or_at_build_root(
    tmp_path: Path,
    monkeypatch,
    output_relative: Path,
) -> None:
    data_root = tmp_path / "pneuma-data"
    repo_root = tmp_path / "repo"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    output = repo_root / output_relative

    def unexpected_open(*_args, **_kwargs):
        pytest.fail("unsafe output must fail before opening source payload")

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        unexpected_open,
    )
    with pytest.raises(ContaminationIndexError, match="build"):
        build_eval_identity_index(
            {
                "families": [
                    {
                        "family": "swe-bench",
                        "identity_metadata_relative_path": (
                            "processed/swe-bench/normalized_metadata.jsonl"
                        ),
                    }
                ]
            },
            family="swe-bench",
            repo_root=repo_root,
            data_root=data_root,
            source_path=source,
            output_path=output,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
    assert not output.is_file()


def test_eval_identity_index_rejects_source_duplicate_members(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "pneuma-data"
    source = data_root / "processed/swe-bench/normalized_metadata.jsonl"
    output = tmp_path / "repo/build/identities/swe-bench.jsonl"
    source_bytes = (
        b'{"source_id":"o__r-7","source_id":"o__r-8",'
        b'"repo":"o/r","base_commit":"abc"}\n'
    )

    class VerifiedStream:
        def __enter__(self):
            self.stream = io.BytesIO(source_bytes)
            return self.stream

        def __exit__(self, *_args):
            self.stream.close()

    monkeypatch.setattr(
        eval_identities,
        "open_authorized_payload",
        lambda *_args, **_kwargs: VerifiedStream(),
    )
    with pytest.raises(ContaminationIndexError, match="duplicate"):
        build_eval_identity_index(
            {
                "families": [
                    {
                        "family": "swe-bench",
                        "identity_metadata_relative_path": (
                            "processed/swe-bench/normalized_metadata.jsonl"
                        ),
                    }
                ]
            },
            family="swe-bench",
            repo_root=tmp_path / "repo",
            data_root=data_root,
            source_path=source,
            output_path=output,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
    assert not output.exists()
